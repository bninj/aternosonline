#!/usr/bin/env python3
"""look_v4.py - motion-proof "lens look" + smooth lighting for the v4 talking-head plate.

No per-frame person matte touches the speaker. Per picture piece (tripod shots):

 ANALYSIS (640x360, graded):
   * occupancy = union over EVERY frame of the piece of
       - MediaPipe selfie-multiclass person mask (conf > 0.2), and
       - "anything that moved": |frame - temporal median| (catches the swivel
         chair, shadows, hands motion-blur)
   * face position per frame (face-skin class centroid) -> heavily smoothed
     (zero-phase Gaussian, sigma 1.0 s) for the virtual key light
   * skin statistics (face-skin pixels) for cross-piece consistency
   * Depth Anything V2 Small on the piece's temporal median frame (static depth)
   * static veiling-glare field (dark-channel of the median, very blurred)

 RENDER (2304x1296):
   1. far-background falloff: blur weight b(x) = depth falloff (0 at/near the
      speaker's depth plane, 1 at the far wall) x keep-region strength x
      protection ramp.  Protection: b == 0 exactly for every pixel within
      DIL (7% H) of anything the speaker occupies at any time in the piece,
      then a wide smoothstep ramp (FEATH = 13% H).  b is STATIC for the piece.
      Blur = layered disc ("bokeh") kernels in linear light, max radius
      RMAX*H, synthetic grain re-added in proportion to b.
   2. lighting (all in ~linear light):
      per-piece skin nudge (exposure + WB, limited) -> static veil removal
      (DDN pieces) -> soft elliptical virtual key on the smoothed face
      position -> gentle vignette -> subtle halation -> highlight soft-knee.

usage: look_v4.py [--only 0,3] [--out DIR] [--no-blur] [--no-light] [--qa-frames 10,20]
       look_v4.py --concat         (just concatenate existing segments)
"""
import argparse, json, os, subprocess, sys, time
import numpy as np
import cv2

ROOT = "/home/user/ddn-project"
TL = os.environ.get("LOOK_TL", f"{ROOT}/edit/timeline_v4.json")
GRADE = os.environ.get("LOOK_GRADE", f"{ROOT}/edit/grade/grade_v4.json")
KEEP = f"{ROOT}/tools/blur/keep"
MODELS = f"{ROOT}/tools/blur/models"
CACHE = os.environ.get("LOOK_CACHE", f"{ROOT}/tools/look_cache")
W, H = int(os.environ.get("LOOK_W", 2304)), int(os.environ.get("LOOK_H", 1296))
AW, AH = 640, 360                       # analysis resolution
FPS = 30

# --- look parameters (fractions of frame height unless noted)
DIL = 0.07          # hard protection distance around the occupancy
FEATH = 0.13        # width of the protection ramp
RMAX = 0.0075       # max disc radius (~10 px at 1296)
FALLOFF_EXP = 1.0
KEY_STOP = 0.20     # virtual key amount (stops at centre)
KEY_SX, KEY_SY = 0.20, 0.30   # key ellipse sigma (fraction of W, H)
KEY_SMOOTH_S = 1.0  # temporal smoothing sigma (seconds)
VIGNETTE = 0.14     # linear-light loss at the corners
HALATION = 0.02
CONTRAST = {k: 1.06 for k in (8, 9, 10, 11, 12, 13)}     # gentle mid contrast around 18% grey (de-milk)
HAL_THR = 0.85
KNEE, KMAX = 0.70, 1.30       # highlight soft knee (linear)
VEIL_K = {0: 0.40, 8: 0.70, 9: 0.70, 10: 0.70, 11: 0.70, 12: 0.70, 13: 0.70}   # milky shots: fraction of black lift removed
SKIN_NUDGE = 0.6    # fraction of the skin deviation removed
SKIN_MAX_STOP = 0.25   # total skin exposure nudge; half global, half through the key light
SKIN_MAX_WB = 0.05

NT = 2
cv2.setNumThreads(NT)
GAMMA = 2.2
LIN16 = (np.arange(65536, dtype=np.float32) / 65535.0) ** GAMMA          # 16-bit display -> linear
ENC = np.clip(np.round((np.arange(4097, dtype=np.float32) / 4096.0) ** (1 / GAMMA) * 255.0), 0, 255).astype(np.uint8)


