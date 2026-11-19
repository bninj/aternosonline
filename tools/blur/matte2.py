#!/usr/bin/env python3
"""matte2.py - licence-clean, temporally stable person (+ optional prop) alpha
matte for a clip range, CPU only.

  1. SAM 2.1 Hiera-Tiny video tracker (Apache-2.0), streamed forward AND
     backward from a prompt frame (handles roll-ins from the frame edge).
     Prompt = box/points of the person from MediaPipe (Apache-2.0) on the
     prompt frame, plus optional extra objects (e.g. the swivel chair the
     speaker rides in on) from the keep JSON "track" list.
  2. Motion-adaptive trimap: the unknown band around the SAM mask is widened
     per pixel by the optical-flow magnitude (DIS), so motion-blurred limbs
     become partial alpha instead of a hard cut.
  3. ViTMatte-S (hustvl/vitmatte-small-composition-1k, Apache-2.0 weights,
     MIT code) on a person-ROI crop -> alpha.
  4. Motion-compensated temporal smoothing inside the band only (flow-warped
     previous alpha, weight 0.5*exp(-|flow|/2px): smooth when still, no lag
     when moving).

Output: DIR/a_000000.png (8-bit alpha at --matte-size), DIR/meta.json with per
frame speed (px/frame at 1080p, p90 of flow on the person). Frame i is the
i-th frame of ffmpeg's `-ss start -t (end-start)` at --fps (same decode as
bgblur2.py), so the two line up exactly.

keep JSON "track" entries (all optional):
  {"track": [{"name": "swivel chair", "t": 211.47,
              "box": [x0,y0,x1,y1], "points": [[x,y],...]}]}   # normalised
  "prompt_t" (top level): time of the prompt frame (default: auto).
"""
import argparse, json, os, sys, time
import numpy as np
import cv2

