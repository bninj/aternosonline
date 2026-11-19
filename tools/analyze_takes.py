#!/usr/bin/env python3
"""Find EVERY attempt at every script sentence (full, partial, false start) in island transcripts and score each one.
Output is a per-script-line table for the LLM editor to make the final pick (with an advisory suggestion).

usage:
  analyze_takes.py --script script.txt --out takes.json [--md takes.md] \\
      --clip A001 --tx tx/A001.json --audio audio/A001.wav [--video proxies/A001.mp4] [--src footage/A001.MOV] \\
      [--clip A002 --tx ... --audio ... ...]
  (--video/--src are per clip, in the same order as --clip; --src = original used by conform, default video/audio)

Matching (re-implemented from kurbaitaev/ghost-editor scripts/takes.py, MIT (c) 2026 kurbaitaev):
  units = script lines split into sentences; a sentence under 4 words merges forward;
  Smith-Waterman on normalised tokens: word sim exact 1.0 / same first 4 chars 0.8 / difflib ratio if >= 0.72;
  match +2*s, mismatch -1, script word missing -0.8, extra spoken word -0.6; repeated best-alignment extraction with
  masking finds every attempt. ATTEMPT if score >= max(3, 0.9 n) and matched >= max(2, 0.3 n); FULL if cov >= 0.9 with
  first and last word. Our addition: a FALSE START tier (starts on the unit's first word, >= 2 matched, score >= 3)
  so restarts that GE's threshold rejects still appear in the table.
Per attempt: coverage, extra/missing words, fillers, largest internal gap, wpm, min/mean word prob, speech level
(70th pct of 10 ms levels > -40 dB), energy (RMS dB std, pitch std in semitones), and face flags against the
attempt's own median pose (turn/glance/side/closed/tilt/big after ghost-editor facescan thresholds), blink count,
sharpness vs clip median. Runs: consecutive script units said back to back (gap <= 0.8 s) are linked.
Selection rules for the editor (GE/GW/YD): meaning over wording; later over earlier all else equal; prefer runs;
never splice half-takes mid-sentence unless on a natural pause; lines never said are reported, not invented.
"""
import argparse, difflib, json, os, re, subprocess
import numpy as np

FILLERS = {"um", "uh", "er", "ah", "erm", "hmm", "mm", "uhm", "umm", "mhm", "eh"}
HERE = os.path.dirname(os.path.abspath(__file__))
SR = 16000


def norm(t):
    return re.sub(r"[^0-9a-z\-]+", "", t.lower()).strip("-")


def toks(s):
    return [x for x in (norm(w) for w in re.split(r"\s+", s)) if x]


def wsim(a, b):
    if a == b: return 1.0
    if len(a) >= 4 and len(b) >= 4 and a[:4] == b[:4]: return 0.8
    r = difflib.SequenceMatcher(None, a, b).ratio()
    return r if r >= 0.72 else 0.0


def units_of(path):
    U, n = [], 0
    for line in open(path):
        line = line.strip()
        if not line: continue
        m = re.match(r"(\d+)\.\s*(.*)", line)
        n, body = (int(m.group(1)), m.group(2)) if m else (n + 1, line)
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])", body)
        merged = []
        for p in parts:
            if merged and len(toks(merged[-1])) < 4: merged[-1] += " " + p
            else: merged.append(p)
        if len(merged) > 1 and len(toks(merged[-1])) < 4: merged[-2] += " " + merged.pop()
        for k, p in enumerate(merged):
            U.append({"id": f"{n}" + ("" if len(merged) == 1 else "abcdefgh"[k]), "line": n, "text": p, "toks": toks(p)})
    return U


def sw(u, w, mask):
    """Smith-Waterman local alignment of unit tokens u against spoken tokens w (masked words score 0)."""
    n, m = len(u), len(w)
    H = np.zeros((n + 1, m + 1)); T = np.zeros((n + 1, m + 1), np.int8)
    S = np.array([[0.0 if mask[j] else wsim(u[i], w[j]) for j in range(m)] for i in range(n)]) if m else np.zeros((n, 0))
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            s = S[i - 1, j - 1]
            d = H[i - 1, j - 1] + (2.0 * s if s > 0 else -1.0)
            up = H[i - 1, j] - 0.8      # script word missing from speech
            lf = H[i, j - 1] - 0.6      # extra spoken word (stumble, repeat, filler)
            b = max(0.0, d, up, lf); H[i, j] = b
            T[i, j] = 0 if b == 0 else (1 if b == d else (2 if b == up else 3))
    i, j = np.unravel_index(np.argmax(H), H.shape); score = float(H[i, j]); path = []
    while i > 0 and j > 0 and T[i, j] != 0:
        t = T[i, j]
        if t == 1: path.append((i - 1, j - 1, S[i - 1, j - 1] > 0)); i -= 1; j -= 1
        elif t == 2: path.append((i - 1, None, False)); i -= 1
        else: path.append((None, j - 1, False)); j -= 1
    return score, path[::-1]


