#!/usr/bin/env python3
"""Cut-QA gate: run before any draft goes out. Writes a pass/fail report (exit 1 on FAIL) and a cut-sheet JPEG.

usage: cut_qa.py CUT.mp4 --edl edl.json --takes takes.json --out qa/ [--window 0.8] [--no-subcheck] [--model large-v3-turbo]

Checks (FAIL = must fix, WARN = listen/look):
  clipped tail / onset  FAIL  voice in the last/first 40 ms of a piece AND the source keeps sounding right past the
                              edge (the word was cut off). Edge voice without the continuation is a WARN.
  join doubles          FAIL  the output audio +-0.8 s around every join is re-transcribed; a doubled word or 2-3-gram
                              that the kept source words don't contain (YildizDikme/claude-video-edit verify.py, MIT)
  join word not heard   WARN  the last word before / first word after a join is missing from the window transcript
  hidden restart        FAIL  each piece split at internal silences >= 0.15 s, every part transcribed alone; two parts
                              opening with the same two words, or a piece repeating the previous piece's opening
                              (kurbaitaev/ghost-editor subcheck.py, MIT)
  final vs script       FAIL  whole output re-transcribed (islands) and aligned to each picked script unit: a script
                              word the picked source take DID say but the final lacks = lost in the cut. Words missing
                              in source and final alike are WARN (said differently / misheard). Doubled n-grams = FAIL.
  no breath             WARN  < 0.15 s of air across a join          (jacobksamuelson/talking-head-video review.py, MIT)
  dead air              WARN  silence > 1.4 s in the output
  choppy                WARN  3+ joins within 8 s (DDN hides cuts with 1.0/1.4 framing, so not a hard fail)
  long word             WARN  a final-transcript word > 0.7 s (stretched or swallowed)
Cut sheet: 3 frames before | 3 frames after every join, face-cropped (cutsheet.jpg).
"""
import argparse, difflib, json, os, re, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audiolib as AL
import transcribe as TX
from analyze_takes import units_of, sw, norm, FILLERS

SR = 16000


def ntoks(words): return [norm(w["w"]) for w in words if norm(w["w"]) and norm(w["w"]) not in FILLERS]


def repeats(ws):
    hits = [ws[i] for i in range(1, len(ws)) if ws[i] == ws[i - 1] and len(ws[i]) > 1]
    for n in (2, 3):
        hits += [" ".join(ws[i:i + n]) for i in range(n, len(ws) - n + 1) if ws[i - n:i] == ws[i:i + n]]
    return hits