def encode(L):
    """linear float -> display uint8 (exact power, no LUT banding)."""
    D = cv2.pow(np.clip(L, 0, 1).astype(np.float32), 1 / GAMMA)
    return cv2.convertScaleAbs(D, alpha=255.0)       # rounds + saturates


def log(*a):
    print("[look]", *a, file=sys.stderr, flush=True)


def pieces():
    tl = json.load(open(TL)); gr = json.load(open(GRADE))
    out = []
    for i, s in enumerate(tl):
        clip = os.path.basename(s["src"]).replace(".MOV", "")
        n = round(s["vend"] * 30) - round(s["vstart"] * 30)
        out.append(dict(i=i, clip=clip, src=f"{ROOT}/footage/raw/{clip}.MOV", t=s["vin"], n=n,
                        grade=gr[str(i)]["filter"]))
    return out


def reader(p, w, h, fmt="rgb24"):
    vf = f"scale={w}:{h}:flags={'lanczos' if w > 1000 else 'area'},format=yuv420p,{p['grade']},format={fmt}"
    cmd = ["ffmpeg", "-loglevel", "error", "-threads", "2", "-ss", f"{p['t']:.4f}", "-i", p["src"], "-frames:v", str(p["n"]),
           "-an", "-vf", vf, "-f", "rawvideo", "-pix_fmt", fmt, "-"]
    pr = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=10 ** 8)
    bpp = 6 if fmt == "rgb48le" else 3
    sz = w * h * bpp
    while True:
        b = pr.stdout.read(sz)
        if len(b) < sz:
            break
        a = np.frombuffer(b, np.uint16 if bpp == 6 else np.uint8).reshape(h, w, 3)
        yield a
    pr.wait()


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def gsmooth1d(x, sigma):
    if sigma <= 0 or len(x) < 2:
        return x
    r = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2); k /= k.sum()
    xp = np.pad(x, (r, r), mode="edge")
    return np.convolve(xp, k, mode="valid")


def disc_kernel(r):
    R = int(np.ceil(r)) + 1
    y, x = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
    d = np.sqrt(x * x + y * y)
    k = np.clip(r + 0.5 - d, 0, 1)
    return k / k.sum()


def poly_mask(points, w, h, feather):
    m = np.zeros((h, w), np.float32)
    pts = np.array([[x * w, y * h] for x, y in points], np.int32)
    cv2.fillPoly(m, [pts], 1.0)
    s = max(1.0, feather * h)
    return cv2.GaussianBlur(m, (0, 0), s)


# ------------------------------------------------------------------ analysis
class Seg:
    def __init__(self):
        import mediapipe as mp
        from mediapipe.tasks.python import vision, BaseOptions
        self.mp = mp
        o = vision.ImageSegmenterOptions(base_options=BaseOptions(model_asset_path=f"{MODELS}/mp/selfie_multiclass_256x256.tflite"),
                                         output_confidence_masks=True, output_category_mask=False)
        self.seg = vision.ImageSegmenter.create_from_options(o)

    def __call__(self, rgb):
        r = self.seg.segment(self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)))
        cm = [np.squeeze(c.numpy_view()).astype(np.float32) for c in r.confidence_masks]
        return 1.0 - cm[0], cm[3]          # person prob, face-skin prob


