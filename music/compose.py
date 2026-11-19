#!/usr/bin/env python3
"""
DDN "Why DDN" pitch video - parametric music-bed generator.

Reads sections.json, snaps section changes to bar lines (tempo may flex by
+/- bpm_flex so the "ding" lands exactly on a downbeat), composes the piece in
MIDI (music.mid) and renders 48 kHz stems + mix + ding:

  out/stem_piano.wav   Salamander Grand Piano (sampled Yamaha C5, CC-BY 3.0)
  out/stem_pad.wav     synthesised pad (additive, no samples)
  out/stem_pulse.wav   synthesised soft pulse (no samples)
  out/stem_tick.wav    synthesised clock tick (no samples)
  out/mix.wav          sum of stems, loudness-normalised (no ding)
  out/mix_with_ding.wav  preview with the ding placed at the cadence
  out/ding.wav         separate soft bell, tuned to the tonic of the resolve
  out/timing.json      the actual bar-snapped section times / tempo / ding time

Usage:
  /home/user/ddn-project/tools/venv/bin/python compose.py [sections.json] [--out out]
"""
import json, sys, os, re, math, argparse
from fractions import Fraction
import numpy as np
import soundfile as sf
from scipy import signal
import mido

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
SAL_DIR = os.path.join(HERE, "samples", "SalamanderGrandPianoV3_48khz24bit")

# ----------------------------------------------------------------------------
# 1. Timing
# ----------------------------------------------------------------------------

