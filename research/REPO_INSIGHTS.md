# Repo Insights: techniques to borrow for the DDN talking-head pipeline

Written 2026-11-18. I read the SKILL.md files, references and core scripts of the 9 cloned repos in `tools/repos/` and ran none of them. All paths below are relative to `/home/user/ddn-project/tools/repos/`.

Short names used below:
- **GE** = `kurbaitaev_ghost-editor`
- **VU** = `browser-use_video-use`
- **GW** = `griffinwooldridge_talking-head-editor`
- **YD** = `YildizDikme_claude-video-edit`
- **JS** = `jacobksamuelson_talking-head-video`
- **MA** = `malenaaza_video-editor-skill/plugins/video-editor/skills/video-editor`
- **HF** = `heygen-com_hyperframes`
- **RS** = `remotion-dev_skills/skills`

**Where the repos disagree with the DDN guide, the guide wins.** The repos were written for social reels. `DDN_STYLE_GUIDE.md` asks for about 90% hard cuts, no cross-dissolves, ease-out with no bounce, typewriter and rise-from-hairline builds, a warm grade and about −19 LUFS on talking heads. Each section below notes the conflicts.

---

## 1. Multi-take selection and script alignment

### 1.1 Transcribe each speech island separately (the biggest single win)
- **Problem.** Whisper run over a whole file merges a restart into one clean sentence, drops short false starts, and stretches words over pauses (seen: one word lasting 4–7 s). Three repos found this on their own: GE, YD and JS.
- **GE recipe** (`GE/references/take-selection.md`, `GE/scripts/vad_pauses.py`, `islands_tx.py`):
  1. Run silero-VAD with **`--min-pause 0.3` s**. The default 0.7 s keeps a quick restart in the same island as the line before it.
  2. Cut each island to its own wav with **0.1 s padding**.
  3. Transcribe all islands in **one** whisper call, so the model loads once.
  4. On raw camera audio, silero beat `silencedetect` clearly. At −38 dB, silencedetect returned 20–24 false islands (breaths, coughs), and whisper invented "To be continued..." on them. On noisy raw audio it returned **one** island for the whole file.
- **If an island still looks too long for its words** (or a word lasts more than 1 s):
  - print a 10 ms RMS envelope, using `#` above −30 dB, `+` above −40 and `.` below;
  - split at the 0.1–0.3 s dips and re-transcribe.
  - A restart shows up as a short first piece, for example "but from the constant, but from the constant".
- **For us.** `faster_whisper` is already in `tools/venv`, and it ships silero VAD (ONNX, so no torch). Its `vad_filter=True, vad_parameters={"min_silence_duration_ms":300}` gives the islands. Then transcribe each island on its own.
- **JS** (`JS/SKILL.md` §2) also runs a second, *filler-keeping* transcription pass, because Whisper normally drops "um"/"uh". It turns hesitations over **0.6 s** into a `remove` list.

### 1.2 Matching attempts to script lines (GE `scripts/takes.py`, verbatim parameters)
GE uses Smith-Waterman local alignment on normalised tokens, extracted repeatedly with masking, so it finds **every** attempt at a sentence, partial ones included.
- **Units:** script lines are split into sentences, and any sentence under 4 words merges forward (lists stay one unit).
- **Word similarity:**
  - exact match = 1.0;
  - same first 4 characters (both words ≥4 chars) = 0.8;
  - otherwise `difflib` ratio, used only if ≥0.72, else 0.
- **Scoring:**
  - a match adds `2*s`, a mismatch costs −1.0;
  - a script word that was **missing** from the speech costs −0.8;
  - an **extra** spoken word (stumble, repeat, filler) costs −0.6.
- **Accept an attempt** when `score ≥ max(3, 0.9·n)` and matched words ≥ `max(2, 0.3·n)`. It is **FULL** when coverage ≥0.9 and it contains both the first and the last word.
- **Per attempt it records:** coverage, extra and missing words, the largest internal gap, min word probability, and face flags (from 0.30 s before the first word to 0.30 s after the last). Those flags are judged against that take's own median pose (see 1.4).
- **Compared with ours:** `tools/analyze_takes.py` uses `rapidfuzz.fuzz.ratio` over whole utterances split at a 0.7 s gap. Smith-Waterman plus 0.3 s islands will catch partial takes and false starts that our version merges.

### 1.3 Choosing between takes (rules that recur across repos)
- **Meaning over wording** (GE). Pick the take that carries the script's meaning; the live wording is often better than the script.
- **Later over earlier, all else equal**, because people warm up (GE, GW, YD, JS). GW's rule is "keep the LAST complete take unless an earlier one is clearly better". YD adds that when retakes start the same way, keep the take that stays fluent to the end.
- **Prefer runs** (GE). When sentences 5–8 come out in one breath, keep the run as one segment. That gives one cut instead of four and keeps the delivery continuous.
- **Never splice half a take onto half another** mid-sentence unless the join sits on a natural pause (GW `references/cutting.md`). Splicing a one-liner from a different run is fine if the framing matches. A punch-in hides small differences; a lighting change it cannot hide (GE).
- **Lines the speaker never said never appear,** not as captions and not as cards. Report them in the handover (GE).
- **Look-aways** (GE rule 8, `scripts/facescan.py: badframes`). These flags are measured against the take's own median:

  | Flag | Condition |
  |---|---|
  | turn | yaw > 4° for ≥3 frames |
  | glance | lookDown > +0.18 (not a blink) for ≥2 frames |
  | side | eyes sideways > 0.15 while the head holds still |
  | closed | eyes shut ≥7 frames |
  | tilt | roll > 5° |
  | big | pitch > 9° |

  - A window counts as a **keep** if it is ≤0.5 s and the head stays within 12° (that is ordinary talking).
  - Anything longer is a **cover**: fix it with the cheapest option first. Trim it, then punch in, then hold a graphic, then a framed insert; full-screen stock comes last.
  - A lesson from one audit: hiding all 31 flagged windows put the speaker on screen only 33% of the time, and 29 of those windows were 0.03–0.4 s blips. Don't over-cover.
- **VU's counterpoint** (`VU/SKILL.md`, anti-patterns): "hand-tuned moment-scoring functions: the LLM picks better than any heuristic you'll write". VU hands the editor sub-agent a phrase-level packed transcript (`[start-end] text`, breaking on silences ≥0.5 s) plus a brief. Our best design is both: compute the metrics (alignment, disfluency, energy, face flags) and let the LLM make the final pick from a table.
- **Energy and delivery scoring.** No cloned repo scores prosody; our `analyze_takes.py` (energy, pitch std, wpm) is already ahead. Fagan1024/smart-video-editor (section 6) adds a vision usability score per frame.

### 1.4 Word-boundary cutting, padding and handles