class Depth:
    MEAN = np.array([0.485, 0.456, 0.406], np.float32); STD = np.array([0.229, 0.224, 0.225], np.float32)

    def __init__(self):
        import onnxruntime as ort
        so = ort.SessionOptions(); so.intra_op_num_threads = NT
        self.s = ort.InferenceSession(f"{MODELS}/dav2/model.onnx", so, providers=["CPUExecutionProvider"])

    def __call__(self, rgb, short=518):
        h, w = rgb.shape[:2]
        iw = int(round(w * short / h / 14.0)) * 14
        x = cv2.resize(rgb, (iw, short), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        x = ((x - self.MEAN) / self.STD).transpose(2, 0, 1)[None]
        d = self.s.run(None, {"pixel_values": x})[0][0]
        return cv2.resize(d, (w, h), interpolation=cv2.INTER_CUBIC)


def analyse(p, force=False):
    os.makedirs(CACHE, exist_ok=True)
    fn = f"{CACHE}/piece{p['i']:02d}.npz"
    if os.path.exists(fn) and not force:
        return dict(np.load(fn))
    t0 = time.time()
    seg = Seg()
    frames, person, face_xy, face_w, skin = [], [], [], [], []
    for f in reader(p, AW, AH):
        pp, fs = seg(f)
        frames.append(f.copy())
        person.append(pp > 0.2)
        m = fs > 0.5
        a = m.sum()
        if a > 40:
            ys, xs = np.nonzero(m)
            face_xy.append((xs.mean() / AW, ys.mean() / AH)); face_w.append(1.0)
            sk = (f[fs > 0.7].astype(np.float32) / 255.0) ** GAMMA
            skin.append(sk.mean(0) if len(sk) > 20 else (np.nan,) * 3)
        else:
            face_xy.append((np.nan, np.nan)); face_w.append(0.0); skin.append((np.nan,) * 3)
    F = np.stack(frames)                                    # n,h,w,3 uint8
    med = np.median(F[::max(1, len(F) // 60)], axis=0).astype(np.uint8)
    # anything that moved (vs the temporal median), at any time in the piece
    medb = cv2.GaussianBlur(med.astype(np.float32), (0, 0), 2)
    moved = np.zeros((AH, AW), bool)
    for f in F:
        d = np.abs(cv2.GaussianBlur(f.astype(np.float32), (0, 0), 2) - medb).max(-1)
        moved |= d > 22
    moved = cv2.morphologyEx(moved.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    pers = np.any(np.stack(person), 0)
    if moved.mean() > 0.6:
        log("piece", p["i"], "motion union too large (global change?) - using person union only")
        moved[:] = False
    occ = pers | moved
    disp = Depth()(cv2.resize(med, (AW * 2, AH * 2), interpolation=cv2.INTER_CUBIC))
    disp = cv2.resize(disp, (AW, AH), interpolation=cv2.INTER_AREA)
    # veiling glare: dark channel of the median frame, large min window, very soft
    lin = (med.astype(np.float32) / 255.0) ** GAMMA
    dc = cv2.erode(lin.min(-1), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
    veil = cv2.GaussianBlur(dc, (0, 0), 25)
    fxy = np.array(face_xy, np.float32); fw = np.array(face_w, np.float32)
    res = dict(occ=occ, pers=pers, moved=moved, disp=disp.astype(np.float32), med=med, veil=veil.astype(np.float32),
               face_xy=fxy, face_w=fw, skin=np.array(skin, np.float32))
    np.savez_compressed(fn, **res)
    log(f"analysed piece {p['i']} ({p['n']} fr) in {time.time() - t0:.0f}s; occ {occ.mean():.2f} moved {moved.mean():.2f}")
    return res


def face_analyse(p, force=False):
    """per-frame face centre + skin colour. MediaPipe FaceLandmarker (Apache-2.0) on an upscaled
    head crop located from the person mask (the full-frame detector misses the small, hazy faces
    of the wide DDN shots)."""
    fn = f"{CACHE}/face{p['i']:02d}.npz"
    if os.path.exists(fn) and not force:
        return dict(np.load(fn))
    import mediapipe as mp
    from mediapipe.tasks.python import vision, BaseOptions
    o = vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=f"{ROOT}/tools/models/face_landmarker.task"),
                                     num_faces=1, min_face_detection_confidence=0.3)
    fl = vision.FaceLandmarker.create_from_options(o)
    seg = Seg()
    FW, FH = 1280, 720
    xy, w, skin = [], [], []
    for f in reader(p, FW, FH):
        pp, fs = seg(cv2.resize(f, (AW, AH), interpolation=cv2.INTER_AREA))
        m = pp > 0.5
        res = None
        if m.sum() > 200:
            ys, xs = np.nonzero(m); top = ys.min()
            bx = np.nonzero(m[top:top + int(0.11 * AH)])[1]
            cx, cy = bx.mean() * FW / AW, (top + 0.07 * AH) * FH / AH
            r = 128
            x0 = int(np.clip(cx - r, 0, FW - 2 * r)); y0 = int(np.clip(cy - r, 0, FH - 2 * r))
            crop = np.ascontiguousarray(cv2.resize(f[y0:y0 + 2 * r, x0:x0 + 2 * r], (512, 512), interpolation=cv2.INTER_CUBIC))
            det = fl.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=crop))
            if det.face_landmarks:
                lm = np.array([[q.x, q.y] for q in det.face_landmarks[0]], np.float32) * 2 * r + [x0, y0]
                res = lm
        if res is None:      # close-ups: the face is bigger than the crop -> full frame
            det = fl.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(f)))
            if det.face_landmarks:
                res = np.array([[q.x, q.y] for q in det.face_landmarks[0]], np.float32) * [FW, FH]
        if res is not None:
            c = res.mean(0)
            xy.append((c[0] / FW, c[1] / FH)); w.append(1.0)
            hull = cv2.convexHull(res.astype(np.int32))
            mk = np.zeros((FH, FW), np.uint8); cv2.fillConvexPoly(mk, hull, 1)
            mk = cv2.erode(mk, np.ones((5, 5), np.uint8))
            px = (f[mk > 0].astype(np.float32) / 255.0) ** GAMMA
            if len(px) > 50:
                yv = px @ np.array([0.2126, 0.7152, 0.0722], np.float32)
                lo, hi = np.percentile(yv, [25, 85])
                sel = px[(yv >= lo) & (yv <= hi)]
                skin.append(sel.mean(0))
            else:
                skin.append((np.nan,) * 3)
        else:
            xy.append((np.nan, np.nan)); w.append(0.0); skin.append((np.nan,) * 3)
    out = dict(face_xy=np.array(xy, np.float32), face_w=np.array(w, np.float32), skin=np.array(skin, np.float32))
    np.savez_compressed(fn, **out)
    log(f"faces piece {p['i']}: found in {np.mean(w) * 100:.0f}% of frames")
    return out