def plan_timing(cfg):
    bpm0 = float(cfg.get("bpm", 104))
    flex = float(cfg.get("bpm_flex", 3))
    ding = float(cfg["ding"])
    best = None
    for n in range(1, 400):
        bpm = n * 240.0 / ding           # 4/4: bar = 240/bpm seconds
        if abs(bpm - bpm0) <= flex + 1e-9:
            if best is None or abs(bpm - bpm0) < abs(best[1] - bpm0):
                best = (n, bpm)
    if best is not None:
        n_ding, bpm = best
        origin = 0.0
    else:  # cannot flex enough: keep bpm, shift the grid origin
        bpm = bpm0
        bar = 240.0 / bpm
        n_ding = int(ding // bar)
        origin = ding - n_ding * bar
    bar = 240.0 / bpm

    def snap(t):
        return max(0, int(round((t - origin) / bar)))

    bars = {
        "hook": 0,
        "change": snap(cfg["change"][0]),
        "now": snap(cfg["now"][0]),
        "ddn": snap(cfg["ddn"][0]),
        "ask": snap(cfg["ask"][0]),
        "ding": n_ding,
    }
    # the ding bar is fixed; squeeze earlier sections if needed so that each
    # has >= 1 bar and the ask has >= 3 bars (the cadence) before the ding
    order = ["change", "now", "ddn", "ask"]
    lim = bars["ding"] - 3
    for k in reversed(order):
        bars[k] = max(0, min(bars[k], lim))
        lim = bars[k] - 1
    for a_, b_ in zip(order, order[1:]):
        if bars[b_] <= bars[a_]:
            bars[b_] = min(bars[a_] + 1, bars["ding"] - 1)
    return dict(bpm=bpm, bar=bar, beat=bar / 4, origin=origin, bars=bars,
                end=float(cfg["end"]), ding=ding)


# ----------------------------------------------------------------------------
# 2. Harmony (written in D major; global transpose applied at the end)
# ----------------------------------------------------------------------------
# name: (bass note, upper voicing).  Voicings stay mid-low (F#2 .. A4) and
# open: add9 / sus2 / 6-9 colours and inversions instead of plain triads.
CH = {
    "Bm9":      (47, [54, 59, 61, 62]),        # B  | F# B C# D
    "Bm9/A":    (45, [54, 59, 61, 62]),        # A  | (descending bass)
    "Gmaj9":    (43, [54, 57, 59, 62]),        # G  | F# A B D
    "Dadd9/F#": (42, [57, 62, 64, 66]),        # F# | A D E F#
    "Em9":      (40, [55, 59, 62, 66]),        # E  | G B D F#
    "A7sus4":   (45, [55, 62, 64, 69]),        # A  | G D E A
    "Aadd9":    (45, [57, 59, 61, 64]),        # A  | A B C# E
    "A7":       (45, [55, 61, 64, 69]),        # A  | G C# E A
    "Dadd9":    (38, [57, 62, 64, 66]),        # D  | A D E F#
    "G69/D":    (38, [55, 59, 64, 69]),        # D  | G B E A
    "Em7/D":    (38, [55, 59, 62, 64]),        # D  | G B D E
    "Bm7":      (47, [57, 62, 66, 69]),        # B  | A D F# A
    "F#m7":     (42, [57, 61, 64, 69]),        # F# | A C# E A
    "A/G":      (43, [57, 61, 64, 69]),        # G  | A C# E A
    "Asus2/C#": (49, [57, 59, 64, 69]),        # C# | A B E A
    "Gm6/Bb":   (46, [55, 58, 62, 64]),        # Bb | G Bb D E  (borrowed iv)
}

# progressions per section: (body, tail) - tail always sits at section end
PROG = {
    "change": (["Bm9", "Bm9/A", "Gmaj9", "Dadd9/F#", "Em9", "Em9"],
               ["A7sus4", "Aadd9"]),
    "now":    (["Gmaj9", "Dadd9/F#", "Em9", "Bm7", "Gmaj9", "Asus2/C#"],
               ["A7sus4"]),
    "ddn":    (["Dadd9", "G69/D", "Dadd9", "Em7/D", "Bm7", "Gmaj9",
                "Em9", "Asus2/C#"], []),
    # ask = rising pre-cadence + fixed 3-bar cadence into the ding
    "ask_pre": ["Em9", "Gmaj9", "Dadd9/F#", "Bm7"],
    "cadence": ["Gmaj9", "Gm6/Bb", "A7sus4"],
}

D_MAJOR = [0, 2, 4, 5, 7, 9, 11]


def diatonic(anchor, step):
    # robust version: walk the scale
    pcs = sorted({(p + 2) % 12 for p in D_MAJOR})
    n = anchor
    s = 1 if step > 0 else -1
    for _ in range(abs(step)):
        n += s
        while n % 12 not in pcs:
            n += s
    return n


def lh_mid(bass, up):
    """Middle note of the left-hand figure: the 5th if it is a chord tone,
    otherwise the nearest chord tone above the bass (e.g. A over F#)."""
    pcs = {bass % 12} | {u % 12 for u in up}
    for iv in (7, 8, 9, 3, 4, 5):
        if (bass + iv) % 12 in pcs:
            return bass + iv
    return bass + 12


def clear_of(notes, ref):
    """Drop voicing notes a semitone away from `ref` (avoid close rubs)."""
    return [n for n in notes if abs(n - ref) != 1]


def fit(body, tail, n):
    if n <= 0:
        return []
    if n <= len(tail):
        return tail[-n:]
    m = n - len(tail)
    return [body[i % len(body)] for i in range(m)] + list(tail)


# ----------------------------------------------------------------------------
# 3. Composition -> note events (beats from grid origin)
# ----------------------------------------------------------------------------
class Song:
    def __init__(self, seed):
        self.ev = {"piano": [], "pad": [], "pulse": [], "tick": []}
        self.rng = np.random.default_rng(seed)
        self.markers = []

    def add(self, trk, beat, dur, pitch, vel, human=True):
        if human and trk == "piano":
            beat += self.rng.normal(0, 0.012)
            vel += self.rng.integers(-3, 4)
        vel = int(np.clip(vel, 1, 127))
        self.ev[trk].append((max(0.0, beat), max(0.05, dur), int(pitch), vel))


def motif(song, bar_beat, anchor, vel, n=4, extend=0, shape=(-3, 0, 1, 2)):
    """The motif: 5-1-2-3 (pickup, dotted quarter, eighth, half).
    bar_beat = beat of the downbeat it lands on (pickup is half a beat earlier)."""
    rhythm = [(-0.5, 0.5), (0.0, 1.5), (1.5, 0.5), (2.0, 2.0)]
    steps = list(shape)
    notes = []
    for i in range(min(n, 4)):
        off, d = rhythm[i]
        if i == n - 1 and n < 4:
            d = 2.5                    # unanswered question: hold
        notes.append((off, d, diatonic(anchor, steps[i])))
    if extend:                          # lift: add a rising 4th on top
        notes[-1] = (2.0, 1.0, notes[-1][2])
        notes.append((3.0, 2.0, diatonic(anchor, steps[-1] + extend)))
    for k, (off, d, p) in enumerate(notes):
        song.add("piano", bar_beat + off, d, p, vel + (4 if k == 1 else 0))


def compose(tm, cfg):
    song = Song(int(cfg.get("seed", 7)))
    B = tm["bars"]
    bpb = 4
    sec_order = ["hook", "change", "now", "ddn", "ask"]
    starts = {s: B[s] for s in sec_order}
    ends = {"hook": B["change"], "change": B["now"], "now": B["ddn"],
            "ddn": B["ask"], "ask": B["ding"]}
    end_bar_f = (tm["end"] - tm["origin"]) / tm["bar"]
    post_bars = int(math.ceil(end_bar_f)) - B["ding"] + 1

    chords = {}   # bar -> chord name
    for s in ["change", "now", "ddn"]:
        body, tail = PROG[s]
        for i, c in enumerate(fit(body, tail, ends[s] - starts[s])):
            chords[starts[s] + i] = c
    n_ask = ends["ask"] - starts["ask"]
    cad = PROG["cadence"][-n_ask:] if n_ask <= 3 else PROG["cadence"]
    n_pre = n_ask - len(cad)
    pre = [PROG["ask_pre"][i % len(PROG["ask_pre"])] for i in range(n_pre)]
    if n_pre and n_pre < len(PROG["ask_pre"]):
        pre = PROG["ask_pre"][-n_pre:]
    for i, c in enumerate(pre + cad):
        chords[starts["ask"] + i] = c
    for i in range(post_bars):
        chords[B["ding"] + i] = "Dadd9"

    def section_of(bar):
        if bar >= B["ding"]:
            return "post"
        for s in reversed(sec_order):
            if bar >= starts[s]:
                return s
        return "hook"

    # ---------------- tick (clock) ----------------
    tick_end = starts["now"] + 2
    for bar in range(0, tick_end):
        for b in range(bpb):
            beat = bar * bpb + b
            # level: present in hook, recedes through change, gone in now
            if bar < starts["change"]:
                lvl = 1.0
            else:
                lvl = max(0.0, 1.0 - (bar - starts["change"] + b / 4) /
                          (tick_end - starts["change"]))
                lvl = 0.55 * lvl
            if lvl > 0.02:
                song.add("tick", beat, 0.1, 76 if b % 2 == 0 else 72,
                         int(100 * lvl), human=False)

    # ---------------- pad ----------------
    # one pad chord per bar; identical consecutive chords are tied.
    pad_start = starts["change"] - 0.5            # faint swell into change
    bars_sorted = sorted(chords)
    i = 0
    while i < len(bars_sorted):
        bar = bars_sorted[i]
        c = chords[bar]
        j = i
        while j + 1 < len(bars_sorted) and chords[bars_sorted[j + 1]] == c \
                and section_of(bars_sorted[j + 1]) == section_of(bar):
            j += 1
        s = section_of(bar)
        beat0 = bar * bpb
        if bar == starts["change"]:
            beat0 = pad_start * bpb
        dur = (bars_sorted[j] + 1) * bpb - beat0
        bass, up = CH[c]
        vel = {"change": 34, "now": 46, "ddn": 54, "ask": 62, "post": 54}[s]
        notes = sorted(set(up[:3]))
        if c == "A7sus4":            # piano owns the sus4->3 move; pad stays neutral
            notes = [55, 64, 69]
        for p in notes:
            song.add("pad", beat0, dur + 0.25, p, vel, human=False)
        i = j + 1

    # ---------------- piano + pulse per bar ----------------
    for bar in bars_sorted:
        s = section_of(bar)
        c = chords[bar]
        bass, up = CH[c]
        k = bar - starts[s] if s != "post" else bar - B["ding"]
        n_sec = (ends[s] - starts[s]) if s != "post" else post_bars
        b0 = bar * bpb

        if s == "change":
            song.add("piano", b0, 4.0, bass - 12 if bass >= 45 else bass, 44)
            # rolled, quiet upper chord on the "and" of 2
            for q, p in enumerate(up[:3]):
                song.add("piano", b0 + 1.5 + q * 0.04, 2.4, p, 33)
            # motif: question (3 notes) on bars 1 and 5 - anchored on B4
            if k % 4 == 1 and k < n_sec - 1:
                motif(song, b0, 71, 40, n=3 if k < 4 else 4)
        elif s == "now":
            # light movement: walking broken chord in the left hand
            song.add("piano", b0, 1.5, bass, 46)
            song.add("piano", b0 + 1.5, 1.0, lh_mid(bass, up), 38)
            song.add("piano", b0 + 2.5, 1.5, bass + 12, 40)
            for q, p in enumerate(clear_of(up[:3], bass + 12)):
                song.add("piano", b0 + 1.0 + q * 0.03, 2.9, p, 36)
            if k % 4 == 0 and k < n_sec - 1:
                motif(song, b0, 67, 44)                     # anchored on G4
            # pulse enters softly on quarters from the second bar
            if k >= 1:
                for q in range(4):
                    song.add("pulse", b0 + q, 0.5, bass, 34 + (6 if q == 0 else 0),
                             human=False)
        elif s == "ddn":
            song.add("piano", b0, 2.5, bass, 50)
            song.add("piano", b0 + 2.5, 1.5, bass + 12, 42)
            for q, p in enumerate(up):
                song.add("piano", b0 + q * 0.02, 1.4, p, 40)
            for q, p in enumerate(clear_of(up[1:], bass + 12)):
                song.add("piano", b0 + 1.5 + q * 0.02, 2.4, p, 35)
            if k % 4 == 0 and k < n_sec - 1:
                motif(song, b0, 74, 48)                     # anchored on D5
            elif k % 4 == 2 and k < n_sec - 1:
                # answer: 3-2-1 falling, on the beat, quiet
                for q, st in enumerate([2, 1, 0]):
                    song.add("piano", b0 + 1 + q, 1.0,
                             diatonic(74, st), 40)
            for q in range(8):
                v = 42 if q % 2 == 0 else 32
                if q == 0:
                    v = 48
                song.add("pulse", b0 + q * 0.5, 0.4, bass, v, human=False)
        elif s == "ask":
            is_cad = k >= n_sec - 3
            cad_i = k - (n_sec - 3)
            if not is_cad:
                # gentle lift: upper voicing an octave higher, a bit brighter
                song.add("piano", b0, 2.5, bass, 52)
                song.add("piano", b0 + 2.5, 1.5, bass + 12, 44)
                for q, p in enumerate(up):
                    song.add("piano", b0 + q * 0.02, 1.4, p + (12 if p < 62 else 0), 42)
                for q, p in enumerate(clear_of(up[1:], bass + 12)):
                    song.add("piano", b0 + 1.5 + q * 0.02, 2.4, p, 37)
                if k == 0:
                    motif(song, b0, 74, 50, extend=2)        # D5 ... up to A5
                for q in range(8):
                    song.add("pulse", b0 + q * 0.5, 0.4, bass,
                             (50 if q % 2 == 0 else 38) + (4 if q == 0 else 0), human=False)
            else:
                # cadence: broadening, fewer notes
                if c == "A7sus4":
                    song.add("piano", b0, 4.0, bass - 12, 48)
                    song.add("piano", b0, 4.0, bass, 44)
                    for q, p in enumerate(up):
                        song.add("piano", b0 + q * 0.05, 2.0, p, 40)
                    # sus4 -> 3 (D -> C#) on beat 3: the dominant "breath"
                    song.add("piano", b0 + 2, 2.0, 55, 36)
                    song.add("piano", b0 + 2, 2.0, 61, 40)
                    song.add("piano", b0 + 2, 2.0, 64, 36)
                    for q in range(2):
                        song.add("pulse", b0 + q * 2, 1.5, bass, 40, human=False)
                else:
                    song.add("piano", b0, 4.0, bass - 12 if bass > 44 else bass, 48)
                    song.add("piano", b0, 4.0, bass, 44)
                    for q, p in enumerate(up):
                        song.add("piano", b0 + 0.5 + q * 0.06, 3.5, p, 42)
                    # top line of the cadence: B4 -> Bb4(G6-ish) -> A4
                    top = {"Gmaj9": 71, "Gm6/Bb": 70}.get(c)
                    if top:
                        song.add("piano", b0 + 2, 2.0, top, 44)
                    for q in range(4):
                        song.add("pulse", b0 + q, 0.8, bass,
                                 44 if q == 0 else 34, human=False)
        elif s == "post":
            if k == 0:
                # THE resolve - lands exactly on the ding downbeat (no humanise)
                song.add("piano", b0, 10.0, 38, 52, human=False)       # D2
                song.add("piano", b0, 10.0, 50, 44, human=False)       # D3
                for p in [57, 62, 64, 66]:
                    song.add("piano", b0, 10.0, p, 46, human=False)
                song.add("piano", b0, 10.0, 74, 42, human=False)       # D5 on top
                song.add("pulse", b0, 3.0, 38, 46, human=False)
            elif k == 1:
                # last, low echo of the motif under "Thank you"
                motif(song, b0, 62, 34, n=4)                         # A3 D4 E4 F#4
    song.chords = chords
    song.section_of = section_of
    return song


# ----------------------------------------------------------------------------
# 4. MIDI out
# ----------------------------------------------------------------------------

def write_midi(song, tm, path, transpose):
    tpb = 480
    mid = mido.MidiFile(ticks_per_beat=tpb)
    meta = mido.MidiTrack()
    mid.tracks.append(meta)
    meta.append(mido.MetaMessage("set_tempo", tempo=int(round(60e6 / tm["bpm"]))))
    meta.append(mido.MetaMessage("time_signature", numerator=4, denominator=4))
    origin_beats = tm["origin"] / tm["beat"]
    marks = sorted([(tm["bars"][k] * 4 + origin_beats, k.upper()) for k in
                    ["hook", "change", "now", "ddn", "ask", "ding"]])
    t_prev = 0
    for b, name in marks:
        t = int(round(b * tpb))
        meta.append(mido.MetaMessage("marker", text=name, time=t - t_prev))
        t_prev = t
    progs = {"piano": 0, "pad": 89, "pulse": 38, "tick": 115}
    for ch, (trk, evs) in enumerate(song.ev.items()):
        tr = mido.MidiTrack()
        mid.tracks.append(tr)
        tr.append(mido.MetaMessage("track_name", name=trk))
        chn = 9 if trk == "tick" else ch
        if trk != "tick":
            tr.append(mido.Message("program_change", program=progs[trk], channel=chn))
        msgs = []
        for (b, d, p, v) in evs:
            p2 = p + transpose if trk != "tick" else p
            on = int(round((b + origin_beats) * tpb))
            off = int(round((b + d + origin_beats) * tpb))
            msgs.append((on, 1, mido.Message("note_on", note=p2, velocity=v, channel=chn)))
            msgs.append((off, 0, mido.Message("note_off", note=p2, velocity=0, channel=chn)))
        msgs.sort(key=lambda x: (x[0], x[1]))
        t_prev = 0
        for t, _, m in msgs:
            tr.append(m.copy(time=t - t_prev))
            t_prev = t
    mid.save(path)


# ----------------------------------------------------------------------------
# 5. DSP helpers
# ----------------------------------------------------------------------------

def mtof(p):
    return 440.0 * 2 ** ((p - 69) / 12.0)


def peaking(x, f0, gain_db, q):
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * f0 / SR
    al = np.sin(w) / (2 * q)
    b = np.array([1 + al * A, -2 * np.cos(w), 1 - al * A])
    a = np.array([1 + al / A, -2 * np.cos(w), 1 - al / A])
    return signal.lfilter(b / a[0], a / a[0], x, axis=0)


def shelf_high(x, f0, gain_db):
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * f0 / SR
    al = np.sin(w) / 2 * np.sqrt(2)
    cw = np.cos(w)
    b0 = A * ((A + 1) + (A - 1) * cw + 2 * np.sqrt(A) * al)
    b1 = -2 * A * ((A - 1) + (A + 1) * cw)
    b2 = A * ((A + 1) + (A - 1) * cw - 2 * np.sqrt(A) * al)
    a0 = (A + 1) - (A - 1) * cw + 2 * np.sqrt(A) * al
    a1 = 2 * ((A - 1) - (A + 1) * cw)
    a2 = (A + 1) - (A - 1) * cw - 2 * np.sqrt(A) * al
    return signal.lfilter(np.array([b0, b1, b2]) / a0, np.array([a0, a1, a2]) / a0, x, axis=0)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "hp", fs=SR, output="sos"), x, axis=0)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "lp", fs=SR, output="sos"), x, axis=0)


