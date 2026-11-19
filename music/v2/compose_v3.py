#!/usr/bin/env python3
"""
DDN pitch - music bed v3: SOFT, warm, confident underscore that follows the edit.

  /home/user/ddn-project/tools/venv/bin/python compose_v3.py [edit_v3.json] [--out DIR]

* Tempo map: a smooth (PCHIP) beat->time curve through the section downbeats
  (hook 1.85, change 10.50, now 23.76, ddn 35.21, ask 62.73, punchline 72.23,
  end card 77.00) -> every section change is an exact downbeat; tempo glides
  between ~112 and ~100 BPM (no jumps).
* Camera switches / graphic beats: accents are placed at the EXACT time
  (a soft mallet note, a layer fading in/out, a cymbal swell that peaks on
  the cut) so they land on the frame even when the cut is between beats.
* Every note is a recorded, licence-verified sample (see MUSIC.md).
"""
import os, sys, json, math, argparse
import numpy as np
import soundfile as sf
from scipy import signal
from scipy.interpolate import PchipInterpolator
import mido

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import samplers as S
from compose_v2 import peaking, shelf, hp, lp, make_ir, reverb, pan, comp

SR = S.SR

# ----------------------------------------------------------------------------
# timing
# ----------------------------------------------------------------------------
SEC_BARS = [("hook", 4), ("change", 6), ("now", 5), ("ddn", 12), ("ask", 4), ("punch", 2)]


def plan(cfg):
    keys = ["hook", "change", "now", "ddn", "ask", "punch", "endcard"]
    t = [cfg["sections"][k] for k in keys]
    beats, b = [0], 0
    bars = cfg.get("bars", dict(SEC_BARS))
    for k in keys[:-1]:
        b += 4 * bars[k]
        beats.append(b)
    f = PchipInterpolator(beats, t, extrapolate=True)
    slope_end = float(f.derivative()(beats[-1]))
    fb = lambda x: np.where(np.asarray(x) <= beats[-1], f(np.minimum(x, beats[-1])),
                            t[-1] + (np.asarray(x) - beats[-1]) * slope_end)
    grid = np.linspace(0, beats[-1] + 16, 20000)
    inv = PchipInterpolator(fb(grid), grid)
    bpm = 60 / f.derivative()(np.linspace(0, beats[-1], 2000))
    return dict(time=lambda x: float(fb(x)), beat=lambda s: float(inv(s)), sec_beats=dict(zip(keys, beats)),
                bpm_min=float(bpm.min()), bpm_max=float(bpm.max()), end=cfg["end"], cfg=cfg)


# ----------------------------------------------------------------------------
# harmony (D major).  bass = Yamaha RBX finger bass (E1..A2)
# ----------------------------------------------------------------------------
CH = {
    "Bm":    (35, [54, 59, 62, 66]),
    "G":     (31, [55, 59, 62, 69]),      # G add9 (A on top)
    "Gmaj7": (31, [54, 59, 62, 67]),
    "G/D":   (38, [55, 59, 62, 67]),
    "D":     (38, [54, 57, 62, 64]),      # D add9
    "D/F#":  (30, [54, 57, 62, 64]),
    "Em7":   (28, [55, 59, 62, 64]),
    "Em9":   (28, [55, 59, 62, 66]),
    "F#m7":  (30, [52, 57, 61, 64]),
    "A/G":   (31, [52, 57, 61, 64]),
    "A/C#":  (37, [52, 57, 61, 64]),
    "Asus":  (33, [52, 57, 62, 64]),
    "A":     (33, [52, 57, 61, 64]),
}
PROG = {
    "hook":   ["Bm", "Bm", "G", "Asus"],
    "change": ["Bm", "G", "D/F#", "Em7", "G", "Asus"],
    "now":    ["G", "A/G", "F#m7", "Bm", "Asus"],
    "ddn":    ["D", "G/D", "D", "Em7", "Bm", "A/C#", "D", "G", "Em7", "F#m7", "G", "Asus"],
    "ask":    ["G", "A", "Bm", "Gmaj7"],
    "punch":  ["Em9", "Asus"],
}
DIA_PCS = sorted({2, 4, 6, 7, 9, 11, 1})


