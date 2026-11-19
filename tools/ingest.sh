#!/bin/bash
# ingest one clip: 1080p proxy, 16k mono wav, contact sheet (1 frame / 4 s)
f="$1"; b=$(basename "$f" .MOV); D=/home/user/ddn-project/footage
ffmpeg -loglevel error -y -i "$f" -vf "scale=1920:1080:flags=lanczos,fps=30" -c:v libx264 -preset veryfast -crf 20 -g 30 -c:a aac -b:a 160k "$D/proxy/$b.mp4"
ffmpeg -loglevel error -y -i "$f" -vn -ac 1 -ar 16000 "$D/audio/$b.wav"
ffmpeg -loglevel error -y -i "$D/proxy/$b.mp4" -vf "fps=1/4,scale=480:-1,drawtext=text='%{pts\:hms}':x=8:y=8:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6,tile=6x8" -frames:v 1 "$D/sheets/$b.jpg"
echo "done $b"
