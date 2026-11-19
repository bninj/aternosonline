#!/usr/bin/env python3
"""Word timings -> caption phrases (JSON for Remotion + SRT).
usage: make_captions.py words.json OUT.json OUT.srt [--offset SECONDS]
Rules: one short phrase at a time (<= 26 chars, <= 5 words), break after punctuation, numbers as digits with %,
emphasis on numbers, DDN, Sky; never any dash; proper-noun fixes. Phrase stays on until the next phrase starts
(if the gap is < 0.6 s) so captions don't blink.
"""
import json, re, sys

words = json.load(open(sys.argv[1]))
off = float(sys.argv[sys.argv.index("--offset") + 1]) if "--offset" in sys.argv else 0.0
FIX = {"starts.": "Starz.", "starts": "Starz", "blockbuster.": "Blockbuster.", "blockbuster": "Blockbuster",
       "cast": "Cast", "ai": "AI", "skye": "Sky", "skye,": "Sky,", "infinia": "Infinia", "ofcom": "Ofcom"}
NUM = {"twelve": "12", "five": "5", "99": "99", "75": "75", "ninety": None}

# merge "N percent" -> "N%"
toks = []
i = 0
while i < len(words):
    w = dict(words[i]); t = w["w"]
    low = t.lower().strip(".,?!")
    if low in ("twelve", "five", "99", "75") and i + 1 < len(words) and words[i + 1]["w"].lower().startswith("percent"):
        n = {"twelve": "12", "five": "5"}.get(low, low)
        tail = re.sub(r"(?i)percent", "", words[i + 1]["w"])
        w["w"] = n + "%" + tail; w["e"] = words[i + 1]["e"]; i += 2
    else:
        w["w"] = FIX.get(t.lower(), t) if t.lower() in FIX else t; i += 1
    w["w"] = w["w"].replace("-", " ").replace("–", " ").replace("—", " ").strip()
    toks.append(w)

def emph(t):
    b = t.strip(".,?!'s")
    return bool(re.search(r"\d", t)) or b in ("DDN", "DDN’", "Sky") or t.startswith("DDN")

phrases, cur = [], []
for k, w in enumerate(toks):
    cur.append(w)
    text = " ".join(x["w"] for x in cur)
    nxt = toks[k + 1] if k + 1 < len(toks) else None
    gap = (nxt["s"] - w["e"]) if nxt else 9
    endp = w["w"][-1] in ".?!"
    comma = w["w"][-1] in ",:"
    longish = len(text) >= 16 or len(cur) >= 4
    if nxt is None or endp or gap > 0.35 or (comma and len(cur) >= 2) or len(text) >= 24 or (longish and len(text + " " + nxt["w"]) > 26):
        phrases.append(cur); cur = []

out = []
for j, p in enumerate(phrases):
    s, e = p[0]["s"] + off, p[-1]["e"] + off
    nxt_s = phrases[j + 1][0]["s"] + off if j + 1 < len(phrases) else None
    if nxt_s is not None and nxt_s - e < 0.6: e = nxt_s
    else: e = e + 0.35
    out.append(dict(start=round(s - 0.05, 3), end=round(e, 3),
                    words=[dict(text=w["w"], start=round(w["s"] + off, 3), end=round(w["e"] + off, 3), emphasis=emph(w["w"])) for w in p],
                    text=" ".join(w["w"] for w in p)))

for o in out:
    assert not re.search(r"[-–—]", o["text"]), o["text"]
json.dump(out, open(sys.argv[2], "w"), indent=1)

def ts(x):
    h, x = divmod(x, 3600); m, x = divmod(x, 60); s = int(x); ms = int(round((x - s) * 1000))
    if ms == 1000: s, ms = s + 1, 0
    return f"{int(h):02d}:{int(m):02d}:{s:02d},{ms:03d}"
with open(sys.argv[3], "w") as f:
    for n, o in enumerate(out, 1):
        f.write(f"{n}\n{ts(max(0, o['start']))} --> {ts(o['end'])}\n{o['text']}\n\n")
print(len(out), "phrases")
for o in out: print(f"{o['start']:6.2f}-{o['end']:6.2f}  {o['text']}")
