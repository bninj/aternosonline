#!/bin/bash
# strip.sh OUT.jpg CLIP START END LABEL [N]  -> one row of N frames
out=$1; c=$2; s=$3; e=$4; tag=$5; n=${6:-8}
d=$(mktemp -d /tmp/claude-0/-home-user/dc066354-8ace-5f9c-97bb-fc22fd7a3463/scratchpad/strip.XXXX)
i=0
for t in $(python3 -c "print(' '.join('%.2f'%($s+($e-$s)*k/($n-1)) for k in range($n)))"); do
  ffmpeg -loglevel error -y -ss $t -i /home/user/ddn-project/footage/proxy/$c.mp4 -frames:v 1 \
    -vf "scale=320:-1,drawtext=text='$tag $t':x=4:y=4:fontsize=16:fontcolor=yellow:box=1:boxcolor=black@0.6" $d/f_$i.jpg
  i=$((i+1))
done
ffmpeg -loglevel error -y -i $d/f_%d.jpg -vf tile=${n}x1 "$out"