def load(p):
    A = analyse(p)
    A.update(face_analyse(p))
    return A


# ------------------------------------------------------------- static maps
def blur_weight(p, A):
    """static blur weight b in [0,1] at analysis res + its parts (for QA)."""
    occ = A["occ"].astype(np.uint8)
    disp = A["disp"]
    # focus plane = the speaker's depth (near); far = the far wall
    dfocus = np.percentile(disp[A["pers"]], 50) if A["pers"].any() else np.percentile(disp, 90)
    dfar = np.percentile(disp, 1.5)
    start = dfar + 0.65 * (dfocus - dfar)                 # everything nearer than this stays sharp
    bd = np.clip((start - disp) / max(1e-6, start - dfar), 0, 1) ** FALLOFF_EXP
    bd = cv2.GaussianBlur(bd, (0, 0), 3)
    # distance (in fractions of H) from anything the speaker occupies at any time
    dist = cv2.distanceTransform((1 - occ).astype(np.uint8), cv2.DIST_L2, 5) / AH
    prot = smoothstep(DIL, DIL + FEATH, dist)
    prot[dist < DIL] = 0.0
    keep = np.ones((AH, AW), np.float32)
    kf = f"{KEEP}/{p['clip']}.json"
    if os.path.exists(kf):
        for r in json.load(open(kf)).get("regions", []):
            m = poly_mask(r["points"], AW, AH, r.get("feather", 0.015) * 2)
            keep *= 1 - m * (1 - r.get("strength", 0.0))
    b = bd * keep * prot
    b[dist < DIL] = 0.0
    return b.astype(np.float32), dict(bd=bd, prot=prot, keep=keep, dist=dist, dfocus=dfocus, dfar=dfar)


