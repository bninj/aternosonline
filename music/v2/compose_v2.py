#!/usr/bin/env python3
"""
DDN pitch - music bed v2 ("live Yamaha rhythm section + marimba motif").

  /home/user/ddn-project/tools/venv/bin/python compose_v2.py [timeline_v2.json] [--out DIR]

Reads the locked edit timeline (seconds), builds a beat grid (constant tempo,
chosen inside bpm_range so the groove entry and the end-card resolve are exact
downbeats; other section changes snap to the nearest beat and start a new bar,
so a section may end with a short 2/4 or 3/4 bar), composes MIDI and renders
stems from recorded, licence-verified samples only.
"""
import os, sys, json, math, argparse
import numpy as np
import soundfile as sf
from scipy import signal
import mido

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import samplers as S

SR = S.SR

# ----------------------------------------------------------------------------
# timing
# ----------------------------------------------------------------------------

def plan(cfg):
    t_in, t_res = cfg["change"], cfg["resolve"]
    lo, hi = cfg.get("bpm_range", [116, 124])
    target = cfg.get("bpm", 120)
    best = None
    for n in range(1, 400):
        bpm = n * 60.0 / (t_res - t_in)
        if lo <= bpm <= hi and (best is None or abs(bpm - target) < abs(best[1] - target)):
            best = (n, bpm)
    n_res, bpm = best
    spb = 60.0 / bpm
    tb = lambda t: (t - t_in) / spb               # time -> beat (0 = groove entry)
    B = {"change": 0, "resolve": n_res}
    for k in ["now", "ddn", "ask"]:
        B[k] = int(round(tb(cfg[k])))
    # drop: the nearest beat at/just before "So Sky,"
    B["drop"] = int(math.floor(tb(cfg["drop"]) + 0.25))
    B["hook"] = -int(cfg.get("hook_bars", 4)) * 4
    return dict(bpm=bpm, spb=spb, t0=t_in, beats=B, end=cfg["end"],
                time=lambda b: t_in + b * spb)


def bars_of(start, end):
    """Split [start,end) beats into bars of 4; a remainder of 2/3 becomes a
    short final bar, a remainder of 1 extends the last bar to 5/4."""
    n = end - start
    q, r = divmod(n, 4)
    lens = [4] * q
    if r in (2, 3):
        lens.append(r)
    elif r == 1:
        if lens:
            lens[-1] = 5
        else:
            lens = [1]
    out, b = [], start
    for L in lens:
        out.append((b, L))
        b += L
    return out


# ----------------------------------------------------------------------------
# harmony (D major / B minor). bass in RBX range (E1=28 .. A2=45)
# ----------------------------------------------------------------------------
CH = {
    #        bass  stab voicing (TX81Z FM piano / marimba chords, mid register)
    "Bm":   (35, [54, 59, 62, 66]),      # B | F# B D F#
    "Bm/A": (33, [54, 59, 62, 66]),
    "G":    (31, [55, 59, 62, 64]),      # G | G B D E  (6th)
    "Gmaj7": (31, [54, 59, 62, 66]),
    "Em7":  (28, [55, 59, 62, 64]),
    "Em9":  (28, [55, 59, 62, 66]),
    "A":    (33, [52, 57, 61, 64]),
    "Asus": (33, [52, 57, 62, 64]),
    "D":    (38, [54, 57, 62, 64]),      # D | F# A D E  (add9)
    "D/F#": (30, [54, 57, 62, 64]),
    "F#m7": (30, [52, 57, 61, 64]),
    "A/C#": (37, [52, 57, 61, 64]),
}
PROG = {
    "hook":   ["Bm", "Bm", "Bm/A", "G"],
    "change": ["Bm", "Bm", "G", "G", "Em7", "Asus", "Asus"],
    "now":    ["G", "A", "Bm", "D/F#", "Em7", "Asus"],
    "ddn":    ["D", "D", "G", "G", "Bm", "A/C#", "D", "D",
               "Em7", "F#m7", "G", "G", "Asus", "Asus"],
    "ask":    ["G", "A", "F#m7", "Bm", "Gmaj7"],
}

# the motif: 1-bar syncopated cell (beat, scale step, length) on a D-major
# scale, anchored per section; it develops from minor question to major answer
DIA = [2, 4, 6, 7, 9, 11, 13]        # D E F# G A B C#  (pitch classes from C)


def deg(anchor, step):
    pcs = sorted({p % 12 for p in DIA})
    n = anchor
    s = 1 if step > 0 else -1
    for _ in range(abs(step)):
        n += s
        while n % 12 not in pcs:
            n += s
    return n