def make_ir(rt60=2.0, length=3.0, seed=1, damp=4500.0, predelay=0.012):
    """Synthetic stereo room/plate IR: decorrelated noise, exponential decay,
    progressively darker tail. Pure DSP - no impulse-response samples used."""
    rng = np.random.default_rng(seed)
    n = int(length * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2))
    env = np.exp(-6.9 * t / rt60)
    lo = lp(ir, damp * 0.35, 1)
    hi = ir - lo
    hi *= np.exp(-6.9 * t / (rt60 * 0.45))[:, None]
    ir = (lo * 1.6 + hi) * env[:, None]
    ir = lp(ir, damp, 2)
    fade = np.minimum(1, (n - np.arange(n)) / (0.3 * SR))
    ir *= fade[:, None]
    ir[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))[:, None]
    ir = np.vstack([np.zeros((int(predelay * SR), 2)), ir])
    ir /= np.sqrt(np.sum(ir ** 2) / 2)
    return ir


def reverb(x, ir, wet):
    y = np.stack([signal.fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1)
    return x * (1 - wet * 0.3) + y * wet


# ----------------------------------------------------------------------------
# 6. Piano sampler (Salamander Grand Piano V3 SFZ)
# ----------------------------------------------------------------------------

class Salamander:
    def __init__(self, root=SAL_DIR):
        sfz = None
        for dp, dn, fn in os.walk(root):
            for f in fn:
                if f.lower().endswith(".sfz") and "retuned" in f.lower():
                    sfz = os.path.join(dp, f)
        if sfz is None:
            for dp, dn, fn in os.walk(root):
                for f in fn:
                    if f.lower().endswith(".sfz"):
                        sfz = os.path.join(dp, f)
        if sfz is None:
            raise SystemExit("Salamander SFZ not found under %s" % root)
        self.base = os.path.dirname(sfz)
        self.regions = self._parse(open(sfz, encoding="latin-1").read())
        self.cache = {}
        self.sfz = sfz

    def _parse(self, txt):
        txt = re.sub(r"//[^\n]*", "", txt)
        # the Retuned SFZ has one typo ("tune-27" for "tune=-27"); repair it
        txt = re.sub(r"\btune-(\d+)", r"tune=-\1", txt)
        toks = re.split(r"(<\w+>)", txt)
        regions, group, cur, hdr = [], {}, None, None
        def kv(s):
            d = {}
            for m in re.finditer(r"(\w+)=(.*?)(?=\s+\w+=|$)", s.strip(), re.S):
                d[m.group(1)] = m.group(2).strip()
            return d
        for t in toks:
            if re.fullmatch(r"<\w+>", t):
                hdr = t
                continue
            if hdr == "<group>":
                group = kv(t)
            elif hdr == "<region>":
                r = dict(group)
                r.update(kv(t))
                regions.append(r)
        keep = []
        for r in regions:
            if r.get("trigger", "attack") != "attack":
                continue                        # release / pedal noises
            if "sample" not in r or "lokey" not in r and "key" not in r:
                continue
            if any(k.startswith("on_locc") or k.startswith("locc") for k in r):
                continue
            lk = int(r.get("lokey", r.get("key")))
            hk = int(r.get("hikey", r.get("key")))
            keep.append(dict(lo=lk, hi=hk, lv=int(r.get("lovel", 1)), hv=int(r.get("hivel", 127)),
                             center=int(r.get("pitch_keycenter", r.get("key", lk))),
                             tune=float(r.get("tune", 0)), vol=float(r.get("volume", 0)),
                             sample=r["sample"].replace("\\", "/")))
        return keep

    def region(self, p, v):
        c = [r for r in self.regions if r["lo"] <= p <= r["hi"] and r["lv"] <= v <= r["hv"]]
        if not c:
            c = sorted(self.regions, key=lambda r: abs(r["center"] - p) * 200 + abs(r["lv"] - v))[:1]
        return c[0]

    def load(self, path):
        if path not in self.cache:
            x, sr = sf.read(os.path.join(self.base, path), dtype="float64", always_2d=True)
            assert sr == SR, sr
            if x.shape[1] == 1:
                x = np.repeat(x, 2, 1)
            # the recordings start with ~12-16 ms of pre-roll; trim it so
            # note onsets (and the cadence) land exactly on the grid
            m = np.abs(x).max(1)
            i0 = int(np.argmax(m > 0.02 * m.max()))
            i0 = max(0, i0 - int(0.0015 * SR))
            x = x[i0:].copy()
            x[:32] *= np.linspace(0, 1, 32)[:, None]
            self.cache[path] = x
        return self.cache[path]

    def note(self, p, v, dur, release=0.9):
        r = self.region(p, v)
        x = self.load(r["sample"])
        semis = p - r["center"] + r["tune"] / 100.0
        ratio = 2 ** (semis / 12.0)                  # playback speed
        need = int((dur + release + 0.05) * SR * ratio) + 64
        seg = x[:need]
        if abs(semis) > 1e-6:
            fr = Fraction(1 / ratio).limit_denominator(400)
            seg = signal.resample_poly(seg, fr.numerator, fr.denominator, axis=0)
        n_on = int(dur * SR)
        n_rel = int(release * SR)
        seg = seg[: n_on + n_rel]
        env = np.ones(len(seg))
        if len(seg) > n_on:
            t = np.arange(len(seg) - n_on) / SR
            env[n_on:] = np.exp(-6.9 * t / release) * np.clip(1 - t / release, 0, 1) ** 0.5
        g = 10 ** (r["vol"] / 20) * (0.25 + 0.75 * (v / 127.0) ** 2)
        return seg * env[:, None] * g


# ----------------------------------------------------------------------------
# 7. Synth voices (all synthesised, no samples)
# ----------------------------------------------------------------------------

def pad_voice(p, dur, vel, cutoff, rng):
    """Warm additive pad: three slightly detuned voices, soft-saw spectrum
    rolled off above `cutoff`, slow attack/release, slow drift."""
    att, rel = 1.6, 1.1
    n = int((dur + rel) * SR)
    t = np.arange(n) / SR
    f0 = mtof(p)
    out = np.zeros((n, 2))
    for vi, (det, pan) in enumerate([(-6, 0.15), (0, 0.5), (6, 0.85)]):
        f = f0 * 2 ** (det / 1200)
        drift = 1 + 0.0015 * np.sin(2 * np.pi * (0.13 + 0.05 * vi) * t + rng.uniform(0, 6))
        ph = 2 * np.pi * np.cumsum(f * drift) / SR + rng.uniform(0, 6.28)
        v = np.zeros(n)
        k = 1
        while k * f0 < min(cutoff * 3, 9000):
            a = (1 / k) / (1 + (k * f0 / cutoff) ** 4)
            v += a * np.sin(k * ph)
            k += 1
        out[:, 0] += v * np.cos(pan * np.pi / 2)
        out[:, 1] += v * np.sin(pan * np.pi / 2)
    env = np.ones(n)
    na = int(att * SR)
    env[:na] = np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    nd = int(dur * SR)
    env[nd:] = np.exp(-np.arange(n - nd) / SR * 3.0) * np.linspace(1, 0, n - nd)
    return out * env[:, None] * (vel / 127.0) * 0.12


def pulse_voice(p, dur, vel):
    """Soft felt-bass pulse: sine + gentle 2nd/3rd harmonic, quick decay."""
    d = min(dur, 0.6) + 0.35
    n = int(d * SR)
    t = np.arange(n) / SR
    f = mtof(p)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.08 * np.sin(6 * np.pi * f * t)
    env = (1 - np.exp(-t / 0.006)) * np.exp(-t / 0.13)
    x = x * env * (vel / 127.0) ** 1.5 * 0.5
    x = lp(x, 700)
    return np.stack([x, x], 1)


def tick_voice(p, vel, rng):
    """Clock tick: very short resonant noise click mostly above 4 kHz."""
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n) * np.exp(-t / 0.0025)
    fc = 6200 if p == 76 else 5200
    sos = signal.butter(2, [fc * 0.8, fc * 1.25], "bp", fs=SR, output="sos")
    y = signal.sosfilt(sos, x)
    # a tiny woody body around 2.2 kHz, very short
    body = np.sin(2 * np.pi * (2300 if p == 76 else 1900) * t) * np.exp(-t / 0.002) * 0.04
    y = (y + body) * (vel / 127.0) * 0.25
    return np.stack([y * 0.9, y * 1.0], 1)


