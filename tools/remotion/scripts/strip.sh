#!/usr/bin/env bash
# Frame strip: scripts/strip.sh video.mp4 out.jpg START END STEP [crop=w:h:x:y] [cols]
set -e
V=$1; O=$2; S=$3; E=$4; STEP=$5; CROP=${6:-1920:1080:0:0}; COLS=${7:-6}
N=$(( (E - S) / STEP + 1 )); ROWS=$(( (N + COLS - 1) / COLS ))
ffmpeg -v error -y -i "$V" -vf "select='between(n\,$S\,$E)*not(mod(n-$S\,$STEP))',crop=$CROP,scale=420:-2,drawtext=text='f%{eif\:t*30+0.5\:d}':x=6:y=6:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.6,tile=${COLS}x${ROWS}:padding=3" -frames:v 1 -vsync vfr "$O"
