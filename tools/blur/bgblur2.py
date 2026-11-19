#!/usr/bin/env python3
"""bgblur2.py - background blur v2: same lens model as bgblur.py (clean plate,
Depth Anything depth, layered normalised disc blur, grain), but a rebuilt
matte + compositing stage that fixes the "outline around the moving speaker":

  * matte from matte2.py (SAM 2.1 track + motion-adaptive trimap + ViTMatte,
    flow-compensated temporal smoothing) instead of RVM + EMA + MediaPipe core.
    The speaker's swivel chair can be tracked as foreground too.
  * composite = alpha*F + (1-alpha)*blurred_bg with F = decontaminated
    foreground (pymatting estimate_foreground_ml, MIT). The soft edge never
    shows the sharp original background any more.
  * fill / no-spread mask = alpha support dilated by the speaker's motion, so
    motion-blur tails never smear into the background blur.
  * motion-eased blur: the background CoC eases to (1 - ease) during fast
    motion (fast attack, ~0.6 s release), like a focus puller losing a subject.
  * soft light wrap of the blurred background over the outer matte edge.

Usage (normally via matte2.py first, then this):
  matte2.py --in SRC --start S --end E --out MATTE_DIR --keep keep/CLIP.json
  bgblur2.py --in SRC --start S --end E --matte MATTE_DIR --out out.mp4 \
      --size 2304x1296 --keep-polygon keep/CLIP.json
Debug: --debug-dir D writes orig/alpha/fill/comp JPEGs per frame (1080p).
"""
import argparse, json, os, subprocess, sys, time, threading, queue
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bgblur as B
from bgblur import smoothstep, push_pull, affine_fit, log

NT = B.NTHREADS


