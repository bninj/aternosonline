#!/usr/bin/env python3
"""
DDN pitch - music bed v4: CURIOUS / SPECULATIVE, soft; resolves into warmth
and a steady pulse by Why DDN.  Same tempo map, downbeats and edit-locked
accents as v3 (plan / MIDI / render are reused from compose_v3).

  /home/user/ddn-project/tools/venv/bin/python compose_v4.py [edit_v4.json] [--out DIR]
"""
import os, sys, json, argparse
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import samplers as S
import compose_v3 as V3
from compose_v3 import plan, write_midi, render, Song, deg, SEC_BARS

# ----------------------------------------------------------------------------
# harmony: D major / G lydian.  Hook + Why change use only sus2/sus4, add9,
# m11 and maj7#11 colours (the #11 = C# over G is the lydian "what if").
# ----------------------------------------------------------------------------
CH = {
    "Gmaj7#11": (31, [59, 61, 66]),        # G | B C# F#
    "Dsus2":    (38, [57, 62, 64]),        # D | A D E
    "Dsus2/F#": (30, [57, 62, 64]),
    "Asus2":    (33, [57, 59, 64]),        # A | A B E
    "Asus4":    (33, [57, 62, 64]),        # A | A D E
    "Bm11":     (35, [57, 61, 64]),        # B | A C# E
    "Em9":      (28, [55, 59, 62, 66]),
    "A/G":      (31, [57, 61, 64]),        # lydian lift
    "F#m11":    (30, [57, 59, 64]),        # F# | A B E
    # Why DDN / ask: the "answer" - warmer, fuller, still add9-coloured
    "D":        (38, [54, 57, 62, 64]),
    "G/D":      (38, [55, 59, 62, 69]),
    "Em7":      (28, [55, 59, 62, 64]),
    "Bm7":      (35, [54, 57, 62, 66]),
    "A/C#":     (37, [52, 57, 61, 64]),
    "Gadd9":    (31, [55, 59, 62, 69]),
    "F#m7":     (30, [52, 57, 61, 64]),
    "Asus":     (33, [52, 57, 62, 64]),
    "A":        (33, [52, 57, 61, 64]),
    "Bm":       (35, [54, 59, 62, 66]),
    "Gmaj7":    (31, [54, 59, 62, 67]),
    "G":        (31, [55, 59, 62, 69]),
}
PROG = {
    "hook":   ["Gmaj7#11", "Dsus2", "Gmaj7#11", "Asus2"],
    "change": ["Bm11", "Gmaj7#11", "Dsus2/F#", "Em9", "Gmaj7#11", "Asus4"],
    "now":    ["Gmaj7#11", "A/G", "F#m11", "Bm11", "Asus4"],
    "ddn":    ["D", "G/D", "D", "Em7", "Bm7", "A/C#", "D", "Gadd9", "Em7", "F#m7", "G", "Asus"],
    "ask":    ["G", "A", "Bm", "Gmaj7"],
    "punch":  ["Em9", "Asus"],
}

# motifs (beat offset, scale step, length): a rising figure that PAUSES ...
Q1 = [(0.0, 0, 0.45), (0.5, 1, 0.45), (1.0, 4, 2.2)]                       # 1-2-5 ?
Q2 = [(0.0, 0, 0.45), (0.5, 1, 0.45), (1.0, 4, 0.45), (1.5, 5, 2.0)]       # 1-2-5-6 ?  (reaches further)
# ... and the answer that arrives in Why DDN: it comes back down and lands
ANS = [(0.0, 5, 0.45), (0.5, 4, 0.45), (1.0, 2, 0.45), (1.5, 1, 0.9), (2.5, 0, 1.4)]   # 6-5-3-2-1


def fig(s, b0, anchor, vel, cell, trk="marimba"):
    for k, (o, st, d) in enumerate(cell):
        s.add(trk, b0 + o, d, deg(anchor, st), vel + (4 if k == len(cell) - 1 else 0))


