#!/usr/bin/env python3
"""QA evidence for look_v4.py -> /home/user/ddn-project/output/look_v4/"""
import json, os, subprocess, sys
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import look_v4 as L
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = f"{L.ROOT}/output/look_v4"
NB = f"{L.ROOT}/edit/plates_noblur_v4"
LK = f"{L.ROOT}/edit/plates_look_v4"
QA = f"{OUT}/qa_frames"
W, H = L.W, L.H
P = L.pieces()
fast = {int(k): v for k, v in json.load(open(f"{L.CACHE}/fastest.json")).items()}


def frames(path, idx):
    sel = "+".join(f"eq(n\\,{i})" for i in idx)
    b = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-vf", f"select='{sel}'", "-vsync", "0",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(b, np.uint8).reshape(-1, H, W, 3)


def bgr(a):
    return cv2.cvtColor(a, cv2.COLOR_RGB2BGR)


def label(img, txt):
    img = img.copy()
    cv2.putText(img, txt, (12, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 4)
    cv2.putText(img, txt, (12, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    return img


def stills_and_strips(i, mid):
    s0 = fast[i]; idx = list(range(s0, s0 + 12))
    nb = frames(f"{NB}/seg{i:02d}.mp4", [mid]); lk = frames(f"{LK}/seg{i:02d}.mp4", [mid])
    ba = np.hstack([label(nb[0], "before (no-blur plate)"), label(lk[0], "after (look_v4)")])
    cv2.imwrite(f"{OUT}/still_p{i:02d}_before_after.jpg", bgr(ba), [cv2.IMWRITE_JPEG_QUALITY, 93])
    # 12-frame strip, 100% crop around the speaker during the fastest motion
    A = L.load(P[i])
    fx, fy = np.nanmedian(A["face_xy"][idx], 0) if np.isfinite(A["face_xy"][idx]).any() else (0.4, 0.3)
    cw, ch = 520, 760
    x0 = int(np.clip(fx * W - cw / 2, 0, W - cw)); y0 = int(np.clip(fy * H - 120, 0, H - ch))
    nbf = frames(f"{NB}/seg{i:02d}.mp4", idx)
    rows = {"no-blur plate": [], "look_v4 plate": [], "look_v4 frame (lossless)": [], "same frame rendered with blur OFF": [],
            "|lossless diff| x50": []}
    dmax = 0
    for k, fi in enumerate(idx):
        a = cv2.imread(f"{QA}/p{i:02d}_f{fi:03d}_look.png")[..., ::-1]
        r = cv2.imread(f"{QA}/p{i:02d}_f{fi:03d}_noblurlook.png")[..., ::-1]
        d = np.abs(a.astype(np.int16) - r)
        zone = L.blur_weight(P[i], A)[1]["dist"] < L.DIL
        zone = cv2.resize(zone.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
        dmax = max(dmax, int(d[zone].max()))
        sl = (slice(y0, y0 + ch), slice(x0, x0 + cw))
        rows["no-blur plate"].append(nbf[k][sl])
        lkf = frames(f"{LK}/seg{i:02d}.mp4", [fi])[0]
        rows["look_v4 plate"].append(lkf[sl])
        rows["look_v4 frame (lossless)"].append(a[sl])
        rows["same frame rendered with blur OFF"].append(r[sl])
        dd = np.clip(d[sl] * 50, 0, 255).astype(np.uint8)
        zc = zone[sl]
        dd[~zc] = (dd[~zc] * 0.5 + 40).astype(np.uint8)     # grey-out outside the protected zone
        rows["|lossless diff| x50"].append(dd)
    strip = []
    for name, ims in rows.items():
        row = np.hstack([label(im, f"{name} f{idx[k]}" if k == 0 else f"f{idx[k]}") for k, im in enumerate(ims)])
        strip.append(row)
    strip = np.vstack(strip)
    cv2.imwrite(f"{OUT}/strip_p{i:02d}_fastest_motion_100pct.jpg", bgr(strip), [cv2.IMWRITE_JPEG_QUALITY, 92])
    return dmax, idx


def flicker_chart(ids):
    fig, axs = plt.subplots(len(ids), 1, figsize=(11, 2.6 * len(ids)))
    for ax, i in zip(axs, ids):
        r = np.load(f"{L.CACHE}/render{i:02d}.npz")["flick"]
        t = np.arange(1, len(r) + 1)
        ax.plot(t, r[:, 0], color="#888", lw=1, label="input: mean |frame diff| (whole frame)")
        ax.plot(t, r[:, 1], color="#1f6feb", lw=1, ls="--", label="output: mean |frame diff| (whole frame)")
        ax.plot(t, r[:, 4], color="#d1242f", lw=1.2, label="output minus input |frame diff|, blurred background only")
        ax.axhline(0, color="k", lw=0.5)
        ax.set_title(f"piece {i}: added temporal change (red) max {r[:, 4].max():+.3f} codes; "
                     f"protected-zone diff vs blur-off render: max {r[:, 3].max():.0f}", fontsize=9)
        ax.set_ylabel("8-bit codes"); ax.legend(fontsize=7, loc="upper right")
    axs[-1].set_xlabel("frame")
    fig.tight_layout(); fig.savefig(f"{OUT}/flicker_scan.png", dpi=110); plt.close(fig)


def consistency_chart():
    """skin + frame brightness per piece, before vs after (face landmarks on both plates, 5 frames/piece)."""
    import mediapipe as mp
    from mediapipe.tasks.python import vision, BaseOptions
    o = vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=f"{L.ROOT}/tools/models/face_landmarker.task"),
                                     num_faces=1, min_face_detection_confidence=0.3)
    fl = vision.FaceLandmarker.create_from_options(o)
    res = {"before": [], "after": []}
    for p in P:
        A = L.load(p)
        idx = [int(x) for x in np.linspace(2, p["n"] - 3, 5)]
        for tag, d in (("before", NB), ("after", LK)):
            F = frames(f"{d}/seg{p['i']:02d}.mp4", idx)
            ys, rg, bg, fr = [], [], [], []
            for k, f in zip(idx, F):
                fr.append(((f.astype(np.float32) / 255) ** 2.2).mean())
                cx, cy = A["face_xy"][k]
                if not np.isfinite(cx):
                    continue
                r = int(0.16 * H) if p["i"] < 17 else int(0.3 * H)
                x0 = int(np.clip(cx * W - r, 0, W - 2 * r)); y0 = int(np.clip(cy * H - r, 0, H - 2 * r))
                crop = np.ascontiguousarray(cv2.resize(f[y0:y0 + 2 * r, x0:x0 + 2 * r], (512, 512), interpolation=cv2.INTER_AREA))
                det = fl.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=crop))
                if not det.face_landmarks:
                    continue
                lm = (np.array([[q.x, q.y] for q in det.face_landmarks[0]]) * 512).astype(np.int32)
                mk = np.zeros((512, 512), np.uint8); cv2.fillConvexPoly(mk, cv2.convexHull(lm), 1)
                mk = cv2.erode(mk, np.ones((7, 7), np.uint8))
                px = (crop[mk > 0].astype(np.float32) / 255) ** 2.2
                yv = px @ np.array([0.2126, 0.7152, 0.0722], np.float32)
                lo, hi = np.percentile(yv, [25, 85]); s = px[(yv >= lo) & (yv <= hi)].mean(0)
                ys.append(s @ np.array([0.2126, 0.7152, 0.0722])); rg.append(s[0] / s[1]); bg.append(s[2] / s[1])
            res[tag].append([np.median(ys) if ys else np.nan, np.median(rg) if rg else np.nan,
                             np.median(bg) if bg else np.nan, np.mean(fr)])
    B = np.array(res["before"]); Af = np.array(res["after"])
    x = np.arange(len(P))
    fig, axs = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    ev = lambda v: np.log2(v / np.nanmedian(B[:, 0]))
    axs[0].plot(x, ev(B[:, 0]), "o-", color="#888", label="before"); axs[0].plot(x, ev(Af[:, 0]), "o-", color="#1f6feb", label="after")
    axs[0].set_ylabel("skin luminance\n(stops vs median before)")
    axs[1].plot(x, B[:, 1], "o-", color="#888"); axs[1].plot(x, Af[:, 1], "o-", color="#1f6feb"); axs[1].set_ylabel("skin R/G")
    axs[1].plot(x, B[:, 2] * 0 + np.nan)
    ax2 = axs[1].twinx(); ax2.plot(x, B[:, 2], "s:", color="#bbb"); ax2.plot(x, Af[:, 2], "s:", color="#7aa7f0"); ax2.set_ylabel("skin B/G (dotted)")
    axs[2].plot(x, np.log2(B[:, 3] / np.median(B[:, 3])), "o-", color="#888"); axs[2].plot(x, np.log2(Af[:, 3] / np.median(B[:, 3])), "o-", color="#1f6feb")
    axs[2].set_ylabel("whole-frame mean\n(stops)"); axs[2].set_xlabel("piece")
    axs[0].legend(); axs[2].set_xticks(x)
    sd = lambda v: np.nanstd(v)
    fig.suptitle(f"Skin / brightness consistency across the 20 pieces. Spread (std) before -> after: "
                 f"skin {sd(ev(B[:, 0])):.2f} -> {sd(ev(Af[:, 0])):.2f} stops, R/G {sd(B[:, 1]):.3f} -> {sd(Af[:, 1]):.3f}", fontsize=10)
    fig.tight_layout(); fig.savefig(f"{OUT}/consistency_chart.png", dpi=110); plt.close(fig)
    np.savez(f"{OUT}/consistency_data.npz", before=B, after=Af)
    return B, Af


