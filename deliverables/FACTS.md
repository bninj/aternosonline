# FACTS.md: every on-screen claim, its source, and where it appears

Status: **sources verified 18 Nov 2026**; on-screen times are from the final cut (v6, 77.2 s).
Rule: only these claims may appear on screen. No other statistics or claims.

**Logo policy (updated by the user, 18 Nov):** logos are now used. A company's official logo appears when it is named (Sky, Netflix, YouTube, Canal+, Starz), and the DDN logo appears on the end card. **No DDN logo on the 30 day pilot card**, because the pilot is the user's own proposal, not a DDN offer. Source tags stay as text. Logo file sources are in `brand/logos/SOURCES.md`.

| # | On-screen text (exact) | Spoken line | Source | Verified? | Appears at |
|---|---|---|---|---|---|
| 1 | Falling line graphic, "12%", tag "Ofcom Media Nations 2026" | "Ofcom says traditional TV viewing fell twelve percent in a year…" | Ofcom, *Media Nations UK 2026* (published 29 Jul 2026): linear TV viewing fell 12% in 2025, to 1 hour 51 minutes a day | ✅ Via [VideoWeek's report on the release](https://videoweek.com/2026/07/29/younger-audiences-reaching-saturation-in-streaming-finds-ofcom/): "linear TV… (12 percent)… reaching 1 hour and 51 minutes per day". The Ofcom PDF itself blocked automated download, so I relied on trade-press quotes of it. | 0:10.9–0:16.0 (12% lands 0:13.2) |
| 2 | "Netflix", "YouTube" (name and official logo) | "Netflix and YouTube know what you want to watch." | Not a statistic: names only | n/a | 0:16.5–0:19.3 (logos behind the speaker) |
| 3 | Chat bubble: "Something for me and the kids, under two hours." | "Imagine asking…" | Illustrative example, the user's own. Spoken context: Sky Q voice search, launched 22 Mar 2017 ([Sky Group](https://skygroup.sky/article/sky-q-unveils-voice-search-and-new-features-making-it-easier-to-find-and-watch-movies-shows-and-sports)) | ✅ | 0:28.0–0:32.6 (Listening pill, then the bubble types 'Sky, make me scared.') |
| 4 | Card "5%", tag "Cast AI, enterprise average" | "Cast AI found enterprise chips average about five percent use." | Cast AI, *2026 State of Kubernetes Optimization Report*: average GPU utilisation about 5% across ~23,000 clusters ([report](https://cast.ai/reports/state-of-kubernetes-optimization/), [press release](https://cast.ai/press-release/2026-state-of-kubernetes-optimization-report/)) | ✅ | 0:36.1–0:40.5 (5% lands 0:39.5; label 'AVERAGE USE', tag 'Cast AI, enterprise average') |
| 5 | BUSY gauge rising towards 99%, tag "per DDN" | "DDN says customers reach up to ninety nine percent busy…" | DDN blog, *Infinia 2.4: The Foundation for Higher GPU Utilization* ([link](https://www.ddn.com/blog/infinia-2-4-launch-for-gpu-utilization-production-ai/)): "drive GPU utilization as high as 99%" | ✅ | 0:49.0–0:51.8 (99% lands 0:50.1; label 'BUSY, UP TO', tag 'per DDN') |
| 6 | Card "99% busy, 75% lower cost per token", tag "per DDN" | "…and cut cost per token by seventy five percent." | Same DDN blog: "cut cost per token by 75%" | ✅ (see note) | 0:51.8–0:54.4 (75% lands 0:53.2, tag 'per DDN') |
| 7 | "Canal Plus", "Starz" (name and official logo) | "DDN already works with media companies like Canal Plus and Starz." | DDN media page ([ddn.com/solutions/media-companies](https://www.ddn.com/solutions/media-companies/)) lists both as customers. Wording is "works with", which does not imply AI work. | ✅ | 0:56.6–0:58.6 (Canal+ left, Starz right) |
| 8 | Two-item card "How busy the chips are" / "What each answer costs" | The ask | The user's own pilot proposal, **not a DDN standard**. No DDN logo or claim attached. | n/a | 1:01.0–1:07.5 ('30 day pilot' tag and the two-metric card); 'If both improve → scale it' 1:07.5–1:10.0 |
| 9 | "Blockbuster" | "Sky, don't be the next Blockbuster." | Rhetorical, not a claim | n/a | 1:11.8–1:12.7 (logo lands, then shatters) |
| 10 | End card "Thanks for watching." | none | Closing card, no claim, no logo | n/a | 1:14.2–1:17.2 (end card) |

## Notes for a DDN-employee audience
- **The 75% figure:** DDN's earlier KV-cache material says it comes from cutting *input* token costs ("up to 75%"). The 2.4 blog states it more broadly. Our wording ("per DDN", "DDN says") attributes it correctly. Judges know the background, so the attribution matters.
- **The 99% figure is an "up to" claim.** The script says "up to"; the gauge rises *towards* 99% and is tagged "per DDN".
- **Canal+:** DDN lists Canal+ by logo only (no public case study). The Starz case study dates from 2013. "Works with" is accurate; anything stronger would not be.
- **Ofcom wording:** do not use "steepest ever", as instructed. The coverage itself says "steepest annual decline… in recent years", so "ever" would be wrong anyway.

## Other on-screen elements (not claims)
- Arsenal crest (fair use, internal contest entry) on 'Arsenal lose', with a droop and grey-out gag. **No score or result is shown.**
- Stopwatch: counts elapsed time from the first word; it shows no total.
- Name super: 'Eliud Awuah', 'T Level Placement Student'.
- Progress bar: Why change, Why now, Why DDN, The ask (section labels only).
- Logos: Netflix, YouTube, Canal+, Starz, Blockbuster and Arsenal on screen (no logo on the end card). Sky and DDN also appear on monitors in the footage. Sources: brand/logos/SOURCES.md.
