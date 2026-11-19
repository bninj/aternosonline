# DDN on-screen graphics and subtitles (Remotion), v2

The code is in `tools/remotion/src/ddn/`, imported through `./ddn` (`index.ts`). The demo is `src/GraphicsDemo.tsx`. Compositions in `src/Root.tsx`:
- `GraphicsDemo`: logos on, over the stand-in footage.
- `GraphicsDemoText`: the same timeline with every logo moment as text.
- `GraphicsOverlay`: no footage, alpha overlay. The glass falls back to a tinted fill.

Output is 1920x1080 at 30 fps. Every token is a px value @1080; for 4K, scale by width / 1920.

The design system is DDN's 2026 system from `research/DDN_STYLE_GUIDE.md` (section numbers are cited in the code). v2 adds the user's direction:
- real frosted glass with a touch of prism;
- motion blur;
- no cut-in or cut-out of any graphic or caption;
- a pitch-progress diagram;
- a pitch clock;
- official logos.

## Build, preview, render
```
cd tools/remotion
npx remotion studio                                   # GraphicsDemo / GraphicsDemoText / GraphicsOverlay
node scripts/stills.mjs GraphicsDemo out/ 200,650     # many stills from one bundle
npx remotion render src/index.ts GraphicsDemo out.mp4
python3 scripts/flicker_scan.py out.mp4 90            # flicker / pop scan (90 = known footage cut)
node scripts/check-onscreen.mjs public/demo_transcript.json   # dash lint
```

## Frosted glass without backdrop-filter (Backdrop.tsx, primitives.tsx)
Wrap the whole edit in `<Footage source={...}>`. Footage draws the main layer itself, so the glass copies can never drift from it:
```tsx
<Footage source={{src: 'cut.mp4', kind: 'video', blurredSrc: 'cut_blur34.mp4'}}>
  ...graphics...
</Footage>
```

How each plate (`FrostedGlass`) is built, bottom to top:
1. `Frost`: a copy of the footage layer, aligned pixel for pixel and clipped to the plate's rounded shape. It is smoked (`brightness 0.42, saturate 1.2`) and blurred.
   - Alignment is measured every frame with `getBoundingClientRect` relative to the Footage root, in `useLayoutEffect`, so React applies it before Chrome paints.
   - The measurement includes the rise transforms, Studio's preview scale and any scale animation (the copy is counter-scaled).
   - Video copies are re-anchored to composition frame 0 with `trimBefore`, so they show the same frame as the main layer.
2. Wine to Slate tint at about 0.45 alpha, so the glass stays translucent.
3. Top sheen, 5 % moving grain, inner top highlight (1 px).
4. Prism rim:
   - a 1.5 px border that refracts (red, amber, green, cyan, violet) at the top-left corner and fades to a white hairline;
   - on entrance, one dispersed glint travels the rim (22 f) with a faint sheen across the face.
5. Content, with an RGB split of 3 px on entrance that decays to 0 as the plate settles (and returns at 70 % on exit). It is applied to graphic content only, never to footage or faces.

Blur source: pass `blurredSrc` (an ffmpeg pre-blurred proxy) for speed and identical renders. Without it, the copy is blurred with CSS `filter: blur(34px)`, which is deterministic, unlike `backdrop-filter`.

Make a proxy:
```
ffmpeg -i cut.mp4 -vf "scale=960:540,gblur=sigma=17,setsar=1,format=yuv420p" -c:v libx264 -crf 20 -g 30 cut_blur34.mp4
```

Footage must be square-pixel (`setsar=1`). A non-square SAR made @remotion/media draw a stretched frame (critique log v2, round 1).

Tones:
- `tone="dark"` is the smoked glass for text.
- `tone="light"` is pale frost for colour logos (official artwork stays unmodified).

**Contrast rule:** red is never used as text on glass.
- Caption emphasis is white text on a Brand Red marker that wipes in when the word is spoken. White on #ED2738 is 3.9:1, which passes for large text.
- Measured worst-case white on dark glass over the stand-in wall: see `output/critique_log.md` v2.