| Source | Lead (before 1st word) | Tail (after last word) | Pause handling | Notes |
|---|---|---|---|---|
| VU `SKILL.md` Hard Rule 7 | 50 ms | 80 ms | prefer silences ≥400 ms; 150–400 usable with a visual check; <150 ms unsafe | allowed range 30–200 ms (absorbs 50–100 ms timestamp drift) |
| GE `take-selection.md` §5 | 100–150 ms | 200–300 ms | pauses over ~1 s → cut plus punch; under 0.5 s → keep (rhythm) | never past the next spoken word |
| GE `scripts/plan_cut.py` | 100 ms (min 30) | 180 ms (min 60) | internal silence >0.26 s → ~0.18 s (tail 0.11 + lead 0.07) | energy threshold = 8th-percentile floor + 14 dB; never mid-blink (slide edge 1–6 frames, or a picture-only split ≤4 frames) |
| GE raw refine (smeared takes) | onset − 70 ms | offset + 120 ms | — | onset/offset where RMS > −37 dB (−30 dB clips soft first words); end within ~0.1 s of the last word, because eyes close right after |
| GW `scripts/cut.py` | 30 ms | 60 ms | gaps >0.15 s collapse to ~0.09 s | tight preset; see the tail walker below |
| YD `reference/audio.md` natural | 100 ms | 160 ms | max kept pause 0.35 s | default |
| YD tight | 40 ms | 60 ms | max kept pause 0.15 s | Shorts |
| JS `scripts/assemble.py` | 120 ms (`PAD_IN`) | 220 ms (`PAD_OUT`) | pauses >0.7 s become cuts; keep ~0.3 s breath | — |
| MA `SKILL.md` Rule 3 | silence end − 100 ms (30 ms clipped onsets in testing) | silence start + 50 ms | "quiet" = 22 dB under the voice's own peaks; natural pace keeps 0.3 s | — |

**Recommendation for DDN** (calm, corporate, about 3.5 s average shot):
- lead **100 ms**, tail **180 ms**;
- shrink internal pauses over **0.35 s** to about **0.25 s**;
- never cut a gap under 0.2 s between words that run together (YD);
- round frames **outward** (GW, YD).

**Refining cut points from audio, not from Whisper times** (Whisper word ends are often 0.1–0.4 s early):
- **GW tail walker** (`GW/scripts/cut.py: tail()`):
  - quiet threshold Q = noise floor (8th percentile of 10 ms levels) + 12 dB, clamped to −56…−40 dB;
  - walk forward until 30 ms sits below Q;
  - then look **250 ms** further for a "dip then resume" (≥30 ms above Q+4). That catches clipped "-ence/-ts/-s" endings;
  - onset: walk back up to **150 ms** over breathy h-/f-/s-/th- onsets.
- **YD release bursts** (`YD/reference/audio.md` §2):
  - words ending in t/k/p have a silent closure and then a **10–120 ms** burst. Keep the burst if silence follows it; without this rule "basic" becomes "basi";
  - extend the word end while the level stays above a soft floor of about −61 dB, by up to 0.10 s;
  - pull the start back up to 0.06 s.
- **JS caution:** an f/s is quiet in broadband but loud **above 2.5 kHz**. Run the energy check on a high-passed copy as well.
- **GE frame sync:**
  - iPhones run at 29.97–29.99 fps, so frame/30 drifts up to 0.16 s over 12 min. Use the source's real PTS (`ffprobe` packet times);
  - snap every piece to the frame grid and cut audio at the **same** snapped times, otherwise the voice drifts 43–54 ms early by the end of a 23-piece cut (GE `SKILL.md` gotchas);
  - start each piece on the frame **nearest** its cut time.

### 1.5 Audio at the joins
- **Equal-power crossfade, 35 ms, using real handles** (GE `scripts/voice_smooth.py`):
  - each piece is extended by 17.5 ms on both sides from the source and given a sine-ramp fade over the handles, centred on the edit point;
  - the total length stays exactly Σ(b−a), so nothing moves in time;
  - joins between raw-contiguous pieces get no fade.
- **Per-take level match:** the 70th percentile of 10 ms speech levels above −40 dB, moved to the median of all takes and **clamped ±3 dB**. It is one constant gain per take.
- **Room-tone bed:** the quietest 1.5 s inside the chosen takes (peak <0.06, flat RMS), looped with 200 ms crossfades at ×0.7 under the whole voice. Gaps never drop to digital zero. YD agrees: "room tone, not digital silence".
- **Simpler alternatives:**
  - VU Hard Rule 3: `afade=t=in:st=0:d=0.03,afade=t=out:st={dur-0.03}:d=0.03` on every segment;
  - HF `skills/media-use/scripts/lib/transcriptCutFade.mjs`: 30 ms, shrunk to dur/4 on short segments, and no fade at the film's true start or end;
  - YD `scripts/build.py`: 4 ms in / 15 ms out, and 50 ms when a hand-set end sits inside running speech;
  - JS: `afade=t=in:d=0.015` … `afade=t=out:d=0.03`.
- **Gap in ours:** `tools/conform.py` uses 8 ms fades. Raise that to 30 ms, or better, use GE's 35 ms equal-power crossfade with handles.

### 1.6 Catching hidden restarts and clipped words (self-check)
- **GE `scripts/subcheck.py`:**
  - split each planned piece at internal silences **≥0.15 s** (floor + 14 dB) and transcribe each part on its own;
  - flag **REPEAT** when two parts open with the same two words, and **REPEATS PREVIOUS PIECE**;
  - flag words longer than **0.7 s**;
  - in one batch it found 8 hidden false starts.
- **YD `scripts/verify.py`:** re-transcribes a **1.6 s window** around every join. It flags doubled words (`and and`), repeated 2–3-grams, and energy still high at a cut point.
- **JS `scripts/review.py`** (a hard gate: 0 ❌ before any draft):
  - word integrity at each cut, kept-words vs heard-words diff (❌);
  - choppy: 3+ camera cuts within 8 s (❌);
  - no breath: under 0.15 s of air across a cut;
  - edge voice: speech-level sound in the first or last 40 ms of a piece;
  - dead air over 1.4 s;
  - mid-sentence content cuts;
  - opening with "Hi, I'm…" (a story note).
- **GW final review:** re-transcribe `final.mp4` and diff it against the keep list, so no word is missing or doubled.

---

## 2. Cut quality and pacing

### 2.1 Hiding jump cuts
DDN emulates two cameras: 100% ↔ 140% scale with a 4K source, per guide §6.
- **JS `assemble.py`:**
  - each new segment alternates framing on the pattern `[1.0, 1.18]` (wide ↔ medium), with **1.3–1.45** for the one or two lines that carry the argument;
  - consecutive phrases of one take stay one segment unless the pause is >0.7 s;
  - fillers **inside** a shot are **muted, not cut** (a run of jump cuts reads as choppy);
  - keep **≥4 s between camera cuts**;
  - the zoom is clamped to the sharp limit for the source resolution, so 4K→1080 allows up to 2×.
- **GE:**
  - "Snap zooms, not crossfades, between takes of the same sentence";
  - `"tight": 1.3` gives a raw cut that reads as a second camera, while 1.6 reads as a punch-in;
  - the user calibrated that per-cut zooms annoy viewers, so use **at most 3 comic punch-ins per reel**;
  - otherwise hide a jump with a shot-size change or a short **0.2 s dissolve**. For DDN, use the shot-size change only.