CELL = [(0.0, 0, 0.45), (0.5, 2, 0.45), (1.5, 4, 0.9), (2.5, 3, 1.2)]       # 1-3-5-4
ANSWER = [(0.0, 0, 0.45), (0.5, 2, 0.45), (1.5, 5, 0.9), (2.5, 4, 1.2)]     # 1-3-6-5


class Song:
    def __init__(self, seed=5):
        self.ev = {k: [] for k in ["kick", "snare", "tom_hi", "tom_mid", "tom_lo", "hat", "hat_open",
                                   "shaker", "bass", "marimba", "clav", "fmpiano", "vibes", "bowed", "cymbal"]}
        self.rng = np.random.default_rng(seed)

    def add(self, trk, beat, dur, pitch, vel, human=0.008):
        b = beat + (self.rng.normal(0, human) if human else 0)
        v = int(np.clip(vel + (self.rng.integers(-4, 5) if human else 0), 1, 127))
        self.ev[trk].append((b, dur, int(pitch), v))


def motif(song, b0, anchor, vel, cell=CELL, trk="marimba", oct_double=False):
    for (o, st, d) in cell:
        p = deg(anchor, st)
        song.add(trk, b0 + o, d, p, vel + (6 if o == 0 else 0))
        if oct_double:
            song.add(trk, b0 + o, d, p - 12, vel - 14)


