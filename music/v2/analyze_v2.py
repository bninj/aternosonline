#!/usr/bin/env python3
"""Checks + voice preview for the v2 bed.
  analyze_v2.py [out_dir]
Writes preview_with_voice.wav (voice -16 LUFS, music ducked under speech),
analysis.json, spectrogram.png."""
import os, sys, json
import numpy as np
import soundfile as sf
from scipy import signal
import pyloudnorm as pyln
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "out_v2")
VOICE = "/home/user/ddn-project/edit/voice_v1.wav"
SR = 48000
tm = json.load(open(os.path.join(out, "timing.json")))
mix, _ = sf.read(os.path.join(out, "mix.wav"))
stems = {f[5:-4]: sf.read(os.path.join(out, f))[0] for f in sorted(os.listdir(out)) if f.startswith("stem_")}
meter = pyln.Meter(SR)
db = lambda x: 20 * np.log10(max(float(x), 1e-12))
rep = {}

# ---------------- music-only checks ----------------
rep["mix_integrated_lufs"] = round(meter.integrated_loudness(mix), 2)
rep["mix_true_peak_dbtp"] = round(db(np.abs(signal.resample_poly(mix, 4, 1, axis=0)).max()), 2)
rep["mix_clipped_samples"] = int(np.sum(np.abs(mix) >= 0.999))
rep["duration_s"] = round(len(mix) / SR, 3)
rep["last_50ms_peak_dbfs"] = round(db(np.abs(mix[-int(0.05 * SR):]).max()), 1)
rep["first_100ms_peak_dbfs"] = round(db(np.abs(mix[: int(0.1 * SR)]).max()), 1)
S = tm["sections"]
bounds = [("preroll", 0.0, S["hook"]), ("hook", S["hook"], S["change"]), ("change", S["change"], S["now"]),
          ("now", S["now"], S["ddn"]), ("ddn", S["ddn"], S["ask"]), ("ask", S["ask"], S["drop"]),
          ("drop", S["drop"], S["resolve"]), ("endcard", S["resolve"], tm.get("end", 80.0))]


def bands(x):
    m = x.mean(1) if x.ndim > 1 else x
    f, P = signal.welch(m, SR, nperseg=8192)
    tot = P[f > 20].sum() + 1e-30
    return {"<250": P[(f > 20) & (f < 250)].sum() / tot, "250-1k": P[(f >= 250) & (f < 1000)].sum() / tot,
            "1-4k": P[(f >= 1000) & (f < 4000)].sum() / tot, ">4k": P[f >= 4000].sum() / tot}


sec = {}
for name, a, b in bounds:
    seg = mix[int(a * SR): int(b * SR)]
    d = {"t": [round(a, 2), round(b, 2)]}
    try:
        d["lufs"] = round(meter.integrated_loudness(seg), 1)
    except Exception:
        d["lufs"] = None
    d["rms_dbfs"] = round(db(np.sqrt(np.mean(seg ** 2))), 1)
    d["band_pct"] = {k: round(100 * v, 1) for k, v in bands(seg).items()}
    d["stems_rms_dbfs"] = {k: round(db(np.sqrt(np.mean(v[int(a * SR): int(b * SR)] ** 2))), 1) for k, v in stems.items()}
    sec[name] = d
rep["sections"] = sec

# ---------------- preview with voice + ducking ----------------
v, vsr = sf.read(VOICE)
assert vsr == SR
if v.ndim > 1:
    v = v.mean(1)
v = v * 10 ** ((-16 - meter.integrated_loudness(v)) / 20)
n = max(len(v), len(mix))
V = np.zeros(n); V[: len(v)] = v
M = np.zeros((n, 2)); M[: len(mix)] = mix
# speech activity from the voice envelope (30 ms RMS), held 250 ms
hop = int(0.01 * SR)
rms = np.sqrt(np.convolve(V ** 2, np.ones(int(0.03 * SR)) / int(0.03 * SR), "same"))[::hop]
act = rms > 10 ** (-42 / 20)
act = np.convolve(act.astype(float), np.ones(25), "same") > 0
# music sits ~8 dB lower than mix.wav (-20 LUFS) while he talks -> about 12 dB under the voice
duck_db = np.where(act, -8.0, -2.0)
# smooth: attack 120 ms, release 600 ms
g = np.zeros_like(duck_db); g[0] = duck_db[0]
for i in range(1, len(g)):
    a = 0.08 if duck_db[i] < g[i - 1] else 0.017
    g[i] = g[i - 1] + a * (duck_db[i] - g[i - 1])