- **GW `render_cut.py`:**
  - base framing at **110%** with the face centred and the eyes about 40% down; punch-in at **130%**; reframing done in one lanczos pass from the camera original;
  - when the head position jumps between two neighbouring pieces, put a punch-in or an MG run over the join.
- **MA `SKILL.md` Rule 10** (headroom check):
  - estimated top of head = forehead landmark (10) − 0.45 × face height;
  - after the crop it must sit ≥60 px below the frame top, and the chin must stay above the caption area;
  - if a shot fails, keep it at 1.00. If most shots fail, use no zooms in that video.
- **YD `reference/style.md` §7:** "Cut-synced punch-ins at 30 fps without motion blur read as jolts; ≈1 per minute at most." A **hard** cut between two scale levels is fine (it reads as a camera change); an *animated* zoom on the cut is what jolts.

### 2.2 Slow push-in at a key line
MA `scripts/pushin.py`:
- `--zoom 1.15` over `--duration 1.5` s, eased in and out, then hold, then ease back over `--back 0.4` s (or cut back on a new sentence);
- one or two per video at most;
- drawn at **sub-pixel** precision, because ffmpeg `zoompan` shook by about 3 px on slow zooms.

In Remotion, do this with a `scale` interpolate on the `<OffthreadVideo>` wrapper, not with zoompan.

### 2.3 J/L cuts (split edits)
- **GE `plan_cut.py` `vearly`:** the picture cuts N frames before the sound, and the next piece's picture starts that much earlier. GE also uses a picture-only split of ≤4 frames to dodge a mid-blink edge.
- **VU:** "Never reason audio and video independently; every cut must work on both tracks."
- **For DDN:** use 2–4 frame J-cuts (audio leads) on take changes, and run the blink check on picture edges.

### 2.4 Pacing numbers
- **JS `reference/style.md`:**
  - something changes every **4–8 s** (a cut, an overlay, a zoom), but never stack changes;
  - give the face **1–2 s** of clean time between overlays;
  - keep ~0.3 s of breath at each cut;
  - give a screen ↔ camera switch about 0.5 s of air;
  - remove whole sentences, never clauses ending on a comma.
- **GE calibration** from 6 top reels: 113 of 119 transitions were hard cuts; median shot about 3 s; 0.4–0.9 audible SFX per 10 s, on graphics and not on cuts; B-roll 20–35% of runtime. That matches DDN's ≈3.5 s and ~90% hard cuts.
- **VU:** speaker handoffs get 400–600 ms of air; extend past punchlines and reactions.

### 2.5 Self-checking cuts visually
- **GE `scripts/qa_cut.py`:**
  - face flags on every output frame;
  - pauses >0.30 s inside speech;
  - silence at every join;
  - a **cut sheet**: the 3 frames before and after every cut, cropped to the face.
- **VU `helpers/timeline_view.py`:**
  - render a filmstrip plus waveform PNG **±1.5 s around every cut of the rendered output**;
  - check each one for a flash, a waveform spike (pop), hidden subtitles and misaligned overlays;
  - also check the first 2 s, the last 2 s and 2–3 midpoints;
  - **cap at 3 self-eval passes**, then flag the rest to the user.
- **VU critic sub-agent:** for anything published, give a fresh agent the render, the EDL and the references, and brief it to *roast, not praise*. It returns a verdict, ranked problems with timecodes and evidence, and the 5 fixes to do first.
- **YD:** "blank stares" are silent but visible. Find them with a frame-difference measure, not audio.

---

## 3. Motion-design quality

### 3.1 Easing and timing doctrine (DDN-compatible values)
- **Never linear** except typewriter and camera drift (VU, YD, JS, GE).
- **DDN tokens:** `ddn-out` = `cubic-bezier(0.16,1,0.3,1)` (also the RS `timing.md` example), `ddn-inout` = `(0.65,0,0.35,1)`, `ddn-ui` = `(0.4,0,0.2,1)`.
- **Remotion:**
  - `interpolate(frame,[0,0.3*fps],[0,1],{easing:Easing.bezier(0.16,1,0.3,1),extrapolateLeft:'clamp',extrapolateRight:'clamp'})`;
  - spring with no bounce: `Easing.spring({damping:200})`;
  - RS `timing.md`: linear scale *looks* slower as it grows, so ease scale with the bezier.
- **HF `.claude/skills/motion-doctrine/SKILL.md`** "timing intents":
  - a single entry runs ≤ about 800 ms; a longer build should be a stagger, not one slow element;
  - **exit ≈ 75% of entry**; total stagger ≤500 ms;
  - `bounce`/`elastic` eases are banned (and DDN bans overshoot entirely);
  - similar elements share one ease and duration.
- **Entrance length by video type** (YD `reference/style.md` §7):
  - talk: **0.5–0.8 s**, long holds, a keyword card that swaps on its word, a lower third once;
  - educational: 0.6–0.9 s;
  - Short: 0.25–0.45 s.
- **Springs** (GW `references/techniques.md`): use closed-form step responses summed per retarget (seek-safe), with **overshoot <2%** (bounce ≤0.1). Shots enter already moving and leave accelerating; nothing fades out slowly.
- **Word-locking:**
  - an element lands **on the word or up to 0.15 s early, never late** (GW);
  - or it appears about **0.1 s before onset** and leaves only after its sentence ends (YD);
  - VU: start the overlay `reveal_duration` early so the *landing* frame is the payoff word.
- **Stillness before climax:** a **0.3–0.75 s** pause between an action and its result (HF motion-doctrine).
- **Readability:**
  - each state stays readable ≥1 s (GW);
  - hold the final frame ≥1 s (VU);
  - over VO, the graphic lasts at least narration + 1 s (VU);
  - sync-to-narration cards: floor 3 s, typically 5–7 s (VU).
- **Never reveal two independent elements in parallel** (VU). One thing, a pause, then the next.
- **No idle wobble** (HF motion-doctrine): no breathe, float, drift or glow-pulse loops. If a scene finishes entering with seconds left, that is a planning bug. GW and YD say the same: no ambient drift, and hold still between beats.

### 3.2 Typography animation
- **Waterfall entry** (HF `.claude/skills/cut-the-curve/SKILL.md` §6), for title cards and segment openers:
  - **binary** opacity via `set` (no fade);
  - from below, ease `power4.out` ≈ `cubic-bezier(0.165,0.84,0.44,1)`;
  - each element starts within ±2 frames of the previous one settling, and the gaps shrink.

  | Element | Y offset | Duration | Overlap |
  |---|---|---|---|
  | anchor | 60–80 px | 0.16–0.20 s | 0–2 frame gap |
  | normal word | 40–50 px | 0.13–0.16 s | 1 frame |
  | punctuation | 30–48 px | 0.10–0.13 s | 1–2 frames |

  This fits DDN's "rise from under a hairline" card (guide §4.5): mask the text below the hairline.
- **Nudge curve** (cut-the-curve §7), for sliding a composed group to make room. Three chained tweens:

  | Phase | Ease | Share of distance | Share of time |
  |---|---|---|---|
  | 1 | `power3.in` | 10% | 20% |
  | 2 | linear | 65% | 18% |
  | 3 | `power4.out` | 25% | 62% |

  The tail takes ≥3× the ramp's time; reveal new content during phase 2.
