#!/usr/bin/env python3
"""bgblur.py - lens-like shallow depth-of-field background blur for static-tripod
talking-head clips (CPU only).

Pipeline (per clip, cached):  clean plate (masked temporal median of ~40 frames)
  + Depth Anything V2 Small disparity of the plate (static depth map)
  + default focus = speaker's disparity.
Per frame:  RVM (Robust Video Matting, recurrent) person matte -> temporal
  stabilisation -> person region filled with the (exposure-matched) clean plate
  -> depth-graded, layered, normalised disc ("bokeh") blur in ~linear light with
  highlight boost -> grain matched to the source re-added in blurred areas
  -> speaker composited back with RVM foreground colours on the soft edge.
  Focus follows the speaker (Depth Anything on the current frame every N frames).

Example:
  bgblur.py --in footage/raw/IMG_3856.MOV --out out.mp4 --start 10 --end 16 \
      --size 1920x1080 --strength 1.0 --keep-polygon keep.json
  # 4K source punch-in (crop in source pixels) rendered to 1080p:
  bgblur.py --in ... --crop 384,216,3072,1728 --size 1920x1080

keep-polygon JSON (coordinates normalised 0..1 of the FULL source frame):
  {"regions": [
     {"name": "sign chair", "points": [[0.62,0.45],[0.80,0.45],[0.80,0.95],[0.62,0.95]],
      "strength": 0.0, "feather": 0.01},
     {"name": "monitor", "points": [...], "strength": 0.4}
  ]}
  strength multiplies the blur radius inside the polygon (0 = keep sharp,
  0.4 = light blur, 1 = no change, >1 = more).

Licences: RVM weights/code are GPL-3.0 (used here as an internal tool, model
file only, not redistributed in a product); Depth Anything V2 Small is
Apache-2.0; everything else here is our own code.
"""
import argparse, json, os, subprocess, sys, time, hashlib
import numpy as np
import cv2
import onnxruntime as ort

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "models")
CACHE = os.path.join(HERE, "cache")
RVM_PATH = os.path.join(MODELS, "rvm", "rvm_mobilenetv3_fp32.onnx")
DA_PATH = os.path.join(MODELS, "dav2", "model.onnx")
MP_PATH = os.path.join(MODELS, "mp", "selfie_multiclass_256x256.tflite")
PLATE_W, PLATE_H = 1920, 1080
CACHE_V = 2                            # bump to invalidate old clip caches          # cache resolution (full frame)
NTHREADS = int(os.environ.get("BGBLUR_THREADS", "2"))
cv2.setNumThreads(NTHREADS)


def log(*a):
    print("[bgblur]", *a, file=sys.stderr, flush=True)


# ----------------------------------------------------------------------------- io
def probe(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=width,height,r_frame_rate:format=duration", "-of", "json", path])
    j = json.loads(out)
    s = j["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    has_audio = bool(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
        "stream=index", "-of", "csv=p=0", path]).strip())
    return dict(w=int(s["width"]), h=int(s["height"]), fps=float(num) / float(den),
                dur=float(j["format"]["duration"]), audio=has_audio)


def vf_chain(crop, W, H):
    f = []
    if crop:
        x, y, w, h = crop
        f.append(f"crop={w}:{h}:{x}:{y}")
    f.append(f"scale={W}:{H}:flags=lanczos:in_color_matrix=bt709:in_range=tv")
    f.append("format=rgb24")
    return ",".join(f)


class Reader:
    def __init__(self, path, start, dur, crop, W, H, fps=None):
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{start:.4f}", "-i", path]
        if dur is not None:
            cmd += ["-t", f"{dur:.4f}"]
        vf = vf_chain(crop, W, H)
        if fps:
            vf = f"fps={fps}," + vf
        cmd += ["-an", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.W, self.H = W, H
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=W * H * 3 * 2)

    def read(self):
        n = self.W * self.H * 3
        b = self.p.stdout.read(n)
        if len(b) < n:
            return None
        return np.frombuffer(b, np.uint8).reshape(self.H, self.W, 3)

    def close(self):
        try:
            self.p.stdout.close()
            self.p.kill()
        except Exception:
            pass


def grab(path, t, crop, W, H):
    r = Reader(path, t, None, crop, W, H)
    f = r.read()
    r.close()
    return f


