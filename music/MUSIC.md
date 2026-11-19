# Music + SFX for the DDN "Why DDN" pitch: **current = v5** in `out_v5/` (the v4 sound, re-fitted to the tightened edit)

## v5: re-timed to `edit/SHOTPLAN_v4.json` and `edit/voice_master_v3.wav` (74.2 s)
The sound and arrangement are v4's (curious, then confident; described below). Only the timing changed: `v2/edit_v5.json`.

**Licensing: no credits needed.** v5 contains **no attribution-required material**. Every sample in `music_mix.wav`, the stems and the SFX is CC0 (public domain).
- The Naked Drums kit (CC BY 4.0, which v3 and v4 used) has been **removed** (`"kit": "cc0"` in `edit_v5.json`). It is replaced by:
  - **Kick:** the Renoise "Acoustic Kit Two Handed" Yamaha Stage Custom muffled kick ("kick stop" 1–5). The author is crash_noise_division. The licence is "CC0, Public Domain", re-checked at https://files.renoise.com/forum/downloads/Instruments/Crash_noise_division-Acoustic_Kit_Two_Handed/LICENSE.txt. Its 32-bit FLACs were converted to 24-bit WAV.
  - **Ghost snare:** the same kit's Pearl snare, centre hits, layers 2–4. CC0.
  - **Toms:** VCSL "Tom 1" and "Tom 2" stick hits (Versilian Studios, CC0).
- Each replacement is level-matched to the piece it replaces: measured RMS at the velocities used is within ±1 dB. Timing is identical.
- The resolve stack was softened by 10 velocity steps so the mix reaches −20.0 LUFS at −3.4 dBTP.
- Exact sources used, per `out_v5/timing.json` (`samples_used` + `sfx_sources`): VCSL (44 files), FreePats RBX bass (7), Renoise kit (4) and BigSoundBank (1). All are CC0. A courtesy credit is optional, never required.
- After the kit swap, the measured results are:
  - **Mix:** −20.0 LUFS, true peak −3.4 dBTP, 74.2 s.
  - **Loudness by section (LUFS):**

| hook | change | now | DDN | ask | punchline drop | end card |
|---|---|---|---|---|---|---|
| −24.4 | −23.0 | −20.8 | −18.9 | −18.3 | −23.5 | −19.7 |

  - **Downbeats:** within ±4 ms.
  - **Preview:** the voice is a median 23.6 dB above the music.

**Section downbeats.** Hook 1.07, change 9.353, now 21.906, DDN 32.592, ask 58.71, punchline 67.643, end-card resolve 71.30.
- Bars per section: 4 / 6 / 5 / 12 / 4 / 1.5.
- The tempo map glides **116 → 96 BPM**. It runs faster than v4 because the edit is tighter; the hook bars are the fastest, the punchline the slowest.
- Measured onsets at every downbeat: −1 to +7 ms.

**Accents at exact cut and graphic times** (scheduled exactly; measured within ≤ 12 ms):

| Time (s) | Accent |
|---|---|
| 10.986 | TX81Z plucks enter |
| 13.15 | "12%": vibes C#–E |
| 16.553 | marimba pickup lands and the bass enters |
| 21.906 | shaker enters |
| 23.354 | vibes note |
| 26.252 | soft kick enters, cymbal swell peaks |
| 34.359 | vibes note |
| 39.46 → 41.154 | "5%": drop-out |
| 44.52 | snap zoom, "Arsenal lose": a wry two-note marimba fall |
| 45.52 | soft tom fill lands |
| 50.08 | "99%": vibes bloom |
| 53.18 | "75%": marimba fall |
| 54.488 | cymbal swell peaks |
| 60.143 | vibes note |
| 69.52 | snap zoom, "Blockbuster": one soft low knock inside the drop |

**Measured** (`out_v5/analysis.json`, `spectrogram.png`):
- `music_mix.wav` and `sfx_all_positioned.wav` are each exactly 74.2 s at 48 kHz.
- The mix is −20.9 LUFS with true peak −3.3 dBTP. The tail is at −76 dBFS by 74.2 s.
- Loudness by section (LUFS):

| chair | hook | change | now | DDN | ask | punchline drop | end card |
|---|---|---|---|---|---|---|---|
| −50 | −25.3 | −23.9 | −21.8 | −19.8 | −19.3 | −24.6 | −18.7 |