- **Typing text** (VU): anchor on the **full** string width, or the text slides left as it grows. A typewriter should be human-paced (YD). DDN's typewriter is stepped, one character per N frames.
- **Sizes at 1080p** (YD §4): content ≥32 px, card titles ≥44 px, labels ≥20 px, nothing under 18 px; weights 600–800; no thin weights, no low-opacity content text. Double all of these at 2160p.
- **Fonts fail silently** (VU): in Remotion, `await` the font (`@remotion/fonts` `loadFont` / `delayRender`) and assert `document.fonts.check('700 76px "<Font>"')`, or throw.
- **Remotion gotchas** (GW, techniques.md): `will-change` on scaled elements blurs text; `opacity`/`filter` on a `preserve-3d` element flattens it; measure text only after fonts load; outgoing titles leave before incoming ones take the same space.

### 3.3 Seams and transitions
DDN uses hard cuts about 90% of the time. Below are the few transitions DDN does use and how to build them well.
- **Rack-focus blur-cut** (cut-the-curve §5), for a same-surface state swap:
  - the outgoing side stays fully opaque;
  - hard swap at **peak blur 8–12 px** (max 16–18);
  - ~1.06 scale ("lens breathing"), eases `power2.in`/`power2.out`;
  - at most once per ~8 s;
  - blur the wrapper, never a `<video>` directly, and never blur and opacity in one tween on one element.
- **Zoom-through** (§1), for a text→text swap:

  | Phase | Scale | Blur | Opacity | Ease | Time |
  |---|---|---|---|---|---|
  | exit | 1→1.2 | 0→10 px | 1→0.15 (separate linear tween) | `power3.in` | 0.2 s |
  | swap | — | — | — | — | hard |
  | entry | 0.75→1 | 10→0 px | 0.15→1 | `expo.out` | 0.5 s |

  - Text-scale subjects take **10 px** blur; full-frame surfaces take 18–20 px.
  - **Z-sign rule:** a push exit must be met by a push entry (both scales growing); never a receding exit into a grow-from-small entry.
- **Cut-the-curve** (§3), for a graphic→graphic boundary:
  - partial travel **±230 px at 1920** (~12% of the frame), so ±460 px at 4K;
  - exit `power4.in` and entry `power4.out` with the same distance and duration;
  - exit opacity is gone at 25–30% of the travel, and the entry ignites at 0.35 opacity;
  - total about 0.6 s, always in one direction (the "current").
- **Vector law** (motion-doctrine): keep the same axis, direction and speed across a cut, and cut mid-motion on both sides. Never ping-pong between opposite directions on consecutive seams.
- **Opaque stage** (HF `.claude/skills/seam-craft/SKILL.md`): any overlap window where the summed opacity drops below 1 flashes white unless the root has a background. In Remotion, give the composition root `backgroundColor`.
- **YD transition table** (`reference/style.md` §9):
  - blur dip on a cut where the picture jumps: blur in ~0.18 s, clear in ~0.32 s;
  - dark blur dip for a subject change: about 80% darkening in 0.3 s, back in 0.55 s;
  - chapter veil ~1.5 s, and the cut happens **under** the closed pane;
  - **no blur on plain cuts;**
  - start a veil only after the last word has decayed, on **0.3–0.6 s** of the clip's own room tone.
- **Transition budget:** 2–3 types per film, repeated (HF). DDN's own list is hard cut, vertical slice, light-leak flash and whip.

### 3.4 Captions
- **Rail / embed / drop model** (HF `.claude/skills/captions-overlay/SKILL.md`):
  - fillers are **dropped**;
  - verbatim text rides a lower **rail** that sits on top as an overlay, with no reserved band, and the composition centres on the true H/2;
  - an **embed** (one big word composited behind the subject with a matte) is rare: ≤1 per beat, never two adjacent.
- **Chunking:**
  - JS: 2–4 words in a solid box for social;
  - VU: about 2-word chunks, breaking on punctuation and pauses ≥0.3 s, and growing to 3 words rather than flashing a cue **<0.35 s**;
  - natural style: 4–7 words.
  - DDN's 2026 style is sentence captions on frosted glass (guide §4.4).
- **Timing:**
  - master SRT times use the output timeline: `word.start − segment_start + segment_offset` (VU Hard Rule 5);
  - captions are applied **last**, after every overlay (Rule 1);
  - build captions from the **final** program audio, transcribed in chunks padded with silence, not with neighbouring audio (YD §6);
  - fix only misheard names, with a `--fix` map (GW `captions.py`). Never rewrite.
- **Remotion:** use `@remotion/captions` (`createTikTokStyleCaptions`, `combineTokensWithinMilliseconds`); see RS `remotion-captions/display-captions.md`.

### 3.5 Critique loop with contact sheets and frame checks
- **GW** (`references/motion.md`, `references/techniques.md`):
  1. Write a **one-sentence concept** per run ("a transformation or a mechanism, not a layout"), a beat map and a banned list (`references/brief.md`).
  2. Snapshot each run **at its beat times**.
  3. Critique the snapshots against the checklist:
     - every element exists for a reason;
     - each beat lands on or just before its word;
     - nothing spills out of the frame;
     - no empty half-frame for more than ~1.5 s;
     - brand names use the official casing;
     - exits are fast;
     - a motif or callback ties the runs together.
  4. Render.
  5. Decode frames from the **actual MP4**, not browser screenshots.
- **GW `scripts/qa.py`** (port this; it is about 60 lines of numpy). It works on frames scaled to 320×180 grayscale:
  - **pop:** a frame's mean absolute difference is >2.0 and >3× the median of its neighbours (window ±4, excluding ±1). `--expect` whitelists intended hard changes;
  - **frozen:** ≥0.75 s with diff <0.01;
  - **tile artefact:** NCC between quadrants >0.2;
  - **loop seam:** last vs first frame diff <0.5.
- **YD `scripts/audit.mjs`** checks layout at 0.5 s steps:
  - mark the face with `data-keepout` and each card with `data-box`;
  - fail on overlaps, text over the face, or anything inside the **64 px** safe margin;
  - always check `t=0`, because it is the poster frame.
- **JS:** `hf snapshot --at <overlay midpoints>`, then read the contact sheet and the full-size frames. In Remotion the equivalent is `npx remotion still <comp> --frame=N` at each beat, tiled with ffmpeg `tile=`.
- **HF Seam Gate** (`.claude/skills/motion-doctrine/scripts/seam-gate.mjs`, a numeric check of a ledger of seams): exit still moving at the cut, entry already mid-flight, measured direction equals the ledger direction, zero overlap, Z-sign match. The *idea* ports to Remotion: sample each layer's bounding box at cut ±2 frames and assert continuity.
- **Remotion motion blur** (RS `remotion-markup/motion-blur.md`): `<HtmlInCanvasMotionBlur samples={8} shutterAngle={180}>`. GW renders at **4× sub-frames** (8× for whip moves) and averages them. Both multiply CPU render time, so use them only on fast moves.

