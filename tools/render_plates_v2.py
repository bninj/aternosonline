#!/usr/bin/env python3
"""Render the BLURRED picture plate with the v2 blur pipeline (matte2.py + bgblur2.py).

usage: render_plates_v2.py timeline_v3.json grade.json OUTDIR [--size 2304x1296] [--only i,j] [--concat]
                           [--keep-raw DIR]

Same contract as render_plates.py: segment i gets exactly round(vend*30)-round(vstart*30) frames
starting at the picture in-point (vin/vout, J-cut aware), graded with grade[i], BT.709 tags, then
concatenated to OUTDIR/plate.mp4 (frame-for-frame with edit/plates_noblur/plate.mp4).

Two lanes run in parallel: lane A computes the mattes (SAM 2.1 + ViTMatte, the slow part) segment
after segment; lane B renders + grades each segment as soon as its matte is ready. Mattes live in
tools/blur/mattes/segNN and are deleted after the segment is done. Progress: OUTDIR/progress.log.
"""
import json, os, subprocess, sys, threading, time, shutil

tl = json.load(open(sys.argv[1])); grade = json.load(open(sys.argv[2])); OUT = os.path.abspath(sys.argv[3])
size = sys.argv[sys.argv.index("--size") + 1] if "--size" in sys.argv else "2304x1296"
only = set(int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
keep_raw = sys.argv[sys.argv.index("--keep-raw") + 1] if "--keep-raw" in sys.argv else None
os.makedirs(OUT, exist_ok=True)
BLUR = "/home/user/ddn-project/tools/blur"
PY = "/home/user/ddn-project/tools/venv/bin/python"
MATTES = f"{BLUR}/mattes"
LOG = open(f"{OUT}/progress.log", "a", buffering=1)


def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + "\n")


jobs, segs = [], []
for i, s in enumerate(tl):
    clip = os.path.basename(s["src"]).replace(".MOV", "")
    src = "/home/user/ddn-project/footage/raw/" + clip + ".MOV"
    vin, vout = s.get("vin", s["in"]), s.get("vout", s["out"])
    n = round(s["vend"] * 30) - round(s["vstart"] * 30) if "vstart" in s else round((vout - vin) * 30)
    fin = f"{OUT}/seg{i:02d}.mp4"
    segs.append(fin)
    if only is not None and i not in only:
        continue
    keep = f"{BLUR}/keep/{clip}.json"
    jobs.append(dict(i=i, clip=clip, src=src, start=vin, end=vin + (n + 3) / 30.0, n=n, fin=fin,
                     keep=keep if os.path.exists(keep) else None, mdir=f"{MATTES}/seg{i:02d}"))

ready = {}
cv = threading.Condition()
failed = []


def lane_matte():
    for j in jobs:
        ok = os.path.exists(os.path.join(j["mdir"], "meta.json"))
        if not ok:
            t = time.time()
            log(f"matte seg{j['i']:02d} {j['clip']} {j['start']:.3f}-{j['end']:.3f} ({j['n']} frames)")
            cmd = [PY, f"{BLUR}/matte2.py", "--in", j["src"], "--start", f"{j['start']:.4f}", "--end", f"{j['end']:.4f}",
                   "--out", j["mdir"]]
            if j["keep"]:
                cmd += ["--keep", j["keep"]]
            with open(f"{OUT}/seg{j['i']:02d}_matte.log", "w") as lf:
                r = subprocess.run(cmd, cwd=BLUR, stdout=lf, stderr=subprocess.STDOUT)
            ok = r.returncode == 0 and os.path.exists(os.path.join(j["mdir"], "meta.json"))
            log(f"matte seg{j['i']:02d} {'ok' if ok else 'FAILED'} in {time.time()-t:.0f}s")
        with cv:
            ready[j["i"]] = ok
            cv.notify_all()


def lane_render():
    for j in jobs:
        with cv:
            while j["i"] not in ready:
                cv.wait()
            ok = ready[j["i"]]
        if not ok:
            failed.append(j["i"])
            continue
        t = time.time()
        raw = f"{OUT}/seg{j['i']:02d}_blur.mp4"
        cmd = [PY, f"{BLUR}/bgblur2.py", "--in", j["src"], "--out", raw, "--matte", j["mdir"],
               "--start", f"{j['start']:.4f}", "--end", f"{j['end']:.4f}", "--size", size, "--crf", "14"]
        if j["keep"]:
            cmd += ["--keep-polygon", j["keep"]]
        with open(f"{OUT}/seg{j['i']:02d}_render.log", "w") as lf:
            r = subprocess.run(cmd, cwd=BLUR, stdout=lf, stderr=subprocess.STDOUT)
        if r.returncode != 0:
            log(f"render seg{j['i']:02d} FAILED")
            failed.append(j["i"])
            continue
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", raw, "-frames:v", str(j["n"]), "-an",
                        "-vf", grade[str(j["i"])]["filter"] + ",setsar=1,format=yuv420p",
                        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                        "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-r", "30", j["fin"]], check=True)
        if keep_raw:
            os.makedirs(keep_raw, exist_ok=True)
            shutil.move(raw, os.path.join(keep_raw, os.path.basename(raw)))
        else:
            os.remove(raw)
        shutil.rmtree(j["mdir"], ignore_errors=True)
        nf = subprocess.check_output(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                                      "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", j["fin"]]).decode().strip()
        log(f"done seg{j['i']:02d} {j['n']} frames (got {nf}) render {time.time()-t:.0f}s")


ta, tb = threading.Thread(target=lane_matte), threading.Thread(target=lane_render)
t0 = time.time()
ta.start(); tb.start(); ta.join(); tb.join()
log(f"all segments finished in {(time.time()-t0)/60:.1f} min; failed={failed}")

if not failed and (only is None or "--concat" in sys.argv):
    with open(f"{OUT}/list.txt", "w") as f:
        for p in segs:
            f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{OUT}/list.txt", "-c", "copy",
                    f"{OUT}/plate.mp4"], check=True)
    nf = subprocess.check_output(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                                  "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", f"{OUT}/plate.mp4"]).decode().strip()
    log(f"plate -> {OUT}/plate.mp4 ({nf} frames)")
