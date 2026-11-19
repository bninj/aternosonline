#!/usr/bin/env python3
"""Build a synthetic multi-take talking-head rush for testing the take pipeline.

Speech is espeak-ng TTS laid out like a real recording session (with the problems a real take has), mixed over a
pink-noise room tone at 48 kHz, then muxed onto a 4K HLG HEVC clip at 29.97 fps (iPhone-like timing drift) made from
a still portrait (slow drift so frames differ).

Takes laid out (script in <out>/script.txt):
  L1  "Data is the fuel of AI."                                   one clean attempt
  L2  false start "At DDN, we build the" ... then a full attempt   -> expect attempt 2
  L3  attempt with a filler "um" (4 dB quieter) ...
  L4  attempt with a 1.6 s hesitation mid-line ... 2.2 s pause ...
  L3+L4 said again cleanly as one continuous run (0.45 s apart)  -> expect attempt 2 of both
Writes <out>/expected.json with the expected picks and the true word times of every phrase.

usage: make_test_takes.py OUTDIR [--portrait test/portrait.jpg] [--res 3840x2160] [--no-video]
"""
import argparse, json, os, subprocess, tempfile
import numpy as np

SR = 48000
SCRIPT = ["Data is the fuel of AI.",
          "At DDN, we build the infrastructure that keeps every GPU fully utilized.",
          "Our platform moves data at the speed your models demand.",
          "That is why the world's largest AI factories run on DDN."]
# in recording order: (text for espeak, pause after in s, gain dB, espeak speed, pitch, label)
TAKES = [
    ("Data is the fuel of A I.", 1.2, 0, 150, 50, "L1a"),
    ("At D D N, we build the", 0.6, 0, 160, 50, "L2a_falsestart"),
    ("At D D N, we build the infrastructure that keeps every G P U fully utilized.", 1.0, 0, 150, 55, "L2b"),
    ("Our platform,", 0.25, -4, 165, 45, "L3a_1"),
    ("um,", 0.35, -4, 120, 40, "L3a_filler"),
    ("moves data at the speed your models demand.", 1.2, -4, 165, 45, "L3a_2"),
    ("That is why", 1.6, -1, 150, 48, "L4a_1"),                          # 1.6 s hesitation mid-line
    ("the world's largest A I factories run on D D N.", 2.2, -1, 150, 48, "L4a_2"),   # long pause after
    ("Our platform moves data at the speed your models demand.", 0.45, 0, 150, 55, "L3b"),
    ("That is why the world's largest A I factories run on D D N.", 1.0, 0, 150, 55, "L4b_run"),
]
EXPECTED = {"1": 0, "2": 1, "3": 1, "4": 1}   # unit id -> attempt index (0-based, in time order)


def tts(text, speed, pitch, tmp):
    p = os.path.join(tmp, "t.wav")
    subprocess.run(["espeak-ng", "-v", "en-us", "-s", str(speed), "-p", str(pitch), "-w", p, text], check=True)
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    x = np.frombuffer(pcm, np.float32).astype(np.float64)
    # trim espeak's own leading/trailing silence so our pauses are exact
    nz = np.where(np.abs(x) > 0.01)[0]
    return x[max(nz[0] - 240, 0):nz[-1] + 480] if len(nz) else x


def pink(n, rng):
    w = rng.standard_normal(n)
    f = np.fft.rfft(w); k = np.arange(len(f)); k[0] = 1
    y = np.fft.irfft(f / np.sqrt(k), n)
    return y / np.std(y)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out"); ap.add_argument("--portrait", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "test", "portrait.jpg"))
    ap.add_argument("--res", default="3840x2160"); ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    parts, pos, log = [np.zeros(int(0.8 * SR))], 0.8, []
    with tempfile.TemporaryDirectory() as tmp:
        for text, pause, gdb, spd, pit, lab in TAKES:
            x = tts(text, spd, pit, tmp) * 10 ** (gdb / 20) * 0.5
            log.append({"label": lab, "text": text, "start": round(pos, 3), "end": round(pos + len(x) / SR, 3)})
            parts += [x, np.zeros(int(pause * SR))]; pos += len(x) / SR + pause
    y = np.concatenate(parts + [np.zeros(int(0.6 * SR))])
    y += pink(len(y), rng) * 10 ** (-58 / 20)          # room tone ~ -58 dBFS RMS
    y = np.clip(y, -1, 1)
    wav = os.path.join(a.out, "rush.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f64le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "pcm_s16le", wav],
                   input=y.tobytes(), check=True)
    open(os.path.join(a.out, "script.txt"), "w").write("\n".join(SCRIPT) + "\n")
    json.dump({"expected_picks": EXPECTED, "phrases": log, "duration": len(y) / SR,
               "notes": "attempt indices are 0-based, in time order, per script unit"},
              open(os.path.join(a.out, "expected.json"), "w"), indent=1)
    print(f"audio {len(y) / SR:.2f} s -> {wav}")
    if a.no_video:
        return
    w, h = a.res.split("x")
    dur = len(y) / SR
    mov = os.path.join(a.out, "rush_hlg.mov")
    # sRGB still -> linear light, +0.7 stop so skin/highlights go above HLG reference white, -> HLG BT.2020 10-bit
    vf = (f"scale=-2:{h}:flags=lanczos,pad={w}:{h}:(ow-iw)/2:0:color=0x202020,"
          f"crop={w}-16:{h}-16:8+6*sin(t/3):8+6*cos(t/4),scale={w}:{h},"
          "noise=alls=3:allf=t,"
          "format=gbrp,zscale=tin=iec61966-2-1:min=gbr:pin=bt709:rin=pc:t=linear:p=bt709:m=gbr:r=pc:npl=203,"
          "format=gbrpf32le,exposure=exposure=0.7,"
          "zscale=tin=linear:pin=bt709:min=gbr:rin=pc:t=arib-std-b67:p=bt2020:m=bt2020nc:r=tv:npl=203,format=yuv420p10le")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", "30000/1001", "-i", a.portrait, "-i", wav,
                    "-t", f"{dur:.3f}", "-vf", vf, "-r", "30000/1001",
                    "-c:v", "libx265", "-preset", "ultrafast", "-crf", "24", "-pix_fmt", "yuv420p10le",
                    "-x265-params", "colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc:log-level=error",
                    "-color_primaries", "bt2020", "-color_trc", "arib-std-b67", "-colorspace", "bt2020nc",
                    "-tag:v", "hvc1", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest", mov], check=True)
    print(f"video -> {mov}")


if __name__ == "__main__":
    main()