def compose(tm, cfg):
    s = Song(cfg.get("seed", 5))
    B = tm["beats"]
    secs = [("hook", B["hook"], 0), ("change", 0, B["now"]), ("now", B["now"], B["ddn"]),
            ("ddn", B["ddn"], B["ask"]), ("ask", B["ask"], B["drop"])]
    s.bars = []          # (start, len, section, idx, chord)
    for name, a, b in secs:
        bl = bars_of(a, b)
        prog = PROG[name]
        for i, (bs, L) in enumerate(bl):
            last = i == len(bl) - 1
            c = prog[i % len(prog)] if not (last and name != "hook") else prog[-1]
            s.bars.append((bs, L, name, i, c, len(bl)))

    for (b0, L, sec, i, c, nb) in s.bars:
        bass, stab = CH[c]
        last = i == nb - 1
        nxt_bass = None
        for (bb, LL, ss, ii, cc, nn) in s.bars:
            if bb == b0 + L:
                nxt_bass = CH[cc][0]

        # ---------------- HOOK: sparse, playful tension ----------------
        if sec == "hook":
            if i in (0, 2):
                s.add("bass", b0, 1.4, bass, 92)
                s.add("kick", b0, 0, 36, 58)
            if i == 1:
                s.add("bass", b0 + 2.5, 0.4, bass, 70)
                s.add("bass", b0 + 3.0, 0.9, bass + 2 if bass + 2 <= 45 else bass, 76)
            # the motif, alone, dry - a question (minor, last note hangs)
            if i in (0, 2):
                motif(s, b0, 59, 64)                         # B3 D4 F#4 E4
            if i == 1:
                s.add("marimba", b0 + 1.5, 0.4, 66, 54)      # echo fragment
                s.add("marimba", b0 + 2.0, 0.9, 64, 50)
            if i == 3:
                # pickup into the groove: shaker gesture + low tom 8ths + bass walk
                s.add("marimba", b0 + 0.0, 0.45, 59, 60)
                s.add("marimba", b0 + 0.5, 0.45, 62, 60)
                s.add("marimba", b0 + 1.5, 1.5, 69, 62)
                s.add("shaker", b0 + 1.5, 0, 1, 70)
                s.add("tom_lo", b0 + 3.0, 0, 41, 64)
                s.add("tom_mid", b0 + 3.5, 0, 43, 72)
                s.add("bass", b0 + 3.0, 0.45, 31, 86)
                s.add("bass", b0 + 3.5, 0.45, 33, 92)
            continue

        energy = {"change": 0, "now": 1, "ddn": 2, "ask": 3}[sec]

        # ---------------- DRUMS ----------------
        for q in range(int(L * 2)):                       # 8th grid
            pos = q * 0.5
            beat_in = pos % 4
            is_fill_zone = last and L <= 3 and pos >= L - 1.0
            # kick
            kpat = {0: [0, 2.5], 1: [0, 1.5, 2.5], 2: [0, 1.5, 2, 3.5], 3: [0, 1.5, 2, 3, 3.5]}[energy]
            if beat_in in kpat and not is_fill_zone:
                s.add("kick", b0 + pos, 0, 36, 92 if beat_in == 0 else 78)
            # backbeat: snare on 2 and 4 (ghost-soft in change)
            if beat_in in (1, 3) and not is_fill_zone:
                v = {0: 40, 1: 62, 2: 84, 3: 88}[energy]
                s.add("snare", b0 + pos, 0, 38, v)
            # hats: 8ths, accent the offbeats; open hat on the last & of 2-bar phrases
            if not is_fill_zone:
                if energy >= 2 and beat_in == 3.5 and i % 2 == 1:
                    s.add("hat_open", b0 + pos, 0.5, 46, 60)
                else:
                    hv = {0: 42, 1: 52, 2: 60, 3: 64}[energy] + (10 if pos % 1 == 0.5 else 0)
                    s.add("hat", b0 + pos, 0, 42, hv)
        # shaker 16ths from WHY NOW (soft, alternating strokes)
        if energy >= 1:
            for q in range(int(L * 4)):
                pos = q * 0.25
                v = (40 if q % 2 else 54) + 6 * (energy - 1)
                s.add("shaker", b0 + pos, 0, 0 if q % 2 == 0 else 1, v, human=0.004)
        # fills in short bars (section turnarounds) and every 4th bar in DDN/ASK
        if last and L <= 3:
            f0 = b0 + L - 1.0
            for k, (tr, v) in enumerate([("tom_hi", 70), ("tom_mid", 76), ("tom_lo", 82), ("tom_lo", 88)]):
                s.add(tr, f0 + k * 0.25, 0, 45, v + 6 * energy - 6)
            s.add("cymbal", b0 + L, 0, 1, 100, human=0)                    # soft cymbal on the next downbeat
        elif energy >= 2 and i % 4 == 3 and not last:
            s.add("tom_mid", b0 + 3.5, 0, 43, 66)
            s.add("tom_lo", b0 + 3.75, 0, 41, 72)

        # ---------------- BASS (Yamaha RBX, picked) ----------------
        if energy == 0:
            bpat = [(0, 0.45), (1.5, 0.4), (2.0, 0.45), (3.0, 0.4), (3.5, 0.4)]
        else:
            bpat = [(q * 0.5, 0.42) for q in range(8)]
        for (pos, d) in bpat:
            if pos >= L:
                continue
            p = bass
            v = 96 if pos == 0 else (84 if pos % 1 == 0 else 74)
            if energy >= 2 and pos == 3.5 and nxt_bass is not None and nxt_bass != bass:
                # approach note into the next root
                p = nxt_bass + (1 if nxt_bass < bass else -1)
                p = min(max(p, 28), 45)
            if energy >= 1 and pos == 2.0 and bass + 7 <= 45 and i % 2 == 1:
                p = bass + 7                                # the 5th, every other bar
            s.add("bass", b0 + pos, d, p, v)

        # ---------------- MARIMBA motif ----------------
        if sec == "change":
            if i % 2 == 0 and not last:
                motif(s, b0, 59, 58)                       # minor question (B3...)
            elif not last:
                # quiet 8th-note ostinato on chord tones (low, under the voice)
                for q, ci in enumerate([0, 1, 2, 1]):
                    s.add("marimba", b0 + q + 0.5, 0.4, stab[ci], 44)
        elif sec == "now":
            if i % 2 == 0 and not last:
                motif(s, b0, 59, 60, cell=ANSWER)          # same rhythm, wider leap
            elif not last:
                for q, ci in enumerate([0, 1, 2, 1]):
                    s.add("marimba", b0 + q + 0.5, 0.4, stab[ci], 46)
        elif sec == "ddn":
            if i % 4 == 0 and not last:
                motif(s, b0, 62, 66, oct_double=True)      # the motif in D major, doubled low
            elif i % 4 == 2 and not last:
                motif(s, b0, 62, 62, cell=ANSWER, oct_double=True)
            elif not last:
                for q, ci in enumerate([0, 1, 2, 1]):
                    s.add("marimba", b0 + q + 0.5, 0.4, stab[ci], 46)
        elif sec == "ask":
            # lift: the motif climbs a step each bar
            if not last:
                anchor = [62, 64, 66, 67, 69][min(i, 4)]
                motif(s, b0, anchor, 66 + 2 * i, oct_double=True)

        # ---------------- TX81Z keys (sparingly) ----------------
        if sec == "now" and not last:
            # Clavisynth: off-beat plucks, chord tones, low-mid register
            for q in range(4):
                p = stab[(q + i) % 3]
                s.add("clav", b0 + q + 0.5, 0.18, p, 46)
        if sec in ("ddn", "ask") and not last:
            # FM Piano: two short stabs per bar (on 1 and the "and" of 2)
            for pos, v in [(0, 58), (1.5, 50)]:
                for p in stab[:3]:
                    s.add("fmpiano", b0 + pos, 0.35, p, v, human=0.004)
            if sec == "ddn" and i % 2 == 1:
                for q in range(4):
                    s.add("clav", b0 + q + 0.5, 0.15, stab[(q + i) % 3], 40)
        # vibes (hard mallets) colour at the start of each 4-bar phrase in DDN/ASK
        if energy >= 2 and i % 4 == 0:
            for p in stab[1:]:
                s.add("vibes", b0, 2.0, p + 12, 46)

    # ---------------- DROP: "So Sky, don't be the next Blockbuster" ----------
    d0, r0 = B["drop"], B["resolve"]
    s.add("kick", d0, 0, 36, 96)
    s.add("bass", d0, 3.0, 28, 82)                           # E1, rings out
    for p in [55, 59, 62]:
        s.add("marimba", d0, 0.6, p, 66)
    s.add("cymbal", d0, 0, 2, 100, human=0)                              # soft cymbal hit
    for p in [64, 67, 74]:                                    # bowed vibes Em(add9) bed, very soft
        s.add("bowed", d0 + 0.5, (r0 - d0) - 3.0, p, 40, human=0)
    # pickup into the resolve: A sus -> A, cymbal swell, 3 marimba notes
    s.add("bass", r0 - 2, 2.0, 33, 78)
    s.add("cymbal", r0, 0, 3, 100, human=0)                              # 1.5 s crescendo ends ON the resolve
    for k, p in enumerate([57, 61, 64]):
        s.add("marimba", r0 - 1.5 + k * 0.5, 0.45, p, 52 + 4 * k)

    # ---------------- RESOLVE (end card) ----------------
    s.add("kick", r0, 0, 36, 100, human=0)
    s.add("bass", r0, 6.0, 38, 104, human=0)                  # D2
    for p in [50, 57, 62, 66]:
        s.add("marimba", r0, 1.2, p, 74, human=0)
    for p in [62, 66, 69, 76]:
        s.add("vibes", r0, 5.0, p + 12, 60, human=0)
    for p in [50, 57, 62, 64, 66]:
        s.add("fmpiano", r0, 4.0, p, 62, human=0)
    s.add("cymbal", r0, 0, 4, 100, human=0)                              # soft cymbal hit
    # pre-roll swell before the first word (bowed vibes, very soft)
    s.preroll = True
    return s