def compose(tm):
    cfg = tm["cfg"]
    s = Song(cfg.get("seed", 4))
    SB = tm["sec_beats"]
    s.exact = set(SB.values())
    T, Bt = tm["time"], tm["beat"]
    A = cfg["accents"]
    bars = []
    for sec, nb in SEC_BARS:
        for i in range(nb):
            bars.append((SB[sec] + 4 * i, sec, i, PROG[sec][i % len(PROG[sec])], nb))
    s.bars = bars
    b_pluck = Bt(A["pluck_in"])           # 12.30: muted TX81Z plucks enter
    b_bass = Bt(A["bass_in"])             # 18.07: bass enters (gently)

    for (b0, sec, i, c, nb) in bars:
        bass, ch = CH[c]
        nxt = next((CH[x[3]][0] for x in bars if x[0] == b0 + 4), None)

        # ---------------- HOOK: the question, almost nothing else -----------
        if sec == "hook":
            # one soft sus/lydian colour per bar on TX81Z FM piano, very quiet
            s.add("fmpiano", b0, 3.8, 0, 26, extra=tuple(ch))
            if i == 0:
                fig(s, b0 + 1.0, 62, 40, Q1)                      # D E A ...
            elif i == 2:
                fig(s, b0 + 1.0, 62, 42, Q2)                      # D E A B ... (further)
            elif i == 3:
                s.add("vibes", b0 + 2.0, 2.0, 76, 30)             # a lone E5 hangs (sus)
            continue
        if sec == "punch":
            continue
        lvl = {"change": 0, "now": 1, "ddn": 2, "ask": 3}[sec]

        # ---------------- chords: soft sustained TX81Z FM piano --------------
        if lvl <= 1:
            s.add("fmpiano", b0, 3.8, 0, 28 + 2 * lvl, extra=tuple(ch))
        else:
            s.add("fmpiano", b0, 2.2, 0, 34, extra=tuple(ch[:3]))
            s.add("fmpiano", b0 + 2.5, 1.4, 0, 30, extra=tuple(ch[1:4]))

        # ---------------- muted plucks (TX81Z Clavisynth, pizzicato-like) ----
        if lvl == 0:
            # sparse curious plucks on beats 2 and 3&, from the 12.30 cut
            for pos, ci in [(1.0, 0), (2.5, 1), (3.5, 2)]:
                if b0 + pos >= b_pluck - 1e-6:
                    s.add("clav", b0 + pos, 0.12, ch[ci % len(ch)] + 12, 24)
        elif lvl == 1:
            for q in range(8):
                if q in (0, 3, 5, 6):                                  # gentle, syncopated motion
                    s.add("clav", b0 + q * 0.5, 0.12, ch[q % len(ch)] + 12, 26 + (4 if q % 2 else 0))
        else:
            for q in range(8):                                         # steady pulse (the answer)
                s.add("clav", b0 + q * 0.5, 0.12, [ch[0], ch[1], ch[2], ch[1]][q % 4] + 12,
                      26 + (5 if q % 2 else 0) + 2 * (lvl - 2))

        # ---------------- bass (Yamaha RBX finger), enters at 18.07 ----------
        if lvl == 0:
            if b0 >= b_bass - 1e-6:
                s.add("bass", b0, 3.6, bass, 58)
            elif b0 + 4 > b_bass:
                s.add("bass", b_bass, b0 + 4 - b_bass - 0.1, bass, 58, human=0)
        elif lvl == 1:
            s.add("bass", b0, 2.4, bass, 62)
            s.add("bass", b0 + 2.5, 1.3, bass, 56)
        else:
            for pos, d, v in [(0, 1.4, 70), (1.5, 0.45, 56), (2.5, 0.9, 62), (3.5, 0.45, 58)]:
                p = bass
                if pos == 3.5 and nxt is not None and nxt != bass:
                    p = deg(nxt, 1 if nxt < bass else -1)
                    p = p if 28 <= p <= 45 else bass
                s.add("bass", b0 + pos, d, p, v)

        # ---------------- percussion: mostly from Why now --------------------
        if lvl >= 1:
            for q in range(8):
                s.add("shaker", b0 + q * 0.5, 0, q % 2, (24 if q % 2 == 0 else 32) + 3 * lvl, human=0.004)
        if lvl == 1 and b0 >= Bt(A["kick_in"]) - 1e-6:
            s.add("kick", b0, 0, 36, 34)                                # a heartbeat on 1
        if lvl >= 2:
            for pos in ([0, 2.5] if lvl == 2 else [0, 1.5, 2.5]):
                s.add("kick", b0 + pos, 0, 36, 42 if pos == 0 else 34)
            s.add("snare", b0 + 3, 0, 38, 18 + 2 * (lvl - 2))           # brush-soft ghost on 4

        # ---------------- mallet motifs --------------------------------------
        if sec == "change":
            if i in (0, 4):
                fig(s, b0 + 1.0, 59 if i == 0 else 62, 44, Q1 if i == 0 else Q2)   # still asking
            elif i == 2:
                s.add("vibes", b0 + 2.0, 2.0, 73, 28)                            # C#5: unresolved
        elif sec == "now":
            if i in (0, 2):
                fig(s, b0 + 0.5, 62 if i == 0 else 64, 46, Q2)
            elif i in (1, 3):
                for q, ci in enumerate([0, 1, 2]):                               # soft broken chord
                    s.add("marimba", b0 + 1.0 + q, 0.6, ch[ci], 36)
        elif sec == "ddn":
            if c in ("D", "G/D", "Gadd9") and i % 2 == 0:
                fig(s, b0, 66, 50, ANS)                                          # the answer lands
                fig(s, b0, 78, 26, ANS, trk="vibes")
            else:
                for q, ci in enumerate([0, 1, 2, 1]):
                    s.add("marimba", b0 + q + 0.5, 0.4, ch[ci], 36)
        elif sec == "ask":
            fig(s, b0, [62, 64, 66, 69][i], 48 + 2 * i, Q2 if i < 3 else Q1)     # asks once more, higher

    # ---------------- accents at exact edit times (as v3) ----------------
    at = Bt
    s.add("clav", at(A["pluck_in"]), 0.12, 71, 30, human=0)                       # first pluck ON the 12.30 cut
    s.accents.append(("TX81Z plucks enter", A["pluck_in"]))
    s.accents.append(("bass enters", A["bass_in"]))
    for k, p in enumerate([57, 62, 64]):                                          # rising pickup lands on 18.07
        s.add("marimba", at(A["bass_in"]) - 1.5 + k * 0.5, 0.45, p, 36 + 3 * k, human=0)
    s.add("marimba", at(A["bass_in"]), 1.5, 69, 44, human=0)
    s.accents.append(("marimba pickup lands", A["bass_in"]))
    s.add("shaker", at(A["shaker_in"]), 0, 1, 32, human=0)
    s.accents.append(("shaker enters", A["shaker_in"]))
    s.add("kick", at(A["kick_in"]), 0, 36, 36, human=0)
    s.accents.append(("soft kick enters (with swell)", A["kick_in"]))
    for tc in A.get("tom_fill_into", []):
        bc = at(tc)
        for k, (tom, v) in enumerate([(2, 26), (1, 30), (0, 34)]):
            s.add("toms", bc - 1.0 + k * 0.5, 0, tom, v, human=0)
        s.accents.append(("soft tom fill lands", tc))
    for tc, p in A["mallet_on"]:
        s.add("vibes", at(tc), 2.0, p, 34, human=0)
        s.accents.append(("vibes note", tc))
    for tc in A["swell_into"]:
        s.add("cymbal", at(tc), 0, 3, 100, human=0)
        s.accents.append(("cymbal swell peaks", tc))
    g = A["graphics"]
    s.add("vibes", at(g["12%"]), 1.5, 73, 32, human=0)                            # C#5 then E5: a raised eyebrow
    s.add("vibes", at(g["12%"]) + 0.5, 1.5, 76, 28, human=0)
    s.accents.append(("12% vibes", g["12%"]))
    s.add("vibes", at(g["5%"]), 3.0, 69, 30, human=0)
    s.gates.append(("idle", g["5%"], A["idle_until"]))
    s.accents.append(("5%: drop-out until", A["idle_until"]))
    for k, p in enumerate([74, 78, 81]):
        s.add("vibes", at(g["99%"]) + k * 0.25, 2.5, p, 36, human=0)
    s.add("cymbal", at(g["99%"]), 0, 1, 100, human=0)
    s.accents.append(("99% vibes bloom", g["99%"]))
    for k, p in enumerate([69, 66, 61]):
        s.add("marimba", at(g["75%"]) + k * 0.5, 0.45, p, 44, human=0)
    s.accents.append(("75% marimba fall", g["75%"]))
    s.gates.append(("shaker_in", A["shaker_in"], None))

    # ---------------- punchline + resolve (as v3) ----------------
    p0, r0 = SB["punch"], SB["endcard"]
    s.add("kick", p0, 0, 36, 40, human=0)
    s.add("bass", p0, 1.5, 28, 56, human=0)
    s.add("fmpiano", p0, 1.5, 0, 28, human=0, extra=(55, 59, 62))
    for p in [64, 67]:
        s.add("bowed", p0 + 0.5, (r0 - p0) - 3.0, p, 14, human=0)
    s.add("bass", r0 - 2, 2.0, 33, 60, human=0)
    for k, p in enumerate([57, 61, 64]):
        s.add("marimba", r0 - 1.5 + k * 0.5, 0.45, p, 40 + 4 * k, human=0)
    s.add("cymbal", r0, 0, 3, 100, human=0)
    s.add("kick", r0, 0, 36, 52, human=0)
    s.add("bass", r0, 5.0, 38, 80, human=0)
    s.add("fmpiano", r0, 5.0, 0, 44, human=0, extra=(50, 57, 62, 64, 66))
    for p in [50, 57, 62, 66]:
        s.add("marimba", r0, 1.2, p, 56, human=0)
    for p in [74, 78, 81]:
        s.add("vibes", r0, 4.0, p, 40, human=0)
    s.add("cymbal", r0, 0, 4, 100, human=0)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timeline", nargs="?", default=os.path.join(HERE, "edit_v4.json"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "out_v4"))
    a = ap.parse_args()
    cfg = json.load(open(a.timeline))
    tm = plan(cfg)
    s = compose(tm)
    os.makedirs(a.out, exist_ok=True)
    write_midi(s, tm, os.path.join(a.out, "music.mid"))
    info = render(s, tm, a.out)
    T = tm["time"]
    timing = dict(
        version="v4 curious/speculative",
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
