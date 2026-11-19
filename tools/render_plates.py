#!/usr/bin/env python3
"""Render the picture plate: per segment background blur (from 4K source) + grade, then concat to one video.
usage: render_plates.py timeline.json grade.json OUTDIR [--size 2304x1296] [--only i,j] [--noblur]
Each segment is rendered with exactly round((out-in)*30) frames so it lines up with the conformed voice track.
Plate is oversampled (default 2304x1296 = 1.2x of 1080p) so Remotion can push in up to ~20% without upscaling.
"""
import json, os, subprocess, sys

tl = json.load(open(sys.argv[1])); grade = json.load(open(sys.argv[2])); OUT = os.path.abspath(sys.argv[3])
size = sys.argv[sys.argv.index("--size") + 1] if "--size" in sys.argv else "2304x1296"
only = set(int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
noblur = "--noblur" in sys.argv
os.makedirs(OUT, exist_ok=True)
BLUR = "/home/user/ddn-project/tools/blur"
KEEP = {c: f"keep/{c}.json" for c in ["IMG_3845","IMG_3848","IMG_3850","IMG_3851","IMG_3852","IMG_3853","IMG_3854","IMG_3856","IMG_3858","IMG_3860"]}
W, H = size.split("x")
segs = []
for i, s in enumerate(tl):
    clip = os.path.basename(s["src"]).replace(".MOV", "")
    src = "/home/user/ddn-project/footage/raw/" + clip + ".MOV"
    s = dict(s); s["in"], s["out"] = s.get("vin", s["in"]), s.get("vout", s["out"])  # picture in/out (J-cut aware)
    n = round(s["vend"] * 30) - round(s["vstart"] * 30) if "vstart" in s else round((s["out"] - s["in"]) * 30)
    raw = f"{OUT}/seg{i:02d}_blur.mp4"; fin = f"{OUT}/seg{i:02d}.mp4"; segs.append(fin)
    if only is not None and i not in only: continue
    if noblur:
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{s['in']:.4f}", "-i", src, "-frames:v", str(n), "-an",
                        "-vf", f"scale={W}:{H}:flags=lanczos", "-c:v", "libx264", "-crf", "14", "-preset", "fast", raw], check=True)
    else:
        cmd = ["/home/user/ddn-project/tools/venv/bin/python", f"{BLUR}/bgblur.py", "--in", src, "--out", raw,
               "--start", f"{s['in']:.4f}", "--end", f"{s['out'] + 0.1:.4f}", "--size", size, "--strength", "1.0",
               "--no-audio", "--crf", "14"]
        k = KEEP.get(clip)
        if k and os.path.exists(f"{BLUR}/{k}"): cmd += ["--keep-polygon", f"{BLUR}/{k}"]
        print("blur", i, clip, s["in"], s["out"], flush=True)
        subprocess.run(cmd, check=True, cwd=BLUR)
    # grade + exact frame count + square pixels, BT.709 tags
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", raw, "-frames:v", str(n), "-an",
                    "-vf", grade[str(i)]["filter"] + ",setsar=1,format=yuv420p",
                    "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                    "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-r", "30", fin], check=True)
    os.remove(raw)
    print("done", i, n, "frames", flush=True)

if only is None or "--concat" in sys.argv:
    with open(f"{OUT}/list.txt", "w") as f:
        for p in segs: f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{OUT}/list.txt", "-c", "copy",
                    f"{OUT}/plate.mp4"], check=True)
    print("plate ->", f"{OUT}/plate.mp4")
