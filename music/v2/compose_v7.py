#!/usr/bin/env python3
"""
DDN pitch - music bed v7: understated. One warm instrument (soft-mallet
vibraphone, recorded) carries harmony and the motif; a gentle Yamaha RBX bass;
the lightest percussion (CC0 Yamaha kick + shaker) only from Why now.
No pluck layer, no marimba ostinato, few notes, humanised timing/velocity,
rolled chords, softened attacks, more plate - it sits BEHIND the voice.
Same curious -> confident arc and the same edit-locked downbeats/accents.

  /home/user/ddn-project/tools/venv/bin/python compose_v7.py [edit_v7.json] [--out DIR]
"""
import os, sys, json, argparse
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import samplers as S
from compose_v3 import plan, write_midi, render, Song, deg, SEC_BARS
from compose_v4 import CH, Q1, Q2, ANS

PROG = {
    "hook":   ["Gmaj7#11", "Dsus2", "Gmaj7#11", "Asus2"],
    "change": ["Bm11", "Gmaj7#11", "Dsus2/F#", "Em9", "Gmaj7#11", "Asus4"],
    "now":    ["Gmaj7#11", "A/G", "F#m11", "Bm11", "Asus4"],
    "ddn":    ["D", "G/D", "D", "Em7", "Bm7", "A/C#", "D", "Gadd9", "Em7", "F#m7", "G", "Asus"],
    "ask":    ["G", "A", "Bm", "Gmaj7", "A"],
    "punch":  ["Em9", "Asus"],
}
# vibraphone voicings (sounding pitches; the vibes range starts at F3)
VOX = {k: [p + 12 if p < 55 else p for p in v[1]] for k, v in CH.items()}


class HSong(Song):
    """More human: timing sd ~12 ms, velocity +-5, natural accent shape."""
    def add(self, trk, beat, dur, pitch, vel, human=0.022, extra=None):
        if beat in getattr(self, "exact", ()) or human == 0:
            human = 0
        b = beat + (self.rng.normal(0, human) if human else 0)
        v = int(np.clip(vel + (self.rng.integers(-5, 6) if human else 0), 1, 127))
        self.ev[trk].append((b, dur, int(pitch), v, extra))


def roll(s, b0, notes, vel, dur, spread=0.06, trk="vibes"):
    """A gently rolled chord (low to high, 25-45 ms apart), top note a little softer."""
    for k, p in enumerate(sorted(notes)):
        s.add(trk, b0 + k * spread * (0.8 + 0.4 * s.rng.random()), dur, p, vel - 2 * k)


def fig(s, b0, anchor, vel, cell, trk="vibes"):
    for k, (o, st, d) in enumerate(cell):
        s.add(trk, b0 + o, d, deg(anchor, st), vel - (3 if k == 0 else 0))