def deg(anchor, step):
    n, s = anchor, (1 if step > 0 else -1)
    for _ in range(abs(step)):
        n += s
        while n % 12 not in DIA_PCS:
            n += s
    return n


CELL = [(0.0, 0, 0.45), (0.5, 2, 0.45), (1.5, 4, 0.9), (2.5, 3, 1.4)]    # 1-3-5-4 (question)
ANSWER = [(0.0, 0, 0.45), (0.5, 2, 0.45), (1.5, 5, 0.9), (2.5, 4, 1.4)]  # 1-3-6-5


class Song:
    def __init__(self, seed):
        self.ev = {k: [] for k in ["kick", "snare", "toms", "shaker", "bass", "marimba", "clav",
                                   "fmpiano", "vibes", "bowed", "cymbal"]}
        self.rng = np.random.default_rng(seed)
        self.gates = []           # (track, t_start, t_end, gain) gain envelopes at exact times
        self.accents = []         # log for timing.json

    def add(self, trk, beat, dur, pitch, vel, human=0.006, extra=None):
        if beat in getattr(self, "exact", ()):      # section downbeats: no humanising
            human = 0
        b = beat + (self.rng.normal(0, human) if human else 0)
        v = int(np.clip(vel + (self.rng.integers(-3, 4) if human else 0), 1, 127))
        self.ev[trk].append((b, dur, int(pitch), v, extra))


def motif(s, b0, anchor, vel, cell=CELL, trk="marimba", n=4):
    for (o, st, d) in cell[:n]:
        s.add(trk, b0 + o, d, deg(anchor, st), vel + (5 if o == 0 else 0))


