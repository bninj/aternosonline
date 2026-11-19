#!/usr/bin/env python3
"""Convert transcribe.py JSON (source-clip times) + an EDL into Remotion @remotion/captions Caption[] on the edited timeline.
Usage: tx_to_captions.py tx.json edl.json out_captions.json [--src SRC]
  Only words fully inside an EDL clip whose src matches (--src, default: every clip) are kept, re-timed to output time.
  Without an EDL (pass '-') words keep their source times.
Caption shape: {text, startMs, endMs, timestampMs, confidence}; text has a leading space except the first word
(the convention createTikTokStyleCaptions expects).
"""
import json, sys

tx = json.load(open(sys.argv[1]))
edl = None if sys.argv[2] == "-" else json.load(open(sys.argv[2]))["clips"]
out = sys.argv[3]
src = sys.argv[sys.argv.index("--src") + 1] if "--src" in sys.argv else None
words = [w for s in tx["segments"] for w in s["words"]]
caps = []


def add(w, s, e):
    caps.append({"text": (" " if caps else "") + w["w"], "startMs": round(s * 1000), "endMs": round(e * 1000),
                 "timestampMs": round((s + e) / 2 * 1000), "confidence": w.get("p")})


if edl is None:
    for w in words:
        add(w, w["s"], w["e"])
else:
    t0 = 0.0
    for c in edl:
        if src is None or c["src"] == src:
            for w in words:
                if w["s"] >= c["in"] - 0.02 and w["e"] <= c["out"] + 0.02:
                    add(w, t0 + max(w["s"] - c["in"], 0), t0 + min(w["e"], c["out"]) - c["in"])
        t0 += c["out"] - c["in"]
json.dump(caps, open(out, "w"), indent=1)
print(f"{len(caps)} caption words -> {out}")
