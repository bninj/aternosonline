#!/usr/bin/env python3
"""v3 checks + voice preview.
  analyze_v3.py [out_dir]
preview_with_voice.wav: voice -16 LUFS (peak-limited to -1 dBFS for the preview),
music ~20 dB under the voice while he talks (+5 dB in gaps >= 0.5 s), 1-4 kHz of
the music dipped a further 4 dB during speech, SFX at their delivered level."""
import os, sys, json
import numpy as np
import soundfile as sf
from scipy import signal
import pyloudnorm as pyln
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "out_v3")
cfg = json.load(open(sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "edit_v3.json")))
VOICE = cfg.get("voice", "/home/user/ddn-project/edit/voice_v1.wav")
SR = 48000
tm = json.load(open(os.path.join(out, "timing.json")))
sx = json.load(open(os.path.join(out, "sfx_timing.json")))
mix, _ = sf.read(os.path.join(out, "music_mix.wav"))
stems = {f[5:-4]: sf.read(os.path.join(out, f))[0] for f in sorted(os.listdir(out)) if f.startswith("stem_")}
sfx_all, _ = sf.read(os.path.join(out, "sfx_all_positioned.wav"))
meter = pyln.Meter(SR)
db = lambda x: 20 * np.log10(max(float(x), 1e-12))
rep = {}
N = len(mix)

# ---------------- music-only ----------------
rep["music_mix"] = dict(lufs=round(meter.integrated_loudness(mix), 2),
                        true_peak_dbtp=round(db(np.abs(signal.resample_poly(mix, 4, 1, axis=0)).max()), 2),
                        sample_peak_dbfs=round(db(np.abs(mix).max()), 2),
                        clipped=int(np.sum(np.abs(mix) >= 0.999)), duration=round(N / SR, 3),
                        last_50ms_peak_dbfs=round(db(np.abs(mix[-int(0.05 * SR):]).max()), 1))
SD = tm["section_downbeats"]
bounds = [("chair", 0, SD["hook"]), ("hook", SD["hook"], SD["change"]), ("change", SD["change"], SD["now"]),
          ("now", SD["now"], SD["ddn"]), ("ddn", SD["ddn"], SD["ask"]), ("ask", SD["ask"], SD["punch"]),
          ("punch", SD["punch"], SD["endcard"]), ("endcard", SD["endcard"], cfg["end"])]
sec = {}
for name, a, b in bounds:
    seg = mix[int(a * SR): int(b * SR)]
    m = seg.mean(1); f, P = signal.welch(m, SR, nperseg=8192); tot = P[f > 20].sum() + 1e-30
    sec[name] = dict(t=[round(a, 2), round(b, 2)],
                     lufs=round(meter.integrated_loudness(seg), 1) if len(seg) > 0.5 * SR else None,
                     band_pct={"<250": round(100 * P[(f > 20) & (f < 250)].sum() / tot, 1),
                               "250-1k": round(100 * P[(f >= 250) & (f < 1000)].sum() / tot, 1),
                               "1-4k": round(100 * P[(f >= 1000) & (f < 4000)].sum() / tot, 1),
                               ">4k": round(100 * P[f >= 4000].sum() / tot, 1)},
                     stems_rms={k: round(db(np.sqrt(np.mean(v[int(a * SR): int(b * SR)] ** 2))), 1) for k, v in stems.items()})
# punchline window specifically
pw = mix[int(72.4 * SR): int(75.6 * SR)]
rep["punchline_72.4_75.6_lufs"] = round(meter.integrated_loudness(pw), 1)
rep["sections"] = sec


# ---------------- does each change land on the frame? ----------------
def onset_near(x, t, pre=0.08, post=0.12):
    """first sample where the 2 ms peak envelope rises 10 dB above the level
    just before t (onset of a new event). returns offset in ms (None if none)."""
    m = np.abs(x.mean(1) if x.ndim > 1 else x)
    hop = int(0.001 * SR)
    a, b = int((t - pre) * SR), int((t + post) * SR)
    e = np.array([m[i:i + 2 * hop].max() for i in range(a, b, hop)]) + 1e-9
    ref = np.median(e[: int(0.03 / 0.001)])
    k = np.where(e > ref * 10 ** (10 / 20))[0]
    k = [i for i in k if i * hop >= int(0.03 * SR)]
    return round(((a + k[0] * hop) / SR - t) * 1000, 1) if k else None
lands = {}
groove = stems["bass"] + stems["drums"]
for k in ["change", "now", "ddn", "ask", "punch", "endcard"]:
    lands[k] = dict(target=SD[k], requested=cfg["sections"][k], onset_offset_ms=onset_near(groove, SD[k]))