def ding_sound(tonic_midi):
    """Soft bell / chime: additive, slightly inharmonic partials, tuned so its
    strike tone is the tonic of the resolve. Fully synthesised."""
    dur = 4.0
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = mtof(tonic_midi)
    partials = [  # (ratio, amp, decay s)
        (0.5, 0.18, 2.2),     # hum (octave below)
        (1.0, 1.00, 1.9),     # strike / fundamental = tonic
        (2.0, 0.30, 1.1),
        (2.997, 0.10, 0.7),   # the 5th above the octave (fits add9 chord)
        (4.07, 0.05, 0.45),
        (5.43, 0.025, 0.3),   # a touch of inharmonic shimmer
    ]
    y = np.zeros(n)
    rng = np.random.default_rng(3)
    for r, a, dcy in partials:
        ph = rng.uniform(0, 6.28)
        beat = 1 + 0.0007 * np.sin(2 * np.pi * 0.7 * t)
        y += a * np.sin(2 * np.pi * f * r * t * beat + ph) * np.exp(-t / dcy)
    att = 1 - np.exp(-t / 0.004)              # soft mallet, no click
    y *= att
    y[-int(0.2 * SR):] *= np.linspace(1, 0, int(0.2 * SR))
    st = np.stack([y, y], 1)
    ir = make_ir(rt60=2.4, length=3.0, seed=11, damp=6000)
    st = reverb(np.vstack([st, np.zeros((int(1.0 * SR), 2))]), ir, 0.35)
    st = st[: n]
    st[-int(0.3 * SR):] *= np.linspace(1, 0, int(0.3 * SR))[:, None]
    st /= np.max(np.abs(st))
    return st * 10 ** (-12 / 20)               # peak -12 dBFS: a quiet ding


