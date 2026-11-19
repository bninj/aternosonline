// Framing for PitchFinal v4 (SHOTPLAN_v4: 20 picture segments, J-cut times). px @1920x1080 BEFORE the push-in.
// Faces: scripts/face_boxes.py on the v4 plate (faces_v4.json), hand-marked where the landmarker misses (small, dark
// faces in the Why DDN wides). Camera moves: per-segment eased drift (reset at every cut), snap-zoom accents on key
// words, and a velocity-matched seam (push zoom + rack-focus blur) at the four section changes only.
import {Easing} from 'remotion';
import plan from './shotplan_v5.json'; // v5: 21 shots (IMG_3859 inserted at 67.643)
import detected from './faces_v5.json'; // v4 detections, re-indexed for the v5 insert (17 re-detected on the v5 plate)

export type Box = {x: number; y: number; w: number; h: number};
const FPS = 30;
export const fr = (s: number) => Math.round(s * FPS);

type FaceRow = {i: number; center?: number[]; box?: Box};
// Hand-marked from gridded mid-segment frames of the v4 plate (landmarker misses these: small or dark faces).
const MANUAL: Record<number, {center: [number, number]; box: Box}> = {
  0: {center: [672, 190], box: {x: 577, y: 60, w: 190, h: 260}},
  1: {center: [710, 288], box: {x: 620, y: 170, w: 180, h: 240}},
  8: {center: [576, 288], box: {x: 470, y: 170, w: 230, h: 250}},
  9: {center: [710, 240], box: {x: 630, y: 140, w: 170, h: 210}},
  10: {center: [787, 250], box: {x: 705, y: 150, w: 170, h: 210}},
  11: {center: [787, 255], box: {x: 705, y: 155, w: 170, h: 210}},
  12: {center: [749, 262], box: {x: 665, y: 160, w: 170, h: 210}},
  13: {center: [806, 245], box: {x: 725, y: 145, w: 170, h: 210}},
  14: {center: [614, 240], box: {x: 510, y: 95, w: 210, h: 260}},
  16: {center: [576, 262], box: {x: 470, y: 140, w: 220, h: 260}},
};

// Keep-outs (pre-zoom): Sky monitor (segments 1 to 7), DDN monitor + laptop (8 to 13), AI sign (0, 14 to 19).
const SKY_A: Box = {x: 1229, y: 230, w: 441, h: 288};
const SKY_B: Box = {x: 1152, y: 200, w: 538, h: 365};
const DDN_M: Box = {x: 1018, y: 205, w: 460, h: 290};
export const KEEP_OUT: Box[][] = [
  [{x: 1075, y: 430, w: 173, h: 165}], [SKY_A], [SKY_A], [SKY_A], [SKY_B], [SKY_B], [SKY_B], [SKY_B],
  [DDN_M], [DDN_M], [DDN_M], [DDN_M], [DDN_M], [DDN_M],
  [{x: 1114, y: 499, w: 211, h: 219}], [{x: 1114, y: 499, w: 211, h: 219}], [{x: 1094, y: 499, w: 192, h: 154}],
  [{x: 1344, y: 518, w: 230, h: 173}], // 17 (v5 insert, IMG_3859 medium) checked on the plate
  [{x: 1344, y: 518, w: 230, h: 173}], [{x: 1344, y: 518, w: 230, h: 173}], [{x: 1344, y: 518, w: 230, h: 173}],
];

export const SEAM_CUTS = plan.sections_for_progress_bar.map((s) => s.start).filter((t) => t > 0.5).map(fr); // 9.353, 21.906, 32.592, 58.71
const SNAPS = plan.snap_zooms.map((s) => ({f: fr(s.t), amount: s.amount}));
const segStart = plan.segments.map((s) => fr(s.start));

export const segIndexAt = (frame: number) => {
  for (let i = segStart.length - 1; i >= 0; i--) if (frame >= segStart[i]) return i;
  return 0;
};

const P4in = (x: number) => x * x * x * x;
const P4out = (x: number) => 1 - Math.pow(1 - x, 4);
const DRIFT = Easing.bezier(0.37, 0, 0.63, 1); // sine in-out: no linear starts or stops
const clamp01 = (x: number) => Math.max(0, Math.min(1, x));

export const faceOf = (i: number): {center: [number, number]; box: Box} => {
  const d = (detected as FaceRow[]).find((r) => r.i === i);
  if (MANUAL[i]) return MANUAL[i];
  if (d && d.center && d.box) return {center: [d.center[0], d.center[1]], box: d.box};
  return {center: [960, 360], box: {x: 860, y: 220, w: 200, h: 260}};
};

// Camera state for a frame: scale about the face centre, plus motion blur (px) for snaps and seams.
export const cameraAt = (frame: number) => {
  const i = segIndexAt(frame);
  const s = plan.segments[i];
  const f0 = fr((s as {zoom_from?: number}).zoom_from ?? s.start);
  const f1 = fr(s.end);
  let z = s.zoom[0] + (s.zoom[1] - s.zoom[0]) * DRIFT(clamp01((frame - f0) / Math.max(1, f1 - f0)));
  let blur = 0;
  // snap-zoom accents: +4 % in 5 f (power4-out), then hold to the cut
  for (const sn of SNAPS) {
    if (sn.f >= segStart[i] && sn.f < f1 && frame >= sn.f) {
      const r = clamp01((frame - sn.f) / 5);
      z *= 1 + sn.amount * P4out(r);
      if (r < 1) blur = Math.max(blur, 2.2 * Math.sin(Math.PI * r));
    }
  }
  // section seam: outgoing pushes +3 % with blur rising to 18 px over 4 f (power4-in); the incoming keeps pushing
  // +3 % over 5 f (power4-out) as the blur clears. Mirrored eases, same direction: one continuous push through the cut.
  for (const c of SEAM_CUTS) {
    if (frame >= c - 4 && frame < c) {
      const p = (frame - (c - 4) + 1) / 4;
      z *= 1 + 0.03 * P4in(p);
      blur = Math.max(blur, 18 * p * p);
    }
    if (frame >= c && frame < c + 6) {
      const q = (frame - c) / 5;
      z *= 1 + 0.03 * P4out(clamp01(q));
      blur = Math.max(blur, 18 * Math.pow(1 - clamp01(q), 2));
    } else if (frame >= c + 6 && segIndexAt(frame) === segIndexAt(c)) {
      z *= 1.03; // the incoming push is kept for the rest of that segment (no pull-back)
    }
  }
  const face = faceOf(i);
  return {i, z, blur, origin: face.center};
};

// Worst-case (end-of-segment, after snaps/seams) face box, for placement checks.
export const faceZoomed = (i: number): Box => {
  const s = plan.segments[i];
  const z = s.zoom[1] * 1.03 * (SNAPS.some((sn) => sn.f >= segStart[i] && sn.f < fr(s.end)) ? 1.04 : 1);
  const f = faceOf(i);
  const c = f.center;
  return {x: c[0] + (f.box.x - c[0]) * z, y: c[1] + (f.box.y - c[1]) * z, w: f.box.w * z, h: f.box.h * z};
};

const zoomAbout = (b: Box, c: number[], z: number): Box => ({x: c[0] + (b.x - c[0]) * z, y: c[1] + (b.y - c[1]) * z, w: b.w * z, h: b.h * z});
export const keepOutZoomed = (i: number, z: number): Box[] => KEEP_OUT[i].map((b) => zoomAbout(b, faceOf(i).center, z));
export const faceAt = (i: number, z: number): Box => zoomAbout(faceOf(i).box, faceOf(i).center, z);
