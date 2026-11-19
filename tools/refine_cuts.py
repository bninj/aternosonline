#!/usr/bin/env python3
"""Turn picked attempts into a frame-accurate EDL with cut points refined on the audio (not on Whisper word times).

usage:
  refine_cuts.py --takes takes.json --pick 1:0 2:1 3:1 4:1 --out edl.json [--lead 0.10 --tail 0.18]
                 [--max-pause 0.35 --keep-pause 0.25] [--cut-fillers] [--run-gap 0.8]
  --pick UNIT:IDX uses analyze_takes.py's attempt index; --pick suggested takes the advisory picks for every unit.
  A pick may also be CLIP:START-END (source seconds) for a hand-chosen range.

Rules (sources: griffinwooldridge/talking-head-editor cut.py, YildizDikme/claude-video-edit reference/audio.md,
kurbaitaev/ghost-editor take-selection.md + SKILL.md, jacobksamuelson/talking-head-video; all MIT, re-implemented):
  * picks said back to back in the same clip (gap <= --run-gap) stay ONE segment (a run: one cut instead of several);
  * inside a segment, pauses > --max-pause (Whisper gaps or audio silences) are shrunk to --keep-pause
    (tail 0.15 + lead 0.10); fillers are cut out only with --cut-fillers (default: pick filler-free takes instead);
  * Whisper word ends run 0.1-0.4 s early, so each out point walks forward on 10 ms levels until 30 ms sit below
    Q = floor + 12 dB (clamped -56..-40) in BOTH broadband and >2.5 kHz (sibilants), then looks 250 ms further for a
    dip-then-resume (>= 30 ms above Q+4: clipped -ence/-ts/-s); words ending in t/k/p/ed also keep a 10-120 ms release
    burst found within 150 ms; never past the next spoken word;
  * each in point finds the true onset and walks back up to 150 ms over breathy h-/f-/s-/th- onsets;
  * pad lead 100 ms / tail 180 ms, never into neighbouring sound; round frames OUTWARD on the source's real frame PTS
    (iPhone 29.97 fps drifts up to 0.16 s over 12 min against frame/30); audio is cut at the same snapped times.
"""
import argparse, json, math, re, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audiolib as AL

FILLERS = {"um", "uh", "er", "ah", "erm", "hmm", "mm", "uhm", "umm", "mhm", "eh"}
H = AL.HOP


def nrm(w): return re.sub(r"[^0-9a-z']+", "", w.lower())


