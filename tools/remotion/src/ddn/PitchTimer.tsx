import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONT} from './fonts';
import {FrostedGlass} from './primitives';
import {Slot, SlotProps} from './Slot';
import {C, EASE} from './tokens';

// Pitch clock: "the 90 seconds have begun". Frosted capsule, a thin ring and a Geist Mono readout.
// Not on screen all the time: it enters when the clock starts, holds, then animates away (Slot envelope +
// motion blur). For an optional reprise near the end, place a second <PitchTimer variant="reprise"> with the same
// clockZero; it reads the real elapsed time.
//  * Ring: hairline track that draws itself in, Brand Red progress arc (elapsed / total) with a soft head glow.
//  * Digits roll (rise + blur, 6 f, ddn-out) when they change; they never hard cut.
//  * At 00:00 a single soft red pulse leaves the ring: the "go" moment. No ticking SFX implied.
export type PitchTimerProps = SlotProps & {
  clockZero: number; // absolute frame at which the clock reads 00:00 (the 90 s begin)
  totalSeconds?: number; // 90
  showTotal?: boolean; // " / 01:30"
  label?: string; // optional mono eyebrow, e.g. "90 seconds"
  variant?: 'intro' | 'reprise';
  scale?: number; // 1 = 64 px digits
};

const mmss = (s: number) => {
  const t = Math.max(0, Math.floor(s));
  return `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`;
};

// One digit column that rolls when its value changes.
const RollDigit: React.FC<{seconds: number; fps: number; index: number; size: number}> = ({seconds, fps, index, size}) => {
  const now = mmss(seconds);
  const ch = now[index];
  if (ch === ':') return <span style={{display: 'inline-block', width: '0.6em', textAlign: 'center', opacity: 0.55}}>:</span>;
  // time since this column last changed
  const frac = seconds - Math.floor(seconds);
  const prevS = Math.floor(seconds) - 1;
  const prev = mmss(prevS)[index];
  const changed = seconds >= 1 && prev !== ch;
  const p = changed ? interpolate(frac * fps, [0, 6], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.out}) : 1;
  const cell: React.CSSProperties = {position: 'absolute', left: 0, right: 0, textAlign: 'center'};
  return (
    <span style={{position: 'relative', display: 'inline-block', width: '0.6em', height: size * 1.05, overflow: 'hidden', verticalAlign: 'bottom'}}>
      {p < 1 ? <span style={{...cell, transform: `translateY(${(-p * 0.55).toFixed(3)}em)`, opacity: 1 - p, filter: `blur(${(p * 4).toFixed(2)}px)`}}>{prev}</span> : null}
      <span style={{...cell, transform: `translateY(${((1 - p) * 0.55).toFixed(3)}em)`, opacity: p, filter: p < 1 ? `blur(${((1 - p) * 4).toFixed(2)}px)` : undefined}}>{ch}</span>
    </span>
  );
};

const Ring: React.FC<{size: number; progress: number; draw: number; pulse: number}> = ({size, progress, draw, pulse}) => {
  const r = size / 2 - 4;
  const c = 2 * Math.PI * r;
  const a = Math.max(0.004, progress);
  const head = -Math.PI / 2 + a * 2 * Math.PI;
  const hx = size / 2 + r * Math.cos(head);
  const hy = size / 2 + r * Math.sin(head);
  return (
    <svg width={size} height={size} style={{display: 'block', overflow: 'visible'}}>
      <defs>
        <radialGradient id="pt-glow">
          <stop offset="0%" stopColor={C.red} stopOpacity={0.55} />
          <stop offset="100%" stopColor={C.red} stopOpacity={0} />
        </radialGradient>
      </defs>
      {pulse > 0 && pulse < 1 ? <circle cx={size / 2} cy={size / 2} r={r * (1 + 0.6 * pulse)} fill="none" stroke={C.red} strokeWidth={2} opacity={0.45 * (1 - pulse)} /> : null}
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.22)" strokeWidth={2}
        strokeDasharray={c} strokeDashoffset={c * (1 - draw)} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
      {[0, 90, 180, 270].map((d) => (
        <line key={d} x1={size / 2} y1={6} x2={size / 2} y2={11} stroke="rgba(255,255,255,0.4)" strokeWidth={1.5} transform={`rotate(${d} ${size / 2} ${size / 2})`} opacity={draw} />
      ))}
      {progress > 0 ? (
        <>
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={C.red} strokeWidth={3.5} strokeLinecap="round"
            strokeDasharray={`${c * a} ${c}`} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
          <circle cx={hx} cy={hy} r={9} fill="url(#pt-glow)" />
          <circle cx={hx} cy={hy} r={3} fill={C.red} />
        </>
      ) : null}
    </svg>
  );
};

const Inner: React.FC<PitchTimerProps> = ({from, clockZero, totalSeconds = 90, showTotal = true, label, variant = 'intro', scale = 1}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const abs = from + frame;
  const seconds = Math.max(0, (abs - clockZero) / fps);
  const size = 64 * scale;
  const draw = variant === 'intro' ? interpolate(frame, [3, 21], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.inOut}) : 1;
  const pulse = interpolate(abs, [clockZero, clockZero + 20], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.out});
  const progress = abs >= clockZero ? Math.min(1, seconds / totalSeconds) : 0;
  return (
    <FrostedGlass padX={30 * scale} padY={20 * scale} radius={999}>
      <div style={{display: 'flex', alignItems: 'center', gap: 24 * scale}}>
        <Ring size={78 * scale} progress={progress} draw={draw} pulse={variant === 'intro' ? pulse : 0} />
        <div style={{display: 'flex', flexDirection: 'column'}}>
          {label ? <div style={{fontFamily: FONT.mono, fontSize: 22 * scale, color: 'rgba(255,255,255,0.62)', letterSpacing: '0.04em', marginBottom: 2 * scale}}>{label}</div> : null}
          <div style={{display: 'flex', alignItems: 'baseline', fontFamily: FONT.mono, fontWeight: 400, color: C.white, lineHeight: 1.05}}>
            <span style={{fontSize: size, display: 'inline-flex'}}>
              {[0, 1, 2, 3, 4].map((i) => <RollDigit key={i} seconds={seconds} fps={fps} index={i} size={size} />)}
            </span>
            {showTotal ? <span style={{fontSize: 28 * scale, color: 'rgba(255,255,255,0.5)', marginLeft: 14 * scale, whiteSpace: 'pre'}}>/ {mmss(totalSeconds)}</span> : null}
          </div>
        </div>
      </div>
    </FrostedGlass>
  );
};

export const PitchTimer: React.FC<PitchTimerProps> = (p) => (
  <Slot {...p} name={p.name ?? `PitchTimer ${p.variant ?? 'intro'}`} enterFrames={p.enterFrames ?? 18} exitFrames={p.exitFrames ?? 14}>
    {() => <Inner {...p} />}
  </Slot>
);
