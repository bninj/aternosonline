"""Find logo positions that sit BEHIND the speaker but stay readable.
usage: logo_place.py matte_dir first_frame from to aspect h region(x0,y0,x1,y1) [avoid boxes ...]
Alpha PNGs are in plate px (2304x1296); positions are footage px @1920 (pre-zoom). For each candidate box we measure,
on every frame of [from, to), which columns of the logo are covered by the person (alpha > 0.5 in >= 8% of the column).
Accept: covered columns only at ONE edge, max over frames <= 14 % of the width; prefer 4..14 % (visibly behind)."""
import sys, json, glob, os
import numpy as np
from PIL import Image

mdir, first, f0, f1, aspect, h = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6])
x0, y0, x1, y1 = map(float, sys.argv[7].split(','))
avoid = [tuple(map(float, a.split(','))) for a in sys.argv[8:]]
S = 1920 / 2304
frames = []
for f in range(f0, f1, 2):
    p = os.path.join(mdir, f'a_{f - first:06d}.png')
    a = np.asarray(Image.open(p).convert('L').resize((960, 540)), dtype=np.float32) / 255.0  # 2 px per cell @1920
    frames.append(a > 0.5)
occ = np.stack(frames)  # T x 540 x 960
w = h * aspect
best = []
for y in np.arange(y0, y1 - h, 8):
    for x in np.arange(x0, x1 - w, 8):
        if any(not (x + w < ax or x > ax + aw or y + h < ay or y > ay + ah) for ax, ay, aw, ah in avoid):
            continue
        r0, r1, c0, c1 = int(y / 2), int((y + h) / 2), int(x / 2), int((x + w) / 2)
        sub = occ[:, r0:r1, c0:c1]  # T x rows x cols
        colcov = sub.mean(axis=1) > 0.08  # T x cols
        ok = True
        worst = 0.0
        for t in range(colcov.shape[0]):
            cols = np.where(colcov[t])[0]
            if len(cols) == 0:
                continue
            n = colcov.shape[1]
            frac = len(cols) / n
            edge_right = cols.min() >= n * (1 - 0.14)
            edge_left = cols.max() <= n * 0.14
            if not (edge_right or edge_left):
                ok = False; break
            worst = max(worst, frac)
        if ok:
            best.append((worst, float(x), float(y)))
MAXC = float(os.environ.get('MAXC', '0.14'))
best = [b for b in best if 0.015 <= b[0] <= MAXC] or best
best.sort(key=lambda b: (b[2], -b[0]))  # highest on the wall first, then most tucked
print(json.dumps([{'x': round(x), 'y': round(y), 'h': h, 'w': round(w), 'covered': round(c, 3)} for c, x, y in best[:8]]))
