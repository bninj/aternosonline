# Music bed: DDN "Why DDN" pitch (~85 s)

## Concept
This is an original instrumental bed with no vocals, written for a voice-over aimed at older professionals. The feel is warm, confident and unhurried. A clean grand piano carries everything, with a soft pad underneath and a felt-like pulse that grows from nothing into a steady heartbeat. There is no drop, no drum kit and no big build.

- **Motif.** One four-note idea (scale degrees 5-1-2-3: a pickup, a dotted quarter, an eighth and a half note) develops across the piece:
  - WHY CHANGE: it is stated in B minor, unanswered (3 notes, held).
  - WHY NOW: it is completed over G.
  - WHY DDN: it moves to D major (A4-D5-E5-F#5), with a falling 3-2-1 answer.
  - ASK: it extends up to A5 for the lift.
  - After the ding: one last quiet, low statement (A3-D4-E4-F#4) under "Thank you".
- **Harmony.** There is no four-chord loop. The chords are open add9 / sus2 / maj9 / 6-9 voicings and inversions, all diatonic to D major / B minor:
  - WHY CHANGE: a descending bass line (B-A-G-F#-E).
  - WHY DDN: a tonic pedal for steadiness.
  - The ask cadence is **Gmaj9 → Gm6/B♭ (borrowed iv) → A7sus4 → A → D(add9)**. The bass runs G-B♭-A-D, and the top voice moves B-B♭-A.
- **Speech room.** Piano voicings stay between B1 and A4. The melody peaks at A5 (880 Hz) only in the ask lift. The pad is low-passed (520–950 Hz depending on section). The piano gets −3 dB at 2.6 kHz and the pad −4 dB at 2.5 kHz (a "speech pocket"). Measured share of mix energy in 1–4 kHz is about 1 % in every music section.

## Key / tempo / structure (default draft)
Key: **D major** (B minor colour at the start). Tempo: **104.35 BPM**, flexed from 104 so that the ding falls on bar 35's downbeat. Time signature 4/4, bar = 2.300 s.

| Section | Requested | Bar-snapped | What plays |
|---|---|---|---|
| HOOK | 0–9 | 0.0–9.2 (bars 0–3) | faint clock tick only; the pad swells in during the last half bar |
| WHY CHANGE | 9–27 | 9.2–27.6 (4–11) | sparse piano: low bass note, a quiet rolled chord, the motif as a question; the tick recedes |
| WHY NOW | 27–44 | 27.6–43.7 (12–18) | light movement: broken-chord left hand; a soft quarter-note pulse enters |
| WHY DDN | 44–70 | 43.7–69.0 (19–29) | steady eighth-note pulse, gently syncopated chords, motif in major |
| ASK | 70–85 | 69.0–80.5 (30–34) | gentle lift (the voicing rises an octave, the pad opens), then the 3-bar cadence |
| DING | 80.5 | **80.500** (bar 35 downbeat) | D(add9) resolve lands exactly here (measured onset offset: 0 ±1 ms) |
| end | 85.5 | 85.5 | the chord holds, then a cos² fade to digital silence at 85.5 s |

Measured on the draft (`out/analysis.json`):
- Integrated −22.0 LUFS; true peak −5.7 dBTP; no clipping.
- Loudness by section: hook −43, change −25, now −23, ddn −21, ask −21, post −23 LUFS.
- The last 100 ms is at −87 dBFS and the final sample is 0.
- The piano chroma at the ding is D / F# / A / E.

The spectrogram is in `out/spectrogram.png`.

## Files
- `compose.py`: the generator (timing → composition → MIDI → render → mix).
- `analyze.py`: the objective checks and the spectrogram.
- `sections.json`: the timing input (default draft).
- `out/music.mid`: four tracks (piano, pad, pulse, tick) with section markers and the tempo.
- `out/stem_piano.wav`, `stem_pad.wav`, `stem_pulse.wav`, `stem_tick.wav`: 48 kHz / 24-bit stereo. The stems share the mix gain, so stems summed = `mix.wav`.
- `out/mix.wav`: the bed **without** the ding.
- `out/mix_with_ding.wav`: a preview only, with the ding placed at −4 dB.
- `out/ding.wav`: a separate 4 s soft chime with peak −12 dBFS. Its strike tone is **D6 (1174.7 Hz)**, the tonic of the resolve, and its partials are D5 / D6 / D7 / A7. Place its start at the ding time.
- `out/timing.json`: the actual snapped times, tempo and chord per bar. Use these as the edit points.

## Re-render with new timings
1. Edit `sections.json`: `hook/change/now/ddn/ask` = [start, end] in seconds, `ding` = seconds, `end` = seconds.
   - Optional keys: `bpm` (104), `bpm_flex` (3), `transpose` (semitones; also moves the ding), `target_lufs` (−22) and `seed`.
2. Run:
   ```
   cd /home/user/ddn-project/music
   /home/user/ddn-project/tools/venv/bin/python compose.py            # or: compose.py other.json --out other_dir
   /home/user/ddn-project/tools/venv/bin/python analyze.py            # checks + spectrogram
   ```
   A run takes about 25 s.
3. How the timing is fitted:
   - The tempo is chosen within 104 ± 3 BPM so that the ding is an exact downbeat. If that is impossible, the bar grid is shifted instead.
   - Section starts snap to the nearest bar line.
   - The ask always gets its 3-bar cadence, taking bars from earlier sections if needed.
   - Progressions are fitted to whatever bar counts result, and each section's turnaround always sits at its end.
4. Then read the real section and ding times from `out/timing.json`.
5. Requirement: the Salamander samples must be in `samples/SalamanderGrandPianoV3_48khz24bit/`. To restore them:
   - Download `SalamanderGrandPianoV3_48khz24bit.tar.bz2` from the archive.org item below. Its sha256 is in `samples/…tar.bz2.sha256`; the tarball itself was deleted after extraction to save 1.4 GB.
   - Extract it into `samples/`.

## Sound sources and licences

### 1. Salamander Grand Piano V3, 48 kHz / 24-bit (the only sampled instrument)
- Instrument: a **Yamaha C5** grand piano, recorded by the author with two AKG C414 microphones in AB, 16 velocity layers, sampled in minor thirds.
- Author: **Alexander Holm**. The Retuned SFZ mapping (`SalamanderGrandPianoV3Retuned.sfz`, used here) is by Markus Fiedler and ships in the same archive.
- Source: https://archive.org/details/SalamanderGrandPianoV3, file `SalamanderGrandPianoV3_48khz24bit.tar.bz2`.
- Licence: **Creative Commons Attribution 3.0 (CC BY 3.0)**, http://creativecommons.org/licenses/by/3.0/.
- Where I verified the licence:
  - The archive.org item metadata: `licenseurl` = CC BY 3.0, creator "Alexander Holm". A copy is saved in `samples/SalamanderGrandPianoV3_meta_archive.org.json`.
  - The bundled `README`: "Licence: CC-by http://creativecommons.org/licenses/by/3.0/ Author: Alexander Holm".
  - The SFZ header: "License: CC-by".
- What CC BY 3.0 allows and requires: commercial use and video sync are allowed. **Attribution is required.**
- Attribution text (put it in the video credits or description):
  > Piano: "Salamander Grand Piano" by Alexander Holm (Yamaha C5 samples), licensed under CC BY 3.0 – https://creativecommons.org/licenses/by/3.0/ – source: archive.org/details/SalamanderGrandPianoV3. Samples were processed (pitch-shifted, enveloped, EQ, reverb) and used in an original composition.
- How the samples were played back: through a small SFZ player written in `compose.py`.
  - It uses only the note samples.
  - Hammer-release and pedal-noise samples are not used.
  - It applies its own release envelope.
  - It trims about 13 ms of pre-roll so onsets land on the grid.

### 2. Synthesised, no samples (written in `compose.py`, original, no licence encumbrance)
- **Pad**: additive soft-saw voices, 3 per note with ±6 cents detune, slow drift, low-passed.
- **Pulse**: a sine plus gentle harmonics with a fast decay ("felt bass").
- **Clock tick**: band-passed noise click around 5–6 kHz.
- **Ding**: an additive bell with slightly inharmonic partials.
- **Reverb**: a synthetic, noise-based impulse response. No third-party IRs are used.

### Not used / caveats
- I did not find another Yamaha-sampled instrument whose licence was as clear as Salamander's, so the pad, pulse, tick and ding are **synthesised**, not Yamaha samples. I did not use any General MIDI / "Yamaha XG"-style soundfonts, because their provenance and licences are usually unclear.
- The same archive.org item also contains a file `YamahaDisklavierPro-GrandPiano.tar.bz2`. Its author and licence are not stated separately, so it was **not downloaded or used**.
- The bundled README is headed "Salamander Grand Piano V2" although the archive is V3. The licence is the same CC BY 3.0 in both, and the author's own changelog in it covers V3.
- CC BY 3.0 has no share-alike or non-commercial terms. The only obligation is attribution, including a link to the licence and a note that the samples were modified. The music composition itself is original to this project.

## Honest listening notes
"Listening" here was done by analysis: loudness, peaks, band energy, spectrogram, onset timing, and a scan for semitone clashes between overlapping notes. That scan found only the intentional maj7 / add9 colours. Nobody has listened by ear yet, so a quick ear-check on real speakers is still worthwhile. Things to check:
- **Low end.** The low end (D2 pedal in WHY DDN) is fairly full, at 44–49 % of energy below 250 Hz. If the VO sounds boomy, pull `stem_pulse` down 2–3 dB or high-pass the mix at 80 Hz.
- **WHY CHANGE entry.** WHY CHANGE comes in with a low B1 bass note at 9.2 s. It is deliberate, but it is the most noticeable entry in the piece.
- **Ducking.** The bed is delivered at −22 LUFS. Under VO, duck it a further 6–10 dB while speech is present.
