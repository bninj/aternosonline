# Articulat CF: licensed routes and the closest free match

Date: 2026-11-18. Rules followed: no Articulat font files were downloaded, extracted or saved. The ddn.com public homepage was opened in headless Chrome. Its Adobe Fonts kit loaded in the browser the normal way, and we took screenshots of the page's own text strings only. The reference images in `brand/fonts/match/ref/` are screenshots, not font data. We did not trace the glyphs or build a font from them. They exist only for the measurements below.

---

## 1. Legitimate ways to get Articulat CF

| Route | What it gives | Can it be used in video? | Source |
|---|---|---|---|
| **Adobe Fonts, paid plan** | All 20 styles (Thin → Heavy, each with an oblique). The page says the family is in the **full library only**: its data marks every style `library_availability: {full: true, trial: false}`, so the free tier does not include it. The full library comes with Creative Cloud plans (single app or All Apps) and other paid plans, which Adobe's subscription-requirements page lists as paid Adobe Express, Acrobat Pro/Standard and others. The page says "Subscribe to Creative Cloud to use more fonts". | **Yes.** Adobe's licensing FAQ answers "Can I use the fonts in the production of film or video content? **Yes**", and this covers in-house, commercial and broadcast use and online distribution (YouTube/Vimeo). It needs an active subscription. Adobe Fonts sync to desktop apps such as After Effects and Premiere and do not give you font files. **They cannot be loaded into our Remotion/headless-Chrome pipeline.** Adobe's web kits are for websites, not for render servers. | https://fonts.adobe.com/fonts/articulat-cf · https://helpx.adobe.com/fonts/using/font-licensing.html · https://helpx.adobe.com/fonts/system-subscription-requirements.html (Adobe help pages returned 403 to our fetcher, so the FAQ wording above comes from search excerpts of those pages and their regional copies, e.g. https://helpx.adobe.com/au/fonts/web/font-licensing/font-licensing.html) |
| **Free Adobe account / Adobe Express free** | **No.** The free tier only gives the basic library (about 5,500 fonts). Articulat is marked `trial: false`, meaning it is not in the free library. | n/a | same as above |
| **Connary Fagen trial licence** | No trial files can be downloaded. The licensing page says: "If you need to test fonts for internal mockups or client pitches, **contact us to arrange a trial license**." | Only for **internal mockups or pitches**. It does not cover final or published video. | https://connary.com/licensing/ |
| **Buy from Connary Fagen** | Desktop licence: price tiers by number of users (1/5/20/50/100/100+). Single styles from **$35.99**; **Articulat Essentials** (4 styles) from **$84.99**; **full family** (20 styles) from **$381.49**. Prices are "from", meaning the 1-user tier. Resellers: Fontspring lists single styles from $44.99 and the family from $375. MyFonts and YouWorkForThem also sell it. | **Unclear, so ask first.** The desktop EULA only mentions static images, documents and print, and says nothing about video or broadcast. The licensing page says "less common uses include on-air broadcasts… contact us" about an **extended licence**. The EULA also **bans installing the font on any server** or digital-asset system, and allows one device per authorised *employee*. A cloud render box would break those terms, so a Remotion server render needs written permission or an extended/app licence. | https://connary.com/articulat.html · https://connary.com/licensing/desktop/ · https://www.fontspring.com/fonts/connary-fagen-type-design/articulat-cf |

**Practical route if Articulat is required:** (a) a designer with Creative Cloud sets type in After Effects for titles and lower-thirds (clearly covered); or (b) email Connary Fagen (connary.com/contact) asking for a desktop **plus video/extended** licence that names the Remotion render machine. Until then, use the free match below.

**Weight-name gotcha, important when we get real files.** Adobe serves Articulat to the web with weights shifted by one step. ddn.com's CSS `font-weight` maps to these styles:

