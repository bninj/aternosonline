#!/usr/bin/env python3
"""Shortlist the best takes per line (or per continuous run) and cut preview clips for the take picker page.
usage: build_picker.py takes.json OUTDIR
"""
import json, os, re, subprocess, sys

takes = json.load(open(sys.argv[1]))
OUT = sys.argv[2]
os.makedirs(f"{OUT}/clips", exist_ok=True)
PROXY = "/home/user/ddn-project/footage/proxy"
units = {str(i + 1): u for i, u in enumerate(takes["units"])}

def score(a):
    s = {"FULL": 3, "part": 1}.get(a["kind"], -5)
    s += 2 * a["cov"] + 2 * a["meanp"] - 1.0 * len(a["fillers"]) - a["maxgap"]
    s += (a.get("pitch_std_st") or 0) / 4 + (a.get("rms_db_std") or 0) / 10
    if a["wpm"] > 195 and len(a["said"].split()) >= 6: s -= (a["wpm"] - 195) / 25          # too fast reads as rushed
    return s

def bad(uid, a):
    t = a["said"].lower()
    if a["kind"] == "FALSE_START": return "false start"
    if uid == "12" and ("energy" in t or "5" not in t or "enterprise" not in t): return "wrong/missing fact wording"
    if uid == "15" and ("99" not in t or "75" not in t): return "wrong/missing number"
    if uid == "13" and "arsenal" not in t: return "incomplete"
    if uid == "5" and ("stream" not in t or "traditional tv." in t or "move to traditional" in t): return "wrong meaning"
    if uid == "6" and "sky needs" not in t: return "incomplete"
    if a["maxgap"] > 1.5: return "restart inside"
    return None

def note(uid, a):
    n = []
    nw = len(a["said"].split())
    if a["wpm"] > 195 and nw >= 6: n.append(f"quick ({a['wpm']} wpm)")
    if a["fillers"]: n.append("filler: " + ", ".join(a["fillers"]))
    if a["cov"] < 0.85: n.append("wording differs")
    if uid == "6" and "fast" not in a["said"].lower(): n.append("drops 'and fast' (may be misheard)")
    if uid == "5" and "year" not in a["said"].lower(): n.append("no 'in a year'")
    if uid == "16":
        n.append("says 'worked with' (fact table prefers 'work with')" if "worked" in a["said"].lower() else "says 'work with' ✓")
    if a["maxgap"] > 0.4: n.append(f"pause {a['maxgap']:.1f}s mid line")
    return "; ".join(n)

GROUPS = [  # (title, section, unit ids, pre-roll s)
    ("Hook: Sorry I kept you waiting / AI chips / Sky pays", "Hook", ["1", "2", "3"], 2.0),
    ("So first, why change?", "Why change", ["4"], 0.4),
    ("Ofcom 12%", "Why change", ["5"], 0.4),
    ("Netflix and YouTube… and fast", "Why change", ["6"], 0.4),
    ("Second, why now?", "Why now", ["7"], 0.4),
    ("Sky Q voice search", "Why now", ["8"], 0.4),
    ("Next step: an AI assistant", "Why now", ["9"], 0.4),
    ("Imagine asking…", "Why now", ["10"], 0.4),
    ("Third, why DDN?", "Why DDN", ["11"], 0.4),
    ("Idle chips / Cast AI 5%", "Why DDN", ["12"], 0.4),
    ("Sky Sports / Arsenal", "Why DDN", ["13"], 0.4),
    ("DDN's Infinia", "Why DDN", ["14"], 0.4),
    ("99% busy, 75% cost per token", "Why DDN", ["15"], 0.4),
    ("Canal Plus and Starz", "Why DDN", ["16"], 0.4),
    ("Ask: the ask is clear / pilot / measure", "Ask", ["17", "18", "19"], 0.6),
    ("Ending: don't be the next Blockbuster / Thank you", "Ask", ["20", "21"], 0.5),
]

def candidates(uids):
    if len(uids) == 1:
        uid = uids[0]
        out = []
        for a in units[uid]["attempts"]:
            if bad(uid, a): continue
            out.append(dict(parts=[(uid, a)], s=score(a), clip=a["clip"], a=a["a"], b=a["b"]))
        return out
    # multi-unit: consecutive attempts in one clip forming a run (each unit once, in order, gap <= 1.2 s)
    out = []
    first = units[uids[0]]["attempts"]
    for a0 in first:
        if bad(uids[0], a0): continue
        chain, cur = [(uids[0], a0)], a0
        for uid in uids[1:]:
            nxt = [a for a in units[uid]["attempts"] if a["clip"] == cur["clip"] and 0 <= a["a"] - cur["b"] <= 1.6 and not bad(uid, a)]
            if not nxt: break
            cur = min(nxt, key=lambda a: a["a"]); chain.append((uid, cur))
        if len(chain) < len(uids) and not (uids[0] == "17" and len(chain) >= 2): continue
        s = sum(score(a) for _, a in chain) / len(chain) + (0.8 if len(chain) == len(uids) else 0)
        out.append(dict(parts=chain, s=s, clip=a0["clip"], a=chain[0][1]["a"], b=chain[-1][1]["b"]))
    return out

page = []
for title, section, uids, pre in GROUPS:
    cands = sorted(candidates(uids), key=lambda c: -c["s"])
    # de-duplicate overlapping candidates
    picked = []
    for c in cands:
        if any(c["clip"] == p["clip"] and c["a"] < p["b"] and p["a"] < c["b"] for p in picked): continue
        picked.append(c)
        if len(picked) == 5: break
    items = []
    for rank, c in enumerate(picked):
        gid = "g%02d" % (len(page) + 1)
        name = f"{gid}_{rank + 1}.mp4"
        ss, ee = max(0, c["a"] - pre), c["b"] + 0.45
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{ss:.3f}", "-to", f"{ee:.3f}", "-i", f"{PROXY}/{c['clip']}.mp4",
                        "-vf", "scale=1280:-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "30", "-c:a", "aac", "-b:a", "96k",
                        "-movflags", "+faststart", f"{OUT}/clips/{name}"], check=True)
        said = " ".join(a["said"] for _, a in c["parts"])
        notes = "; ".join(x for x in (note(u, a) for u, a in c["parts"]) if x)
        wpm = round(sum(a["wpm"] for _, a in c["parts"]) / len(c["parts"]))
        items.append(dict(file=f"clips/{name}", clip=c["clip"], start=round(c["a"], 2), end=round(c["b"], 2),
                          said=said, notes=notes, wpm=wpm, score=round(c["s"], 2),
                          picks={u: a["idx"] for u, a in c["parts"]}))
    page.append(dict(id="g%02d" % (len(page) + 1), title=title, section=section, units=uids, items=items))
    print(title, len(items), [round(i["score"], 1) for i in items])

json.dump(page, open(f"{OUT}/picker.json", "w"), indent=1)
