# Instrument and SFX options: real Yamaha (and other recorded) samples with verified licences

Research date: 2026-11-18. The brief has changed: the music should be **energetic and driving but not crazy**, at 110–124 BPM, uplifting and confident, with no drops. The SFX should be smooth and premium.

Every licence below was read at its original source (the LICENSE file in the repo or archive, or the page itself). Test downloads are in `music/candidates/` and total about 0.63 GB. Downloaded files are untrusted data: there is no executable content, only audio plus SFZ/XML text.

## 1. Verified real-Yamaha instruments

| # | Instrument | Yamaha evidence | Library / author | Licence (verbatim key clause) | Format / size | Quality notes | Fit for an energetic pitch bed |
|---|---|---|---|---|---|---|---|
| Y1 | **Yamaha RBX electric bass**, picked + fingered | README: "Sound samples created by Andrea Biasior … from a Yamaha RBX bass guitar" | FreePats "Clean Electric Bass YR" — https://freepats.zenvoid.org/ElectricGuitar/clean-electric-bass.html (GitHub `freepats/electric-bass-YR`) | "Published under the terms of Creative Commons CC0 public domain dedication" (+ full CC0 1.0 LICENSE.txt in archive). No attribution needed. | SFZ+WAV 44.1k/24-bit mono. Pick 4.5 MB, Finger 5.1 MB. **Downloaded:** `candidates/freepats_yamaha_rbx_bass/` | Chromatic E1–D#2 (MIDI 28–39), stretched to A2 (45). One velocity layer, normalised, 2–6 s sustains, quiet tails (−45…−65 dB). Bass register only, so keep lines in E1–A2. | **Good.** Picked = driving 8ths; finger = warmer. Use velocity→filter/gain for dynamics. |
| Y2 | **Yamaha TX81Z FM synth module (1987 hardware)**, 3 patches: "FM Piano", "Piano 1", "Clavisynth" | VCSL `Electrophones/TX81Z/Origin.txt`: "These patches are user-created using the TX81Z Programmer application and **sampled from the original FM hardware** using Samplit." | VCSL (Versilian Community Sample Library), Versilian Studios — https://github.com/sgossner/VCSL | README: "This collection is under a Creative Commons 0 license. Essentially it's Public Domain- you can do whatever you want with these sounds (even make commercial software), no royalties, no credit, no special terms." (+ CC0 1.0 LICENSE) | WAV 44.1k/24 mono. FM Piano/Piano 1: 22 notes C0–G#6 (major thirds) × 3 vel layers. Clavisynth: 19 notes × 3 vel. 129 MB total. **Downloaded:** `candidates/VCSL/Electrophones/TX81Z/` | Noise floor about −70 dB. These are recordings of a real Yamaha unit, so they are not an emulation. The sound itself is FM synthesis, and VCSL's note says it "sounds best with super short release". | **Good for stabs/plucks.** FM Piano = DX-style EP stabs. Clavisynth = percussive pluck/arp that is not generic. Use it sparingly or it reads "80s preset". |
| Y3 | **Yamaha Recording Custom drum kit** (kick + 5 toms). The snares are an Ayotte and a Pearl, and the cymbals are Sabian/Zildjian. | README "Shells: Yamaha Recording Custom - Cherry … 22" Kick … 10/12/13/14/16" Toms" | "Naked Drums", Wilkinson Audio. SFZ conversion by kinwie — https://github.com/sfzinstruments/WilkinsonAudio.NakedDrums | Repo LICENSE = **CC BY 4.0** legal code. The catalogue page https://sfzinstruments.github.io/drums/naked_drums says "License: CC-BY-4.0". Attribution required. | SFZ v2 (ARIA #define/#include) + FLAC 44.1k. 10 round-robins, up to 5 velocities, many mics. Full set 1.3 GB. **Downloaded a subset (60 MB):** kick, snare centre, sidestick, hats closed/tight/pedal/open, ride bow (RR 1–4, direct+OH). | Pro-recorded (Neve/API pres) with a big, punchy rock kit tone. Use the direct (close) mics plus a little OH for a tight modern sound. A flattener for the macro format is included (below). | **Very good backbone.** Tight kick/snare at moderate velocity, 8th/16th hats. Toms for the ask fill. |
| Y4 | **Yamaha Stage Custom Standard kick** (the snare is Pearl Steel Shell and the hi-hat is Zildjian K Custom Hybrid) | description.html: "The kick is a Yamaha Stage Custom Standard, the snare is a Pearl Steel Shell, and the hihat is a Zildjian K Custom Hybrid." | "Acoustic Kit Two Handed", crash_noise_division (Renoise forum) — https://files.renoise.com/forum/downloads/Instruments/Crash_noise_division-Acoustic_Kit_Two_Handed/ | LICENSE.txt: "CC0, Public Domain" | Renoise .xrni (zip) → 55 FLAC samples, **32-bit FLAC** (libsndfile can't read it, so convert with `ffmpeg -i x.flac -c:a pcm_s24le x.wav`). Kick mono, others stereo, 44.1k. 37 MB. **Downloaded:** `candidates/renoise_acoustic_kit_two_handed/extracted/` | Kick "stop" (muffled) ×5 + "reso" (sustained) ×5. Snare centre/edge/rim and hats open/closed have L/R-hand × 4–5 velocities. Two Behringer B1M condensers, a roomier "real kit in a room" sound. | **Good, simpler alternative** to Naked Drums. The muffled Yamaha kick is a nice modern four-on-the-floor kick. CC0, so no credit needed. |
| Y5 | Yamaha Eterna classical (nylon) guitar, multisampled one-shots | Freesound pack 11573 description: "A 1-shot sample taken of a Yamaha Eterna classical acoustic guitar, recorded with a CAD E100 microphone." | quartertone, Freesound — https://freesound.org/people/quartertone/packs/11573/ | Sound 183089 shows "**Attribution 4.0**". Check each file's licence when downloading. | WAV 48k/24 mono, file names carry 5 velocity layers (`~v01…v05`). **Not downloaded:** Freesound blocks this sandbox (HTTP 403) and needs a free login. | I could not audit it. | Optional colour: muted nylon plucks for a light rhythmic figure. Not core. |
| Y6 | Yamaha upright piano | VCSL folder "Upright Piano, Yamaha" (Versilian's own labelling; same as VSCO 2 CE "Upright No. 1") | VCSL, CC0 as above | CC0 | 142 WAV. Not downloaded. | n/a | Piano was rejected, so listed for completeness only. |
| Y7 | Yamaha Disklavier Pro grand ("YDP Grand"); Salamander = Yamaha C5 | FreePats page: "Built from the Zenph Studios Yamaha Disklavier Pro Piano Multisamples for OLPC" | FreePats | "Creative Commons Attribution 3.0 license" | SF2 36 MB | n/a | Piano, so rejected. |

### Checked and NOT usable or not verified (do not use without further checks)
- **VCSL / VSCO 2 marimba, vibraphone, glockenspiel, xylophone:** no maker is documented anywhere (repo notes, the vcsl page). They are **not confirmed Yamaha**. They are still CC0 and good (see §3).
- **Univ. of Iowa MIS:** terms are "may be downloaded and used for any projects, without restrictions". The instruments are not Yamaha: trumpet = "Bach 180S37 Stradivarius (1987)", guitar = "Raimundo 118", and marimba/vibes/xylophone/bells/flute/sax/trombone all list "Model: NA".
- **FreePats "FM Synthesized Piano" / "Synth Bass 2" / "Synth Brass 2":** these are DX7 imitations "Recorded from Hexter software synthesizer" or from Dexed. That makes them **software synthesis, not Yamaha samples** (CC0, but they don't meet the "real Yamaha" goal). Dexed itself is synthesis too.
- **Yamaha DX-7 "Blaze"** (Yamaha Synthesizers Europe, 2015, 821 MB SFZ): there is no licence text and only a dead Facebook-app download.
- **Drumdrops "Yamaha Hybrid Kit"** (free with coupon, 1.7 GB): I found no licence text. **Pettinhouse Yamaha 9000 kit**: no licence found. **TheoK Yamaha Pacifica guitar**: no licence found, and it is distorted.
- **Pianobook "David's CP70"** (Yamaha CP-70): Kontakt-only, needs a login, and the terms are only in a FAQ ("should* be copyright free"). It can't be rendered here.
- I found **no** freely licensed Yamaha brass, woodwinds, vibraphone/marimba, celesta, CP-80 or acoustic/electric steel guitar multisamples that document the maker.

## 2. Other verified, licence-clean recorded instruments (non-Yamaha), all downloaded

All are from VCSL (CC0, wording as above), under `candidates/VCSL/`. Makers are undocumented.
- **Marimba** (`Idiophones/Struck Idiophones/Marimba`): 10 notes (F1, C2, G2, B2, F3, C4, G4, B4, F5, C6) × soft/med/loud, stereo 24-bit, 31 MB. The sampling is sparse, so pitch-shift no more than about ±3 semitones per sample.
- **Vibraphone** (`…/Vibraphone`): soft mallets, hard mallets (2 vel) and bowed. 11 notes, stereo 16-bit, 95 MB, ~15 s sustains.
- **Glockenspiel** (`…/Glockenspiel`): 7 notes × 3 dyn.
- **Hand chimes** (19 pitches), **Triangles** (hits + roll), **Bell tree**, **Mark trees** (asc/desc/slow/fast).
- **Suspended cymbal 1 & 2**: hits, bowed, and **mallet-roll crescendos of 1.5 s, 2 s and 4 s**. These are natural risers.
- **Shaker (small)** up/down strokes and rolls, **Claps** (group + solo), **Bass Drum 1** (concert bass drum).

## 3. SFX: verified sources (smooth, real recordings)

**Download note:** BigSoundBank and Freesound return HTTP 403 to this sandbox (bot protection), and I did not try to get around it. The user needs to download those few files in a browser (Freesound also needs a free login). The VCSL items are already on disk.

| Need | Pick (primary) | Licence (verbatim) | Spec | Backup / layer |
|---|---|---|---|---|
| **Timer start + tick** | BigSoundBank **"Chronograph #2"** (s2138) https://bigsoundbank.com/stopwatch-2-s2138.html: "Two beats per second of a stopwatch. Easy to loop." 2 beats/s = **120 BPM**, so it can lock to the groove. | "CC0 (public domain): Free and royalty-free" | 24/48 mono, 11 s, studio | **"Tic Tac Mechanical Alarm Clock #5"** (s2816, Neumann KM184, loopable, 29 s, CC0). **"Timer #2"** (s0082, small kitchen timer ticking, 7 s, CC0). **"Winder #4"** (s2665, alarm clock wound by key, 4 s, CC0) works as the "timer is set" gesture. Freesound **"Grandmother clock ticking"** by tryl (475356, 96k/24, NTG-4), **CC BY 4.0**. |
| **Ding** (sign flips to "AI: working") | BigSoundBank **"Counter Bell #3"** (s2531), "An all-metal counter bell … hotels or bars" | "CC0 (public domain): Free and royalty-free" | 24/48 mono, MixPre-3 + ME66 | Layer it with VCSL hand chime or glockenspiel on the tonic (CC0) for a pitched, musical ding. Counter Bell #1 (s0479) and #5 (s2533, double ring) are also CC0. |
| **Soft whoosh** (graphic entrances) | BigSoundBank **"Whoosh #4"** (s1796) / **#3** (s1795), "Whoosh made with a long rope" | "CC0 (public domain): Free and royalty-free" | 24/48 **stereo ORTF**, Rode NT5, 1–2 s | #6/#9 (wooden sheet, CC0). For the softest, most premium version, use a **reversed VCSL suspended-cymbal soft hit** or the shaker "Up" stroke, low-passed at about 6 kHz. Avoid the "sword" whooshes (#1, #2), which are too sharp. |
| **Subtle riser** | VCSL **susCymb1_cresc_2s / _4s**, susCymb2_cresc (mallet roll swell) | CC0 | stereo 24-bit | Mark trees slow ascend; triangle roll. Both are CC0. |
| **Gentle impact** | VCSL **Bass Drum 1** soft/mf hit + **susCymb hit_mp** | CC0 | | Naked Drums floor tom + kick (CC BY 4.0), or Yamaha Stage Custom "reso" kick (CC0), with a low-pass. |

Recommended BigSoundBank credit is optional: "Additional sounds: Joseph SARDIN - BigSoundBank.com". Their licence page (https://bigsoundbank.com/droit.html) says "Use, including for commercial purposes … Without any restrictions … Nothing is mandatory" and lists CC0 1.0. Sonniss GDC bundles are also royalty-free ("No attribution is required"; "licensed for media production … films, TV, YouTube … advertisements"), but they are 9–48 GB, which is too big for this disk.

## 4. What premium tech pitch / keynote underscores do instead of "corporate piano + pad"
- They rely on **rhythm before harmony**: a real or tight kit, claps/snaps on 2 and 4, and 8th/16th hats or shakers carry the energy.
- A **syncopated melodic ostinato** comes from a percussive instrument such as marimba, muted guitar, FM pluck or clav, rather than sustained chords.
- They use **driving picked-bass 8ths** under the ostinato.
- Harmony comes as short **stabs**, leaving gaps for speech, and sections build by **adding layers**, never by a drop.
- Transitions use **acoustic swells** (cymbal rolls, reversed cymbals), and arrivals land on a **clean stop + one pitched accent**.
- Clichés to avoid: the ukulele/glockenspiel/whistle "happy startup" sound, four-chord piano+pad, EDM drops, and big trailer hits.

## 5. Three concepts (all verified samples, 116–122 BPM, about 2.0 s per bar at 120)

Sections are hook (0–9), why change (9–27), why now (27–44), why DDN (44–70), ask (70–85), with the ding at 80.5. compose.py's tempo-flex can keep the ding on a downbeat.

### A. "Live Yamaha rhythm section + marimba hook" (recommended)
- **Instruments:** Naked Drums (Yamaha Recording Custom; close mics + some OH) · Yamaha RBX **picked** bass · VCSL marimba (med/loud) ostinato · VCSL vibes hard-mallet stabs · claps/shaker · Chronograph #2 tick · counter bell + glock ding.
- **Hook:** the chair alone in silence plus room tone. "Winder #4" sets the timer, then the Chronograph tick starts at 120 BPM, dry and close. On bar 4 a muffled kick doubles the tick on beat 1.
- **Why change:** the tick becomes the hi-hat grid (it hands over to closed hats). The kick plays on 1 and 3, and the bass plays roots in 8ths. The marimba gives a 1-bar syncopated figure in minor, mid-register (C3–C5).
- **Why now:** a 2 s cymbal crescendo leads in. The snare/claps on 2 and 4 enter, the marimba figure completes, and shaker 16ths join.
- **Why DDN:** the full, steady groove, with the bass moving to a confident major progression. Vibes stabs come on the off-beats, and the glock doubles the marimba every second phrase. Nothing new happens on the beat so the voice can sit on top.
- **Ask:** the bass climbs, a 4 s cymbal crescendo plays, and a 1-bar tom fill (Yamaha toms) builds. Then **everything stops on the downbeat**, and the counter bell plus a glock/hand-chime tonic ring as the sign flips. A soft final kick + bass note follow under "thank you".
- **Why it works:** real, organic and energetic without being "Claude generic". Everything heard is a real recording, and two of the instruments are documented Yamaha.

### B. "Yamaha FM keys + live kit" (more tech, slightly retro-modern)
- **Instruments:** TX81Z **Clavisynth** 8th/16th pluck arpeggio (short release) · TX81Z **FM Piano** off-beat chord stabs · RBX **finger** bass · Naked Drums (sidestick → snare) · cymbal-crescendo risers.
- **Hook:** the tick alone, then a single filtered Clavisynth note pulsing with it.
- **Why change:** the sidestick plus a sparse pluck arpeggio, with the bass on whole notes.
- **Why now:** the arpeggio thickens to 16ths, the kick goes four-on-the-floor, and the bass moves to 8ths.
- **Why DDN:** FM Piano stabs plus the full kit with the snare.
- **Ask:** a riser, a stop, then the ding with an FM Piano tonic chord ringing.
- **Character and risk:** the most "technology" flavoured, and nicely on-brand with Yamaha's 1980s FM heritage. It can tip into an "80s preset" feel if the stabs are long or loud.

### C. "Organic percussion drive" (lightest, most 'startup')
- **Instruments:** Yamaha Stage Custom **muffled kick** four-on-the-floor (CC0 kit) · VCSL shakers, claps, tambourine · marimba **low-register** ostinato doubled by the RBX bass · hand-chime/vibes chord swells (bowed vibes for sustain) · Pearl snare rim clicks.
- **Hook:** the tick plus a single shaker.
- **Why change:** kick on 1, low marimba plus bass ostinato.
- **Why now:** four-on-the-floor kick plus claps.
- **Why DDN:** full percussion plus vibes swells on chord changes.
- **Ask:** a triangle roll and cymbal crescendo, a stop, then the ding with a hand-chime chord.
- **Character:** bright, warm and human. It carries the least harmonic "weight", so it is less of a confident "enterprise" feel than A.

### Mix notes for all three
- Keep the ostinato fundamentals at 130–1000 Hz. Cut 2–4 kHz by 3–4 dB on mallets and hats, and duck the music 3–4 dB under the VO.
- Close-mic the drums and keep the overheads low so the room doesn't compete with the classroom audio.
- The ding should be the only bright event at 80.5 s.

## 6. Recommendation
Go with **Concept A** at about 120 BPM, using the BigSoundBank Chronograph #2 as the timer: its 2 beats/s *is* the tempo, so the gag turns into the groove. Use the counter bell + glock as the ding. Keep two TX81Z Clavisynth/FM Piano touches from B as accent colour in "why DDN" if more "tech" flavour is wanted. Use Renoise CC0 kit as a fallback if the Naked Drums CC BY credit is inconvenient. Caveat: its snare and hats are not Yamaha.

## 7. Attribution text (only CC BY items need it)
- Drums: "Naked Drums" by Wilkinson Audio (SFZ conversion via sfzinstruments), CC BY 4.0, https://github.com/sfzinstruments/WilkinsonAudio.NakedDrums
- If used: "Grandmother clock ticking" by tryl, https://freesound.org/s/475356/, CC BY 4.0
- If used: Yamaha Eterna guitar samples by quartertone, https://freesound.org/people/quartertone/packs/11573/, CC BY 4.0
- CC0 (optional courtesy credit): VCSL (Versilian Studios); FreePats Yamaha RBX bass (Andrea Biasior); BigSoundBank (Joseph Sardin); Acoustic Kit Two Handed (crash_noise_division).

## 8. Files on disk (`/home/user/ddn-project/music/candidates/`, about 630 MB)
- `VCSL/`: LICENSE (CC0), README.md, `SOURCE_COMMIT.txt`, TX81Z (3 patches), marimba, vibraphone, glock, hand chimes, triangles, bell tree, mark trees, suspended cymbals 1+2, shaker small, claps, bass drum 1, plus partial Gong 2 / Tubular Bells 3. The git store was removed to save disk. Re-fetch other folders with a blobless clone plus `git checkout HEAD -- "<folder>"`.
- `NakedDrums/`: LICENSE (CC BY 4.0), README.md, all SFZ/Data text, 260 core samples (`Samples/`), `SOURCE_COMMIT.txt`. Its SFZ uses #define/#include macros: `_tools/sfz_flatten.py "Stereo/Naked Drums OH.sfz"` resolves them to flat region JSON (key, velocity, round-robin, sample). Only kick (36), snare 1 (38), sidestick (37), hats (26/39/42/44/46/49) and ride bow (51), RR 1–4, are present locally.
- `freepats_yamaha_rbx_bass/`: Picked + Finger, SFZ + WAV + LICENSE + README.
- `renoise_acoustic_kit_two_handed/`: LICENSE.txt (CC0), description.html, `extracted/Instrument.xml` + `SampleData/*.flac` (32-bit FLAC, so convert with ffmpeg).