| ddn.com CSS weight | Adobe style actually served (fvd) |
|---|---|
| 400 | **Normal** (n4) |
| 500 | **Regular** (n5) |
| 600 | **Medium** (n6) |
| 700 | **Demi Bold** (n7) |

Bold (n8), Extra Bold and Heavy are not used on the site. This is the "weight discrepancy" reported in Adobe's community forum. So ddn.com's 700 headline is **Demi Bold**, and its body text is the **Normal** style, which is lighter than desktop "Regular".

---

## 2. Closest free lookalike, chosen by measurement

### Method
1. **Reference.** We loaded ddn.com in headless Chrome (Playwright, `/usr/bin/google-chrome`) and confirmed that `articulat-cf` 400/500/600/700 were loaded. We placed the page's own strings in an overlay at 120 px, black on white, `letter-spacing: 0`, `font-synthesis: none`, and captured them at each of the 4 CSS weights. The strings were "DDN Powers the World's AI Data", "AI That Gets to ROI Faster", "We'll handle the complexity.", "Built for organizations building AI's future", "Advanced data intelligence platform", "8 out of 10 of the worlds' leading automotive companies trust DDN.", "From NVIDIA's Selene to xAI's Colossus" and "10x". The site has no "%" glyph, and "AI AT SCALE" is set in Geist Mono, not Articulat.
2. **Candidates.** We rendered 41 families with the same Chrome rasteriser and the same strings at 400/500/600/700. From Google Fonts (all SIL OFL): Inter Tight, Inter, Figtree, Plus Jakarta Sans, Manrope, Albert Sans, Outfit, Urbanist, Onest, Geist, Instrument Sans, Hanken Grotesk, DM Sans, Public Sans, Schibsted Grotesk, Work Sans, Red Hat Display/Text, Golos Text, Rethink Sans, Funnel Sans, Host Grotesk, Wix Madefor Display, Archivo, Be Vietnam Pro, Sora, Mona Sans, Hubot Sans, Poppins, Lexend, Karla, Gantari, Readex Pro and Arimo. From Fontshare (ITF Free Font Licence): General Sans, Satoshi, Switzer, Supreme, Cabinet Grotesk, Author and Synonym.
3. **Normalisation.** Each candidate was scaled so that its cap height (measured on the "1" in "10x") equals Articulat's (84 px at a 120 px font size, i.e. 0.70 em), and aligned on the baseline.
4. **Metrics.** We cut out each glyph using Chrome's per-character boxes and measured:
   - binarised **IoU** (overlap; higher is better);
   - symmetric **chamfer** edge distance in px (lower is better);
   - **x-height/cap-height ratio** relative to Articulat (Articulat's is 62/84 = 0.738);
   - mean glyph-width log error;
   - **ink ratio** (stroke weight);
   - **set width** (whole-line width relative to Articulat, which tells us the tracking needed).

   Composite score = (1−IoU)·100 + 2·chamfer + 40·|ln xh| + 20·glyph-width error + 20·|ln ink|. Lower is better.
5. **Round 1:** all 41 families at the 4 fixed weights.
6. **Round 2:** the top 8 as variable fonts, swept from weight 340 to 760 in steps of 20, to find the weight whose stroke matches each Articulat weight.
7. **Video check:** the "ALEX BOUZA[RI]" lower-third name (Articulat Medium caps) cropped from `reference/frames/In-Conversation-CEO-01-Vertical/f_005.jpg`.

### Results (round 2, best weight per family; full tables in `brand/fonts/match/round2_finetune_ranking.txt`)

| Articulat (ddn CSS weight → style) | 1st | 2nd | 3rd | **Inter Tight** |
|---|---|---|---|---|
| 400 → Normal | Manrope 380 (score 26.8, IoU .787) | Onest 340 (29.0) | **Inter Tight 340 (30.0, IoU .741, ink 1.00)** | rank 3 |
| 500 → Regular | Funnel Sans 340 (24.0) | Onest 360 (24.2) | Manrope 440 (24.7) | 380: 26.5, IoU .777 (rank 5) |
| 600 → Medium | Funnel Sans 440 (18.9) | Onest 480 (19.5) | **Inter Tight 480 (20.5, IoU .833)** | rank 3 |
| 700 → Demi Bold | Funnel Sans 620 (15.2, IoU .877) | **Inter Tight 620 (15.2, IoU .877, chamfer .86 best)** | Onest 620 (17.3) | rank 2 (tie) |
| Video caps "ALEX BOUZA" (IoU after width-normalising) | Inter 560 (.818) | Onest 580 (.805) | Mona Sans 580 (.794) | 540: .773 |

Mean composite over the 4 weights: Onest 22.5, Funnel Sans 22.6, Inter Tight 23.0, Manrope 23.1, Mona Sans 24.0, Instrument Sans 27.5, Geist 30.4. In round 1, the Fontshare fonts (General Sans, Satoshi, Switzer, Supreme…), Figtree, Plus Jakarta Sans, Outfit, Urbanist and the rest all scored lower; see `round1_ranking.txt`. The top four are within about 3% of each other, so the per-glyph check below decides between them.

**Per-glyph check** (`glyphs_500.png`, `glyphs_700.png`). Articulat's tells are:
- two-storey **a** with a straight stem;
- **t** with a flat, cut top;
- **y** with a straight diagonal tail;
- **R** with a straight leg;
- **G** with a bar and no spur;
- **1** with a flag and *no* base;
- round **0** and **8**;
- comma-shaped curly **'** apostrophe;
- round **.** full stop.

How each contender fits:
- **Onest**: its **y** has a curly hooked tail and its **t** is lighter, so it fails on a common letter.
- **Funnel Sans**: its **1** has a foot serif and it runs heavy at text sizes (ink +17% at Normal).
- **Manrope**: more geometric (rounder **e**/**c**, narrow **0**). It is the best lightweight body match but has the weakest heavy weights.
- **Inter Tight**: matches a/t/y/R/1/0/8/D closely. It has the best chamfer at Bold and an exact ink match at Normal and Bold. Its only visible differences are a straight wedge apostrophe (no stylistic set gives a curly one; ss03/cv01-cv10 tested) and a slightly narrower set width, which tracking fixes.

### Recommendation: **Inter Tight** (variable, one family for every weight)

- **Licence:** SIL Open Font License 1.1. Commercial use, video and broadcast are fine, and it can be embedded and installed on render servers. You may not sell the font by itself. Copyright 2022 The Inter Project Authors.
- **Files:** `brand/fonts/InterTight/InterTight[wght].ttf` (wght axis 100–900), `brand/fonts/InterTight/InterTight-Italic[wght].ttf`, and `brand/fonts/InterTight/OFL.txt`. Source: https://github.com/google/fonts/tree/main/ofl/intertight (upstream https://github.com/rsms/inter-tight).
- **Runner-up for light body text:** Manrope (`brand/fonts/Manrope/Manrope[wght].ttf` + `OFL.txt`, OFL). Use it only if a single paragraph style must look closer to Articulat Normal and mixing families is acceptable.

**Settings to match Articulat.** Inter Tight's cap height is 0.7275 em; Articulat's is 0.70 em.

| Use (style-guide name) | Articulat style | Inter Tight `font-weight` | `font-size` | Extra `letter-spacing` (add to any tracking in the spec) |
|---|---|---|---|---|
| Body / subtitles / captions ("Regular" on ddn.com = CSS 400) | Normal | **340** | ×0.966 | **+0.014em** |
| Desktop "Regular" (e.g. AE files labelled Regular) | Regular (n5) | **380** | ×0.966 | **+0.022em** |
| "Medium": names, title cards, sub-heads | Medium (n6) / CSS 600 | **480** | ×0.966 | **+0.025em** |
| "Bold" headlines (ddn.com h1/h2 = CSS 700) | Demi Bold (n7) | **620** | ×0.966 | **+0.023em** |
| Lower-third name, CAPS (measured on video frame) | Medium caps | **540** | ×0.966 | **+0.05em** (includes the tracking DDN's editor applied) |

- Keep DDN's own tracking on top of these values. For example, the ddn.com h1 is −3.12 px at 104 px, i.e. −0.03em, so for Inter Tight use −0.03 + 0.023 ≈ **−0.007em**.
- For the "10x"-style numerals use `font-feature-settings: "tnum"` when you need tabular figures; Inter Tight supports `tnum`.
- The x-height relative to cap height is within 1.2% of Articulat (Inter Tight 0.750 vs Articulat 0.738), so no further vertical adjustment is needed.

### Plugging into Remotion (do **not** edit here; for the agent working on `tools/remotion/`)
`tools/remotion/src/ddn/fonts.ts` currently loads static `inter-tight-latin-{400,500,600}-normal.woff2`. Those static files cannot give the in-between weights 340/380/480/620/540, and anything heavier than 600 gets either 600 or a synthesised bold. Suggested change:

1. Copy `brand/fonts/InterTight/InterTight[wght].ttf` to `tools/remotion/public/fonts/InterTight-VF.ttf`, and copy `OFL.txt` next to it.
2. Replace `INTER_TIGHT_FILES` with one variable face:
   ```ts
   loadFont({family: 'Inter Tight', url: staticFile('fonts/InterTight-VF.ttf'), weight: '100 900', display: 'block'});
   ```
3. Add the tokens. These apply only when the fallback is active; if real Articulat files appear, use the weights 400/500/600/700 with 0 extra tracking and size ×1.
   ```ts
   export const DDN_TYPE = {
     regular: {fontWeight: 340, letterSpacing: '0.014em', sizeScale: 0.966},
     regularDesktop: {fontWeight: 380, letterSpacing: '0.022em', sizeScale: 0.966},
     medium: {fontWeight: 480, letterSpacing: '0.025em', sizeScale: 0.966},
     bold: {fontWeight: 620, letterSpacing: '0.023em', sizeScale: 0.966},
     capsName: {fontWeight: 540, letterSpacing: '0.05em', sizeScale: 0.966},
   } as const;
   ```
4. Update the `document.fonts.check` probes to use the new weights, e.g. `620 78px "Inter Tight"`.

Also note on that module's Articulat slots: it maps `ArticulatCF-Regular.otf` → 400. That is fine for desktop files. But ddn.com's "400" is actually the **Normal** style, so to reproduce the website's body weight you would need `ArticulatCF-Normal.otf` at 400.

---

## Files
- **Comparison sheet:** `brand/fonts/match/COMPARISON_SHEET.png`. It collects `stack_700_h1.png`, `stack_600_h5.png`, `stack_500_h4.png`, `stack_400_p2_fine.png`, `glyphs_500.png` and `glyphs_700.png`. Also `stack_700_h2.png`, `stack_400_p2.png` and the overlay `overlay_700_h2.png` (red = Articulat, blue = candidate).
- **Scores:**
  - `brand/fonts/match/round1_ranking.txt` (41 families);
  - `round2_finetune_ranking.txt` (weight sweep);
  - `video_caps_check.txt`;
  - raw `scores.json`, `scores2.json`, `finetune_summary.json`.
- **Reproduce:** `brand/fonts/match/scripts/`.
  - Render: `node render.js ref|cand`, `render2.js cand` and `render3.js cand` (Playwright from `/opt/node-tools`). These scripts expect `strings.json` in the working directory, and `render2.js`/`render3.js` load the variable TTFs from a scratch folder (`dl/`), so check the paths before re-running.
  - Score with `tools/venv/bin/python score.py` / `score2.py`, then run `rank.py` / `rank2.py`.
  - Sheets: `stack*.py`, `grid*.py`.
