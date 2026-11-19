# Self-Critique Loop: "Does this look like DDN, or like AI?"

Every graphic and every edit goes through this loop before you see it.
The judge is DDN's real footage, not taste. The reference frames are in `reference/frames/`, and the specs are in `research/DDN_STYLE_GUIDE.md`.

---

## The loop (repeat until it passes, max ~5 rounds per element)

1. **Render**: a low-res proxy of the element or section (fast).
2. **Contact sheet**: pull frames at fixed points: first frame, every 3 frames through the animation-in, mid-hold, and the exit.
3. **Side-by-side**: put our sheet next to the matching DDN reference frames (same element type) in one image. Compare at the same scale.
4. **Score** each item on the checklists below as pass or fail, and write down *what* is wrong in concrete terms (e.g. "tag text 20% too large", "enters 6 frames too slow", "red is too saturated").
5. **Fix**: change the specific numbers, not "make it better".
6. **Motion check**: look at frame-to-frame timing (a strip of every frame of the animation). Easing and speed problems only show up in motion.
7. **Full-pass watch**: once the section passes, check it in context with the cuts and the audio.
8. **Log it**: record each round in `output/critique_log.md` (what failed, what changed), so the decisions are traceable and you can push back on any of them.

Only after everything passes do you get a preview. You then give the human judgement and I loop again.

---

## Checklist A: "AI-generic" tells (any one = FAIL)

- [ ] Bouncy, elastic or overshooting motion (DDN never bounces)
- [ ] Transition effects on ordinary cuts (DDN uses about 90% hard cuts)
- [ ] Glow or neon on everything, or purple/blue "cyber" gradients (not DDN colours)
- [ ] Generic floating particles, plexus networks or "digital rain" (not used in DDN's 2026 look)
- [ ] Everything fading in at the same speed (no rhythm, no hierarchy)
- [ ] Text centred by default when DDN offsets it to the lower-left third
- [ ] Default fonts (Arial, Roboto, plain system UI) instead of Articulat/Inter Tight plus Geist Mono
- [ ] Emoji, stock icons or clip-art arrows
- [ ] Captions that pop or scale word by word, TikTok-style (DDN captions change by hard cut)
- [ ] Animation that starts on the same frame as the cut every time (feels robotic; needs offsets)
- [ ] Graphics over the face
- [ ] Too much at once: more than one animated graphic element competing on screen
- [ ] Perfectly clean, flat digital colour with no grain or texture where DDN uses grain
- [ ] Whooshes and SFX on every graphic (DDN is music-led, with SFX used sparingly)

## Checklist B: DDN fidelity (all must PASS)

- [ ] Colours are exact brand hex values (#ED2738 red, #7D2D3F wine, #201E1E black, warm greys)
- [ ] Easing matches: expo-out for rises, stepped/linear for typewriter, no ease on hard cuts
- [ ] Timing within ±2 frames of the spec table (section 7 of the style guide)
- [ ] Type sizes, weights and letter-spacing match the reference frames when compared side by side
- [ ] Position: inside the 5% safe margin, lower-left third, 8–16% from the left edge
- [ ] Footage grade: warm, soft contrast, lifted blacks, skin around 65–70 IRE, fine grain
- [ ] Pacing: talking-head shots about 3–5 s (punch-ins hide jump cuts); faster only in hype moments

## Checklist C: Edit quality

- [ ] No clipped words: every cut is checked on the waveform, not just the transcript
- [ ] No audible clicks or pops: short audio crossfades on every cut
- [ ] Breath and room tone feel natural: not machine-gun tight, not draggy
- [ ] Jump cuts are hidden (alternate 100% and ~140% punch-in) or are deliberate
- [ ] Best take per line was chosen for **delivery**, not just correct words; reasons are logged
- [ ] Energy arc: the open hooks within 3 s, the middle doesn't sag, the close lands
- [ ] Loudness: voice-led at about -19 LUFS (DDN interview) or -14 LUFS (YouTube/social); peaks below -1 dBTP

---

## Tools that make it work
- `ffmpeg`: contact sheets (`tile`), frame strips, side-by-side (`hstack`), scene/cut timings
- Remotion `still` renders: render any single frame instantly for pixel checks
- Colour sampling (Python/Pillow): measure the hex value of rendered pixels against the brand palette
- `pyloudnorm`: loudness check
- My own eyes on every sheet. I read the images directly, so this is a visual review, not just numbers.
