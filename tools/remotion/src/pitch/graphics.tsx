// Pitch-specific illustrative graphics (v4). All use the DDN v2 system: frosted glass with the DDN-spectrum prism,
// Slot envelope (rise + blur-to-sharp, motion blur while moving, exits ~75 % of entries), ddn-out / ddn-inout easing.
// Text only plus permitted logos; no numbers or claims beyond the fact table.
import React, {useMemo} from 'react';
import {getLength, getPointAtLength} from '@remotion/paths';
import chair from './chair_contour.json';
import {AbsoluteFill, interpolate, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {getWaveformPortion, useAudioData} from '@remotion/media-utils';
import {C, display, EASE, FONT, FrostedGlass, Grain, Hairline, Logo, LogoId, LOGOS, MonoTag, onScreen, Rise, Slot, SlotProps, T, TYPE} from '../ddn';

const cl = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// ---------------------------------------------------------------------------------------------------------------
// Live voice bars: the real voice track drives the bars (no idle wobble: they move only when he speaks).
const VoiceBars: React.FC<{voice: string; absFrame: number; bars?: number; height?: number; color?: string; width?: number}> = ({voice, absFrame, bars = 18, height = 30, color = C.white, width = 4}) => {
  const {fps} = useVideoConfig();
  const audio = useAudioData(staticFile(voice));
  const t = absFrame / fps;
  const amps = audio
    ? getWaveformPortion({audioData: audio, startTimeInSeconds: Math.max(0, t - 0.45), durationInSeconds: 0.45, numberOfSamples: bars, normalize: false}).map((b) => b.amplitude)
    : new Array(bars).fill(0);
  return (
    <div style={{display: 'flex', alignItems: 'center', gap: width * 0.75, height}}>
      {amps.map((a, i) => (
        <div key={i} style={{width, height: Math.max(width, Math.min(1, a * 3.2) * height), borderRadius: width / 2, background: color, opacity: 0.55 + 0.45 * Math.min(1, a * 3)}} />
      ))}
    </div>
  );
};

const Mic: React.FC<{size?: number; color?: string}> = ({size = 26, color = C.white}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.8} strokeLinecap="round">
    <rect x="8.5" y="3" width="7" height="11.5" rx="3.5" />
    <path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3" />
  </svg>
);

// ---------------------------------------------------------------------------------------------------------------
// Hook: an idle AI chip, "Waiting for data", with a typing-style status (three dots fill in sequence).
const Chip: React.FC<{size: number; glow: number}> = ({size, glow}) => {
  const pins = [0.28, 0.5, 0.72];
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" style={{display: 'block', overflow: 'visible'}}>
      {pins.map((p) => (
        <g key={p} stroke="rgba(255,255,255,0.7)" strokeWidth={2} strokeLinecap="round">
          <line x1={64 * p} y1={4} x2={64 * p} y2={11} /><line x1={64 * p} y1={53} x2={64 * p} y2={60} />
          <line x1={4} y1={64 * p} x2={11} y2={64 * p} /><line x1={53} y1={64 * p} x2={60} y2={64 * p} />
        </g>
      ))}
      <rect x={12} y={12} width={40} height={40} rx={7} stroke="rgba(255,255,255,0.9)" strokeWidth={2} />
      <rect x={22} y={22} width={20} height={20} rx={4} fill={`rgba(237,39,56,${0.15 + 0.5 * glow})`} stroke={C.red} strokeWidth={1.5} />
    </svg>
  );
};

export const ChipStatus: React.FC<SlotProps & {emphAt?: number}> = (p) => (
  <Slot {...p} name="ChipStatus">
    {() => <ChipStatusInner emphAt={p.emphAt} />}
  </Slot>
);
const ChipStatusInner: React.FC<{emphAt?: number}> = ({emphAt}) => {
  const frame = useCurrentFrame();
  const glow = emphAt !== undefined ? interpolate(frame, [emphAt - 4, emphAt + 8], [0, 1], {...cl, easing: EASE.inOut}) : 0;
  const cycle = 24;
  return (
    <FrostedGlass padX={40} padY={28} radius={30}>
      <div style={{display: 'flex', alignItems: 'center', gap: 30}}>
        <Chip size={98} glow={glow * 0.6} />
        <div>
          <div style={{fontFamily: FONT.mono, fontSize: 32, color: 'rgba(255,255,255,0.7)', letterSpacing: '0.04em'}}>AI chip</div>
          <div style={{display: 'flex', alignItems: 'baseline', gap: 16}}>
            <div style={{...display('medium', 58, -0.01), color: C.white, whiteSpace: 'nowrap'}}>Waiting for data</div>
            <div style={{display: 'flex', gap: 9}}>
              {[0, 1, 2].map((i) => {
                const ph = ((frame - 8 - i * 6) % cycle + cycle) % cycle;
                const on = frame >= 8 + i * 6 ? interpolate(ph, [0, 6, 12, 18], [0.25, 1, 1, 0.25], cl) : 0.25;
                return <div key={i} style={{width: 12, height: 12, borderRadius: 6, background: C.red, opacity: on}} />;
              })}
            </div>
          </div>
        </div>
      </div>
    </FrostedGlass>
  );
};