### 3.6 Brand restyling (GW `references/look.md`)
- Take the look from the brand's **current** site, not memory: `scripts/extract_brand.js` returns type, radii histogram, colour counts and `@font-face` URLs. This was already done for DDN.
- Use the real logo SVG, never a redrawn one.
- Pick **one brand-native motif object** to carry through the runs. For DDN that is the ring arc or the red swoosh.
- Check by placing a snapshot next to a site screenshot; both should read as the same brand.

**Avoid** (YD §10):
- radial gradients, glows and big soft shadows, which band after compression (DDN's 2–3% grain helps);
- cream or white cards over dark video;
- full-frame colour washes over the speaker.

---

## 4. Audio finishing

### 4.1 Voice-cleanup chains (verbatim)
- **GE `scripts/voice_smooth.py`**, applied after the 35 ms join crossfades and the room tone. The loudnorm runs as two passes with `linear=true`:
  ```
  highpass=f=70,deesser=i=0.35:m=0.5:f=0.5:s=o,acompressor=threshold=-22dB:ratio=2:attack=12:release=160:knee=6:makeup=1,agate=threshold=0.006:ratio=1.8:range=0.4:attack=8:release=300:knee=4,equalizer=f=180:t=q:w=1.2:g=2,equalizer=f=3200:t=q:w=1.5:g=0.8,loudnorm=I=-16:TP=-1.5:LRA=9
  ```
- **JS `scripts/assemble.py` `VOICE_CHAINS`:**
  ```
  light:  highpass=f=75,afftdn=nr=6:nf=-50:tn=1,equalizer=f=250:t=q:w=1.2:g=-1.5,equalizer=f=3800:t=q:w=1.2:g=1.5,acompressor=threshold=-22dB:ratio=2.2:attack=8:release=140:makeup=1.5
  medium: highpass=f=80,afftdn=nr=12:nf=-45:tn=1,equalizer=f=250:t=q:w=1.2:g=-2,equalizer=f=3800:t=q:w=1.2:g=2,deesser=i=0.3,acompressor=threshold=-22dB:ratio=3:attack=6:release=120:makeup=2
  ```
- **MA `scripts/voice/clean_voice.py`.** The order is pre → denoise → post, and it compresses *before* denoising so leftover noise is not raised afterwards.
  - Pre:
    ```
    highpass=f=80:poles=2,[bandreject=f={50|60}*k:width_type=q:w=30 for k=1,2,3],acompressor=threshold=-24dB:ratio={2 light|3 strong}:attack=10:release=150:makeup=2
    ```
  - Denoise, using the first engine available:
    1. `deep-filter -a {12 light|6 gentle}`, the standalone Rust binary, which needs no torch;
    2. `arnndn=m=cb.rnnn:mix={0.7 light|1.0 strong|0.4 gentle}`, the RNNoise "conjoined-burgers" model;
    3. `afftdn=nr={12|24|6}:nf={measured floor, clamped -80..-20}`.
  - **Safety:** if the voice level drops more than 3 dB, the engine ate voice; retry more gently, then fall back.
  - Post:
    ```
    deesser=i={0.3|0.5}:m=0.5:f=0.5,equalizer=f=3000:width_type=o:w=1.5:g={1.5|2.5},alimiter=limit=0.95:level=false
    ```
  - **Measure first,** on the uncut original that still has its pauses. Speech-to-noise gap ≥45 dB: no cleaning. Under 30 dB: strong.
  - **Check:** re-transcribe the cleaned voice. If any word changed, clean one step lighter.
- **GW `scripts/voice.py`:**
  1. DeepFilterNet3 with **`atten_lim_db=24`**; 40+ sounds robotic. Use 18 if it sounds processed.
  2. Zero-phase **match-EQ** toward the LTASS speech curve (Byrne 1994):
     - at 50% strength, boosts capped at +2.5 dB, cuts at −6 dB, and nothing above +0.5 dB from 4 kHz up;
     - `firequalizer=zero_phase=on:gain_entry='entry(f,g);…'`, using these target points re 1 kHz: `{100:-1,125:1,160:3,200:4.5,250:5,315:5,400:5,500:4,630:3,800:1.5,1000:0,1250:-1.5,1600:-3,2000:-4.5,2500:-6.5,3150:-7.5,4000:-8.5,5000:-9.5,6300:-10,8000:-11.5,10000:-13.5,12500:-16.5,16000:-21}`.
  3. `acompressor=threshold=-22dB:ratio=1.8:attack=12:release=160`.
  4. **One static gain** to the target, then `alimiter=limit=0.89:attack=5:release=60:level=disabled:latency=1`. No dynamic loudnorm, because it "lifts every pause by 40–60 dB and floods gaps with room noise".
  5. Measure filter latency by cross-correlation and trim it to **0 samples**, with an assert. firequalizer adds about 10 ms.
- **GE `scripts/denoise.sh`:** DeepFilterNet3 capped at **20 dB**, because full strength sounds "thin, watery". Add a little low-mid warmth later (+2 dB @ 180 Hz).
- **GE `scripts/voice_enhance.py`:** ClearerVoice MossFormer2_SE_48K/SR_48K (Apache-2.0). Warning: its SR merge throws away the real 5–16 kHz on full-band iPhone audio (measured −6 dB at 10–16 kHz). Skip SR when the input is already full band (≥15 kHz).
- **YD dissent** (`reference/audio.md` §1): "The voice is sacred". By default it applies only one linear gain, and processing happens only on request, with an A/B file. Adaptive denoise and low-pass filters cause the "boxed/underwater/lisping" voice. That makes YD a good **guard rail**: always render an unprocessed A/B, because we cannot listen.

**Recommended DDN chain** (the iPhone 12 built-in mic, indoors):
1. Measure the noise gap (MA).
2. Clean with `deep-filter -a 12`, or `arnndn mix=0.7` if the binary is not available.
3. `highpass=f=80`, a hum notch only if measured, and `acompressor=threshold=-22dB:ratio=2:attack=12:release=160:knee=6`.
4. `deesser=i=0.3:m=0.5:f=0.5`, then `equalizer=f=180:t=q:w=1.2:g=1.5` and `equalizer=f=3200:t=q:w=1.5:g=1`.
5. Apply the static gain plus `alimiter` (GW / our `master_audio.sh`).
6. Re-transcribe to make sure no word was lost.

Our `tools/master_audio.sh` already does steps 3 and 5 (measured gain plus limiter plus 3 correction passes), which is the right design (GW and MA arrived at the same).

### 4.2 Loudness targets

| Use | Target | Source |
|---|---|---|
| DDN "In Conversation" talking heads (measured) | **−18.8 to −19.2 LUFS** | DDN guide §3 |
| DDN sizzle / event wrap | −13.2 to −13.5 LUFS | DDN guide §3 |
| Social / YouTube master | −14 LUFS, TP ≤ −1 dBTP, LRA 11 | VU `render.py`, MA, YD, GE finals |
| Voice stem before SFX/music | −16 LUFS, TP −1.5 | GE `prep.sh`, JS |

Rules:
- **Normalise the voice first, then place SFX relative to it, and never lift the finished mix** (GE `references/sound-and-memes.md`). The older pipeline lifted the finished mix by +10 dB and every SFX hit the limiter.
- Measure on the stereo file. `-ac 1` sums the channels and reports peaks about 3 dB too high; use `pan=mono|c0=c0` instead (YD §3).
- For ddn.com and internal use, deliver the master at −19 LUFS to match house. Deliver a −14 LUFS variant for social.

### 4.3 SFX and music: sourcing, levels and ducking
- **SFX levels relative to the voice:**
  - GE `build.mjs`: measure the p95 of 50 ms windows over kept words, then set each role against it: UI −14 dB, whoosh −12, impact −8;
  - YD absolute peak starting points: −30 to −32 dBFS for ticks and whooshes, raised to −28 or lowered to −34 after the user listens;
  - MA amix volumes 0.36–0.54 under the voice (0.20–0.30 was too quiet).
- **Density:**
  - GE: 6–12 subtle sounds per minute on graphics, none on cuts ("Hormozi-style edits leave cuts dry");
  - VU: ~8 effects in 18 s reads as designed, ~20 reads as generic;
  - YD: no transition sounds by default;
  - each effect is tied to a visible event, with round-robin variants so repeats don't machine-gun (GE).
- **Hit on the frame** (VU): measure the file's attack (the first sample within about −30 dB of its peak) and start the file that much **before** the contact frame. A whoosh starts about 0.15 s early so it peaks on the cut (MA).
- **Typing sounds:** one key sound per revealed character group, with jitter in pitch, level and timing; never a generic loop (YD §5).
- **Music bed:**
  - GE `scripts/lib/motion.mjs`:
    - level = voice −20 dB, so −36 LUFS under a −16 voice;
    - fade in 0.6 s, out 1.2 s;
    - duck windows at **−8 dB**, ramping down over **0.25 s before** speech and back up over **0.4 s after**.
  - VU: duck −12 to −15 dB relative to the music-only level, and ramp out *before* a stinger or end card.
  - YD: the bed sits ≥18–22 dB under the voice while someone speaks.
  - JS: about 0.08–0.12 linear (≈10 dB under), carried through the end slate.
  - HF `media-use/references/mixing.md`: duck to 0.3–0.4, then **carve** (dip only the voice bands in the bed). In ffmpeg, that is `sidechaincompress` or a 2–4 kHz `equalizer` dip on the bed during speech.
- **Sourcing:**
  - GE `library/sfx` is CC0 (28 files); its music beds are **Mixkit Free licence** (commercial OK, no attribution, per `library/music/manifest.json`);
  - HF and JS bundle a few `.wav` files;
  - our `tools/sfx_gen.py` (procedural) plus YD `scripts/sfx.py` (filtered-noise whoosh, decaying-sine ticks, modal-partial chimes) carry no licence risk;
  - **avoid GE's meme sounds** (rips, not cleared for YouTube Content ID).

---

## 5. Colour: iPhone HDR/HLG, and grading to the DDN look

### 5.1 HLG → SDR Rec.709
- **iPhone 12 records Dolby Vision 8.4 / HLG BT.2020 by default.** JS `ingest.py --check` warns "HDR is ON — turn it off (Settings › Camera › Record Video › HDR Video)". For future shoots, **record with HDR off**: it is the cheapest fix.
- **Detection** (GE `scripts/prep.sh`, JS): `ffprobe -show_entries stream=color_transfer`. Treat `arib-std-b67` (HLG) or `smpte2084` (PQ) as HDR.
- **GE `scripts/grade_lib.py: hdr_to_sdr`** has no zscale, so it bakes the tone map into a `.cube`:
  - HLG inverse OETF with `a=0.17883277, b=0.28466892, c=0.55991073`;
  - OOTF for a **1000-nit** display (system gamma 1.2);
  - scale by **203 nits = SDR reference white**;
  - BT.2020→709 matrix;
  - a soft shoulder on luminance above **0.8** (`Yt = k + (1−k)(1−exp(−(Y−k)/(1−k)))`);
  - gamma 1/2.4.
  - Apply as: `scale=in_color_matrix=bt2020,format=rgb48le,lut3d=file=sdr.cube:interp=tetrahedral,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv`.
  - The `setparams` step matters, because the frame tags otherwise override `-color_trc` and an HLG tag survives.
- **Our ffmpeg has `zscale` and `tonemap`.** The chain in our `conform.py` (`npl=203`, `tonemap=hable:desat=0`) is the standard one. Hable tends to crush and darken skin, so A/B it against GE's soft-shoulder LUT and `tonemap=mobius:param=0.3` before locking. Also **add the `setparams=…bt709` tail** (GE's lesson).
- **Keyframes for random access** (GE): encode intermediates at `-g 30 -keyint_min 30`.
- **Determinism** (GE): libx264 at a fixed thread count produces identical bytes on every run. **One HDR asset switches a HyperFrames render to HDR**, so tone-map every insert as well (GE `broll_qa.py`, `insert_prep.py`).
- **HF media-use:** its realtime grade path is SDR/Rec.709 only and *rejects* PQ/HLG instead of guessing.