def compose(tm):
    cfg = tm["cfg"]
    s = Song(cfg.get("seed", 3))
    SB = tm["sec_beats"]
    s.exact = set(SB.values())
    T, Bt = tm["time"], tm["beat"]
    bars = []
    for sec, nb in SEC_BARS:
        for i in range(nb):
            bars.append((SB[sec] + 4 * i, sec, i, PROG[sec][i % len(PROG[sec])], nb))
    s.bars = bars

    for (b0, sec, i, c, nb) in bars:
        bass, ch = CH[c]
        last = i == nb - 1
        nxt = next((CH[x[3]][0] for x in bars if x[0] == b0 + 4), None)
        if sec == "hook":
            # sparse, playful: bass single notes, the motif as a question
            if i in (0, 2):
                s.add("bass", b0, 1.6, bass, 70)
                motif(s, b0, 59 if i == 0 else 62, 46, n=4 if i == 2 else 3)
            if i == 1:
                s.add("bass", b0 + 2.5, 1.2, bass, 60)
                s.add("marimba", b0 + 1.5, 0.45, 66, 40)
                s.add("marimba", b0 + 2.0, 1.0, 64, 38)
            if i == 3:
                s.add("bass", b0, 2.0, bass, 66)
                s.add("bass", b0 + 3.0, 0.45, 31, 60)
                s.add("bass", b0 + 3.5, 0.45, 33, 64)
                for k, p in enumerate([57, 62, 64]):
                    s.add("marimba", b0 + 2 + k * 0.5, 0.45, p, 40 + 3 * k)
                s.add("toms", b0 + 3.0, 0, 0, 30)      # 0 = floor tom
                s.add("toms", b0 + 3.5, 0, 1, 34)      # 1 = mid tom
            continue

        lvl = {"change": 0, "now": 1, "ddn": 2, "ask": 3, "punch": -1}[sec]
        if sec == "punch":
            continue

        # ---- soft kit: Yamaha kick, shaker, ghost snare (DDN/ASK) ----
        kpat = {0: [0, 2.5], 1: [0, 2.5, 3.5], 2: [0, 1.5, 2.5], 3: [0, 1.5, 2.5, 3.5]}[lvl]
        for pos in kpat:
            s.add("kick", b0 + pos, 0, 36, 46 if pos == 0 else 36)
        for q in range(8):
            v = (30 if q % 2 == 0 else 40) + 4 * lvl
            s.add("shaker", b0 + q * 0.5, 0, q % 2, v, human=0.004)
        if lvl >= 2:
            for pos in (1, 3):
                s.add("snare", b0 + pos, 0, 38, 22 + 3 * (lvl - 2))

        # ---- bass (RBX finger): warm, mostly roots, gentle syncopation ----
        if lvl == 0:
            bp = [(0, 1.8, 74), (2.5, 1.3, 64)]
        elif lvl == 1:
            bp = [(0, 1.4, 76), (1.5, 0.45, 60), (2.5, 1.3, 66)]
        else:
            bp = [(0, 1.4, 78), (1.5, 0.45, 62), (2.0, 0.45, 64), (3.0, 0.45, 62), (3.5, 0.45, 66)]
        for pos, d, v in bp:
            p = bass
            if pos == 3.5 and nxt is not None and nxt != bass:
                p = deg(nxt, 1 if nxt < bass else -1)          # diatonic approach (no chromatic rub)
                p = p if 28 <= p <= 45 else bass
            if pos == 2.0 and i % 2 == 1 and bass + 7 <= 45:
                p = bass + 7
            s.add("bass", b0 + pos, d, p, v)

        # ---- TX81Z FM Piano: soft sustained chords (gentle, low velocity) ----
        s.add("fmpiano", b0, 3.6 if lvl < 2 else 2.2, 0, 34 + 2 * lvl, extra=tuple(ch[:3]))
        if lvl >= 2:
            s.add("fmpiano", b0 + 2.5, 1.4, 0, 30, extra=tuple(ch[1:4]))

        # ---- TX81Z Clavisynth: muted 8th pulse from WHY NOW ----
        if lvl >= 1:
            for q in range(8):
                p = [ch[0], ch[1], ch[2], ch[1]][q % 4] + 12
                s.add("clav", b0 + q * 0.5, 0.12, p, 24 + (6 if q % 2 else 0) + 2 * lvl)

        # ---- marimba: motif (develops) / soft ostinato ----
        if sec == "change":
            if i in (0, 4):
                motif(s, b0, 59, 46, n=3 if i == 0 else 4)
            elif i in (2, 3):                                  # ostinato from the 18.07 cut on
                for q, ci in enumerate([0, 1, 2, 1]):
                    s.add("marimba", b0 + q + 0.5, 0.4, ch[ci], 34)
        elif sec == "now":
            if i in (1, 3):                                    # 25.46 cut: the answer
                motif(s, b0, 64 if i == 1 else 62, 48, cell=ANSWER)
            else:
                for q, ci in enumerate([0, 1, 2, 1]):
                    s.add("marimba", b0 + q + 0.5, 0.4, ch[ci], 36)
        elif sec == "ddn":
            if i in (1, 5, 9) and c not in ("A/C#", "F#m7", "A", "Asus"):  # 37.18: motif in D major
                motif(s, b0, 62, 52)
                motif(s, b0, 74, 30, trk="vibes")              # soft vibes double (octave up)
            elif i in (3, 7):
                motif(s, b0, 62, 48, cell=ANSWER)
            else:
                for q, ci in enumerate([0, 1, 2, 1]):
                    s.add("marimba", b0 + q + 0.5, 0.4, ch[ci], 38)
        elif sec == "ask":
            motif(s, b0, [62, 64, 66, 69][i], 50 + 2 * i, n=4 if i < 3 else 3)  # lift: the motif climbs
            if i == 3:
                s.add("vibes", b0 + 2.5, 1.5, 74, 34)

    # ---------------- accents at exact edit times ----------------
    A = cfg["accents"]
    def at(t):
        return Bt(t)
    # soft tom fills into the 18.07 and 48.75 cuts (last note ON the cut)
    for tc in A["tom_fill_into"]:
        bc = at(tc)
        for k, (tom, v) in enumerate([(2, 30), (1, 34), (0, 38)]):
            s.add("toms", bc - 1.0 + k * 0.5, 0, tom, v, human=0)
        s.accents.append(("tom fill lands", tc))
    # a single soft mallet note exactly on cuts that carry no other change
    for tc, p in A["mallet_on"]:
        s.add("vibes", at(tc), 2.0, p, 36, human=0)
        s.accents.append(("vibes note", tc))
    # cymbal swells peaking exactly on a cut
    for tc in A["swell_into"]:
        s.add("cymbal", at(tc), 0, 3, 100, human=0)
        s.accents.append(("cymbal swell peaks", tc))
    # graphic beats
    g = A["graphics"]
    s.add("vibes", at(g["12%"]), 1.5, 74, 34, human=0)                       # D5
    s.add("vibes", at(g["12%"]) + 0.5, 1.5, 78, 30, human=0)                 # F#5
    s.accents.append(("12% vibes", g["12%"]))
    s.add("vibes", at(g["5%"]), 3.0, 69, 32, human=0)                        # single lonely A4
    s.gates.append(("idle", g["5%"], A["idle_until"]))                       # layers drop out
    s.accents.append(("5%: drop-out until", A["idle_until"]))
    for k, p in enumerate([74, 78, 81]):                                       # 99%: chord blooms
        s.add("vibes", at(g["99%"]) + k * 0.25, 2.5, p, 38, human=0)
    s.add("cymbal", at(g["99%"]), 0, 1, 100, human=0)
    s.accents.append(("99% vibes bloom", g["99%"]))
    for k, p in enumerate([69, 66, 61]):                                       # 75%: falls (F#m7 tones)
        s.add("marimba", at(g["75%"]) + k * 0.5, 0.45, p, 46, human=0)
    s.accents.append(("75% marimba fall", g["75%"]))
    # layers that enter exactly on a cut
    s.gates.append(("shaker_in", A["shaker_in"], None))
    s.add("shaker", at(A["shaker_in"]), 0, 1, 44, human=0)                    # first stroke ON the cut
    s.accents.append(("shaker enters", A["shaker_in"]))

    # ---------------- punchline + resolve ----------------
    p0, r0 = SB["punch"], SB["endcard"]
    s.add("kick", p0, 0, 36, 40, human=0)
    s.add("bass", p0, 1.5, 28, 56, human=0)                                    # E1, short
    s.add("fmpiano", p0, 1.5, 0, 28, human=0, extra=(55, 59, 62))
    for p in [64, 67]:
        s.add("bowed", p0 + 0.5, (r0 - p0) - 3.0, p, 14, human=0)              # barely-there Em air
    s.add("bass", r0 - 2, 2.0, 33, 60, human=0)
    for k, p in enumerate([57, 61, 64]):
        s.add("marimba", r0 - 1.5 + k * 0.5, 0.45, p, 40 + 4 * k, human=0)
    s.add("cymbal", r0, 0, 3, 100, human=0)                                    # swell peaks on the end card
    # resolve (end card)
    s.add("kick", r0, 0, 36, 52, human=0)
    s.add("bass", r0, 5.0, 38, 80, human=0)
    s.add("fmpiano", r0, 5.0, 0, 44, human=0, extra=(50, 57, 62, 64, 66))
    for p in [50, 57, 62, 66]:
        s.add("marimba", r0, 1.2, p, 56, human=0)
    for p in [74, 78, 81]:
        s.add("vibes", r0, 4.0, p, 40, human=0)
    s.add("cymbal", r0, 0, 4, 100, human=0)
    return s


