import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {evolvePath, getLength} from '@remotion/paths';
import {display, FONT} from './fonts';
import {GlassPlate, MonoTag, Rise, buildScale} from './primitives';
import {onScreen} from './sanitize';
import {Slot, SlotProps} from './Slot';
import {C, EASE, T, TYPE} from './tokens';

// Falling line chart: hairline axis, white line draws left to right (ddn-inout), the last segment and end
// point in Brand Red, then the value rises in beside the end point and the source tag types on.
export type LineChartFallProps = SlotProps & {
  value: string; // "12%"
  source: string; // "Ofcom Media Nations 2026"
  points?: number[]; // y values 0..1 (1 = top), left to right
  label?: string; // optional small mono caption above the chart; omitted by default
  valueAt?: number; // frame (in slot) the value is spoken; the line finishes just before and the value lands on it
  chartW?: number;
  chartH?: number;
  scale?: number; // overall card scale for type and padding (1 = default; the pitch film uses about 0.78)
  countUp?: boolean; // the value counts up and lands exactly on valueAt (instead of rising in whole)
  glow?: boolean; // glowing end point
};


const Inner: React.FC<Omit<LineChartFallProps, keyof SlotProps> & {duration: number}> = ({value, source, points = [0.86, 0.8, 0.83, 0.71, 0.66, 0.52, 0.47, 0.3, 0.18], label, valueAt, duration, chartW: W = 620, chartH: H = 250, scale: k0 = 1, countUp = false, glow = false}) => {
  const frame = useCurrentFrame();
  onScreen(value, 'chart value');
  if (label) onScreen(label, 'chart label');
  const k = buildScale(duration, 52);
  const s0 = Math.round(T.firstOffset * k);
  const drawF = Math.round(24 * k);
  const pts = points.map((y, i) => [12 + (i / (points.length - 1)) * (W - 24), 12 + (1 - y) * (H - 24)] as const);
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ');
  const last = pts.slice(-2);
  const dLast = `M${last[0][0]} ${last[0][1]} L${last[1][0]} ${last[1][1]}`;
  const total = getLength(d);
  const lastLen = getLength(dLast);
  const p = interpolate(frame, [s0, s0 + drawF], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.inOut});
  const whiteFrac = 1 - lastLen / total;
  const whiteP = Math.min(1, p / whiteFrac);
  const redP = Math.max(0, (p - whiteFrac) / (1 - whiteFrac));
  const w = evolvePath(whiteP, d);
  const r = evolvePath(redP, dLast);
  const dot = interpolate(frame, [s0 + drawF - 2, s0 + drawF + 5], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.inOut});
  const autoValue = s0 + drawF + Math.round(4 * k); // short stillness after the line lands
  // Value lands ON its word: the 12 f expo-out rise is visually settled (>94 %) after 6 f, so start 6 f early.
  const valueStart = valueAt !== undefined ? (countUp ? valueAt - 28 : valueAt - 6) : autoValue;
  const vm = value.match(/^(\D*)(\d+)(.*)$/);
  const cnt = countUp && vm && valueAt !== undefined ? Math.floor(interpolate(frame, [valueAt - 24, valueAt], [0, parseInt(vm[2], 10)], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.inOut}) + 1e-6) : null;
  const shownValue = cnt !== null && vm ? `${vm[1]}${cnt}${vm[3]}` : value;
  const tagStart = countUp && valueAt !== undefined ? valueAt + 2 : valueStart + Math.round(12 * k);
  return (
    <GlassPlate padX={Math.round(48 * k0)} padY={Math.round(40 * k0)}>
      {label ? <div style={{fontFamily: FONT.mono, fontSize: TYPE.eyebrow, color: 'rgba(255,255,255,0.7)', marginBottom: 16}}>{label}</div> : null}
      <div style={{display: 'flex', alignItems: 'flex-end', gap: 28}}>
        <svg width={W} height={H} style={{overflow: 'visible', display: 'block'}}>
          <line x1={0} y1={H} x2={W} y2={H} stroke="rgba(255,255,255,0.55)" strokeWidth={1} />
          {[0.25, 0.5, 0.75].map((g) => <line key={g} x1={0} y1={H * g} x2={W} y2={H * g} stroke="rgba(255,255,255,0.12)" strokeWidth={1} />)}
          <path d={d} fill="none" stroke={C.white} strokeWidth={4} strokeLinejoin="round" strokeLinecap="round" strokeDasharray={w.strokeDasharray} strokeDashoffset={w.strokeDashoffset} />
          <path d={dLast} fill="none" stroke={C.red} strokeWidth={4} strokeLinecap="round" strokeDasharray={r.strokeDasharray} strokeDashoffset={r.strokeDashoffset} opacity={redP > 0 ? 1 : 0} />
          {glow ? <circle cx={last[1][0]} cy={last[1][1]} r={22 * dot} fill={C.red} opacity={0.28 * dot} style={{filter: 'blur(6px)'}} /> : null}
          <circle cx={last[1][0]} cy={last[1][1]} r={9 * dot} fill={C.red} opacity={dot} />
        </svg>
        <Rise startFrame={valueStart}>
          <div style={{...display('regular', Math.round(TYPE.number * k0), -0.02), lineHeight: 1, color: C.white, fontFeatureSettings: '"tnum" 1', transform: 'translateY(8px)', minWidth: `${value.length * 0.6}em`}}>{shownValue}</div>
        </Rise>
      </div>
      <div style={{marginTop: Math.round(28 * k0), height: TYPE.tagBar}}><MonoTag text={source} startFrame={tagStart} /></div>
    </GlassPlate>
  );
};

export const LineChartFall: React.FC<LineChartFallProps> = (p) => (
  <Slot {...p} name={p.name ?? 'LineChartFall'}>{({duration}) => <Inner {...p} duration={duration} />}</Slot>
);
