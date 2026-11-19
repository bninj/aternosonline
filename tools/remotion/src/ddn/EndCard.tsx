import React from 'react';
import {AbsoluteFill, interpolate, Sequence, useCurrentFrame} from 'remotion';
import {display, FONT} from './fonts';
import {Grain, Hairline, Rise} from './primitives';
import {onScreen} from './sanitize';
import {C, EASE} from './tokens';
import {Logo} from './logos';

// End card [4.10A]: the 2026 outro grey #E7E7E7 with grain. v2: it dissolves in over the last shot (16 f, ddn-inout,
// never a cut), then the official DDN logo (primary colour artwork, unmodified) rises from under a hairline, then
// the line in DDN Black. logo={false} falls back to the text lead "DDN." in Brand Red.
export type EndCardProps = {from: number; durationInFrames: number; lead?: string; line?: string; size?: number; logo?: boolean; logoHeight?: number};

const Body: React.FC<Required<Omit<EndCardProps, 'from' | 'durationInFrames'>>> = ({lead, line, size, logo, logoHeight}) => {
  const frame = useCurrentFrame();
  const bg = interpolate(frame, [0, 16], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.inOut});
  return (
    <AbsoluteFill style={{opacity: bg}}>
      <AbsoluteFill style={{background: C.outroGray}} />
      <Grain opacity={0.06} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
          {logo ? (
            <Rise startFrame={12} frames={16}>
              <Logo id="ddn" height={logoHeight} />
            </Rise>
          ) : null}
          <div style={{marginTop: logo ? 44 : 0, display: 'flex', flexDirection: 'column', alignItems: 'stretch'}}>
            <Hairline width="100%" startFrame={logo ? 20 : 10} color="rgba(32,30,30,0.3)" />
            <Rise startFrame={logo ? 23 : 13} style={{marginTop: 18}}>
              <div style={{...display('medium', size, -0.02), lineHeight: 1.1, color: C.black, whiteSpace: 'nowrap'}}>
                {logo ? null : <span style={{color: C.red}}>{lead} </span>}
                {line}
              </div>
            </Rise>
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const EndCard: React.FC<EndCardProps> = ({from, durationInFrames, lead = 'DDN.', line = 'Keep the chips busy.', size = 76, logo = true, logoHeight = 120}) => {
  onScreen(lead, 'EndCard');
  onScreen(line, 'EndCard');
  return (
    <Sequence from={from} durationInFrames={durationInFrames} name="EndCard">
      <Body lead={lead} line={line} size={size} logo={logo} logoHeight={logoHeight} />
    </Sequence>
  );
};
