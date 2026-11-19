# DDN Motion-Design Style Guide (reverse-engineered)

Compiled 2026-11-18 from ddn.com HTML/CSS, the official DDN brand-assets page, and 26 videos hosted on ddn.com (2024-07 to 2026-10). Every spec below comes from a frame measurement unless it is marked **(est.)**.

Target: iPhone 12 talking head, 3840x2160 @ 30 fps (deliver 4K or 1080p). Every 1080p value doubles for 2160p.

---

## 0. Sources and what was obtainable

| Source | Result |
|---|---|
| ddn.com home + 20 CSS files | Downloaded to `reference/ddn_home.html` and `reference/css/` (merged as `reference/theme.css`). |
| Brand page `ddn.com/company/brand-assets/` | **Official palette found.** Logos (SVG) downloaded to `brand/`. Contact for the full brand book: brand@ddn.com (it is not public). |
| YouTube `@DDNintelligence` | The channel listing worked (titles and view counts below), but **video downloads were blocked**: googlevideo returned 403, then YouTube showed "Sign in to confirm you're not a bot". Only thumbnails were fetched (`reference/yt_thumbs/`). |
| WordPress media library (`/wp-json/wp/v2/media?media_type=video`) | **75 self-hosted DDN videos listed. 26 downloaded** to `reference/videos/`, covering the main brand campaigns and the talking-head series. These are the original masters DDN publishes, at better quality than YouTube re-encodes. |
| Vimeo / Wistia / Vidyard | No embeds on 172 crawled ddn.com pages. All other embeds are YouTube. |
| LinkedIn | Blocked by the proxy (403). The LinkedIn-format masters (1080x1350) are on ddn.com and were downloaded anyway. |

### Most relevant downloaded videos (ranked for a talking-head use case)

| File (`reference/videos/`) | Date | Format | What it is |
|---|---|---|---|
| `02-DDN_12102024_video_li_InConversationPaul01_03_1080x1350-Sub.mp4` | Jan 2025 | 1080x1350, 30p, 93 s | **"In Conversation with Paul Bloch"**: the reference talking-head template |
| `02-DDN_12122024_video_li_InConversationSven02_02_1080x1350.mp4` | Jan 2025 | 1080x1350, 30p, 95 s | Same series, CTO |
| `In-Conversation-CEO-01-Vertical.mp4`, `02-Origin-Story-In-Conversation-CEO-03-For-Web.mp4` | Nov–Dec 2024 | 1080x1920, 30p | Same series, CEO/CMO, vertical |
| `ddn-sepd-wrap-video-1920x1080-1.mp4` | **Jul 2026 (newest)** | 1920x1080, 30p, 66 s | Partner Day event wrap shot on iPhone. **Newest graphics system, and the closest match to your footage** |
| `GTC_DDN-Company-Commercial.mp4` | May 2025 | 960x540, 29.97p, 31 s | Brand sizzle ("Welcome to the future with DDN") |
| `Infinai_Teaser_Voice-Option-1.mp4` | Dec 2024 | 1920x1080, 23.976p, 28 s | "Beyond Artificial" launch teaser |
| `DDN-Beyond-Artificial-Half-Frame-Edit.mp4` | Dec 2024 | 1920x1080, 30p, 16 s | Split-screen "BEYOND ___" campaign |
| `DDN_040825_video_li_GoogleAICloudNirvana_Partnership-Page_1080x1350.mp4` | Apr 2025 | 1080x1350, 25p, 60 s | Product explainer with stat callouts |
| `homepage-video.mp4` | Apr 2025 | 720x900, 30p, 68 s | Explainer ("Data Revolution:") |
| Loops: `vortex-bg-…`, `ddn-header-loop-generic-…`, `ddn-ai-factories-lp-*`, `Hero_01-r2-1`, `sphere`, `after-dark-loop`, `gartner-…` | 2024–2026 | various | Website background plates |
| `DDN-Virtual-Classroom-Promo-SHORT-1.2.mp4` | Sep 2024 | 1080p, 144 s | **Legacy/low-craft. Do not imitate.** |

### YouTube channel (metadata only; video data was blocked)
Recent uploads include "DDN: Behind Every AI Breakthrough" (5AmSgjhq-JU, 143 views), "DDN 2025 Year in Review" (cxcaci1Yggw, 168), "DDN AI400X3 Series" (YIi2fqlH3iQ, 896), "Run Your AI Factory at Full Speed" (JZTaTd1BCVA, 2.0k), "What is the DDN Data Intelligence Platform?" (Pfy0lSe-Gso, 1.2k), "Meet DDN Infinia" (YDBPbUWdV4c, 1.5k), and ISC 2026 / AI Data Summit 2026 keynotes. View counts are low (typically 50–2,000), and yt-dlp's flat listing did not return upload dates. The 2026 thumbnail system is documented in section 4.9 from `reference/frames/yt_thumbs_montage.jpg`.

