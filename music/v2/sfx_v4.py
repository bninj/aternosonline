#!/usr/bin/env python3
"""Build the 5 dampened SFX from RECORDED CC0 sources (no synthesis).
  sfx_v3.py [edit_v3.json] [--out DIR]
Each file is written starting at t=0 (its placement time is in sfx_timing.json),
plus sfx_all_positioned.wav (80 s, every SFX already placed).
Levels: peak = (voice dialogue-peak reference) - N dB, where the reference is the
95th percentile of 50 ms peaks of edit/voice_v1.wav normalised to -16 LUFS."""
import os, sys, json, argparse
import numpy as np
import soundfile as sf
from scipy import signal
import pyloudnorm as pyln

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import samplers as S
from compose_v2 import hp, lp, peaking, make_ir, reverb

SR = 48000
BSB = os.path.join(S.CAND, "bigsoundbank")
VOICE = "/home/user/ddn-project/edit/voice_v1.wav"


def voice_ref_db():
    v, sr = sf.read(VOICE)
    v = v * 10 ** ((-16 - pyln.Meter(sr).integrated_loudness(v)) / 20)
    w = int(0.05 * sr)
    pk = np.array([np.abs(v[i:i + w]).max() for i in range(0, len(v) - w, w)])
    return 20 * np.log10(np.percentile(pk, 95))


def rd(path):
    x, sr = sf.read(path, always_2d=True)
    assert sr == SR
    if x.shape[1] == 1:
        x = np.repeat(x, 2, 1)
    S.USED.add(path)
    return x


def fade(x, fin, fout):
    n = len(x)
    a = int(fin * SR); b = int(fout * SR)
    e = np.ones(n)
    if a:
        e[:a] = np.sin(np.linspace(0, np.pi / 2, a)) ** 2      # smooth swell-in
    if b:
        e[-b:] *= np.cos(np.linspace(0, np.pi / 2, b)) ** 2
    return x * e[:, None]


def trim_lead(x, thr=0.01):
    m = np.abs(x).max(1)
    i0 = int(np.argmax(m > thr * m.max()))
    return x[max(0, i0 - int(0.002 * SR)):]


def level(x, peak_db):
    return x * 10 ** (peak_db / 20) / np.abs(x).max()