# ----------------------------------------------------------------------------
# MIDI (tempo map written as a tempo change on every 8th note)
# ----------------------------------------------------------------------------

def write_midi(s, tm, path):
    tpb = 480
    T = tm["time"]
    mid = mido.MidiFile(ticks_per_beat=tpb)
    meta = mido.MidiTrack(); mid.tracks.append(meta)
    meta.append(mido.MetaMessage("time_signature", numerator=4, denominator=4))
    # a pre-roll bar (0 -> 1.85 s) then the tempo map
    pre = T(0)
    tick = lambda b: int(round((b + 4) * tpb))
    evs = [(0, mido.MetaMessage("set_tempo", tempo=int(round(pre / 4 * 1e6)))),
           (0, mido.MetaMessage("marker", text="PREROLL"))]
    endb = tm["sec_beats"]["endcard"] + 6
    b = 0.0
    while b < endb:
        dt = T(b + 0.5) - T(b)
        evs.append((tick(b), mido.MetaMessage("set_tempo", tempo=int(round(dt * 2 * 1e6)))))
        b += 0.5
    for k, v in tm["sec_beats"].items():
        evs.append((tick(v), mido.MetaMessage("marker", text=k.upper())))
    evs.sort(key=lambda e: e[0]); tp = 0
    for t, m in evs:
        meta.append(m.copy(time=t - tp)); tp = t
    gm = {"marimba": 12, "vibes": 11, "bowed": 11, "clav": 7, "fmpiano": 5, "bass": 33}
    dn = {"kick": 36, "snare": 38, "shaker": 70, "cymbal": 52}
    ch_i = 0
    for trk, evl in s.ev.items():
        if not evl:
            continue
        tr = mido.MidiTrack(); mid.tracks.append(tr)
        tr.append(mido.MetaMessage("track_name", name=trk))
        if trk in gm:
            ch = ch_i % 9; ch_i += 1
            tr.append(mido.Message("program_change", program=gm[trk], channel=ch))
        else:
            ch = 9
        msgs = []
        for (b, d, p, v, ex) in evl:
            notes = list(ex) if (trk == "fmpiano" and ex) else [p]
            if trk == "toms":
                notes = [[41, 45, 48][p]]
            elif trk in dn:
                notes = [dn[trk]]
            for n in notes:
                on = max(0, tick(b)); off = max(on + 30, tick(b + max(d, 0.25)))
                msgs.append((on, 1, mido.Message("note_on", note=n, velocity=v, channel=ch)))
                msgs.append((off, 0, mido.Message("note_off", note=n, velocity=0, channel=ch)))
        msgs.sort(key=lambda x: (x[0], x[1])); tp = 0
        for t, _, m in msgs:
            tr.append(m.copy(time=t - tp)); tp = t
    mid.save(path)


