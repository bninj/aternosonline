#!/usr/bin/env python3
"""Re-cut the blurred plate (rendered on timeline_v3 segments) to the tighter timeline_v4 pieces, frame-exact.
Every v4 piece's picture range [vin, vout) lies inside one v3 segment's [vin, vout) from the same source clip.
usage: derive_blur_v4.py OLD_TIMELINE NEW_TIMELINE OLD_PLATE_DIR OUT_DIR
"""
import json, os, subprocess, sys

old = json.load(open(sys.argv[1])); new = json.load(open(sys.argv[2])); OLD = sys.argv[3]; OUT = sys.argv[4]
os.makedirs(OUT, exist_ok=True)
parts = []
for i, s in enumerate(new):
    clip = os.path.basename(s["src"])
    cands = [j for j, o in enumerate(old) if os.path.basename(o["src"]) == clip and o["vin"] - 1e-3 <= s["vin"] and s["vout"] <= o["vout"] + 1 / 30]
    if not cands: sys.exit(f"piece {i} ({clip} {s['vin']:.3f}-{s['vout']:.3f}) is not inside any old segment")
    j = cands[0]; o = old[j]
    off = round((s["vin"] - o["vin"]) * 30)
    n = round(s["vend"] * 30) - round(s["vstart"] * 30)
    src = f"{OLD}/seg{j:02d}.mp4"; dst = f"{OUT}/piece{i:02d}.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-vf", f"select='between(n\\,{off}\\,{off + n - 1})',setpts=N/30/TB",
                    "-frames:v", str(n), "-an", "-r", "30", "-c:v", "libx264", "-crf", "14", "-preset", "medium",
                    "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", dst], check=True)
    got = int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", dst],
                             capture_output=True, text=True).stdout.strip())
    print(f"piece {i:02d} <- seg{j:02d} offset {off} frames {n} (got {got})", flush=True)
    assert got == n, (i, got, n)
    parts.append(dst)
with open(f"{OUT}/list.txt", "w") as f:
    for p in parts: f.write(f"file '{os.path.abspath(p)}'\n")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{OUT}/list.txt", "-c", "copy", f"{OUT}/plate.mp4"], check=True)
print("plate ->", f"{OUT}/plate.mp4")
