import React, {useMemo} from 'react';
import {AbsoluteFill, Html5Audio, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {EASE, Footage, FootageSource, LineChartFall, MeasureCard, PITCH_CAPTION_LOOK, PitchTimer, SectionBar, Subtitles} from '../ddn';
import plan from './shotplan_v5.json';
import {pitchTranscriptV3} from './captions';
import {cameraAt, faceAt, fr, keepOutZoomed, segIndexAt, Box} from './layout_v4';
import {ChairSpotlight, ChipGrid, DepthLogos, DepthShatter, EndBuild, NameTag, PersonLayer, VoiceChat, VoicePill} from './graphics';

// PitchFinal v4: the tight edit (SHOTPLAN_v4, 20 picture segments, J-cuts), 74.2 s = 2226 f.
// Camera: eased drift per segment, snap-zoom accents on the key words, a velocity-matched seam (push + rack-focus
// blur) at the four section changes only; every other cut is a clean hard J-cut. Graphics are compact, to the side,
// below the monitors or above the AI sign, and anchored to spoken words (word_anchors / captions_v3).
export type PitchV4Props = {
  plate: string; // swap for the look plate: 'pitch/plate_look_v4.mp4'
  plateBlur: string | null; // pre-blurred proxy of the plate (frost)
  audio: string | null; // review audio (mix)
  voice: string; // dry voice, analysed for the live voice bars only
  showGuides?: boolean;
};

const PLATE_END = 2205; // 73.497 s: first frame without picture
const W = plan.word_anchors as Record<string, number>;
const w = (k: string) => fr(W[k]);
const cutF = (i: number) => fr(plan.segments[i].start);
const CUTS = plan.segments.slice(1).map((s) => fr(s.start));
const SEAM_DDN = fr(32.592); // Why DDN section seam
const G = 0.79; // graphics bottom (fraction of H): clears the 54 px caption pill (top at 0.83 H) by 40 px
const R = {anchor: 'right' as const};
// Depth logos: [x, y, height] in footage px @1920 (pre-zoom), placed behind calm edges (head side, shoulder).
// v5b: solved by scripts/logo_place.py against the per-frame person alpha: each logo tucks behind him by 4 to 9 % of
// its width at one edge (max 3 % after review: the wordmark's last letter must stay whole), on every frame.
const LOGO_POS = {netflix: [204, 64, 140], youtube: [72, 222, 120], canal: [340, 64, 112], starz: [324, 204, 100], bb: [360, 110, 196]} as const;
// Person alpha (SAM 2.1 + ViTMatte on the look plate), plate frame ranges [from, to).
const PERSON = [{src: 'pitch/person_s3.webm', from: 497, to: 583}, {src: 'pitch/person_s13.webm', from: 1694, to: 1761}, {src: 'pitch/person_s19.webm', from: 2148, to: 2182}];

export const PitchV4: React.FC<PitchV4Props> = ({plate, plateBlur, audio, voice, showGuides = false}) => {
  const frame = useCurrentFrame();
  const transcript = useMemo(() => pitchTranscriptV3(), []);
  const cam = cameraAt(Math.min(frame, PLATE_END - 1));
  const endT = interpolate(frame, [PLATE_END, PLATE_END + 16], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.inOut});
  const blur = cam.blur + 18 * endT;
  const camStyle: React.CSSProperties = {transformOrigin: `${cam.origin[0]}px ${cam.origin[1]}px`, transform: `scale(${(cam.z * (1 + 0.04 * endT)).toFixed(5)})`, filter: blur > 0.05 ? `blur(${blur.toFixed(2)}px)` : undefined};
  const footage: FootageSource = {
    src: plate, kind: 'video', blurredSrc: plateBlur ?? undefined,
    freezeAt: frame >= PLATE_END ? PLATE_END - 1 : undefined,
    style: {transformOrigin: `${cam.origin[0]}px ${cam.origin[1]}px`, transform: `scale(${(cam.z * (1 + 0.04 * endT)).toFixed(5)})`, filter: blur > 0.05 ? `blur(${blur.toFixed(2)}px)` : undefined},
  };

  // slot helpers: in/out in frames; entrances never start before the picture cut they would otherwise straddle
  const after = (f: number, seg: number) => Math.max(f, cutF(seg) + 2);
  const timerFrom = fr(0.85);
  const chartFrom = after(w('Ofcom') - 3, 2);
  const tilesFrom = after(w('Netflix') - 4, 3);
  const voiceFrom = w('Sky Q voice search') - 16; // dwell: >= 2 s fully visible inside the punch shot
  const chatFrom = w('AI assistant') - 4; // v5b: listening state from "an AI assistant", opens on "Imagine asking"
  const idleFrom = w('Cast AI') - 4;
  const ddnFrom = w("DDN's Infinia") - 4;
  const caFrom = w('Canal Plus') - 4;
  const askFrom = w('pilot') - 5;
  const bbFrom = w('Blockbuster') - 5;

  return (
    <Footage source={footage}>
      {audio ? <Html5Audio src={staticFile(audio)} /> : null}

      {/* 0 Hook: the real AI chair is spotlit (SAM 2.1 contour, local lift, gentle surround dim) while it is alone and
          through "Sorry I kept you waiting", locked to the footage transform; off by 3.0 s as he turns to camera.
          The pitch clock starts on "Sorry". */}
      <AbsoluteFill style={{transformOrigin: `${cam.origin[0]}px ${cam.origin[1]}px`, transform: `scale(${cam.z.toFixed(5)})`}}>
        <ChairSpotlight dimIn={[w("That's AI chips"), w("That's AI chips") + 11]} dimOut={[w("That's AI chips") + 44, w("That's AI chips") + 59]} lineIn={[w("That's AI chips"), w("That's AI chips") + 12]} offAt={[w("That's AI chips") + 44, w("That's AI chips") + 59]} />
        {/* Logos IN the room, partly behind him (the person layer below re-composites him in front). Footage space. */}
        <DepthLogos from={tilesFrom} durationInFrames={fr(19.25) - tilesFrom} items={[
          {logo: 'netflix', at: 3, x: LOGO_POS.netflix[0], y: LOGO_POS.netflix[1], h: LOGO_POS.netflix[2]},
          {logo: 'youtube', at: w('YouTube') - 4 - tilesFrom, x: LOGO_POS.youtube[0], y: LOGO_POS.youtube[1], h: LOGO_POS.youtube[2]}]} />
        <DepthLogos from={caFrom} durationInFrames={fr(58.62) - caFrom} panel={{x: 302, y: 40, w: 520, h: 286}} items={[
          {logo: 'canalplus', at: 3, x: LOGO_POS.canal[0], y: LOGO_POS.canal[1], h: LOGO_POS.canal[2]},
          {logo: 'starz', at: 9 /* both logos on "Canal Plus" so Starz also dwells >= 2 s */, x: LOGO_POS.starz[0], y: LOGO_POS.starz[1], h: LOGO_POS.starz[2]}]} />
        <DepthShatter from={bbFrom} durationInFrames={fr(72.62) - bbFrom} x={LOGO_POS.bb[0]} y={LOGO_POS.bb[1]} h={LOGO_POS.bb[2]}
          crackAt={fr(71.92) - bbFrom} breakAt={fr(72.06) - bbFrom} />
      </AbsoluteFill>
      {PERSON.map((pl) => <PersonLayer key={pl.src} src={pl.src} plateFrom={pl.from} durationInFrames={pl.to - pl.from} style={camStyle} />)}
      <NameTag from={fr(5.2)} durationInFrames={fr(8.6) - fr(5.2)} anchor="right" bottom={0.36} name="ELIUD AWUAH" />
      <PitchTimer from={timerFrom} durationInFrames={fr(2.9) - timerFrom} clockZero={w('Sorry')} anchor="right" bottom={0.3} />

      {/* Progress: presents at each section seam, then a slim strip. */}
      <SectionBar sections={plan.sections_for_progress_bar.map((s) => ({label: s.label, from: fr(s.start)}))} from={fr(plan.sections_for_progress_bar[0].start)}
        durationInFrames={fr(73.2) - fr(plan.sections_for_progress_bar[0].start)} />

      {/* Why change */}
      <LineChartFall from={chartFrom} durationInFrames={fr(16.4) - chartFrom} {...R} bottom={G} valueAt={w('12%') - chartFrom} value="12%" source="Ofcom Media Nations 2026"
        chartW={400} chartH={100} scale={0.66} countUp glow />


      {/* Why now */}
      <VoicePill from={voiceFrom} durationInFrames={fr(26.2) - voiceFrom} {...R} bottom={0.645} text="Sky Q voice search" voice={voice} />
      <VoiceChat from={chatFrom} durationInFrames={SEAM_DDN - chatFrom} {...R} bottom={G} text="Sky, make me scared." voice={voice}
        typeStart={w('Sky, make me scared') - chatFrom} typeEnd={fr(32.2) - chatFrom} openAt={w('Imagine asking') - chatFrom} />

      {/* Why DDN: one chip-use grid that evolves (idle 5 %, then data flows in, 99 % busy, cost per token down 75 %) */}
      <ChipGrid from={idleFrom} durationInFrames={fr(41.0) - idleFrom} {...R} bottom={0.8} mode="idle" landAt={w('5%') - idleFrom} source="Cast AI, enterprise average" />
      <ChipGrid from={ddnFrom} durationInFrames={fr(54.35) - ddnFrom} {...R} bottom={0.8} mode="ddn" flowAt={w('data flowing to the chips') - ddnFrom - 4}
        landAt={w('99%') - ddnFrom} countFrames={Math.min(34, w('99%') - w('customers'))} costFrom={w('cut costs per token') - ddnFrom - 2} costLandAt={w('75%') - ddnFrom} source="per DDN" />


      {/* The ask: "30 day pilot" pill on "pilot", grows into the measure card on "Then measure", holds through "So Sky",
          leaves before "Blockbuster". Upper right: clear of the face in all four shots and of the AI sign. */}
      <MeasureCard from={askFrom} durationInFrames={fr(71.6) - askFrom} {...R} bottom={0.45}
        tag="30 day pilot" tagAt={w('pilot') - askFrom - 1} itemsAt={after(w('Then measure'), 16) - askFrom} width={500} labelSize={32} barLabelSize={24} pad={24} gap={12}
        items={[{label: 'How busy the chips are', at: after(w('Then measure'), 16) - askFrom + 2, before: 0.22, after: 0.9}, {label: 'What each answer costs', at: after(w('Then measure'), 16) - askFrom + 10, before: 0.85, after: 0.3}]} 
        payoff={{text: 'If both improve', to: 'scale it', at: w('And if both improve') - askFrom, arrowAt: w('scale it') - askFrom - 6}} />


      <Subtitles transcript={transcript} look={PITCH_CAPTION_LOOK} anchor="center" joinGapFrames={6} snapTo={CUTS}
        suppress={[{from: w('Imagine asking'), to: SEAM_DDN}, {from: PLATE_END - 6, to: 2400}]}
        centerX={cam.origin[0]} maxRight={1070} />

      <EndBuild from={PLATE_END} durationInFrames={2295 - PLATE_END} />

      {showGuides ? <Guides frame={frame} z={cam.z} /> : null}
    </Footage>
  );
};

const Guides: React.FC<{frame: number; z: number}> = ({frame, z}) => {
  const i = segIndexAt(Math.min(frame, PLATE_END - 1));
  const r = (b: Box, c: string, k: string) => <div key={k} style={{position: 'absolute', left: b.x, top: b.y, width: b.w, height: b.h, border: `3px solid ${c}`}} />;
  return <>{[r(faceAt(i, z), '#00ff66', 'f'), ...keepOutZoomed(i, z).map((b, j) => r(b, '#ffcc00', `k${j}`))]}</>;
};
