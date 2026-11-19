# Research round 2: premium matting, skills/plugins, pitch pacing, audio sources

Written 2026-11-19. This was research only: nothing was installed and no long renders were run. I looked at `tools/blur/bgblur.py` and `tools/blur/out/hook_motion_strip.jpg` to ground the diagnosis.

Environment assumed: 4 CPUs, 15 GB RAM, no GPU. The venv already has torch 2.15 CPU, onnxruntime 1.32 and opencv-contrib 5.1.

Speed figures marked *(est.)* are my own extrapolations, not measurements. Time each one on a 2 s clip before an overnight run.

---

## PRIORITY 1: the "weird outline" around the moving speaker

### 1.1 Likely causes in the current `bgblur.py`
Read these before swapping models. Each is a hypothesis, and each has a cheap test.

On the hook roll-in strip (`tools/blur/out/hook_motion_strip.jpg`, frames 5–8) I can see two artefacts:
- a dark, smeared ghost of the body and trousers trailing on the floor behind him;
- a band of noticeably *less* blurred background hugging his silhouette.

Five likely causes in the code:

1. **The soft edge band shows the sharp, original background.** The composite is `res = bg + (fg - bg)*a`. Here `fg` is the *original frame* everywhere, except a narrow band where RVM's `fgr` is mixed in, and even there the correction is clipped to ±48 code values (lines 651–657).
   - Where alpha is between 0.05 and 0.95, you therefore see unblurred background texture at partial opacity, ringing the person. Motion makes it worse because motion blur widens the soft band to 10–40 px.
   - This is the classic "cookie-cutter outline".
   - **Fix:** in the soft band, `fg` must be a *decontaminated foreground* estimate (the foreground colour with the background colour removed), never the source pixel. Use RVM `fgr` without the ±48 clip, or `pymatting.estimate_foreground_ml(frame, alpha)` (MIT, CPU, about 0.3–1 s per 1080p frame on an ROI *(est.)*).
2. **The alpha "stabiliser" lags behind motion.** `stabilise_alpha` is an EMA with a floor of k=0.5 for small changes. Mid-alpha values (exactly the motion-blurred edge) change less than 0.125 per frame, so they lag by roughly 1–2 frames.
   - That leaves a ghost edge one step behind the body: half-transparent person over blurred plate on the trailing side, and sharp background on the leading side.
   - **Fix:** remove it, or gate it with optical-flow magnitude (see 1.4). Recurrent models (RVM, MatAnyone) are already temporally smooth.
3. **The plate fill does not cover the motion-blur tail.** The fill mask is `a > 0.02`, dilated by H/160 (about 7 px at 1080p). Fast arms leave a motion-blur smear 20–60 px wide that RVM partly scores as background, so the person's colours stay in the "background" and get blurred, giving the dark smear ghost.
   - The `keep` term stops spreading only inside `am_full`, not in the tail.
   - **Fix:** dilate the fill and keep-out region by the optical-flow magnitude of the person pixels (radius = |flow| × 1.0–1.5 px), not by a constant.
4. **The MediaPipe core is unioned with a hard `max(a, cm)`.** It is a 256×256 model upscaled, with no temporal model. During fast motion it can lag or lead the true edge, which gives a hard-edged, stepped silhouette for a frame.
   - **Fix:** feather the core (Gaussian σ ≈ 4 px), erode it more (≥25 px at 1080p), or drop it once a better matte exists (the trouser problem disappears with MatAnyone or SAM 2 masks).
5. **The depth focal plane includes the floor and chair around him.** Floor pixels at his depth stay sharp, so his surroundings form an in-focus collar against the blurred room. This is physically correct but reads as an outline.
   - **Fix:** compute the CoC from depth *relative to a person-only focus*, and add a minimum blur ring of about 0.3·R outside the dilated matte, so nothing next to him is pin-sharp unless it is in the keep-polygon.

**Fast diagnosis, before any new model:** render 3 s of the roll-in with debug outputs:
- alpha as greyscale;
- `fg - frame` (the decontamination);
- `bg` before compositing;
- the final frame, with an edge overlay (alpha 0.05–0.95 band in magenta).

