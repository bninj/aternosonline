#!/usr/bin/env python3
"""Conform an EDL (JSON) into one clip: tone-mapped/scaled video with hard cuts + a smoothed voice track.

EDL: {"fps": "30000/1001", "clips": [{"src": "footage/IMG_0001.MOV", "in": 12.34, "out": 18.90, "take": "A#1"}, ...]}
     (refine_cuts.py writes frame-snapped in/out on the source's real PTS; "take" groups pieces for level matching,
      default = one take per clip entry)
usage:
  conform.py edl.json out.mp4 [--res 1920x1080|3840x2160] [--tonemap [auto|hable|mobius|lut|none]] [--crf 18]
             [--xfade-ms 35] [--no-level-match] [--no-roomtone] [--roomtone-gain 0.7] [--audio-out voice.wav]

Audio (re-implemented from kurbaitaev/ghost-editor scripts/voice_smooth.py, MIT (c) 2026 kurbaitaev):
  * every join gets an equal-power (sin/cos) crossfade of --xfade-ms centred on the edit point, using REAL audio
    handles from the source (each piece extended by xfade/2 on both sides), so total length stays exactly sum(out-in)
    and nothing moves in time; joins between source-contiguous pieces get no fade;
  * per-take level match: 70th percentile of 10 ms speech levels (> -40 dB) moved to the median of all takes,
    clamped +-3 dB, one constant gain per take;
  * room-tone bed: the quietest flat 1.5 s inside the used source range, looped with 200 ms crossfades at x0.7 under
    the whole voice, so gaps never fall to digital silence.
Video: per piece -ss/-t on the source, tone-map (tonemap.py chains, all ending in setparams=bt709), CFR at the EDL/source
rate, BT.709 tags, -g 30. Picture cuts are hard cuts at exactly the same snapped times as the audio.
"""
import argparse, json, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audiolib as AL
import tonemap as TM

SR = 48000


def speech_db(x):
    e = AL.levels(x, SR)
    return float(np.percentile(e[e > -40], 70)) if (e > -40).sum() > 5 else None