def load_audio(path, sr=SR):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0


def audio_metrics(y, s, e):
    import librosa
    seg = y[int(s * SR):int(e * SR)]
    if len(seg) < SR * 0.4: return {}
    f = seg[:len(seg) // 160 * 160].reshape(-1, 160); L = 20 * np.log10(np.sqrt((f.astype(np.float64) ** 2).mean(1)) + 1e-9)
    sp = L[L > -40]
    m = {"level_db": round(float(np.percentile(sp, 70)), 1) if len(sp) > 5 else None,
         "rms_db_std": round(float(np.std(sp)), 2) if len(sp) > 5 else 0.0}
    f0 = librosa.yin(seg, fmin=70, fmax=400, sr=SR)
    v = f0[(f0 > 70) & (f0 < 400)]
    if len(v) > 10: m["pitch_std_st"] = round(float(np.std(12 * np.log2(v / np.median(v)))), 2)
    return m


# ---------------- face scan (mediapipe FaceLandmarker, whole clip once, ~10 fps, real frame times) -------------
def facescan(video, every_s=0.1, cache=None):
    if cache and os.path.exists(cache):
        return json.load(open(cache))
    import cv2, mediapipe as mp
    from mediapipe.tasks.python import vision, BaseOptions
    lm = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=os.path.join(HERE, "models", "face_landmarker.task")),
        output_face_blendshapes=True, output_facial_transformation_matrixes=True, num_faces=1))
    cap = cv2.VideoCapture(video); rows = []; nxt = 0.0
    while True:
        ok = cap.grab()
        if not ok: break
        t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        if t + 1e-6 < nxt: continue
        nxt = t + every_s
        ok, fr = cap.retrieve()
        if not ok: break
        r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)))
        row = {"t": round(t, 3), "face": bool(r.face_landmarks)}
        if r.face_landmarks:
            H, W = fr.shape[:2]; xs = [p.x * W for p in r.face_landmarks[0]]; ys = [p.y * H for p in r.face_landmarks[0]]
            x0, x1, y0, y1 = int(max(min(xs), 0)), int(min(max(xs), W)), int(max(min(ys), 0)), int(min(max(ys), H))
            g = cv2.cvtColor(fr[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
            R = np.array(r.facial_transformation_matrixes[0])[:3, :3]
            bs = {b.category_name: b.score for b in r.face_blendshapes[0]}
            row.update(yaw=float(np.degrees(np.arcsin(-np.clip(R[2, 0], -1, 1)))),
                       pitch=float(np.degrees(np.arctan2(R[2, 1], R[2, 2]))), roll=float(np.degrees(np.arctan2(R[1, 0], R[0, 0]))),
                       blink=(bs.get("eyeBlinkLeft", 0) + bs.get("eyeBlinkRight", 0)) / 2,
                       down=(bs.get("eyeLookDownLeft", 0) + bs.get("eyeLookDownRight", 0)) / 2,
                       side=max(bs.get("eyeLookOutLeft", 0), bs.get("eyeLookOutRight", 0), bs.get("eyeLookInLeft", 0), bs.get("eyeLookInRight", 0)),
                       sharp=float(cv2.Laplacian(g, cv2.CV_64F).var()) if g.size else 0.0,
                       cx=float(np.mean(xs) / W))
        rows.append(row)
    cap.release(); lm.close()
    if cache: json.dump(rows, open(cache, "w"))
    return rows


def face_flags(rows, a, b, clip_sharp):
    """flags from 0.30 s before the first word to 0.30 s after the last, against the attempt's own median pose."""
    win = [r for r in rows if a - 0.3 <= r["t"] <= b + 0.3]
    if not win: return {}
    fw = [r for r in win if r["face"]]
    out = {"face_ratio": round(len(fw) / len(win), 2)}
    if not fw: return out
    med = {k: float(np.median([r[k] for r in fw])) for k in ("yaw", "pitch", "roll", "down", "side")}
    dt = float(np.median(np.diff([r["t"] for r in win]))) if len(win) > 1 else 0.1
    tests = {"turn": (lambda r: abs(r["yaw"] - med["yaw"]) > 4, 3 / 30),
             "glance": (lambda r: r["down"] - med["down"] > 0.18 and r["blink"] < 0.5, 2 / 30),
             "side": (lambda r: r["side"] - med["side"] > 0.15 and abs(r["yaw"] - med["yaw"]) < 2, 2 / 30),
             "closed": (lambda r: r["blink"] > 0.5, 7 / 30),
             "tilt": (lambda r: abs(r["roll"] - med["roll"]) > 5, 1 / 30),
             "big": (lambda r: abs(r["pitch"] - med["pitch"]) > 9, 1 / 30)}
    ev = []
    for name, (f, mind) in tests.items():
        k = 0
        while k < len(win):
            if win[k]["face"] and f(win[k]):
                j = k
                while j + 1 < len(win) and win[j + 1]["face"] and f(win[j + 1]): j += 1
                d = win[j]["t"] - win[k]["t"] + dt
                if d >= mind:
                    ev.append({"flag": name, "t0": win[k]["t"], "t1": round(win[j]["t"] + dt, 2),
                               "action": "keep" if d <= 0.5 else "cover"})
                k = j + 1
            else:
                k += 1
    blinks = sum(1 for i in range(1, len(fw)) if fw[i]["blink"] > 0.5 >= fw[i - 1]["blink"])
    sh = float(np.median([r["sharp"] for r in fw]))
    out.update({"flags": ev, "n_cover": sum(e["action"] == "cover" for e in ev), "blinks": blinks,
                "sharp_rel": round(sh / clip_sharp, 2) if clip_sharp else None,
                "soft": bool(clip_sharp and sh < 0.6 * clip_sharp)})
    return out


# ---------------- matching ----------------------------------------------------------------------------------
def find_attempts(u, W):
    wt = [x["n"] for x in W]; mask = [False] * len(W); n = len(u["toks"]); found = []

    def record(path, score, kind):
        matched = [p for p in path if p[2]]
        js = [p[1] for p in path if p[1] is not None]; j0, j1 = min(js), max(js)
        for j in range(j0, j1 + 1): mask[j] = True
        ui = [p[0] for p in matched]
        # the alignment stops at the last MATCHED word: a misheard ending ("fuel in the eye" for "fuel of AI") or opening
        # would be cut off, so extend over the rest of the same island when the first/last script word didn't match
        if max(ui) < n - 1:
            while j1 + 1 < len(W) and not mask[j1 + 1] and W[j1 + 1]["isl"] == W[j1]["isl"] and W[j1 + 1]["s"] - W[j1]["e"] < 0.5:
                j1 += 1; mask[j1] = True
        if min(ui) > 0:
            while j0 > 0 and not mask[j0 - 1] and W[j0 - 1]["isl"] == W[j0]["isl"] and W[j0]["s"] - W[j0 - 1]["e"] < 0.5:
                j0 -= 1; mask[j0] = True
        span = W[j0:j1 + 1]
        extra = [W[p[1]]["w"] for p in path if p[0] is None] + [x["w"] for x in W[j0:j1 + 1]
                 if not any(p[1] is not None and W[p[1]] is x for p in path)]
        cov = len(matched) / n
        full = cov >= 0.9 and min(ui) == 0 and max(ui) == n - 1
        fil = [x["n"] for x in span if x["n"] in FILLERS]
        gaps = [round(span[k + 1]["s"] - span[k]["e"], 2) for k in range(len(span) - 1)]
        dur = span[-1]["e"] - span[0]["s"]
        found.append({"j0": j0, "j1": j1, "a": span[0]["s"], "b": span[-1]["e"], "score": round(score, 1),
                      "kind": "FULL" if full else kind, "cov": round(cov, 2), "first": min(ui) == 0, "last": max(ui) == n - 1,
                      "extra": [x for x in extra if norm(x) not in FILLERS],
                      "missing": [u["toks"][i] for i in range(n) if i not in ui],   # script words not matched
                      "fillers": fil, "maxgap": max(gaps) if gaps else 0.0,
                      "wpm": round(sum(1 for x in span if x["n"] not in FILLERS) / max(dur, 0.1) * 60),
                      "minp": round(min(x["p"] for x in span), 2), "meanp": round(float(np.mean([x["p"] for x in span])), 2),
                      "islands": sorted({x["isl"] for x in span}), "said": " ".join(x["w"] for x in span),
                      "words": [{"w": x["w"], "s": x["s"], "e": x["e"]} for x in span]})

    while True:                       # GE tier: every real attempt, partials included
        score, path = sw(u["toks"], wt, mask)
        matched = [p for p in path if p[2]]
        if not path or score < max(3.0, 0.9 * n) or len(matched) < max(2, 0.3 * n): break
        record(path, score, "part")
    while True:                       # false-start tier: short restarts that open on the unit's first word
        score, path = sw(u["toks"], wt, mask)
        matched = [p for p in path if p[2]]
        if not path or score < 3.0 or len(matched) < 2 or matched[0][0] != 0: break
        record(path, score, "FALSE_START")
    return found


def suggest(attempts):
    """Advisory pick, encoding the editor rules: FULL first; quality; later over earlier within 1 point; runs win ties."""
    if not attempts: return None, "never said: report it, don't invent it"
    full = [k for k, x in enumerate(attempts) if x["kind"] == "FULL"]
    pool = full or [k for k, x in enumerate(attempts) if x["kind"] != "FALSE_START"] or list(range(len(attempts)))

    def q(x):
        return (10 * x["cov"] - 1.5 * len(x["fillers"]) - 1.0 * len(x["extra"]) - 0.5 * len(x["missing"])
                - 2.0 * (x["maxgap"] > 0.7) - 1.0 * x.get("face", {}).get("n_cover", 0) - 1.0 * (x["minp"] < 0.3)
                - 1.0 * bool(x.get("face", {}).get("soft")))
    best = max(q(attempts[k]) for k in pool)
    near = [k for k in pool if q(attempts[k]) >= best - 1.0]
    inrun = [k for k in near if attempts[k].get("run")]
    pick = max(inrun or near, key=lambda k: (attempts[k]["clip_order"], attempts[k]["a"]))
    why = ("only FULL" if len(full) == 1 else "best FULL" if full else "no FULL take: best partial, check wording")
    if len(near) > 1: why += f"; {len(near)} within 1 pt -> latest" + (" in a run" if inrun else "")
    return pick, why


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--script", required=True); ap.add_argument("--out", required=True); ap.add_argument("--md")
    ap.add_argument("--clip", action="append", required=True); ap.add_argument("--tx", action="append", required=True)
    ap.add_argument("--audio", action="append", required=True); ap.add_argument("--video", action="append", default=[])
    ap.add_argument("--src", action="append", default=[])
    ap.add_argument("--run-gap", type=float, default=0.8, help="max pause between units to count as one run (s)")
    ap.add_argument("--face-every", type=float, default=0.1, help="face scan interval (s)")
    a = ap.parse_args()
    U = units_of(a.script)
    clips, attempts_by_unit = {}, {u["id"]: [] for u in U}
    for ci, cid in enumerate(a.clip):
        txp, aud = a.tx[ci], a.audio[ci]
        vid = a.video[ci] if ci < len(a.video) else None
        src = a.src[ci] if ci < len(a.src) else (vid or aud)
        tx = json.load(open(txp))
        isl = tx.get("islands") or [{"i": k, "words": s["words"]} for k, s in enumerate(tx["segments"])]
        W = [{"w": w["w"], "n": norm(w["w"]), "s": w["s"], "e": w["e"], "p": w["p"], "isl": x["i"]}
             for x in isl for w in x["words"] if norm(w["w"])]
        y = load_audio(aud)
        rows = facescan(vid, a.face_every, os.path.splitext(a.out)[0] + f".{cid}.facescan.json") if vid else []
        clip_sharp = float(np.median([r["sharp"] for r in rows if r["face"]])) if any(r["face"] for r in rows) else None
        clips[cid] = {"src": src, "audio": aud, "video": vid, "tx": txp, "order": ci}
        used = set()
        for u in U:
            for x in find_attempts(u, W):
                x.update(clip=cid, clip_order=ci, **audio_metrics(y, x["a"], x["b"]))
                if rows: x["face"] = face_flags(rows, x["a"], x["b"], clip_sharp)
                used.update(x["islands"]); attempts_by_unit[u["id"]].append(x)
        clips[cid]["unmatched_islands"] = [{"i": x["i"], "text": x.get("text", "")} for x in isl if x["i"] not in used and x["words"]]
    # runs: unit k attempt followed within run_gap by a unit k+1 attempt in the same clip, nothing in between
    allatt = sorted([(x["clip_order"], x["a"], uid, x) for uid, L in attempts_by_unit.items() for x in L], key=lambda t: (t[0], t[1]))
    order = {u["id"]: k for k, u in enumerate(U)}
    runs, rid = [], 0
    for k in range(len(allatt) - 1):
        c0, _, u0, x0 = allatt[k]; c1, _, u1, x1 = allatt[k + 1]
        if c0 == c1 and order[u1] == order[u0] + 1 and 0 <= x1["a"] - x0["b"] <= a.run_gap \
                and x0["kind"] != "FALSE_START" and x1["kind"] != "FALSE_START":
            if not x0.get("run"): rid += 1; x0["run"] = f"R{rid}"; runs.append({"id": f"R{rid}", "units": [u0]})
            x1["run"] = x0["run"]; runs[-1]["units"].append(u1)
    units_out, picks = [], {}
    for u in U:
        L = sorted(attempts_by_unit[u["id"]], key=lambda x: (x["clip_order"], x["a"]))
        for k, x in enumerate(L): x["idx"] = k
        pk, why = suggest(L)
        picks[u["id"]] = {"attempt": pk, "why": why}
        units_out.append({"id": u["id"], "line": u["line"], "text": u["text"], "n": len(u["toks"]), "attempts": L})
    res = {"script": os.path.abspath(a.script), "clips": clips, "units": units_out, "runs": runs, "suggested": picks,
           "rules": ["meaning over exact wording", "later attempt over earlier, all else equal", "prefer continuous runs",
                     "never splice half-takes mid-sentence unless on a natural pause", "lines never said: report, don't invent"]}
    json.dump(res, open(a.out, "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    md = render_md(res)
    if a.md: open(a.md, "w").write(md)
    print(md)


def render_md(res):
    o = ["# Take table", "", "Rules: " + "; ".join(res["rules"]) + ".",
         "Pick per unit with `refine_cuts.py --pick UNIT:IDX ...`. kind FULL = cov>=0.9 with first+last word.", ""]
    for u in res["units"]:
        sg = res["suggested"][u["id"]]
        o.append(f"## [{u['id']}] {u['text']}")
        o.append(f"suggested: **{sg['attempt']}** ({sg['why']})" if sg["attempt"] is not None else f"**{sg['why']}**")
        o.append("")
        o.append("| idx | clip | time | kind | cov | extra / missing | fillers | gap | wpm | p min/mean | lvl dB | rmsσ / pitchσ | face | run | said |")
        o.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for x in u["attempts"]:
            f = x.get("face", {})
            fs = "-" if not f else (f"{f.get('face_ratio', 0):.0%} blink{f.get('blinks', 0)} sharp{f.get('sharp_rel')}"
                                    + ("".join(f" {e['flag']}({e['action']})" for e in f.get("flags", []))) + (" SOFT" if f.get("soft") else ""))
            o.append(f"| {x['idx']} | {x['clip']} | {x['a']:.2f}-{x['b']:.2f} | {x['kind']} | {x['cov']:.2f} | "
                     f"{' '.join(x['extra']) or '-'} / {' '.join(x['missing']) or '-'} | {' '.join(x['fillers']) or '-'} | "
                     f"{x['maxgap']:.2f} | {x['wpm']} | {x['minp']:.2f}/{x['meanp']:.2f} | {x.get('level_db')} | "
                     f"{x.get('rms_db_std', '-')} / {x.get('pitch_std_st', '-')} | {fs} | {x.get('run', '-')} | {x['said']} |")
        o.append("")
    for cid, c in res["clips"].items():
        if c["unmatched_islands"]:
            o.append(f"Unmatched islands in {cid} (ad-libs, restarts of nothing, noise): " +
                     "; ".join(f"#{x['i']} \"{x['text']}\"" for x in c["unmatched_islands"]))
    return "\n".join(o)


if __name__ == "__main__":
    main()