class Writer:
    def __init__(self, out, W, H, fps, src=None, start=0, dur=None, crf=16, preset="medium"):
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{W}x{H}", "-r", f"{fps:.6f}", "-i", "-"]
        if src is not None:
            cmd += ["-ss", f"{start:.4f}"] + (["-t", f"{dur:.4f}"] if dur else []) + ["-i", src,
                    "-map", "0:v", "-map", "1:a?", "-c:a", "aac", "-b:a", "192k", "-shortest"]
        cmd += ["-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                "-color_range", "tv", "-movflags", "+faststart", out]
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def write(self, rgb):
        self.p.stdin.write(np.ascontiguousarray(rgb).tobytes())

    def close(self):
        self.p.stdin.close()
        self.p.wait()


# ------------------------------------------------------------------------- models
def _sess(path):
    so = ort.SessionOptions()
    so.intra_op_num_threads = NTHREADS
    so.inter_op_num_threads = 1
    return ort.InferenceSession(path, so, providers=["CPUExecutionProvider"])


class Matter:
    """Robust Video Matting (mobilenetv3) with recurrent state."""

    def __init__(self, internal_short=288):
        self.s = _sess(RVM_PATH)
        self.internal_short = internal_short
        self.reset()

    def reset(self):
        z = np.zeros((1, 1, 1, 1), np.float32)
        self.rec = [z, z, z, z]

    def step(self, rgb):
        h, w = rgb.shape[:2]
        ratio = np.array([min(1.0, self.internal_short / min(h, w))], np.float32)
        x = rgb.transpose(2, 0, 1)[None].astype(np.float32) * (1 / 255.0)
        fgr, pha, *self.rec = self.s.run(None, {
            "src": x, "r1i": self.rec[0], "r2i": self.rec[1], "r3i": self.rec[2],
            "r4i": self.rec[3], "downsample_ratio": ratio})
        return pha[0, 0], fgr[0].transpose(1, 2, 0)


class Segmenter:
    """MediaPipe selfie-multiclass (Apache-2.0): coarse but solid body/clothes mask.
    Used only as an eroded *core* so dark trousers on a dark floor never go
    semi-transparent; edges (hair, fingers) come from RVM."""

    def __init__(self):
        import mediapipe as mp
        from mediapipe.tasks.python import vision, BaseOptions
        self.mp = mp
        o = vision.ImageSegmenterOptions(
            base_options=BaseOptions(model_asset_path=MP_PATH),
            output_confidence_masks=True, output_category_mask=False)
        self.seg = vision.ImageSegmenter.create_from_options(o)

    def __call__(self, rgb):
        r = self.seg.segment(self.mp.Image(image_format=self.mp.ImageFormat.SRGB,
                                           data=np.ascontiguousarray(rgb)))
        return 1.0 - r.confidence_masks[0].numpy_view()[..., 0].astype(np.float32)


def body_core(p, H):
    """solid inner region from the coarse person probability."""
    e = max(3, int(H / 90)) | 1
    m = (p > 0.75).astype(np.uint8)
    m = cv2.erode(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (e, e)))
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), e / 3)


class Depth:
    """Depth Anything V2 Small -> relative disparity (bigger = nearer)."""
    MEAN = np.array([0.485, 0.456, 0.406], np.float32)
    STD = np.array([0.229, 0.224, 0.225], np.float32)

    def __init__(self, short=518):
        self.s = _sess(DA_PATH)
        self.short = short

    def __call__(self, rgb):
        h, w = rgb.shape[:2]
        ih = self.short
        iw = int(round(w * ih / h / 14.0)) * 14
        x = cv2.resize(rgb, (iw, ih), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        x = ((x - self.MEAN) / self.STD).transpose(2, 0, 1)[None]
        d = self.s.run(None, {"pixel_values": x})[0][0]
        return cv2.resize(d, (w, h), interpolation=cv2.INTER_CUBIC)


# ------------------------------------------------------------------------ helpers
def push_pull(img, w, levels=6):
    """fill pixels with low weight w from their surroundings (pyramid
    normalised convolution) - smooth, no streaks."""
    pyr = []
    num, den = img * w[..., None], w.copy()
    for _ in range(levels):
        pyr.append((num, den))
        num, den = cv2.pyrDown(num), cv2.pyrDown(den)
    out = num / np.maximum(den, 1e-5)[..., None]
    for num, den in reversed(pyr):
        up = cv2.resize(out, (num.shape[1], num.shape[0]), interpolation=cv2.INTER_LINEAR)
        k = np.clip(den * 4, 0, 1)[..., None]
        out = (num / np.maximum(den, 1e-5)[..., None]) * k + up * (1 - k)
    return out


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def disc_kernel(r):
    """Anti-aliased disc (bokeh) kernel of radius r (px), normalised."""
    R = int(np.ceil(r)) + 1
    y, x = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
    d = np.sqrt(x * x + y * y)
    k = np.clip(r + 0.5 - d, 0, 1)
    # very slight brighter rim, like many real lenses (onion-free, subtle)
    k *= 1.0 + 0.12 * smoothstep(r * 0.6, r, d)
    return k / k.sum()


def affine_fit(src, dst, mask, n=40000):
    idx = np.flatnonzero(mask.ravel())
    if idx.size < 500:
        return 1.0, 0.0
    if idx.size > n:
        idx = np.random.default_rng(0).choice(idx, n, replace=False)
    s, d = src.ravel()[idx], dst.ravel()[idx]
    A = np.stack([s, np.ones_like(s)], 1)
    # two rounds of trimmed least squares for robustness
    keep = np.ones_like(s, bool)
    for _ in range(3):
        a, b = np.linalg.lstsq(A[keep], d[keep], rcond=None)[0]
        res = np.abs(a * s + b - d)
        keep = res < np.percentile(res, 80)
    return float(a), float(b)


def temporal_noise(src, t, mask=None):
    """sensor/codec noise std (0..255, 1080p luma) from consecutive frames of
    the static camera (trimmed std of frame differences; duplicated frames,
    which iPhone files contain, are skipped)."""
    r = Reader(src, t, 0.3, None, PLATE_W, PLATE_H)
    fr = []
    for _ in range(6):
        f = r.read()
        if f is None:
            break
        fr.append(cv2.cvtColor(f, cv2.COLOR_RGB2GRAY).astype(np.float32))
    r.close()
    est = []
    for x, y in zip(fr[:-1], fr[1:]):
        d = x - y
        if mask is not None:
            d = d[~mask]
        d = d[np.abs(d) < 12]
        sd = float(d.std() / np.sqrt(2))
        if sd > 0.05:
            est.append(sd)
    return float(np.median(est)) if est else 1.0


def noise_sigma(rgb):
    """Immerkaer noise estimate on luma (in 0..255 units), robust to texture."""
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    k = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], np.float32)
    r = np.abs(cv2.filter2D(g, -1, k))
    # use only low-texture pixels
    lap = cv2.Laplacian(cv2.GaussianBlur(g, (0, 0), 2), cv2.CV_32F)
    flat = np.abs(lap) < np.percentile(np.abs(lap), 40)
    return float(np.sqrt(np.pi / 2) * np.mean(r[flat]) / 6.0)


