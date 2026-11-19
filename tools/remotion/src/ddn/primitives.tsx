import React, {createContext, useContext} from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {CameraMotionBlur} from '@remotion/motion-blur';
import {C, EASE, GLASS, PRISM, T, TYPE} from './tokens';
import {FONT} from './fonts';
import {onScreen} from './sanitize';
import {Frost, useFootage} from './Backdrop';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// ---------------------------------------------------------------------------------------------------------------
// Envelope: every graphic enters and exits smoothly (v2 rule: no hard cuts, no pops, no overshoot).
// Entry: rise + blur to sharp + opacity, ddn-out. Exit: ~75 % of the entry, gentle ease-in, rises away and softens.
export type Envelope = {enterStart: number; enterFrames: number; exitStart: number; exitFrames: number};
const EnvCtx = createContext<Envelope | null>(null);
export const EnvelopeProvider = EnvCtx.Provider;

export const makeEnvelope = (duration: number, opts: {delay?: number; enter?: number; exit?: number} = {}): Envelope => {
  const delay = opts.delay ?? T.firstOffset;
  // Short lines compress the motion so the hold is never shorter than the moves.
  const k = Math.max(0.5, Math.min(1, (duration - delay) / ((opts.enter ?? T.enterFrames) + (opts.exit ?? T.exitFrames) + 20)));
  const enterFrames = Math.max(6, Math.round((opts.enter ?? T.enterFrames) * k));
  const exitFrames = Math.max(5, Math.round((opts.exit ?? T.exitFrames) * k));
  return {enterStart: delay, enterFrames, exitStart: Math.max(delay + enterFrames, duration - exitFrames), exitFrames};
};

export type EnvelopeValues = {enter: number; exit: number; frame: number; env: Envelope | null};
export const useEnvelope = (): EnvelopeValues => {
  const frame = useCurrentFrame();
  const env = useContext(EnvCtx);
  if (!env) return {enter: 1, exit: 0, frame, env};
  const enter = interpolate(frame, [env.enterStart, env.enterStart + env.enterFrames], [0, 1], {...clamp, easing: EASE.out});
  const exit = interpolate(frame, [env.exitStart, env.exitStart + env.exitFrames], [0, 1], {...clamp, easing: EASE.exit});
  return {enter, exit, frame, env};
};

export const isMoving = (env: Envelope, frame: number) =>
  (frame >= env.enterStart - 1 && frame <= env.enterStart + env.enterFrames + 1) || frame >= env.exitStart - 1;

// Applies the envelope to its children: translateY, CSS blur, opacity. One motion, one curve: calm, premium.
export const Reveal: React.FC<{children: React.ReactNode; rise?: number; blur?: number; style?: React.CSSProperties}> = ({children, rise = T.enterRisePx, blur = T.enterBlurPx, style}) => {
  const {enter, exit, frame, env} = useEnvelope();
  if (env && frame < env.enterStart) return <div style={{opacity: 0, ...style}}>{children}</div>;
  // Position on expo-out; opacity and blur on time with a soft curve, so frame 1 is never a visible jump (round 3).
  const t0 = env ? env.enterStart : 0;
  const len = env ? env.enterFrames : 1;
  const fadeIn = interpolate(frame, [t0, t0 + len * 0.75], [0, 1], {...clamp, easing: EASE.inOut});
  const sharp = interpolate(frame, [t0, t0 + len], [0, 1], {...clamp, easing: EASE.soft});
  const y = rise * (1 - enter) - rise * 0.55 * exit;
  const b = blur * (1 - sharp) + blur * 0.8 * exit;
  const o = Math.min(fadeIn, 1 - exit);
  return (
    <div style={{transform: `translate3d(0, ${y.toFixed(2)}px, 0)`, filter: b > 0.05 ? `blur(${b.toFixed(2)}px)` : undefined, opacity: o, willChange: 'transform', ...style}}>
      {children}
    </div>
  );
};

// @remotion/motion-blur CameraMotionBlur, only while the element moves (shutter 0 = single sample, same tree).
export const MotionBlurWhileMoving: React.FC<{env: Envelope; children: React.ReactNode; samples?: number}> = ({env, children, samples = T.motionBlurSamples}) => {
  const frame = useCurrentFrame();
  return (
    <CameraMotionBlur shutterAngle={isMoving(env, frame) ? T.shutterAngle : 0} samples={samples}>
      {children}
    </CameraMotionBlur>
  );
};

// RGB split amount for the current envelope: decays to 0 as the element settles; returns on exit. Never on faces:
// it is applied to graphic content only.
export const useSplit = () => {
  const {exit, frame, env} = useEnvelope();
  const t = env ? interpolate(frame, [env.enterStart, env.enterStart + env.enterFrames], [0, 1], {...clamp, easing: EASE.soft}) : 1;
  return PRISM.splitPx * ((1 - t) + 0.7 * exit);
};
export const splitFilter = (d: number) =>
  d > 0.15 ? `drop-shadow(${(-d).toFixed(2)}px 0 rgba(255,60,90,0.55)) drop-shadow(${d.toFixed(2)}px 0 rgba(60,190,255,0.55))` : undefined;

