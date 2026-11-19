#!/usr/bin/env python3
"""Per-segment exposure + white-balance match to one warm DDN-style target, as an ffmpeg filter string.
usage: grade.py timeline.json OUT.json   (measures each segment on the 1080p proxy; writes {index: filter})
Target: midtone median Y ~ TARGET_MED, mid R/G 1.07, B/G 0.93 (slightly warm), soft contrast, gentle denoise when lifted.
"""
import json, sys
import cv2, numpy as np

TARGET_MED, RG, BG = 0.40, 1.07, 0.93

def measure(src, t0, t1):
    cap = cv2.VideoCapture(src); ys, rg, bg = [], [], []
    for t in np.linspace(t0 + 0.3, t1 - 0.3, 5):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, f = cap.read()
        if not ok: continue
        f = f.astype(np.float32) / 255
        y = 0.0722 * f[..., 0] + 0.7152 * f[..., 1] + 0.2126 * f[..., 2]
        m = (y > 0.15) & (y < 0.9)
        ys.append(np.median(y)); rg.append(f[..., 2][m].mean() / f[..., 1][m].mean()); bg.append(f[..., 0][m].mean() / f[..., 1][m].mean())
    return float(np.mean(ys)), float(np.mean(rg)), float(np.mean(bg))

def filt(med, rg, bg):
    # gamma so the median lands near target (ffmpeg eq: out = in^(1/gamma)); cap the lift to avoid washing out noise
    g = np.log(med) / np.log(TARGET_MED)
    g = float(np.clip(g, 0.85, 1.45))
    rs, bs = float(np.clip(RG / rg, 0.94, 1.06)), float(np.clip(BG / bg, 0.94, 1.06))
    f = []
    if g > 1.15: f.append("hqdn3d=1.2:1.2:4:4")          # light denoise only where shadows are lifted
    f.append(f"colorchannelmixer=rr={rs:.4f}:bb={bs:.4f}")
    f.append(f"eq=gamma={g:.3f}:contrast=1.04:saturation=0.94")
    f.append("curves=master='0/0.035 0.5/0.5 0.92/0.9 1/0.95'")  # lifted blacks, soft highlight roll-off (DDN look)
    return ",".join(f), dict(gamma=round(g, 3), r=round(rs, 4), b=round(bs, 4), med=round(med, 3), rg=round(rg, 3), bg=round(bg, 3))

tl = json.load(open(sys.argv[1])); out = {}
for i, s in enumerate(tl):
    src = s["src"].replace("../footage/raw/", "/home/user/ddn-project/footage/proxy/").replace(".MOV", ".mp4")
    a = s["in"] + (1.9 if i == 0 else 0)  # hook: measure after the roll-in starts
    f, info = filt(*measure(src, a, s["out"]))
    out[str(i)] = dict(filter=f, **info); print(i + 1, info)
json.dump(out, open(sys.argv[2], "w"), indent=1)
