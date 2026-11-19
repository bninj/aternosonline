import React from 'react';
import {AbsoluteFill, interpolate, interpolateColors, Sequence, useCurrentFrame} from 'remotion';
import {display} from './fonts';
import {EnvelopeProvider, FrostedGlass, makeEnvelope, MotionBlurWhileMoving, Reveal} from './primitives';
import {onScreen} from './sanitize';
import {C, EASE, PRISM} from './tokens';

// Pitch progress, echoing the contest slide's scoring bar: a row of labelled segments, the active one solid DDN red,
// finished ones pale rose, upcoming ones neutral, on a light frosted panel. At each section change it PRESENTS itself
// (labels readable, about 1.7 s), the new segment fills red with a soft on-brand prism glint, then it CONDENSES into a
// slim strip on the top edge (active segment still red) for the rest of the section. Every change is a tween.
export type SectionBarProps = {
  sections: {label: string; from: number}[]; // absolute frames: when each section becomes active (picture cut times)
  from: number; // visible from (absolute frame); usually sections[0].from
  durationInFrames: number;
  presentFrames?: number; // hold of the presented state after each change (default 52 = 1.73 s)
  width?: number; // presented width px (default 900)
  slimWidth?: number; // condensed width px (default 520)
  labelSize?: number; // presented label px (default 26)
  top?: number; // px from the top edge (default 46)
  right?: number; // px from the right edge (default 154 = 8 % W)
};

const ROSE = '#F4D3D8'; // pale rose (DDN pale pink #E8B5BE family), finished sections
const NEUTRAL = 'rgba(32,30,30,0.10)';

const Body: React.FC<SectionBarProps> = ({sections, from, durationInFrames, presentFrames = 52, width = 900, slimWidth = 520, labelSize = 26, top = 46, right = 154}) => {
  const frame = useCurrentFrame();
  const abs = from + frame;
  const env = makeEnvelope(durationInFrames, {delay: 0, enter: 16, exit: 12});
  sections.forEach((s) => onScreen(s.label, 'SectionBar'));
  const c = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
  // Presented amount: 1 while presenting (expand 14 f, hold, condense 18 f), 0 when slim.
  const present = Math.max(...sections.map((s) => {
    const a = interpolate(abs, [s.from, s.from + 14], [0, 1], {...c, easing: EASE.inOut});
    const b = interpolate(abs, [s.from + presentFrames, s.from + presentFrames + 18], [1, 0], {...c, easing: EASE.inOut});
    return Math.min(a, b);
  }));
  const segH = 6 + (labelSize * 1.7 - 6) * present;
  const w = slimWidth + (width - slimWidth) * present;
  const pad = 8 + 4 * present;
  const lab = display('medium', labelSize, -0.005);
  return (
    <EnvelopeProvider value={env}>
      <MotionBlurWhileMoving env={env} samples={5}>
        <AbsoluteFill>
          <div style={{position: 'absolute', top, right}}>
            <Reveal rise={-14} blur={10}>
              <FrostedGlass tone="light" padX={pad} padY={pad} radius={10 + 4 * present}>
                <div style={{display: 'flex', gap: 4 + 2 * present, width: w}}>
                  {sections.map((s, i) => {
                    const next = sections[i + 1]?.from ?? 1e9;
                    const fill = interpolate(abs, [s.from, s.from + 16], [0, 1], {...c, easing: EASE.inOut}); // fills red on activation
                    const done = interpolate(abs, [next, next + 16], [0, 1], {...c, easing: EASE.inOut}); // settles to rose
                    const bg = interpolateColors(done, [0, 1], [C.red, ROSE]);
                    const active = fill * (1 - done);
                    const txt = interpolateColors(active, [0, 1], [done > 0.5 ? C.wine : '#6E6767', '#FFFFFF']);
                    // prism glint across the fresh fill (DDN spectrum), once
                    const g = interpolate(abs, [s.from + 6, s.from + 34], [-40, 140], c);
                    const gOn = abs > s.from + 4 && abs < s.from + 36;
                    const st = PRISM.stops;
                    return (
                      <div key={i} style={{flex: '1 1 0', position: 'relative', height: segH, borderRadius: 3 + 3 * present, background: NEUTRAL, overflow: 'hidden'}}>
                        <div style={{position: 'absolute', left: 0, top: 0, bottom: 0, width: `${(Math.max(fill, done > 0 ? 1 : 0) * 100).toFixed(2)}%`, background: bg}} />
                        {gOn ? <div style={{position: 'absolute', inset: 0, mixBlendMode: 'screen', opacity: 0.85,
                          background: `linear-gradient(110deg, transparent ${g - 20}%, ${st[0]} ${g - 10}%, rgba(255,255,255,0.9) ${g}%, ${st[4]} ${g + 10}%, transparent ${g + 20}%)`}} /> : null}
                        {present > 0.01 ? (
                          <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: interpolate(present, [0.55, 1], [0, 1], c),
                            ...lab, lineHeight: 1, color: txt, whiteSpace: 'nowrap'}}>{s.label}</div>
                        ) : null}
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

export const SectionBar: React.FC<SectionBarProps> = (p) => (
  <Sequence from={p.from} durationInFrames={p.durationInFrames} name="SectionBar" layout="none">
    <Body {...p} />
  </Sequence>
);