def build(ref):
    room = make_ir(0.8, 1.2, 1, 5000)          # same small room as the music
    out = {}
    # 1. timer click: MacBook trackpad click (BigSoundBank s1740), softened
    x = trim_lead(rd(os.path.join(BSB, "macbook-trackpad-simple-click-s1740.flac")))[: int(0.18 * SR)]
    x = hp(x, 300); x = lp(x, 3500, 2); x = peaking(x, 2500, -3, 1.0)
    x = fade(x, 0.004, 0.08)
    x = reverb(np.vstack([x, np.zeros((int(0.3 * SR), 2))]), room, 0.15)
    out["click"] = x
    # 2-4. airy swishes: BigSoundBank rope whooshes #4, #7, #3 (stereo ORTF),
    # slowed attack (>=150 ms swell), rolled off above ~6 kHz, short tail
    # 2-4. airy swells (v4: no rope whoosh): the rising part of a soft mallet-roll
    # cymbal swell (VCSL, recorded) + a REVERSED soft-mallet vibraphone note (VCSL),
    # 0.55-0.7 s, smooth sin^2 rise, no transient at the top (75 ms cos^2 release
    # starts just before the roll's own peak), low-passed at 6 kHz, warm.
    VIB = ("Idiophones", "Struck Idiophones", "Vibraphone", "Soft Mallets")
    for name, cy, vn, L in [("whoosh_chart", "susCymb1_cresc_1.5s.wav", "Vibes_soft_A2_v1_rr1_Main.wav", 0.60),
                            ("whoosh_gauge", "susCymb1_cresc_2s.wav", "Vibes_soft_E3_v1_rr2_Main.wav", 0.55),
                            ("whoosh_ask", "susCymb1_cresc_4s.wav", "Vibes_soft_A2_v1_rr1_Main.wav", 0.70)]:
        c = S.cymbal(cy)
        cp = int(np.argmax(np.abs(c).max(1)))
        stop = cp - int(0.03 * SR)                     # stop before the roll's peak: no spike
        c = c[max(0, stop - int(L * SR)): stop].copy()
        c = hp(c, 700); c = lp(c, 6000, 4)
        v = S.load(S.vcsl(*VIB, vn))[: int(1.6 * SR)][::-1].copy()   # reversed note: swells into the moment
        v = v[-int(L * SR):]
        v = hp(v, 180); v = lp(v, 5000, 2)
        n = min(len(c), len(v))
        y = c[-n:] / np.abs(c).max() + 0.55 * v[-n:] / np.abs(v).max()
        t = np.arange(n) / SR
        rise = np.sin(0.5 * np.pi * np.clip(t / (n / SR), 0, 1)) ** 2            # whole-length smooth swell
        y *= rise[:, None]
        tail = int(0.075 * SR)                                                  # soft release after the top
        y = np.vstack([y, y[-1:] * np.cos(np.linspace(0, np.pi / 2, tail))[:, None] ** 2])
        y = peaking(y, 2500, -2, 0.8)
        y = reverb(np.vstack([y, np.zeros((int(0.5 * SR), 2))]), room, 0.18)
        y[-int(0.3 * SR):] *= np.linspace(1, 0, int(0.3 * SR))[:, None]
        out[name] = y
    # 5. end-card chime: soft vibraphone D5 + hand chime D5 (VCSL, recorded), warm
    vib = S.load(S.vcsl("Idiophones", "Struck Idiophones", "Vibraphone", "Soft Mallets", "Vibes_soft_D4_v1_rr1_Main.wav"))
    hc = S.load(S.vcsl("Idiophones", "Struck Idiophones", "Hand Chimes", "sus_D4_r01_main.wav"))
    n = int(2.6 * SR)
    x = np.zeros((n, 2))
    x[: min(n, len(vib))] += vib[:n] / np.abs(vib).max()
    x[: min(n, len(hc))] += 0.45 * hc[:n] / np.abs(hc).max()
    x = hp(x, 200); x = lp(x, 4000, 2); x = peaking(x, 2500, -2, 1.0)
    x = fade(x, 0.025, 1.4)                        # rounded onset (25 ms), short tail
    x = reverb(np.vstack([x, np.zeros((int(0.5 * SR), 2))]), room, 0.2)
    out["chime"] = x
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timeline", nargs="?", default=os.path.join(HERE, "edit_v4.json"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "out_v4"))
    a = ap.parse_args()
    cfg = json.load(open(a.timeline))
    ref = voice_ref_db()
    below = cfg["sfx_level_below_dialogue_peak_db"]
    snd = build(ref)
    place = {"click": cfg["sfx"]["click"][0], "whoosh_chart": cfg["sfx"]["whoosh"][0],
             "whoosh_gauge": cfg["sfx"]["whoosh"][1], "whoosh_ask": cfg["sfx"]["whoosh"][2],
             "chime": cfg["sfx"]["chime"][0]}
    total = int(cfg["end"] * SR)
    allp = np.zeros((total, 2))
    info = {}
    for k, x in snd.items():
        kind = "whoosh" if k.startswith("whoosh") else k
        pk_db = ref - below.get(k, below.get(kind))
        x = level(x, pk_db)
        sf.write(os.path.join(a.out, f"sfx_{k}.wav"), x, SR, subtype="PCM_24")
        # whooshes: the swell PEAK lands on the graphic time (offset = time - peak position)
        pkpos = int(np.argmax(np.abs(x).max(1))) / SR if kind == "whoosh" else 0.0
        start = place[k] - pkpos
        i = int(round(start * SR))
        seg = x[: total - i]
        allp[i: i + len(seg)] += seg
        info[k] = dict(file=f"sfx_{k}.wav", place_at=round(start, 3), event_time=place[k],
                       peak_offset_in_file=round(pkpos, 3), peak_dbfs=round(pk_db, 1),
                       below_dialogue_peak_db=below.get(k, below.get(kind)), length_s=round(len(x) / SR, 2))
    sf.write(os.path.join(a.out, "sfx_all_positioned.wav"), allp, SR, subtype="PCM_24")
    info["_reference"] = dict(dialogue_peak_ref_dbfs=round(ref, 2),
                              definition="95th pct of 50 ms peaks of voice_v1.wav at -16 LUFS integrated")
    info["_sources"] = sorted(os.path.relpath(p, S.CAND) for p in S.USED)
    json.dump(info, open(os.path.join(a.out, "sfx_timing.json"), "w"), indent=1)
    tp = os.path.join(a.out, "timing.json")
    if os.path.exists(tp):                      # also record placement in timing.json
        t = json.load(open(tp))
        t["sfx"] = {k: v for k, v in info.items() if not k.startswith("_")}
        t["sfx_reference"] = info["_reference"]; t["sfx_sources"] = info["_sources"]
        json.dump(t, open(tp, "w"), indent=1)
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
