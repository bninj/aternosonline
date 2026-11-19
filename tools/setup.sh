#!/usr/bin/env bash
# Rebuild the DDN talking-head + motion-graphics toolkit in an ephemeral container.
# Every command here was run and verified on 2026-11-18 (Ubuntu 24.04, Python 3.13, Node 22, ffmpeg 6.1.1, 4 CPU, no GPU).
# Usage: bash setup.sh [--smoke|--selftest]   (run from anywhere; installs next to this script)
#   --smoke     end-to-end render smoke test (~2 min)
#   --selftest  take pipeline self-test on a synthetic multi-take HLG rush: matcher picks, cut refine, conform, QA gate (~6 min)
set -euo pipefail
TOOLS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(dirname "$TOOLS")"
cd "$TOOLS"
t0=$(date +%s)

echo "== 1/6 system packages (libEGL for mediapipe tasks; espeak-ng only for synthetic test speech)"
if ! ldconfig -p | grep -q libEGL.so.1 || ! command -v espeak-ng >/dev/null; then
  apt-get install -y -q libegl1 libgles2 espeak-ng >/dev/null 2>&1 || { apt-get update -q >/dev/null && apt-get install -y -q libegl1 libgles2 espeak-ng >/dev/null; }
fi

echo "== 2/6 python venv"
[ -x venv/bin/python ] || python3 -m venv venv
# CPU-only torch first (silero-vad depends on torch; the default wheel drags in ~5 GB of CUDA libs)
venv/bin/pip install -q torch --index-url https://download.pytorch.org/whl/cpu
venv/bin/pip install -q faster-whisper auto-editor scenedetect librosa pyloudnorm opencv-python-headless \
  mediapipe rapidfuzz silero-vad soundfile numpy scipy
venv/bin/auto-editor --version   # first run downloads the auto-editor binary from GitHub releases

echo "== 3/6 models"
mkdir -p models
[ -s models/face_landmarker.task ] || curl -sSfL -o models/face_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task
# Whisper large-v3-turbo (CTranslate2, ~1.6 GB) into ~/.cache/huggingface; int8 on CPU = ~0.35x realtime on 4 cores
venv/bin/python -c "from faster_whisper import WhisperModel; WhisperModel('large-v3-turbo', device='cpu', compute_type='int8')"
venv/bin/python -c "from silero_vad import load_silero_vad; load_silero_vad(onnx=True)"
venv/bin/python tonemap.py lut models/hlg_softshoulder_203.cube   # 203-nit soft-shoulder HLG->709 LUT for the tone-map A/B

echo "== 4/6 remotion project"
cd "$TOOLS/remotion"
if [ -f package-lock.json ]; then npm ci --no-fund --no-audit; else
  V=4.0.545
  npm install --no-fund --no-audit remotion@$V @remotion/cli@$V @remotion/media@$V @remotion/media-parser@$V \
    @remotion/transitions@$V @remotion/captions@$V @remotion/google-fonts@$V @remotion/fonts@$V @remotion/shapes@$V \
    @remotion/paths@$V @remotion/noise@$V @remotion/media-utils@$V @remotion/layout-utils@$V @remotion/light-leaks@$V \
    @remotion/motion-blur@$V @fontsource/inter react@19 react-dom@19 typescript @types/react
fi
npx remotion browser ensure   # downloads chrome-headless-shell into node_modules/.remotion (works through the proxy)
mkdir -p public/fonts
cp node_modules/@fontsource/inter/files/inter-latin-{400,500,700}-normal.woff2 public/fonts/
"$TOOLS/venv/bin/python" "$TOOLS/sfx_gen.py" public/sfx
# official Remotion agent skill (text-only) into the project root so Claude Code sessions pick it up
(cd "$PROJECT" && npx -y skills add remotion-dev/skills --skill remotion-best-practices --agent claude-code -y >/dev/null)

echo "== 5/6 hyperframes (fallback renderer, Apache-2.0)"
cd "$TOOLS/hyperframes-test"
if [ -f package-lock.json ]; then npm ci --no-fund --no-audit; else npm init -y >/dev/null; npm i --no-fund --no-audit hyperframes@0.9.67 gsap@3.15.0; fi

echo "== 6/6 done in $(( $(date +%s) - t0 ))s"

if [ "${1:-}" = "--smoke" ]; then
  S="$TOOLS/test"; mkdir -p "$S"; cd "$S"
  espeak-ng -s 150 -w s.wav "Data is the fuel of A I. At D D N, we build the infrastructure that keeps every G P U fully utilized."
  ffmpeg -v error -y -f lavfi -i testsrc2=size=3840x2160:rate=30 -i s.wav -shortest -c:v libx265 -preset ultrafast \
    -pix_fmt yuv420p10le -x265-params "colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc:log-level=error" -tag:v hvc1 -c:a aac s_hlg.mov
  echo '{"clips":[{"src":"s_hlg.mov","in":0.0,"out":3.0}]}' > s_edl.json
  "$TOOLS/venv/bin/python" "$TOOLS/conform.py" s_edl.json s_cut.mp4 --tonemap
  "$TOOLS/venv/bin/python" "$TOOLS/transcribe.py" s.wav s_tx.json large-v3-turbo
  echo "Data is the fuel of AI. At DDN, we build the infrastructure that keeps every GPU fully utilized." > s_script.txt
  "$TOOLS/venv/bin/python" "$TOOLS/analyze_takes.py" --script s_script.txt --out s_takes.json --clip S --tx s_tx.json --audio s.wav 2>/dev/null | grep suggested
  "$TOOLS/venv/bin/python" "$TOOLS/tx_to_captions.py" s_tx.json s_edl.json "$TOOLS/remotion/public/captions.json"
  cp s_cut.mp4 "$TOOLS/remotion/public/cut.mp4"
  cd "$TOOLS/remotion" && npx remotion render TalkingHead out/smoke_th.mp4 --log=error
  "$TOOLS/master_audio.sh" out/smoke_th.mp4 out/smoke_th_master.mp4
  echo "SMOKE OK -> $TOOLS/remotion/out/smoke_th_master.mp4"
fi

if [ "${1:-}" = "--selftest" ]; then
  bash "$TOOLS/selftest_takes.sh"
fi
