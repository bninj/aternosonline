// Per-segment framing data for PitchFinal, px @1920x1080 BEFORE the segment's push-in.
// Faces: mediapipe FaceLandmarker on the rough cut (scripts/face_boxes.py, segments 2 to 6, 13, 14) and hand-marked
// from gridded frames where the face is too small for the landmarker (segments 0, 1, 7 to 12; the DDN shots are wide
// and dark). Boxes include hair and a chin margin. Keep-outs: SHOTPLAN.json keep_out (monitors, AI sign).
import {Easing} from 'remotion';
import plan from './shotplan.json';

export type Box = {x: number; y: number; w: number; h: number};

const SKY: Box = {x: 1114, y: 151, w: 634, h: 432}; // Sky monitor, segments 1 to 6
const DDN: Box = {x: 979, y: 184, w: 576, h: 324}; // DDN monitor + laptop, segments 7 to 12

const RAW: {center: [number, number]; face: Box; avoid: Box[]}[] = [
  {center: [631, 243], face: {x: 530, y: 120, w: 220, h: 250}, avoid: [{x: 1050, y: 380, w: 350, h: 700}]}, // 0 hook, AI chair
  {center: [720, 300], face: {x: 630, y: 180, w: 180, h: 250}, avoid: [SKY]},
  {center: [656, 386], face: {x: 527, y: 176, w: 257, h: 385}, avoid: [SKY]},
  {center: [765, 417], face: {x: 646, y: 220, w: 239, h: 349}, avoid: [SKY]},
  {center: [819, 370], face: {x: 636, y: 123, w: 323, h: 405}, avoid: [SKY]},
  {center: [755, 337], face: {x: 596, y: 111, w: 317, h: 415}, avoid: [SKY]},
  {center: [645, 343], face: {x: 483, y: 87, w: 324, h: 478}, avoid: [SKY]},
  {center: [583, 313], face: {x: 440, y: 170, w: 300, h: 300}, avoid: [DDN]},
  {center: [736, 238], face: {x: 640, y: 130, w: 200, h: 230}, avoid: [DDN]},
  {center: [783, 238], face: {x: 680, y: 130, w: 210, h: 230}, avoid: [DDN]},
  {center: [785, 254], face: {x: 680, y: 140, w: 210, h: 230}, avoid: [DDN]},
  {center: [767, 265], face: {x: 660, y: 150, w: 210, h: 230}, avoid: [DDN]},
  {center: [828, 238], face: {x: 730, y: 130, w: 200, h: 230}, avoid: [DDN]},
  {center: [616, 330], face: {x: 478, y: 115, w: 428, h: 403}, avoid: [{x: 1100, y: 480, w: 300, h: 220}]}, // AI sign
  {center: [906, 397], face: {x: 714, y: 105, w: 379, h: 514}, avoid: [{x: 1340, y: 500, w: 290, h: 210}]},
];

export type Segment = (typeof plan.segments)[number];
const EASE_PUSH = Easing.bezier(0.65, 0, 0.35, 1); // ddn-inout: slow drift, no overshoot

export const segmentAt = (t: number): Segment => {
  for (let i = plan.segments.length - 1; i >= 0; i--) if (t >= plan.segments[i].start - 1e-6) return plan.segments[i];
  return plan.segments[0];
};

// Zoom inside the segment only: starts at zoom[0] on the cut frame (clean reset), drifts to zoom[1] by the next cut.
export const zoomAt = (t: number): number => {
  const s = segmentAt(t);
  const t0 = (s as {zoom_from?: number}).zoom_from ?? s.start;
  const p = Math.max(0, Math.min(1, (t - t0) / Math.max(0.001, s.end - t0)));
  return s.zoom[0] + (s.zoom[1] - s.zoom[0]) * EASE_PUSH(p);
};

const zoomBox = (b: Box, c: [number, number], z: number): Box => ({x: c[0] + (b.x - c[0]) * z, y: c[1] + (b.y - c[1]) * z, w: b.w * z, h: b.h * z});

// Worst case (end-of-segment zoom) boxes for placement and QA.
export const SEG_LAYOUT = RAW.map((r, i) => {
  const z = plan.segments[i].zoom[1];
  return {...r, faceZoomed: zoomBox(r.face, r.center, z), avoidZoomed: r.avoid.map((b) => zoomBox(b, r.center, z))};
});
