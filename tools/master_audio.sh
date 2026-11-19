#!/usr/bin/env bash
# Loudness master: speech cleanup -> measured gain to target LUFS -> brickwall limiter (~-1.5 dBTP). Video stream copied.
# Usage: master_audio.sh in.mp4 out.mp4 [target_lufs=-14]
# (ffmpeg's loudnorm in linear mode refuses to raise gain when peaks would exceed TP and silently lands 1-2 LU short
#  on peaky speech; measured gain + alimiter hits the target reliably.)
set -euo pipefail
IN="$1"; OUT="$2"; I="${3:--14}"
PRE="highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=2"
measure() { ffmpeg -hide_banner -nostats -i "$1" -map 0:a:0 -af "$2,ebur128=peak=true" -f null - 2>&1 | awk '/Integrated loudness:/{f=1} f&&/ I:/{print $2; exit}'; }
CUR=$(measure "$IN" "$PRE")
GAIN=$(python3 -c "print(round($I - ($CUR), 2))")
echo "measured $CUR LUFS after cleanup -> gain ${GAIN} dB"
render() { ffmpeg -v error -y -i "$IN" -map 0:v? -map 0:a:0 -c:v copy \
  -af "$PRE,volume=${1}dB,alimiter=limit=0.84:attack=2:release=60:level=false,aresample=48000" \
  -c:a aac -b:a 256k -movflags +faststart "$OUT"; }
render "$GAIN"
# the limiter shaves ~0.5-1 LU off peaky speech: re-measure and compensate (up to 3 passes, stop within 0.2 LU)
for pass in 1 2 3; do
  OUTI=$(measure "$OUT" "anull")
  python3 -c "import sys; sys.exit(0 if abs(($I)-($OUTI))<=0.2 else 1)" && break
  GAIN=$(python3 -c "print(round($GAIN + ($I) - ($OUTI), 2))")
  echo "pass$pass $OUTI LUFS -> corrected gain ${GAIN} dB"
  render "$GAIN"
done
ffmpeg -hide_banner -nostats -i "$OUT" -map 0:a:0 -af ebur128=peak=true -f null - 2>&1 | awk '/Summary/{f=1} f&&/ I:|Peak:/{print}'
