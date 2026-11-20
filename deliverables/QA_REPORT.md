# QA report: "Why DDN" pitch, final (v6)

Entrant: Eliud Awuah, T Level Placement Student. Customer example: Sky. Final file: `output/final/final_1080.mp4` (1920x1080, 30 fps, H.264 High, 77.247 s, 2317 frames). The 4K version was dropped at Eliud's request.

## The brief's 7 checks
| # | Check | Result |
|---|---|---|
| 1 | Total duration ≤ 90 s | ✅ **77.2 s** (1:17). The brief's target was 85; it's shorter because the takes were tightened for pace, and nothing was cut from the script. |
| 2 | No cut lands mid-sentence | ✅ Every one of the 21 shots starts and ends on a sentence boundary. The automated cut QA (re-transcribing every join) **passed with 0 failures**: no clipped or doubled words, no hidden restarts. |
| 3 | Every number on screen matches the fact table and the audio | ✅ 12% (Ofcom), 5% (Cast AI, "enterprise average"), 99% ("busy, up to", per DDN), 75% (lower cost per token, per DDN). Each was confirmed in the audio by a second transcription pass. Each lands within 1 frame of the spoken word. See FACTS.md. |
| 4 | Subtitles match the spoken audio exactly, spelling checked | ✅ Captions are built from the edited voice track (51 phrases), with transcription errors corrected by hand ("arcs" → "ask", "Starz", a phantom duplicate "Sky" removed). No phrase crosses a sentence end or a section change. See captions.srt and DEVIATIONS.md. |
| 5 | Sound off: the visuals tell the story | ✅ The progress bar (Why change → Why now → Why DDN → The ask), captions and number graphics carry the argument without audio. |
| 6 | Audio: no clipping, music never masks the voice | ✅ −15.3 LUFS integrated, peak −4.0 dBFS, loudness range 2.9 LU. Voice mastered to −16 LUFS; music about 20 dB under speech and ducked while he talks; 5 dampened recorded SFX. |
| 7 | No dashes in on-screen text | ✅ 0 dashes in captions; the arrows are drawn shapes, not characters. |

## Other checks
- **Graphics never cover the face, the Sky/DDN monitors or the AI sign:** checked per shot against face and keep-out boxes. Logos behind the speaker tuck by at most 3% of their width.
- **Flicker:** a full frame-difference scan found none; the only large frame changes are the 21 planned cuts.
- **Camera:** every zoom is an eased move. A per-frame scale-curve check shows no jumps except at cuts.
- **Colour:** per-shot exposure and white-balance match, de-haze on the DDN-monitor spot, a soft key light, and a motion-proof background falloff (no per-frame matte at the speaker's edge).
- **Licences:** the music and SFX are CC0 only (no credits needed); see MUSIC.md. Logos are official artwork, with sources in brand/logos/SOURCES.md. The Arsenal crest is fair use for this internal entry, so check the rights before any public use.
- **Fonts:** Inter Tight (closest measured match to DDN's Articulat CF) and Geist Mono, both OFL.

## Known limits
- Delivered at 1080p, downscaled from the 4K iPhone source, so all framings, including punch-ins, are fully sharp.
- "30 day pilot" and the two metric labels appear in the graphics only; they weren't spoken (approved by Eliud). "If both improve, scale it" was recorded and is in the cut (IMG_3859).
- The sign reads "AI" (no "waiting for data", no flip). The video ends on a "Thanks for watching." card (no logo), with the music resolving there.