// ---------------------------------------------------------------------------------------------------------------
// "Sky Q voice search": a small pill with a mic and the live voice bars.
export const VoicePill: React.FC<SlotProps & {text: string; voice: string}> = (p) => (
  <Slot {...p} name="VoicePill">{() => <VoicePillInner text={p.text} voice={p.voice} from={p.from} />}</Slot>
);
const VoicePillInner: React.FC<{text: string; voice: string; from: number}> = ({text, voice, from}) => {
  const frame = useCurrentFrame();
  onScreen(text, 'VoicePill');
  return (
    <FrostedGlass padX={40} padY={22} radius={999}>
      <div style={{display: 'flex', alignItems: 'center', gap: 24}}>
        <Mic size={44} color={C.red} />
        <VoiceBars voice={voice} absFrame={from + frame} bars={14} height={48} width={6} />
        <div style={{...display('medium', 54, -0.01), color: C.white, whiteSpace: 'nowrap'}}>{text}</div>
      </div>
    </FrostedGlass>
  );
};

// ---------------------------------------------------------------------------------------------------------------
// "Imagine asking, Sky, make me scared": a voice bubble listens (live bars), then the request types on with his words.
export const VoiceChat: React.FC<SlotProps & {text: string; voice: string; typeStart: number; typeEnd: number}> = (p) => (
  <Slot {...p} name="VoiceChat">{({side}) => <VoiceChatInner {...p} tail={side === 'right' ? 'right' : 'left'} />}</Slot>
);
const VoiceChatInner: React.FC<{text: string; voice: string; typeStart: number; typeEnd: number; from: number; tail: 'left' | 'right'}> = ({text, voice, typeStart, typeEnd, from, tail}) => {
  const frame = useCurrentFrame();
  onScreen(text, 'VoiceChat');
  const rate = text.length / Math.max(1, typeEnd - typeStart);
  const n = Math.max(0, Math.min(text.length, Math.floor((frame - typeStart) * rate)));
  const r = 30;
  const radius = tail === 'left' ? `${r}px ${r}px ${r}px 6px` : `${r}px ${r}px 6px ${r}px`;
  const lab = display('regular', 48, -0.005);
  return (
    <FrostedGlass padX={34} padY={22} radius={radius}>
      <div style={{display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10}}>
        <Mic size={22} color={C.red} />
        <VoiceBars voice={voice} absFrame={from + frame} bars={20} height={22} width={3} color="rgba(255,255,255,0.85)" />
      </div>
      <div style={{...lab, lineHeight: 1.15, color: C.white, whiteSpace: 'pre', position: 'relative'}}>
        <span style={{visibility: 'hidden'}}>{text}</span>
        <span style={{position: 'absolute', left: 0, top: 0}}>
          {[...text].map((ch, i) => (
            <span key={i} style={{opacity: interpolate(frame, [typeStart + i / rate, typeStart + i / rate + 3], [0, 1], cl)}}>{ch}</span>
          ))}
        </span>
        {n > 0 && n < text.length ? null : null}
      </div>
    </FrostedGlass>
  );
};