# ----------------------------------------------------------------------------
# MIDI
# ----------------------------------------------------------------------------

def write_midi(song, tm, path):
    tpb = 480
    mid = mido.MidiFile(ticks_per_beat=tpb)
    meta = mido.MidiTrack(); mid.tracks.append(meta)
    hook_b = tm["beats"]["hook"]
    pre_s = tm["time"](hook_b)                 # seconds before the first hook bar
    # bar 0: one 4/4 bar stretched to the pre-roll length, then the real tempo
    meta.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    meta.append(mido.MetaMessage("set_tempo", tempo=int(round(pre_s / 4 * 1e6)), time=0))
    meta.append(mido.MetaMessage("marker", text="PREROLL", time=0))
    to_tick = lambda b: int(round((b - hook_b + 4) * tpb))   # +4: the pre-roll bar
    evs = [(to_tick(hook_b), 0, mido.MetaMessage("set_tempo", tempo=int(round(tm["spb"] * 1e6))))]
    for (b0, L, sec, i, c, nb) in song.bars:
        if i == 0:
            evs.append((to_tick(b0), 1, mido.MetaMessage("marker", text=sec.upper())))
        evs.append((to_tick(b0), 2, mido.MetaMessage("time_signature", numerator=L if L != 5 else 5, denominator=4)))
    evs.append((to_tick(tm["beats"]["drop"]), 1, mido.MetaMessage("marker", text="DROP")))
    evs.append((to_tick(tm["beats"]["drop"]), 2, mido.MetaMessage("time_signature", numerator=4, denominator=4)))
    evs.append((to_tick(tm["beats"]["resolve"]), 1, mido.MetaMessage("marker", text="RESOLVE")))
    evs.sort(key=lambda e: (e[0], e[1]))
    # remove duplicate consecutive time signatures
    last_ts, t_prev = None, 0
    for t, _, m in evs:
        if m.type == "time_signature":
            if last_ts == (m.numerator,):
                continue
            last_ts = (m.numerator,)
        meta.append(m.copy(time=t - t_prev)); t_prev = t
    gm = {"marimba": 12, "vibes": 11, "bowed": 11, "clav": 7, "fmpiano": 5, "bass": 34}
    drum_note = {"kick": 36, "snare": 38, "tom_hi": 48, "tom_mid": 45, "tom_lo": 41, "hat": 42,
                 "hat_open": 46, "shaker": 70, "cymbal": 52}
    chn = 0
    for trk, evl in song.ev.items():
        if not evl:
            continue
        tr = mido.MidiTrack(); mid.tracks.append(tr)
        tr.append(mido.MetaMessage("track_name", name=trk))
        if trk in gm:
            ch = chn % 9; chn += 1
            tr.append(mido.Message("program_change", program=gm[trk], channel=ch))
        else:
            ch = 9
        msgs = []
        for (b, d, p, v) in evl:
            note = p if trk in gm else drum_note[trk]
            on = max(0, to_tick(b)); off = max(on + 30, to_tick(b + max(d, 0.25)))
            msgs.append((on, 1, mido.Message("note_on", note=note, velocity=v, channel=ch)))
            msgs.append((off, 0, mido.Message("note_off", note=note, velocity=0, channel=ch)))
        msgs.sort(key=lambda x: (x[0], x[1])); t_prev = 0
        for t, _, m in msgs:
            tr.append(m.copy(time=t - t_prev)); t_prev = t
    # pre-roll swell note (bowed vibes) on its own track
    tr = mido.MidiTrack(); mid.tracks.append(tr)
    tr.append(mido.MetaMessage("track_name", name="preroll_bowed"))
    tr.append(mido.Message("program_change", program=11, channel=8))
    tr.append(mido.Message("note_on", note=66, velocity=30, channel=8, time=0))
    tr.append(mido.Message("note_off", note=66, velocity=0, channel=8, time=to_tick(hook_b + 2)))
    mid.save(path)


