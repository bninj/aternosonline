#!/usr/bin/env python3
"""License-free procedural SFX for motion graphics (whoosh, riser, sub hit, UI tick).
Usage: sfx_gen.py outdir   -> writes whoosh.wav, whoosh_short.wav, riser.wav, hit.wav, tick.wav (48 kHz stereo)
"""
import sys, os
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

SR = 48000
rng = np.random.default_rng(7)


def swept_noise(dur, f0, f1, q=2.0, attack=0.6):
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    block = 512
    zi = None
    for i in range(0, n, block):
        t = i / n
        fc = f0 * (f1 / f0) ** t
        lo, hi = fc / (1 + 1 / q), min(fc * (1 + 1 / q), SR / 2 - 100)
        sos = butter(2, [lo, hi], btype="band", fs=SR, output="sos")
        seg, zi = sosfilt(sos, noise[i:i + block], zi=zi if zi is not None else np.zeros((sos.shape[0], 2)))
        out[i:i + block] = seg
    t = np.linspace(0, 1, n)
    env = np.where(t < attack, (t / attack) ** 2, ((1 - t) / (1 - attack)) ** 1.5)
    return out * env


def stereo_pan(x, start=-0.8, end=0.8):
    p = np.linspace(start, end, len(x))
    l, r = np.cos((p + 1) * np.pi / 4), np.sin((p + 1) * np.pi / 4)
    return np.stack([x * l, x * r], 1)


def norm(x, peak_db=-3):
    return x / (np.max(np.abs(x)) + 1e-9) * 10 ** (peak_db / 20)


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    sf.write(f"{outdir}/whoosh.wav", norm(stereo_pan(swept_noise(0.9, 300, 4000, attack=0.55))), SR)
    sf.write(f"{outdir}/whoosh_short.wav", norm(stereo_pan(swept_noise(0.35, 600, 6000, attack=0.5), 0.6, -0.6)), SR)
    r = swept_noise(2.5, 200, 8000, q=4, attack=0.95)
    sf.write(f"{outdir}/riser.wav", norm(np.stack([r, r], 1)), SR)
    t = np.arange(int(0.8 * SR)) / SR
    hit = np.sin(2 * np.pi * (55 + 60 * np.exp(-t * 30)) * t) * np.exp(-t * 5)
    hit += 0.3 * swept_noise(0.8, 3000, 300, attack=0.01)[: len(t)]
    sf.write(f"{outdir}/hit.wav", norm(np.stack([hit, hit], 1)), SR)
    t = np.arange(int(0.06 * SR)) / SR
    tick = np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 90)
    sf.write(f"{outdir}/tick.wav", norm(np.stack([tick, tick], 1), -9), SR)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "sfx")