## Motion rules (v2)
| Rule | Value |
|---|---|
| Entry (every Slot graphic) | 14 f, ddn-out: rise 26 px, blur 14 to 0 px, opacity over the first 55 % |
| Exit | 10 f (about 75 % of the entry), soft in-out: rises away 14 px, blur to 11 px, fades. Ends exactly at the slot end |
| Short lines | Entry and exit compress (down to 50 %) so the hold is never shorter than the moves |
| Motion blur | `@remotion/motion-blur` `CameraMotionBlur`, 6 samples, 180°, only while a plate moves (shutter 0 otherwise, same React tree) |
| Captions | One plate per run of consecutive phrases: it enters (10 f) at the first, exits (8 f) after the last. Phrase to phrase: plate size tweens (8 f, ddn-out), old text lifts away and blurs out (5 f), new text rises in from blur (8 f) |
| Inner builds | Rise from under a hairline (ddn-out + blur 6 to 0), counter 24 f ddn-inout, source tag bar grows and characters fade up 3 f each (no popping) |
| End card | #E7E7E7 dissolves in over 16 f, DDN logo rises at f12, hairline at f20, line at f23 |
| Easing | ddn-out (0.16,1,0.3,1), ddn-inout (0.65,0,0.35,1), ddn-ui (0.4,0,0.2,1), exit (0.45,0,0.55,1). No overshoot anywhere |

## Placement (`layout.ts`, `Slot.tsx`)
Every graphic takes `SlotProps`:
- `from`, `durationInFrames`;
- `anchor`: `'left' | 'right' | 'center' | 'auto'`;
- `faceBox`, `avoid: Box[]` (for example a monitor in shot that already shows a logo);
- `offset {x, y}` px;
- `bottom` (fraction of H, default 0.75);
- `enterFrames`, `exitFrames`.

`auto` picks the side with more free room between the 8 % inset and the nearest face or avoid box. Max width is that room minus 48 px, capped at 1000 px.

Captions are centred with the plate bottom on the 5 % safe line. With `anchor="auto"` they move to the far side if the face or an avoid box enters the caption band.

## Components
| Component | Key props | Notes |
|---|---|---|
| `Footage` | `source: {src, kind: 'image' \| 'video', blurredSrc?, style?, trimBefore?, volume?}` or `null` | Root wrapper. Main layer plus frost source. `null` gives an overlay render with fallback tint |
| `Subtitles` | `transcript`, `emphasis?` (`['DDN','Sky']`; digits auto), `anchor?`, `faceBox?`, `avoid?`, `suppress?`, `joinGapFrames?` (8) | Deterministic layout via `@remotion/layout-utils` after the fonts load; balanced two-line wrap; soft swaps |
| `SectionProgress` | `sections: {label, from, to, weight?, logo?}[]` (absolute frames), `from`, `durationInFrames`, `width?` (940), `edge?` ('top'), `anchor?`, `faceBox?`, `avoid?`, `offset?`, `showWeights?` | Echoes the contest bar. Segment widths are proportional to the real section durations. The current segment fills in Brand Red; finished segments settle to pale pink #E8B5BE; the current label brightens and gains a red dot. Replaces SectionMarker |
| `SectionBar` | `sections: {label, from}[]` (absolute frames of each section change), `from`, `durationInFrames`, `presentFrames?` (52), `width?` (900), `slimWidth?` (520), `labelSize?` (26), `top?`, `right?` | Contest-slide style progress, used in PitchFinal. Light frosted panel, equal labelled segments: active #ED2738, done pale rose, upcoming neutral. Presents on each change (fill plus DDN-spectrum glint), then condenses to a slim top strip |
| `PitchTimer` | `clockZero` (absolute frame of 00:00), `totalSeconds?` (90), `showTotal?`, `label?`, `variant?` ('intro' \| 'reprise'), `scale?`, plus SlotProps | Frosted capsule, hairline ring draws in, Brand Red progress arc with soft head, single red pulse at 00:00, Geist Mono digits roll. Shown at the start, then animates away. A `reprise` instance near the end reads the real elapsed time |
| `KeywordStack` | `items: {text, at, logo?, show?}[]`, `show?: 'logo' \| 'text'`, `logoHeight?` (64), `direction?` | One chip per name. Logo chips are light frost with clear space = 0.5 × logo height |
| `BigWord` | `text`, `logo?`, `show?`, `logoHeight?` (150), `size?` | "Blockbuster": the official ticket logo, or the big word as fallback |
| `MeasureCard` | `items: {label, at, before, after}[]` (bar lengths 0..1), `tag?` ("30 day pilot"), `width?`, plus SlotProps | The ask: each metric gets a quiet before bar and a Brand Red after bar that morphs to its target. Illustrative, with no numbers. Give it a long slot (it is built to hold through the next line); exit 14 f. No DDN logo |
| `EndCard` | `logo?` (true), `line?`, `lead?`, `logoHeight?` (120) | DDN primary colour logo, then "Keep the chips busy." |
| `LineChartFall`, `StatCard`, `BusyGauge`, `ChatBubble`, `AskCard` | as v1 (chat characters now fade up 3 f each; cursor fades) | Now on frosted glass with the v2 envelope. Source tags are 30 px on a 46 px bar (+25 %) |

