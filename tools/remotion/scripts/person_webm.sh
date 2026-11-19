#!/usr/bin/env bash
# Person RGBA clip for depth layering: plate frames [FROM, TO) + matte2 alpha PNGs -> VP9 webm with alpha.
# usage: scripts/person_webm.sh plate.mp4 FROM TO matte_dir out.webm
set -e
P=$1; FROM=$2; TO=$3; M=$4; O=$5
ffmpeg -v error -y -i "$P" -framerate 30 -i "$M/a_%06d.png" -filter_complex \
  "[0:v]select='between(n\,$FROM\,$((TO-1)))',setpts=N/30/TB,format=rgba[v];[1:v]format=gray,scale=${W:-2304}:${H:-1296}:flags=lanczos[a];[v][a]alphamerge,format=yuva420p[o]" \
  -map "[o]" -frames:v $((TO-FROM)) -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 24 -row-mt 1 -deadline good -cpu-used 4 -auto-alt-ref 0 "$O"