def roomtone(src, lo, hi, n_out, gain):
    """quietest flat 1.5 s in src[lo:hi], looped with 200 ms crossfades to n_out samples"""
    step = int(0.1 * SR); W15 = 15
    fr = src[:len(src) // step * step].reshape(-1, step); r = np.sqrt((fr ** 2).mean(1)); pk = np.abs(fr).max(1)
    best, bt = None, 1e9
    for s0 in range(int(lo * 10), max(int(hi * 10) - W15, int(lo * 10))):
        rr = r[s0:s0 + W15]
        if len(rr) < W15: break
        m = float(np.sqrt(np.mean(rr ** 2)))
        if 1e-6 < m < bt and pk[s0:s0 + W15].max() < 0.06 and rr.max() < 3 * np.median(rr):
            bt, best = m, src[s0 * step:(s0 + W15) * step].copy()
    if best is None: return np.zeros(n_out), None
    cf = int(0.2 * SR); fade = np.sin(np.linspace(0, np.pi / 2, cf)); tone = np.zeros(n_out); p = 0
    while p < n_out:
        seg = best.copy(); seg[:cf] *= fade; seg[-cf:] *= fade[::-1]
        e = min(n_out, p + len(seg)); tone[p:e] += seg[:e - p]; p += len(seg) - cf
    return tone * gain, 20 * np.log10(bt)


def build_audio(clips, xfade_ms=35, level_match=True, room=True, room_gain=0.7, log=print):
    srcs = {}
    for c in clips:
        if c["src"] not in srcs: srcs[c["src"]] = AL.load(c["src"], SR)
    h = xfade_ms / 2000; n = int(round(h * SR))
    ramp = np.sin(np.linspace(0, np.pi / 2, 2 * n)) if n else np.ones(0)

    def take(src, a, b):
        x = srcs[src]; i0, i1 = int(round(a * SR)), int(round(b * SR)); out = np.zeros(i1 - i0)
        s0, s1 = max(0, i0), min(len(x), i1)
        if s1 > s0: out[s0 - i0:s1 - i0] = x[s0:s1]
        return out
    tk = [c.get("take", f"#{k}") for k, c in enumerate(clips)]
    gains = {t: 1.0 for t in tk}
    if level_match:
        lv = {t: speech_db(np.concatenate([take(c["src"], c["in"], c["out"]) for c, u in zip(clips, tk) if u == t])) for t in set(tk)}
        vals = [v for v in lv.values() if v is not None]
        if vals:
            med = float(np.median(vals))
            gains = {t: 1.0 if v is None else 10 ** (np.clip(med - v, -3, 3) / 20) for t, v in lv.items()}
            log("level match: " + ", ".join(f"{t} {lv[t]:.1f} dB -> {20 * np.log10(gains[t]):+.1f}" for t in sorted(lv) if lv[t] is not None))
    L = [c["out"] - c["in"] for c in clips]; N = int(round(sum(L) * SR)); out = np.zeros(N + 2 * n + SR)
    pos = 0.0
    for k, c in enumerate(clips):
        cont_in = k > 0 and clips[k - 1]["src"] == c["src"] and abs(clips[k - 1]["out"] - c["in"]) < 1e-3
        cont_out = k + 1 < len(clips) and clips[k + 1]["src"] == c["src"] and abs(clips[k + 1]["in"] - c["out"]) < 1e-3
        hi_, ho_ = (0 if cont_in or k == 0 else h), (0 if cont_out or k == len(clips) - 1 else h)
        piece = take(c["src"], c["in"] - hi_, c["out"] + ho_) * gains[tk[k]]
        if hi_ and n: piece[:2 * n] *= ramp
        if ho_ and n: piece[-2 * n:] *= ramp[::-1]
        if k == 0 and n: piece[:n] *= np.sin(np.linspace(0, np.pi / 2, n))           # no click at the very start
        if k == len(clips) - 1 and n: piece[-n:] *= np.cos(np.linspace(0, np.pi / 2, n))
        i = int(round((pos - hi_) * SR)) + n                                         # +n: buffer offset for the first handle
        out[i:i + len(piece)] += piece
        pos += L[k]
    out = out[n:n + N]
    if room:
        s0 = clips[0]["src"]; used = [c for c in clips if c["src"] == s0]
        tone, db = roomtone(srcs[s0], min(c["in"] for c in used), max(c["out"] for c in used), N, room_gain)
        if db is None:   # nothing quiet enough inside the used range: search the whole source
            tone, db = roomtone(srcs[s0], 0, len(srcs[s0]) / SR, N, room_gain)
        out += tone
        log(f"room tone: {db:.1f} dBFS RMS bed x{room_gain}" if db is not None else "room tone: no quiet stretch found, skipped")
    return np.clip(out, -1, 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edl"); ap.add_argument("out")
    ap.add_argument("--res", default="1920x1080")
    ap.add_argument("--tonemap", nargs="?", const="hable", default="auto", choices=["auto", "hable", "mobius", "lut", "none"],
                    help="auto (default) = hable when the source is HLG/PQ, plain scale otherwise")
    ap.add_argument("--crf", default="18"); ap.add_argument("--preset", default="veryfast")
    ap.add_argument("--fps", default="auto", help="output rate; auto = EDL 'fps' or the first source's rate")
    ap.add_argument("--xfade-ms", type=float, default=35); ap.add_argument("--no-level-match", action="store_true")
    ap.add_argument("--no-roomtone", action="store_true"); ap.add_argument("--roomtone-gain", type=float, default=0.7)
    ap.add_argument("--audio-out", help="also keep the voice wav")
    a = ap.parse_args()
    E = json.load(open(a.edl)); clips = E["clips"]
    base = os.path.dirname(os.path.abspath(a.edl))
    for c in clips:
        if not os.path.isabs(c["src"]) and not os.path.exists(c["src"]): c["src"] = os.path.join(base, c["src"])
    w, h = a.res.split("x")
    rate = (E.get("fps") if a.fps == "auto" else a.fps) or AL.video_rate(clips[0]["src"]) or "30"
    if a.fps == "auto" and not E.get("fps"): rate = AL.video_rate(clips[0]["src"]) or "30"
    voice = build_audio(clips, a.xfade_ms, not a.no_level_match, not a.no_roomtone, a.roomtone_gain)
    with tempfile.TemporaryDirectory() as tmp:
        wav = a.audio_out or os.path.join(tmp, "voice.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f64le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "pcm_s24le", wav],
                       input=voice.tobytes(), check=True)
        args, fc = ["ffmpeg", "-v", "error", "-y"], []
        for i, c in enumerate(clips):
            tr = TM.transfer_of(c["src"])
            method = {"auto": "hable", "none": "none"}.get(a.tonemap, a.tonemap)
            vchain = TM.chain("hable" if method == "none" else method, w, h, tr if method != "none" else "bt709")
            # -ss 1 ms early: the frame at exactly `in` is kept even if the snapped time was rounded down
            args += ["-ss", f"{max(c['in'] - 0.001, 0):.6f}", "-t", f"{c['out'] - c['in']:.6f}", "-i", c["src"]]
            fc.append(f"[{i}:v:0]{vchain},fps={rate},setpts=PTS-STARTPTS[v{i}]")
        fc.append("".join(f"[v{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=0[v]")
        args += ["-i", wav, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", f"{len(clips)}:a",
                 "-c:v", "libx264", "-preset", a.preset, "-crf", a.crf, *TM.X264_TAGS,
                 "-c:a", "aac", "-b:a", "256k", "-ac", "2", "-movflags", "+faststart", a.out]
        subprocess.run(args, check=True)
    vd = float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration", "-of", "csv=p=0", a.out],
                              capture_output=True, text=True).stdout.strip() or 0)
    print(f"{len(clips)} pieces, voice {len(voice) / SR:.3f} s, video {vd:.3f} s @ {rate} -> {a.out}")


if __name__ == "__main__":
    main()
