import React from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame} from 'remotion';
import {Anchor, Box, maxWidthFor, Offset, resolveSide, Side, sideStyle} from './layout';
import {FRAME, SAFE} from './tokens';
import {EnvelopeProvider, makeEnvelope, MotionBlurWhileMoving, Reveal} from './primitives';

// Every graphic lives exactly for its line (from, durationInFrames). v2: it enters and exits smoothly inside that
// window (Reveal + CameraMotionBlur while moving), never hard cuts. Placement: side away from the face and from any
// avoid boxes (e.g. a monitor that already shows a logo), inside the safe area, above the caption band.
export type SlotProps = {
  from: number; // frame the line starts
  durationInFrames: number; // length of the line, no longer
  anchor?: Anchor; // 'left' | 'right' | 'center' | 'auto'
  faceBox?: Box;
  avoid?: Box[]; // extra keep-out boxes, px @1080
  offset?: Offset; // nudge after placement, px @1080
  bottom?: number; // graphic bottom as a fraction of H (default 0.75, above captions)
  enterFrames?: number;
  exitFrames?: number;
  name?: string;
};

export type SlotCtx = {side: Side | 'center'; maxWidth: number; duration: number};

const Body: React.FC<SlotProps & {children: (ctx: SlotCtx) => React.ReactNode}> = ({durationInFrames, anchor = 'auto', faceBox, avoid = [], offset = {}, bottom = SAFE.graphicsBottom, enterFrames, exitFrames, children}) => {
  useCurrentFrame();
  const side = resolveSide(anchor, faceBox, avoid);
  const maxWidth = maxWidthFor(side, faceBox, 1000, avoid);
  const env = makeEnvelope(durationInFrames, {enter: enterFrames, exit: exitFrames});
  return (
    <EnvelopeProvider value={env}>
      <MotionBlurWhileMoving env={env}>
        <AbsoluteFill>
          <div style={{position: 'absolute', bottom: FRAME.h * (1 - bottom) - (offset.y ?? 0), ...sideStyle(side, offset), maxWidth, display: 'flex', flexDirection: 'column',
            alignItems: side === 'left' ? 'flex-start' : side === 'right' ? 'flex-end' : 'center'}}>
            <Reveal>{children({side, maxWidth, duration: durationInFrames})}</Reveal>
          </div>
        </AbsoluteFill>
      </MotionBlurWhileMoving>
    </EnvelopeProvider>
  );
};

export const Slot: React.FC<SlotProps & {children: (ctx: SlotCtx) => React.ReactNode}> = (p) => (
  <Sequence from={p.from} durationInFrames={Math.max(1, p.durationInFrames)} name={p.name} layout="none">
    <Body {...p} />
  </Sequence>
);