- Preview (voice at −16 LUFS): music is −37 LUFS under speech, the voice is a median 24.8 dB above it full-band and 40.8 dB above it in 1–4 kHz.

**SFX** (same recorded set as v4): click 1.07, swells 10.93 (chart) / 48.98 (gauge) / 64.84 (measure card), chime 71.40.
- The new voice master is denser than voice_v1, so the SFX were raised to stay audible on headphones.
- Peaks relative to dialogue peaks: click −23 dB, swells −21 / −19 / −22 dB, chime −27 dB.
- Audibility proxy (headphone / laptop):

| SFX | Headphone | Laptop |
|---|---|---|
| click | −5.9 | −14.5 |
| chart swell | −5.1 | −26 |
| gauge swell | −10.4 | −23 |
| measure-card swell | −2.7 | −20 |
| chime | +0.3 | −4 |

- The gauge swell is still partly masked by dense speech.
- Each file's `place_at` is in `out_v5/timing.json → sfx`.

**Re-render:**
```
cd /home/user/ddn-project/music/v2
/home/user/ddn-project/tools/venv/bin/python compose_v4.py edit_v5.json --out ../out_v5
/home/user/ddn-project/tools/venv/bin/python sfx_v4.py edit_v5.json --out ../out_v5
/home/user/ddn-project/tools/venv/bin/python analyze_v3.py ../out_v5 edit_v5.json
```

The v4 audio was deleted to save disk; it is reproducible with `edit_v4.json`.

---

# v4 (curious, soft): the sound v5 uses

v4 keeps v3's timing work and changes the character and the whooshes. Everything below §v4 describes v3 and is still valid for licences, research, the tempo map and the method. Earlier drafts are superseded: v1 `out/` (piano), v2 `out_v2/` (energetic), v3 `out_v3/` (soft groove). Their audio was deleted to free disk; the scripts re-render them.

## v4: what changed
**Character: curious, "what if…".** It starts as a question and resolves into confidence.