---

## 1. Colour palette

### 1.1 Official brand colours (from ddn.com/company/brand-assets)
| Name | Hex | Use in motion |
|---|---|---|
| **Brand Red** | `#ED2738` | Accent, highlights, logo mark |
| **Deep Red** | `#CB343B` | Name-tag fill, CTA, web primary (`#cb343b` is the most-used colour in the theme CSS) |
| **Wine** | `#7D2D3F` | Gradient end, dark panels |
| Terra | `#D98878` | Warm secondary, soft gradient stops |
| **DDN Black** | `#201E1E` | Wordmark, dark backgrounds (not pure black) |
| **Warm Black** | `#402022` | Dark gradient partner of DDN Black |
| Brown | `#77494D` | Mid-tone in wine gradients |
| Warm Gray | `#D8D2CB` | Light neutral |
| Deep Blue | `#374967` | Cool counterpoint (2026 gradients) |
| Steel Blue | `#7594B2` | Cool secondary |
| Light Blue | `#BDD6E7` | Cool tint |
| Cool Gray | `#F0F0F0` | Light backgrounds (the 2026 outro uses `#E7E7E7`) |

### 1.2 Logo-mark colours (sampled from `brand/favicon.svg` render)
Orange `#FE7500` → Red-orange `#F9502E` → Brand Red `#ED2738` → Deep Red `#CB343B` → Wine `#7D2D3E` → shadow `#3F1F21`. The ring is a 3D-shaded torus. Lit from the lower left, it runs orange to red, and on the upper right it runs wine into dark.

### 1.3 Gradients actually used
| Name | Definition | Seen in |
|---|---|---|
| **Fire** (2024–25 campaign) | linear 90°: `#C8212B` → `#DE571D` → `#F5930E` | Beyond Artificial, GTC commercial (`frames/DDN-Beyond-Artificial-Half-Frame-Edit/f_002.jpg`) |
| Web fire button | `linear-gradient(98deg,#F04E23 5%,#D71612 100%)` | theme.css |
| **Ember dark** (web CTA, animated) | `linear-gradient(var(--angle),#201E1E,#402022)` + `linear-gradient(angle+180°,#7D2D3F,#402022)`, `background-blend-mode:hard-light`; `--angle` rotates 0→360° in **8 s linear, infinite** | theme.css `.animated-cta-banner` |
| Wine fade | `linear-gradient(90deg,#CB343B 0.8%, rgba(125,45,63,.4) 80%)` | theme.css |
| Dark wine card | `linear-gradient(135deg,#6B1F2A 0%,#4A1620 30%,#2D0F15 60%,#1A0A0D 100%)` | theme.css |
| Rust | `linear-gradient(113deg,#141516 35%,#3F1F12 92%)` | theme.css |
| Red glow | `radial-gradient(circle at 50% -30%, rgba(255,45,45,.35), rgba(255,45,45,.15) 30%, rgba(255,45,45,.05) 50%, transparent 80%)` | theme.css |
| **2026 Wine→Slate** (stat/number BG) | Diagonal, bottom-left `#3D1C23` → centre `#473B4F` → top/right `#4E556F`, plus **film grain** (~4% mono noise) | `frames/ddn-sepd-wrap-video-1920x1080-1/full_t23.jpg` |
| 2026 Red→Cream | diagonal `#980D20` / `#DA0F2C` → `#EF7F8B` → `#FEF7EF`, with pixel-block mosaic | `ddn-ai-factories-lp-hero-video` |
| Header loop | `#3F1306` → `#741E11` (rust), with thin circuit lines and a particle wave | `ddn-header-loop-generic` |
| Vortex | `#D55E26` (top) → `#9E3730` → `#7E312B` (bottom), with faint concentric dotted rings | `vortex-bg-1920x960-1` |

### 1.4 Live-footage grade targets (sampled)
- Interview wall (key-lit cream): `#F2E3CE` / `#F0DFCB`. Shadows sit at `#212025`, so they are **lifted** and never crushed to 0. Warm, creamy, low-contrast, soft-key look.
- Title-card tint: bottom ~45% overlaid with wine `#230E15`–`#24191F`, fading to clear at mid-frame (see 4.1).
- 2026 iPhone event footage is left close to native iPhone colour: slightly warm, no heavy LUT, no added letterbox.

---

## 2. Typography

