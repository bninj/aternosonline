// Pitch-specific illustrative graphics (v4). All use the DDN v2 system: frosted glass with the DDN-spectrum prism,
// Slot envelope (rise + blur-to-sharp, motion blur while moving, exits ~75 % of entries), ddn-out / ddn-inout easing.
// Text only plus permitted logos; no numbers or claims beyond the fact table.
import React from 'react';
import {AbsoluteFill, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
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
    <FrostedGlass padX={26} padY={18} radius={22}>
      <div style={{display: 'flex', alignItems: 'center', gap: 20}}>
        <Chip size={62} glow={glow * 0.6} />
        <div>
          <div style={{fontFamily: FONT.mono, fontSize: 22, color: 'rgba(255,255,255,0.65)', letterSpacing: '0.04em'}}>AI chip</div>
          <div style={{display: 'flex', alignItems: 'baseline', gap: 10}}>
            <div style={{...display('medium', 36, -0.01), color: C.white, whiteSpace: 'nowrap'}}>Waiting for data</div>
            <div style={{display: 'flex', gap: 6}}>
              {[0, 1, 2].map((i) => {
                const ph = ((frame - 8 - i * 6) % cycle + cycle) % cycle;
                const on = frame >= 8 + i * 6 ? interpolate(ph, [0, 6, 12, 18], [0.25, 1, 1, 0.25], cl) : 0.25;
                return <div key={i} style={{width: 8, height: 8, borderRadius: 4, background: C.red, opacity: on}} />;
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
    <FrostedGlass padX={26} padY={14} radius={999}>
      <div style={{display: 'flex', alignItems: 'center', gap: 16}}>
        <Mic size={28} color={C.red} />
        <VoiceBars voice={voice} absFrame={from + frame} bars={14} height={30} width={4} />
        <div style={{...display('medium', 34, -0.01), color: C.white, whiteSpace: 'nowrap'}}>{text}</div>
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
  const numSize = 78;
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
          <div style={{fontFamily: FONT.mono, fontSize: 24, color: 'rgba(255,255,255,0.7)', letterSpacing: '0.06em'}}>CHIPS BUSY</div>
          <div style={{...display('regular', numSize, -0.02), lineHeight: 1, color: C.white, fontFeatureSettings: '"tnum" 1', whiteSpace: 'nowrap'}}>{lit}%</div>
          <div style={{marginTop: 12, height: TYPE.tagBar}}><MonoTag text={p.source} startFrame={p.landAt + 2} /></div>
        </div>
      </div>
      {p.mode === 'ddn' ? (
        <div style={{height: 86 * costIn, overflow: 'hidden', opacity: costIn}}>
          <div style={{paddingTop: 16}}>
            <div style={{display: 'flex', alignItems: 'baseline', justifyContent: 'space-between'}}>
              <div style={{fontFamily: FONT.mono, fontSize: 24, color: 'rgba(255,255,255,0.75)', letterSpacing: '0.06em'}}>COST PER TOKEN</div>
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
// Streaming-style logo tiles in a row, waterfall entry (staggered arrival from below, ddn-out).
export const LogoTiles: React.FC<SlotProps & {items: {logo: LogoId; at: number}[]; tileW?: number; tileH?: number; logoH?: number}> = (p) => (
  <Slot {...p} name="LogoTiles">
    {() => <LogoTilesInner items={p.items} tileW={p.tileW ?? 196} tileH={p.tileH ?? 110} logoH={p.logoH ?? 46} />}
  </Slot>
);
const LogoTilesInner: React.FC<{items: {logo: LogoId; at: number}[]; tileW: number; tileH: number; logoH: number}> = ({items, tileW, tileH, logoH}) => {
  const frame = useCurrentFrame();
  return (
    <div style={{display: 'flex', gap: 14}}>
      {items.map((it, i) => {
        const pr = interpolate(frame, [it.at, it.at + 16], [0, 1], {...cl, easing: EASE.out});
        const o = interpolate(frame, [it.at, it.at + 10], [0, 1], {...cl, easing: EASE.inOut});
        const bl = 1 - interpolate(frame, [it.at, it.at + 16], [0, 1], {...cl, easing: EASE.ui});
        const l = LOGOS[it.logo];
        const h = Math.min(logoH, (tileW - 40) / l.aspect);
        return (
          <div key={i} style={{opacity: o, transform: `translateY(${(1 - pr) * 34}px)`, filter: bl > 0.01 ? `blur(${(8 * bl).toFixed(2)}px)` : undefined}}>
            <FrostedGlass tone="light" padX={0} padY={0} radius={16} style={{width: tileW, height: tileH}}>
              <div style={{width: tileW, height: tileH, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
                <Logo id={it.logo} height={h} />
              </div>
            </FrostedGlass>
          </div>
        );
      })}
    </div>
  );
};

// ---------------------------------------------------------------------------------------------------------------
// Blockbuster: the official logo arrives, then fades to grey (the obsolete one). The artwork itself is untouched;
// only the whole tile is desaturated and dimmed after it has been seen in full colour.
export const ObsoleteLogo: React.FC<SlotProps & {logo: LogoId; greyAt: number; logoH?: number}> = (p) => (
  <Slot {...p} name="ObsoleteLogo">{() => <ObsoleteInner logo={p.logo} greyAt={p.greyAt} logoH={p.logoH ?? 104} />}</Slot>
);
const ObsoleteInner: React.FC<{logo: LogoId; greyAt: number; logoH: number}> = ({logo, greyAt, logoH}) => {
  const frame = useCurrentFrame();
  const g = interpolate(frame, [greyAt, greyAt + 24], [0, 1], {...cl, easing: EASE.inOut});
  const pad = Math.round(logoH * LOGOS[logo].clear);
  return (
    <div style={{filter: g > 0.01 ? `grayscale(${g.toFixed(3)}) brightness(${(1 - 0.12 * g).toFixed(3)})` : undefined, opacity: 1 - 0.35 * g}}>
      <FrostedGlass tone="light" padX={pad + 10} padY={pad} radius={22}>
        <Logo id={logo} height={logoH} />
      </FrostedGlass>
    </div>
  );
};

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