gs = np.interp(np.arange(n), np.arange(len(g)) * hop, g)
Md = M * (10 ** (gs / 20))[:, None]
prev = Md + V[:, None]
pk = np.abs(prev).max()
if pk > 10 ** (-1 / 20):
    prev *= 10 ** (-1 / 20) / pk
sf.write(os.path.join(out, "preview_with_voice.wav"), prev, SR, subtype="PCM_24")
rep["preview"] = {"voice_lufs": -16.0, "music_ducked_lufs": round(meter.integrated_loudness(Md), 1),
                  "preview_lufs": round(meter.integrated_loudness(prev), 1),
                  "duck_db_during_speech": -8.0}

# speech-band masking: per 50 ms frame during speech, voice vs (ducked) music energy in 1-4 kHz
def band_env(x, lo, hi):
    sos = signal.butter(4, [lo, hi], "bp", fs=SR, output="sos")
    y = signal.sosfilt(sos, x)
    w = int(0.05 * SR)
    return np.sqrt(np.add.reduceat(y ** 2, np.arange(0, len(y), w)) / w)

vb = band_env(V, 1000, 4000)
mb = band_env(Md.mean(1), 1000, 4000)
fa = act[:: 5][: len(vb)]
ratio = 20 * np.log10((vb[fa] + 1e-9) / (mb[fa] + 1e-9))
rep["speech_band_voice_over_music_db"] = {"median": round(float(np.median(ratio)), 1),
                                          "p10": round(float(np.percentile(ratio, 10)), 1),
                                          "frames_below_10dB_pct": round(float(np.mean(ratio < 10) * 100), 1)}
# same for full band (voice vs music)
vf = band_env(V, 80, 8000); mf = band_env(Md.mean(1), 80, 8000)
r2 = 20 * np.log10((vf[fa] + 1e-9) / (mf[fa] + 1e-9))
rep["fullband_voice_over_music_db_median"] = round(float(np.median(r2)), 1)

json.dump(rep, open(os.path.join(out, "analysis.json"), "w"), indent=1)
print(json.dumps(rep, indent=1))

# ---------------- spectrogram ----------------
fig, axs = plt.subplots(3, 1, figsize=(17, 11), height_ratios=[3, 2, 1.3], sharex=True)
for ax, x, title in [(axs[0], mix.mean(1), "mix.wav (music only)"), (axs[1], prev.mean(1), "preview_with_voice.wav")]:
    f, t, Z = signal.stft(x, SR, nperseg=4096, noverlap=4096 - 512)
    Zdb = 20 * np.log10(np.abs(Z) + 1e-9)
    sel = (f >= 30) & (f <= 14000)
    ax.pcolormesh(t, f[sel], Zdb[sel], vmin=Zdb.max() - 80, vmax=Zdb.max(), cmap="magma", shading="auto")
    ax.set_yscale("log"); ax.set_ylim(30, 14000); ax.set_ylabel("Hz")
    ax.axhline(1000, color="cyan", lw=0.6, ls="--"); ax.axhline(4000, color="cyan", lw=0.6, ls="--")
    ax.set_title(title)
    for name, a, b in bounds:
        ax.axvline(a, color="white", lw=0.8); ax.text(a + 0.2, 9500, name.upper(), color="white", fontsize=9)
axs[0].set_title(f"mix.wav  |  {tm['bpm']} BPM  |  {rep['mix_integrated_lufs']} LUFS  |  TP {rep['mix_true_peak_dbtp']} dBTP")
ax = axs[2]
w = int(0.1 * SR)
for k, x in list(stems.items()):
    r = np.sqrt(np.convolve(x.mean(1) ** 2, np.ones(w) / w, "same")[:: w // 4])
    ax.plot(np.arange(len(r)) * (w // 4) / SR, 20 * np.log10(r + 1e-9), lw=0.8, label=k)
ax.plot(np.arange(len(gs[::w // 4])) * (w // 4) / SR, gs[::w // 4] - 60, color="k", lw=1.2, label="duck (dB-60)")
ax.set_ylim(-80, -10); ax.legend(ncol=9, fontsize=8, loc="upper left"); ax.set_xlabel("s")
for name, a, b in bounds:
    ax.axvline(a, color="grey", lw=0.6)
plt.tight_layout()
plt.savefig(os.path.join(out, "spectrogram.png"), dpi=80)
print("wrote spectrogram")