class Refiner:
    def __init__(self, env, words):
        self.E = env; self.W = words   # whole-clip word list (for neighbour limits)

    def true_onset(self, s, e):
        E = self.E; t = s
        while t < min(e, s + 0.3) and E.quiet(t): t += H            # whisper start early: move to the sound
        t0 = t
        while t - H > 0 and t > t0 - 0.15 and not E.quiet(t - H): t -= H   # soft onset walk-back (<= 150 ms)
        return t

    def true_end(self, s, e, word, limit):
        E = self.E; t = e
        while t > max(s, e - 0.3) and E.quiet(t - H): t -= H       # whisper end late (in silence): back to the sound
        while True:                                               # GW tail walker
            while t < limit and not all(E.quiet(t + k * H) for k in range(3)): t += H
            nxt = None
            for k in range(25):                                   # 250 ms look-ahead for dip-then-resume
                u = t + k * H
                if u >= limit - 0.05: break
                if all(E.loud(u + j * H) for j in range(3)): nxt = u; break
            if nxt is None: break
            t = nxt
        if re.search(r"(t|k|p|ed|ts|ks|ps)$", nrm(word)):           # YD release-burst rule
            k = 0
            while k < 15 and t + k * H < limit - 0.03:
                if E.loud(t + k * H, 0):
                    j = k
                    while j < 12 + k and E.loud(t + j * H, 0): j += 1
                    if (j - k) * H <= 0.12 and all(E.quiet(t + (j + m) * H) for m in range(3)):
                        t = t + j * H
                    break
                k += 1
        return min(t, limit)

    def next_sound(self, t, limit):
        """first time after t where >= 30 ms is loud (the next sound, breath or word)"""
        E = self.E
        while t < limit:
            if all(E.loud(t + j * H) for j in range(3)): return t
            t += H
        return limit

    def prev_sound(self, t, limit):
        E = self.E
        while t > limit:
            if all(E.loud(t - (j + 1) * H) for j in range(3)): return t
            t -= H
        return limit

    def piece(self, ws, lead, tail):
        W = self.W; E = self.E
        i0 = W.index(ws[0]); i1 = W.index(ws[-1])
        nxt_w = W[i1 + 1]["s"] - 0.02 if i1 + 1 < len(W) else E.T
        prv_w = W[i0 - 1]["e"] + 0.02 if i0 > 0 else 0.0
        on = self.true_onset(ws[0]["s"], ws[-1]["e"])
        en = self.true_end(ws[0]["s"], ws[-1]["e"], ws[-1]["w"], max(nxt_w, ws[-1]["e"] + 0.03))
        lim_out = min(nxt_w + 0.02, self.next_sound(en + 0.03, E.T) - 0.03)
        lim_in = max(prv_w - 0.02, self.prev_sound(on - 0.03, 0.0) + 0.03) if i0 > 0 else 0.0
        a = max(on - lead, min(lim_in, on), 0.0); b = min(en + tail, max(lim_out, en))
        return {"a": a, "b": b, "onset": on, "end": en, "wa": ws[0]["s"], "wb": ws[-1]["e"],
                "text": " ".join(w["w"] for w in ws)}

    def audio_splits(self, a, b, max_pause):
        """silences > max_pause inside [a, b] that Whisper hid by stretching words"""
        E = self.E; out = []; t = a; run0 = None
        while t < b:
            if E.quiet(t): run0 = t if run0 is None else run0
            else:
                if run0 is not None and t - run0 > max_pause: out.append((run0, t))
                run0 = None
            t += H
        return out


