#!/usr/bin/env bash
# End-to-end self-test of the take pipeline on synthetic footage (espeak multi-take rush on a 4K HLG HEVC 29.97 clip).
# Asserts: matcher suggestions == expected picks; good cut passes the QA gate; a deliberately clipped cut fails it.
# Usage: bash selftest_takes.sh [OUTDIR=tools/test/mt]      (~6 min on 4 vCPU; reuses the rush if it exists)
set -euo pipefail
T="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; PY="$T/venv/bin/python"
D="${1:-$T/test/mt}"; mkdir -p "$D"; cd "$D"
[ -s rush_hlg.mov ] || "$PY" "$T/make_test_takes.py" "$D"
ffmpeg -v error -y -i rush_hlg.mov -vn -ac 1 -ar 16000 audio.wav               # analysis audio from the camera file
"$PY" "$T/tonemap.py" proxy rush_hlg.mov proxy.mp4                               # 1080p SDR proxy for face metrics
"$PY" "$T/tonemap.py" ab rush_hlg.mov ab --times 3,20 2>/dev/null | tail -4      # hable vs mobius vs soft-shoulder LUT
"$PY" "$T/transcribe.py" audio.wav tx.json 2>/dev/null | tail -1                 # island transcription
"$PY" "$T/analyze_takes.py" --script script.txt --out takes.json --md takes.md \
  --clip RUSH --tx tx.json --audio audio.wav --video proxy.mp4 --src rush_hlg.mov 2>/dev/null | grep suggested
"$PY" - <<'EOF'
import json
t, e = json.load(open("takes.json")), json.load(open("expected.json"))["expected_picks"]
got = {k: v["attempt"] for k, v in t["suggested"].items()}
assert got == e, f"matcher picks {got} != expected {e}"
fs = [x for u in t["units"] for x in u["attempts"] if x["kind"] == "FALSE_START"]
assert fs, "false start not detected"
print("OK matcher picks", got, "| false starts:", [x["said"] for x in fs])
EOF
"$PY" "$T/refine_cuts.py" --takes takes.json --pick suggested --out edl.json
"$PY" "$T/conform.py" edl.json cut.mp4
"$PY" "$T/cut_qa.py" cut.mp4 --edl edl.json --takes takes.json --out qa_good > qa_good.log 2>/dev/null; grep "Cut QA" qa_good.log   # exits here (set -e) if the good cut fails
# deliberately clip the 3rd piece ~0.27 s into its last word ("demand")
"$PY" - <<'EOF'
import json
e = json.load(open("edl.json")); c = e["clips"][2]; fd = 1001 / 30000
c["out"] = round(c["in"] + round((c["out"] - 0.43 - c["in"]) / fd) * fd, 6); c["label"] += " CLIPPED"
json.dump(e, open("edl_clipped.json", "w"), indent=1)
EOF
"$PY" "$T/conform.py" edl_clipped.json cut_clipped.mp4 >/dev/null
if "$PY" "$T/cut_qa.py" cut_clipped.mp4 --edl edl_clipped.json --takes takes.json --out qa_clipped 2>/dev/null | grep -E "Cut QA|FAIL\*\*"; then
  echo "SELFTEST FAILED: clipped cut passed the QA gate"; exit 1
fi
echo "SELFTEST OK -> $D (takes.md, edl.json, cut.mp4, qa_good/qa.md, qa_clipped/qa.md, qa_*/cutsheet.jpg, ab/tonemap_ab.jpg)"