| Role | DDN font | Source | Free fallback |
|---|---|---|---|
| Headlines, titles, 2026 captions, lower-third name | **Articulat CF** (`font-family: articulat-cf`): Medium/Bold for titles, Regular for subtitles | Adobe Fonts (Connary Fagen), included with Creative Cloud | **Inter Tight** / **Inter** (closest metrics). Alternatives: Figtree, Plus Jakarta Sans |
| Technical tags, role tag, 2024–25 captions, eyebrows | **Geist Mono** (`"Geist Mono", monospace`) | Free (Vercel, SIL OFL) on Google Fonts | Geist Mono itself. Older videos look like Roboto Mono |
| Campaign display caps ("BEYOND", "WELCOME") | Heavy grotesk caps, likely Articulat CF Bold/Heavy | — | Inter Tight ExtraBold, tracking −1% |

Web type rules from theme.css: weights 700/600/500/400; uppercase used 13×; letter-spacing between −0.02em and +0.32px; base sizes 48/36/24/16 px. Easing tokens: `cubic-bezier(.4,0,.2,1)` at 150 ms and 300 ms, `cubic-bezier(.25,.46,.45,.94)`, and `cubic-bezier(.25,.74,.22,.99)`. Keyframes: `fadeInUp` (opacity 0→1 with translateY 30 px→0), `angleFlow`, `marquee-scroll`, `lightSweepU`.

**The core type idea:** pair a clean grotesk (human, editorial) with monospace (data, machine). Brackets `[ ]`, a trailing underscore cursor `_`, and a colon after a mono label ("Data Revolution:") act as "terminal" punctuation.

---

## 3. Global motion and pacing numbers

| Metric | Talking-head series (In Conversation) | 2026 event wrap | Brand sizzle / teaser |
|---|---|---|---|
| Frame rate | 30p | 30p | 23.976p / 29.97p |
| Aspect | 4:5 (1080x1350), 9:16 | 16:9 | 16:9, plus 4:5 social cuts |
| Average shot length | **≈3.5 s** in A/B camera interviews (low-threshold detect on Paul: cuts at 7.8, 14.1, 17.5, 19.2, 21.6, 25.3, 28.4, 31.5, 32.7, 35.6 s); 4.7–5.8 s in walk-and-talk cuts | **2.3 s** (29 shots / 66 s) | **1.3–1.8 s** (GTC 1.29 s; Beyond half-frame 1.35 s; Infinai 1.76 s) |
| Explainers | — | — | 3.0–5.3 s (Nirvana 3.75 s, homepage 5.3 s) |
| Loudness | −18.8 to −19.2 LUFS (voice-led, music bed low) | −13.2 LUFS (music-forward) | −13.5 LUFS |
| Music tempo (crude autocorrelation, low confidence) | ~90 BPM | ~112 BPM | ~83/166 BPM (half/double-time) |
| Cutting rule | Two cameras on the interview (medium-wide plus close), with hard cuts on sentence boundaries | Hard cuts on caption changes | Cuts on the beat. The Beyond edit cuts every **16 frames (0.53 s)** like a metronome |

Overall easing feel: **smooth, confident, mostly ease-out**. Nothing bounces or overshoots, and there is no elastic motion. Graphics change by **hard cut** (captions, number holds) or by **typewriter build** (lower thirds, titles). Transitions between shots are almost always straight cuts. The few exceptions are listed in section 5.

