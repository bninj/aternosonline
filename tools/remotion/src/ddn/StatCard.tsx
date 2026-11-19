import React from 'react';
import {useCurrentFrame} from 'remotion';
import {display, FONT} from './fonts';
import {GlassPlate, MonoTag, Rise, buildScale, useCount} from './primitives';
import {onScreen} from './sanitize';
import {Slot, SlotProps} from './Slot';
import {C, T, TYPE} from './tokens';

// 2026 counter [4.6] as an overlay card: number counts up (24 f ddn-inout), then the source tag types on.
// value "5%" counts 0 to 5; lines adds smaller headline lines under the number; source is mandatory.
export type StatCardProps = SlotProps & {
  value: string; // e.g. "5%" or "99% busy,"
  lines?: string[]; // extra lines under the value, e.g. ["75% lower cost per token"]
  source: string; // tag text, e.g. "Cast AI, enterprise average"
  countFrom?: number;
  valueSize?: number;
  landAt?: number; // frame (in slot) the number is spoken: the count lands exactly there
  linesAt?: number; // frame (in slot) the extra lines rise (e.g. on a spoken "75%")
  scale?: number; // overall card scale (1 = default)
};

const Inner: React.FC<Omit<StatCardProps, keyof SlotProps> & {duration: number}> = ({value, lines = [], source, countFrom = 0, valueSize = TYPE.number, duration, landAt, linesAt, scale: k0 = 1}) => {
  const frame = useCurrentFrame();
  const k = buildScale(duration, 40);
  onScreen(value, 'StatCard value');
  lines.forEach((l) => onScreen(l, 'StatCard line'));
  const m = value.match(/^(\D*)(\d+(?:\.\d+)?)(.*)$/);
  const target = m ? parseFloat(m[2]) : 0;
  const decimals = m && m[2].includes('.') ? m[2].split('.')[1].length : 0;
  const cf = Math.round(T.countFrames * k);
  const start = landAt !== undefined ? Math.max(T.firstOffset, landAt - cf) : Math.round(T.firstOffset * k);
  const n = useCount(countFrom, target, start, landAt !== undefined ? landAt - start : cf);
  // Floor while counting up, so the final value appears exactly on the landing frame (not 0.5 early via rounding).
  const q = Math.pow(10, decimals);
  const shown = m ? `${m[1]}${(Math.floor(n * q + 1e-6) / q).toFixed(decimals)}${m[3]}` : value;
  const linesStart = linesAt !== undefined ? linesAt - 6 : start + Math.round(14 * k);
  const tagStart = Math.max(start, linesStart) + Math.round((lines.length ? 12 : 10) * k);
  return (
    <GlassPlate padX={Math.round(48 * k0)} padY={Math.round(40 * k0)}>
      <Rise startFrame={start}>
        <div style={{...display('regular', Math.round(valueSize * k0), -0.02), lineHeight: 1, color: C.white,
          fontFeatureSettings: '"tnum" 1', whiteSpace: 'pre', minWidth: `${value.length * 0.62}em`}}>{shown}</div>
      </Rise>
      {lines.map((l, i) => (
        <Rise key={i} startFrame={linesStart + i * 2} style={{marginTop: i === 0 ? 18 : 4}}>
          <div style={{...display('regular', Math.round(TYPE.headline * k0), -0.01), lineHeight: 1.15, color: C.white}}>{l}</div>
        </Rise>
      ))}
      <div style={{marginTop: Math.round(28 * k0), height: TYPE.tagBar}}>
        <MonoTag text={source} startFrame={tagStart} />
      </div>
    </GlassPlate>
  );
};

export const StatCard: React.FC<StatCardProps> = (p) => (
  <Slot {...p} name={p.name ?? `StatCard ${p.value}`}>{({duration}) => <Inner {...p} duration={duration} />}</Slot>
);