# ----------------------------------------------------------------------------
# DSP
# ----------------------------------------------------------------------------

def peaking(x, f0, g, q):
    A = 10 ** (g / 40); w = 2 * np.pi * f0 / SR; al = np.sin(w) / (2 * q)
    b = np.array([1 + al * A, -2 * np.cos(w), 1 - al * A]); a = np.array([1 + al / A, -2 * np.cos(w), 1 - al / A])
    return signal.lfilter(b / a[0], a / a[0], x, axis=0)


def shelf(x, f0, g, high=True):
    A = 10 ** (g / 40); w = 2 * np.pi * f0 / SR; al = np.sin(w) / 2 * np.sqrt(2); cw = np.cos(w)
    sA = 2 * np.sqrt(A) * al
    if high:
        b = [A * ((A + 1) + (A - 1) * cw + sA), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sA)]
        a = [(A + 1) - (A - 1) * cw + sA, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sA]
    else:
        b = [A * ((A + 1) - (A - 1) * cw + sA), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - sA)]
        a = [(A + 1) + (A - 1) * cw + sA, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - sA]
    b = np.array(b); a = np.array(a)
    return signal.lfilter(b / a[0], a / a[0], x, axis=0)


def hp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, "hp", fs=SR, output="sos"), x, axis=0)


def lp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, "lp", fs=SR, output="sos"), x, axis=0)


def make_ir(rt60, length, seed, damp, predelay=0.01):
    rng = np.random.default_rng(seed)
    n = int(length * SR); t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)) * np.exp(-6.9 * t / rt60)[:, None]
    ir = lp(ir, damp, 2)
    ir *= np.minimum(1, (n - np.arange(n)) / (0.2 * SR))[:, None]
    ir = np.vstack([np.zeros((int(predelay * SR), 2)), ir])
    return ir / np.sqrt(np.sum(ir ** 2) / 2)