Easing presets to use:
- `ddn-out` = `cubic-bezier(0.16, 1, 0.3, 1)` (expo-out) for rises and slide-ins **(est.)**
- `ddn-inout` = `cubic-bezier(0.65, 0, 0.35, 1)` for counters and long moves **(est.)**
- `ddn-ui` = `cubic-bezier(0.4, 0, 0.2, 1)` (the site's own token) for small UI fades
- Typewriter = linear/stepped (one character per N frames, no easing)

---

## 4. Graphic elements: buildable specs

Coordinates are given as % of frame plus px at **1920x1080 / 3840x2160**. Interview-series values were measured on 1080x1350 and converted by frame height.

### 4.1 "IN CONVERSATION" title card (series open), 2024–25
Reference: `reference/frames/paul_detail/full_t2.5.jpg`, `open_01.jpg`, `open_02.jpg`; `frames/In-Conversation-CEO-01-Vertical/sheet_01.jpg`

**Layers, bottom to top:**
1. Interview close-up, already rolling from frame 0 (cold open on the speaker's voice).
2. **Wine gradient tint**: linear from bottom (`#230E15` at 0.9 opacity) to clear at ~55% height, plus overall warm multiply. It deepens over the first 1 s.
3. **Giant outline word stack** "CON / VER / SATION": Articulat CF Medium caps, **outline only** (1.5 px @1080 / 3 px @2160, white @ 55–60% opacity, no fill). Cap height ≈ 16% of frame height (≈175 px @1080 / 350 px @2160). Line pitch ≈ 19% H. Left-aligned at x = −1% so it bleeds off the frame edges. The stack sits in the lower 55% of frame. It **drifts slowly** (≈1–2% of width over 3 s, linear) for parallax.
4. **Title block**, left-aligned at x = 12% (1080x1350 measure: x = 130/1080):
   - "IN" in small caps Articulat Regular (cap ≈ 1.6% H) + **"CONVERSATION"** in Articulat Medium caps (cap ≈ 3.7% H → ≈ 40 px cap ≈ 56 px font @1080, 112 px @2160).
   - Line 2: "WITH" (small) + **"PAUL BLOCH"** (same size as CONVERSATION).
   - Baseline of line 2 at ≈ 80% of frame height.

**Timing @30 fps** (measured on Paul):
| Frame | Event |
|---|---|
| 0 | Outline stack already visible, tint at ~50% |
| 39–45 | "IN CONVERSATION" **types on left→right** (≈2 characters per frame, i.e. 12 chars in 6 frames) |
| 48–57 | "WITH PAUL BLOCH" types on (≈1.5 chars/frame) |
| 99–114 | **Red/orange light-leak flash** over the whole frame (`#E8452B` → `#F7A35C`, screen blend, peak 70% at f105, ~15 frames) |
| 114–135 | Hold. Tint deepens to wine |
| 138–144 | **Vertical slice transition**: 4–6 vertical strips of the next shot (medium-wide) slide in, staggered left→right, each moving ±8% vertically, ~6 frames total. Title and outline exit with the strips |
| 144 | Clean on the wide shot, with the first caption already present |

Total title duration ≈ **4.8 s (144 f)**.

### 4.2 Bracket lower third (name super), 2024–25 signature
Reference: `reference/frames/paul_detail/full_t8.0.jpg`, `open_02.jpg` (frames 165–237); `frames/02-Origin-Story-In-Conversation-CEO-03-For-Web/sheet_01.jpg`

**Layout** (measured on 1080x1350 and converted to 16:9 by height):
- **Bracket name:** `[PAUL BLOCH]`. The brackets are thin vertical rules with short serifs (stroke ≈ 3 px @1080 / 6 px @2160, white) and are taller than the text (bracket height ≈ 1.6× cap height). Name in Articulat CF Medium caps, white, cap ≈ 3.1% H (font ≈ 46 px @1080 / 92 px @2160), tracking 0, with ~8 px inner padding to the brackets.
- **Role tag** directly under it, left edge aligned with the left bracket: a solid rectangle filled **Deep Red/Brand Red** (sampled `#CC2632`; use `#CB343B`), no radius, height ≈ 3.4% H (37 px @1080 / 74 px @2160). Text "President & Co-founder at DDN" in **Geist Mono Regular**, white, ≈ 2.2% H (24 px @1080 / 48 px @2160), 10 px side padding.
- **Position:** left edge x ≈ 16% W in 4:5. **For 16:9, place it at x = 8% W (154 px @1080 / 307 px @2160).** Bracket top sits ≈ 63% H, so the block stacks just above the caption line, roughly at chest height, overlapping the subject's body (it is not boxed off in a safe corner).
- No background plate and no drop shadow. It relies on the creamy, low-key image for contrast. If needed, add a 30% black shadow with 20 px blur.

**Animation @30 fps** (measured):
| Frame (relative) | Event |
|---|---|
| 0 | Empty brackets `[ ]` cut on, collapsed to ~0.6× cap height wide |
| 0–18 | Brackets hold (a "cursor wait") |
| 18–36 | Name **types on one character every 3 frames** while the right bracket travels right to stay attached to the last glyph (linear). "PAUL BLOCH" = 10 chars ≈ 30 f |
| 51–72 | Red tag: the rectangle grows left→right with the text, typing on at **≈1.3 chars/frame** (29 chars in ~22 f). Bar width tracks the text (it is not a separate wipe) |
| hold | ≈ 4 s total on screen |
| out | Characters delete right→left at ~2× the in speed, or a hard cut (both appear in the series) **(est.)** |

### 4.3 Word-chunk captions (2024–25 interview style)
Reference: `reference/frames/paul_detail/full_t8.0.jpg`, `open_02.jpg`; `frames/02-DDN_12102024_…/sheet_01.jpg`
- **Geist Mono Regular**, white, sentence case, 1–3 words per card ("So the company", "with NVIDIA.").
- **Plate:** rounded rectangle, fill `#3F3F3F` @ ~85% (or `#201E1E` @ 80%), radius ≈ 16 px @1080, padding 24 px horizontal / 16 px vertical. The plate width hugs the text.
- Size ≈ 3.9% H in 4:5 → **42 px @1080 / 84 px @2160** in 16:9.
- Centred horizontally, with the plate centre at ≈ 78% H (16:9: bottom of plate at 86% H).
- **Changes on every 2–4 words with a hard cut** (≈ 8–20 frames per card, synced to speech). No animation in or out.

### 4.4 Sentence captions on frosted glass (2026 style, recommended for new work)
Reference: `reference/frames/ddn-sepd-wrap-video-1920x1080-1/full_t31.jpg`, `caption_steps.jpg`, `sheet_01.jpg`
- **Articulat CF Regular** (fallback: Inter), white at ~95%, sentence case with full punctuation ("The shift is not incremental."). One short sentence or clause per card.
- **Cap height ≈ 58 px @1080 → font ≈ 78–80 px @1080 / 156–160 px @2160** (large, made for social and muted autoplay).
- **Plate:** frosted glass. Use a **backdrop blur ≈ 30 px @1080**, a tint gradient from warm mauve on the left (`rgba(140,110,120,0.55)`) to slate on the right (`rgba(90,100,130,0.55)`), radius ≈ 18 px @1080, and padding ≈ 56 px horizontal / 36 px vertical. The plate hugs the text. Measured plate: x 420–1500, y 878–1035 @1080.
- Position: centred, plate bottom at **96% H** (very low; 45 px margin @1080).
- Change: **hard cut** sentence to sentence. Plate width snaps to the new text with no tween. Each sentence is on screen ≈ 1.5–2.5 s.

### 4.5 Title card / chapter card (2026)
Reference: `reference/frames/ddn-sepd-wrap-video-1920x1080-1/full_t7.6.jpg`, `full_t6.5.jpg`, `titlecard_steps.jpg`
- **Frosted panel** over the live shot: inset x 8.6%–91.4% W (165→1755 px @1080), y 9.5%–90.5% H (103→977). **Radius ≈ 48 px @1080 / 96 px @2160.** Heavy blur (≈ 60 px @1080) of the underlying shot, tinted warm `#5A4040` @ 60%, with a soft top-centre glow (radial, `rgba(255,220,200,0.25)`).
- **Hairline:** 1 px @1080 (2 px @2160), white @ 55%, from x = 15% to 85% W, at y = 27% H.
- **Title:** Articulat CF Regular/Medium, white, 2 lines, **≈ 84 px @1080 / 168 px @2160**, leading 1.2, left edge x = 15% W, first cap top ≈ 36% H.
- **Subtitle:** Articulat Regular, white @ 75%, ≈ 46 px @1080, 24 px under the title.
- **Logo:** horizontal ddn logo (white wordmark, colour mark) ≈ 140 px wide @1080, at x = 15%, y = 77–80% H.
- **Animation:**

| Frame (relative) | Event |
|---|---|
| 0 | Hard cut to panel (empty) |
| 8–20 | **Hairline + text rise together**: start ≈ +26% H lower, ease `ddn-out`. Text is **masked to the area below the hairline** (so it appears to emerge from under the line), with vertical motion blur and opacity 0→1 |
| 12–22 | Subtitle words stagger in, about 2 f per word |
| 20–30 | Logo fades in, 0→100% |
| 30–75 | Hold (~1.5 s) |
| 76 | Hard cut out |

### 4.6 Stat / number callouts
**2026 counter** (`reference/frames/ddn-sepd-wrap-video-1920x1080-1/full_t23.jpg`, `counter_steps.jpg`):
- Full-frame **Wine→Slate grain gradient** (1.3) with a centred frosted rounded plate (radius ≈ 16 px, fill white @ 6%). Measured plate: 390–1530 x 420–660 @1080.
- Number in Articulat Regular, white, with tabular figures. Cap ≈ 90 px → **font ≈ 125 px @1080 / 250 px @2160**.
- **Count-up:** $2.5B → $500,000,000,000 over **≈ 24 frames (0.8 s)**, easing `ddn-inout` (sampled increments rise, then decelerate). It lands on a round number, holds **≈ 70 frames (2.3 s)**, then hard cuts.
- The previous shot cuts to this card **mid-sentence**, and the caption is removed while the number is on screen.

**2025 explainer stat** (`frames/DDN_040825_…/sheet_01.jpg` at 26–34 s): huge bold sans ("1 TB/s", "99.999%") at ≈ 13% H, white, centred over darkened red-tinted B-roll. Second line ("Throughput") at 55% of that size. On screen ≈ 2 s per stat, hard cuts between stats.

### 4.7 Mono label + headline ("terminal tag"), 2025
Reference: `frames/homepage-video/sheet_01.jpg` (0–4 s), YouTube thumbnails.
- Red tag `#CB343B` with white Geist Mono text ending in a colon ("Data Revolution:"), height ≈ 3.5% H. A two-line Articulat Medium headline sits beneath it (≈ 6.5% H), left-aligned at x = 7%.
- The headline **types on letter by letter** (≈1 char per frame), with a red cursor on the last letter.

### 4.8 Campaign kinetic type, 2024–25 (for openers/hype only)
- **"BEYOND _"** (`frames/DDN-Beyond-Artificial-Half-Frame-Edit/sheet_01.jpg`): Fire gradient, heavy caps at ≈ 10% H, left x = 4%, with a **blinking underscore cursor** (on 8 f / off 8 f). The frame then splits 50/50. The left half keeps "BEYOND" on fire red; the right half cycles footage plus a mono-bold word ("MEDICINE", "THE GRIND", …) **every 16 frames**.
- **"WELCOME / TO THE FUTURE WITH [logo]"** (`frames/GTC_DDN-Company-Commercial/sheet_01.jpg`): typewriter "THE FUTURE_" on the Fire gradient, then heavy caps over cinematic stock with a **persistent ddn bug bottom-right** (≈ 4% H, x = 96%, y = 92%). It uses wipe/whip transitions with a red swoosh (the ring arc) sweeping across frame.
- **Gold dotted concentric rings** ("vortex", halftone dots on dark wine): end-card background for Beyond Artificial / Infinia. The Infinia mark is a dot-matrix "∞/8" in orange-red dots.

### 4.9 Thumbnail / speaker-card system (2026 YouTube)
Reference: `reference/frames/yt_thumbs_montage.jpg`
- Left 50%: headline in Articulat Regular/Medium, sentence case, white on dark wine (`#201E1E`→`#7D2D3F` diagonal) or DDN Black on a pale pink-to-white gradient. Above it, a **Geist Mono eyebrow** ("DDN Data Summit | ISC 2026", "PEARC 2026") at ~30% of headline size, in red on light backgrounds or grey on dark.
- Right side: speaker, either **in a circle crop** with a pale ring halo or full-bleed. Name card bottom-right: Articulat Medium name over a Geist Mono uppercase title, on a black @ 70% box.
- ddn logo bottom-left (light version) or top-left (dark version).

### 4.10 Logo stings / outros
**A. 2026 line-ring build** (current, recommended). Reference: `frames/ddn-sepd-wrap-video-1920x1080-1/outro_steps.jpg`, `end_sheet.jpg`. Background `#E7E7E7`. All frames below are relative to the hard cut to grey.

| Frame | Event |
|---|---|
| 0 | Hard cut from the last shot to flat `#E7E7E7` |
| 2–40 | 3–5 **thin outline circles** (1 px @1080, pink-red `#D46A7E` @ 80%), born tiny at centre. They grow and **orbit around each other** (Spirograph-like) to ≈ 7% H diameter, easing `ddn-inout` |
| 34–46 | The cluster slides left to the mark position. The wordmark "ddn" fades in at the right in pale pink (`#E8B5BE`) |
| 42–48 | The circles collapse into one **thick ring** (dark wine), which then fills with the **brand torus gradient** over ~8 f |
| 48–80 | The wordmark colour shifts from pale pink to **DDN Black `#201E1E`** |
| 80+ | Hold ≈ 1.5 s. Final size: horizontal logo ≈ 21% W wide, centred |

Total ≈ 2.7 s plus hold.

**B. 2024–25 chrome 3D sting** (In Conversation series). Reference: `frames/paul_detail/outro_sting.jpg`, `outro_sheet.jpg`. All frames relative to the start of the montage.

| Frame | Event |
|---|---|
| 0–27 | **3D photo-wall flythrough**: a tilted plane of archival photos, camera dollying |
| 27–36 | Whip motion-blur dissolve to white |
| 36–42 | Pure white |
| 42–60 | Chrome/black **extruded 3D logo** (ring and wordmark separately) tumbles in from the lower right, with heavy motion blur |
| 60–84 | The pieces rotate to face camera. A **red glow** (`#ED2738` @ 40%, 80 px blur) sits behind the ring. Chrome reflections sweep across it |
| 84–96 | Morphs into the flat colour stacked logo (ring above "ddn") on white |
| 96+ | Hold ≈ 3 s |

**C. Simple stacked logo on white/black** (Beyond teaser, Nirvana): the ring scales in from 110% to 100% over 12 f with `ddn-out`, then the wordmark fades up under it. For a co-brand, "Google Cloud × ddn" is stacked vertically.

### 4.11 Backgrounds and texture library
| Element | Spec | Reference frame |
|---|---|---|
| Film grain | Monochrome, ~3–5% opacity, on every gradient card in 2026 | `full_t23.jpg` |
| Ember angle-flow | Two-layer conic-ish gradient rotating 360° per 8 s (web) | theme.css |
| Pixel-block mosaic | Square cells (≈ 3% W) stepping through red→cream; glitchy reveal | `frames/ddn-ai-factories-lp-hero-video/f_002.jpg` |
| Sunrise arc + pixel strips | Big orange arc horizon, silhouette, pixel-sorted vertical strips | `frames/Hero_01-r2-1/f_002.jpg` |
| Dot-wireframe globe | White point/line sphere on black, slow rotation (~20 s) | `frames/sphere/f_002.jpg` |
| Circuit + particle wave | Thin rust lines, glowing particle ribbon on `#3F1306`→`#741E11` | `frames/ddn-header-loop-generic-1920x960-1/f_002.jpg` |
| Concentric dotted vortex | Orange→red gradient with faint dotted rings | `frames/vortex-bg-1920x960-1/f_002.jpg` |
| Red tile wall (3D) | Glossy red square tiles in a diamond relief; camera push; used as a transition plate | `frames/ddn-sepd-wrap-video-1920x1080-1/sheet_01.jpg` @14–16 s |
| Data streams / binary | Blue-red binary ribbons, red network nodes on black | Origin-Story sheet @36–40 s, Nirvana sheet @2–8 s |

---

## 5. Transition list (by frequency)
1. **Hard cut**: about 90% of all transitions, both shot-to-shot and graphic-to-graphic.
2. **Typewriter build** (text-level), with a bracket or underscore cursor.
3. **Light-leak flash**: red-orange, screen blend, ~15 f, used once near the opener.
4. **Vertical-slice wipe**: 4–6 strips, staggered, ~6 f (shot to shot in the opener).
5. **Whip/zoom motion-blur**: ~6–9 f, into a logo sting or between sizzle shots (Nirvana @44 s).
6. **Red swoosh arc wipe**: a ring-shaped red arc sweeps across, ~8 f (GTC commercial @3 s).
7. **Red tile-wall / pattern plate**: a ~1 s branded interstitial between sections (2026).
8. **Pixel-mosaic dissolve**: block-stepped, ~10 f (2025–26 web loops).
9. Cut to **solid colour** (white or `#E7E7E7`) before the logo outro.

No cross-dissolves were observed except inside the logo stings.

---

## 6. Talking-head framing and overlay rules
- **Two angles:** a medium close-up (eyes at ~33% H, head and shoulders, subject offset to one third) and a medium-wide seated shot (full torso, hands visible, subject centred). Cut between them every ≈ 3–5 s on sentence ends. **With one iPhone, emulate this with 4K→1080 punch-ins: 100% ↔ 140% scale, re-centred.**
- Subject is lit soft from the front-side against a **plain warm cream wall**. A small piece of red art in the background is the only brand colour in shot. Shallow depth of field.
- Graphics sit **over the subject's torso/lap area** in the lower-left third. They never sit over the face.
- B-roll inserts (server racks, detail macros, abstract data) run 2–6 s each and are graded to the same warm look.
- Captions are on for the whole video (silent-autoplay social).
- The open is cold: voice starts at frame 0, with the title card over the A-roll.

**Suggested grade for iPhone 12 footage** (HDR/HLG → Rec.709):
1. Convert HLG to 709 (ACES or a DaVinci CST).
2. Exposure: put the skin key at 65–70 IRE.
3. Contrast −10, lift blacks so the darkest values sit around `#1E1E22`.
4. Highlights −15, soft roll-off.
5. White balance warm by ~+300 K; aim the cream wall at `#F0DFCB`.
6. Saturation −10%, then skin +5.
7. Mild halation/bloom on highlights (≈ 5%).
8. Fine grain 2–3%.
9. Optional for brand moments: a wine vignette from the bottom (`#230E15` @ 60%).

---

## 7. Implementation cheat-sheet (30 fps)
| Element | In | Hold | Out | Ease |
|---|---|---|---|---|
| Series title card | type 6–10 f per line | ~3 s | slice wipe 6 f | linear type / `ddn-out` strips |
| Bracket lower third | 18 f wait + 3 f/char name + ~1.3 chars/f tag | ~4 s | reverse type or cut | stepped |
| Mono word captions (2024–25) | cut | 8–20 f | cut | — |
| Glass sentence captions (2026) | cut | 45–75 f | cut | — |
| Chapter card (2026) | 12 f rise from under a hairline | 45 f | cut | `cubic-bezier(0.16,1,0.3,1)` |
| Number counter | 24 f count-up | 70 f | cut | `cubic-bezier(0.65,0,0.35,1)` |
| Logo outro (2026) | 80 f build | 45 f | end | `ddn-inout` |
| Light-leak flash | 15 f | — | — | screen blend, ease-in-out opacity |

Pixel conversion: every value given @1080 doubles for the 3840x2160 timeline. Keep a 5% title-safe margin. DDN's own interview supers sit at 8–16% from the left edge.

---

## 8. Reference frame index
- Brand logo renders: `/home/user/ddn-project/brand/*_preview.png`. SVGs: `ddn-logo-primary-color.svg`, `ddn-logo-simplified-blk.svg`, `ddn-logo-black.svg`, `main-logo-small.svg` (white wordmark), `favicon.svg` (mark only).
- Title card: `reference/frames/paul_detail/full_t1.0.jpg`, `full_t2.5.jpg`, `open_01.jpg`
- Lower third and mono caption: `reference/frames/paul_detail/full_t8.0.jpg`, `open_02.jpg`, `open_03.jpg`
- Slice transition and light leak: `reference/frames/paul_detail/open_01.jpg` (cells 33–38), `open_02.jpg` (cells 46–47)
- Chrome logo sting: `reference/frames/paul_detail/outro_sting.jpg`, `outro_sheet.jpg`
- 2026 chapter card: `reference/frames/ddn-sepd-wrap-video-1920x1080-1/full_t7.6.jpg`, `full_t6.5.jpg`, `titlecard_steps.jpg`
- 2026 glass captions: `…/ddn-sepd-wrap-video-1920x1080-1/full_t31.jpg`, `caption_steps.jpg`
- 2026 counter: `…/full_t23.jpg`, `counter_steps.jpg`
- 2026 logo build: `…/outro_steps.jpg`, `end_sheet.jpg`, `outro_final.png`
- Partner logo grid / red tile wall: `…/full_t10.5.jpg`, `full_t14.3.jpg`
- Campaign type: `reference/frames/DDN-Beyond-Artificial-Half-Frame-Edit/sheet_01.jpg`, `GTC_DDN-Company-Commercial/sheet_01.jpg`, `Infinai_Teaser_Voice-Option-1/sheet_01.jpg`
- Explainer stats: `reference/frames/DDN_040825_video_li_GoogleAICloudNirvana_Partnership-Page_1080x1350/sheet_01.jpg`
- Mono-tag headline: `reference/frames/homepage-video/sheet_01.jpg`
- Background loops: `reference/frames/loops_montage.jpg`
- 2026 YouTube thumbnails: `reference/frames/yt_thumbs_montage.jpg`
- Every video has `reference/frames/<video>/sheet_NN.jpg` (timestamped contact sheet) and `f_NNN.jpg` frames. Scene cuts are in `reference/scenes.txt`.

---

## 9. What we can't know / assumptions
- **No YouTube videos were analysed**: downloads were bot-blocked. The newest YouTube-only content (ISC 2026 keynotes, the "Behind Every AI Breakthrough" sizzle, customer stories) was judged from thumbnails only. Its lower thirds and keynote openers may differ from the website masters.
- **The brand guide PDF is not public** (request it from brand@ddn.com). The palette is official. Font names come from the website CSS; video fonts were matched by eye and may be a related grotesk.
- The **Articulat CF font files** were not downloaded: they load via Adobe Fonts through script, and the kit is licensed. Geist Mono is free.
- **Easing curves are estimates** from 2–4-frame sampling. Typewriter rates and timings are measured to ±2 frames. Sizes are measured to ±5% on compressed web encodes.
- **Two graphic generations coexist.** 2024–25 uses brackets, mono captions, chrome 3D logo and a fire gradient. 2026 uses frosted glass, sentence captions, a line-ring logo build, wine-slate grain and grey/cream. **Use the 2026 system** for "current DDN", and borrow the bracket lower third if you want the "In Conversation" feel.
- Music and SFX were not identified. Tempo figures come from a crude autocorrelation. By ear-equivalent analysis, interviews carry a low ambient-piano/pad bed and sizzles use cinematic tech-pulse tracks. Light-leak and whip moments likely have whoosh SFX, but this is unverified.
- Exact blur radii, glass tint and the grain amount are visual estimates.
- Frame rates vary across DDN deliverables (23.976, 25, 29.97, 30). The 30p choice matches the interview series exactly.
