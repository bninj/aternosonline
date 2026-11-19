// DDN brand tokens. Every value traces to research/DDN_STYLE_GUIDE.md (section in brackets).
import {Easing} from 'remotion';

// [1.1] Official palette (ddn.com/company/brand-assets). Never approximate these.
export const C = {
  red: '#ED2738', // Brand Red: emphasis, gauge fill, chart end point
  deepRed: '#CB343B', // Deep Red: mono tag fill (role tag / terminal tag)
  wine: '#7D2D3F',
  black: '#201E1E', // DDN Black (not pure black)
  warmBlack: '#402022',
  warmGray: '#D8D2CB',
  coolGray: '#F0F0F0',
  outroGray: '#E7E7E7', // [4.10A] 2026 outro background
  white: '#FFFFFF',
  pinkRed: '#D46A7E', // [4.10A] 2026 outro circles
  palePink: '#E8B5BE', // [4.10A] 2026 outro wordmark start colour
} as const;

// Frosted glass v2 [4.4, 4.5]. Real frost, rendered deterministically: the plate shows a pre-blurred copy of the
// footage behind it (Backdrop.tsx), never CSS backdrop-filter (that dropped plates on ~1 % of frames, round 3 of v1).
// The smoke (brightness + wine/slate tint) is set so the lightest plate pixel over a cream classroom wall still gives
// white text >= 7:1. Red is never used for text on the plate: emphasis is white text on a Brand Red marker (3.9:1).
export const GLASS = {
  radiusPx: 22,
  blurPx: 34, // [4.4] DDN caption glass blur ~30 px @1080; [4.5] chapter card 60 px
  smoke: 0.42, // brightness multiplier on the blurred footage (dark tone)
  saturate: 1.2,
  // [1.3] 2026 Wine to Slate hues over the frost (alpha keeps it translucent)
  tint: 'linear-gradient(105deg, rgba(52,24,31,0.50) 0%, rgba(48,40,56,0.44) 55%, rgba(50,58,82,0.44) 100%)',
  // light tone: logos keep their official colours on a pale frost (Cool Gray family)
  lightSmoke: 1.15,
  lightTint: 'linear-gradient(105deg, rgba(250,247,245,0.80) 0%, rgba(244,244,246,0.76) 100%)',
  // fallback when no footage is available (alpha overlay renders): same look, no frost
  fallbackDark: 'linear-gradient(105deg, rgba(46,24,30,0.88) 0%, rgba(44,36,50,0.86) 55%, rgba(40,46,64,0.86) 100%)',
  fallbackLight: 'rgba(246,244,243,0.94)',
  grainOpacity: 0.05, // [4.11] 3 to 5 % mono grain on 2026 cards
} as const;

// Prism (v3, user: "prism, but in line with DDN's brand"): the dispersion runs through DDN's own spectrum, the logo
// ring's orange #FE7500 -> red-orange #F9502E -> Brand Red #ED2738 -> wine #7D2D3F, with a hint of Steel Blue #7594B2
// as the cool end, instead of a generic rainbow. Used on the glass rim (refracted edge) and the entrance light sweep.
export const PRISM = {
  rimPx: 2,
  stops: ['rgba(254,117,0,0.95)', 'rgba(249,80,46,0.95)', 'rgba(237,39,56,0.95)', 'rgba(125,45,63,0.9)', 'rgba(117,148,178,0.9)'],
  sweepFrames: 26, // entrance: a soft prism light band crosses the glass once, and a glint travels the rim
  sweepAlpha: 0.36, // peak opacity of the interior light band (screen blend)
  splitPx: 3, // RGB split on entrance, decays to 0 with the rise
} as const;

// [3] Easing presets. No overshoot anywhere.
export const EASE = {
  out: Easing.bezier(0.16, 1, 0.3, 1), // ddn-out: rises, slide-ins
  inOut: Easing.bezier(0.65, 0, 0.35, 1), // ddn-inout: counters, long moves
  ui: Easing.bezier(0.4, 0, 0.2, 1), // ddn-ui: small UI fades
  soft: Easing.bezier(0.33, 0, 0.2, 1), // v2: opacity / blur ramps that start gently (no first frame jump)
  exit: Easing.bezier(0.45, 0, 0.55, 1), // v2 exits: soft in-out, starts and ends at rest (no snap)
} as const;

// [7] Timing table @30 fps (frames).
export const T = {
  fps: 30,
  riseFrames: 12, // chapter card: 12 f rise from under a hairline
  countFrames: 24, // number counter: 24 f count-up
  tagCharsPerFrame: 1.3, // role tag types at about 1.3 chars per frame
  firstOffset: 3, // content never starts on the cut frame (checklist A)
  enterFrames: 14, // v2: every graphic enters (rise + blur to sharp + opacity, ddn-out)
  exitFrames: 10, // v2: exits take ~75 % of the entry (ddn-ui, rise away + blur + fade). No hard cuts anywhere.
  enterRisePx: 26,
  enterBlurPx: 14,
  swapFrames: 10, // caption phrase to phrase: soft blur swap
  motionBlurSamples: 6,
  shutterAngle: 180,
  captionLeadFrames: 3, // words land 0 to 0.15 s early, never late
} as const;

// Frame geometry @1920x1080. Scale everything by width / 1920 for 4K.
export const FRAME = {w: 1920, h: 1080} as const;
export const SAFE = {
  margin: 0.05, // 5 % title safe (96 px x / 54 px y @1080)
  sideInset: 0.08, // [4.2] DDN supers sit at x = 8 % W in 16:9 (154 px @1080)
  graphicsBottom: 0.75, // graphics stay above the caption band (caption plate top is 79 % H): 46 px gap
} as const;

// Type scale @1080 [4.4, 4.6, 4.2, 4.5].
export const TYPE = {
  caption: 78, // 2026 glass caption: 78 to 80 px
  number: 132, // 2026 counter 125 px; a touch larger as an overlay card
  headline: 64,
  word: 84, // chapter title size, used for spoken keywords
  big: 168, // "Blockbuster" line: 2x chapter title
  tag: 30, // v2: source tags +25 % for laptop legibility (DDN role tag is 24 px on a 37 px bar)
  tagBar: 46,
  eyebrow: 24,
} as const;

export const sec = (s: number, fps = T.fps) => Math.round(s * fps);