def heard(tok, toks):
    return any(t == tok or difflib.SequenceMatcher(None, t, tok).ratio() >= 0.72 or (len(tok) >= 4 and tok in t) for t in toks)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cut"); ap.add_argument("--edl", required=True); ap.add_argument("--takes", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--window", type=float, default=0.8)
    ap.add_argument("--no-subcheck", action="store_true"); ap.add_argument("--model", default="large-v3-turbo")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    E = json.load(open(a.edl)); P = E["clips"]; T = json.load(open(a.takes))
    base = os.path.dirname(os.path.abspath(a.edl))
    for c in P:
        if not os.path.isabs(c["src"]) and not os.path.exists(c["src"]): c["src"] = os.path.join(base, c["src"])
    tbase = os.path.dirname(os.path.abspath(a.takes))
    rp = lambda p: p if os.path.isabs(p) or os.path.exists(p) else os.path.join(tbase, p)
    src2clip = {}
    for cid, c in T["clips"].items():
        src2clip[os.path.realpath(rp(c["src"]))] = c
    issues = []
    add = lambda sev, t, kind, msg: issues.append({"sev": sev, "t": round(float(t), 2), "kind": kind, "msg": msg})

    # output timeline
    pos = np.concatenate([[0], np.cumsum([c["out"] - c["in"] for c in P])])
    joins = [k for k in range(1, len(P)) if not (P[k]["src"] == P[k - 1]["src"] and abs(P[k]["in"] - P[k - 1]["out"]) < 1e-3)]
    # source envelopes + kept words mapped to the output timeline
    envs, srcw, kept = {}, {}, []
    for c in P:
        key = os.path.realpath(c["src"])
        if key not in envs:
            envs[key] = AL.Env(AL.load(c["src"], SR), SR)
            cl = src2clip.get(key)
            srcw[key] = [w for s in json.load(open(rp(cl["tx"])))["segments"] for w in s["words"]] if cl else []
    for k, c in enumerate(P):
        for w in srcw[os.path.realpath(c["src"])]:
            m = (w["s"] + w["e"]) / 2
            if c["in"] <= m < c["out"]:
                kept.append({"w": w["w"], "s": pos[k] + max(w["s"], c["in"]) - c["in"], "e": pos[k] + min(w["e"], c["out"]) - c["in"], "piece": k})

    # 1. edges: clipped tail / onset, edge voice, air
    for k, c in enumerate(P):
        Ev = envs[os.path.realpath(c["src"])]
        edges = []
        if k + 1 < len(P) and k + 1 not in joins: pass
        else: edges.append(("tail", c["out"], pos[k + 1]))
        if k == 0 or k in joins: edges.append(("onset", c["in"], pos[k]))
        for side, t, tout in edges:
            if side == "tail":
                inside = max(Ev.lv(t - 0.04 + j * 0.01) for j in range(4)) > Ev.Q + 10
                beyond = np.mean([Ev.loud(t + j * 0.01) for j in range(5)]) >= 0.6
            else:
                inside = max(Ev.lv(t + j * 0.01) for j in range(4)) > Ev.Q + 10
                beyond = np.mean([Ev.loud(t - 0.05 + j * 0.01) for j in range(5)]) >= 0.6
            if inside and beyond:
                add("FAIL", tout, f"clipped {side}", f"piece {k} {side} @ src {t:.2f}s: voice at the edge and the source keeps sounding "
                    f"{'after' if side == 'tail' else 'before'} it -> a word is cut; move the cut into the silence")
            elif inside:
                add("WARN", tout, "edge voice", f"piece {k} {side} @ src {t:.2f}s: speech-level sound in the {'last' if side == 'tail' else 'first'} 40 ms")
    for k in joins:
        Ea, Eb = envs[os.path.realpath(P[k - 1]["src"])], envs[os.path.realpath(P[k]["src"])]
        t = P[k - 1]["out"]; q1 = 0.0
        while q1 < 1.0 and Ea.quiet(t - q1 - 0.01): q1 += 0.01
        t = P[k]["in"]; q2 = 0.0
        while q2 < 1.0 and Eb.quiet(t + q2): q2 += 0.01
        if q1 + q2 < 0.15:
            add("WARN", pos[k], "no breath", f"join {k}: only {q1 + q2:.2f} s of air across the cut")

    # output audio checks
    y = AL.load(a.cut, SR); Eo = AL.Env(y, SR)
    t, run0 = 0.0, None
    while t < Eo.T:
        if Eo.quiet(t): run0 = t if run0 is None else run0
        else:
            if run0 is not None and t - run0 > 1.4: add("WARN", run0, "dead air", f"{t - run0:.2f} s of silence")
            run0 = None
        t += 0.01
    jt = [pos[k] for k in joins]
    for i in range(len(jt)):
        n8 = [x for x in jt if jt[i] <= x < jt[i] + 8]
        if len(n8) >= 3:
            add("WARN", jt[i], "choppy", f"{len(n8)} joins within 8 s from {jt[i]:.2f}s: alternate 1.0/1.4 framing or cut whole sentences"); break

    print("loading whisper ...", flush=True)
    M = TX.load_model(a.model)
    # 2. join windows
    joinlog = []
    for k in joins:
        t = pos[k]; w0, w1 = max(0, t - a.window), min(len(y) / SR, t + a.window)
        hw, text, _ = TX.tx(M, y[int(w0 * SR):int(w1 * SR)], w0)
        ht = ntoks(hw)
        exp = [w for w in kept if w["s"] >= w0 - 0.05 and w["e"] <= w1 + 0.05]
        et = ntoks(exp)
        new_rep = [r for r in repeats(ht) if r not in repeats(et)]
        if new_rep:
            add("FAIL", t, "join doubles", f"join {k} @ {t:.2f}s heard \"{text}\": doubled {', '.join(sorted(set(new_rep)))}")
        before = [w for w in kept if w["piece"] == k - 1 and norm(w["w"]) not in FILLERS]
        after = [w for w in kept if w["piece"] == k and norm(w["w"]) not in FILLERS]
        for side, ws in (("before", before[-1:]), ("after", after[:1])):
            for w in ws:
                if w["s"] >= w0 and w["e"] <= w1 and not heard(norm(w["w"]), ht):
                    add("WARN", t, "join word not heard", f"join {k}: \"{w['w']}\" ({side} the cut) not in window transcript \"{text}\"")
        joinlog.append({"join": k, "t": round(t, 2), "heard": text, "expected": " ".join(w["w"] for w in exp)})

    # 3. hidden restarts inside pieces
    sublog = []
    if not a.no_subcheck:
        prev_first = None
        for k in range(len(P)):
            a0, b0 = pos[k], pos[k + 1]
            L = Eo.L[int(a0 / 0.01):int(b0 / 0.01)]; th = Eo.floor + 14
            idx = np.where(L > th)[0]; parts = []
            if len(idx):
                s = p = idx[0]
                for i in idx[1:]:
                    if i - p > 15: parts.append((s, p)); s = i
                    p = i
                parts.append((s, p))
            texts = []
            for s, e in parts:
                pa, pb = max(0, a0 + s * 0.01 - 0.05), min(len(y) / SR, a0 + e * 0.01 + 0.08)
                if pb - pa < 0.25: continue
                _, tt, _ = TX.tx(M, y[int(pa * SR):int(pb * SR)], pa); texts.append((round(pa, 2), tt))
            starts = [tuple(norm(x) for x in tt.split()[:2]) for _, tt in texts if len(tt.split()) >= 2]
            if len(starts) != len(set(starts)):
                add("FAIL", a0, "hidden restart", f"piece {k}: two parts open with the same words: " + " | ".join(tt for _, tt in texts))
            fw = tuple(norm(x) for x in texts[0][1].split()[:2]) if texts and len(texts[0][1].split()) >= 2 else None
            if fw and fw == prev_first:
                add("FAIL", a0, "hidden restart", f"piece {k} repeats the previous piece's opening \"{' '.join(fw)}\"")
            prev_first = fw
            sublog.append({"piece": k, "parts": texts})

    # 4. final whole-output transcription vs script
    isl = TX.run_islands(M, y.astype(np.float32))
    FW = [{"w": w["w"], "n": norm(w["w"]), "s": w["s"], "e": w["e"], "p": w["p"]} for x in isl for w in x["words"] if norm(w["w"])]
    final_text = " ".join(w["w"] for w in FW)
    for w in FW:
        if w["e"] - w["s"] > 0.7: add("WARN", w["s"], "long word", f"\"{w['w']}\" lasts {w['e'] - w['s']:.2f} s")
    ft = [w["n"] for w in FW if w["n"] not in FILLERS]
    for r in sorted(set(repeats(ft))):
        add("FAIL", 0, "final doubles", f"final transcript repeats \"{r}\"")
    picked = {}
    for c in P:
        for lab in str(c.get("label", "")).split("+"):
            if ":" in lab and lab.split(":")[0] in {u["id"] for u in T["units"]}:
                uid, idx = lab.split(":"); picked[uid] = int(re.match(r"\d+", idx).group())
    scriptlog = []
    U = {u["id"]: u for u in units_of(T["script"])}
    for u in T["units"]:
        if u["id"] not in picked:
            add("WARN", 0, "unit not in cut", f"[{u['id']}] \"{u['text']}\" is not in the EDL"); continue
        src_missing = set(u["attempts"][picked[u["id"]]]["missing"])
        ut = U[u["id"]]["toks"]
        score, path = sw(ut, [w["n"] for w in FW], [False] * len(FW))
        got = {p[0] for p in path if p[2]}
        fmiss = [ut[i] for i in range(len(ut)) if i not in got]
        lost = [x for x in fmiss if x not in src_missing]
        said_diff = [x for x in fmiss if x in src_missing]
        if lost:
            add("FAIL", 0, "word lost in cut", f"[{u['id']}] the picked take said {lost} but the final doesn't")
        if said_diff:
            add("WARN", 0, "said differently", f"[{u['id']}] script words {said_diff} not heard in source take or final (ASR or wording; editor accepted)")
        scriptlog.append({"unit": u["id"], "script": u["text"], "final_missing": fmiss, "source_missing": sorted(src_missing)})

    # 5. cut sheet
    sheet = cutsheet(a.cut, [pos[k] for k in joins], os.path.join(a.out, "cutsheet.jpg"))

    fails = [i for i in issues if i["sev"] == "FAIL"]; warns = [i for i in issues if i["sev"] == "WARN"]
    verdict = "FAIL" if fails else "PASS"
    rep = {"verdict": verdict, "cut": a.cut, "joins": [round(pos[k], 3) for k in joins], "issues": issues,
           "join_windows": joinlog, "subcheck": sublog, "final_transcript": final_text, "script_check": scriptlog, "cutsheet": sheet}
    json.dump(rep, open(os.path.join(a.out, "qa.json"), "w"), indent=1, default=float)
    md = [f"# Cut QA: **{verdict}** ({len(fails)} fail, {len(warns)} warn)", f"`{a.cut}` - {len(joins)} joins at "
          + ", ".join(f"{pos[k]:.2f}s" for k in joins), ""]
    for i in sorted(issues, key=lambda i: (i["sev"] != "FAIL", i["t"])):
        md.append(f"- **{i['sev']}** {i['t']:.2f}s {i['kind']}: {i['msg']}")
    md += ["", "## Join windows", *[f"- join {j['join']} @ {j['t']}s heard: \"{j['heard']}\"" for j in joinlog],
           "", "## Final transcript", final_text, "", f"Cut sheet: {sheet}",
           "", "A clean report does not mean every join sounds right: listen to the joins and look at the cut sheet."]
    open(os.path.join(a.out, "qa.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))
    sys.exit(1 if fails else 0)


def cutsheet(video, times, out, n=3):
    import cv2
    cap = cv2.VideoCapture(video); fps = cap.get(cv2.CAP_PROP_FPS) or 30
    ok, fr0 = cap.read()
    if not ok or not times:
        cap.release(); return None
    from tonemap import _face_box
    box = _face_box(fr0)
    if box:
        x0, y0, x1, y1 = box; fw, fh = x1 - x0, y1 - y0
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2; half = int(max(fw, fh) * 1.1)
        crop = (max(cx - int(half * 16 / 9), 0), max(cy - half, 0), min(cx + int(half * 16 / 9), fr0.shape[1]), min(cy + half, fr0.shape[0]))
    else:
        crop = (0, 0, fr0.shape[1], fr0.shape[0])
    rows = []
    for t in times:
        f = int(round(t * fps)); tiles = []
        for i in range(f - n, f + n):
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(i, 0)); ok, im = cap.read()
            im = im if ok else np.zeros_like(fr0)
            im = cv2.resize(im[crop[1]:crop[3], crop[0]:crop[2]], (256, 144))
            col = (0, 220, 255) if i >= f else (255, 255, 255)
            cv2.rectangle(im, (0, 0), (256, 18), (0, 0, 0), -1)
            cv2.putText(im, f"{i / fps:.2f}s f{i}" + (" | CUT" if i == f else ""), (4, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, col, 1, cv2.LINE_AA)
            tiles.append(im)
        sep = np.full((144, 4, 3), (0, 0, 255), np.uint8)
        rows.append(np.hstack(tiles[:n] + [sep] + tiles[n:]))
    cap.release()
    cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])
    return out


if __name__ == "__main__":
    main()
