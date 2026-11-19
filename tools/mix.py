#!/usr/bin/env python3
"""Final mix: voice (already mastered to about -16 LUFS) + music bed (ducked under speech) + positioned SFX.
usage: mix.py VOICE.wav MUSIC.wav OUT.wav [--sfx file@time@gainDB ...] [--music-gain DB] [--duck DB] [--dur 80]
- Music sits about 20 dB under the voice while he speaks (sidechain from the voice), lifting about 5 dB in gaps.
- SFX are low-passed and placed at their times, gain relative to full scale (about -26 dB under dialogue peaks).
- Fade the music under 'Thank you' is the composer's job; the mix only ducks.
- Master: -15 LUFS integrated, true peak -1.0 dBTP (laptop friendly), 48 kHz 24-bit.
"""
import json, subprocess, sys

args = sys.argv[1:]
voice, music, out = args[0], args[1], args[2]
def opt(name, default):
    return args[args.index(name) + 1] if name in args else default
mg = float(opt("--music-gain", "-6"))
dur = float(opt("--dur", "80"))
sfx = [a.split("@") for i, a in enumerate(args) if i > 0 and args[i - 1] == "--sfx"]

inputs = ["-i", voice, "-i", music]
fc = [f"[0:a]apad=whole_dur={dur},asplit=2[v][key]",
      f"[1:a]volume={mg}dB,atrim=0:{dur}[m0]",
      # duck the music with the voice as key: about 6 dB extra reduction while he talks, smooth release
      "[m0][key]sidechaincompress=threshold=0.02:ratio=6:attack=25:release=450:knee=4:makeup=1[m]"]
mixins = ["[v]", "[m]"]
for k, (f, t, g) in enumerate(sfx):
    inputs += ["-i", f]
    ms = int(float(t) * 1000)
    fc.append(f"[{k + 2}:a]lowpass=f=9000,volume={g}dB,adelay={ms}|{ms},apad=whole_dur={dur}[s{k}]")
    mixins.append(f"[s{k}]")
fc.append("".join(mixins) + f"amix=inputs={len(mixins)}:normalize=0:duration=first,atrim=0:{dur}[mix]")
graph = ";".join(fc)

def run(extra):
    return subprocess.run(["ffmpeg", "-hide_banner", "-y", *inputs, "-filter_complex", graph + extra, *([] if "null" in extra else [])],
                          capture_output=True, text=True)

# pass 1: measure loudness of the mix
p = subprocess.run(["ffmpeg", "-hide_banner", *inputs, "-filter_complex", graph + ";[mix]loudnorm=I=-15:TP=-1.0:LRA=9:print_format=json[o]",
                    "-map", "[o]", "-f", "null", "-"], capture_output=True, text=True)
j = json.loads(p.stderr[p.stderr.rfind("{"):p.stderr.rfind("}") + 1])
ln = (f"loudnorm=I=-15:TP=-1.0:LRA=9:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
      f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", graph + f";[mix]{ln},aresample=48000[o]",
                "-map", "[o]", "-c:a", "pcm_s24le", out], check=True)
r = subprocess.run(["ffmpeg", "-hide_banner", "-i", out, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
print("\n".join(l for l in r.splitlines()[-12:] if "I:" in l or "Peak:" in l or "LRA:" in l))