Every on-screen string still goes through `onScreen()`, which throws on any dash character.

## Logos
Official artwork only, unmodified. Sources and trademark notes are in `brand/logos/SOURCES.md`; the copies are in `public/logos/`. The registry is `logos.tsx` (`LogoId`):
- `ddn`, `ddn-white`, `netflix`, `youtube`, `blockbuster`, `canalplus`, `starz`.
- Real footage: a Sky logo is on a monitor in the Why change / Why now shots, and a DDN logo in the Why DDN shots. So never put a Sky or DDN logo graphic over those shots. Pass the monitor rectangle as `avoid` (on every Slot graphic, Subtitles and SectionProgress) so graphics stay off it. The progress label for Why DDN is text by default.
- **Sky is not included.** No public-domain or official SVG was reachable; it stays text until Sky's own file is added.
- There is no DDN logo on the pilot or ask card (it is the user's proposal, not a DDN offer).
- Use `show="text"` per item or per component when the footage already shows that logo on a monitor. Use `avoid` and `offset` to keep the graphics off that screen.

## Fonts
The measured match is from `research/FONT_MATCH.md`.

Inter Tight variable is `public/fonts/InterTight-VF.ttf` (wght 100 to 900, OFL). It is set with `display(role, size, tracking)`:

| Role | Weight / tracking |
|---|---|
| regular (captions, body) | 340 / +0.014em |
| regularDesktop | 380 / +0.022em |
| medium (keywords, payoff, end line, caption emphasis) | 480 / +0.025em |
| bold | 620 / +0.023em |
| capsName | 540 / +0.05em |

All roles use size ×0.966. DDN's own tracking is added on top.

The Articulat CF drop-in slot is unchanged. With the real files, the roles map to 400/400/500/600/500 at ×1 with no extra tracking.

Geist Mono is unchanged.

`useFontsReady()` holds a frame until the real metrics are available, so caption measurement never caches fallback widths.

## Outputs
- Demo: `output/graphics/GraphicsDemo_v2.mp4`.
- Contact sheet: `output/graphics/contact_v2.jpg`.
- Motion strips and reference comparisons: `output/graphics/v2_*.jpg`.
- Critique rounds: `output/critique_log.md` (v2 section).

## Known weaknesses
- The stand-in footage is a still interview plate with a slow push-in, plus a 3 s wall crop standing in for the empty chair (real sign: "AI"). Re-check frost and contrast on the real classroom footage (white boards and windows are brighter than the cream wall).
- Footage must be `<OffthreadVideo>`-friendly and square pixel. `@remotion/media <Video>` gave wrong frames on one render tab under memory pressure, so the Footage layer uses OffthreadVideo. Render with `--concurrency=2` on this 15 GB box.
- Frost costs one extra decoded copy of the footage per visible plate (cheap with the 960 px proxy).
- Render speed is about 0.5 s per frame at 1080p with motion blur.
- Sky logo missing (see above).
- Display face is Inter Tight until Articulat CF is licensed.

## PitchFinal (real film)
`src/pitch/PitchFinal.tsx`, composition `PitchFinal`, 1920x1080, 30 fps, 2400 f.
- Props:
  - `plate`: `pitch/plate.mp4`, a hard link to `edit/plates_noblur/plate.mp4`;
  - `plateBlur`: a 960 px gblur proxy (make it with the ffmpeg line above);
  - `voice`: `pitch/voice_master.wav`;
  - `showGuides`: draws face and keep-out boxes, for QA only.
- Run `scripts/sync_pitch.sh` after SHOTPLAN or captions change.
- Face boxes and keep-outs are in `src/pitch/layout.ts`.
- Captions are re-chunked in `src/pitch/captions.ts`.
- Use hard links, not symlinks, in `public/` (symlinks 404 in the render server).
- Prism uses DDN's spectrum: tokens `PRISM.stops`.