lands["hook"] = dict(target=SD["hook"], onset_offset_ms=onset_near(stems["bass"], SD["hook"]))
rep["section_downbeats_vs_edit"] = lands
acc = {}
for a_ in tm["accents"]:
    t = a_["t"]
    w = a_["what"]
    st = stems["vibes"] if "vibes" in w else stems["drums"] if "tom" in w else stems["fx"] if "cymbal" in w \
        else stems["marimba"] if "marimba" in w else stems["shaker"] if "shaker" in w else None
    if st is None or "drop-out" in w:
        acc[f"{w} @{t}"] = "gain envelope (exact)"
    elif "cymbal" in w:
        i0 = int((t - 0.3) * SR); i1 = int((t + 0.3) * SR)
        acc[f"{w} @{t}"] = round((i0 + int(np.argmax(np.abs(st[i0:i1]).max(1)))) / SR * 1000 - t * 1000, 1)
    else:
        acc[f"{w} @{t}"] = onset_near(st, t)
rep["accent_onsets_ms"] = acc

# ---------------- preview ----------------
v, vsr = sf.read(VOICE)
v = v.mean(1) if v.ndim > 1 else v
v = v * 10 ** ((-16 - meter.integrated_loudness(v)) / 20)
# preview-only voice peak limiter (-1 dBFS), then back to -16 LUFS
def limit1(x, ceil):
    pk = np.abs(x)
    la = int(0.003 * SR)
    pkenv = np.maximum.reduce([np.r_[pk[k:], np.zeros(k)] for k in range(0, la, 3)])
    need = np.minimum(1.0, ceil / np.maximum(pkenv, 1e-9))
    g = np.empty_like(need); cur = 1.0; r = np.exp(-1 / (0.05 * SR))
    for i in range(len(need)):
        cur = need[i] if need[i] < cur else cur * r + (1 - r) * need[i]
        g[i] = cur
    return x * np.convolve(g, np.ones(la) / la, "same")
for _ in range(3):
    v = limit1(v, 10 ** (-1.5 / 20))
    v = v * 10 ** ((-16 - meter.integrated_loudness(v)) / 20)
n = max(len(v), N)
V = np.zeros(n); V[: len(v)] = v
M = np.zeros((n, 2)); M[:N] = mix
FX = np.zeros((n, 2)); FX[: len(sfx_all)] = sfx_all
hop = int(0.01 * SR)
rms = np.sqrt(np.convolve(V ** 2, np.ones(int(0.03 * SR)) / int(0.03 * SR), "same"))[::hop]
act = rms > 10 ** (-40 / 20)
# speech = active, bridging gaps shorter than 0.5 s
sp = act.copy()
i = 0
while i < len(sp):
    if not sp[i]:
        j = i
        while j < len(sp) and not sp[j]:
            j += 1
        if (j - i) * 0.01 < 0.5 and i > 0 and j < len(sp):
            sp[i:j] = True
        i = j
    else:
        i += 1
base = -16.0                     # music_mix (-20 LUFS) -> about -36 LUFS under a -16 LUFS voice
tgt = np.where(sp, base, base + 5.0)
g = np.zeros_like(tgt); g[0] = tgt[0]
for i in range(1, len(g)):
    a = 1 - np.exp(-0.01 / 0.12) if tgt[i] < g[i - 1] else 1 - np.exp(-0.01 / 0.5)
    g[i] = g[i - 1] + a * (tgt[i] - g[i - 1])
gs = np.interp(np.arange(n), np.arange(len(g)) * hop, g)
# dynamic EQ: extra -4 dB on the music's 1-4 kHz while he talks
sos = signal.butter(2, [1000, 4000], "bp", fs=SR, output="sos")
band = signal.sosfiltfilt(sos, M, axis=0)
spd = np.interp(np.arange(n), np.arange(len(sp)) * hop, np.convolve(sp.astype(float), np.ones(15) / 15, "same"))
Md = (M - band * (1 - 10 ** (-4 / 20) * 1.0) * spd[:, None] * 0 + 0)  # placeholder (kept explicit below)
Md = M + band * ((10 ** (-4 / 20) - 1) * spd)[:, None]
Md = Md * (10 ** (gs / 20))[:, None]
prev = Md + V[:, None] + FX
pk = np.abs(prev).max()
rep["preview"] = dict(voice_lufs=round(meter.integrated_loudness(V), 1),
                      music_in_preview_lufs=round(meter.integrated_loudness(Md), 1),
                      music_during_speech_lufs=round(meter.integrated_loudness(Md[np.repeat(sp, hop)[:n].astype(bool)]), 1),
                      preview_peak_dbfs=round(db(pk), 2))
sf.write(os.path.join(out, "preview_with_voice.wav"), prev, SR, subtype="PCM_24")


def band_env(x, lo, hi, w=0.05):
    y = signal.sosfilt(signal.butter(4, [lo, hi], "bp", fs=SR, output="sos"), x)
    W = int(w * SR)
    return np.sqrt(np.add.reduceat(y ** 2, np.arange(0, len(y), W)) / W)