### 5.2 Grading to a brand look
- **Grade conflict.** GE `house_look.py` says the speaker's face is NEVER regraded; only the inserts are conformed to it. DDN's guide (§6) explicitly asks for a warm grade, so we grade the A-roll, then **conform B-roll to the graded plate** with GE's method:
  - stats in CIE Lab on a small frame:
    - median L* (exposure);
    - std L* (contrast);
    - mean chroma;
    - **white balance = median a\*/b\* over the 40% least-chromatic pixels with 8<L\*<97**. That separated real casts from blue-sea content where mean b* failed;
  - transform: `L' = 100(L/100)^g`, contrast ×k around the median, a*/b* white point shifted and chroma scaled, baked into a `.cube`;
  - tolerances: |ΔL*| ≤15 (fail) and 7 (target); |Δwb b*| ≤8 (fail) and 2.5 (target); chroma ratio 0.8–1.2 (warn) and 0.5–2.0 (hard);
  - no-neutral shots get at most 8 b* of WB move;
  - house tolerance: |dL*| 8, wb b* 5, wb a* 4, sat and contrast ×0.85–1.15.
  - Sources: `GE/scripts/grade_lib.py`, `house_look.py`, `insert_prep.py`, `broll_qa.py`.
- **White balance, measured** (MA `scripts/balance.py`):
  - find the white and grey regions, report the cast (for example "cool cast 4.9%"), and print a `colorchannelmixer` that keeps brightness;
  - under 1.5% needs no correction;
  - **offer half strength first** when saturation is boosted, because full correction plus saturation pushed skin orange.
- **VU `helpers/grade.py`:**
  - ASC CDL mental model: slope = highlights, offset = shadows, power = mids;
  - an auto mode capped at **±8%** per axis;
  - presets (verbatim):
    ```
    neutral_punch:  eq=contrast=1.06:brightness=0.0:saturation=1.0,curves=master='0/0 0.25/0.23 0.75/0.77 1/1'
    warm_cinematic: eq=contrast=1.12:brightness=-0.02:saturation=0.88,colorbalance=rs=0.02:gs=0.0:bs=-0.03:rm=0.04:gm=0.01:bm=-0.02:rh=0.08:gh=0.02:bh=-0.05,curves=master='0/0 0.25/0.22 0.75/0.78 1/1'
    ```
  - apply the grade **per segment during extraction**, not after concat (that would encode twice); never go aggressive without checking skin tones.