def side_by_side(t0, dur, name):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t0:.3f}", "-t", f"{dur}", "-i", f"{NB}/plate.mp4",
                    "-ss", f"{t0:.3f}", "-t", f"{dur}", "-i", f"{LK}/plate.mp4", "-filter_complex",
                    "[0]scale=1152:648,drawtext=text='before':x=20:y=20:fontsize=30:fontcolor=white:borderw=2[a];"
                    "[1]scale=1152:648,drawtext=text='after (look_v4)':x=20:y=20:fontsize=30:fontcolor=white:borderw=2[b];"
                    "[a][b]hstack", "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p",
                    f"{OUT}/{name}"], check=True)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    mids = {0: 140, 3: 40, 9: 120, 12: 30}
    rep = {}
    for i, m in mids.items():
        d, idx = stills_and_strips(i, m)
        rep[i] = dict(protected_zone_max_diff_vs_blur_off=d, strip_frames=idx)
        print("piece", i, "protected-zone max |diff| vs blur-off render (lossless):", d, flush=True)
    flicker_chart(list(mids))
    B, Af = consistency_chart()
    tl = json.load(open(L.TL))
    side_by_side(0.0, 10, "hook_before_after_10s.mp4")
    side_by_side(round(tl[9]["vstart"] * 30) / 30, 10, "ddn_piece09_before_after_10s.mp4")
    json.dump(rep, open(f"{OUT}/qa_summary.json", "w"), indent=1)
    print("done")
    os._exit(0)