vb = band_env(V, 1000, 4000); mb = band_env(Md.mean(1), 1000, 4000)
fa = (act[::5][: len(vb)]) & (vb > 10 ** (-45 / 20))
r = 20 * np.log10((vb[fa] + 1e-9) / (mb[fa] + 1e-9))
vf = band_env(V, 80, 12000); mf = band_env(Md.mean(1), 80, 12000)
r2 = 20 * np.log10((vf[fa] + 1e-9) / (mf[fa] + 1e-9))
rep["masking_during_speech"] = dict(voice_over_music_1_4k_db_median=round(float(np.median(r)), 1),
                                    p5=round(float(np.percentile(r, 5)), 1),
                                    voice_over_music_fullband_db_median=round(float(np.median(r2)), 1))

# ---------------- SFX audibility proxies ----------------
def third_oct_ratio(sig, rest, t0, t1):
    a, b = int(t0 * SR), int(t1 * SR)
    s1 = sig[a:b]; s2 = rest[a:b]
    f, P1 = signal.welch(s1, SR, nperseg=2048); _, P2 = signal.welch(s2, SR, nperseg=2048)
    cs = 125 * 2 ** (np.arange(0, 22) / 3)
    best = -99
    for c in cs:
        m = (f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))
        if m.sum() and P2[m].sum() > 0:
            best = max(best, 10 * np.log10(P1[m].sum() / P2[m].sum()))
    return best
lap_sos = signal.butter(2, [350, 9000], "bp", fs=SR, output="sos")
aud = {}
for k, d in sx.items():
    if k.startswith("_"):
        continue
    t0 = d["place_at"]; L = d["length_s"]
    fxs = FX.mean(1); rest = (Md + V[:, None]).mean(1)
    win = (t0, t0 + min(L, 0.8))
    hp_ratio = third_oct_ratio(fxs, rest, *win)
    a, b = int(win[0] * SR), int(win[1] * SR)
    lap = 10 * np.log10(np.mean(signal.sosfilt(lap_sos, fxs)[a:b] ** 2) / (np.mean(signal.sosfilt(lap_sos, rest)[a:b] ** 2) + 1e-20))
    aud[k] = dict(peak_dbfs=d["peak_dbfs"], best_third_octave_sfx_over_rest_db=round(hp_ratio, 1),
                  laptop_band_sfx_over_rest_db=round(float(lap), 1))
rep["sfx_audibility"] = aud
json.dump(rep, open(os.path.join(out, "analysis.json"), "w"), indent=1)
print(json.dumps(rep, indent=1))

# ---------------- spectrogram ----------------
fig, axs = plt.subplots(3, 1, figsize=(18, 11), height_ratios=[3, 3, 1.4], sharex=True)
for ax, x, title in [(axs[0], mix.mean(1), "music_mix.wav"), (axs[1], prev.mean(1), "preview_with_voice.wav (voice + ducked music + SFX)")]:
    f, t, Z = signal.stft(x, SR, nperseg=4096, noverlap=4096 - 512)
    Zd = 20 * np.log10(np.abs(Z) + 1e-9); sel = (f >= 30) & (f <= 14000)
    ax.pcolormesh(t, f[sel], Zd[sel], vmin=Zd.max() - 80, vmax=Zd.max(), cmap="magma", shading="auto")
    ax.set_yscale("log"); ax.set_ylim(30, 14000); ax.set_title(title)
    ax.axhline(1000, color="cyan", lw=0.5, ls="--"); ax.axhline(4000, color="cyan", lw=0.5, ls="--")
    for c in cfg["cuts"]:
        ax.axvline(c, color="white", lw=0.5, ls=":")
    for name, a, b in bounds:
        ax.axvline(a, color="white", lw=1.0); ax.text(a + 0.2, 9000, name.upper(), color="white", fontsize=8)
for k, d in sx.items():
    if not k.startswith("_"):
        axs[1].axvline(d["event_time"], color="lime", lw=1.0)
axs[0].set_title(f"music_mix.wav | {tm['bpm_min']:.0f}-{tm['bpm_max']:.0f} BPM tempo map | {rep['music_mix']['lufs']} LUFS | TP {rep['music_mix']['true_peak_dbtp']} dBTP  (dotted = camera cuts)")
ax = axs[2]
w = int(0.1 * SR)
for k, x in stems.items():
    rr = np.sqrt(np.convolve(x.mean(1) ** 2, np.ones(w) / w, "same")[:: w // 4])
    ax.plot(np.arange(len(rr)) * (w // 4) / SR, 20 * np.log10(rr + 1e-9), lw=0.8, label=k)
ax.plot(np.arange(len(gs[:: w // 4])) * (w // 4) / SR, gs[:: w // 4] - 40, "k", lw=1.2, label="music gain in preview (dB-40)")
ax.set_ylim(-80, -10); ax.legend(ncol=9, fontsize=7, loc="upper left")
for c in cfg["cuts"]:
    ax.axvline(c, color="grey", lw=0.5, ls=":")
plt.tight_layout(); plt.savefig(os.path.join(out, "spectrogram.png"), dpi=75)
print("wrote spectrogram")