def snap(a, b, F, fps_grid=30.0):
    if len(F):
        d = float(np.median(np.diff(F))) if len(F) > 1 else 1 / 30
        i = int(np.searchsorted(F, a + 1e-6, "right") - 1); i = max(i, 0)
        j = int(np.searchsorted(F, b - 1e-6, "left"))
        fa = float(F[i]); fb = float(F[j]) if j < len(F) else float(F[-1] + d)
        return fa, fb, j - i
    fa, fb = math.floor(a * fps_grid) / fps_grid, math.ceil(b * fps_grid) / fps_grid
    return fa, fb, round((fb - fa) * fps_grid)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--takes", required=True); ap.add_argument("--pick", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lead", type=float, default=0.10); ap.add_argument("--tail", type=float, default=0.18)
    ap.add_argument("--max-pause", type=float, default=0.35); ap.add_argument("--keep-pause", type=float, default=0.25)
    ap.add_argument("--run-gap", type=float, default=0.8); ap.add_argument("--cut-fillers", action="store_true")
    a = ap.parse_args()
    T = json.load(open(a.takes)); units = {u["id"]: u for u in T["units"]}; clips = T["clips"]
    picks = []
    if a.pick == ["suggested"]:
        a.pick = [f"{uid}:{v['attempt']}" for uid, v in T["suggested"].items() if v["attempt"] is not None]
    for p in a.pick:
        k, v = p.split(":", 1)
        if k in units:
            x = units[k]["attempts"][int(v)]
            picks.append({"clip": x["clip"], "words": x["words"], "label": f"{k}:{v}", "a": x["a"], "b": x["b"]})
        elif k in clips:
            s, e = map(float, v.split("-"))
            picks.append({"clip": k, "words": None, "label": p, "a": s, "b": e})
        else:
            sys.exit(f"unknown unit/clip in --pick {p}")
    # group back-to-back picks of one clip into segments (runs)
    segs = []
    for p in picks:
        if segs and segs[-1]["clip"] == p["clip"] and 0 <= p["a"] - segs[-1]["b"] <= a.run_gap and p["words"] and segs[-1]["words"]:
            segs[-1]["words"] += p["words"]; segs[-1]["b"] = p["b"]; segs[-1]["label"] += "+" + p["label"]
        else:
            segs.append(dict(p, words=list(p["words"]) if p["words"] else None))
    cache = {}
    edl, report, rec = [], [], 0.0
    half = a.keep_pause / 2
    tail_int, lead_int = a.keep_pause * 0.6, a.keep_pause * 0.4    # 0.15 + 0.10
    for si, sg in enumerate(segs):
        c = clips[sg["clip"]]
        if sg["clip"] not in cache:
            tx = json.load(open(c["tx"]))
            W = [w for s in tx["segments"] for w in s["words"] if nrm(w["w"])]
            x = AL.load(c["audio"], 16000)
            F = AL.frame_times(c["src"]) if AL.has_video(c["src"]) else np.zeros(0)
            cache[sg["clip"]] = (Refiner(AL.Env(x, 16000), W), F, AL.video_rate(c["src"]) if len(F) else "30")
        R, F, rate = cache[sg["clip"]]
        if sg["words"] is None:                        # hand range: snap only
            fa, fb, nf = snap(sg["a"], sg["b"], F)
            edl.append({"src": c["src"], "in": round(fa, 6), "out": round(fb, 6), "take": f"{sg['clip']}#{si}", "label": sg["label"], "frames": nf})
            continue
        # map pick words onto the clip word list objects (same dicts by value)
        ws = [next(w for w in R.W if abs(w["s"] - x["s"]) < 1e-6 and w["w"] == x["w"]) for x in sg["words"]]
        groups, cur = [], []
        for w in ws:
            if a.cut_fillers and nrm(w["w"]) in FILLERS:
                if cur: groups.append(cur); cur = []
                continue
            if cur and w["s"] - cur[-1]["e"] > a.max_pause: groups.append(cur); cur = []
            cur.append(w)
        if cur: groups.append(cur)
        pieces = []
        for gi, g in enumerate(groups):
            pc = R.piece(g, a.lead if gi == 0 else lead_int, a.tail if gi == len(groups) - 1 else tail_int)
            # audio silences longer than max_pause that Whisper hid inside the piece
            for q0, q1 in R.audio_splits(pc["onset"] + 0.05, pc["end"] - 0.05, a.max_pause):
                left = dict(pc, b=q0 + tail_int, end=q0); right = dict(pc, a=q1 - lead_int, onset=q1)
                pieces.append(left); pc = right
            pieces.append(pc)
        for pi, pc in enumerate(pieces):
            fa, fb, nf = snap(pc["a"], pc["b"], F)
            if edl and edl[-1]["src"] == c["src"] and edl[-1]["take"] == f"{sg['clip']}#{si}" and fa <= edl[-1]["out"]:
                edl[-1]["out"] = round(max(fb, edl[-1]["out"]), 6); edl[-1]["text"] += " " + pc["text"]; continue
            edl.append({"src": c["src"], "in": round(fa, 6), "out": round(fb, 6), "take": f"{sg['clip']}#{si}",
                        "label": sg["label"], "text": pc["text"], "frames": nf,
                        "join": "start" if not edl else ("pause" if edl[-1]["take"] == f"{sg['clip']}#{si}" else "take")})
            report.append(f"  {sg['label']:>8s} piece {pi}: words {pc['wa']:.2f}-{pc['wb']:.2f} -> audio {pc['onset']:.2f}-{pc['end']:.2f}"
                          f" (end {(pc["end"] - pc["wb"]) * 1000:+.0f} ms) -> cut {fa:.3f}-{fb:.3f} [{nf} fr] | {pc['text'][:60]}")
    total = sum(e["out"] - e["in"] for e in edl)
    json.dump({"fps": cache[segs[0]["clip"]][2] if segs else "30", "clips": edl,
               "params": {k: getattr(a, k) for k in ("lead", "tail", "max_pause", "keep_pause", "run_gap", "cut_fillers")}},
              open(a.out, "w"), indent=1)
    print("\n".join(report))
    print(f"{len(segs)} segments -> {len(edl)} pieces, {total:.2f} s -> {a.out}")


if __name__ == "__main__":
    main()