# -------------------------------------------------------------------- clip cache
def build_cache(src, info, nsamples=40, t0=None, t1=None, force=False):
    name = os.path.splitext(os.path.basename(src))[0]
    t0 = 0.0 if t0 is None else max(0.0, t0)
    t1 = info["dur"] - 0.2 if t1 is None else min(info["dur"] - 0.2, t1)
    key = f"{name}_{int(t0)}_{int(t1)}"
    d = os.path.join(CACHE, key)
    meta_p = os.path.join(d, "meta.json")
    if os.path.exists(meta_p) and not force and json.load(open(meta_p)).get("cache_v") == CACHE_V:
        meta = json.load(open(meta_p))
        if "noise_v4" not in meta:
            meta["noise_sigma"] = temporal_noise(src, 0.5 * (meta["t0"] + meta["t1"]))
            meta["noise_v4"] = True
            json.dump(meta, open(meta_p, "w"), indent=1)
        plate = cv2.cvtColor(cv2.imread(os.path.join(d, "plate.png")), cv2.COLOR_BGR2RGB)
        disp = np.load(os.path.join(d, "disp.npy")).astype(np.float32)
        cp = os.path.join(d, "plate_conf.png")
        meta["conf"] = cv2.imread(cp, 0).astype(np.float32) / 255 if os.path.exists(cp) else None
        return plate, disp, meta
    os.makedirs(d, exist_ok=True)
    log(f"building clip cache {key}: {nsamples} samples")
    tic = time.time()
    matter = Matter(internal_short=320)
    segm = Segmenter()
    ts = np.linspace(t0 + 0.1, t1, nsamples)
    frames, masks, alphas = [], [], []
    # the 1080p proxy (same framing) decodes ~4x faster than the 4K original
    proxy = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(src))), "proxy", name + ".mp4")
    gsrc = src
    if os.path.exists(proxy):
        try:
            pi = probe(proxy)
            if abs(pi["dur"] - info["dur"]) < 0.5 and pi["w"] * info["h"] == pi["h"] * info["w"]:
                gsrc = proxy
        except Exception:
            pass
    for t in ts:
        f = grab(gsrc, float(t), None, PLATE_W, PLATE_H)
        if f is None:
            continue
        matter.reset()
        for _ in range(3):  # let the recurrent state converge on the still frame
            a, _ = matter.step(f)
        pm = segm(f)
        a = np.maximum(a, body_core(pm, PLATE_H))
        m = ((a > 0.02) | (pm > 0.3)).astype(np.uint8)
        m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)))
        frames.append(f)
        masks.append(m.astype(bool))
        alphas.append(a)
    F = np.stack(frames)          # N,H,W,3 uint8
    M = np.stack(masks)           # N,H,W bool (True = person)
    plate = np.zeros((PLATE_H, PLATE_W, 3), np.uint8)
    cnt = (~M).sum(0)
    var = np.zeros((PLATE_H, PLATE_W), np.float32)   # per-pixel temporal MAD (moving props)
    for y0 in range(0, PLATE_H, 90):
        blk = F[:, y0:y0 + 90].astype(np.float32)
        blk[M[:, y0:y0 + 90]] = np.nan
        with np.errstate(all="ignore"):
            med = np.nanmedian(blk, axis=0)
        plate[y0:y0 + 90] = np.nan_to_num(med, nan=0).clip(0, 255).astype(np.uint8)
        with np.errstate(all="ignore"):
            mad = np.nanmedian(np.abs(blk - med[None]).mean(-1), axis=0)
        var[y0:y0 + 90] = np.nan_to_num(mad, nan=255)
    hole = (cnt < max(3, int(0.15 * len(F)))).astype(np.uint8)
    if hole.any():
        s = 4
        small = cv2.resize(plate, (PLATE_W // s, PLATE_H // s), interpolation=cv2.INTER_AREA)
        hs = cv2.resize(hole, (PLATE_W // s, PLATE_H // s), interpolation=cv2.INTER_NEAREST)
        hs = cv2.dilate(hs, np.ones((3, 3), np.uint8))
        inp = cv2.inpaint(cv2.cvtColor(small, cv2.COLOR_RGB2BGR), hs, 9, cv2.INPAINT_TELEA)
        inp = cv2.cvtColor(cv2.resize(inp, (PLATE_W, PLATE_H), interpolation=cv2.INTER_CUBIC), cv2.COLOR_BGR2RGB)
        hb = cv2.GaussianBlur(cv2.dilate(hole, np.ones((9, 9), np.uint8)).astype(np.float32), (0, 0), 4)[..., None]
        plate = (plate * (1 - hb) + inp * hb).clip(0, 255).astype(np.uint8)
    log(f"plate done ({hole.mean()*100:.1f}% inpainted) {time.time()-tic:.0f}s")

    depth = Depth(short=518)
    disp_p = depth(plate)
    # Robust static depth: median of per-sample depth maps (each aligned to the
    # plate's depth scale) over the samples where that pixel is not the person.
    # Avoids Depth Anything hallucinating on the plate's ghosted/inpainted areas.
    dsz = (960, 540)
    ref = cv2.resize(disp_p, dsz, interpolation=cv2.INTER_AREA)
    stack = []
    for i in range(0, len(F), 2):
        di = cv2.resize(depth(F[i]), dsz, interpolation=cv2.INTER_AREA)
        mi = cv2.resize(M[i].astype(np.uint8), dsz, interpolation=cv2.INTER_NEAREST).astype(bool)
        a_, b_ = affine_fit(di, ref, ~mi)
        if a_ <= 0:
            continue
        di = a_ * di + b_
        di[mi] = np.nan
        stack.append(di)
    if stack:
        with np.errstate(all="ignore"):
            med = np.nanmedian(np.stack(stack), axis=0)
        holes = ~np.isfinite(med)
        med[holes] = ref[holes]
        hb = cv2.GaussianBlur(cv2.dilate(holes.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(np.float32), (0, 0), 3)
        med = med * (1 - hb) + ref * hb
        disp_p = cv2.resize(med.astype(np.float32), (PLATE_W, PLATE_H), interpolation=cv2.INTER_CUBIC)
    # default focus: sample frame with a decent-size speaker
    area = M.mean((1, 2))
    focus = None
    cand = [i for i in np.argsort(-area) if 0.02 < area[i] < 0.25]
    vals = []
    for i in cand[:3]:
        df = depth(F[i])
        a, b = affine_fit(df, disp_p, ~M[i])
        core = cv2.erode((alphas[i] > 0.9).astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
        if core.sum() > 500:
            vals.append(a * float(np.median(df[core])) + b)
    lo, hi = np.percentile(disp_p, 1), np.percentile(disp_p, 99.5)
    if vals:
        focus = float(np.clip(np.median(vals), lo + 0.1 * (hi - lo), lo + 0.95 * (hi - lo)))
    else:
        focus = float(np.percentile(disp_p, 90))
    quiet = int(np.argmin(area))
    sig = temporal_noise(src, float(ts[quiet]), M[quiet])
    meta = dict(key=key, src=os.path.abspath(src), t0=t0, t1=t1, n=len(F),
                inpainted_frac=float(hole.mean()), d_far=float(lo), d_near=float(hi),
                focus=focus, noise_sigma=sig, noise_v4=True, cache_v=CACHE_V, build_s=time.time() - tic)
    cv2.imwrite(os.path.join(d, "plate.png"), cv2.cvtColor(plate, cv2.COLOR_RGB2BGR))
    conf = smoothstep(0.12, 0.35, cnt.astype(np.float32) / max(1, len(F)))
    # things that move between samples (the swivel chair) make the plate a
    # ghosted mix there: don't trust it
    conf = conf * (1 - smoothstep(8.0, 20.0, cv2.GaussianBlur(var, (0, 0), 3)))
    conf = cv2.GaussianBlur(cv2.erode(conf, np.ones((15, 15), np.uint8)), (0, 0), 6)
    cv2.imwrite(os.path.join(d, "plate_conf.png"), cv2.resize((conf * 255).astype(np.uint8), (960, 540), interpolation=cv2.INTER_AREA))
    np.save(os.path.join(d, "disp.npy"), cv2.resize(disp_p, (960, 540), interpolation=cv2.INTER_AREA).astype(np.float16))
    # small preview of depth for humans
    dn = ((disp_p - lo) / (hi - lo)).clip(0, 1)
    cv2.imwrite(os.path.join(d, "depth_preview.jpg"),
                cv2.applyColorMap((cv2.resize(dn, (960, 540)) * 255).astype(np.uint8), cv2.COLORMAP_INFERNO))
    json.dump(meta, open(meta_p, "w"), indent=1)
    meta["conf"] = cv2.resize(conf, (960, 540), interpolation=cv2.INTER_AREA)
    log(f"cache built in {time.time()-tic:.0f}s focus={focus:.3f} far={lo:.3f} near={hi:.3f} noise={sig:.2f}")
    return plate, cv2.resize(disp_p, (960, 540), interpolation=cv2.INTER_AREA), meta


# ------------------------------------------------------------------------ render
class Renderer:
    def __init__(self, plate, disp, meta, W, H, crop, src_wh, args):
        self.W, self.H, self.args = W, H, args
        sw, sh = src_wh
        cx, cy, cw, ch = crop if crop else (0, 0, sw, sh)
        self.crop_n = (cx / sw, cy / sh, cw / sw, ch / sh)

        def crop_resize(img, interp):
            h, w = img.shape[:2]
            x0, y0 = int(round(cx / sw * w)), int(round(cy / sh * h))
            x1, y1 = int(round((cx + cw) / sw * w)), int(round((cy + ch) / sh * h))
            return cv2.resize(img[y0:y1, x0:x1], (W, H), interpolation=interp)

        self.plate = crop_resize(plate, cv2.INTER_CUBIC)
        self.plate_f = self.plate.astype(np.float32)
        c = meta.get("conf")
        self.conf = crop_resize(c, cv2.INTER_LINEAR)[..., None].astype(np.float32) if c is not None else None
        self.plate_s = cv2.resize(self.plate, (W // 16, H // 16), interpolation=cv2.INTER_AREA).astype(np.float32)
        d = crop_resize(disp.astype(np.float32), cv2.INTER_CUBIC)
        # edge-aware refinement of the depth map with the plate as guide
        g = cv2.cvtColor(self.plate, cv2.COLOR_RGB2GRAY)
        rad = max(4, int(H / 135))
        self.disp = cv2.ximgproc.guidedFilter(g, d, rad, (0.02 * (meta["d_near"] - meta["d_far"])) ** 2)
        self.d_far, self.d_near = meta["d_far"], meta["d_near"]
        self.dn = ((self.disp - self.d_far) / (self.d_near - self.d_far)).astype(np.float32)
        self.focus_n = (meta["focus"] - self.d_far) / (self.d_near - self.d_far)
        self.focus_n = float(np.clip(self.focus_n, 0.1, 0.95))
        if args.focus is not None:
            self.focus_n = args.focus
        self.focus_cur = self.focus_n
        # per-region strength multiplier
        self.mult = np.ones((H, W), np.float32)
        if args.keep_polygon:
            regs = json.load(open(args.keep_polygon))
            regs = regs.get("regions", regs) if isinstance(regs, dict) else regs
            for r in regs:
                pts = np.array(r["points"], np.float32)
                px = (pts[:, 0] - self.crop_n[0]) / self.crop_n[2] * W
                py = (pts[:, 1] - self.crop_n[1]) / self.crop_n[3] * H
                m = np.zeros((H, W), np.uint8)
                cv2.fillPoly(m, [np.stack([px, py], 1).round().astype(np.int32)], 1)
                fe = max(1.0, r.get("feather", 0.01) * H)
                m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), fe)
                self.mult = self.mult * (1 - m) + float(r.get("strength", 0.0)) * self.mult * m
        self.R = args.strength * 0.0125 * H        # max blur radius (px) at full depth
        rr = [0.0, 1.0, 2.0, 3.5, 5.5, 8.0, 11.5, 16.0, 22.0, 30.0, 40.0, 54.0, 72.0]
        top = self.R * max(1.0, float(self.mult.max())) * 1.05
        self.levels = [r for r in rr if r < top] + [next(r for r in rr if r >= top)] if top > 1 else [0.0, 1.0]
        self.kern = {}
        # grain bank (luma, slightly correlated like compressed sensor noise)
        rng = np.random.default_rng(1)
        self.grain = []
        for _ in range(4):
            n = rng.standard_normal((H + 64, W + 64)).astype(np.float32)
            n = cv2.GaussianBlur(n, (0, 0), 0.6 * H / 1080)
            n /= n.std()
            self.grain.append(n)
        self.rng = rng
        self.sigma = meta["noise_sigma"] * (H / 1080.0) ** 0  # noise std in 0..255 at output res
        self.prev_alpha = None
        # gamma ~2 "linear light"
        self.to_lin = ((np.arange(256, dtype=np.float32) / 255.0) ** 2.0)

    # --- coc map from current focus
    def coc(self):
        f = self.focus_cur
        tol = self.args.dof
        dn = self.dn
        back = np.clip((f - tol - dn) / max(f - tol, 0.05), 0, 1)
        front = np.clip((dn - f - tol) / max(1 - f - tol, 0.05), 0, 1) * self.args.near
        c = self.R * (back ** self.args.falloff + front)
        return (c * self.mult).astype(np.float32)

    def stabilise_alpha(self, a):
        if self.prev_alpha is None or self.prev_alpha.shape != a.shape:
            self.prev_alpha = a
            return a
        d = np.abs(a - self.prev_alpha)
        k = np.clip(d * 4.0, self.args.alpha_smooth, 1.0)   # move fast when the matte really moves
        a = self.prev_alpha + k * (a - self.prev_alpha)
        self.prev_alpha = a
        return a

    def prepare(self, coc):
        """Everything that depends only on the CoC map (recomputed only when
        focus moves): per-level spread masks, normalisers and blend weights."""
        H, W = self.H, self.W
        L = self.levels
        self.coc_cur = coc
        dil = max(3, int(H / 160)) | 1
        cz = cv2.dilate(coc, np.ones((dil, dil), np.uint8))
        # clean-plate fill only where the blur is big enough to smear the
        # speaker's colours; near the focal plane (his own chair, which swivels
        # and so is wrong in the plate) the real pixels are used.
        g0 = max(1.5, 0.15 * self.R)
        self.fill_gate = smoothstep(g0, 2.5 * g0, cz).astype(np.float32)
        self.grain_amt = (smoothstep(0.5, 3.0, coc) * self.sigma * self.args.grain).astype(np.float32)
        lv = []
        wl = np.clip(1 - coc / L[1], 0, 1).astype(np.float32)     # weight of the sharp layer
        ws_ = wl.copy()
        for k in range(1, len(L)):
            r, lo = L[k], L[k - 1]
            hi = L[k + 1] if k + 1 < len(L) else None
            up = np.clip((coc - lo) / (r - lo), 0, 1)
            w = up if hi is None else np.minimum(up, np.clip((hi - coc) / (hi - r), 0, 1))
            w = w.astype(np.float32)
            ws_ += w
            if w.max() <= 1e-4:
                continue
            ds = 1 if r < 4 else (2 if r < 8 else (4 if r < 20 else 8))
            if H > 1080:
                ds = max(1, int(round(ds * H / 1080)))
            m = smoothstep(0.35 * r, 0.75 * r, coc).astype(np.float32)   # who may spread this far
            w2, h2 = W // ds, H // ds
            mm = cv2.resize(m, (w2, h2), interpolation=cv2.INTER_AREA) if ds > 1 else m
            rk = r / ds
            kk = self.kern.get(rk)
            if kk is None:
                kk = self.kern[rk] = disc_kernel(rk)
            db = cv2.filter2D(mm, -1, kk, borderType=cv2.BORDER_REFLECT)
            inv = (1.0 / np.maximum(db, 1e-4)).astype(np.float32)
            dbf = cv2.resize(db, (W, H), interpolation=cv2.INTER_LINEAR) if ds > 1 else db
            ok = smoothstep(0.02, 0.15, dbf).astype(np.float32)
            wl += w * (1 - ok)
            lv.append(dict(ds=ds, size=(w2, h2), m1=m, kk=kk, w=w * ok))
        ws_ = np.maximum(ws_, 1e-6)
        self.w_lin3 = cv2.merge([wl / ws_] * 3)
        for d in lv:
            ww = d.pop("w") / ws_
            d["w1"] = ww.astype(np.float32)
        self.lv = lv

    def render(self, frame, alpha, fgr, coc, rvm_a=None, core_mp=None):
        H, W = self.H, self.W
        if coc is not getattr(self, "coc_cur", None):
            self.prepare(coc)
        a = alpha
        a3 = cv2.merge([a, a, a])
        ff = frame.astype(np.float32)
        # 1. person region -> exposure-matched clean plate (only where blur spreads)
        dil = max(3, int(H / 160)) | 1
        am = cv2.dilate((a > 0.02).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dil * 2 + 1, dil * 2 + 1)))
        am = cv2.GaussianBlur(am.astype(np.float32), (0, 0), dil / 2.5)
        am_full = cv2.max(am, a)
        am = cv2.multiply(am_full, self.fill_gate)
        # speaker pixels that stay in the fill (near the focal plane, no plate)
        # must not spread into the background blur (-> no glow/halo)
        keep = 1.0 - cv2.subtract(am_full, am)
        s = 16
        ws, hs = W // s, H // s
        bgw = cv2.resize(1 - am, (ws, hs), interpolation=cv2.INTER_AREA)[..., None]
        fs = cv2.resize(frame, (ws, hs), interpolation=cv2.INTER_AREA).astype(np.float32)
        sig = ws / 12
        num = cv2.GaussianBlur(fs * bgw, (0, 0), sig)
        den = cv2.GaussianBlur(self.plate_s * bgw, (0, 0), sig)
        gain = np.clip((num + 2) / (den + 2), 0.6, 1.6).astype(np.float32)
        gain = cv2.resize(gain, (W, H), interpolation=cv2.INTER_LINEAR)
        am3 = cv2.merge([am, am, am])
        plate_adj = cv2.multiply(self.plate_f, gain)
        if self.conf is not None and self.conf.min() < 0.99:
            # where the plate is unreliable (speaker never left that spot) fill
            # from the surrounding live background instead (1/8 res push-pull)
            q = 8
            sm = cv2.resize(ff, (W // q, H // q), interpolation=cv2.INTER_AREA)
            wq = cv2.resize(1 - cv2.dilate(am_full, np.ones((9, 9), np.uint8)), (W // q, H // q), interpolation=cv2.INTER_AREA)
            pp = cv2.resize(push_pull(sm, smoothstep(0.5, 1.0, wq).astype(np.float32), 5), (W, H), interpolation=cv2.INTER_LINEAR)
            plate_adj = plate_adj * self.conf + pp * (1 - self.conf)
        fill = cv2.add(ff, cv2.multiply(cv2.subtract(plate_adj, ff), am3))

        # 2. ~linear light (gamma 2) + highlight boost for bokeh bloom
        lin = cv2.multiply(fill, fill, scale=1 / 65025.0)
        y = cv2.transform(lin, np.array([[0.2126, 0.7152, 0.0722]], np.float32))
        boost = 1.0 + self.args.bloom * 6.0 * smoothstep(0.55, 0.95, y)
        lin_b = cv2.multiply(lin, cv2.merge([boost, boost, boost]))

        # 3. layered, normalised disc blur; blend levels by CoC
        out = cv2.multiply(lin, self.w_lin3)
        for d in self.lv:
            m1 = cv2.multiply(d["m1"], keep)
            src = cv2.multiply(lin_b, cv2.merge([m1, m1, m1]))          # premultiply at full res
            if d["ds"] > 1:
                src = cv2.resize(src, d["size"], interpolation=cv2.INTER_AREA)
                ms = cv2.resize(m1, d["size"], interpolation=cv2.INTER_AREA)
                ls = cv2.resize(lin, d["size"], interpolation=cv2.INTER_AREA)
            else:
                ms, ls = m1, lin
            num = cv2.filter2D(src, -1, d["kk"], borderType=cv2.BORDER_REFLECT)
            db = cv2.filter2D(ms, -1, d["kk"], borderType=cv2.BORDER_REFLECT)
            k = smoothstep(0.01, 0.08, db).astype(np.float32)
            inv = k / np.maximum(db, 1e-4)
            B = cv2.add(cv2.multiply(num, cv2.merge([inv, inv, inv])), cv2.multiply(ls, cv2.merge([1 - k] * 3)))
            if d["ds"] > 1:
                B = cv2.resize(B, (W, H), interpolation=cv2.INTER_LINEAR)
            w1 = d["w1"]
            out = cv2.add(out, cv2.multiply(B, cv2.merge([w1, w1, w1])))
        # soft shoulder for boosted highlights, back to gamma
        sh = 0.85
        over = out - sh
        np.maximum(over, 0, out=over)
        out = out - over + (1 - sh) * np.tanh(over * (1 / (1 - sh)))
        bg = cv2.sqrt(np.maximum(out, 0)) * 255.0

        # 4. grain back where we blurred
        if self.args.grain > 0:
            g = self.grain[self.rng.integers(len(self.grain))]
            ox, oy = self.rng.integers(0, 64, 2)
            g = g[oy:oy + H, ox:ox + W]
            lum = cv2.transform(bg, np.array([[1 / 765.0] * 3], np.float32))
            amt = self.grain_amt * (0.6 + 1.6 * lum * (1 - lum))
            gg = cv2.multiply(g, amt)
            bg = cv2.add(bg, cv2.merge([gg, gg, gg]))

        # 5. composite speaker back. RVM's foreground colour is only trusted on
        # RVM's own soft edge (hair, motion-blurred fingers); elsewhere real pixels.
        if fgr is not None and rvm_a is not None:
            wf = (1 - smoothstep(0.75, 1.0, rvm_a)) * smoothstep(0.02, 0.15, rvm_a)
            if core_mp is not None:
                wf = wf * (1 - core_mp)
            wf = wf.astype(np.float32)
            fg = cv2.add(ff, cv2.multiply(np.clip(fgr * 255.0 - ff, -48, 48).astype(np.float32), cv2.merge([wf, wf, wf])))
        else:
            fg = ff
        res = cv2.add(bg, cv2.multiply(cv2.subtract(fg, bg), a3))
        return np.clip(res, 0, 255).astype(np.uint8)


def parse_size(s):
    w, h = s.lower().split("x")
    return int(w), int(h)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=None)
    ap.add_argument("--size", default="1920x1080", help="output size, e.g. 1920x1080 or 3840x2160")
    ap.add_argument("--crop", default=None, help="x,y,w,h crop in SOURCE pixels (punch-in) before scaling to --size")
    ap.add_argument("--strength", type=float, default=1.0, help="blur strength (1.0 = max radius 1.25%% of frame height)")
    ap.add_argument("--keep-polygon", default=None, help="JSON with regions (normalised source coords) and per-region strength")
    ap.add_argument("--focus", type=float, default=None, help="fixed focus (0=far .. 1=near normalised disparity); default tracks speaker")
    ap.add_argument("--focus-every", type=float, default=0.5, help="seconds between focus re-estimates (0 = fixed)")
    ap.add_argument("--dof", type=float, default=0.04, help="in-focus tolerance band (normalised disparity)")
    ap.add_argument("--falloff", type=float, default=0.7, help="exponent of blur vs depth behind focus (1 = physical)")
    ap.add_argument("--near", type=float, default=0.25, help="relative blur for things nearer than focus")
    ap.add_argument("--bloom", type=float, default=0.35, help="highlight boost inside blur (0..1)")
    ap.add_argument("--grain", type=float, default=1.0, help="re-grain amount (1 = match source noise)")
    ap.add_argument("--depth-update", type=float, default=0.5, help="live depth correction rate where the scene changed vs the plate (0 = static depth)")
    ap.add_argument("--alpha-smooth", type=float, default=0.5, help="temporal matte smoothing factor (1 = none)")
    ap.add_argument("--matte-res", type=int, default=1080, help="matting resolution (height); upsampled with guided filter")
    ap.add_argument("--preroll", type=float, default=1.0, help="seconds of matting warm-up before --start")
    ap.add_argument("--fps", type=float, default=None, help="force output fps (e.g. 30 for the 120 fps clip)")
    ap.add_argument("--plate-range", default=None, help="t0,t1 seconds used to build the clean plate (default whole clip)")
    ap.add_argument("--rebuild-cache", action="store_true")
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--dump-alpha", default=None, help="write the matte as a small grey mp4 (for QA)")
    args = ap.parse_args()

    info = probe(args.inp)
    W, H = parse_size(args.size)
    crop = tuple(int(v) for v in args.crop.split(",")) if args.crop else None
    end = min(args.end if args.end is not None else info["dur"], info["dur"])
    start = max(0.0, args.start)
    fps = args.fps or info["fps"]
    pr = (float(x) for x in args.plate_range.split(",")) if args.plate_range else (None, None)
    plate, disp, meta = build_cache(args.inp, info, t0=next(pr), t1=next(pr), force=args.rebuild_cache) \
        if args.plate_range else build_cache(args.inp, info, force=args.rebuild_cache)
    rend = Renderer(plate, disp, meta, W, H, crop, (info["w"], info["h"]), args)
    log(f"levels={['%.1f' % l for l in rend.levels]} R={rend.R:.1f}px focus={rend.focus_n:.3f}")

    mh = min(args.matte_res, H)
    mw = int(round(W * mh / H / 2)) * 2
    matter = Matter(internal_short=288)
    segm = Segmenter()
    depth = Depth(short=392) if (args.focus is None and args.focus_every > 0) else None

    s0 = max(0.0, start - args.preroll)
    npre = int(round((start - s0) * fps))
    reader = Reader(args.inp, s0, end - s0, crop, W, H, fps=fps)   # fps filter = constant frame rate, no drops/dups drift
    writer = Writer(args.out, W, H, fps, None if args.no_audio or not info["audio"] else args.inp,
                    start, end - start, crf=args.crf, preset=args.preset)
    awriter = None
    if args.dump_alpha:
        awriter = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray",
                                    "-s", "480x270", "-r", f"{fps:.6f}", "-i", "-", "-c:v", "libx264",
                                    "-crf", "12", "-pix_fmt", "yuv420p", args.dump_alpha], stdin=subprocess.PIPE)
    every = max(1, int(round(args.focus_every * fps))) if depth else 0
    tm = dict(matte=0.0, focus=0.0, render=0.0)
    import threading, queue
    qs = 4 if H <= 1080 else 2
    q_in, q_mat = queue.Queue(maxsize=qs), queue.Queue(maxsize=qs)

    def t_read():
        while True:
            fr = reader.read()
            q_in.put(fr)
            if fr is None:
                return

    def t_matte():
        """matting + focus tracking; emits (frame, alpha, fgr, rvm_alpha, core, coc)"""
        target = rend.focus_n
        coc = rend.coc()
        force_coc = [False]
        last_cf = rend.focus_cur
        i = 0
        while True:
            fr = q_in.get()
            if fr is None:
                q_mat.put(None)
                return
            t = time.time()
            small = fr if mh == H else cv2.resize(fr, (mw, mh), interpolation=cv2.INTER_AREA)
            a, fgr = matter.step(small)
            pm = segm(cv2.resize(small, (640, 360), interpolation=cv2.INTER_AREA))
            pm = cv2.resize(pm, (W, H), interpolation=cv2.INTER_LINEAR)
            if mh != H:
                g = cv2.cvtColor(fr, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
                a = cv2.resize(a, (W, H), interpolation=cv2.INTER_LINEAR)
                a = cv2.ximgproc.guidedFilter(g, a, int(2 * H / mh), 1e-4).clip(0, 1)
                fgr = cv2.resize(fgr, (W, H), interpolation=cv2.INTER_LINEAR)
            cm = body_core(pm, H)
            rvm_a = a
            a = rend.stabilise_alpha(np.maximum(a, cm))
            tm["matte"] += time.time() - t
            if depth is not None and i % every == 0:
                t = time.time()
                core = a > 0.9
                # very large / edge-cut silhouettes (walking past the lens) are
                # not the subject distance: hold focus instead of racking
                if 0.01 < core.mean() < 0.22:
                    hw = (W * 270 // H // 2 * 2, 270) if H > 540 else (W, H)
                    df = depth(cv2.resize(fr, hw, interpolation=cv2.INTER_AREA))
                    c2 = cv2.resize(core.astype(np.uint8), hw, interpolation=cv2.INTER_NEAREST)
                    c2 = cv2.erode(c2, np.ones((5, 5), np.uint8)).astype(bool)
                    bgm = cv2.resize((a < 0.01).astype(np.uint8), hw, interpolation=cv2.INTER_NEAREST).astype(bool)
                    dref = cv2.resize(rend.dn, hw, interpolation=cv2.INTER_AREA)
                    aa, bb = affine_fit(df, dref, bgm)
                    if aa > 0 and args.depth_update > 0:
                        # live depth correction where the scene really changed
                        # vs the plate (e.g. the speaker's swivel chair moved)
                        diff = (aa * df + bb) - dref
                        # near the silhouette Depth Anything bleeds the (nearer)
                        # person outwards, so there only "farther" corrections count
                        ok_far = cv2.erode(bgm.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32)
                        ok_any = cv2.erode(bgm.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)
                        ok = np.where(diff < 0, ok_far, ok_any)
                        upd = ok * smoothstep(0.06, 0.15, np.abs(diff))
                        upd = cv2.GaussianBlur(upd, (0, 0), 2)
                        if upd.max() > 0.05:
                            delta = (diff * upd * args.depth_update).astype(np.float32)
                            rend.dn = rend.dn + cv2.resize(delta, (W, H), interpolation=cv2.INTER_LINEAR)
                            force_coc[0] = True
                    if c2.sum() > 100 and aa > 0:
                        nt = float(np.clip(aa * np.median(df[c2]) + bb, 0.1, 0.95))
                        if abs(nt - target) > 0.03:          # deadband: no breathing
                            target = nt
                tm["focus"] += time.time() - t
            if i < npre:                      # warm-up: converge, emit nothing
                rend.focus_cur = target
            else:
                if depth is not None:
                    rend.focus_cur += (target - rend.focus_cur) * min(1.0, 1.25 / fps)   # ~0.8 s pull
                    if abs(rend.focus_cur - last_cf) > 0.004 or i == npre or force_coc[0]:
                        force_coc[0] = False
                        coc = rend.coc()
                        last_cf = rend.focus_cur
                q_mat.put((fr, a, fgr, rvm_a, cm, coc))
            i += 1

    th = [threading.Thread(target=t_read, daemon=True), threading.Thread(target=t_matte, daemon=True)]
    for x in th:
        x.start()
    n_out = 0
    tic = time.time()
    while True:
        item = q_mat.get()
        if item is None:
            break
        fr, a, fgr, rvm_a, cm, coc = item
        t = time.time()
        out = rend.render(fr, a, fgr, coc, rvm_a, cm)
        tm["render"] += time.time() - t
        writer.write(out)
        if awriter:
            awriter.stdin.write((cv2.resize(a, (480, 270), interpolation=cv2.INTER_AREA) * 255).astype(np.uint8).tobytes())
        n_out += 1
        if n_out % 30 == 0:
            el = time.time() - tic
            log(f"{n_out} frames  {el / n_out:.2f}s/frame  focus={rend.focus_cur:.3f}")
    reader.close()
    writer.close()
    if awriter:
        awriter.stdin.close()
        awriter.wait()
    el = time.time() - tic
    secs = n_out / fps
    log(f"done: {n_out} frames ({secs:.1f}s) in {el:.0f}s = {el / max(secs, 1e-6):.1f} s per output second "
        f"(incl. {npre} preroll frames); per-frame cpu: "
        + " ".join(f"{k}={v / max(n_out, 1):.3f}" for k, v in tm.items()))
    os._exit(0)   # skip mediapipe's noisy destructor


if __name__ == "__main__":
    main()