def reverb(x, ir, wet):
    y = np.stack([signal.fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1)
    return x + y * wet


def pan(x, p):                     # p in [-1, 1]
    a = (p + 1) * np.pi / 4
    return np.stack([x[:, 0] * np.cos(a) * 1.414, x[:, 1] * np.sin(a) * 1.414], 1)


def limit(x, ceil_lin, la_s=0.004, rel_s=0.06):
    """Look-ahead peak limiter; returns limited signal."""
    pkenv = np.abs(x).max(1)
    la = max(1, int(la_s * SR))
    pkenv = np.maximum.reduce([np.r_[pkenv[k:], np.zeros(k)] for k in range(0, la, 4)])
    need = np.minimum(1.0, ceil_lin / np.maximum(pkenv, 1e-9))
    gl = np.empty_like(need); cur = 1.0; rel = np.exp(-1 / (rel_s * SR))
    for i in range(len(need)):
        cur = need[i] if need[i] < cur else cur * rel + (1 - rel) * need[i]
        gl[i] = cur
    gl = np.convolve(gl, np.ones(la) / la, "same")
    return x * gl[:, None]


def comp(x, thr_db=-18, ratio=2.5, att=0.005, rel=0.12, makeup=0):
    """Gentle feed-forward bus compressor (glue)."""
    lvl = np.abs(x).max(1)
    a_a = np.exp(-1 / (att * SR)); a_r = np.exp(-1 / (rel * SR))
    env = signal.lfilter([1 - a_r], [1, -a_r], lvl)     # cheap smoothing
    env = np.maximum(env, 1e-9)
    db = 20 * np.log10(env)
    over = np.maximum(0, db - thr_db)
    g = -over * (1 - 1 / ratio) + makeup
    g = signal.lfilter([1 - a_a], [1, -a_a], g)
    return x * (10 ** (g / 20))[:, None]


# ----------------------------------------------------------------------------
# render
# ----------------------------------------------------------------------------

def render(song, tm, cfg, out):
    total = int(round(tm["end"] * SR))
    L = total + 6 * SR
    tb = {k: np.zeros((L, 2)) for k in ["kick", "snare", "toms", "hats", "perc", "bass", "marimba", "keys", "vibes", "fx"]}

    def place(buf, t, x, g=1.0):
        i = int(round(t * SR))
        if i < 0:
            x = x[-i:]; i = 0
        if i >= len(buf):
            return
        x = x[: len(buf) - i]
        buf[i: i + len(x)] += x * g

    T = tm["time"]
    kit = S.drums()
    mar = S.marimba()
    vib = S.vibes("Hard Mallets")
    vbow = S.vibes("Bowed")
    clav = S.tx81z("Clavisynth")
    fmp = S.tx81z("FM Piano")
    bass = S.RBXBass()

    for (b, d, p, v) in song.ev["kick"]:
        place(tb["kick"], T(b), kit["kick"].render(v))
    for (b, d, p, v) in song.ev["snare"]:
        place(tb["snare"], T(b), pan(kit["snare"].render(v), 0.05))
    for k, pn in [("tom_hi", -0.3), ("tom_mid", 0.1), ("tom_lo", 0.35)]:
        for (b, d, p, v) in song.ev[k]:
            place(tb["toms"], T(b), pan(kit[k].render(v), pn))
    for (b, d, p, v) in song.ev["hat"]:
        place(tb["hats"], T(b), pan(kit["hat"].render(v), -0.35))
    for (b, d, p, v) in song.ev["hat_open"]:
        place(tb["hats"], T(b), pan(kit["hat_open"].render(v, choke_s=d * tm["spb"]), -0.35))
    for (b, d, p, v) in song.ev["shaker"]:
        place(tb["perc"], T(b), pan(kit["shaker_up" if p else "shaker_dn"].render(v), 0.45))
    for (b, d, p, v) in song.ev["bass"]:
        place(tb["bass"], T(b), bass.render(p, v, d * tm["spb"]))
    for (b, d, p, v) in song.ev["marimba"]:
        place(tb["marimba"], T(b), pan(mar.render(p, v, d * tm["spb"]), 0.15 if p >= 60 else -0.1))
    for (b, d, p, v) in song.ev["clav"]:
        place(tb["keys"], T(b), pan(clav.render(p, v, d * tm["spb"]), 0.4))
    for (b, d, p, v) in song.ev["fmpiano"]:
        place(tb["keys"], T(b), pan(fmp.render(p, v, d * tm["spb"], release=0.12), -0.25))
    for (b, d, p, v) in song.ev["vibes"]:
        place(tb["vibes"], T(b), pan(vib.render(p, v, d * tm["spb"]), 0.25))
    for (b, d, p, v) in song.ev["bowed"]:
        x = vbow.render(p, v, d * tm["spb"], release=0.8)
        n = len(x); fade = np.minimum(1, np.arange(n) / (0.9 * SR))
        place(tb["vibes"], T(b), x * fade[:, None])
    # cymbals: 1 = soft hit on a section downbeat, 2 = drop hit, 3 = 1.5 s swell
    # ending on the beat, 4 = resolve hit
    for (b, d, p, v) in song.ev["cymbal"]:
        if p == 3:
            x = S.cymbal("susCymb1_cresc_1.5s.wav")
            pk = int(np.argmax(np.abs(x).max(1)))
            place(tb["fx"], T(b) - pk / SR, x * np.r_[np.ones(pk), np.exp(-np.arange(len(x) - pk) / (0.25 * SR))][:, None], 0.5)
        else:
            x = S.cymbal({1: "susCymb2_hit_pp1.wav", 2: "susCymb2_hit_mp1.wav", 4: "susCymb2_hit_mp1.wav"}[p])
            place(tb["fx"], T(b), x, {1: 0.35, 2: 0.45, 4: 0.55}[p])
    # pre-roll: one soft bowed-vibes swell under the empty chair (F#4 -> fades as he speaks)
    pre_end = T(tm["beats"]["hook"])
    x = vbow.render(66, 36, pre_end + 1.0, release=1.5)
    n = len(x); t = np.arange(n) / SR
    env = np.clip(t / 1.4, 0, 1) ** 2 * np.clip((pre_end + 1.6 - t) / 1.8, 0, 1)
    place(tb["vibes"], 0.15, x * env[:, None], 0.8)

    # ---- per-track processing: keep 1-4 kHz clear for the voice ----
    room = make_ir(0.9, 1.4, 1, 6000)
    plate = make_ir(1.8, 2.6, 2, 5000, 0.02)
    k = tb["kick"]; k = hp(k, 38); k = peaking(k, 70, 1.0, 1.0); k = peaking(k, 4500, 3.0, 1.0); k = peaking(k, 300, -4, 1.0); k = peaking(k, 2500, -4, 1.0)
    sn = tb["snare"]; sn = hp(sn, 90); sn = peaking(sn, 2600, -7, 0.7); sn = shelf(sn, 7000, 1.5)
    tm_ = tb["toms"]; tm_ = hp(tm_, 50); tm_ = peaking(tm_, 2500, -6, 0.7)
    h = tb["hats"]; h = hp(h, 3500, 2); h = peaking(h, 3800, -6, 1.0); h = lp(h, 15000)
    pc = tb["perc"]; pc = hp(pc, 4000, 2); pc = peaking(pc, 4200, -4, 1.0)
    drums = k * 0.6 + sn * 0.6 + tm_ * 0.55 + h * 0.36
    drums = reverb(drums, room, 0.10)
    drums = comp(drums, thr_db=-16, ratio=2.0)
    # drum-bus limiter: tame snare/tom peaks to ~12 dB above the bus loudness
    import pyloudnorm as _pl
    _ld = _pl.Meter(SR).integrated_loudness(drums)
    drums = limit(drums, 10 ** ((_ld + 12) / 20))
    perc = pc * 0.30 + 0.0
    bs = tb["bass"]; bs = hp(bs, 38); bs = peaking(bs, 90, -2.0, 0.8); bs = peaking(bs, 700, 2.5, 1.0); bs = peaking(bs, 1400, -6, 0.8); bs = lp(bs, 2600, 2)
    bs = comp(bs, thr_db=-14, ratio=3.0)
    mr = tb["marimba"]; mr = hp(mr, 120); mr = peaking(mr, 2200, -5, 0.8); mr = lp(mr, 4500, 2)
    mr = reverb(mr, plate, 0.18)
    ky = tb["keys"]; ky = hp(ky, 150); ky = peaking(ky, 2500, -6, 0.7); ky = lp(ky, 3500, 2)
    ky = reverb(ky, plate, 0.20)
    vb = tb["vibes"]; vb = hp(vb, 150); vb = peaking(vb, 3000, -4, 0.8); vb = lp(vb, 6000, 2)
    vb = reverb(vb, plate, 0.30)
    fx = tb["fx"]; fx = hp(fx, 200); fx = peaking(fx, 3000, -5, 0.7); fx = lp(fx, 9000)
    fx = reverb(fx, plate, 0.2)

    stems = {"drums": drums, "perc": perc, "bass": bs, "marimba": mr,
             "keys": ky, "vibes": vb, "fx": fx}
    # ---- balance: K-weighted loudness of each stem over the WHY DDN window,
    # set relative to the drums (the arc between sections comes from the
    # arrangement itself, these gains are constant over the whole piece)
    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    rel = cfg.get("balance", {"drums": 0.0, "bass": -3.0, "marimba": -4.0, "keys": -9.0,
                              "vibes": -10.0, "perc": -13.0, "fx": -12.0})
    a0, a1 = int(T(tm["beats"]["ddn"]) * SR), int(T(tm["beats"]["drop"]) * SR)
    ref = meter.integrated_loudness(stems["drums"][a0:a1])
    for kname in stems:
        if kname == "fx":
            continue
        lk = meter.integrated_loudness(stems[kname][a0:a1])
        stems[kname] = stems[kname] * 10 ** ((ref + rel[kname] - lk) / 20)
    # fx (cymbals) are sporadic: level them against the marimba at the resolve
    r0 = int(T(tm["beats"]["resolve"]) * SR)
    lf = meter.integrated_loudness(stems["fx"][r0 - 2 * SR: r0 + 2 * SR])
    lm = meter.integrated_loudness(stems["marimba"][a0:a1])
    stems["fx"] = stems["fx"] * 10 ** ((lm + rel["fx"] + 4 - lf) / 20)
    # ---- end: resolve rings, natural tail, fade to silence at `end` ----
    t = np.arange(L) / SR
    t_res = T(tm["beats"]["resolve"])
    f0, f1 = t_res + 1.3, tm["end"]
    fade = np.ones(L)
    m = (t >= f0) & (t < f1)
    fade[m] = np.cos(0.5 * np.pi * (t[m] - f0) / (f1 - f0)) ** 1.5
    fade[t >= f1] = 0
    for k in stems:
        stems[k] = (stems[k] * fade[:, None])[:total]
    mix = sum(stems.values())
    # transparent peak limiter (5 ms look-ahead) applied as a common gain to
    # mix AND stems, so stems still sum to the mix
    lufs0 = meter.integrated_loudness(mix)
    g0 = 10 ** ((cfg.get("target_lufs", -20.0) - lufs0) / 20)
    ceil = 10 ** (-4.0 / 20)
    pkenv = np.abs(mix * g0).max(1)
    la = int(0.005 * SR)
    pkenv = np.maximum.reduce([np.r_[pkenv[k:], np.zeros(k)] for k in range(0, la, 8)])
    need = np.minimum(1.0, ceil / np.maximum(pkenv, 1e-9))
    gl = np.empty_like(need); cur = 1.0; rel = np.exp(-1 / (0.12 * SR))
    for i in range(len(need)):
        cur = need[i] if need[i] < cur else cur * rel + (1 - rel) * need[i]
        gl[i] = cur
    gl = np.convolve(gl, np.ones(la) / la, "same")
    rep_lim = float(20 * np.log10(gl.min()))
    for k in stems:
        stems[k] = stems[k] * gl[:, None]
    mix = sum(stems.values())
    print("limiter max reduction dB", round(rep_lim, 2))

    lufs = meter.integrated_loudness(mix)
    g = 10 ** ((cfg.get("target_lufs", -20.0) - lufs) / 20)
    pk = np.max(np.abs(signal.resample_poly(mix, 4, 1, axis=0))) * g
    if pk > 10 ** (-3.2 / 20):
        g *= 10 ** (-3.2 / 20) / pk
    os.makedirs(out, exist_ok=True)
    for kname, x in stems.items():
        sf.write(os.path.join(out, f"stem_{kname}.wav"), x * g, SR, subtype="PCM_24")
    sf.write(os.path.join(out, "mix.wav"), mix * g, SR, subtype="PCM_24")
    return dict(gain_db=20 * np.log10(g), lufs_pre=lufs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timeline", nargs="?", default=os.path.join(HERE, "timeline_v2.json"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "out_v2"))
    a = ap.parse_args()
    cfg = json.load(open(a.timeline))
    tm = plan(cfg)
    song = compose(tm, cfg)
    os.makedirs(a.out, exist_ok=True)
    write_midi(song, tm, os.path.join(a.out, "music.mid"))
    info = render(song, tm, cfg, a.out)
    T = tm["time"]
    timing = dict(
        bpm=round(tm["bpm"], 4), seconds_per_beat=round(tm["spb"], 5),
        sections={k: round(T(v), 3) for k, v in tm["beats"].items()},
        section_beats=tm["beats"],
        requested={k: cfg[k] for k in ["change", "now", "ddn", "ask", "drop", "resolve", "end"]},
        bars=[dict(t=round(T(b0), 3), beats=L, section=sec, chord=c) for (b0, L, sec, i, c, nb) in song.bars],
        preroll_swell=[0.15, round(T(tm["beats"]["hook"]) + 1.0, 2)],
        sfx_suggested={"timer_click": 1.85, "impacts": [round(T(tm["beats"][k]), 3) for k in ["change", "now", "ddn", "ask"]],
                       "end_chime": round(T(tm["beats"]["resolve"]), 3)},
        mix_gain_db=round(info["gain_db"], 2),
        samples_used=sorted(os.path.relpath(p, S.CAND) for p in S.USED),
    )
    json.dump(timing, open(os.path.join(a.out, "timing.json"), "w"), indent=1)
    print(json.dumps({k: timing[k] for k in ["bpm", "sections", "mix_gain_db"]}, indent=1))


if __name__ == "__main__":
    main()
