#!/usr/bin/env python3
"""HLG/PQ -> SDR Rec.709 tone mapping: filter chains, soft-shoulder LUT, proxies and an A/B stills sheet.

Subcommands:
  tonemap.py chain [--method hable|mobius|lut] [--res 1920x1080]     print the ffmpeg -vf chain
  tonemap.py lut OUT.cube [--size 33] [--knee 0.8]                    write the 203-nit soft-shoulder LUT
  tonemap.py proxy IN.mov OUT.mp4 [--method hable] [--res 1920x1080]  1080p SDR H.264 proxy (BT.709 tagged, -g 30)
  tonemap.py ab IN.mov OUTDIR [--times 3,10] [--methods hable,mobius,lut]
        stills for each method at each time + a side-by-side sheet with a face crop and skin stats (Lab L*, chroma, hue)

Every chain ends with setparams=bt709 so frame-level tags can't leak HLG metadata into intermediates
(lesson from kurbaitaev/ghost-editor, MIT). The soft-shoulder LUT re-implements the maths described in
ghost-editor scripts/grade_lib.py (MIT, (c) 2026 kurbaitaev): HLG inverse OETF -> OOTF for a 1000-nit display
(system gamma 1.2) -> /203 nits (SDR reference white) -> BT.2020->709 -> soft shoulder above Y=0.8 -> BT.1886 gamma 1/2.4.
"""
import argparse, json, os, subprocess, sys
import numpy as np

TAIL = "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv"
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LUT = os.path.join(HERE, "models", "hlg_softshoulder_203.cube")


def transfer_of(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer",
                        "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    return r


def chain(method="hable", w=1920, h=1080, transfer="arib-std-b67", lut=DEFAULT_LUT):
    """ffmpeg -vf chain HDR -> SDR BT.709 at w x h (resize first: 2-3x faster than tone-mapping at 4K)."""
    if transfer not in ("arib-std-b67", "smpte2084"):          # already SDR: scale + tag only
        return f"scale={w}:{h}:flags=lanczos,format=yuv420p,{TAIL}"
    if method == "lut":
        if transfer != "arib-std-b67":
            raise SystemExit("the soft-shoulder LUT is HLG-only; use hable/mobius for PQ")
        if not os.path.exists(lut):
            write_lut(lut)
        return (f"scale={w}:{h}:flags=lanczos:in_color_matrix=bt2020:in_range=tv,format=rgb48le,"
                f"lut3d=file={lut}:interp=tetrahedral,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,{TAIL}")
    tm = {"hable": "tonemap=tonemap=hable:desat=0", "mobius": "tonemap=tonemap=mobius:param=0.3:desat=0"}[method]
    return (f"zscale=w={w}:h={h}:f=bilinear:tin={transfer}:min=bt2020nc:pin=bt2020:rin=tv:t=linear:npl=203,"
            f"format=gbrpf32le,zscale=p=bt709,{tm},zscale=t=bt709:m=bt709:r=tv,format=yuv420p,{TAIL}")


# encoder args shared by every intermediate: BT.709 tags + 1 s GOP for random access
X264_TAGS = ["-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
             "-color_range", "tv", "-g", "30", "-keyint_min", "30"]


def write_lut(path, size=33, knee=0.8, peak_nits=1000.0, ref_nits=203.0):
    a, b, c = 0.17883277, 0.28466892, 0.55991073
    g = np.linspace(0, 1, size)
    B, G, R = np.meshgrid(g, g, g, indexing="ij")         # .cube order: R fastest
    E = np.stack([R, G, B], -1).reshape(-1, 3)
    lin = np.where(E <= 0.5, E ** 2 / 3, (np.exp((E - c) / a) + b) / 12)     # HLG inverse OETF -> scene light 0..1
    Ys = lin @ np.array([0.2627, 0.6780, 0.0593])
    gamma = 1.2
    disp = peak_nits * (np.maximum(Ys, 1e-9) ** (gamma - 1))[:, None] * lin  # OOTF (nits)
    rel = disp / ref_nits                                                      # 1.0 = SDR reference white
    M = np.array([[1.6605, -0.5876, -0.0728], [-0.1246, 1.1329, -0.0083], [-0.0182, -0.1006, 1.1187]])
    rgb = np.maximum(rel @ M.T, 0)
    Y = rgb @ np.array([0.2126, 0.7152, 0.0722])
    Yt = np.where(Y > knee, knee + (1 - knee) * (1 - np.exp(-(Y - knee) / (1 - knee))), Y)
    rgb = rgb * (Yt / np.maximum(Y, 1e-9))[:, None]
    rgb = np.clip(rgb, 0, 1) ** (1 / 2.4)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        f.write(f"TITLE \"HLG 1000nit -> SDR709 203nit soft shoulder {knee}\"\nLUT_3D_SIZE {size}\n")
        f.write("\n".join(f"{r:.6f} {g_:.6f} {b_:.6f}" for r, g_, b_ in rgb) + "\n")
    return path


def proxy(src, out, method="hable", res="1920x1080", crf="20"):
    w, h = res.split("x")
    vf = chain(method, w, h, transfer_of(src))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", crf,
                    *X264_TAGS, "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out], check=True)


def _face_box(img):
    """largest face (mediapipe FaceLandmarker) -> x0,y0,x1,y1 in pixels, or None"""
    try:
        import mediapipe as mp
        from mediapipe.tasks.python import vision, BaseOptions
        lm = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=os.path.join(HERE, "models", "face_landmarker.task")), num_faces=1))
        r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=img[:, :, ::-1].copy())); lm.close()
        if not r.face_landmarks: return None
        H, W = img.shape[:2]; xs = [p.x * W for p in r.face_landmarks[0]]; ys = [p.y * H for p in r.face_landmarks[0]]
        return int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
    except Exception as e:
        print("face detection unavailable:", e, file=sys.stderr); return None