def compose(tm):
    cfg = tm["cfg"]
    s = HSong(cfg.get("seed", 7))
    SB = tm["sec_beats"]
    s.exact = set(SB.values())
    T, Bt = tm["time"], tm["beat"]
    A = cfg["accents"]
    bars = []
    for sec, _ in SEC_BARS:
        nb = cfg["bars"][sec]
        for i in range(int(np.ceil(nb))):
            bars.append((SB[sec] + 4 * i, sec, i, PROG[sec][i % len(PROG[sec])], nb))
    s.bars = bars
    b_bass = Bt(A["bass_in"])

    for (b0, sec, i, c, nb) in bars:
        bass = CH[c][0]
        vx = VOX[c]
        if sec == "punch":
            continue
        if sec == "hook":
            if i in (0, 2):
                roll(s, b0, vx, 30, 7.5)                    # one soft colour, left to ring
            if i == 0:
                fig(s, b0 + 1.5, 71, 30, Q1)                # the question (B C# F#), once
            if i == 3:
                s.add("vibes", b0 + 2.0, 2.5, 76, 26)       # a lone E5 hangs
            continue
        if sec == "change":
            if i % 2 == 0:
                roll(s, b0, vx, 30, 7.5)
            if i == 4:
                fig(s, b0 + 1.5, 71, 32, Q2)                # asks again, a little further
            if b0 >= b_bass - 1e-6:
                s.add("bass", b0, 3.7, bass, 50)            # long, quiet notes
            elif b0 + 4 > b_bass:
                s.add("bass", b_bass, b0 + 4 - b_bass - 0.1, bass, 50, human=0)
            continue
        if sec == "now":
            roll(s, b0, vx, 32, 3.6)
            if i in (1, 3):
                s.add("vibes", b0 + 2.5, 1.2, vx[-1], 24)   # a soft echo on the "and" of 3
            if i == 2:
                fig(s, b0 + 1.0, 71, 32, Q2)
            s.add("bass", b0, 2.4, bass, 54)
            s.add("bass", b0 + 2.5, 1.3, bass, 46)
            if b0 >= Bt(A["shaker_in"]) - 1e-6:
                for pos in (1, 3):                          # a breath on 2 and 4, not a tick
                    s.add("shaker", b0 + pos, 0, 0, 22)
            if b0 >= Bt(A["kick_in"]) - 1e-6:
                s.add("kick", b0, 0, 36, 30)
            continue
        # ---- Why DDN + ask: warmer, a steady (still soft) pulse ----
        lvl = 2 if sec == "ddn" else 3
        roll(s, b0, vx, 34 + (lvl - 2) * 2, 2.3)
        s.add("vibes", b0 + 2.5, 1.4, vx[1], 26)            # syncopated warmth, one note
        for pos, d, v in [(0, 2.2, 58), (2.5, 1.3, 50)]:
            s.add("bass", b0 + pos, d, bass, v)
        for pos, v in [(0, 34), (2.5, 28)]:
            s.add("kick", b0 + pos, 0, 36, v)
        for q in range(8):
            s.add("shaker", b0 + q * 0.5, 0, q % 2, 18 if q % 2 == 0 else 24)
        if sec == "ddn" and i in (0, 8):
            fig(s, b0 + 0.0, 74, 34, ANS)                   # the answer, twice in the whole section
        if sec == "ask" and i in (0, 2, 4):
            fig(s, b0 + 1.0, [74, 76, 76][i // 2], 32 + i, Q2 if i == 4 else Q1)   # bar 5 = the payoff lift

    # ---- accents (exact times, all on the one instrument) ----
    at = Bt
    g = A["graphics"]
    s.add("vibes", at(g["12%"]), 1.0, 73, 26, human=0); s.add("vibes", at(g["12%"]) + 0.5, 1.4, 76, 22, human=0)
    s.accents.append(("12% vibes", g["12%"]))
    s.add("vibes", at(g["5%"]), 3.0, 69, 26, human=0)
    s.accents.append(("5%: thins to bass + kick + one note until", A["idle_until"]))
    for k, p in enumerate([74, 78, 81]):
        s.add("vibes", at(g["99%"]) + k * 0.2, 2.5, p, 30 - 2 * k, human=0)
    s.accents.append(("99% vibes bloom", g["99%"]))
    for k, p in enumerate([81, 78, 73]):
        s.add("vibes", at(g["75%"]) + k * 0.5, 0.9, p, 26, human=0)
    s.accents.append(("75% vibes fall", g["75%"]))
    sz = A.get("snap_zooms", {})
    if "arsenal" in sz:
        s.add("vibes", at(sz["arsenal"]), 0.5, 78, 24, human=0); s.add("vibes", at(sz["arsenal"]) + 0.5, 1.0, 73, 22, human=0)
        s.accents.append(("snap zoom: vibes fall", sz["arsenal"]))
    for tc, p in A.get("mallet_on", []):
        s.add("vibes", at(tc), 2.0, p, 28, human=0)
        s.accents.append(("vibes note", tc))
    s.accents.append(("bass enters", A["bass_in"]))
    s.accents.append(("shaker enters (2 and 4)", A["shaker_in"]))
    s.add("kick", at(A["kick_in"]), 0, 36, 30, human=0)
    s.accents.append(("soft kick enters", A["kick_in"]))
    for tc in A.get("swell_into", []):
        s.add("cymbal", at(tc), 0, 3, 100, human=0)
        s.accents.append(("soft cymbal swell peaks", tc))

    # "5%": thin out (remove vibes chords + shaker inside the window, keep the accent note)
    t0, t1 = g["5%"] + 0.03, A["idle_until"] - 0.03
    for trk in ["vibes", "shaker"]:
        s.ev[trk] = [e for e in s.ev[trk] if not (t0 < T(e[0]) < t1)]

    # ---- punchline + resolve ----
    p0, r0 = SB["punch"], SB["endcard"]
    s.add("kick", p0, 0, 36, 28, human=0)
    s.add("bass", p0, 1.2, 28, 38, human=0)
    roll(s, p0, [64, 71], 18, 2.0)
    for p in [64, 67]:
        s.add("bowed", p0 + 0.5, (r0 - p0) - 3.0, p, 12, human=0)
    if "blockbuster" in sz:
        s.add("kick", at(sz["blockbuster"]), 0, 36, 28, human=0)
        s.add("bass", at(sz["blockbuster"]), 0.8, 28, 38, human=0)
        s.accents.append(("snap zoom: soft low knock", sz["blockbuster"]))
    s.add("bass", r0 - 2, 2.0, 33, 36, human=0)
    for k, p in enumerate([69, 73, 76]):
        s.add("vibes", r0 - 1.5 + k * 0.5, 0.6, p, 20 + 2 * k, human=0)
    s.add("cymbal", r0, 0, 3, 100, human=0)
    s.add("kick", r0, 0, 36, 38, human=0)
    s.add("bass", r0, 5.0, 38, 62, human=0)
    roll(s, r0, [62, 66, 69, 74, 76], 40, 6.0, spread=0.05)
    s.add("fmpiano", r0 + 0.03, 5.0, 0, 30, human=0, extra=(50, 57, 62, 64))   # a little warmth under the resolve
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timeline", nargs="?", default=os.path.join(HERE, "edit_v7.json"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "out_v7"))
    a = ap.parse_args()
    cfg = json.load(open(a.timeline))
    tm = plan(cfg)
    s = compose(tm)
    os.makedirs(a.out, exist_ok=True)
    write_midi(s, tm, os.path.join(a.out, "music.mid"))
    info = render(s, tm, a.out)
    T = tm["time"]
    timing = dict(
        version=cfg.get("version"),
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
