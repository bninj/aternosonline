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
    for name, f, cy in [("whoosh_chart", "whoosh-4-s1796.flac", "susCymb1_cresc_1.5s.wav"),
                        ("whoosh_gauge", "whoosh-7-s1800.flac", "susCymb2_cresc_2.5s2.wav"),
                        ("whoosh_ask", "whoosh-3-s1795.flac", "susCymb1_cresc_2s.wav")]:
        x = trim_lead(rd(os.path.join(BSB, f)), 0.02)
        x = hp(x, 180); x = lp(x, 6000, 4)
        # "air" layer: the last 0.45 s of a soft mallet-roll cymbal swell (VCSL), its
        # peak aligned with the whoosh peak, then a quick 120 ms release
        c = S.cymbal(cy)
        cp = int(np.argmax(np.abs(c).max(1)))
        c = c[max(0, cp - int(0.45 * SR)): cp + int(0.3 * SR)].copy()
        cpk = min(cp, int(0.45 * SR))
        c[cpk:] *= np.exp(-np.arange(len(c) - cpk) / (0.06 * SR))[:, None]
        c = hp(c, 1500); c = lp(c, 6000, 4)
        wp = int(np.argmax(np.abs(x).max(1)))
        sh = wp - cpk
        if sh < 0:
            x = np.vstack([np.zeros((-sh, 2)), x]); sh = 0
        n = max(len(x), sh + len(c))
        y = np.zeros((n, 2)); y[: len(x)] += x
        y[: len(x)] *= 0.55
        y[sh: sh + len(c)] += 1.0 * c * np.abs(x).max() / np.abs(c).max()
        x = peaking(y, 2500, -3, 0.8)
        pk = int(np.argmax(np.abs(x).max(1)))
        pre = int(0.16 * SR)                       # lead-in so the swell is >= 160 ms
        x = np.vstack([np.zeros((max(0, pre - pk), 2)), x])
        x = fade(x, 0.16 + max(0, pk / SR - 0.16) * 0.5, 0.25)
        x = reverb(np.vstack([x, np.zeros((int(0.4 * SR), 2))]), room, 0.12)
        out[name] = x
    # 5. end-card chime: soft vibraphone D5 + hand chime D5 (VCSL, recorded), warm
    vib = S.load(S.vcsl("Idiophones", "Struck Idiophones", "Vibraphone", "Soft Mallets", "Vibes_soft_D4_v1_rr1_Main.wav"))
    hc = S.load(S.vcsl("Idiophones", "Struck Idiophones", "Hand Chimes", "sus_D4_r01_main.wav"))
    n = int(2.6 * SR)
    x = np.zeros((n, 2))
    x[: min(n, len(vib))] += vib[:n] / np.abs(vib).max()
    x[: min(n, len(hc))] += 0.45 * hc[:n] / np.abs(hc).max()
    x = hp(x, 200); x = lp(x, 4000, 2); x = peaking(x, 2500, -2, 1.0)
    x = fade(x, 0.012, 1.4)                        # rounded onset, short tail
    x = reverb(np.vstack([x, np.zeros((int(0.5 * SR), 2))]), room, 0.2)
    out["chime"] = x
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timeline", nargs="?", default=os.path.join(HERE, "edit_v3.json"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "out_v3"))
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
        pk_db = ref - below[kind]
        x = level(x, pk_db)
        if kind == "whoosh":
            # match loudness to the first whoosh (peaks differ in shape); cap peak at -24 dBFS
            lm = pyln.Meter(SR, block_size=0.2)
            lx = lm.integrated_loudness(x)
            if "_wref" not in globals():
                globals()["_wref"] = lx
            x = x * 10 ** ((globals()["_wref"] - lx) / 20)
            x = x * min(1.0, 10 ** (-24 / 20) / np.abs(x).max())
            pk_db = 20 * np.log10(np.abs(x).max())
        sf.write(os.path.join(a.out, f"sfx_{k}.wav"), x, SR, subtype="PCM_24")
        # whooshes: the swell PEAK lands on the graphic time (offset = time - peak position)
        pkpos = int(np.argmax(np.abs(x).max(1))) / SR if kind == "whoosh" else 0.0
        start = place[k] - pkpos
        i = int(round(start * SR))
        seg = x[: total - i]
        allp[i: i + len(seg)] += seg
        info[k] = dict(file=f"sfx_{k}.wav", place_at=round(start, 3), event_time=place[k],
                       peak_offset_in_file=round(pkpos, 3), peak_dbfs=round(pk_db, 1),
                       below_dialogue_peak_db=below[kind], length_s=round(len(x) / SR, 2))
    sf.write(os.path.join(a.out, "sfx_all_positioned.wav"), allp, SR, subtype="PCM_24")
    info["_reference"] = dict(dialogue_peak_ref_dbfs=round(ref, 2),
                              definition="95th pct of 50 ms peaks of voice_v1.wav at -16 LUFS integrated")
    info["_sources"] = sorted(os.path.relpath(p, S.CAND) for p in S.USED)
    json.dump(info, open(os.path.join(a.out, "sfx_timing.json"), "w"), indent=1)
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