os.environ.setdefault("HF_HOME", os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "hf"))
NT = int(os.environ.get("BGBLUR_THREADS", "2"))
cv2.setNumThreads(NT)
import torch
torch.set_num_threads(NT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bgblur as B

SAM_ID = "facebook/sam2.1-hiera-tiny"
VM_ID = "hustvl/vitmatte-small-composition-1k"


def log(*a):
    print("[matte2]", *a, file=sys.stderr, flush=True)


def read_range(src, start, dur, W, H, fps):
    r = B.Reader(src, start, dur, None, W, H, fps=fps)
    while True:
        f = r.read()
        if f is None:
            break
        yield f
    r.close()


# ----------------------------------------------------------------- SAM 2 track
class Tracker:
    def __init__(self):
        from transformers import Sam2VideoModel, Sam2VideoProcessor
        self.model = Sam2VideoModel.from_pretrained(SAM_ID).eval()
        self.proc = Sam2VideoProcessor.from_pretrained(SAM_ID)

    def run(self, frames, prompts):
        """frames: list of RGB (h,w,3) in stream order; prompts: list of dicts
        (obj boxes/points in pixel coords of frames) applied on frames[0].
        Returns list of float16 union probability masks (h,w)."""
        proc, model = self.proc, self.model
        sess = proc.init_video_session(inference_device="cpu", dtype=torch.float32)
        out = []
        ids = list(range(1, len(prompts) + 1))
        for k, im in enumerate(frames):
            inp = proc(images=im, device="cpu", return_tensors="pt")
            if k == 0:
                for oid, p in zip(ids, prompts):
                    kw = {}
                    if p.get("box") is not None:
                        kw["input_boxes"] = [[list(map(float, p["box"]))]]
                    if p.get("points"):
                        kw["input_points"] = [[[list(map(float, q)) for q in p["points"]]]]
                        kw["input_labels"] = [[[1] * len(p["points"])]]
                    proc.add_inputs_to_inference_session(inference_session=sess, frame_idx=0, obj_ids=oid,
                                                         original_size=inp.original_sizes[0], **kw)
                sess.obj_with_new_inputs = list(ids)   # HF overwrites this per call
            with torch.inference_mode():
                o = model(inference_session=sess, frame_idx=k, frame=inp.pixel_values[0])
            m = proc.post_process_masks([o.pred_masks], original_sizes=inp.original_sizes, binarize=False)[0]
            m = torch.sigmoid(m[:, 0]).amax(0).numpy().astype(np.float16)
            out.append(m)
            # prune: keep only what the memory bank needs (7 recent + cond frame)
            for f in list(sess.processed_frames):
                if f < k:
                    del sess.processed_frames[f]
            for od in sess.output_dict_per_obj.values():
                nc = od["non_cond_frame_outputs"]
                for f in list(nc):
                    if f < k - 8:
                        del nc[f]
            if k % 30 == 0:
                log(f"  sam {k}/{len(frames)}")
        return out


def person_prompt(segm, im):
    """box + 3 interior points of the person from MediaPipe (im = SAM-res RGB)."""
    p = segm(im)
    m = (p > 0.5).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    if n <= 1:
        return None, 0.0
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    m = (lab == k).astype(np.uint8)
    x, y, w, h = st[k, :4]
    core = cv2.erode(m, np.ones((9, 9), np.uint8))
    ys, xs = np.nonzero(core if core.any() else m)
    pts = []
    for q in (0.2, 0.45, 0.7):           # head/torso/legs along the body
        yy = np.quantile(ys, q)
        sel = np.abs(ys - yy) < 4
        if sel.any():
            pts.append([float(np.median(xs[sel])), float(yy)])
    pad = 0.03 * im.shape[0]
    box = [max(0, x - pad), max(0, y - pad), min(im.shape[1] - 1, x + w + pad), min(im.shape[0] - 1, y + h + pad)]
    return dict(box=box, points=pts), float(m.mean())


# ------------------------------------------------------------------ ViTMatte
class Matter:
    def __init__(self):
        from transformers import VitMatteForImageMatting
        self.m = VitMatteForImageMatting.from_pretrained(VM_ID).eval()

    def __call__(self, rgb, tri):
        h, w = tri.shape
        ph, pw = (32 - h % 32) % 32, (32 - w % 32) % 32
        x = np.concatenate([(rgb.astype(np.float32) / 127.5 - 1.0), (tri.astype(np.float32) / 255)[..., None]], -1)
        x = np.pad(x, ((0, ph), (0, pw), (0, 0)), mode="reflect")
        t = torch.from_numpy(np.ascontiguousarray(x.transpose(2, 0, 1)))[None]
        with torch.inference_mode():
            a = self.m(pixel_values=t).alphas[0, 0, :h, :w].numpy()
        return a


def disk(r):
    r = max(1, int(round(r)))
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def adaptive_band(b, rad, radii):
    """per-pixel variable dilation/erosion of binary mask b by radius map rad."""
    out_d = cv2.dilate(b, disk(radii[0]))
    out_e = cv2.erode(b, disk(max(1, radii[0] // 3)))
    for r in radii[1:]:
        need = (rad >= r).astype(np.uint8)
        if not need.any():
            break
        out_d |= cv2.dilate(b, disk(r)) & need
        out_e &= cv2.erode(b, disk(r * 0.6)) | (1 - need)
    return out_d, out_e


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--start", type=float, required=True)
    ap.add_argument("--end", type=float, required=True)
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--keep", default=None, help="keep JSON (uses its optional 'track' list / 'prompt_t')")
    ap.add_argument("--prompt-t", type=float, default=None)
    ap.add_argument("--matte-size", default="1920x1080")
    ap.add_argument("--vm-scale", type=float, default=0.5, help="ViTMatte crop scale vs matte size")
    ap.add_argument("--debug", action="store_true", help="also save SAM masks + trimaps")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    MW, MH = map(int, args.matte_size.split("x"))
    SW, SH = 960, 540
    dur = args.end - args.start
    tic = time.time()

    # ---- pass A: SAM-res frames into RAM
    small = list(read_range(args.inp, args.start, dur, SW, SH, args.fps))
    N = len(small)
    log(f"{N} frames decoded ({time.time()-tic:.0f}s)")
    keep = json.load(open(args.keep)) if args.keep and os.path.exists(args.keep) else {}
    tracks = [t for t in keep.get("track", []) if args.start - 0.05 <= t["t"] <= args.end + 0.05]
    segm = B.Segmenter()
    pt = args.prompt_t if args.prompt_t is not None else (tracks[0]["t"] if tracks else None)
    if pt is not None:
        p = int(np.clip(round((pt - args.start) * args.fps), 0, N - 1))
        pp, _ = person_prompt(segm, small[p])
    else:   # auto: largest person not cut by the frame edge
        best = (-1, 0, None)
        for i in range(0, N, 5):
            pr, area = person_prompt(segm, small[i])
            if pr is None:
                continue
            x0, y0, x1, y1 = pr["box"]
            edge = (x0 < 3) or (x1 > SW - 4)
            score = area * (0.3 if edge else 1.0)
            if score > best[0]:
                best = (score, i, pr)
        _, p, pp = best
    prompts = [pp] if pp else []
    for t in tracks:
        bx = t.get("box")
        prompts.append(dict(box=[bx[0] * SW, bx[1] * SH, bx[2] * SW, bx[3] * SH] if bx else None,
                            points=[[q[0] * SW, q[1] * SH] for q in t.get("points", [])]))
    log(f"prompt frame {p} ({args.start + p / args.fps:.2f}s), {len(prompts)} objects")
    tr = Tracker()
    t1 = time.time()
    fwd = tr.run(small[p:], prompts)
    bwd = tr.run(small[:p + 1][::-1], prompts) if p > 0 else [None]
    sam = bwd[::-1][:-1] + fwd if p > 0 else fwd
    del small, fwd, bwd
    sam_s = (time.time() - t1) / max(1, N)
    log(f"SAM done {sam_s:.2f}s/frame")

    # ---- pass B: trimap + ViTMatte + temporal
    vm = Matter()
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    FW, FH = 480, 270
    fsc = MH / FH                          # flow px -> matte px
    k1080 = 1080.0 / MH
    prev_g, prev_a = None, None
    speeds = []
    radii = [int(round(r * MH / 1080)) for r in (10, 16, 24, 34, 46, 60)]
    gx, gy = np.meshgrid(np.arange(MW, dtype=np.float32), np.arange(MH, dtype=np.float32))
    tvm = 0.0
    for i, fr in enumerate(read_range(args.inp, args.start, dur, MW, MH, args.fps)):
        if i >= N:
            break
        g = cv2.cvtColor(cv2.resize(fr, (FW, FH), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
        m = cv2.resize(sam[i].astype(np.float32), (MW, MH), interpolation=cv2.INTER_LINEAR)
        b = (m > 0.5).astype(np.uint8)
        if prev_g is not None:
            flow_b = dis.calc(g, prev_g, None)          # cur -> prev (for warping prev alpha)
            mag = np.sqrt((flow_b ** 2).sum(-1)) * fsc
        else:
            flow_b, mag = None, np.zeros((FH, FW), np.float32)
        magm = cv2.resize(mag, (MW, MH), interpolation=cv2.INTER_LINEAR)
        pm = cv2.resize(b, (FW, FH), interpolation=cv2.INTER_NEAREST).astype(bool)
        sp = float(np.percentile(mag[pm], 90)) * k1080 if pm.sum() > 50 else 0.0
        speeds.append(sp)
        if not b.any():
            a = np.zeros((MH, MW), np.float32)
        else:
            # radius map: base + |flow| (spread so the trailing side is covered too)
            rad = radii[0] + 1.0 * cv2.dilate(magm, disk(radii[2]))
            outer, inner = adaptive_band(b, rad, radii)
            tri = np.where(inner > 0, 255, np.where(outer > 0, 128, 0)).astype(np.uint8)
            ys, xs = np.nonzero(outer)
            mg = 24
            x0, y0 = max(0, xs.min() - mg), max(0, ys.min() - mg)
            x1, y1 = min(MW, xs.max() + mg + 1), min(MH, ys.max() + mg + 1)
            ci, ct = fr[y0:y1, x0:x1], tri[y0:y1, x0:x1]
            s = args.vm_scale
            if s != 1:
                ci = cv2.resize(ci, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
                ct = cv2.resize(ct, (ci.shape[1], ci.shape[0]), interpolation=cv2.INTER_NEAREST)
            t2 = time.time()
            ac = vm(ci, ct)
            tvm += time.time() - t2
            if s != 1:
                ac = cv2.resize(ac, (x1 - x0, y1 - y0), interpolation=cv2.INTER_CUBIC)
                # edge-aware upsampling with the full-res crop as guide
                gg = cv2.cvtColor(fr[y0:y1, x0:x1], cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
                ac = cv2.ximgproc.guidedFilter(gg, ac.astype(np.float32), int(round(1.5 / s)), 1e-4)
            a = np.zeros((MH, MW), np.float32)
            a[y0:y1, x0:x1] = np.clip(ac, 0, 1)
            a[inner > 0] = 1.0
            a[outer == 0] = 0.0
            # temporal: flow-warped previous alpha, only in the band, no lag when moving
            if prev_a is not None and flow_b is not None:
                fu = cv2.resize(flow_b, (MW, MH), interpolation=cv2.INTER_LINEAR) * fsc
                wa = cv2.remap(prev_a, gx + fu[..., 0], gy + fu[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                w = 0.5 * np.exp(-magm / 2.0)
                band = ((outer > 0) & (inner == 0)).astype(np.float32)
                w = w * band
                a = a * (1 - w) + wa * w
        cv2.imwrite(os.path.join(args.out, f"a_{i:06d}.png"), (a * 255 + 0.5).astype(np.uint8))
        if args.debug:
            cv2.imwrite(os.path.join(args.out, f"sam_{i:06d}.png"), (cv2.resize(sam[i].astype(np.float32), (SW, SH)) * 255).astype(np.uint8))
            if b.any():
                cv2.imwrite(os.path.join(args.out, f"tri_{i:06d}.png"), cv2.resize(tri, (SW, SH), interpolation=cv2.INTER_NEAREST))
        prev_g, prev_a = g, a
        if i % 30 == 0:
            log(f"  matte {i}/{N}  vitmatte {tvm/(i+1):.2f}s/frame  speed {sp:.1f}")
    meta = dict(src=os.path.abspath(args.inp), start=args.start, end=args.end, fps=args.fps, n=N,
                matte_size=[MW, MH], prompt_frame=p, speeds=speeds, sam_s_per_frame=sam_s,
                vitmatte_s_per_frame=tvm / max(1, N), total_s=time.time() - tic)
    json.dump(meta, open(os.path.join(args.out, "meta.json"), "w"))
    log(f"done {N} frames in {time.time()-tic:.0f}s")
    os._exit(0)


if __name__ == "__main__":
    main()
