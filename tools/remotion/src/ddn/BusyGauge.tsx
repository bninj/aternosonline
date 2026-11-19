import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {display, FONT} from './fonts';
import {GlassPlate, MonoTag, Rise, buildScale} from './primitives';
import {onScreen} from './sanitize';
import {Slot, SlotProps} from './Slot';
import {C, EASE, T, TYPE} from './tokens';

// BUSY gauge: Geist Mono label, number counts with the bar (one motion, ddn-inout), Brand Red fill.
export type BusyGaugeProps = SlotProps & {fromValue?: number; toValue?: number; label?: string; source: string; riseFrames?: number; landAt?: number /* frame in slot the top value is spoken */};

const BAR_W = 600;

const Inner: React.FC<Omit<BusyGaugeProps, keyof SlotProps> & {duration: number}> = ({fromValue = 5, toValue = 99, label = 'BUSY', source, riseFrames = 36, duration, landAt}) => {
  const frame = useCurrentFrame();
  onScreen(label, 'gauge label');
  const k = buildScale(duration, riseFrames + 24);
  const s0 = Math.round(T.firstOffset * k);
  const rf = landAt !== undefined ? Math.min(riseFrames, Math.max(12, landAt - s0 - 4)) : Math.round(riseFrames * k);
  const g0 = landAt !== undefined ? landAt - rf : s0 + Math.round(10 * k);
  const v = interpolate(frame, [g0, g0 + rf], [fromValue, toValue], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.inOut});
  const tagStart = g0 + rf + Math.round(4 * k);
  return (
    <GlassPlate padX={48} padY={40}>
      <Rise startFrame={s0}>
        <div style={{display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', width: BAR_W}}>
          <div style={{fontFamily: FONT.mono, fontSize: 28, letterSpacing: '0.08em', color: 'rgba(255,255,255,0.78)'}}>{label}</div>
          <div style={{...display('regular', TYPE.number, -0.02), lineHeight: 1, color: C.white, fontFeatureSettings: '"tnum" 1'}}>
            {Math.round(v)}%
          </div>
        </div>
      </Rise>
      <div style={{position: 'relative', width: BAR_W, height: 14, marginTop: 24, background: 'rgba(255,255,255,0.14)'}}>
        <div style={{position: 'absolute', left: 0, top: 0, bottom: 0, width: `${v}%`, background: C.red}} />
        {[25, 50, 75].map((t) => <div key={t} style={{position: 'absolute', left: `${t}%`, top: -6, width: 1, height: 26, background: 'rgba(255,255,255,0.35)'}} />)}
      </div>
      <div style={{marginTop: 28, height: TYPE.tagBar}}><MonoTag text={source} startFrame={tagStart} /></div>
    </GlassPlate>
  );
};

export const BusyGauge: React.FC<BusyGaugeProps> = (p) => (
  <Slot {...p} name={p.name ?? 'BusyGauge'}>{({duration}) => <Inner {...p} duration={duration} />}</Slot>
);
