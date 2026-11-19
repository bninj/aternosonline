import {FRAME, SAFE} from './tokens';

export type Box = {x: number; y: number; w: number; h: number}; // px @1920x1080
export type Side = 'left' | 'right';
export type Anchor = Side | 'center' | 'auto';
export type Offset = {x?: number; y?: number}; // px @1080, added after placement (+x right, +y down)

export const overlaps = (a: Box, b: Box) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

// Everything a graphic must keep clear of: the face plus any extra "avoid" boxes (e.g. a monitor in shot that
// already shows a logo). Only boxes reaching into the lower 70 % of frame matter for the graphics band.
export const obstacles = (faceBox?: Box, avoid: Box[] = []) => [...(faceBox ? [faceBox] : []), ...avoid];

const inset = () => FRAME.w * SAFE.sideInset;

// Free horizontal room on one side, measured from that side's inset to the nearest obstacle in the band.
export const roomOn = (side: Side, obs: Box[], band: {y0: number; y1: number} = {y0: FRAME.h * 0.25, y1: FRAME.h * SAFE.graphicsBottom}) => {
  const inBand = obs.filter((b) => b.y < band.y1 && b.y + b.h > band.y0);
  if (side === 'left') return Math.min(FRAME.w - 2 * inset(), ...inBand.filter((b) => b.x + b.w / 2 > inset()).map((b) => b.x - inset()));
  return Math.min(FRAME.w - 2 * inset(), ...inBand.filter((b) => b.x + b.w / 2 < FRAME.w - inset()).map((b) => FRAME.w - inset() - (b.x + b.w)));
};

// 'auto': the side with more free room (ties go to DDN's default, left). No obstacles: left.
export const resolveSide = (anchor: Anchor = 'auto', faceBox?: Box, avoid: Box[] = []): Side | 'center' => {
  if (anchor !== 'auto') return anchor;
  const obs = obstacles(faceBox, avoid);
  if (!obs.length) return 'left';
  return roomOn('right', obs) > roomOn('left', obs) + 1 ? 'right' : 'left';
};

export const sideStyle = (side: Side | 'center', offset: Offset = {}): React.CSSProperties => {
  const dx = offset.x ?? 0;
  if (side === 'left') return {left: inset() + dx};
  if (side === 'right') return {right: inset() - dx};
  return {left: '50%', transform: `translateX(calc(-50% + ${dx}px))`};
};

export const graphicsBottomPx = FRAME.h * (1 - SAFE.graphicsBottom); // distance from frame bottom

// Max width on the chosen side without crossing an obstacle (48 px gap), capped.
export const maxWidthFor = (side: Side | 'center', faceBox?: Box, cap = 1000, avoid: Box[] = []): number => {
  const obs = obstacles(faceBox, avoid);
  if (side === 'center' || !obs.length) return cap;
  return Math.max(360, Math.min(cap, roomOn(side, obs) - 48));
};
