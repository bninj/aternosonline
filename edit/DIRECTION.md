# Edit direction: the user's decisions (single source of truth)

Original brief: the competition, script, process, deviation rules, timing, captions, graphics, facts, music, QA and deliverables (see the conversation brief; the script is in `edit/script.txt`, facts in `deliverables/FACTS.md`).

## Later decisions (these override the original brief)
1. **Hard cap 90 s, target about 85 s.** The chair opener and the timer count inside the 90 s.
2. **Opener:** the AI chair alone for 1–2 s (IMG_3844 is a clean 9 s chair-alone shot, or use the head of the hook clip). Then the timer graphic shows that the 90 s has begun. **Trim the dead space in the hook before the user moves in**, so it doesn't drag after the 1–2 s chair beat.
3. **Timer:** visual only, not on screen all the time (appears at the start, then animates away). **No audible clock tick** in the music or SFX. At most one very soft click at the timer start.
4. **Cuts must be smooth, never choppy.** Audio joins use crossfades and a room-tone bed. Visually, hide same-angle jump cuts by alternating wide and 10–15% punch-ins (Why change, Why now). Where a jump cut stays visible, use a very short soft dissolve (3–5 frames) rather than a harsh snap. The hook and the ask stay continuous runs.
5. **Graphics:** frosted glass plus a subtle prism, motion blur, premium. Never hard cut in or out: everything animates. Captions too. Minimal, clean, high-quality YouTube feel, not AI-generic.
6. **Progress diagram:** a premium version of the contest slide's scoring bar (Why change, Why now, Why DDN, plus the Ask), showing where we are.
7. **Logos are wanted**, but **Sky and DDN logos are already on the monitors** in the footage (Sky: IMG_3847/3848/3850; DDN: IMG_3851/3853/3854). Don't duplicate them, and don't cover those monitors. Logo graphics only for Netflix, YouTube, Canal+, Starz and Blockbuster, plus DDN on the end card. No DDN logo on the pilot card.
8. **Fonts:** exact DDN look. Articulat CF is unlicensed here, so use the closest measured free match (see `research/FONT_MATCH.md`), plus real Geist Mono.
9. **Background blur:** high-quality depth-aware shallow DOF (see `research/BLUR.md`). Keep the speaker, chairs, sign and phone timer sharp, and keep the monitor logos recognisable.
10. **Music:** energetic like a pitch video, but not crazy (about 116–124 BPM, driving, confident, no drops). Not piano-led, nothing synth-generic. Use real licensed Yamaha instruments where they exist (bass, kick/toms, TX81Z, nylon guitar), plus high-quality licensed alternatives for the rest. No vocals; imitate no one.
11. **SFX must be smooth and DAMPENED, felt not heard, and NEVER synthesised or generic; only professionally recorded, licensed SFX (Sonniss GDC bundle, Pixabay, Freesound CC0, BigSoundBank):** max 5 (timer click, 3 airy whooshes on key graphics, soft end-card chime), slow attacks, low-passed, about −26 to −30 dB below dialogue peaks. No section thumps; the music marks the sections.
12. **Lighting:** IMG_3849 has the lights going off at about 27 s, so avoid it. Flag any other light changes.
13. Draft for the user to review before the final render.

## Paused 19 Nov (user asked to stop for usage). Notes for when we resume
14. **Blur around the speaker during movement is NOT acceptable yet.** The user saw a "weird outline" around them when moving, very obvious. The edge has to be spot on.
    - **Next step:** research and test better matting / segmentation before using blur in the final:
      - video matting with temporal consistency, e.g. MatAnyone, a SAM 2 video-propagated mask refined by a matting model, BiRefNet / BiRefNet-matting, RobustVideoMatting at higher resolution
      - edge-aware refinement (guided filter / deep image matting on the trimap band)
      - motion-aware handling (expand the sharp zone during fast motion, or fade the blur strength down during movement)
      - a fallback that blurs only static segments
    - Test on the hook roll-in (IMG_3845 207.3–217.8) and judge it frame by frame at 100% zoom before showing the user.
15. **Pacing reference:** do NOT use DDN's interview videos as the reference for the flow. The target is a strong, high-quality **pitch** video (polished YouTube Short / product-pitch energy, calm enough for professionals).
16. **Work state when paused:**
    - Done: picks (`edit/picks.json`), cut list (`edit/edl_v2.json`), rough cut (`edit/rough_v1.mp4`), voice (`edit/voice_v1.wav`), captions (`edit/captions_v2.json` + .srt), grade (`edit/grade/grade.json`), shot and graphics timing (`edit/SHOTPLAN.json`), TAKES.md, DEVIATIONS.md and FACTS.md (in `deliverables/`).
    - Interrupted: plate render (`tools/render_plates.py`), the final graphics composition (PitchFinal), and the music v2 composition.
17. **Music v4 (user, 19 Nov):** soft, **curious and speculative** (an inquisitive "what if" feel that resolves into confidence by Why DDN and the ask). SFX smooth and premium.
18. **Graphics (user, 19 Nov):** must not obstruct too much (compact, to the side, slim progress bar). **Prism effect clearly present but in DDN's palette** (red, orange to wine logo ring, a hint of steel blue), not a generic rainbow.
19. **Progress indicator = the contest slide's scoring bar visual** (labelled segments: Why change, Why now, Why DDN, The ask; the active one solid DDN red, previous pale rose). It is shown clearly for about 1.5–2 s at each section change, then condenses to a slim top bar. It shows "which part I'm talking about".
20. **Process:** after each draft, review it myself (frames, timing, audio) and iterate before showing the user, and show the user progress along the way.