- **DDN target** (guide §6), for ffmpeg after the tone map:
  - skin at 65–70 IRE;
  - contrast −10;
  - blacks lifted to about `#1E1E22`;
  - highlights −15;
  - +300 K warm, with the cream wall at `#F0DFCB`;
  - saturation −10% (skin +5);
  - 2–3% grain.
  - A starting chain: `eq=contrast=0.94:saturation=0.9,curves=master='0/0.08 0.5/0.52 0.9/0.86 1/0.93',colorbalance=rm=0.03:bm=-0.03:rh=0.02:bh=-0.03,noise=alls=3:allf=t`. Then verify with GE-style Lab stats against frames sampled from the DDN reference videos (median L*, wb b*), **not by eye**.
- **Remotion:** `colorCorrection({exposure,temperature,tint,shadows,highlights,contrast,saturation,vibrance})` from `@remotion/effects/color-correction` runs as one WebGL pass, and Remotion also accepts `.cube` LUTs (RS `remotion-markup/color-correction.md`). On a 4-CPU machine with no GPU, WebGL runs in software through SwiftShader and is slow at 4K. **Bake the grade into the A-roll mezzanine with ffmpeg** and keep Remotion for graphics only.

---

## 6. Repos in the awesome list worth a look
Checked against `zhuyansen_awesome-claude-video-skills/data/skills.json` (526 repos). Star counts and licences are from that file. I have **not** read these repos.

| Repo | ★ / licence | Why it may beat what we have |
|---|---|---|
| https://github.com/echris6/motion-video-kit | 1.4k / MIT | "Independent critic loop, motion principles from 28 launch films, quality bar, **sound design**" for **business** videos, the closest match to a corporate brand piece. Mine its critic brief and quality bar. |
| https://github.com/iart-ai/motion-design-skills | 243 / MIT | Motion-design fundamentals as skills: timing, typography, colour, composition, plus Remotion. A doctrine source that is not tied to HyperFrames. |
| https://github.com/kmilo93sd/agent-video-editor | 8 / MIT | "Editing judgment: pacing, cuts, captions, audio, **color**", with **128 CC0 sounds** and a rights reference. Useful CC0 SFX library and grading notes. |
| https://github.com/Fagan1024/smart-video-editor | 10 / MIT | A vision model **scores every frame's usability** and drops bad takes. That fills our missing visual take-quality score. |
| https://github.com/YeJe-cpu/SeeCut | 468 / no licence asserted | "An AI editor that watches its own cut", a self-review loop for talking heads. Read only; no licence. |
| https://github.com/MakeMyClip/editor | 17 / MIT | Removes silence and **repeated takes** with local whisper.cpp, and exports FCP/DaVinci XML. Useful if DDN wants an NLE handoff (an editable timeline). |
| https://github.com/Vibha-Ramprakash/claude-video-effects | 1.1k / no licence asserted | 51 talking-head effects with face tracking and "behind your head" layers. Reference for the GE "embed" captions. No licence, so read only. |
| https://github.com/feitangyuan/onetake | 4.2k / no licence asserted | A continuity "oracle" that measures seams, the same idea as HF's Seam Gate. Read only. |
| https://github.com/lemomo-ai/lemo-opuscar | 18.2k / no licence asserted (GE vendors parts of it as MIT) | 99 coded film styles. GE's `recipes/*` (swiss-grid, news-package, data-story) come from it and are useful layout references for stat callouts. |
| https://github.com/RajaskaJanuardani/motion-craft | 16 / MIT | Remotion "After Effects-grade" motion with **48 kHz procedural audio** and spline camera. Remotion-native, so easy to port. |
| https://github.com/YKLovePython/halfsize | 110 / MIT | HDR→SDR tone mapping plus **VMAF/SSIM** proof of quality. Useful for checking the quality of our delivery encodes. |
| https://github.com/charlie947/motion-graphics-skills | 711 / MIT | 13 launch-grade MG skills; benchmarked in the list's end-to-end test (4/4). |

**Avoid for commercial DDN work** (AGPL-3.0): OpenMontageInc/OpenMontage (81k★), pireel/pireel, op7418/guizang-product-video-skill, geekjourneyx/hyperframes-motion-director, 0xsline/OpenChatCut, GTKottman/mortiflix-oss, and 5 others in the list. Running them as separate tools may be fine, but don't copy their code into our scripts. 70 entries carry no asserted licence (NOASSERTION), and **an unlicensed repo grants no rights**: read only.

---

## Should we use HyperFrames alongside Remotion?

**No. Borrow its doctrine and don't run it.**

Reasons:
1. **Remotion already covers every DDN element:** typewriter lower third, hairline-rise chapter card, counters, frosted captions, vertical-slice transition, light leak, logo sting. HyperFrames brings no capability that Remotion lacks.
2. **Cost on our box:**
   - it needs Node ≥22 and headless Chrome, a second render stack to keep in sync (fonts, easing tokens, colour tags);
   - in the awesome-list test it was the slowest of 16 (23.5 min for a 15 s brief, though that was agent time);
   - on 4 CPUs, two Chromium renderers compete.
3. **Telemetry and upsell:**
   - the CLI sends PostHog telemetry to `us.i.posthog.com` **on by default** (`packages/cli/src/telemetry/`). Opt out with `HYPERFRAMES_NO_TELEMETRY=1` or `DO_NOT_TRACK=1`;
   - once signed in, telemetry is linked to a HeyGen account;
   - every skill tells the agent to run a `npx hyperframes events --skill=…` "usage beacon" and to send `feedback --rating` after renders. **Do not run either** (JS also says not to send `hf feedback/publish/cloud`);
   - `reverse-any-video` and `style-sampling` are paid **Pro** cloud features, and `media-use` routes to HeyGen credits.
4. **Licence:** Apache-2.0, which is fine commercially if we ever need it.

**What to borrow:**
- **Cut-the-curve parameters:** zoom-through, rack-focus, waterfall entry, nudge curve (section 3.3).
- **Motion doctrine:** vector law, no idle wobble, stillness before climax, exit ≈75% of entry, 2–3 transition types.
- **Captions overlay model:** rail / embed / drop.
- **Seam-craft opaque-stage rule.**
- **Registry blocks** as *visual references* to port to Remotion components: 210 blocks plus about 200 components in `HF/registry/`, for example `lt-*` lower thirds, `count-up`, `mk-progress-stat`, `data-chart`, `light-leak`, `rack-focus`, `transitions-push`, `typewriter`, `svg-line-draw-loader`.
- **The Seam-Gate idea:** a numeric check of seams, rebuilt as a small Remotion bounding-box sampler.

**The one case for HyperFrames:** a client-supplied HTML/GSAP asset, or porting a specific registry block verbatim. Even then, render it with `HYPERFRAMES_NO_TELEMETRY=1` to a ProRes 4444 or WebM-alpha overlay and composite it.