class Renderer2(B.Renderer):
    def render2(self, frame, a, coc, speed_px):
        """frame uint8 RGB (H,W,3); a float32 alpha (H,W); speed_px = speaker
        motion in output px/frame."""
        H, W = self.H, self.W
        if coc is not getattr(self, "coc_cur", None):
            self.prepare(coc)
        ff = frame.astype(np.float32)
        # 1. fill / no-spread region: alpha support, dilated by base + motion
        r = max(3, int(H / 160)) + int(min(0.75 * speed_px, H / 25))
        sup = (a > 0.004).astype(np.uint8)
        amd = cv2.dilate(sup, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
        am_full = cv2.max(cv2.GaussianBlur(amd.astype(np.float32), (0, 0), max(1.0, r / 3)), a)
        am = cv2.multiply(am_full, self.fill_gate)
        keep = 1.0 - cv2.subtract(am_full, am)
        s = 16
        ws, hs = W // s, H // s
        bgw = cv2.resize(1 - am_full, (ws, hs), interpolation=cv2.INTER_AREA)[..., None]
        fs = cv2.resize(frame, (ws, hs), interpolation=cv2.INTER_AREA).astype(np.float32)
        sig = ws / 12
        num = cv2.GaussianBlur(fs * bgw, (0, 0), sig)
        den = cv2.GaussianBlur(self.plate_s * bgw, (0, 0), sig)
        gain = cv2.resize(np.clip((num + 2) / (den + 2), 0.6, 1.6).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
        plate_adj = cv2.multiply(self.plate_f, gain)
        if self.conf is not None and self.conf.min() < 0.99:
            q = 8
            sm = cv2.resize(ff, (W // q, H // q), interpolation=cv2.INTER_AREA)
            wq = cv2.resize(1 - cv2.dilate(am_full, np.ones((9, 9), np.uint8)), (W // q, H // q), interpolation=cv2.INTER_AREA)
            pp = cv2.resize(push_pull(sm, smoothstep(0.5, 1.0, wq).astype(np.float32), 5), (W, H), interpolation=cv2.INTER_LINEAR)
            plate_adj = plate_adj * self.conf + pp * (1 - self.conf)
        am3 = cv2.merge([am, am, am])
        fill = cv2.add(ff, cv2.multiply(cv2.subtract(plate_adj, ff), am3))
        self.dbg_fill = am_full

        # 2-3. lens blur of the filled background (as v1)
        lin = cv2.multiply(fill, fill, scale=1 / 65025.0)
        y = cv2.transform(lin, np.array([[0.2126, 0.7152, 0.0722]], np.float32))
        boost = 1.0 + self.args.bloom * 6.0 * smoothstep(0.55, 0.95, y)
        lin_b = cv2.multiply(lin, cv2.merge([boost, boost, boost]))
        out = cv2.multiply(lin, self.w_lin3)
        for d in self.lv:
            m1 = cv2.multiply(d["m1"], keep)
            src = cv2.multiply(lin_b, cv2.merge([m1, m1, m1]))
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
            Bk = cv2.add(cv2.multiply(num, cv2.merge([inv, inv, inv])), cv2.multiply(ls, cv2.merge([1 - k] * 3)))
            if d["ds"] > 1:
                Bk = cv2.resize(Bk, (W, H), interpolation=cv2.INTER_LINEAR)
            w1 = d["w1"]
            out = cv2.add(out, cv2.multiply(Bk, cv2.merge([w1, w1, w1])))
        sh = 0.85
        over = np.maximum(out - sh, 0)
        out = out - over + (1 - sh) * np.tanh(over * (1 / (1 - sh)))
        bg = cv2.sqrt(np.maximum(out, 0)) * 255.0
        if self.args.grain > 0:
            g = self.grain[self.rng.integers(len(self.grain))]
            ox, oy = self.rng.integers(0, 64, 2)
            g = g[oy:oy + H, ox:ox + W]
            lum = cv2.transform(bg, np.array([[1 / 765.0] * 3], np.float32))
            amt = self.grain_amt * (0.6 + 1.6 * lum * (1 - lum))
            gg = cv2.multiply(g, amt)
            bg = cv2.add(bg, cv2.merge([gg, gg, gg]))

        # 4. decontaminated foreground in the soft band (pymatting, MIT)
        fg = ff
        band = (a > 0.004) & (a < 0.996)
        if band.any():
            from pymatting import estimate_foreground_ml
            ys, xs = np.nonzero(sup)
            mg = 16
            y0, y1 = max(0, ys.min() - mg), min(H, ys.max() + mg + 1)
            x0, x1 = max(0, xs.min() - mg), min(W, xs.max() + mg + 1)
            ci = ff[y0:y1, x0:x1].astype(np.float64) / 255.0
            ca = a[y0:y1, x0:x1].astype(np.float64)
            Fc = estimate_foreground_ml(ci, ca, n_big_iterations=2, n_small_iterations=1, regularization=1e-5)
            fg = ff.copy()
            bb = band[y0:y1, x0:x1]
            fg[y0:y1, x0:x1][bb] = (np.clip(Fc, 0, 1) * 255.0).astype(np.float32)[bb]
        # 5. composite + light wrap on the outer edge
        a3 = cv2.merge([a, a, a])
        res = cv2.add(bg, cv2.multiply(cv2.subtract(fg, bg), a3))
        if self.args.wrap > 0:
            inner = cv2.GaussianBlur(a, (0, 0), max(1.0, 2.5 * H / 1080))
            wr = np.clip(a * (1 - inner) * 2.0, 0, 1) * self.args.wrap
            wr = wr * smoothstep(0.5, 3.0, self.coc_cur)     # only where the bg is really blurred
            res = cv2.add(res, cv2.multiply(cv2.subtract(bg, res), cv2.merge([wr, wr, wr])))
        self.dbg_bg = bg
        return np.clip(res, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--matte", required=True, help="matte2.py output dir for exactly this --start/--end")
    ap.add_argument("--start", type=float, required=True)
    ap.add_argument("--end", type=float, required=True)
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--strength", type=float, default=1.0)
    ap.add_argument("--keep-polygon", default=None)
    ap.add_argument("--focus", type=float, default=None)
    ap.add_argument("--focus-every", type=float, default=0.0, help="0 = fixed focus at the clip cache focus (no breathing)")
    ap.add_argument("--dof", type=float, default=0.04)
    ap.add_argument("--falloff", type=float, default=0.7)
    ap.add_argument("--near", type=float, default=0.25)
    ap.add_argument("--bloom", type=float, default=0.35)
    ap.add_argument("--grain", type=float, default=1.0)
    ap.add_argument("--wrap", type=float, default=0.15, help="light wrap amount on the matte edge")
    ap.add_argument("--ease", type=float, default=0.5, help="blur reduction at full motion (0 = off)")
    ap.add_argument("--ease-lo", type=float, default=6.0, help="speed (px/frame @1080p) where easing starts")
    ap.add_argument("--ease-hi", type=float, default=22.0, help="speed where easing is full")
    ap.add_argument("--plate-range", default=None)
    ap.add_argument("--crf", type=int, default=14)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--debug-dir", default=None)
    ap.add_argument("--debug-crop", default=None, help="only dump frames in i0,i1")
    args = ap.parse_args()
    args.depth_update = 0.0

    info = B.probe(args.inp)
    W, H = B.parse_size(args.size)
    fps = args.fps
    mm = json.load(open(os.path.join(args.matte, "meta.json")))
    speeds = np.array(mm["speeds"], np.float32)
    if args.plate_range:
        t0, t1 = (float(x) for x in args.plate_range.split(","))
        plate, disp, meta = B.build_cache(args.inp, info, t0=t0, t1=t1)
    else:
        plate, disp, meta = B.build_cache(args.inp, info)
    rend = Renderer2(plate, disp, meta, W, H, None, (info["w"], info["h"]), args)
    log(f"v2 levels={['%.1f' % l for l in rend.levels]} R={rend.R:.1f}px focus={rend.focus_n:.3f}")
    depth = B.Depth(short=392) if (args.focus is None and args.focus_every > 0) else None
    every = max(1, int(round(args.focus_every * fps)))

    # motion easing curve (fast attack, slow release), computed up front: no lag
    raw = args.ease * smoothstep(args.ease_lo, args.ease_hi, speeds)
    # look-ahead max over 4 frames so the blur is already gentler when a fast move starts
    la = np.array([raw[max(0, i - 2):i + 5].max() if len(raw) else 0 for i in range(len(raw))], np.float32)
    ease = np.zeros_like(la)
    e = 0.0
    for i, v in enumerate(la):
        e = v if v > e else e + (v - e) * (1.0 / (0.6 * fps) * 3.0)
        ease[i] = e
    # quantise so the CoC map (and its prepare()) changes only in small steps
    ease = np.round(ease / 0.025) * 0.025

    dur = args.end - args.start
    reader = B.Reader(args.inp, args.start, dur, None, W, H, fps=fps)
    writer = B.Writer(args.out, W, H, fps, None, crf=args.crf, preset=args.preset)
    q_in = queue.Queue(maxsize=3)

    def t_read():
        i = 0
        while True:
            fr = reader.read()
            if fr is None or i >= mm["n"]:
                q_in.put(None)
                return
            ap_ = os.path.join(args.matte, f"a_{i:06d}.png")
            a = cv2.imread(ap_, 0).astype(np.float32) / 255.0
            if a.shape != (H, W):
                a = np.clip(cv2.resize(a, (W, H), interpolation=cv2.INTER_CUBIC), 0, 1)
            q_in.put((i, fr, a))
            i += 1

    threading.Thread(target=t_read, daemon=True).start()
    if args.debug_dir:
        os.makedirs(args.debug_dir, exist_ok=True)
    dsel = tuple(int(x) for x in args.debug_crop.split(",")) if args.debug_crop else (0, 10 ** 9)
    target = rend.focus_n
    base_focus_coc = None
    cur_key = None
    coc = None
    tic = time.time()
    n = 0
    while True:
        it = q_in.get()
        if it is None:
            break
        i, fr, a = it
        if depth is not None and i % every == 0:
            core = cv2.erode((a > 0.95).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
            if 0.01 < core.mean() < 0.22:
                hw = (W * 270 // H // 2 * 2, 270)
                df = depth(cv2.resize(fr, hw, interpolation=cv2.INTER_AREA))
                c2 = cv2.erode(cv2.resize(core.astype(np.uint8), hw, interpolation=cv2.INTER_NEAREST), np.ones((5, 5), np.uint8)).astype(bool)
                bgm = cv2.resize((a < 0.01).astype(np.uint8), hw, interpolation=cv2.INTER_NEAREST).astype(bool)
                dref = cv2.resize(rend.dn, hw, interpolation=cv2.INTER_AREA)
                aa, bb = affine_fit(df, dref, bgm)
                if c2.sum() > 100 and aa > 0:
                    nt = float(np.clip(aa * np.median(df[c2]) + bb, 0.1, 0.95))
                    if abs(nt - target) > 0.03:
                        target = nt
        if i == 0:
            rend.focus_cur = target
        else:
            rend.focus_cur += (target - rend.focus_cur) * min(1.0, 1.25 / fps)
        key = (round(rend.focus_cur / 0.004), float(ease[i]))
        if key != cur_key:
            cur_key = key
            coc = (rend.coc() * (1.0 - float(ease[i]))).astype(np.float32)
        sp_out = float(speeds[i]) * H / 1080.0
        out = rend.render2(fr, a, coc, sp_out)
        writer.write(out)
        if args.debug_dir and dsel[0] <= i <= dsel[1]:
            def sv(name, img):
                if img.ndim == 2:
                    img = (np.clip(img, 0, 1) * 255).astype(np.uint8)
                else:
                    img = cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
                if img.shape[0] != 1080:
                    img = cv2.resize(img, (1920, 1080), interpolation=cv2.INTER_AREA)
                cv2.imwrite(os.path.join(args.debug_dir, f"{name}_{i:04d}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
            sv("orig", fr); sv("alpha", a); sv("fill", rend.dbg_fill); sv("comp", out)
        n += 1
        if n % 30 == 0:
            log(f"{n} frames {(time.time()-tic)/n:.2f}s/frame ease={ease[i]:.2f} focus={rend.focus_cur:.3f}")
    reader.close()
    writer.close()
    log(f"done {n} frames in {time.time()-tic:.0f}s")
    os._exit(0)


if __name__ == "__main__":
    main()