# ----------------------------------------------------------------------------
# 8. Render
# ----------------------------------------------------------------------------

def render(song, tm, cfg, outdir):
    tr = int(cfg.get("transpose", 0))
    total = int(math.ceil(tm["end"] * SR))
    pad_len = total + int(6 * SR)
    beat_s = tm["beat"]
    org = tm["origin"]
    rng = np.random.default_rng(int(cfg.get("seed", 7)))
    stems = {k: np.zeros((pad_len, 2)) for k in ["piano", "pad", "pulse", "tick"]}

    def place(buf, start_s, x):
        i = int(round(start_s * SR))
        if i >= len(buf):
            return
        x = x[: len(buf) - i]
        buf[i: i + len(x)] += x

    sal = Salamander()
    for (b, d, p, v) in song.ev["piano"]:
        place(stems["piano"], org + b * beat_s, sal.note(p + tr, v, d * beat_s))

    # pad: cutoff opens with the story
    cut = {"hook": 500, "change": 520, "now": 650, "ddn": 760, "ask": 950, "post": 650}
    for (b, d, p, v) in song.ev["pad"]:
        bar = int(math.floor(b / 4 + 1e-6)) + (1 if (b / 4) % 1 > 0.4 else 0)
        s = song.section_of(bar)
        place(stems["pad"], org + b * beat_s, pad_voice(p + tr, d * beat_s, v, cut[s], rng))
    for (b, d, p, v) in song.ev["pulse"]:
        place(stems["pulse"], org + b * beat_s, pulse_voice(p + tr, d * beat_s, v))
    for (b, d, p, v) in song.ev["tick"]:
        place(stems["tick"], org + b * beat_s, tick_voice(p, v, rng))

    # ---- per-stem processing ----
    ir_room = make_ir(rt60=2.1, length=3.2, seed=1, damp=5000)
    ir_plate = make_ir(rt60=3.0, length=4.0, seed=2, damp=3500, predelay=0.03)
    pn = stems["piano"]
    pn = hp(pn, 45)
    pn = peaking(pn, 2600, -3.0, 0.8)          # speech pocket (1-4 kHz)
    pn = peaking(pn, 90, -3.0, 0.7)            # keep the low end from booming
    pn = reverb(pn, ir_room, 0.28)
    pd = stems["pad"]
    pd = hp(pd, 110)
    pd = peaking(pd, 2500, -4.0, 0.7)
    pd = reverb(pd, ir_plate, 0.45)
    pu = hp(stems["pulse"], 35)
    pu = reverb(pu, ir_room, 0.10)
    tk = reverb(stems["tick"], ir_room, 0.18)
    stems = {"piano": pn * 1.0, "pad": pd * 0.2, "pulse": pu * 0.4, "tick": tk * 0.5}

    # ---- fade out under "Thank you": hold the resolve, then fade to silence at end
    ding_t = org + tm["bars"]["ding"] * tm["bar"]
    f0 = ding_t + 1.2
    f1 = tm["end"]
    t = np.arange(pad_len) / SR
    fade = np.ones(pad_len)
    m = (t >= f0) & (t < f1)
    fade[m] = np.cos(0.5 * np.pi * (t[m] - f0) / (f1 - f0)) ** 2
    fade[t >= f1] = 0
    # also the tiny fade-in at 0 to avoid a click
    fade[: int(0.01 * SR)] *= np.linspace(0, 1, int(0.01 * SR))
    for k in stems:
        stems[k] = (stems[k] * fade[:, None])[:total]

    mix = sum(stems.values())
    # ---- loudness normalise the mix (same gain on every stem so stems sum to mix)
    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    lufs = meter.integrated_loudness(mix)
    target = float(cfg.get("target_lufs", -22.0))
    g = 10 ** ((target - lufs) / 20)
    peak = np.max(np.abs(mix)) * g
    if peak > 10 ** (-3 / 20):                 # keep >= 3 dB sample-peak headroom
        g *= 10 ** (-3 / 20) / peak
    os.makedirs(outdir, exist_ok=True)
    for k, x in stems.items():
        sf.write(os.path.join(outdir, f"stem_{k}.wav"), x * g, SR, subtype="PCM_24")
    mix *= g
    sf.write(os.path.join(outdir, "mix.wav"), mix, SR, subtype="PCM_24")

    ding = ding_sound(74 + 12 + tr)            # D6 strike tone (tonic)
    sf.write(os.path.join(outdir, "ding.wav"), ding, SR, subtype="PCM_24")
    prev = mix.copy()
    i = int(round(ding_t * SR))
    dd = ding * 10 ** (-4 / 20)
    n = min(len(dd), len(prev) - i)
    prev[i: i + n] += dd[:n]
    sf.write(os.path.join(outdir, "mix_with_ding.wav"), prev, SR, subtype="PCM_24")
    return dict(lufs_pre=lufs, gain_db=20 * np.log10(g), ding_time=ding_t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sections", nargs="?", default=os.path.join(HERE, "sections.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    a = ap.parse_args()
    cfg = json.load(open(a.sections))
    tm = plan_timing(cfg)
    song = compose(tm, cfg)
    os.makedirs(a.out, exist_ok=True)
    write_midi(song, tm, os.path.join(a.out, "music.mid"), int(cfg.get("transpose", 0)))
    info = render(song, tm, cfg, a.out)
    bt = lambda b: round(tm["origin"] + b * tm["bar"], 3)
    timing = dict(
        bpm=round(tm["bpm"], 4), bar_seconds=round(tm["bar"], 4), grid_origin=round(tm["origin"], 4),
        sections={k: bt(v) for k, v in tm["bars"].items()},
        section_bars=tm["bars"], ding_time=round(info["ding_time"], 4), end=tm["end"],
        chords={str(k): v for k, v in sorted(song.chords.items())},
        requested={k: cfg[k] for k in ["hook", "change", "now", "ddn", "ask", "ding", "end"]},
        mix_gain_db=round(info["gain_db"], 2),
    )
    json.dump(timing, open(os.path.join(a.out, "timing.json"), "w"), indent=1)
    print(json.dumps({k: timing[k] for k in ["bpm", "sections", "ding_time"]}, indent=1))


if __name__ == "__main__":
    main()