**Remotion licence check (important):** Remotion's licence is free only for individuals and companies of **≤3 employees**. A larger organisation, which DDN or an agency working for it likely is, needs a paid **Company License**. Confirm at https://www.remotion.dev/docs/license (RS `remotion-license/SKILL.md` points there) before delivering commercial work.

**Licence and telemetry of the cloned repos:**

| Repo | Licence | Telemetry and data leaving the machine |
|---|---|---|
| GE | MIT; vendors MIT code from lemo-opuscar and talking-head-reel | `gem_audit.py` uploads video to **Gemini**, `tts_elevenlabs.py` uses ElevenLabs; music is Mixkit (commercial OK), SFX are CC0, memes are not cleared |
| VU | MIT | sends audio to **ElevenLabs Scribe** for ASR |
| GW, YD, JS | MIT | local only; JS's `hf` wrapper turns HF telemetry off |
| MA | MIT | weekly GitHub version check (opt-in) and a manual issue-report link (`report.py`) |
| RS | from remotion-dev/remotion; no LICENSE file in the clone | the Remotion licence applies |
| awesome list | CC0 | — |

Keep client footage local: use our faster-whisper instead of Scribe or Gemini.

---

## Recommended additions to our pipeline (ranked)

1. **Island transcription and Smith-Waterman take matcher.**
   - Use faster-whisper's silero VAD (`min_silence_duration_ms=300`), transcribe each island on its own, and add a filler-keeping pass.
   - Replace the `fuzz.ratio` matching in `analyze_takes.py` with GE `takes.py`'s SW alignment (+2s / −1 / −0.8 missing / −0.6 extra; accept at ≥max(3, 0.9n); FULL at cov ≥0.9 with first and last word).
   - Keep our energy and pitch metrics, add face flags, and let the LLM pick from the table with GE's rules: later over earlier, prefer runs, meaning over wording.
2. **Audio-refined cut points.**
   - Use GW's tail walker (floor + 12 dB, 30 ms quiet, 250 ms resume look-ahead), the 150 ms onset walk-back, and YD's t/k/p burst rule.
   - Check f/s energy above 2.5 kHz.
   - Pad 100 ms / 180 ms, shrink pauses >0.35 s to about 0.25 s, round frames outward, and use real PTS (iPhone 29.97 fps drift).
3. **Join audio:** 35 ms equal-power crossfades with real handles, per-take ±3 dB level match, and a looped room-tone bed (GE `voice_smooth.py`). This replaces the 8 ms fades in `conform.py`.
4. **A cut-QA gate before any draft goes out:**
   - hidden-restart re-transcription (GE `subcheck.py`);
   - ±0.8 s join re-transcription with doubled n-gram detection (YD `verify.py`);
   - JS `review.py` checks: edge voice in the first/last 40 ms, <0.15 s breath, >1.4 s dead air, 3+ cuts in 8 s;
   - a cut-sheet JPEG of 3 frames on each side of every cut;
   - a final whole-video re-transcribe diffed against the script.
5. **Voice chain with a safety check:**
   - measure the noise gap, then deep-filter (`-a 12`, or 20 dB max in GE) or arnndn `mix=0.7`;
   - `highpass 80`, compressor −22 dB 2:1, `deesser i=0.3`, +1.5 dB @180 Hz, +1 dB @3.2 kHz;
   - static gain plus limiter (we have this);
   - assert zero latency (GW cross-correlation);
   - re-transcribe and roll back one step if any word changes;
   - always keep an unprocessed A/B.
6. **HLG tone-map hardening:**
   - add the `setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv` tail;
   - A/B `hable` against `mobius` and GE's 203-nit soft-shoulder LUT on skin;
   - tag every intermediate BT.709, encode with `-g 30`;
   - tone-map B-roll and inserts too.
7. **Measured grade and B-roll conform:** apply the DDN warm grade by ffmpeg into the mezzanine, verify it against Lab stats from the DDN reference frames, then conform each B-roll clip to the graded plate (GE `grade_lib`: least-chromatic-40% white balance, ΔL* ≤7, Δb* ≤2.5, chroma 0.9–1.1).
8. **A motion QA loop in Remotion:**
   - per graphic, write a one-sentence concept, a beat map and a banned list;
   - render `remotion still` contact sheets at the beat times and critique them against GW's checklist;
   - port GW `qa.py` (pops, frozen frames, tiles) to run on every render;
   - add a YD-style keep-out/overlap audit (the face box from mediapipe, 64 px safe margin at 1080 / 128 px at 4K);
   - assert fonts have loaded.
9. **Remotion motion-token library from the doctrine:**
   - waterfall entry, nudge curve, rack-focus (8–12 px peak), zoom-through (10 px text blur);
   - exit ≈75% of entry; entries 0.5–0.8 s; words land 0–0.15 s *before* their spoken word;
   - 0.3–0.75 s stillness before a payoff; no idle loops;
   - use only DDN easings (`ddn-out` / `ddn-inout` / `ddn-ui`), with no overshoot.
10. **Framing plan:**
    - hard-cut alternation 1.0 ↔ 1.4 (DDN) on sentence ends, with ≥4 s between camera cuts;
    - mute mid-shot fillers instead of cutting them;
    - MA's headroom check (forehead − 0.45 × face height, ≥60 px margin);
    - at most 1–2 slow push-ins (1.15× over 1.5 s), done sub-pixel in Remotion, not with zoompan;
    - 2–4 frame J-cuts at take changes, with blink-safe picture edges.
11. **Sound design:**
    - SFX relative to the measured voice peak (UI −14 dB, whoosh −12, impact −8), only on graphics events, 6–12 per minute at most, with the attack offset so they hit on the frame;
    - music bed at voice −20 dB, ducked −8 dB (0.25 s down, 0.4 s up) or −12 to −15 dB, faded out before the end card;
    - deliver the talking-head master at −19 LUFS (DDN house) and a −14 LUFS social variant.
12. **Critic sub-agent pass** on the final render (VU): a fresh agent with the render, the EDL and the DDN reference frames, told to roast it. It returns a ranked list with timecodes. Cap the loop at 3 passes.

## Repos worth cloning next (read-only, same rules)
1. **echris6/motion-video-kit** (MIT): critic loop, a quality bar from 28 launch films, sound design for business video.
2. **Fagan1024/smart-video-editor** (MIT): per-frame vision usability scoring for take selection.
3. **kmilo93sd/agent-video-editor** (MIT): grading and pacing judgment plus 128 CC0 sounds.
4. **iart-ai/motion-design-skills** (MIT): timing, typography and composition fundamentals with Remotion.
5. **RajaskaJanuardani/motion-craft** (MIT): Remotion-native AE-style motion and 48 kHz procedural audio.
6. **YKLovePython/halfsize** (MIT): HDR→SDR plus VMAF/SSIM delivery checks.
7. *(Read only, no licence)* **YeJe-cpu/SeeCut** (self-watching cut review) and **feitangyuan/onetake** (continuity oracle), for ideas only.
