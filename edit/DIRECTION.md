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
21. **v4 (after the user's draft v1 feedback):** cuts must be SNAPPY, with no dead space after lines (lead about 0.05 s, tail about 0.09 s; small extra breath only at section changes). Smoother cuts: J-cuts plus designed zoom-through seams at section changes, and snap-zoom accents on key words. More creative, polished, high-quality YouTube-style motion design: illustrative animated graphics (chip grid for 5% → 99%, data-flow lines, streaming tiles, voice waveform, Blockbuster greying out, DDN logo build), never obstructing. Edit = edl_v3.json / timeline_v4.json / SHOTPLAN_v4.json / captions_v3.json / voice_master_v3.wav. Total 74.2 s.
22. **Blur v2 (SAM 2.1 + ViTMatte) rejected:** still a visible "blob" around the speaker when moving. Replaced by a **motion-proof static far-background falloff**: no per-frame matte at his edge; a per-shot occupancy zone with a wide feather, and depth-graded blur on the far background only. Plus **smoother lighting**: highlight roll-off, de-haze for the DDN-monitor shots, a subtle soft "virtual key light" on the face (heavily smoothed), and a gentle vignette. Tool: tools/look_v4.py → edit/plates_look_v4/plate.mp4. Fallback: no blur, lighting polish only.
23. **User, 19 Nov:**
    - The Blockbuster logo **breaks/shatters** after it lands (before "Thank you").
    - Logos are **larger (about 1.5x) and transparent**: no opaque tiles; they float on frosted glass or over the footage with a soft shadow.
    - Subtitles are **slightly larger (+15–20%) and improved** (cleaner pill, a slightly heavier weight, one line).
24. **v5 (user, 19 Nov):**
    - Remove the hook's "AI chip / Waiting for data" card. Instead **highlight the real AI chair**: a precise glowing contour in DDN red plus a subtle spotlight, during the chair-alone opener and "Sorry I kept you waiting".
    - Overall **cleaner, more polished, "less but better"** pass: no empty caption pills, a consistent grid and margins, one graphic at a time, consistent type and colour.
25. **User, 19 Nov:**
    - **Name card: name only**, in DDN bracket style, after he turns to camera in the hook. The name text is still to come from the user.
    - **"If both improve, scale it"** was said on camera, per the user; it's not in the 16 uploaded clips. Clip numbering gaps: **IMG_3846 and IMG_3859 are missing** (3859 sits between the ask 3858 and the ending 3860). The user has been asked to upload them.
    - **No credits** wanted, so swap the CC BY Naked Drums for the CC0 Renoise Yamaha Stage Custom kick (and CC0 toms), so no attribution is needed.
26. **User, 19 Nov (with a screenshot):**
    - Name: **Eliud Awuah**; name card "[ ELIUD AWUAH ]".
    - **Caption bug:** "Sky, make me scared. Third," merged across a section, so captions must never span a sentence end, a cut or a section change.
    - **Logos bigger, ideally BEHIND the speaker** (depth layering with a person alpha only for segments 3, 13 and 18; fall back to large-beside if the edges aren't clean).
    - The user is looking for IMG_3859 ("If both improve, scale it") in Drive.
27. **v5 edit:** IMG_3859 is inserted (medium shot, "And if both improve, scale it.", source 5.69–7.99) after "before and after". 21 shots; voice 73.497 s; total 76.5 s. Files: edl_v4.json, timeline_v5.json, captions_v4.json, SHOTPLAN_v5.json, voice_master_v4.wav, grade/grade_v5.json, plates_look_v5/. The ask card gains "If both improve → scale it". Music: CC0-only kit (no credits).
28. **User rated the draft 8/10.** Fixes:
    - **Dwell time:** every text graphic stays for its reading time (0.33 s per word) + about 1 s, minimum about 2–2.5 s, never across a section change. The "Sky, make me scared" bubble enters on "Imagine asking" and holds to the seam.
    - **Chair highlight on "That's AI chips"** (2.95) for 1.5–2 s, fading in and out.
    - **Zooms:** subtle, but smoother (sine/expo in-out curves, face anchored, motion blur only on snap-zooms).
    - **Captions** moved up to about 72–76% of frame height, close to the speaker, and about 10% larger.
    - **Music 10–20% louder:** +1.3 dB in the mix (music-gain −6.7).
29. **Caption placement (final rule):** DDN convention, in the lower third over the lap/lower torso (about 80–84% of frame height). Never over the face, chin, mouth or upper chest, logos, graphics, monitors or the AI sign. A fixed position per shot (changes only at cuts), shifted horizontally into clean space if needed, and verified frame by frame.
30. **v6 = FINAL, in 4K (user feedback on v5):**
    - **Subtitles:** no pill; clean bottom-centre text with a soft "layer" (shadow/feathered gradient), larger; subtle emphasis.
    - **Bubble:** types word-synced.
    - **Stopwatch:** a realistic one starting at 0; never "1:30" (any total = the real length, 1:17).
    - **Zooms:** calmer, one slow push per shot, max 3 gentle snaps.
    - **Name super at the top-left:** "Eliud Awuah" / "T Level Placement Student".
    - **Arsenal crest "losing" gag** on "Arsenal lose", with no invented score.
    - **Canal+ left and Starz right** of him, large.
    - **The ask card holds longer.** "If both improve, scale it" is its own kinetic moment.
    - **From "So Sky":** only Blockbuster (larger, premium shatter).
    - **+0.75 s of real-footage rest after "Thank you"** (no freeze), end card 74.247–77.247.
    - **Music v7:** subtler and less generic; SFX dampened but satisfying.
    - **Output 3840x2160.**
31. **Zooms (user):** more dynamic, but never like a cut. Smooth eased punch-ins (0.4–0.6 s, 5–7%) at key moments; slow pushes of 4–6% per shot; a gentle "settle" move after same-spot cuts; no instant scale jumps except at real cuts; verified with a per-frame scale-curve plot. **Arsenal crest large** (about 30–35% of frame height).