- **Hook and Why change: questions only.** No bass or drums until 18.07. Harmony uses only sus2/sus4, add9, m11 and **Gmaj7#11** chords (the lydian raised 4th, C# over G), with no plain triads.
  - Soft TX81Z FM-piano colours hold under a marimba figure that **rises and pauses** (B–C#–F#…, later B–C#–F#–G…).
  - A lone vibraphone E5 hangs unresolved.
  - Muted TX81Z Clavisynth "pizzicato" plucks enter exactly on the 12.30 cut.
  - At 18.07 a marimba pickup lands on the cut and the Yamaha RBX bass enters, gently.
- **Why now: gentle motion.** Syncopated plucks, half-note bass, and a very soft shaker entering on the 23.76 downbeat. A soft Yamaha kick "heartbeat" on beat 1 starts at the 28.56 cut, under the cymbal swell. The question figure is asked again, further.
- **Why DDN: the answer.** The harmony turns warm and plainly major (D, G/D, Em7…). The plucks become a steady 8th-note pulse, with soft kick (1, 3&) and a brush-soft ghost snare on 4. The motif's **answer** appears: it descends 6-5-3-2-1 and lands on D, doubled softly on vibes.
- **Ask:** a soft lift, asking once more but now over major harmony.
- **Unchanged from v3:** the punchline drop and the end-card resolve, the tempo map, the downbeats, and every camera-cut and graphic accent:
  - 12% (14.63) is now a lydian C#–E vibes "raised eyebrow".
  - 5% (42.43) is the drop-out.
  - 99% (53.67) is the bloom.
  - 75% (56.77) is the fall.

**Measured** (`out_v4/analysis.json`, `spectrogram.png`):
- `music_mix.wav` is −21.1 LUFS, true peak −3.3 dBTP, 80.0 s, with a clean tail (−74 dBFS over the last 50 ms).
- Loudness rises section by section (LUFS):

| chair | hook | change | now | DDN | ask | punchline 72.4–75.6 | end card |
|---|---|---|---|---|---|---|---|
| −47 | −25.3 | −24.2 | −22.2 | −20.1 | −19.8 | −26.0 | −19.0 |

- Section downbeats land within ±5 ms. The hook and change downbeats are carried by the keys (0 ms); there is no bass or kick there by design.
- Accents at cuts land within ≤ 6 ms.
- The 1–4 kHz share of the music is ≤ 1 % under speech.
- In the preview, the voice is a median 24 dB above the music full-band and 40 dB above it in 1–4 kHz.
- Note-clash scan: the only overlapping semitone/maj7 pairs left are intentional maj7 / lydian colours (G–F#, C#–D an octave apart).

**SFX v4: smooth and premium.**
- The coarse rope whooshes were removed. Each swell is now the rising part of a soft mallet-roll **cymbal swell** plus a **reversed soft-mallet vibraphone note** (A3 or E4, in key), all VCSL recordings (CC0).
  - Each is 0.55–0.7 s long, with a sin² rise (370–435 ms from 10 % to peak, never more than about 5 dB per 5 ms).
  - It stops before the roll's own peak, so there is no spike, then releases over 75 ms.
  - It is low-passed at 6 kHz.
  - Its peak lands on the graphic time.
- The chime is the same soft vibraphone D5 + hand chime, with a 25 ms rounded onset.
- The click is the BigSoundBank trackpad click, low-passed at 3.5 kHz.
- Peaks relative to dialogue peaks: click −25 dB, whoosh chart −24, whoosh gauge −21, whoosh ask −27, chime −27.
- Audibility proxy (best third-octave on headphones / laptop band):
  - click −3.4 / −13
  - chart −3.5 / −28
  - gauge −8.2 / −24
  - ask +2.4 / −13
  - chime +2.0 / −1.8 (plays after the voice ends)
- So all are subtle. The gauge swell (52.55) is still partly masked by dense speech and will be felt more than heard.
- Placement times are in `out_v4/timing.json → sfx` (`place_at`). `sfx_all_positioned.wav` has all five already placed over 80.0 s.

**v4 sample list** (all licences as in §5 below):
- Naked Drums (CC BY 4.0, credit required): Yamaha kick, toms, ghost snare.
- FreePats RBX finger bass (CC0).
- VCSL (CC0): TX81Z FM Piano and Clavisynth, marimba, vibraphone (soft and bowed), hand chimes, suspended cymbal swells and hit, shaker.
- BigSoundBank (CC0): trackpad click only. The rope whooshes are no longer used.
- The exact files are listed in `out_v4/timing.json` (`samples_used`, `sfx_sources`).

**Re-render v4:**
```
cd /home/user/ddn-project/music/v2
/home/user/ddn-project/tools/venv/bin/python compose_v4.py            # edit_v4.json -> ../out_v4
/home/user/ddn-project/tools/venv/bin/python sfx_v4.py
/home/user/ddn-project/tools/venv/bin/python analyze_v3.py ../out_v4 edit_v4.json
```

---

# (v3 documentation, still the reference for research, licences and method)

## 1. What pitch videos actually use (brief research, Nov 2026)

### Music under speech
- **Tempo.** Explainer and pitch guides cluster around mid-tempo, 85–115 BPM, instrumental and dynamically steady. Some guides suggest a tempo of roughly 60–80 % of the speaker's words per minute so the music supports the pacing rather than driving it.
  - Sources: [Foxi Music explainer guide](https://www.foximusic.com/blog/explainer-video-music-background/), [Artlist on BPM](https://artlist.io/blog/music-bpm/).
- **Arrangement.** Soft instrumentation, restrained melody and a clear midrange, with no dominant guitar or brass under the voice.
  - Practical test: if you can pick out the melody and individual instruments under the VO, the music is too loud.
  - Sources: [Audio Network](https://blog.audionetwork.com/the-edit/music/how-to-choose-music-for-a-voiceover-heavy-video/), [Foxi Music](https://www.foximusic.com/blog/explainer-video-music-background/).
- **Level.** Guides give 18–25 dB under the voice for explainers, rising to about −10 dB when nobody speaks. Our own research doc gives the same target: about 20 dB under the voice and +4–6 dB in gaps (`research/RESEARCH_ROUND2.md`, priority 3; WCAG 1.4.7 says ≥ 20 dB).
  - Sources: [Overseer](https://www.overseeros.com/blog/background-music-volume-under-voiceover), [WeVideo](https://wevideo.com/blog/how-to-set-audio-levels).

### SFX in product and pitch videos
- Use few of them, and keep them short and warm. The more often a sound occurs, the subtler, shorter and warmer it should be.
- Whooshes should be light and clean, not "transition = whoosh, text = pop" everywhere, which reads as amateur. Use a clean pitched accent only at the hero moment.
- Sources: [Toptal UX sounds guide](https://www.toptal.com/designers/ux/ux-sounds-guide), [open-design: SFX without overloading a product video](https://open-design.ai/blog/sound-design-product-videos/), [Ocular Sounds on whooshes](https://ocularsounds.com/blogs/sound-design-tips-tricks/whoosh-audio-effect-adding-motion-and-energy-to-your-edits).
- I found no published dB targets for Apple-style keynote SFX, so the level rule comes from our own research doc: about −26 dB under dialogue peaks, low-passed, at most 5 SFX.

**How this shaped v3:** about 100–112 BPM, soft muted mallets and plucks, a soft kick and shaker, warm finger bass and gentle TX81Z chords. Energy rises by adding layers, not by volume. SFX are only 5 recorded sounds, softened.

## 2. Concept and arrangement
The aim is a soft, warm, confident underscore with forward motion: a light groove rather than ambient mush. It is in D major and starts with a B-minor "question" colour.

**Motif.** One 4-note mallet motif (scale degrees 1-3-5-4, syncopated) develops through the piece:
- Hook: a minor-ish question.
- Why now: the answer (1-3-6-5).
- Why DDN: the motif in D major, doubled softly on vibes.
- Ask: it climbs a step per bar.
- End card: it resolves on D(add9).

**Harmony.** There is no four-chord loop. Each section has its own progression, using add9 / maj7 / 6-9 voicings and inversions. Bass approach notes are diatonic, and an analysis scan leaves only intentional maj7 colours.

| Section (final video, s) | What plays |
|---|---|
| chair 0–1.85 | One soft bowed-vibraphone swell (F#4 + D5) at −49 LUFS, gone before he speaks |
| hook 1.85–10.50 | Sparse: Yamaha RBX bass single notes; the marimba motif as a question; a soft Yamaha-tom pickup into 10.50 |
| why change 10.50–23.76 | Light groove enters on the downbeat: soft Yamaha kick (1, 3&), finger bass, TX81Z FM-piano chords. Shaker enters exactly at the 12.30 cut. Soft vibes double-note at "12%" (14.63). Tom fill lands on the 18.07 cut, where the marimba ostinato starts |
| why now 23.76–35.21 | Adds the TX81Z Clavisynth muted 8th-note pulse and a busier bass. Vibes note on the 25.46 cut, where the motif's answer starts. Soft cymbal swell peaks exactly on the 28.56 cut |
| why DDN 35.21–62.73 | Fullest, still soft: ghost backbeat (Naked Drums snare at its lowest layer, low-passed), syncopated kick, chords twice per bar. Motif in D major after the 37.18 cut. "5%" (42.43): everything except kick and bass drops out (the chips sit idle) and returns on the 44.18 cut. Tom fill into 48.75. Vibes note on 52.05. "99%" (53.67): vibes chord blooms with a soft cymbal. "75%" (56.77): a three-note marimba fall. Cymbal swell peaks on the 58.12 cut |
| ask 62.73–72.23 | Gentle lift: kick on all off-beats, the motif climbs a step per bar |
| punchline 72.23–77.00 | One soft hit on 72.23, then almost everything out (barely-there bowed Em air), at −27.7 LUFS vs −20.5 in Why DDN. A three-note pickup and a soft cymbal swell peak exactly at 77.00 |
| end card 77.00–80.00 | Clean D(add9) resolve on 77.00 (kick, bass, FM piano, marimba, vibes, soft cymbal). It rings, then a cos fade to digital silence at 80.0 |

**Tempo map.** A smooth (PCHIP) curve through the section downbeats gives exactly 4/6/5/12/4/2 bars per section.
- Tempo glides from 112 BPM down to 100 BPM with no jumps.
- Every section change (1.85, 10.50, 23.76, 35.21, 62.73, 72.23, 77.00) is an exact downbeat; the measured onset error is ≤ 4 ms, about 0.1 frame.
- Camera cuts between downbeats get accents placed at the exact cut time: a mallet note, a layer gate, or a swell peak. Measured error is ≤ 6 ms.
- The tempo map is embedded in `music.mid` as a tempo event on every 8th note, plus section markers.

## 3. Measured result (`out_v3/analysis.json`, `out_v3/spectrogram.png`)

**`music_mix.wav`**
- −20.9 LUFS, true peak −3.3 dBTP, no clipping; the last 50 ms is at −76 dBFS.
- Section loudness (LUFS): chair −49, hook −23.6, change −22.4, now −21.5, DDN −20.5, ask −18.9, punchline −24.5 (−27.7 over 72.4–75.6), end card −19.9.
- The 1–4 kHz share of the music is 0.1–0.4 % in every speech section.
- The low end is warm: 72–80 % of energy is below 250 Hz. If laptop playback sounds thin, that is expected; if it sounds boomy on big speakers, high-pass the bed at 60 Hz.

**`preview_with_voice.wav`**
- Voice is at −16 LUFS, peak-limited to −1.5 dBFS for the preview only. Raw `voice_v1.wav` has peaks up to +6.5 dBFS when normalised to −16 LUFS, so the final mix needs a dialogue limiter.
- Music sits at −16 dB from `music_mix.wav`, giving about −37 LUFS during speech (about 21 dB under the voice). It lifts +5 dB in gaps of 0.5 s or more, with 120 ms attack and 500 ms release.
- The music's 1–4 kHz band is dipped a further 4 dB while he talks.
- During speech the voice is a median 23.8 dB over the music full-band, and 42 dB over it in 1–4 kHz.

## 4. SFX (`out_v3/sfx_*.wav`)
There are 5 SFX, all **recorded** sources gently processed (trim, slow fade-in, low-pass, the music's small room). Nothing is synthesised.

How to place them:
- Each file starts at 0. `timing.json → sfx` gives `place_at`, which is the time to put the file's first sample.
- For whooshes, `place_at` is chosen so the swell's peak lands on the graphic time.
- `sfx_all_positioned.wav` is an 80 s stem with all five already placed.

Levels are given relative to the dialogue-peak reference: the 95th percentile of 50 ms peaks of the voice at −16 LUFS, which is +0.5 dBFS.

| File | Event | Source | Processing | Peak (rel. dialogue peak) | Headphone / laptop audibility* |
|---|---|---|---|---|---|
| sfx_click | timer start 1.85 | BigSoundBank "MacBook trackpad simple click" (s1740) | HP 300 Hz, LP 3.5 kHz, 80 ms fade | −27 dB | +0.1 dB / −15 dB |
| sfx_whoosh_chart | chart 12.39 | BSB "Whoosh #4" (s1796, rope, ORTF) + air from VCSL suspended-cymbal mallet-roll swell | 160 ms swell-in, LP 6 kHz | −24 dB | −3.9 / −29 dB |
| sfx_whoosh_gauge | gauge 52.55 | BSB "Whoosh #7" (s1800) + VCSL cymbal swell | same | −21 dB | −9.8 / −27 dB |
| sfx_whoosh_ask | ask card 69.10 | BSB "Whoosh #3" (s1795) + VCSL cymbal swell | same | −24 dB | −2.5 / −20 dB |
| sfx_chime | end card 77.2 | VCSL **soft-mallet vibraphone D5** + hand chime D5, tuned to the resolve | 12 ms rounded onset, LP 4 kHz, 1.4 s fade (3.1 s total) | −27 dB | +3.2 / −0.7 dB |

\*Audibility columns:
- **Headphone column:** the best one-third-octave band of SFX over voice + ducked music in the SFX window. Around −5 dB or higher is roughly detectable on headphones.
- **Laptop column:** the SFX over the rest within 350 Hz–9 kHz. Values well below −10 dB mean barely noticed on laptop speakers.

**Honest caveats**
- The whooshes sit under continuous speech. At the requested −26 dB they were fully masked: −15 to −25 dB in every band.
- So I raised them to −24 dB (chart, ask) and −21 dB (gauge). Even so, the gauge whoosh is still mostly masked, because the voice is dense there. It will be felt rather than heard.
- The click is at the edge of audibility because "Sorry" starts at 1.87.
- The chime plays after the voice ends, so it is clearly audible but soft.
- Nobody has listened by ear yet. Please do a quick headphone check.

**Not obtainable from this machine**
- Freesound and Pixabay return HTTP 403.
- Sonniss only answers with a redirect, and its bundles are multi-GB, too big for the disk.
- If preferred, the user can download these premium alternatives in a browser:
  - Sonniss GDC 2026 bundle (https://sonniss.com/gameaudiogdc). Pick a soft "air swish" and a "UI soft tick".
  - Freesound CC0 soft swishes.

## 5. Every sample used, with licence

| Library | Used for | Author / source | Licence (checked at source) | Attribution |
|---|---|---|---|---|
| **Naked Drums** (v3/v4 only; NOT used in v5) (kick, snare at lowest layers, 3 toms) | kick, ghost backbeat, tom fills | Wilkinson Audio; SFZ by kinwie. https://github.com/sfzinstruments/WilkinsonAudio.NakedDrums (commit 407732a5) | **CC BY 4.0** (repo LICENSE; https://sfzinstruments.github.io/drums/naked_drums) | **Required:** "Drums: 'Naked Drums' by Wilkinson Audio (SFZ by kinwie), CC BY 4.0, https://github.com/sfzinstruments/WilkinsonAudio.NakedDrums" |
| **FreePats Finger Bass YR** | bass | Andrea Biasior, FreePats. http://freepats.zenvoid.org/ElectricGuitar/clean-electric-bass.html | CC0 1.0 (README + LICENSE.txt) | none (courtesy credit optional) |
| **VCSL**: TX81Z FM Piano, TX81Z Clavisynth, marimba, vibraphone (soft, bowed), hand chimes, suspended cymbals 1 + 2, small shaker | chords, pluck pulse, motif, accents, swells, chime, whoosh "air" | Versilian Studios. https://github.com/sgossner/VCSL (commit c1ea7bcc) | CC0 1.0 ("no royalties, no credit, no special terms") | none |
| **BigSoundBank**: Whoosh #3 (s1795), #4 (s1796), #7 (s1800); MacBook trackpad simple click (s1740) | SFX | Joseph Sardin, https://bigsoundbank.com (each page reads "CC0 (public domain): Free and royalty-free") | CC0 1.0 | optional: "Additional sounds: Joseph SARDIN – BigSoundBank.com" |

The exact list of files used is in `out_v3/timing.json → samples_used` and `sfx_sources`.

**Yamaha instruments used**
- The Yamaha Recording Custom kick and toms (Naked Drums).
- The Yamaha RBX bass (FreePats).
- The Yamaha TX81Z: FM Piano and Clavisynth, sampled from the hardware.

The snare (Ayotte/Pearl), marimba, vibraphone and cymbals are not Yamaha; their makers are undocumented. I found no licensed Yamaha nylon guitar that could be downloaded: the Freesound Eterna pack returns 403.

The reverbs are synthetic impulse responses, which are processing, not instruments. No synthesised instruments or SFX are used.

## 6. Re-render
```
cd /home/user/ddn-project/music/v2
/home/user/ddn-project/tools/venv/bin/python compose_v3.py   # edit_v3.json -> ../out_v3 (MIDI, stems, music_mix)
/home/user/ddn-project/tools/venv/bin/python sfx_v3.py       # SFX files + sfx_all_positioned + sfx_timing.json
/home/user/ddn-project/tools/venv/bin/python analyze_v3.py   # preview_with_voice, analysis.json, spectrogram.png
```

What to edit in `edit_v3.json`:
- `sections`: the downbeats.
- `accents`: cut and graphic times.
- `sfx` times, `balance` and `sfx_level_below_dialogue_peak_db`.

Bars per section are fixed at 4/6/5/12/4/2. If a section's length changes by more than about 10 %, change `SEC_BARS` in `compose_v3.py` so the tempo stays within 96–112 BPM.

`sfx_v3.py` also writes the SFX placement into `timing.json`.

## 7. Files
`out_v3/` contains:
- `music.mid`
- `stem_{drums,shaker,bass,marimba,keys,vibes,fx}.wav`: 48 kHz/24-bit. They sum to `music_mix.wav`.
- `music_mix.wav`
- `sfx_*.wav` and `sfx_all_positioned.wav`
- `preview_with_voice.wav`
- `spectrogram.png`
- `timing.json`: section downbeats, every bar, accents and SFX placement.
- `analysis.json`

Disk housekeeping:
- Unused candidate samples (VCSL pianos, glock, triangles and so on; Renoise kit audio) were deleted. Their licence files are kept, and they can be re-fetched as described in `INSTRUMENT_OPTIONS.md`.
