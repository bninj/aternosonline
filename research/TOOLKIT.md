# DDN talking-head + motion-graphics toolkit (code-driven, CPU-only)

Researched, installed and smoke-tested 2026-11-18 in this container (4 vCPU, 15 GB RAM, no GPU, Ubuntu 24.04,
ffmpeg 6.1.1 with zscale/tonemap, Node 22, Python 3.13). Rebuild everything with `bash /home/user/ddn-project/tools/setup.sh [--smoke]`.

## 1. Chosen stack (TL;DR)

| Job | Primary | Fallback / also installed |
|---|---|---|
| Motion graphics + final composite | **Remotion 4.0.545** (React; `@remotion/media`, `transitions`, `captions`, `fonts`, `shapes`, `paths`, `noise`, `light-leaks`, `motion-blur`, `layout-utils`) + official **remotion-best-practices** agent skill | **HyperFrames 0.9.67** (HeyGen, HTML+GSAP, Apache-2.0) + its skills (already in `ddn-project/.claude/skills/hf-*`) |
| Transcription (word timestamps) | **faster-whisper 1.2.1, `large-v3-turbo`, int8, CPU** | `small.en` (same speed here, misheard "Data" -> "Vater"; don't bother) |
| Script alignment / take picking | `tools/transcribe.py` (silero-VAD islands, 300 ms) + `tools/analyze_takes.py` (Smith-Waterman attempt finder + librosa + mediapipe face flags) -> table; the LLM picks | `transcribe.py --mode whole` (3x faster first look) |
| Cut points, joins, QA | `tools/refine_cuts.py` (audio-refined in/out, real PTS) -> `tools/conform.py` (35 ms equal-power crossfades, ±3 dB take match, room tone) -> `tools/cut_qa.py` (pass/fail gate + cut sheet) | — |
| Silence / filler cutting | Word-timestamp cuts from the transcript (fillers are kept in transcript via `initial_prompt`) | **auto-editor 29.3.1** (audio threshold; exports v3 timeline JSON), **silero-vad 6.2.3** (onnx) |
| Scene/cut detection | **PySceneDetect 0.7.3** (`detect-adaptive`) | — |
| Ingest, tone-map, proxies, conform | **ffmpeg 6.1.1** zscale + tonemap (hable) -> Rec.709 + `setparams` BT.709 tail (`tools/tonemap.py`, used by `conform.py`) | `mobius` (param 0.3), 203-nit soft-shoulder LUT; A/B with `tonemap.py ab` |
| Loudness | `tools/master_audio.sh` (HPF + compressor + measured gain + alimiter, iterated to -14 LUFS, ~-1.5 dBFS peak) | ffmpeg `loudnorm` 2-pass (lands 1-2 LU short on peaky speech in linear mode, see gotchas) |
| SFX | `tools/sfx_gen.py` (procedural whoosh / short whoosh / riser / sub hit / UI tick, license-free) | Mixkit (free, no attribution), Pixabay |

**Why Remotion as primary:** biggest ecosystem and most active maintenance (Motion Canvas/Revideo had months-old last
commits in late 2026; Revideo's roadmap follows the Midrender product), first-party agent skills (`remotion-dev/skills`),
first-party captions (`createTikTokStyleCaptions`), transitions, typed props + `calculateMetadata` so an EDL/JSON can
drive the whole edit, frame-accurate `<Video>` of footage, and it composites footage + graphics + audio in one render.
It rendered cleanly here with its own downloaded chrome-headless-shell.

**Licence caveat (important):** Remotion is free only for individuals and companies of up to 3 people. If the entity
producing this is larger (e.g. DDN in-house), it needs a Company License (Creators seat $25/month/seat, or Automators
$0.01/render, $100/month min). If that's a blocker, switch to **HyperFrames** (Apache-2.0, no fees); it works here too
(smoke test passed), it's slower in this container (screenshot capture on software GL), and it has a `/remotion-to-hyperframes` skill for porting.

**Why HyperFrames as fallback (not Motion Canvas / Revideo / Manim / Lottie):** HTML+GSAP is the most "agent-native" format,
Apache-2.0, deterministic, ships Claude Code skills, captions, shader transitions, a registry of blocks, and handles HDR
sources. Motion Canvas (MIT) is good for generator-based explainers but is quieter and has no first-party footage/caption
story; Revideo is uncertain; Manim is for math explainers (wrong look); Lottie is just a format: if a designer supplies
Lottie JSON, play it with `@remotion/lottie` (not installed yet: `npm i @remotion/lottie@4.0.545 lottie-web`).

**Agent skills worth knowing about**
- `remotion-dev/skills` -> `remotion-best-practices` (router to remotion-create/markup/captions/multimedia/render/...): installed in `tools/remotion/.claude/skills/` and `ddn-project/.claude/skills/`.
- `heygen-com/hyperframes` skills (`hyperframes`, `hyperframes-cli`, `media-use`, `hyperframes-registry`, ...): `hf-*` already in `ddn-project/.claude/skills/`.
- `browser-use/video-use` (MIT, very popular): "drop footage, chat, get final.mp4" talking-head skill; cuts on word boundaries/silence gaps; transcription via ElevenLabs API (key needed). Good reference for workflow, but we do the same thing locally with faster-whisper; not installed.
- Others seen: `cut-video` slash command, `video-subtitle-cutter` (whisper + ffmpeg cut lists), `videocut-talk-edit` (Volcengine ASR). Nothing beats the local pipeline below for a DDN-quality job.

## 2. Footage specifics: iPhone 12 4K30 HEVC HDR

iPhone 12 HDR video = HEVC Main10, **HLG (arib-std-b67), BT.2020**, with Dolby Vision 8.4 RPU that ffmpeg ignores (fine:
the base layer is plain HLG). Check with:
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,pix_fmt,color_transfer,color_primaries,color_space:stream_side_data_list -of compact IMG_xxxx.MOV
```
If `color_transfer=arib-std-b67` -> tone-map. If `bt709` (HDR was off) -> just scale. Also check `rotation` side data (portrait clips) and variable frame rate (`r_frame_rate` vs `avg_frame_rate`; conform forces `fps=30`).

**Verified tone-map chain (HLG -> SDR Rec.709), resize inside zscale (2-3x faster than tonemapping at 4K then scaling):**
```
zscale=w=1920:h=1080:f=bilinear:tin=arib-std-b67:min=bt2020nc:pin=bt2020:rin=tv:t=linear:npl=203,
format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,
setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv
```
(`tonemap.py chain --method hable|mobius|lut` prints it. The `setparams` tail stops HLG frame tags leaking into
intermediates; encode intermediates with `-g 30 -keyint_min 30` and BT.709 stream tags. Tone-map B-roll/inserts too.)
(for 4K use `w=3840:h=2160`; for PQ sources use `tin=smpte2084`). `npl=203` = HLG reference white. Hable is a safe
default; try `tonemap=mobius` if faces look too flat/dark, and judge on frames (`ffmpeg -ss 10 -i x -frames:v 1 f.png`).
**Do not feed raw HEVC HLG to Remotion**: it decodes it (slowly, 13.9 s per output second at 4K) and Chrome's own
HDR->SDR conversion gave oversaturated, uncontrolled colours. Always tonemap in ffmpeg first.

## 3. Pipeline (step by step)

All scripts are in `/home/user/ddn-project/tools/`; Python ones run with `tools/venv/bin/python`.

1. **Ingest**: copy originals to `ddn-project/footage/` (read-only), `ffprobe` each (table of duration, transfer, rotation, fps).
2. **Proxies (1080p SDR H.264)**: `tonemap.py proxy footage/IMG.MOV proxies/IMG.mp4 [--method hable|mobius|lut]`
   (~1.0x realtime on 4 cores; BT.709-tagged frames and stream, `-g 30`). Analysis audio straight from the camera file:
   `ffmpeg -i IMG.MOV -vn -ac 1 -ar 16000 audio/IMG.wav`.
   **Before locking the look, A/B the tone map on skin:** `tonemap.py ab footage/IMG.MOV ab/ --times 5,60` writes stills
   + `tonemap_ab.jpg` (full frame + face crop per method) + skin Lab stats. On the synthetic test (+0.7 stop over HLG ref
   white) hable crushed skin (L* 49), mobius held it (L* 67, chroma 28), the soft-shoulder LUT kept it bright but clipped
   28% of skin pixels (it compresses luminance only, so a hot red channel still clips). Judge on real footage.
3. **Transcribe (islands)**: `transcribe.py audio/IMG.wav tx/IMG.json` (large-v3-turbo int8). Silero VAD (inside faster-whisper,
   ONNX) with `min_silence 300 ms` cuts speech islands; each island (+0.1 s) is transcribed alone, so false starts and
   restarts survive as their own islands instead of being merged into one clean sentence; the filler `initial_prompt`
   keeps "um/uh". Islands holding a word > 1 s are re-split at 0.1-0.3 s level dips and re-transcribed. Costs RTF ~1.0-2.0
   on 4 vCPU (each island pays a full 30 s encoder window; batching didn't help on CPU) vs 0.32 for `--mode whole`.
4. **Find every attempt & build the take table**:
   `analyze_takes.py --script script.txt --out takes/takes.json --md takes/takes.md --clip IMG_0012 --tx tx/IMG_0012.json --audio audio/IMG_0012.wav --video proxies/IMG_0012.mp4 --src footage/IMG_0012.MOV [--clip ... repeated per clip, in shooting order]`
   Script units = sentences (< 4 words merge forward). Smith-Waterman alignment (+2·sim / −1 / −0.8 missing / −0.6 extra,
   fuzzy word sim) with masking finds every attempt: FULL (cov ≥ 0.9 + first + last word), part, FALSE_START (≥ 2 words
   from the line's start). Per attempt: coverage, extra/missing, fillers, max gap, wpm, min/mean word prob, speech level,
   RMS-dB σ and pitch σ (semitones), face flags vs the attempt's own median (turn/glance/side/closed/tilt/big, keep ≤ 0.5 s
   vs cover), blinks, sharpness vs clip median, and **runs** (consecutive lines said ≤ 0.8 s apart). `takes.md` is the
   table for the LLM editor, with an advisory suggestion. **The LLM makes the pick**, by these rules: meaning over exact
   wording; later attempt over earlier, all else equal; prefer continuous runs; never splice half-takes mid-sentence unless
   on a natural pause; a line never said is reported, not invented. Unmatched islands (ad-libs) are listed at the end.
5. **Refine cut points -> EDL**: `refine_cuts.py --takes takes/takes.json --pick 1:0 2:1 3:1 4:1 --out edl.json`
   (`--pick suggested` takes the advisory picks; `CLIP:START-END` for a hand range). Picks said back to back become one
   segment. Out points walk forward on 10 ms levels until 30 ms are quiet (floor+12 dB, clamped −56…−40) in broadband AND
   above 2.5 kHz (sibilants), with a 250 ms dip-then-resume look-ahead and a t/k/p release-burst rule; in points find the
   true onset and walk back ≤ 150 ms over breathy onsets. Pad 100 ms / 180 ms (never into neighbouring sound), shrink
   pauses > 0.35 s to ~0.25 s, round frames outward on the source's **real frame PTS** (29.97 fps iPhones drift vs frame/30).
   On the test rush the refined ends landed within 10 ms of the true phrase ends; Whisper's ends were 70-370 ms early.
6. **Conform**: `conform.py edl.json review/cut.mp4` (auto tone-map if HLG/PQ; `--tonemap mobius|lut|none`), or
   `--res 3840x2160 --crf 14` for the final. Video: hard cuts at the snapped times, output at the source rate (29.97 kept),
   BT.709 tags, `-g 30`. Audio is rebuilt in numpy: 35 ms equal-power crossfade at every join using real handles (length
   stays exactly Σ(out−in), no click), one gain per take to the median speech level (clamped ±3 dB), and a looped room-tone
   bed (quietest flat 1.5 s ×0.7) so no gap drops to digital silence. `--audio-out voice.wav` keeps the voice track.
6b. **Cut-QA gate (before any draft goes out)**: `cut_qa.py review/cut.mp4 --edl edl.json --takes takes/takes.json --out qa/`
   -> `qa/qa.md`, `qa/qa.json`, `qa/cutsheet.jpg` (3 frames each side of every cut); exit 1 = FAIL. FAIL: clipped tail/onset
   (voice in the edge 40 ms AND the source keeps sounding past the cut), doubled words/n-grams in the ±0.8 s re-transcribed
   join windows, hidden restarts (each piece split at ≥ 0.15 s silences, parts transcribed alone), script words the picked
   take said but the final re-transcription lacks. WARN: edge voice, < 0.15 s air, > 1.4 s dead air, 3+ joins in 8 s,
   words > 0.7 s, join-adjacent word not heard, script words missing in source and final alike (said differently).
   Whisper alone does not catch a 0.27 s clipped tail (it still "heard" *demand*); the audio edge check does. Listen to
   flagged joins and look at the cut sheet anyway. Self-test of steps 2-6b: `bash tools/selftest_takes.sh`.
7. **Captions**: `tx_to_captions.py tx/IMG.json edl.json remotion/public/captions.json` re-times words onto the edited timeline
   (multi-source EDLs: run per source with `--src` and merge). Remotion `createTikTokStyleCaptions` pages + active-word highlight
   (see `TalkingHead.tsx`). For burned-in sentence captions, combine ~1200 ms; also export an SRT for platforms if needed.
8. **Motion graphics composition** (`tools/remotion/src/`): `TalkingHead.tsx` is the working template = cut video + lower third
   (name + red mono role tag, matching DDN's "[NAME] / CEO & Co-Founder, DDN" look) + word-highlight captions + whoosh SFX via
   `<Audio>`; `calculateMetadata` sizes the comp to the video. Build further scenes as `<Sequence>`s / `@remotion/transitions`
   (`TransitionSeries` with fade/slide/wipe + custom), title cards, stat callouts, `@remotion/shapes`/`paths` line art,
   `@remotion/noise` particle fields. Size everything relative to `width/1920` so the same comp renders 1080p and 4K.
   Fonts are **local** (`src/fonts.ts`, `@remotion/fonts` + `@fontsource/inter`): Google Fonts fetches fail in headless Chrome (proxy CA).
   Swap in DDN's brand font if supplied in `ddn-project/brand/`.
9. **Render**: review at 1080p from proxies: `npx remotion render TalkingHead out/review.mp4`; final: conform 4K mezzanine,
   then `npx remotion render TalkingHead4K out/final_4k.mp4 --props='{"src":"cut4k.mp4",...}' --crf=16` (or `--codec=prores --prores-profile=hq` for a master).
   Studio for interactive tweaking: `npx remotion studio` (port 3000).
10. **Master audio**: `master_audio.sh out/final_4k.mp4 out/final_4k_master.mp4 -14` -> verified -14.0 LUFS, -1.5 dBFS peak on the test render (video stream-copied).
    For music beds: duck under VO in Remotion with a `volume` callback (~-18 to -22 dB under speech), then master the mix.
11. **QC**: `cut_qa.py` on the conformed cut (step 6b), then on the final: `ffmpeg -i final -af ebur128=peak=true -f null -`, frame grabs at every graphic, ffprobe colour tags (bt709, stream and frame level: `ffprobe -show_frames -read_intervals %+#1`), and watch the cuts.

### DDN look notes (from `ddn-project/reference/frames`)
Red-to-orange gradients (signal red ~#E4002B into orange), white/black grounds, heavy uppercase sans headlines with
word-by-word reveals ("BEYOND / THE GRIND"), monospace small-caps role tags on red, dotted circular/spiral particle motifs
(the "o" mark), clean light-sweep logo reveals. Keep motion confident and fast-out/slow-in (spring damping ~200), 6-8 frame staggers.

## 4. Measured CPU performance (4 vCPU, no GPU)

| Task | Result |
|---|---|
| Remotion 1080p, footage + animated text + gradient overlay | 3 s clip: 11.5 s wall (~4-5 s is bundle/browser start); 10 s clip: 26 s => **~2.6 s per output second** (~2 s/s marginal) |
| Remotion 4K (3840x2160), real 4K H.264 SDR mezzanine | 10 s clip: 77 s => **~7.7 s per output second** |
| Remotion 4K, 1080p source upscaled | 10 s: 47 s (4.7 s/s) |
| Remotion 4K, raw HEVC HLG source | 10 s: 139 s (13.9 s/s) **and wrong colours: don't** |
| Remotion transparent overlay only (ProRes 4444) | 1080p 10 s: 26 s; 4K 10 s: 91 s and 1.1 GB: slower than full composite, don't use for long spans |
| Remotion transparent VP9 (webm) 1080p 10 s | 28.6 s |
| Remotion TalkingHead (video + captions + lower third + SFX), 5.3 s 1080p | 22 s |
| HyperFrames 3 s 1080p (video + GSAP text) | 16.8 s (screenshot capture, software GL) |
| faster-whisper large-v3-turbo int8, 25.3 s audio | 8.8 s (**RTF 0.35**) + 4 s model load; transcript perfect incl. "um/uh" |
| faster-whisper small.en int8 | RTF 0.32; worse accuracy |
| 4K HEVC 10-bit decode only | ~3x realtime |
| 1080p SDR proxy from 4K HLG (zscale-resize-first chain) | **~1.0x realtime** (26 s for 25 s); naive order (tonemap at 4K then scale) 3.6x slower |
| 4K SDR mezzanine (CRF 14, preset medium) | 4.8 s per second; conform 4K veryfast ~2.8 s per second |
| analyze_takes.py (3 takes, audio + face metrics) | ~8 s |
| transcribe.py islands, 34.8 s multi-take rush (8 islands) | 35-70 s (**RTF 1.0-2.0**, load-dependent) vs 11 s whole-file |
| analyze_takes.py SW matcher + 10 fps face scan, 34.8 s rush | ~9 s |
| conform.py 4 pieces 4K HLG -> 1080p (tone-map + numpy voice) | 20 s for 15.3 s output |
| cut_qa.py, 3 joins, 15 s cut (join windows + subcheck + final islands) | ~80 s |
| selftest_takes.sh end to end (rush reused) | 6 min 23 s |
| silero-vad (onnx) 25 s | 0.75 s; PySceneDetect 9 s 1080p: 1 s; auto-editor 25 s clip incl. re-encode: 10 s |

**Estimates for a 2-minute finished piece from ~20 min of rushes:** proxies ~20 min, transcription ~7 min, take analysis
~5 min, 1080p review render ~5 min, 4K conform ~6 min + 4K Remotion render ~15-16 min, mastering <1 min.
Tip: iterate at 1080p; only render 4K once. Use `--frames=300-450` to re-render just a section.

## 5. Install commands that worked (all in setup.sh)

```bash
apt-get install -y libegl1 libgles2 espeak-ng          # libEGL needed by mediapipe Tasks; espeak only for test speech
python3 -m venv tools/venv
tools/venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu   # keep silero-vad's torch CPU-only
tools/venv/bin/pip install faster-whisper auto-editor scenedetect librosa pyloudnorm opencv-python-headless mediapipe rapidfuzz silero-vad soundfile numpy scipy
tools/venv/bin/auto-editor --version                    # downloads the binary on first run
curl -sSfL -o tools/models/face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task
cd tools/remotion && npm ci && npx remotion browser ensure
npx -y skills add remotion-dev/skills --skill remotion-best-practices --agent claude-code -y
cd tools/hyperframes-test && npm i hyperframes@0.9.67 gsap@3.15.0
```
Versions: remotion 4.0.545 (all `@remotion/*` pinned identical), faster-whisper 1.2.1, ctranslate2 4.9.0, auto-editor 29.3.1,
scenedetect 0.7.3, librosa 1.0.1, pyloudnorm 0.2.0, opencv 5.1.0, mediapipe 1.2.3, silero-vad 6.2.3, rapidfuzz 3.14.6, hyperframes 0.9.67.

Verification: `setup.sh --smoke` was run in a clean copy of `tools/` (no venv/node_modules/models): full install in 72 s
(warm pip/npm caches and Whisper model already in `~/.cache/huggingface`; a cold container adds ~1.6 GB model + ~1 GB wheels download, expect 5-10 min),
then synthetic HLG HEVC clip -> tonemapped conform -> transcribe -> take scoring -> captions -> Remotion TalkingHead render -> master at -14.0 LUFS: total 2 m 07 s.
The CPU-torch venv is 2.5 GB vs 6.9 GB for the first (CUDA-torch) venv currently in `tools/venv`.

## 6. Gotchas found while testing

- **Run the Python tools with `tools/venv/bin/python`**: `conform.py` now needs numpy/scipy, which the system python lacks.
- **Island transcription mishears short context-free islands** more than whole-file: espeak "fuel of A I" -> "fuel in the eye", "A I factories" -> "iFactories". The SW matcher's fuzzy scoring + island-extension keeps such attempts (shown as `part` with the misheard words as extras); the LLM judges meaning. Partial alignments now extend to the end of their island so a misheard last word is never cut off.
- **zscale sRGB->HLG needs explicit `p=`/`m=gbr` on the linearising step** ("no path between colorspaces" otherwise); see `make_test_takes.py`.
- **Equal-power crossfades assume uncorrelated material**: on a continuous tone the join is click-free but ~2 dB louder for 35 ms; on speech joins (silence/room tone at the edit) it's inaudible.

- **faster-whisper 1.2.1 + PyAV 19**: `av.open(..., metadata_errors=...)` TypeError. `transcribe.py` decodes audio with ffmpeg to a numpy array instead (also handles .MOV directly).
- **Fonts**: headless Chrome doesn't trust the egress proxy CA, so `@remotion/google-fonts` and CDN `<script>`s (GSAP in HyperFrames' template) fail -> `delayRender` timeout. Use local font files / vendored JS. (Remotion's own Chrome download and npm work through the proxy.)
- **mediapipe 1.2.x** has no legacy `mp.solutions`; use the Tasks API (`FaceLandmarker` + `.task` model) and it needs `libEGL.so.1`. Close the landmarker explicitly (done in script) to avoid a shutdown traceback.
- **silero-vad** pulls default torch with CUDA (~5 GB venv); install CPU torch first. `read_audio` needs torchaudio: pass a tensor from ffmpeg/soundfile instead.
- **Loudnorm linear mode** won't raise gain past the true-peak ceiling and silently ends 1-2 LU short on peaky speech; `master_audio.sh` uses measured gain + limiter and re-measures (up to 3 passes).
- **Remotion version skew**: all `remotion`/`@remotion/*` must be the exact same version (pinned without `^`).
- Remotion prints a harmless "differing memory amounts" cgroup warning.
- `--browser-executable=/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell` also works (same speed); the full Playwright Chromium (`/opt/pw-browsers/chromium`) works but is ~2x slower. Not needed: Remotion's own download succeeded.
- PySceneDetect has no `[opencv-headless]` extra anymore; just install `opencv-python-headless` alongside.
- mediapipe pulls `opencv-contrib-python` too (several cv2 wheels coexist; worked, but don't mix GUI calls).
- YuNet ONNX download from the opencv_zoo GitHub raw URL was 403 through the proxy; mediapipe covers face detection anyway.

## 7. Links

- Remotion: https://www.remotion.dev/docs , skills https://remotion.dev/skills (`remotion-dev/skills`), licence https://www.remotion.dev/docs/license/pricing.md , captions https://www.remotion.dev/docs/captions
- HyperFrames: https://github.com/heygen-com/hyperframes , docs https://hyperframes.heygen.com/llms.txt
- video-use skill: https://github.com/browser-use/video-use
- Comparisons: https://www.pkgpulse.com/guides/remotion-vs-motion-canvas-vs-revideo-programmatic-video-2026 , https://autoae.online/blog/revideo-vs-remotion-2026
- faster-whisper: https://github.com/SYSTRAN/faster-whisper (model `mobiuslabsgmbh/faster-whisper-large-v3-turbo`); whisperX (better forced-alignment word times, heavier torch/wav2vec2 stack: only if word timings prove sloppy): https://github.com/m-bain/whisperX ; whisper.cpp: https://github.com/ggml-org/whisper.cpp
- auto-editor: https://github.com/WyattBlue/auto-editor ; PySceneDetect: https://www.scenedetect.com ; silero-vad: https://github.com/snakers4/silero-vad
- mediapipe Face Landmarker: https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker
- ffmpeg zscale/tonemap: https://ffmpeg.org/ffmpeg-filters.html#tonemap-1 , loudnorm: https://ffmpeg.org/ffmpeg-filters.html#loudnorm
- SFX: https://mixkit.co/free-sound-effects/whoosh/ (Mixkit licence, no attribution), Pixabay sound effects; ElevenLabs SFX free tier requires attribution.

## 8. File map

- `tools/setup.sh`: rebuild everything (`--smoke` runs an end-to-end test)
- `tools/transcribe.py` (islands), `analyze_takes.py` (SW take table), `refine_cuts.py` (audio-refined EDL), `conform.py` (joins + tone-map), `cut_qa.py` (QA gate), `tonemap.py` (chains, LUT, proxy, A/B), `audiolib.py` (shared envelopes/PTS), `tx_to_captions.py`, `master_audio.sh`, `sfx_gen.py`
- `tools/make_test_takes.py` + `tools/selftest_takes.sh`: synthetic multi-take HLG rush and the end-to-end take-pipeline self-test (outputs in `tools/test/mt/`)
- `tools/models/hlg_softshoulder_203.cube`: soft-shoulder tone-map LUT (regenerate with `tonemap.py lut`)
- `tools/remotion/`: Remotion project (`src/Root.tsx`, `TalkingHead.tsx`, `SmokeTest.tsx`, `fonts.ts`; `public/fonts`, `public/sfx`), test outputs in `out/`
- `tools/hyperframes-test/smoke/`: HyperFrames fallback smoke project
- `tools/models/face_landmarker.task`; Whisper models in `~/.cache/huggingface` (re-downloaded by setup.sh)
- `tools/test/`: synthetic test assets (TTS takes, fake HLG HEVC clip, transcripts, take scores)