// ---------------------------------------------------------------------------------------------------------------
// Monochrome film grain [4.11]. Seeded per frame so it moves like real grain, not a static texture.
export const Grain: React.FC<{opacity?: number; radius?: number | string}> = ({opacity = GLASS.grainOpacity, radius = 0}) => {
  const frame = Math.floor(useCurrentFrame());
  const id = `grain-${frame % 1000}`;
  return (
    <svg style={{position: 'absolute', inset: 0, width: '100%', height: '100%', borderRadius: radius, opacity, pointerEvents: 'none'}}>
      <filter id={id}>
        <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed={frame % 97} stitchTiles="stitch" />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter={`url(#${id})`} />
    </svg>
  );
};

const ringMask: React.CSSProperties = {
  WebkitMask: 'linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)',
  WebkitMaskComposite: 'xor',
  maskComposite: 'exclude',
};

// Prism rim: a hairline border that refracts at the top left corner (light source top left, as in DDN's mark), plus
// one glint that travels the rim and a faint sheen across the face of the glass on entrance.
const PrismRim: React.FC<{radius: number | string; tone: 'dark' | 'light'}> = ({radius, tone}) => {
  const {frame, env} = useEnvelope();
  const s = PRISM.stops;
  const base = tone === 'dark' ? 'rgba(255,255,255,0.10)' : 'rgba(255,255,255,0.55)';
  const rim = `linear-gradient(128deg, ${s[0]} 0%, ${s[1]} 6%, ${s[2]} 12%, ${s[3]} 18%, ${s[4]} 24%, rgba(255,255,255,0.34) 32%, ${base} 46%, ${base} 78%, rgba(255,255,255,${tone === 'dark' ? 0.2 : 0.7}) 100%)`;
  const t = env ? (frame - env.enterStart) / PRISM.sweepFrames : 2;
  const glintOn = t > -0.1 && t < 1.1;
  const pos = -30 + 160 * EASE.inOut(Math.max(0, Math.min(1, t)));
  const fade = Math.sin(Math.PI * Math.max(0, Math.min(1, t)));
  const glint = `linear-gradient(115deg, transparent ${pos - 14}%, ${s[0]} ${pos - 8}%, ${s[1]} ${pos - 4}%, ${s[2]} ${pos}%, ${s[3]} ${pos + 4}%, ${s[4]} ${pos + 8}%, transparent ${pos + 14}%)`;
  const sheen = `linear-gradient(115deg, transparent ${pos - 18}%, rgba(255,255,255,${tone === 'dark' ? 0.07 : 0.18}) ${pos}%, transparent ${pos + 18}%)`;
  return (
    <>
      {glintOn ? <div style={{position: 'absolute', inset: 0, borderRadius: radius, background: sheen, opacity: fade, pointerEvents: 'none'}} /> : null}
      <div style={{position: 'absolute', inset: 0, borderRadius: radius, padding: PRISM.rimPx, background: rim, pointerEvents: 'none', ...ringMask}} />
      {glintOn ? <div style={{position: 'absolute', inset: 0, borderRadius: radius, padding: PRISM.rimPx + 0.5, background: glint, opacity: fade, pointerEvents: 'none', ...ringMask}} /> : null}
    </>
  );
};

// Frosted glass plate (v2). Layers, bottom to top: real frost (aligned blurred footage, smoked), Wine to Slate tint,
// top sheen, grain, inner highlight, prism rim. Content gets the entrance RGB split. Hugs its content.
export const FrostedGlass: React.FC<{
  children: React.ReactNode; padX?: number; padY?: number; radius?: number | string; tone?: 'dark' | 'light'; prism?: boolean; style?: React.CSSProperties; contentStyle?: React.CSSProperties;
}> = ({children, padX = 56, padY = 36, radius = GLASS.radiusPx, tone = 'dark', prism = true, style, contentStyle}) => {
  const {source} = useFootage();
  const d = useSplit();
  const dark = tone === 'dark';
  const fill = source ? (dark ? GLASS.tint : GLASS.lightTint) : dark ? GLASS.fallbackDark : GLASS.fallbackLight;
  const filter = dark ? `brightness(${GLASS.smoke}) saturate(${GLASS.saturate})` : `brightness(${GLASS.lightSmoke}) saturate(1.05)`;
  return (
    <div style={{position: 'relative', borderRadius: radius, padding: `${padY}px ${padX}px`,
      boxShadow: dark ? '0 22px 60px rgba(18,8,12,0.30), 0 2px 8px rgba(18,8,12,0.18)' : '0 22px 60px rgba(40,24,28,0.22), 0 2px 8px rgba(40,24,28,0.12)', ...style}}>
      <div style={{position: 'absolute', inset: 0, borderRadius: radius, overflow: 'hidden'}}>
        <Frost blurPx={GLASS.blurPx} filter={filter} radius={radius} />
        <div style={{position: 'absolute', inset: 0, background: fill}} />
        <div style={{position: 'absolute', inset: 0, background: `linear-gradient(180deg, rgba(255,255,255,${dark ? 0.075 : 0.25}) 0%, rgba(255,255,255,0) 42%)`}} />
        <Grain radius={radius} opacity={dark ? GLASS.grainOpacity : GLASS.grainOpacity * 0.7} />
        <div style={{position: 'absolute', inset: 0, borderRadius: radius, boxShadow: `inset 0 1px 0 rgba(255,255,255,${dark ? 0.22 : 0.85}), inset 0 -1px 0 rgba(255,255,255,${dark ? 0.04 : 0.3})`}} />
      </div>
      {prism ? <PrismRim radius={radius} tone={tone} /> : null}
      <div style={{position: 'relative', filter: splitFilter(d), ...contentStyle}}>{children}</div>
    </div>
  );
};
export const GlassPlate = FrostedGlass; // v1 name