def skin_stats(img, box):
    """Lab stats on the cheeks/forehead core of the face box (inner 50%)"""
    import cv2
    x0, y0, x1, y1 = box; dx, dy = (x1 - x0) // 4, (y1 - y0) // 4
    patch = img[y0 + dy:y1 - dy, x0 + dx:x1 - dx]
    lab = cv2.cvtColor(patch.astype(np.float32) / 255, cv2.COLOR_BGR2Lab).reshape(-1, 3)
    L, A, B = lab[:, 0], lab[:, 1], lab[:, 2]
    return {"L_med": round(float(np.median(L)), 1), "L_p95": round(float(np.percentile(L, 95)), 1),
            "chroma": round(float(np.median(np.hypot(A, B))), 1), "hue_deg": round(float(np.degrees(np.arctan2(np.median(B), np.median(A)))), 1),
            "clipped_pct": round(float((patch.max(2) >= 250).mean() * 100), 2)}


def ab(src, outdir, times, methods, res="1920x1080"):
    import cv2
    os.makedirs(outdir, exist_ok=True)
    w, h = res.split("x"); tr = transfer_of(src); rows, report = [], {}
    for t in times:
        tiles = []; box = None
        for m in methods:
            p = os.path.join(outdir, f"still_{m}_{t:g}s.png")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", src, "-vf", chain(m, w, h, tr), "-frames:v", "1", p], check=True)
            img = cv2.imread(p)
            box = box or _face_box(img)
            st = skin_stats(img, box) if box else {}
            report[f"{m}@{t:g}"] = st
            if box:
                x0, y0, x1, y1 = box; pad = (x1 - x0) // 2
                crop = img[max(y0 - pad, 0):y1 + pad, max(x0 - pad, 0):x1 + pad]
            else:
                crop = img
            crop = cv2.resize(crop, (480, int(480 * crop.shape[0] / crop.shape[1])))
            full = cv2.resize(img, (480, 270))
            tile = np.vstack([full, crop])
            label = f"{m} t={t:g}s " + (f"L*{st['L_med']} C{st['chroma']} clip{st['clipped_pct']}%" if st else "")
            cv2.rectangle(tile, (0, 0), (480, 22), (0, 0, 0), -1)
            cv2.putText(tile, label, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
            tiles.append(tile)
        hmax = max(x.shape[0] for x in tiles)
        rows.append(np.hstack([np.pad(x, ((0, hmax - x.shape[0]), (0, 0), (0, 0))) for x in tiles]))
    wmax = max(r.shape[1] for r in rows)
    sheet = np.vstack([np.pad(r, ((0, 0), (0, wmax - r.shape[1]), (0, 0))) for r in rows])
    sp = os.path.join(outdir, "tonemap_ab.jpg"); cv2.imwrite(sp, sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
    json.dump(report, open(os.path.join(outdir, "tonemap_ab.json"), "w"), indent=1)
    for k, v in report.items(): print(f"{k:14s} {v}")
    print(f"sheet -> {sp}\n(skin guide: median L* of lit skin ~55-70 on SDR; lower = crushed/dark, clipped% > 1 = blown highlights)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("chain"); c.add_argument("--method", default="hable", choices=["hable", "mobius", "lut"])
    c.add_argument("--res", default="1920x1080"); c.add_argument("--transfer", default="arib-std-b67")
    l = sub.add_parser("lut"); l.add_argument("out", nargs="?", default=DEFAULT_LUT); l.add_argument("--size", type=int, default=33)
    l.add_argument("--knee", type=float, default=0.8)
    p = sub.add_parser("proxy"); p.add_argument("src"); p.add_argument("out"); p.add_argument("--method", default="hable", choices=["hable", "mobius", "lut"])
    p.add_argument("--res", default="1920x1080"); p.add_argument("--crf", default="20")
    b = sub.add_parser("ab"); b.add_argument("src"); b.add_argument("outdir"); b.add_argument("--times", default="3,10")
    b.add_argument("--methods", default="hable,mobius,lut"); b.add_argument("--res", default="1920x1080")
    a = ap.parse_args()
    if a.cmd == "chain":
        w, h = a.res.split("x"); print(chain(a.method, w, h, a.transfer))
    elif a.cmd == "lut":
        print(write_lut(a.out, a.size, a.knee))
    elif a.cmd == "proxy":
        proxy(a.src, a.out, a.method, a.res, a.crf)
    elif a.cmd == "ab":
        ab(a.src, a.outdir, [float(x) for x in a.times.split(",")], a.methods.split(","), a.res)


if __name__ == "__main__":
    main()