View them at 100% in a 4-up. If the band in the final frame shows background texture, it is cause 1. If the alpha trails the body, it is cause 2.

### 1.2 Model options, ranked for this job (CPU, about 77 s of footage, overnight is OK)

| # | Model | Licence | Temporal stability | Hair / motion blur | CPU feasibility (4 cores) | Install |
|---|---|---|---|---|---|---|
| A | **MatAnyone 2** (CVPR 2026, [repo](https://github.com/pq-yang/MatAnyone2), [paper](https://arxiv.org/abs/2512.11782)) | **NTU S-Lab 1.0: non-commercial only.** Commercial use needs written permission (peiqingyang99@outlook.com, ccloy@ntu.edu.sg) | Best-in-class for human video matting. Memory propagation plus a reference-frame memory for big appearance changes, so it is built for roll-ins | Very good; trained on real footage, with an explicit "no segmentation-like boundaries" goal | The only CPU data point: 560×560, 241 frames, 8 threads = 228 s, about 0.95 s/frame ([Windows port perf page](https://sunwood-ai-labs.github.io/MatAnyone2-Gradio-Windows/guide/performance)). At `--max-size 720` on 4 cores: about 3–5 s/frame *(est.)*, so 2,310 frames take about 2–3.5 h. On GPU it needs 13.7 GB at 1080p, so on CPU stay ≤720 to fit in 15 GB RAM *(est.)* | `uv add matanyone2@git+https://github.com/pq-yang/MatAnyone2.git`, Python 3.10. It needs a first-frame mask (from SAM 2 or a click), and the code assumes `cuda:0`, so patch the device to CPU |
| B | **SAM 2.1** video predictor ([repo](https://github.com/facebookresearch/sam2)) or **EfficientTAM** ([repo](https://github.com/yformer/EfficientTAM)), giving a binary mask, then a matting refiner in the unknown band (C or D) | **Apache-2.0** (both) | Tracker-level stability (memory bank). Very robust to roll-in, occlusion and re-entry. Masks are binary, so edges need a refiner | The tracker gives no soft edge; quality depends on the refiner | Hiera-Tiny: about 2.0 s/frame at 6 threads, about 5 s/frame at 2 threads on a laptop i7 ([sam2-lite card](https://huggingface.co/Pablopigue/sam2-lite)), so about 3–4 s/frame here *(est.)*, about 2–2.5 h for 77 s | pip-installable, CPU works (`device="cpu"`). ONNX video exports exist ([square-zero-labs/sam2.1-tiny-video-onnx](https://huggingface.co/square-zero-labs/sam2.1-tiny-video-onnx)) |
| C | **ViTMatte-S** ([repo](https://github.com/hustvl/ViTMatte), HF `hustvl/vitmatte-small-composition-1k`) as a trimap refiner | **MIT** | None (per frame), so the trimap from B or RVM must be stable; then the output is stable apart from the band | Excellent hair; handles motion blur as semi-transparency | About 7 s for 512² in PyTorch CPU (one report). Run it only on a person-ROI crop at about 1024 px long side, about 10–20 s/frame *(est.)*, roughly 8–12 h. That is overnight-feasible but tight. **MEMatte** (memory-efficient ViTMatte, about −50% latency) is an option |
| D | **BiRefNet_HR-matting / BiRefNet-matting / BiRefNet_dynamic** ([repo](https://github.com/ZhengPeng7/BiRefNet), [HR-matting](https://huggingface.co/ZhengPeng7/BiRefNet_HR-matting)) | **MIT** | None; per frame, shimmers on fast motion ([note](https://replicate.com/sprited/birefnet-video/readme)). Needs temporal smoothing (1.4) | Very good static edges at 2K | Heavy (Swin-L). About 4 s for 1024² on M1 Max ONNX, so about 6–10 s/frame at 1024 here *(est.)*. HR at 2048 is too slow for 2,310 frames. ONNX: [PinkPixel/birefnet-hr-matting-onnx](https://huggingface.co/PinkPixel/birefnet-hr-matting-onnx) |
| E | **RVM resnet50** ([repo](https://github.com/PeterL1n/RobustVideoMatting)), our current family | GPL-3.0 (internal tool use, as now) | Good (recurrent) | Good hair; weaker on fast limbs and on dark-on-dark | About 2–3× the cost of mobilenetv3 *(est.)*. A drop-in ONNX swap (`rvm_resnet50_fp32.onnx`) | Trivial. README: keep the downsampled size between 256 and 512 px, and "use a higher ratio for full-body shots". We use 288 short side; try 432 (ratio 0.4) for roll-ins |
| F | **Cutie** ([repo](https://github.com/hkchengrex/Cutie)) VOS, as an alternative tracker to SAM 2 | MIT | Strong VOS memory | Binary | Lighter than SAM 2 *(est.)* | Needs a first-frame mask |
| G | **SAM2Matting** (June 2026, [repo](https://github.com/FudanCVL/SAM2Matting), [paper](https://arxiv.org/html/2606.27339v1)) | **CC BY-NC 4.0** (non-commercial) | Inherits the SAM tracker. SAM3 variant has the best dtSSD on the V-HIM60 benchmarks | Beats MatAnyone 2 on hard V-HIM60 (MAD 14.4 vs 45.8) | SAM2.1-T variant is about 40 fps on an A6000. CPU maybe 3–6 s/frame *(est.)* | conda, Python 3.10. Same licence problem as A |
| — | VideoMaMa (CVPR 2026, video-diffusion mask-to-matte, [arXiv](https://arxiv.org/abs/2601.14255)) | Unclear (reported as CC BY-NC or Stability Community) | Excellent | Excellent | **Not CPU-feasible** (video diffusion) | Skip |
| — | MODNet (Apache-2.0), PP-Matting (Apache-2.0), BackgroundMattingV2 (MIT, needs a clean plate) | Permissive | Weak (MODNet flickers). BGMv2 is good but a *static* plate is impossible when the swivel chair moves | — | Fast | Not worth it over B+C. BGMv2 is only an option for the chair-alone segments |
| — | Matting Anything (MIT), SAM-HQ (Apache-2.0) | Permissive | Per frame | Fine | Heavy | Superseded by B+C |
| — | DaVinci Resolve Magic Mask, Runway | Commercial | Excellent | Excellent | Resolve Magic Mask is Studio-only and GPU | Not possible here. It is the obvious tool if the user has a Mac or PC with Resolve Studio |

**Licence note:** RVM is GPL (fine as an internal tool). MatAnyone 1/2, SAM2Matting and DEVA are **non-commercial**. A sales-incentive contest entry is arguably commercial use. Ask the user before shipping frames matted with A or G; use them at least as the quality reference in an A/B. B+C (Apache + MIT) is fully clean.

### 1.3 Recommended pipeline (best quality, licence-clean)
Run it overnight, only on the ranges in `edit/edl_v2.json` plus 0.5 s handles.

1. **Mask track:** SAM 2.1 Hiera-Small (or Tiny) video predictor at 1024 px.
   - Prompt: one positive box plus 2–3 clicks on the speaker, on a frame where he is fully visible. Propagate **forward and backward**, which handles the roll-in where he enters from frame edge.
   - Add one correction click on any frame where the IoU against RVM drops below 0.9.
   - Save binary masks as PNG at 1024. About 3–4 s/frame *(est.)*.
2. **Trimap:** `unknown = dilate(mask, r_out) − erode(mask, r_in)`, with `r_in` = 4 px and `r_out` = 6 px + 1.2 × |optical flow| at the boundary (OpenCV DIS flow, cheap on CPU).
   - Fast-moving hands get a wide unknown band, so their motion blur becomes partial alpha, not a hard cut.
3. **Alpha:** ViTMatte-S on a person-ROI crop (the bounding box of the dilated mask plus 64 px, long side about 1024–1280), pasted back. Alternatives:
   - fast: RVM-resnet50 alpha used *inside* the unknown band only, with SAM's mask outside;
   - quality reference: MatAnyone 2 at 720 (A/B only, licence).
4. **Temporal clean-up** of alpha, only in the unknown band:
   - flow-warp the previous alpha to the current frame;
   - blend `a_t = lerp(a_t, warp(a_{t-1}), w)` with `w = 0.5·exp(−|flow|/2px)` (smooth when still, none when moving);
   - a 3-frame median on the band only.
   - This replaces `stabilise_alpha` and does not lag motion.
5. **Foreground decontamination:** `pymatting.estimate_foreground_ml(img, alpha)` (MIT) on the ROI. Composite with the **decontaminated F**, never the source pixels, wherever 0 < α < 1.
6. **Background plate for the blur:** keep our clean-plate fill and push-pull. Make the fill region = the alpha support dilated by `max(H/160, 1.5·|flow|)`. Weight the blur by `(1−α)`, so person pixels and the motion-blur tail never spread (premultiplied, normalised blur, as we already do).
7. **Motion-aware blur strength:** compute the speaker's mean flow magnitude per frame, smoothed over 0.3 s.
   - Scale the background CoC by `1 − 0.5·smoothstep(8, 25 px/frame, speed)` (at 1080p). During the roll-in and big gestures the blur gets gentler, so edge errors have less to contrast against.
   - It comes back over about 0.5 s. A real camera's focus puller would also "lose" a fast subject, so it reads naturally.
8. **Light wrap:** add 0.1–0.2 of the blurred background over the outer 3–6 px of the matte, so edges sit in the plate instead of looking cut out. Grain: our existing matched grain, applied *after* the composite, over the whole frame, so foreground and background share the same noise.
9. **QA:** our `qa.py` ring-flicker numbers, plus a frame-by-frame 100% crop at the hand and edge for IMG_3845 207.3–217.8 (as DIRECTION §14 says).

Budget *(est.)*: SAM 2 about 2.5 h + ViTMatte about 8–10 h + render about 0.7 h for 77 s. If too slow:
- run ViTMatte only on frames where flow > 4 px or the band is > 25 px wide;
- elsewhere use RVM-resnet50 in the band.

That should cut ViTMatte to about 30–40% of frames.

### 1.4 Fallbacks (in order)
1. **Fix 1.1 first, keep the current models.** Swap mobilenetv3 for RVM resnet50 at ratio 0.4, use decontaminated F, drop the lagging EMA, use flow-dilated fill, and add a motion-gated blur reduction. This costs under a day of work and may be enough.
2. **Static-only blur:** blur only segments where the speaker's flow stays under about 4 px/frame. In motion segments (hook roll-in, big gestures), crossfade over 10–15 frames to an *unblurred* frame with a gentle vignette and grade. Hide it under a punch-in cut where possible. This is safe and costs nothing.
3. **Fake DOF without a matte:** a very mild depth-only blur (radius about 0.4% H) of the *far* room only, with the near half of the frame untouched. That leaves no person edge to get wrong.

### 1.5 Technique references
- RVM `downsample_ratio` guidance: [inference.md](https://github.com/PeterL1n/RobustVideoMatting/blob/master/documentation/inference.md)
- pymatting foreground estimation (MIT, CPU): https://github.com/pymatting/pymatting
- FBA Matting (MIT), which estimates F, B and α jointly and is good when foreground and background colours are similar (white shirt against white desk): https://github.com/MarcoForte/FBA_Matting
- Library landscape overview (2026): https://ice-ice-bear.github.io/posts/2026-04-13-matting-libraries/

---

## PRIORITY 2: skills, plugins and repos not already in REPO_INSIGHTS.md or TOOLKIT.md

### Anthropic Directory (found via the plugin catalog, 2026)
| Plugin | What it gives us | Verdict |
|---|---|---|
| **Remotion** (official, by Remotion, v4.0.528) | The same skills we have (`remotion-best-practices`, captions, render...) plus `remotion-saas` and `remotion-studio` | Already covered. Install via the directory only to get updates |
| **IT Reelsmaker** (IT Party Pattaya, v1.6.1) | Talking-head edit in Claude Code: cuts pauses and retakes, virtual camera, on-brand Remotion motion graphics, designed hook, quote and number scenes, word-timed subtitles, face-aware layout, loudness mastering | **Read it.** Its virtual-camera and face-aware-layout rules may improve our punch-ins. It is vertical-first (1080×1920) |
| **Motion Reel** (Aries Spring, v1.3.0) | Showreel motion: measured beat grid, shot list, synthesised score and SFX, a critique loop on contact sheets, −14 LUFS | Read its beat-grid and critique-loop docs for the music and graphic sync |
| **Social Media Skills** (106 skills) | Includes `talking-head-and-piece-to-camera`, `youtube-shorts`, `hook-writer`, `captions-and-clipping` | Craft checklists only; low priority |
| **FontHound** | Font picking (Windows app) | Not needed: the font is already matched |
| ManyMotions, Codesign (IMG.LY) | Remote or SaaS editors | Skip (cloud, not our pipeline) |

### GitHub (new to us)
| Repo | Licence | Why it is useful |
|---|---|---|
| [Remocn/remocn](https://github.com/Remocn/remocn) | MIT | 932 MIT Remotion components installed via shadcn (`npx shadcn@latest add @remocn/blur-reveal`), a storyboard-to-visual-QA plugin and a `scene-reviewer` agent. **Best fit for premium frosted-glass and blur-reveal text without writing it from scratch** |
| [digitalsamba/claude-code-video-toolkit](https://github.com/digitalsamba/claude-code-video-toolkit) | MIT | Mature workspace (Remotion + ffmpeg skills, templates, a "made with itself in 90 s" video). Mine its ffmpeg post-render skill and templates |
| [dojocodinglabs/remotion-superpowers](https://github.com/dojocodinglabs/remotion-superpowers) | MIT | Remotion plugin with 13 commands, TikTok captions, transitions and an AI review loop. Mostly API-key driven; borrow the review-loop prompts |
| [WhiteTowerAI/cut-as-code](https://github.com/WhiteTowerAI/cut-as-code) | MIT | Inspectable edit decisions as files, LUT grade candidates, caption presets, lower-thirds and stat cards, a reviewed motion "recipe library" |
| [iart-ai/motion-skills](https://github.com/iart-ai/motion-skills) (19 packs, 56 skills) | MIT | `kinetic-typography-skills`, `ad-video-skills` and `youtube-video-skills` are relevant. (`motion-design-skills` is already in our notes) |
| [vibe-motion/skills](https://github.com/vibe-motion/skills) | (no licence file found) | `brand-launch-video-star` (15–30 s launch-video doctrine), `pixel2motion` (logo PNG to clean SVG to logo motion). Useful for the Netflix/YouTube/Canal+/Starz/Blockbuster logo animations |
| [mattypark/Motion-graphics-skill](https://github.com/mattypark/Motion-graphics-skill) | All rights reserved (read only) | Five editing-intensity levels ("restrained corporate" vs reels), a 60-30-10 colour rule, −14 LUFS / −1.5 dBTP |
| [Moessif/code-video-showcase](https://github.com/Moessif/code-video-showcase) | MIT | Reverse-engineered beat-synced 61 s showcase (spectrogram and structure analysis). Good model for "sections lock to 4 s musical seams" |
| [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) | **AGPL-3.0** | Large agentic production system ("paste a video you love" style analysis). Reference only |
| [zhuyansen/awesome-claude-video-skills](https://github.com/zhuyansen/awesome-claude-video-skills) | list | 180 video-skill repos, security-graded. Use it to find more |

Already covered (not repeated): remotion-dev/skills, heygen-com/hyperframes (and its `talking-head-recut` and `embedded-captions` skills), browser-use/video-use, charlie947, iart-ai/motion-design-skills, kmilo93sd, MakeMyClip.

---

## PRIORITY 3: pacing and craft for a 60–90 s pitch (not interview style)

Numbers with sources first, then our working targets.

### Evidence
- **First 5 seconds:** Google's ABCD research says ≥2 shots in the first 5 s correlate with ad recall and consideration. Open with a human on screen, use tight framing on faces, and introduce the brand early ([ABCD PDF](https://thinkwithgoogle.com/_qs/documents/8472/ABCD_Complete_V7b_HR_1.pdf), [YouTube ad production guide](https://services.google.com/fh/files/misc/youtube_ad_production_guide_external.pdf)).
  - Our chair beat (1–2 s), then the timer, then him rolling in already gives 2–3 visual events in 5 s.
- **Shot length:** TV commercial average shot length was under 2 s by 1991 (MacLachlan & Logan, via [WARC](https://www.warc.com/Content/421e1376-baa5-472f-aa9d-adc58bea5146)).
  - Top talking-head reels: median shot about 3 s, about 95% hard cuts (GE calibration, already in REPO_INSIGHTS §2.4).
  - For a calm, professional pitch, the target is a **2.5–4 s median visual change**: a cut, punch-in or graphic beat. That gives about 22–30 visual changes in 85 s, without cutting the speech itself that often.
- **Pauses between lines:**
  - Natural sentence gaps run 0.5–1 s.
  - Social editing compresses them to 0.1–0.25 s ([ChatCut presets](https://chatcut.io/docs/speech-cleanup.md): Tight 0.15 s, Natural 0.25 s, Relaxed 0.4 s).
  - For a pitch: use **0.20–0.30 s within a section** and **0.45–0.7 s at section turns** (Why change, then Why now, and so on) and before the ask. The longer gaps carry the graphic and music transition.
  - Never go below 0.12 s, or breaths clip and the delivery sounds machine-gunned.
- **J/L cuts:** start with 6–12 frames of audio lead at 30 fps for quick lines ([CapCut guide](https://www.capcut.com/create/j-cuts-and-l-cuts-dialogue-edits), vendor source).
  - Our rule (REPO_INSIGHTS §2.3): 2–4 frames on same-angle take changes, 6–10 frames on angle or section changes, where the next line's breath leads the picture.
  - Use L-cuts to let music swell or a graphic's tail run under the new shot.
- **Punch-ins:** a hard cut between scale levels reads as a camera change; an *animated* zoom on a cut jolts (YD style.md).
  - Alternate wide and 112–115% every 1–2 lines in Why change and Why now.
  - Use at most one slow push (100 to 104% over 4–6 s, ease in-out) at the key line in Why DDN.
  - Never put a punch-in and a graphic entrance on the same frame.
- **Captions that read as premium:**
  - Professional subtitle standards: max **42 characters per line, 2 lines**, reading speed **≤17–20 characters/s**, minimum 5/6 s on screen ([Netflix Timed Text Style Guide](https://backlothelp.netflix.com/hc/en-us/articles/215758617)).
  - Short-form practice: 3–5 words per caption, 1–2 lines, bold sans ([summary](https://www.kapwing.com/resources/social-media-captions-styles-a-complete-guide/)).
  - Generic tells: yellow word-highlight karaoke, bouncing scale-pops on every word, emoji, thick stroke plus drop shadow, all-caps everywhere (several 2026 guides note the yellow-highlight template now reads as generic).
  - Premium for 16:9:
    - 1 line, 3–6 words, sentence case, in Inter Tight;
    - about 4.2–4.6% of frame height (45–50 px at 1080p) in weight 600;
    - on a subtle frosted pill (8–12 px blur behind, 10–14% white fill, no hard stroke);
    - fades in over 6–8 frames with 6–10 px upward travel and a `ddn-out` ease;
    - emphasis uses *one* key word per phrase in the DDN accent colour, never word-by-word karaoke;
    - bottom safe margin about 8–10% of frame height, captions cleared when a full-frame graphic is up.
- **Music under speech:**
  - Accessibility benchmark: background audio ≥20 dB below speech (WCAG 1.4.7).
  - Common guides: bed 18–24 dB under the voice while talking ([summary](https://www.descript.com/blog/article/how-to-set-the-perfect-audio-levels-for-video)). In LUFS terms, voice at −14 integrated puts the bed at about −32 to −36 LUFS short-term under speech.
  - Shape the energy by arrangement (adding layers per section, as MUSIC concept A does), not by fader rides.
  - Duck 3–6 dB further only on dense lines, with 80–150 ms attack and 300–600 ms release.
  - Lift the bed +4–6 dB in gaps of 0.5 s or more and at section turns, so the music "breathes" between lines. That is the main thing that makes pitch videos feel energetic without being loud.
  - Sidechain the voice only into the 1–4 kHz region of the music (dynamic EQ, −3 to −5 dB) instead of full-band ducking. The music keeps its weight while the words stay clear.
- **SFX that feel smooth** (matches DIRECTION §11):
  - −24 to −30 dB relative to dialogue peaks;
  - low-pass at 6–10 kHz, attacks softened (5–15 ms fade-in);
  - the same short room reverb as the music, so they sit in one space;
  - land them on the *graphic's* key frame, not on the cut;
  - at most about 0.5 audible SFX per 10 s (GE calibration: 0.4–0.9);
  - pre-roll whooshes so the peak lands on the frame where the motion is fastest, typically 2–4 frames before the graphic settles.
- **Structure:** hook ≤8 s, then three "why" beats of about 15–20 s each with one visual idea per beat, then the ask with a clean musical stop (already in MUSIC concept A).
  - End card hold: 2.5–3 s, with a −1 dB fade-out of music over the last 1.5 s, or a hard stop on the ding.

### Our working targets (summary)
- median visual change 3 s
- pauses 0.25 s within a section and 0.5–0.7 s at turns
- J-cuts 2–4 frames on same angle, 6–10 frames across angles
- punch-ins at 112–115%, alternating
- 1 slow push
- captions: 1 line, 3–6 words, 42-character cap, ≤17 cps
- music −20 dB under the voice, +5 dB in gaps
- SFX at −26 dB, low-passed, ≤5 in total

---

## PRIORITY 4: licensed music and SFX (brief)
MUSIC.md and INSTRUMENT_OPTIONS.md already cover Salamander, VCSL, FreePats, Naked Drums and BigSoundBank. New candidates:

| Source | Licence | Notes |
|---|---|---|
| [Sonniss GDC 2026 Game Audio Bundle](https://sonniss.com/gameaudiogdc) (7.5 GB, 17 vendors) | Royalty-free, commercial use OK, no attribution (per bundle terms; re-read the 2026 licence, since the 2024 one added a no-AI-training clause) | The best free *premium* SFX: designed whooshes, UI, risers, impacts. It may need a browser download (proxy) |
| [Freesound](https://freesound.org) with the CC0 filter | CC0 / CC BY | Login needed, 403 to the sandbox; the user downloads |
| [Pixabay Music / SFX](https://pixabay.com/music/) | Pixabay Content License (commercial OK, no attribution, no standalone resale) | Quality varies; some tracks are registered with Content ID, so check before use |
| Scott Buckley ([scottbuckley.com.au](https://www.scottbuckley.com.au)) | CC BY 4.0 | Orchestral and cinematic, high production quality. Too cinematic for 120 BPM drive, but good for the ask moment |
| HoliznaCC0 (Free Music Archive) | CC0 | Lo-fi and electronic; patchy |
| [Mixkit](https://mixkit.co) music and SFX | Mixkit licence (commercial OK, no attribution) | Already noted for SFX; the music is generic |
| ElevenLabs Music / SFX (connector is available in this session) | Commercial on paid plans | AI-generated, so it conflicts with "real Yamaha instruments" and "imitate no one". Last resort only |

**Yamaha instruments we had not listed** (licences **unverified**; check before use):
- PatchArena "Lately Bass" (TX81Z, SFZ);
- Reusenoise Yamaha RBX170 bass (SFZ; we already have RBX via FreePats);
- Yamaha RX-17 HD drum-machine pack (KVR / SampleScience; usually royalty-free for music production);
- Yamaha DTXplorer kit (BPB, 2015).

None beats the verified FreePats RBX, VCSL TX81Z and Naked Drums set already chosen.

---

## Next actions (ordered)
1. Run the 4-up debug render of IMG_3845 207.3–217.8 and confirm which of causes 1–5 produce the outline (about 10 min of CPU).
2. Patch `bgblur.py`:
   - decontaminated F (no ±48 clip, or pymatting);
   - remove the lagging EMA;
   - flow-dilated fill and keep-out;
   - feathered MediaPipe core;
   - motion-gated blur strength;
   - RVM resnet50 at ratio 0.4.

   Re-run the same range and QA.
3. If the edges are still visible at 100%: install SAM 2.1 (Apache) + ViTMatte-S (MIT) on CPU and run the 1.3 pipeline overnight on the EDL ranges. Optionally A/B against MatAnyone 2 at 720 (non-commercial: ask the user first).
4. If time runs out, use fallback 1.4.2 (blur static segments only).