// Typewriter count: stepped, linear [3, 4.2].
export const typedCount = (frame: number, start: number, len: number, charsPerFrame: number) =>
  Math.max(0, Math.min(len, Math.floor((frame - start) * charsPerFrame)));

// Source tag [4.2 role tag, 4.7 terminal tag]: Deep Red bar, Geist Mono white, +25 % in v2.
// v2: the bar grows smoothly (ddn-out) and each character fades up over 3 f instead of popping.
export const MonoTag: React.FC<{text: string; startFrame: number; charsPerFrame?: number; style?: React.CSSProperties}> = ({text, startFrame, charsPerFrame = T.tagCharsPerFrame, style}) => {
  const frame = useCurrentFrame();
  onScreen(text, 'MonoTag');
  const typeFrames = text.length / charsPerFrame;
  const bar = interpolate(frame, [startFrame, startFrame + typeFrames + 4], [0, 1], {...clamp, easing: EASE.out});
  const box: React.CSSProperties = {display: 'inline-flex', alignItems: 'center', height: TYPE.tagBar, padding: '0 13px', fontFamily: FONT.mono, fontWeight: 400,
    fontSize: TYPE.tag, color: C.white, whiteSpace: 'pre', letterSpacing: 0, borderRadius: 4, ...style};
  return (
    <div style={{position: 'relative', display: 'inline-block'}}>
      <div style={{position: 'absolute', inset: 0, background: C.deepRed, borderRadius: 4, transformOrigin: 'left center', transform: `scaleX(${bar})`, opacity: bar > 0 ? 1 : 0}} />
      <div style={{...box, position: 'relative'}}>
        {[...text].map((ch, i) => (
          <span key={i} style={{opacity: interpolate(frame, [startFrame + 2 + i / charsPerFrame, startFrame + 5 + i / charsPerFrame], [0, 1], clamp)}}>{ch}</span>
        ))}
      </div>
    </div>
  );
};

// Masked rise: content emerges from under its own bottom edge (or a hairline) [4.5], ddn-out, with blur to sharp.
export const Rise: React.FC<{children: React.ReactNode; startFrame: number; frames?: number; distance?: number; style?: React.CSSProperties}> = ({children, startFrame, frames = T.riseFrames, distance = 0.9, style}) => {
  const frame = useCurrentFrame();
  // One DOM structure before, during and after the rise, so layout can never change when it starts (round 3).
  const p = interpolate(frame, [startFrame, startFrame + frames], [0, 1], {...clamp, easing: EASE.out});
  const o = interpolate(frame, [startFrame, startFrame + frames * 0.75], [0, 1], {...clamp, easing: EASE.inOut});
  const b = 6 * (1 - interpolate(frame, [startFrame, startFrame + frames], [0, 1], {...clamp, easing: EASE.soft}));
  return (
    <div style={{overflow: 'hidden', paddingTop: 8, paddingBottom: 8, paddingLeft: 12, paddingRight: 12, marginBottom: -8, marginLeft: -12, marginRight: -12, ...style, marginTop: ((style?.marginTop as number) ?? 0) - 8}}>
      <div style={{transform: `translateY(${((1 - p) * distance * 100).toFixed(3)}%)`, opacity: o, filter: b > 0.05 ? `blur(${b.toFixed(2)}px)` : undefined}}>{children}</div>
    </div>
  );
};

// Counter [4.6]: ddn-inout, lands on the round target and holds.
export const useCount = (from: number, to: number, startFrame: number, frames: number = T.countFrames) => {
  const frame = useCurrentFrame();
  return interpolate(frame, [startFrame, startFrame + frames], [from, to], {...clamp, easing: EASE.inOut});
};

export const Hairline: React.FC<{width: number | string; startFrame: number; color?: string; frames?: number}> = ({width, startFrame, color = 'rgba(255,255,255,0.55)', frames = T.riseFrames}) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [startFrame, startFrame + frames], [0, 1], {...clamp, easing: EASE.out});
  return <div style={{height: 1, width, background: color, transformOrigin: 'left center', transform: `scaleX(${p})`}} />;
};

// Time scale so a graphic driven by a short line still completes its build before the line ends.
export const buildScale = (durationInFrames: number, idealBuild: number) => Math.max(0.45, Math.min(1, (durationInFrames * 0.55) / idealBuild));