def skin_targets(P):
    """per-piece multiplicative linear gains that pull skin into one range."""
    stats = []
    for p in P:
        A = load(p)
        s = A["skin"]; s = s[~np.isnan(s).any(1)]
        stats.append(np.median(s, 0) if len(s) else np.array([np.nan] * 3))
    S = np.array(stats)
    Y = S @ np.array([0.2126, 0.7152, 0.0722])
    rg, bg = S[:, 0] / S[:, 1], S[:, 2] / S[:, 1]
    ok = ~np.isnan(Y)
    tY, trg, tbg = np.median(Y[ok]), np.median(rg[ok]), np.median(bg[ok])
    gains = np.ones((len(P), 3), np.float32); keyx = np.zeros(len(P), np.float32)
    for k in range(len(P)):
        if not ok[k]:
            continue
        ev = np.clip(SKIN_NUDGE * np.log2(tY / Y[k]), -SKIN_MAX_STOP, SKIN_MAX_STOP)
        gr = np.clip((trg / rg[k]) ** SKIN_NUDGE, 1 - SKIN_MAX_WB, 1 + SKIN_MAX_WB)
        gb = np.clip((tbg / bg[k]) ** SKIN_NUDGE, 1 - SKIN_MAX_WB, 1 + SKIN_MAX_WB)
        g = np.array([gr, 1.0, gb]); g /= (g @ np.array([0.2126, 0.7152, 0.0722]))   # WB without exposure change
        gains[k] = g * 2 ** (0.5 * ev)
        keyx[k] = 0.5 * ev
    return gains, keyx, dict(Y=Y, rg=rg, bg=bg, tY=tY, trg=trg, tbg=tbg)


def face_track(A, n):
    xy = A["face_xy"].copy(); w = A["face_w"].copy()
    if w.sum() == 0:
        return np.full((n, 2), 0.5, np.float32), np.zeros(n, np.float32)
    idx = np.arange(n)
    for c in range(2):
        good = ~np.isnan(xy[:, c])
        xy[:, c] = np.interp(idx, idx[good], xy[good, c])
    # robust: kill single-frame jumps, then heavy zero-phase smoothing
    from scipy.ndimage import median_filter
    sig = KEY_SMOOTH_S * FPS
    for c in range(2):
        xy[:, c] = gsmooth1d(median_filter(xy[:, c], 9, mode="nearest"), sig)
    amp = np.clip(gsmooth1d(median_filter(w, 15, mode="nearest"), sig), 0, 1)
    return xy.astype(np.float32), amp.astype(np.float32)


