#!/usr/bin/env python3
"""qa.py - before/after stills, frame strip and background flicker scan for a
bgblur render.

  qa.py --orig RAW.MOV --start S --end E --out OUT.mp4 --alpha OUT_alpha.mp4 \
        --name tag [--crop x,y,w,h] [--stills 0.5,1.5]

Flicker metric: per frame pair, mean |lowpass(luma_t) - lowpass(luma_t-1)| (0..255)
measured at 480x270 after a sigma=1.5 blur (removes grain, keeps real flicker),
  * bg   = pixels away from the speaker in both frames (alpha<0.01, eroded 12px)
  * ring = band 2..20 px (at 480 wide) around the speaker silhouette (halo zone)
for the original and for the output.  Output <= original is the goal; spikes
in 'ring' reveal matte popping.
"""
import argparse, json, os, sys
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bgblur import Reader, probe  # noqa


def lum_lp(rgb):
    s = cv2.resize(rgb, (480, 270), interpolation=cv2.INTER_AREA)
    g = cv2.cvtColor(s, cv2.COLOR_RGB2GRAY).astype(np.float32)
    return cv2.GaussianBlur(g, (0, 0), 1.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orig", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--alpha", required=True)
    ap.add_argument("--start", type=float, required=True)
    ap.add_argument("--end", type=float, required=True)
    ap.add_argument("--crop", default=None)
    ap.add_argument("--name", required=True)
    ap.add_argument("--stills", default=None, help="comma list of seconds (relative to start)")
    ap.add_argument("--dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "qa"))
    a = ap.parse_args()
    os.makedirs(a.dir, exist_ok=True)
    info = probe(a.out)
    W, H = info["w"], info["h"]
    crop = tuple(int(v) for v in a.crop.split(",")) if a.crop else None
    ro = Reader(a.orig, a.start, a.end - a.start, crop, W, H)
    rb = Reader(a.out, 0, None, None, W, H)
    ra = Reader(a.alpha, 0, None, None, 480, 270)
    dur = a.end - a.start
    stills = [float(x) for x in a.stills.split(",")] if a.stills else [dur * 0.25, dur * 0.75]
    fps = info["fps"]
    still_idx = {int(round(t * fps)): t for t in stills}
    n = int(round(dur * fps))
    strip_idx = set(np.linspace(0, max(0, n - 1), 6).round().astype(int).tolist())
    strip = []
    prev = None
    rows = []
    i = 0
    while True:
        fo, fb, fa = ro.read(), rb.read(), ra.read()
        if fo is None or fb is None or fa is None:
            break
        al = fa[..., 0].astype(np.float32) / 255
        lo, lb = lum_lp(fo), lum_lp(fb)
        if prev is not None:
            plo, plb, pal = prev
            person = ((al > 0.01) | (pal > 0.01)).astype(np.uint8)
            far = cv2.dilate(person, np.ones((25, 25), np.uint8)) == 0
            near = cv2.dilate(person, np.ones((41, 41), np.uint8)).astype(bool) & \
                ~cv2.dilate(person, np.ones((5, 5), np.uint8)).astype(bool)
            r = dict(i=i)
            for nm, m in (("bg", far), ("ring", near)):
                if m.sum() < 50:
                    continue
                r[f"{nm}_in"] = float(np.abs(lo - plo)[m].mean())
                r[f"{nm}_out"] = float(np.abs(lb - plb)[m].mean())
            rows.append(r)
        prev = (lo, lb, al)
        if i in still_idx:
            t = still_idx[i]
            both = np.vstack([fo, fb])
            if W > 1920:
                both = cv2.resize(both, (W // 2, H), interpolation=cv2.INTER_AREA)
            cv2.imwrite(os.path.join(a.dir, f"{a.name}_before_after_{t:.1f}s.jpg"),
                        cv2.cvtColor(both, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
        if i in strip_idx:
            strip.append(cv2.resize(fb, (640, 360), interpolation=cv2.INTER_AREA))
        i += 1
    if strip:
        g = np.vstack([np.hstack(strip[:3]), np.hstack(strip[3:6])]) if len(strip) == 6 else np.hstack(strip)
        cv2.imwrite(os.path.join(a.dir, f"{a.name}_strip.jpg"), cv2.cvtColor(g, cv2.COLOR_RGB2BGR),
                    [cv2.IMWRITE_JPEG_QUALITY, 88])
    summ = dict(name=a.name, frames=i)
    for k in ("bg_in", "bg_out", "ring_in", "ring_out"):
        v = np.array([r[k] for r in rows if k in r])
        if v.size:
            summ[k] = dict(mean=round(float(v.mean()), 3), p95=round(float(np.percentile(v, 95)), 3),
                           max=round(float(v.max()), 3))
    for nm in ("bg", "ring"):
        vo = np.array([r.get(f"{nm}_out", np.nan) for r in rows])
        if np.isfinite(vo).sum() > 5:
            med = np.nanmedian(vo)
            summ[f"{nm}_spikes"] = [int(rows[j]["i"]) for j in np.flatnonzero(vo > max(3 * med, med + 1.0))]
    json.dump(dict(summary=summ, frames=rows), open(os.path.join(a.dir, f"{a.name}_flicker.json"), "w"), indent=1)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