# ----------------------------------------------------------------------------
# render
# ----------------------------------------------------------------------------

def gate_env(n, t_on, t_off=None, fade=0.25, off_gain=0.0, before_gain=None):
    t = np.arange(n) / SR
    e = np.ones(n)
    if t_off is None:        # layer ENTERS at t_on (silent before)
        e = np.clip((t - t_on) / fade + 1.0, 0, 1) if fade > 0 else (t >= t_on).astype(float)
        e = np.clip((t - (t_on - 0.03)) / 0.06, 0, 1)
    else:                    # layer DROPS OUT between t_on and t_off
        down = np.clip((t - t_on) / fade, 0, 1)
        up = np.clip((t - (t_off - 0.03)) / 0.06, 0, 1)
        e = 1 - down * (1 - up) * (1 - off_gain)
    return e


def render(s, tm, out):
    cfg = tm["cfg"]
    T = tm["time"]
    total = int(round(tm["end"] * SR))
    L = total + 6 * SR
    tb = {k: np.zeros((L, 2)) for k in ["kick", "snare", "toms", "shaker", "bass", "marimba", "keys", "vibes", "fx"]}

    def place(buf, t, x, g=1.0):
        i = int(round(t * SR))
        if i < 0:
            x = x[-i:]; i = 0
        if i >= len(buf):
            return
        x = x[: len(buf) - i]
        buf[i: i + len(x)] += x * g

    kit = S.drums()
    mar = S.marimba()
    vs = S.vibes("Soft Mallets")
    vbow = S.vibes("Bowed")
    clav = S.tx81z("Clavisynth")
    fmp = S.tx81z("FM Piano")
    bass = S.RBXBass(S.RBXF)
    toms = [kit["tom_lo"], kit["tom_mid"], kit["tom_hi"]]
    dur = lambda b, d: T(b + d) - T(b)

    for (b, d, p, v, ex) in s.ev["kick"]:
        place(tb["kick"], T(b), kit["kick"].render(v))
    for (b, d, p, v, ex) in s.ev["snare"]:
        place(tb["snare"], T(b), kit["snare"].render(v))
    for (b, d, p, v, ex) in s.ev["toms"]:
        place(tb["toms"], T(b), pan(toms[p].render(v), [0.3, 0.0, -0.3][p]))
    for (b, d, p, v, ex) in s.ev["shaker"]:
        place(tb["shaker"], T(b), pan(kit["shaker_up" if p else "shaker_dn"].render(v), 0.4))
    for (b, d, p, v, ex) in s.ev["bass"]:
        place(tb["bass"], T(b), bass.render(p, v, dur(b, d), release=0.15))
    for (b, d, p, v, ex) in s.ev["marimba"]:
        place(tb["marimba"], T(b), pan(mar.render(p, v, dur(b, d)), 0.15))
    for (b, d, p, v, ex) in s.ev["clav"]:
        place(tb["keys"], T(b), pan(clav.render(p, v, dur(b, d), release=0.05), 0.35), 0.5)
    for (b, d, p, v, ex) in s.ev["fmpiano"]:
        for n in ex:
            place(tb["keys"], T(b) + 0.012 * ex.index(n), pan(fmp.render(n, v, dur(b, d), release=0.35), -0.2))
    for (b, d, p, v, ex) in s.ev["vibes"]:
        place(tb["vibes"], T(b), pan(vs.render(p, v, dur(b, d), release=1.0), -0.25))
    for (b, d, p, v, ex) in s.ev["bowed"]:
        x = vbow.render(p, v, dur(b, d), release=1.0)
        x *= np.minimum(1, np.arange(len(x)) / (0.9 * SR))[:, None]
        place(tb["vibes"], T(b), x, 0.25)
    for (b, d, p, v, ex) in s.ev["cymbal"]:
        if p == 3:
            x = S.cymbal("susCymb1_cresc_1.5s.wav")
            pk = int(np.argmax(np.abs(x).max(1)))
            x = x * np.r_[np.ones(pk), np.exp(-np.arange(len(x) - pk) / (0.2 * SR))][:, None]
            place(tb["fx"], T(b) - pk / SR, x, 0.5)
        else:
            x = S.cymbal("susCymb2_hit_pp1.wav")
            place(tb["fx"], T(b), x, {1: 0.4, 4: 0.6}[p])
    # pre-roll swell: bowed vibes F#4 + D5 under the empty chair
    pre = T(0)                                   # hook start (1.85 in v3/v4)
    dpre = pre + 0.75
    x = vbow.render(66, 30, dpre, release=1.2) + 0.6 * vbow.render(74, 28, dpre, release=1.2)
    n = len(x); t = np.arange(n) / SR
    rise = min(1.2, 0.65 * pre)
    env = np.clip(t / rise, 0, 1) ** 2 * np.clip((dpre + 0.1 - t) / min(1.5, dpre * 0.6), 0, 1)
    place(tb["vibes"], 0.10, x * env[:, None], 0.18)

    # ---- gain envelopes at exact edit times ----
    for kind, t_on, t_off in s.gates:
        if kind == "shaker_in":
            tb["shaker"] *= gate_env(L, t_on)[:, None]
        elif kind == "idle":                       # "5%": thin to kick + bass + one note
            e = gate_env(L, t_on, t_off, fade=0.35, off_gain=0.0)[:, None]
            for k in ["shaker", "marimba", "keys", "snare"]:
                tb[k] *= e

    # ---- processing: soft + keep 1-4 kHz clear ----
    room = make_ir(0.8, 1.2, 1, 5000)
    plate = make_ir(1.9, 2.8, 2, 4500, 0.02)
    k = hp(tb["kick"], 38); k = lp(k, 1800, 2); k = peaking(k, 350, -4, 1.0)            # soft thump
    sn = hp(tb["snare"], 120); sn = lp(sn, 2200, 2); sn = peaking(sn, 1500, -4, 0.8)    # ghost backbeat, brush-soft
    to = hp(tb["toms"], 50); to = lp(to, 1500, 2)
    sh = hp(tb["shaker"], 3500, 2); sh = peaking(sh, 4000, -6, 1.0); sh = lp(sh, 11000)
    drums = k * 1.0 + sn * 0.9 + to * 0.8
    drums = reverb(drums, room, 0.12)
    bs = hp(tb["bass"], 35); bs = lp(bs, 1500, 2); bs = comp(bs, -18, 2.5)
    mr = hp(tb["marimba"], 140); mr = peaking(mr, 2300, -6, 0.8); mr = lp(mr, 3200, 2); mr = reverb(mr, plate, 0.22)
    ky = hp(tb["keys"], 140); ky = peaking(ky, 2500, -6, 0.8); ky = lp(ky, 2600, 2); ky = reverb(ky, plate, 0.25)
    vb = hp(tb["vibes"], 150); vb = peaking(vb, 3000, -5, 0.8); vb = lp(vb, 5000, 2); vb = reverb(vb, plate, 0.35)
    fx = hp(tb["fx"], 300); fx = lp(fx, 7000, 2); fx = reverb(fx, plate, 0.25)
    stems = {"drums": drums, "shaker": sh, "bass": bs, "marimba": mr, "keys": ky, "vibes": vb, "fx": fx}

    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    rel = cfg.get("balance")
    a0 = int(T(tm["sec_beats"]["ddn"]) * SR); a1 = int(T(tm["sec_beats"]["punch"]) * SR)
    ref = meter.integrated_loudness(stems["bass"][a0:a1])
    for kname in stems:
        if kname == "fx":
            continue
        lk = meter.integrated_loudness(stems[kname][a0:a1])
        stems[kname] = stems[kname] * 10 ** ((ref + rel[kname] - lk) / 20)
    r0 = int(T(tm["sec_beats"]["endcard"]) * SR)
    lf = meter.integrated_loudness(stems["fx"][r0 - 2 * SR: r0 + 2 * SR])
    lm = meter.integrated_loudness(stems["marimba"][a0:a1])
    stems["fx"] = stems["fx"] * 10 ** ((lm + rel["fx"] - lf) / 20)

    # ---- end: resolve rings, then fade to silence by `end` ----
    t = np.arange(L) / SR
    tr = T(tm["sec_beats"]["endcard"])
    f0, f1 = tr + 1.2, tm["end"] - 0.02
    fade = np.ones(L)
    m = (t >= f0) & (t < f1)
    fade[m] = np.cos(0.5 * np.pi * (t[m] - f0) / (f1 - f0)) ** 1.5
    fade[t >= f1] = 0
    for kname in stems:
        stems[kname] = (stems[kname] * fade[:, None])[:total]
    mix = sum(stems.values())
    lufs = meter.integrated_loudness(mix)
    g = 10 ** ((cfg.get("target_lufs", -20.0) - lufs) / 20)
    pk = np.max(np.abs(signal.resample_poly(mix, 4, 1, axis=0))) * g
    if pk > 10 ** (-3.3 / 20):
        g *= 10 ** (-3.3 / 20) / pk
    os.makedirs(out, exist_ok=True)
    for kname, x in stems.items():
        sf.write(os.path.join(out, f"stem_{kname}.wav"), x * g, SR, subtype="PCM_24")
    sf.write(os.path.join(out, "music_mix.wav"), mix * g, SR, subtype="PCM_24")
    return dict(gain_db=20 * np.log10(g), lufs_pre=lufs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timeline", nargs="?", default=os.path.join(HERE, "edit_v3.json"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "out_v3"))
    a = ap.parse_args()
    cfg = json.load(open(a.timeline))
    tm = plan(cfg)
    s = compose(tm)
    os.makedirs(a.out, exist_ok=True)
    write_midi(s, tm, os.path.join(a.out, "music.mid"))
    info = render(s, tm, a.out)
    T = tm["time"]
    timing = dict(
        tempo_map="smooth PCHIP beat->time through the section downbeats; see bars[] for every downbeat",
        bpm_min=round(tm["bpm_min"], 2), bpm_max=round(tm["bpm_max"], 2),
        section_downbeats={k: round(T(v), 4) for k, v in tm["sec_beats"].items()},
        requested=cfg["sections"],
        bars=[dict(t=round(T(b0), 3), section=sec, chord=c) for (b0, sec, i, c, nb) in s.bars],
        accents=[dict(what=w, t=round(t, 3)) for w, t in s.accents],
        mix_gain_db=round(info["gain_db"], 2),
        samples_used=sorted(os.path.relpath(p, S.CAND) for p in S.USED),
    )
    json.dump(timing, open(os.path.join(a.out, "timing.json"), "w"), indent=1)
    print(json.dumps({k: timing[k] for k in ["bpm_min", "bpm_max", "section_downbeats", "mix_gain_db"]}, indent=1))


if __name__ == "__main__":
    main()