# ------------------------------------------------------------------ render
def render(p, A, gain, keyx, out, do_blur=True, do_light=True, qa_frames=(), qa_dir=None, log_every=60, max_frames=0):
    i = p["i"]
    b_small, parts = blur_weight(p, A)
    b = cv2.resize(b_small, (W, H), interpolation=cv2.INTER_LINEAR)
    b[cv2.resize((parts["dist"] < DIL).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0] = 0.0
    if not do_blur:
        b[:] = 0
    active = b > 1e-3
    zone = cv2.resize((parts["dist"] < DIL).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    bg8 = cv2.resize(b_small, (W // 8, H // 8), interpolation=cv2.INTER_AREA) > 0.3     # blurred background
    contrast = CONTRAST.get(i, 1.0)
    # blur layers at half resolution: radii 0, r1, r2, r3 ; per-pixel weights from b
    hw, hh = W // 2, H // 2
    R = RMAX * H / 2.0
    radii = [R / 3, 2 * R / 3, R]
    kers = [disc_kernel(r) for r in radii]
    bh = b * 3.0                                    # position in layer space 0..3
    wts = []
    for k in range(4):
        wts.append(np.clip(1 - np.abs(bh - k), 0, 1).astype(np.float32))
    ys, xs = np.nonzero(active.any(1))[0], np.nonzero(active.any(0))[0]
    roi = (ys.min(), ys.max() + 1, xs.min(), xs.max() + 1) if active.any() else None
    # grain sigma: measured temporal noise in the static background, in display units
    noise = A.get("noise", None)
    # lighting static maps
    yy, xx = np.mgrid[0:H // 8, 0:W // 8].astype(np.float32)
    xx /= (W // 8); yy /= (H // 8)
    r2 = ((xx - 0.5) / 0.5) ** 2 * 0.6 + ((yy - 0.5) / 0.5) ** 2 * 0.4
    vig = 1 - VIGNETTE * smoothstep(0.25, 1.0, r2)
    # veiling glare / milky blacks: a uniform additive lift (estimated as the black level of the median
    # frame); a spatial dark-channel estimate confuses the white walls with glare, so stay global.
    linm = (A["med"].astype(np.float32) / 255.0) ** GAMMA
    veil = float(VEIL_K.get(i, 0.0) * np.percentile(linm @ np.array([0.2126, 0.7152, 0.0722], np.float32), 0.5))
    fxy, famp = face_track(A, p["n"])
    key_a = 2 ** (KEY_STOP + keyx) - 1
    tint = np.array([1.0, 0.80, 0.62], np.float32)
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", "30", "-i", "-", "-vf", "format=yuv420p,setsar=1",
                            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
                            "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-threads", "2", out], stdin=subprocess.PIPE)
    rng = np.random.default_rng(1234 + i)
    flick = []
    prev_in = prev_out = None
    t0 = time.time(); n = 0
    for fi, f16 in enumerate(reader(p, W, H, "rgb48le")):
        if max_frames and fi >= max_frames:
            break
        L = LIN16[f16]                                        # linear float32
        L0 = L
        if roi is not None:
            y0, y1, x0, x1 = roi
            sub = L[y0:y1, x0:x1]
            sh = cv2.resize(sub, ((x1 - x0) // 2, (y1 - y0) // 2), interpolation=cv2.INTER_AREA)
            acc = sub * wts[0][y0:y1, x0:x1, None]
            for k, ker in enumerate(kers):
                wk = wts[k + 1][y0:y1, x0:x1]
                if wk.max() <= 0:
                    continue
                bl = cv2.resize(cv2.filter2D(sh, -1, ker, borderType=cv2.BORDER_REFLECT), (x1 - x0, y1 - y0),
                                interpolation=cv2.INTER_LINEAR)
                acc += bl * wk[..., None]
            # grain re-add (blur removed the sensor noise): luma grain ~ sigma in display units
            g = rng.standard_normal(((y1 - y0) // 2 + 1, (x1 - x0) // 2 + 1)).astype(np.float32)
            g = cv2.resize(g, (x1 - x0, y1 - y0), interpolation=cv2.INTER_LINEAR)
            bs = b[y0:y1, x0:x1]
            # display-domain sigma -> linear: dL = gamma * L^(1-1/gamma) * dD
            sig = (A["noise"] if "noise" in A else 0.006) * 1.6
            acc += (g * bs * sig)[..., None] * (GAMMA * np.maximum(acc, 1e-4) ** (1 - 1 / GAMMA))
            L = L.copy()
            L[y0:y1, x0:x1] = np.where(active[y0:y1, x0:x1, None], np.maximum(acc, 0), sub)
        pre = L

        def light(L):
            if not do_light:
                return L
            L = L * gain[None, None, :]
            if veil > 0:
                # soft subtraction: L - V above 2V, quadratic toe below (continuous, slope-matched, never < 0)
                L = np.where(L > 2 * veil, L - veil, L * L / (4 * veil)) / (1 - veil)
            if contrast != 1.0:
                L = 0.18 * np.power(L / 0.18, contrast, dtype=np.float32)
            L = L * m[..., None]
            L = L + hal                                 # halation from the un-blurred frame (pixelwise add)
            # highlight soft knee on the max channel (hue preserving)
            mx = L.max(-1)
            t = np.clip((mx - KNEE) / (KMAX - KNEE), 0, 1)
            f = np.where(mx > KNEE, KNEE + (1 - KNEE) * (1 - (1 - t) ** 2), mx)
            return L * (f / np.maximum(mx, 1e-6))[..., None]

        if do_light:
            cx, cy = fxy[min(fi, len(fxy) - 1)]
            am = famp[min(fi, len(famp) - 1)]
            key = 1 + key_a * am * np.exp(-0.5 * (((xx - cx) / KEY_SX) ** 2 + ((yy - cy) / KEY_SY) ** 2))
            m = cv2.resize((key * vig).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
            # halation: near-clipping parts bloom softly, warm tint; computed from the ORIGINAL frame so
            # the background blur cannot leak into the protected zone through it
            q = cv2.resize(L0, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
            hb = cv2.GaussianBlur(np.maximum(q - HAL_THR, 0), (0, 0), H / 8 * 0.012)
            hb = cv2.GaussianBlur(hb, (0, 0), H / 8 * 0.02)
            hal = HALATION * cv2.resize(hb, (W, H), interpolation=cv2.INTER_LINEAR) * tint
        L = light(L)
        o8 = encode(L)
        enc.stdin.write(o8.tobytes())
        zdiff = -1.0
        if qa_dir:
            # proof: same frame rendered WITHOUT the background blur; must be bit-identical in the zone
            ref = encode(light(L0))
            zdiff = float(np.abs(ref[zone].astype(np.int16) - o8[zone]).max())
            if fi in qa_frames:
                os.makedirs(qa_dir, exist_ok=True)
                cv2.imwrite(f"{qa_dir}/p{i:02d}_f{fi:03d}_look.png", cv2.cvtColor(o8, cv2.COLOR_RGB2BGR))
                cv2.imwrite(f"{qa_dir}/p{i:02d}_f{fi:03d}_noblurlook.png", cv2.cvtColor(ref, cv2.COLOR_RGB2BGR))
        # flicker scan at 1/8 res: temporal change of output vs input (background region)
        si = cv2.resize(f16, (W // 8, H // 8), interpolation=cv2.INTER_AREA).astype(np.float32) / 257
        so = cv2.resize(o8, (W // 8, H // 8), interpolation=cv2.INTER_AREA).astype(np.float32)
        if prev_in is not None:
            flick.append((np.abs(si - prev_in).mean(), np.abs(so - prev_out).mean(), so.mean() - si.mean(), zdiff,
                          np.abs(so - prev_out)[bg8].mean() - np.abs(si - prev_in)[bg8].mean()))
        prev_in, prev_out = si, so
        n += 1
        if n % log_every == 0:
            log(f"piece {i}: {n}/{p['n']} {n / (time.time() - t0):.2f} fps")
    enc.stdin.close(); enc.wait()
    if n != p["n"] and not max_frames:
        raise RuntimeError(f"piece {i}: got {n} frames, expected {p['n']}")
    log(f"piece {i} done {n} frames in {time.time() - t0:.0f}s")
    return np.array(flick, np.float32), b_small, parts


def add_noise_estimate(p, A):
    """temporal noise (display units, 0..1) in the static far background from 2 adjacent graded frames."""
    if "noise" in A:
        return A
    fr = []
    for k, f in enumerate(reader(dict(p, n=3), W // 2, H // 2)):
        fr.append(f.astype(np.float32) / 255.0)
    d = (fr[2] - fr[1]).mean(-1)
    occ = cv2.resize(A["occ"].astype(np.uint8), (W // 2, H // 2), interpolation=cv2.INTER_NEAREST) == 0
    v = d[occ]
    A["noise"] = float(1.4826 * np.median(np.abs(v - np.median(v))) / np.sqrt(2)) * 2.0   # *2: half-res averaging
    return A


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--out", default=f"{ROOT}/edit/plates_look_v4")
    ap.add_argument("--no-blur", action="store_true")
    ap.add_argument("--no-light", action="store_true")
    ap.add_argument("--analyse-only", action="store_true")
    ap.add_argument("--qa-frames", default="")
    ap.add_argument("--qa-dir", default=None)
    ap.add_argument("--concat", action="store_true")
    ap.add_argument("--suffix", default="")
    ap.add_argument("--max-frames", type=int, default=0)
    a = ap.parse_args()
    P = pieces()
    os.makedirs(a.out, exist_ok=True)
    only = [int(x) for x in a.only.split(",")] if a.only else list(range(len(P)))
    if not a.concat:
        for k in only:
            load(P[k])
        if a.analyse_only:
            return
        gains, keyx, _ = skin_targets(P)
        qa = set(int(x) for x in a.qa_frames.split(",") if x)
        for k in only:
            A = add_noise_estimate(P[k], load(P[k]))
            fl, bs, parts = render(P[k], A, gains[k], keyx[k], f"{a.out}/seg{k:02d}{a.suffix}.mp4", not a.no_blur, not a.no_light,
                                   qa, a.qa_dir, max_frames=a.max_frames)
            np.savez_compressed(f"{CACHE}/render{k:02d}{a.suffix}.npz", flick=fl, b=bs, prot=parts["prot"],
                                bd=parts["bd"], keep=parts["keep"], gain=gains[k], keyx=keyx[k], noise=A["noise"])
    if a.concat or a.only is None:
        with open(f"{a.out}/list.txt", "w") as f:
            for k in range(len(P)):
                f.write(f"file '{a.out}/seg{k:02d}.mp4'\n")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{a.out}/list.txt",
                        "-c", "copy", f"{a.out}/plate.mp4"], check=True)
        log("plate ->", f"{a.out}/plate.mp4")


if __name__ == "__main__":
    main()
    os._exit(0)
