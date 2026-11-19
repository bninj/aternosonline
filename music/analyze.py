#!/usr/bin/env python3
"""Objective 'listening' checks for the rendered bed: loudness, peaks, speech-band
(1-4 kHz) share per section, tails, ding alignment, plus spectrogram PNG.

  /home/user/ddn-project/tools/venv/bin/python analyze.py [out_dir]
"""
import json, os, sys
import numpy as np
import soundfile as sf
from scipy import signal
import pyloudnorm as pyln
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out")
tm = json.load(open(os.path.join(out, "timing.json")))
mix, sr = sf.read(os.path.join(out, "mix.wav"))
stems = {k: sf.read(os.path.join(out, f"stem_{k}.wav"))[0] for k in ["piano", "pad", "pulse", "tick"]}
ding, _ = sf.read(os.path.join(out, "ding.wav"))
meter = pyln.Meter(sr)
db = lambda x: 20 * np.log10(max(x, 1e-12))

rep = {}
rep["integrated_lufs"] = round(meter.integrated_loudness(mix), 2)
rep["sample_peak_dbfs"] = round(db(np.max(np.abs(mix))), 2)
up = signal.resample_poly(mix, 4, 1, axis=0)
rep["true_peak_dbtp"] = round(db(np.max(np.abs(up))), 2)
rep["clipped_samples"] = int(np.sum(np.abs(mix) >= 0.999))
rep["dc_offset"] = [round(float(v), 6) for v in mix.mean(0)]
rep["first_10ms_peak_dbfs"] = round(db(np.max(np.abs(mix[: int(0.01 * sr)]))), 1)
rep["last_100ms_rms_dbfs"] = round(db(np.sqrt(np.mean(mix[-int(0.1 * sr):] ** 2))), 1)
rep["last_sample_abs"] = float(np.max(np.abs(mix[-1])))
rep["duration_s"] = round(len(mix) / sr, 3)

S = tm["sections"]
bounds = [("hook", 0, S["change"]), ("change", S["change"], S["now"]), ("now", S["now"], S["ddn"]),
          ("ddn", S["ddn"], S["ask"]), ("ask", S["ask"], tm["ding_time"]), ("post", tm["ding_time"], tm["end"])]


def band_share(x, lo, hi):
    m = x.mean(1) if x.ndim > 1 else x
    f, P = signal.welch(m, sr, nperseg=8192)
    tot = P[(f > 20)].sum() + 1e-30
    return P[(f >= lo) & (f < hi)].sum() / tot, f, P


sec = {}
for name, a, b in bounds:
    seg = mix[int(a * sr): int(b * sr)]
    d = {}
    try:
        d["lufs"] = round(meter.integrated_loudness(seg), 1) if len(seg) > sr * 0.5 else None
    except Exception:
        d["lufs"] = None
    d["rms_dbfs"] = round(db(np.sqrt(np.mean(seg ** 2))), 1)
    sh, f, P = band_share(seg, 1000, 4000)
    d["speechband_1_4k_pct"] = round(100 * sh, 2)
    d["above_4k_pct"] = round(100 * band_share(seg, 4000, 20000)[0], 2)
    d["below_250_pct"] = round(100 * band_share(seg, 20, 250)[0], 1)
    d["centroid_hz"] = int(np.sum(f * P) / np.sum(P))
    d["stem_rms_dbfs"] = {k: round(db(np.sqrt(np.mean(v[int(a * sr): int(b * sr)] ** 2))), 1)
                          for k, v in stems.items()}
    sec[name] = d
rep["sections"] = sec

# ding / cadence alignment: onset of the piano stem near the ding time
pk = np.abs(stems["piano"]).max(1)
hop = int(0.001 * sr)
env = np.array([pk[i:i + 4 * hop].max() for i in range(0, len(pk) - 4 * hop, hop)])
c = int(round(tm["ding_time"] * 1000))
pre = env[c - 30: c - 5].max()
post_i = c - 20 + int(np.argmax(env[c - 20: c + 120] > pre * 2.0))   # first +6 dB rise
rep["cadence_onset_vs_ding_ms"] = post_i - c
# harmonic check at the ding: chroma of 0.4 s after the ding
seg = stems["piano"][int(tm["ding_time"] * sr): int((tm["ding_time"] + 0.6) * sr)].mean(1)
f, P = signal.welch(seg, sr, nperseg=16384)
mask = (f > 60) & (f < 2000)
pcs = np.zeros(12)
for fi, pi in zip(f[mask], P[mask]):
    pcs[int(round(12 * np.log2(fi / 440) + 69)) % 12] += pi
names = "C C# D D# E F F# G G# A A# B".split()
rep["piano_chroma_at_ding_top4"] = [names[i] for i in np.argsort(pcs)[::-1][:4]]
fd, Pd = signal.welch(ding.mean(1), sr, nperseg=16384)
rep["ding_peak_hz"] = round(float(fd[np.argmax(Pd)]), 1)
rep["ding_peak_dbfs"] = round(db(np.max(np.abs(ding))), 1)
rep["ding_tail_last_s"] = round(db(np.max(np.abs(ding[-int(0.05 * sr):]))), 1)

json.dump(rep, open(os.path.join(out, "analysis.json"), "w"), indent=1)
print(json.dumps(rep, indent=1))

# ---------------- spectrogram PNG ----------------
m = mix.mean(1)
f, t, Z = signal.stft(m, sr, nperseg=4096, noverlap=4096 - 512)
Zdb = 20 * np.log10(np.abs(Z) + 1e-9)
fig, axs = plt.subplots(2, 1, figsize=(16, 9), height_ratios=[3, 1.2], sharex=True)
ax = axs[0]
sel = (f >= 30) & (f <= 12000)
ax.pcolormesh(t, f[sel], Zdb[sel], vmin=Zdb.max() - 85, vmax=Zdb.max(), cmap="magma", shading="auto")
ax.set_yscale("log")
ax.set_ylim(30, 12000)
ax.axhspan(1000, 4000, color="cyan", alpha=0.08)
ax.axhline(1000, color="cyan", lw=0.6, ls="--")
ax.axhline(4000, color="cyan", lw=0.6, ls="--")
ax.set_ylabel("Hz (log)")
ax.set_title(f"mix.wav  |  {tm['bpm']} BPM  |  {rep['integrated_lufs']} LUFS  |  TP {rep['true_peak_dbtp']} dBTP"
             "  |  cyan = 1-4 kHz speech band")
for name, a, b in bounds:
    for x in axs:
        x.axvline(a, color="white" if x is ax else "grey", lw=0.8)
    ax.text(a + 0.3, 9000, name.upper(), color="white", fontsize=10)
for x in axs:
    x.axvline(tm["ding_time"], color="yellow", lw=1.2)
ax.text(tm["ding_time"] + 0.2, 40, "DING", color="yellow")
ax2 = axs[1]
win = int(0.1 * sr)
for kname, v in list(stems.items()) + [("mix", mix)]:
    r = np.sqrt(np.convolve(v.mean(1) ** 2, np.ones(win) / win, "same")[::win // 4])
    ax2.plot(np.arange(len(r)) * (win // 4) / sr, 20 * np.log10(r + 1e-9), label=kname,
             lw=1.4 if kname == "mix" else 0.9)
ax2.set_ylim(-80, -10)
ax2.set_ylabel("RMS dBFS")
ax2.set_xlabel("seconds")
ax2.legend(loc="upper left", ncol=5, fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(out, "spectrogram.png"), dpi=90)
print("wrote", os.path.join(out, "spectrogram.png"))
