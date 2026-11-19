import React from 'react';
import {AbsoluteFill, interpolate, interpolateColors, Sequence, useCurrentFrame} from 'remotion';
import {FONT} from './fonts';
import {EnvelopeProvider, FrostedGlass, makeEnvelope, MotionBlurWhileMoving, Reveal} from './primitives';
import {onScreen} from './sanitize';
import {Anchor, Box, Offset, resolveSide, sideStyle} from './layout';
import {C, EASE, FRAME, SAFE} from './tokens';
import {Logo, LogoId} from './logos';

// Pitch progress: echoes the contest scoring bar (Why change 25 | Why now 20 | Why DDN 40 | Delivery 15) as a quiet
// "you are here" indicator. Default width 940 px @1080. Segment widths are proportional to the real section durations (frames from props).
// The current segment fills in Brand Red as the section plays; finished segments settle to DDN pale pink; the label
// of the current section brightens and gains a red dot. Every change is a tween (no cuts). Replaces SectionMarker.
export type ProgressSection = {
  label: string; // "Why change"
  from: number; // absolute frame the section starts
  to: number; // absolute frame it ends
  weight?: number; // contest points, shown only with showWeights
  logo?: LogoId; // e.g. 'ddn-white': drawn after the label text instead of the word (label "Why" + logo)
};

export type SectionProgressProps = {
  sections: ProgressSection[];
  from: number; // visible from (absolute frame)
  durationInFrames: number;
  width?: number; // px @1080 (default 860)
  edge?: 'top' | 'bottom';
  anchor?: Anchor;
  faceBox?: Box;
  avoid?: Box[];
  offset?: Offset;
  showWeights?: boolean;
  labelSize?: number; // px @1080 (default 24)
};


const Body: React.FC<SectionProgressProps> = ({sections, from, durationInFrames, width = 940, edge = 'top', anchor = 'auto', faceBox, avoid = [], offset = {}, showWeights = false, labelSize: LABEL = 24}) => {
  const frame = useCurrentFrame();
  const abs = from + frame;
  const env = makeEnvelope(durationInFrames, {delay: 0, enter: 16, exit: 12});
  const side = resolveSide(anchor, faceBox, avoid);
  const total = sections.reduce((a, s) => a + (s.to - s.from), 0);
  const vert: React.CSSProperties = edge === 'top' ? {top: FRAME.h * SAFE.margin + (offset.y ?? 0)} : {bottom: FRAME.h * SAFE.margin - (offset.y ?? 0)};
  return (
    <EnvelopeProvider value={env}>
      <MotionBlurWhileMoving env={env} samples={5}>
        <AbsoluteFill>
          <div style={{position: 'absolute', ...vert, ...sideStyle(side, offset)}}>
            <Reveal rise={edge === 'top' ? -16 : 16} blur={10}>
              <FrostedGlass padX={22} padY={10} radius={14}>
                <div style={{display: 'flex', gap: 22, width}}>
                  {sections.map((s, i) => {
                    onScreen(s.label, 'SectionProgress');
                    const len = s.to - s.from;
                    const fill = interpolate(abs, [s.from, s.to], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
                    const on = interpolate(abs, [s.from - 4, s.from + 10], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.inOut});
                    const done = interpolate(abs, [s.to - 2, s.to + 16], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.inOut});
                    const active = on * (1 - done);
                    const labelAlpha = 0.58 + 0.42 * active + 0.12 * done * (1 - active);
                    const barColor = interpolateColors(done, [0, 1], [C.red, C.palePink]);
                    return (
                      <div key={i} style={{flex: `${len / total} 1 0`, minWidth: 'max-content'}}>
                        <div style={{display: 'flex', alignItems: 'center', height: Math.round(LABEL * 1.15), fontFamily: FONT.mono, fontSize: LABEL, color: `rgba(255,255,255,${labelAlpha.toFixed(3)})`, whiteSpace: 'nowrap'}}>
                          <span style={{width: 8 * active + 0.001, height: 8, marginRight: 9 * active, borderRadius: 4, background: C.red, opacity: active, flex: 'none',
                            boxShadow: `0 0 10px rgba(237,39,56,${(0.6 * active).toFixed(3)})`}} />
                          <span>{s.label}</span>
                          {s.logo ? <span style={{marginLeft: 9, opacity: 0.55 + 0.45 * Math.max(active, done)}}><Logo id={s.logo} height={20} /></span> : null}
                          {showWeights && s.weight !== undefined ? <span style={{marginLeft: 10, opacity: 0.55}}>{s.weight}</span> : null}
                        </div>
                        <div style={{position: 'relative', height: 5, marginTop: 6, borderRadius: 3, background: 'rgba(255,255,255,0.2)', overflow: 'hidden'}}>
                          <div style={{position: 'absolute', left: 0, top: 0, bottom: 0, width: `${(fill * 100).toFixed(3)}%`, borderRadius: 3, background: barColor,
                            boxShadow: active > 0.01 ? `0 0 12px rgba(237,39,56,${(0.5 * active).toFixed(3)})` : undefined}} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </FrostedGlass>
            </Reveal>
          </div>
        </AbsoluteFill>
      </MotionBlurWhileMoving>
    </EnvelopeProvider>
  );
};

export const SectionProgress: React.FC<SectionProgressProps> = (p) => (
  <Sequence from={p.from} durationInFrames={p.durationInFrames} name="SectionProgress" layout="none">
    <Body {...p} />
  </Sequence>
);