// ---------------------------------------------------------------------------------------------------------------
// Chip-use grid: 100 tiles (10 x 10), so "5 %" is literally 5 lit tiles and "99 %" is 99. Evolves in place:
//  mode 'idle'  : count 0 -> 5 landing on the spoken "5%", tag "Cast AI, enterprise average".
//  mode 'ddn'   : data streams in from the left (flowAt), the grid fills 5 -> 99 landing on "99%", then a cost bar
//                 shrinks to a quarter landing on "75%"; tags "per DDN".
const ORDER = (() => {
  // fixed pseudo-random fill order (deterministic), so lit tiles look like a real utilisation map, not a progress bar
  const a = Array.from({length: 100}, (_, i) => i);
  let s = 7;
  for (let i = a.length - 1; i > 0; i--) {
    s = (s * 9301 + 49297) % 233280;
    const j = Math.floor((s / 233280) * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  const rank = new Array(100);
  a.forEach((tile, k) => (rank[tile] = k));
  return rank as number[];
})();

export type ChipGridProps = SlotProps & {
  mode: 'idle' | 'ddn';
  landAt: number; // frame in slot: 5 % (idle) or 99 % (ddn) lands
  countFrames?: number;
  flowAt?: number; // ddn: data starts streaming in
  costFrom?: number; // ddn: cost bar appears
  costLandAt?: number; // ddn: 75 % lower lands
  source: string;
  costSource?: string;
};

export const ChipGrid: React.FC<ChipGridProps> = (p) => <Slot {...p} name={`ChipGrid ${p.mode}`}>{() => <ChipGridInner p={p} />}</Slot>;

const ChipGridInner: React.FC<{p: ChipGridProps}> = ({p}) => {
  const frame = useCurrentFrame();
  const cf = p.countFrames ?? 30;
  const [a, b] = p.mode === 'idle' ? [0, 5] : [5, 99];
  const v = interpolate(frame, [p.landAt - cf, p.landAt], [a, b], {...cl, easing: EASE.inOut});
  const lit = Math.floor(v + 1e-6);
  const TILE = 10;
  const GAP = 3;
  const gridW = 10 * TILE + 9 * GAP;
  const flow = p.flowAt !== undefined ? interpolate(frame, [p.flowAt, p.flowAt + 12], [0, 1], {...cl, easing: EASE.inOut}) * interpolate(frame, [p.landAt + 6, p.landAt + 24], [1, 0], cl) : 0;
  const costIn = p.costFrom !== undefined ? interpolate(frame, [p.costFrom, p.costFrom + 14], [0, 1], {...cl, easing: EASE.out}) : 0;
  const costP = p.costLandAt !== undefined ? interpolate(frame, [p.costLandAt - 24, p.costLandAt], [0, 1], {...cl, easing: EASE.inOut}) : 0;
  const costPct = Math.floor(75 * costP + 1e-6);
  const numSize = 84;
  return (
    <FrostedGlass padX={26} padY={22}>
      <div style={{display: 'flex', alignItems: 'center', gap: 24}}>
        <div style={{position: 'relative', width: gridW, height: gridW}}>
          {/* data streams: thin lines flowing into the grid from the left (DDN Infinia feeding the chips) */}
          {flow > 0 ? (
            <svg width={120} height={gridW} style={{position: 'absolute', right: gridW + 4, top: 0, opacity: flow, overflow: 'visible'}}>
              {[0.15, 0.38, 0.62, 0.85].map((y, i) => (
                <line key={i} x1={0} y1={gridW * y} x2={120} y2={gridW * y} stroke={i % 2 ? C.red : 'rgba(255,255,255,0.85)'} strokeWidth={2} strokeLinecap="round"
                  strokeDasharray="10 14" strokeDashoffset={-(frame * 3 + i * 7)} />
              ))}
            </svg>
          ) : null}
          {Array.from({length: 100}, (_, k) => {
            const on = ORDER[k] < lit;
            const fresh = on && ORDER[k] >= lit - 3;
            return (
              <div key={k} style={{position: 'absolute', left: (k % 10) * (TILE + GAP), top: Math.floor(k / 10) * (TILE + GAP), width: TILE, height: TILE, borderRadius: 2.5,
                background: on ? C.red : 'rgba(255,255,255,0.13)', boxShadow: fresh ? '0 0 8px rgba(237,39,56,0.9)' : undefined}} />
            );
          })}
        </div>
        <div>
          <div style={{fontFamily: FONT.mono, fontSize: 26, color: 'rgba(255,255,255,0.78)', letterSpacing: '0.06em'}}>CHIPS BUSY</div>
          <div style={{...display('regular', numSize, -0.02), lineHeight: 1, color: C.white, fontFeatureSettings: '"tnum" 1', whiteSpace: 'nowrap'}}>{lit}%</div>
          <div style={{marginTop: 12, height: TYPE.tagBar}}><MonoTag text={p.source} startFrame={p.landAt + 2} /></div>
        </div>
      </div>
      {p.mode === 'ddn' ? (
        <div style={{height: 86 * costIn, overflow: 'hidden', opacity: costIn}}>
          <div style={{paddingTop: 16}}>
            <div style={{display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 20}}>
              <div style={{fontFamily: FONT.mono, fontSize: 26, color: 'rgba(255,255,255,0.8)', letterSpacing: '0.06em'}}>COST PER TOKEN</div>
              <div style={{...display('medium', 34, -0.01), color: C.white, fontFeatureSettings: '"tnum" 1'}}>{costPct}% lower</div>
            </div>
            <div style={{position: 'relative', height: 12, marginTop: 10, borderRadius: 6, background: 'rgba(255,255,255,0.12)'}}>
              <div style={{position: 'absolute', left: 0, top: 0, bottom: 0, width: `${100 - 75 * costP}%`, borderRadius: 6, background: C.red}} />
            </div>
          </div>
        </div>
      ) : null}
    </FrostedGlass>
  );
};

// ---------------------------------------------------------------------------------------------------------------
// Logos float on ONE translucent light-frost panel (no opaque tiles): official artwork, unaltered, about 1.5x the v1
// size, arriving as a waterfall (staggered rise from below with blur to sharp, ddn-out).
export const LogoTiles: React.FC<SlotProps & {items: {logo: LogoId; at: number}[]; logoH?: number; gap?: number}> = (p) => (
  <Slot {...p} name="LogoTiles">
    {() => <LogoTilesInner items={p.items} logoH={p.logoH ?? 72} gap={p.gap ?? 44} />}
  </Slot>
);
const LogoTilesInner: React.FC<{items: {logo: LogoId; at: number}[]; logoH: number; gap: number}> = ({items, logoH, gap}) => {
  const frame = useCurrentFrame();
  return (
    <FrostedGlass tone="light" tint="rgba(250,247,245,0.52)" padX={34} padY={26} radius={22}>
      <div style={{display: 'flex', alignItems: 'center', gap}}>
        {items.map((it, i) => {
          const pr = interpolate(frame, [it.at, it.at + 16], [0, 1], {...cl, easing: EASE.out});
          const o = interpolate(frame, [it.at, it.at + 10], [0, 1], {...cl, easing: EASE.inOut});
          const bl = 1 - interpolate(frame, [it.at, it.at + 16], [0, 1], {...cl, easing: EASE.ui});
          const l = LOGOS[it.logo];
          const h = Math.min(logoH, 300 / l.aspect);
          return (
            <div key={i} style={{opacity: o, transform: `translateY(${((1 - pr) * 30).toFixed(2)}px)`, filter: `${bl > 0.01 ? `blur(${(8 * bl).toFixed(2)}px) ` : ''}drop-shadow(0 2px 6px rgba(20,10,14,0.18))`}}>
              <Logo id={it.logo} height={h} />
            </div>
          );
        })}
      </div>
    </FrostedGlass>
  );
};

// ---------------------------------------------------------------------------------------------------------------
// Blockbuster BREAKS: the official logo lands (rise + blur to sharp) floating over the footage with a soft shadow,
// holds a beat, hairline cracks run from the impact point (with a DDN-spectrum glint), then it splits into a few large
// shards along those cracks that drift apart (motion blurred) and fade. The artwork is never redrawn: every shard is
// the same official logo, clipped to its polygon.
const SHARDS: {poly: [number, number][]; dir: [number, number]; rot: number}[] = [
  {poly: [[0, 0], [0.42, 0], [0.36, 0.46], [0, 0.58]], dir: [-1, -0.7], rot: -9},
  {poly: [[0.42, 0], [0.78, 0], [0.55, 0.42], [0.36, 0.46]], dir: [0.2, -1], rot: 6},
  {poly: [[0.78, 0], [1, 0], [1, 0.52], [0.55, 0.42]], dir: [1, -0.6], rot: 11},
  {poly: [[0, 0.58], [0.36, 0.46], [0.47, 1], [0, 1]], dir: [-1, 0.8], rot: 8},
  {poly: [[0.36, 0.46], [0.55, 0.42], [0.72, 1], [0.47, 1]], dir: [0.1, 1], rot: -5},
  {poly: [[0.55, 0.42], [1, 0.52], [1, 1], [0.72, 1]], dir: [1, 0.7], rot: -12},
];
const IMPACT: [number, number] = [0.47, 0.45];

export const ShatterLogo: React.FC<SlotProps & {logo: LogoId; crackAt: number; breakAt: number; logoH?: number}> = (p) => (
  <Slot {...p} name="ShatterLogo" exitFrames={p.exitFrames ?? 6}>{() => <ShatterInner logo={p.logo} crackAt={p.crackAt} breakAt={p.breakAt} logoH={p.logoH ?? 150} />}</Slot>
);
const ShatterInner: React.FC<{logo: LogoId; crackAt: number; breakAt: number; logoH: number}> = ({logo, crackAt, breakAt, logoH}) => {
  const frame = useCurrentFrame();
  const lw = logoH * LOGOS[logo].aspect;
  const crack = interpolate(frame, [crackAt, crackAt + 4], [0, 1], {...cl, easing: EASE.out});
  const t = interpolate(frame, [breakAt, breakAt + 18], [0, 1], {...cl, easing: Easing4in});
  const fade = interpolate(frame, [breakAt + 4, breakAt + 18], [1, 0], {...cl, easing: EASE.inOut});
  const speed = frame >= breakAt && frame <= breakAt + 18 ? (Easing4in(Math.min(1, (frame - breakAt + 1) / 18)) - Easing4in(Math.max(0, (frame - breakAt) / 18))) : 0;
  const st = ['rgba(254,117,0,0.95)', 'rgba(237,39,56,0.95)', 'rgba(117,148,178,0.9)'];
  const cracks = SHARDS.flatMap((sh) => sh.poly).filter(([x, y]) => x > 0 && x < 1 && y > 0 && y < 1);
  return (
    <div style={{position: 'relative', width: lw, height: logoH, filter: 'drop-shadow(0 6px 18px rgba(10,6,8,0.35))'}}>
      {SHARDS.map((sh, i) => {
        const dx = sh.dir[0] * 150 * t;
        const dy = sh.dir[1] * 110 * t + 70 * t * t; // a little gravity
        const clip = `polygon(${sh.poly.map(([x, y]) => `${(x * 100).toFixed(1)}% ${(y * 100).toFixed(1)}%`).join(', ')})`;
        const mb = Math.min(10, speed * 260);
        return (
          <div key={i} style={{position: 'absolute', inset: 0, clipPath: clip, opacity: t > 0 ? fade : 1,
            transform: `translate(${dx.toFixed(2)}px, ${dy.toFixed(2)}px) rotate(${(sh.rot * 1.8 * t).toFixed(2)}deg)`, transformOrigin: `${IMPACT[0] * 100}% ${IMPACT[1] * 100}%`,
            filter: mb > 0.2 ? `blur(${mb.toFixed(2)}px)` : undefined}}>
            <Logo id={logo} height={logoH} />
          </div>
        );
      })}
      {/* hairline cracks from the impact point, glinting in DDN's spectrum, gone once the shards separate */}
      <svg width={lw} height={logoH} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible', opacity: crack * (1 - t * 3 > 0 ? 1 - t * 3 : 0)}}>
        <defs>
          <linearGradient id="crackglint" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor={st[0]} /><stop offset="0.5" stopColor="#FFFFFF" /><stop offset="1" stopColor={st[2]} />
          </linearGradient>
        </defs>
        {cracks.map(([x, y], i) => {
          const x0 = IMPACT[0] * lw;
          const y0 = IMPACT[1] * logoH;
          return <line key={i} x1={x0} y1={y0} x2={x0 + (x * lw - x0) * crack} y2={y0 + (y * logoH - y0) * crack} stroke="url(#crackglint)" strokeWidth={3.5} strokeLinecap="round" />;
        })}
      </svg>
    </div>
  );
};
const Easing4in = (x: number) => Math.pow(x, 2.2); // accelerating break-away

// ---------------------------------------------------------------------------------------------------------------
// End card v4 [4.10A 2026 outro]: #E7E7E7 dissolves in, thin pink-red circles grow and orbit, then converge into the
// logo ring's position and hand over to the official DDN logo; the line rises from under a hairline.
export const EndBuild: React.FC<{from: number; durationInFrames: number; line?: string; logoHeight?: number}> = ({from, durationInFrames, line = 'Keep the chips busy.', logoHeight = 118}) => {
  onScreen(line, 'EndBuild');
  return (
    <Sequence from={from} durationInFrames={durationInFrames} name="EndBuild">
      <EndBuildInner line={line} logoHeight={logoHeight} />
    </Sequence>
  );
};
const EndBuildInner: React.FC<{line: string; logoHeight: number}> = ({line, logoHeight}) => {
  const frame = useCurrentFrame();
  const bg = interpolate(frame, [0, 14], [0, 1], {...cl, easing: EASE.inOut});
  const lw = logoHeight * LOGOS.ddn.aspect;
  // ring centre inside the logo artwork: ring spans x 0..93 of the 280 x 93 viewBox
  const ringR = (logoHeight * 0.5) * 0.98;
  const ringCx = -lw / 2 + logoHeight * 0.5;
  const build = interpolate(frame, [4, 40], [0, 1], {...cl, easing: EASE.inOut}); // circles grow and orbit
  const converge = interpolate(frame, [30, 44], [0, 1], {...cl, easing: EASE.inOut}); // circles collapse onto the ring
  const logoIn = interpolate(frame, [38, 50], [0, 1], {...cl, easing: EASE.inOut});
  const circles = [0, 1, 2, 3];
  return (
    <AbsoluteFill style={{opacity: bg}}>
      <AbsoluteFill style={{background: C.outroGray}} />
      <Grain opacity={0.06} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
          <div style={{position: 'relative', width: lw, height: logoHeight}}>
            <svg width={lw} height={logoHeight} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible', opacity: 1 - logoIn}}>
              {circles.map((i) => {
                const ang = (i / circles.length) * Math.PI * 2 + build * Math.PI * 1.6;
                const orbit = ringR * 0.55 * build * (1 - converge);
                const r = ringR * (0.25 + 0.55 * build) * (1 - converge) + ringR * converge;
                const cx = lw / 2 + ringCx + Math.cos(ang) * orbit;
                const cy = logoHeight / 2 + Math.sin(ang) * orbit;
                return <circle key={i} cx={cx} cy={cy} r={Math.max(0.5, r)} fill="none" stroke={C.pinkRed} strokeOpacity={0.8} strokeWidth={1.4} />;
              })}
            </svg>
            <div style={{position: 'absolute', inset: 0, opacity: logoIn, transform: `scale(${(0.985 + 0.015 * logoIn).toFixed(4)})`}}>
              <Logo id="ddn" height={logoHeight} />
            </div>
          </div>
          <div style={{marginTop: 40, display: 'flex', flexDirection: 'column', alignItems: 'stretch'}}>
            <Hairline width="100%" startFrame={48} color="rgba(32,30,30,0.3)" />
            <Rise startFrame={51} style={{marginTop: 16}}>
              <div style={{...display('medium', 72, -0.02), lineHeight: 1.1, color: C.black, whiteSpace: 'nowrap'}}>{line}</div>
            </Rise>
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export {T};

// ---------------------------------------------------------------------------------------------------------------
// Hook: spotlight on the real AI chair (static tripod shot). SAM 2.1 mask of the chair (scripts in critique log):
//  * a gentle wine-black darkening of everything but the chair (feathered inverse matte),
//  * a soft local lift on the chair itself (screen),
//  * a precise DDN-red contour that draws on around the chair's silhouette, with a DDN-spectrum glint travelling it.
// Rendered inside the footage transform, so it stays locked to the chair through the push-in.

export const ChairSpotlight: React.FC<{dimIn: [number, number]; dimOut: [number, number]; lineIn: [number, number]; offAt: [number, number]}> = ({dimIn, dimOut, lineIn, offAt}) => {
  const frame = useCurrentFrame();
  const off = interpolate(frame, offAt, [1, 0], {...cl, easing: EASE.inOut});
  const dim = Math.min(interpolate(frame, dimIn, [0, 1], {...cl, easing: EASE.inOut}), interpolate(frame, dimOut, [1, 0], {...cl, easing: EASE.inOut}));
  const draw = interpolate(frame, lineIn, [0, 1], {...cl, easing: EASE.inOut});
  const len = useMemo(() => getLength(chair.d), []);
  const g = ((frame - lineIn[0]) * 18) % len; // glint position along the contour (px), one lap per ~2 s
  const gp = getPointAtLength(chair.d, Math.max(0, g));
  const vis = draw * off;
  if (vis <= 0.001 && dim <= 0.001) return null;
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <AbsoluteFill style={{background: 'rgba(14,8,10,0.42)', opacity: dim * off, WebkitMaskImage: `url(${staticFile('pitch/chair_inverse.png')})`, WebkitMaskSize: '100% 100%', maskImage: `url(${staticFile('pitch/chair_inverse.png')})`, maskSize: '100% 100%'}} />
      <AbsoluteFill style={{background: 'rgba(255,240,236,0.22)', mixBlendMode: 'screen', opacity: vis, WebkitMaskImage: `url(${staticFile('pitch/chair_alpha.png')})`, WebkitMaskSize: '100% 100%', maskImage: `url(${staticFile('pitch/chair_alpha.png')})`, maskSize: '100% 100%'}} />
      <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible', opacity: off}}>
        <defs>
          <radialGradient id="chairglint">
            <stop offset="0" stopColor="#FFFFFF" stopOpacity={0.95} /><stop offset="0.35" stopColor="#FE7500" stopOpacity={0.7} />
            <stop offset="0.7" stopColor="#7594B2" stopOpacity={0.25} /><stop offset="1" stopColor="#7594B2" stopOpacity={0} />
          </radialGradient>
        </defs>
        <path d={chair.d} fill="none" stroke={C.red} strokeOpacity={0.35} strokeWidth={9} strokeLinejoin="round" style={{filter: 'blur(6px)'}}
          strokeDasharray={len} strokeDashoffset={len * (1 - draw)} />
        <path d={chair.d} fill="none" stroke={C.red} strokeWidth={2.6} strokeLinejoin="round" strokeLinecap="round"
          strokeDasharray={len} strokeDashoffset={len * (1 - draw)} />
        {draw > 0.98 && gp ? <circle cx={gp.x} cy={gp.y} r={16} fill="url(#chairglint)" /> : null}
      </svg>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------------------------------------------
// DDN bracket name tag [4.2]: "[ ELIUD AWUAH ]". Thin bracket rules with short serifs (taller than the caps); the
// empty brackets open, hold a beat, then the name types on (each new letter fades up over 2 f) and the right bracket
// travels with the last glyph. Name only, no title. Over footage with a soft shadow, as in DDN's series.
const Bracket: React.FC<{side: 'l' | 'r'; h: number}> = ({side, h}) => (
  <svg width={14} height={h} viewBox={`0 0 14 ${h}`} style={{display: 'block', flex: 'none'}}>
    <path d={side === 'l' ? `M12 2 H3 V${h - 2} H12` : `M2 2 H11 V${h - 2} H2`} fill="none" stroke="#FFFFFF" strokeWidth={3} />
  </svg>
);
export const NameTag: React.FC<SlotProps & {name: string; size?: number}> = (p) => (
  <Slot {...p} name="NameTag" enterFrames={p.enterFrames ?? 8}>{() => <NameTagInner name={p.name} size={p.size ?? 46} />}</Slot>
);
const NameTagInner: React.FC<{name: string; size: number}> = ({name, size}) => {
  const frame = useCurrentFrame();
  onScreen(name, 'NameTag');
  const t0 = 12; // brackets hold, then type
  const cpf = 0.5; // one character every 2 frames
  const lab = display('capsName', size);
  const open = interpolate(frame, [2, 10], [0.6, 1], {...cl, easing: EASE.out}); // brackets open from 0.6x cap width
  const n = Math.max(0, (frame - t0) * cpf);
  const chars = [...name];
  const shown = chars.filter((_, i) => i < Math.ceil(n));
  const h = Math.round(size * 0.966 * 1.25);
  return (
    <div style={{display: 'flex', alignItems: 'center', filter: 'drop-shadow(0 2px 10px rgba(10,6,8,0.45))'}}>
      <Bracket side="l" h={h} />
      <div style={{...lab, color: C.white, lineHeight: `${h}px`, whiteSpace: 'pre', padding: `0 ${Math.round(size * 0.22)}px`, minWidth: size * 0.6 * open}}>
        {shown.map((ch, i) => (
          <span key={i} style={{opacity: interpolate(frame, [t0 + i / cpf, t0 + i / cpf + 2], [0, 1], cl)}}>{ch}</span>
        ))}
      </div>
      <Bracket side="r" h={h} />
    </div>
  );
};

// ---------------------------------------------------------------------------------------------------------------
// Logos placed IN the room: large, official artwork, sitting behind the speaker (the person layer is composited on
// top from a SAM 2.1 + ViTMatte alpha). Depth: a touch of blur and atmosphere so they sit on the wall plane, a soft
// glow behind for separation. Positions are px @1920 in footage space (they ride the camera transform).
export type DepthLogoItem = {logo: LogoId; at: number; x: number; y: number; h: number};
export const DepthLogos: React.FC<{from: number; durationInFrames: number; items: DepthLogoItem[]; exitFrames?: number; breakAt?: number; crackAt?: number}> = (p) => (
  <Sequence from={p.from} durationInFrames={p.durationInFrames} name="DepthLogos" layout="none">
    <DepthLogosInner {...p} />
  </Sequence>
);
const DepthLogosInner: React.FC<{durationInFrames: number; items: DepthLogoItem[]; exitFrames?: number}> = ({durationInFrames, items, exitFrames = 10}) => {
  const frame = useCurrentFrame();
  const out = interpolate(frame, [durationInFrames - exitFrames, durationInFrames], [0, 1], {...cl, easing: EASE.exit});
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {items.map((it, i) => {
        const pr = interpolate(frame, [it.at, it.at + 18], [0, 1], {...cl, easing: EASE.out});
        const o = interpolate(frame, [it.at, it.at + 12], [0, 1], {...cl, easing: EASE.inOut}) * (1 - out);
        const bl = 10 * (1 - interpolate(frame, [it.at, it.at + 18], [0, 1], {...cl, easing: EASE.soft})) + 6 * out;
        const w = it.h * LOGOS[it.logo].aspect;
        return (
          <div key={i} style={{position: 'absolute', left: it.x, top: it.y, width: w, height: it.h, opacity: o * 0.96,
            transform: `translateY(${((1 - pr) * 40 - out * 20).toFixed(2)}px) scale(${(0.97 + 0.03 * pr).toFixed(4)})`,
            filter: `blur(${(0.7 + bl).toFixed(2)}px) drop-shadow(0 0 28px rgba(255,255,255,0.18)) drop-shadow(0 10px 24px rgba(10,6,8,0.35))`}}>
            <Logo id={it.logo} height={it.h} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// Blockbuster in the room: lands (rise + blur to sharp), cracks and shatters in place, behind the speaker.
export const DepthShatter: React.FC<{from: number; durationInFrames: number; x: number; y: number; h: number; crackAt: number; breakAt: number}> = (p) => (
  <Sequence from={p.from} durationInFrames={p.durationInFrames} name="DepthShatter" layout="none">
    <DepthShatterInner {...p} />
  </Sequence>
);
const DepthShatterInner: React.FC<{x: number; y: number; h: number; crackAt: number; breakAt: number}> = ({x, y, h, crackAt, breakAt}) => {
  const frame = useCurrentFrame();
  const pr = interpolate(frame, [0, 16], [0, 1], {...cl, easing: EASE.out});
  const o = interpolate(frame, [0, 10], [0, 1], {...cl, easing: EASE.inOut});
  const bl = 10 * (1 - interpolate(frame, [0, 16], [0, 1], {...cl, easing: EASE.soft}));
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{position: 'absolute', left: x, top: y, opacity: o, transform: `translateY(${((1 - pr) * 40).toFixed(2)}px)`, filter: `blur(${(0.6 + bl).toFixed(2)}px)`}}>
        <ShatterInner logo="blockbuster" crackAt={crackAt} breakAt={breakAt} logoH={h} />
      </div>
    </AbsoluteFill>
  );
};

// The speaker, cut out of the same plate by a SAM 2.1 + ViTMatte alpha (VP9 with alpha, frame-aligned to the plate
// range [plateFrom, plateFrom + duration)). Drawn above the depth logos, below the cards and captions.
export const PersonLayer: React.FC<{src: string; plateFrom: number; durationInFrames: number; style: React.CSSProperties}> = ({src, plateFrom, durationInFrames, style}) => (
  <Sequence from={plateFrom} durationInFrames={durationInFrames} name="PersonLayer" layout="none">
    <AbsoluteFill style={style}>
      <OffthreadVideo src={staticFile(src)} transparent muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />
    </AbsoluteFill>
  </Sequence>
);
