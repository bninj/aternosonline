import React, {useMemo} from 'react';
import {Html5Audio, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {EASE, Footage, FootageSource, LineChartFall, MeasureCard, PITCH_CAPTION_LOOK, PitchTimer, SectionBar, Subtitles} from '../ddn';
import plan from './shotplan_v4.json';
import {pitchTranscriptV3} from './captions';
import {cameraAt, faceAt, fr, keepOutZoomed, segIndexAt, Box} from './layout_v4';
import {ChipGrid, ChipStatus, EndBuild, LogoTiles, ObsoleteLogo, VoiceChat, VoicePill} from './graphics';

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

const PLATE_END = 2136; // 71.197 s: first frame without picture
const W = plan.word_anchors as Record<string, number>;
const w = (k: string) => fr(W[k]);
const cutF = (i: number) => fr(plan.segments[i].start);
const G = 0.81; // graphics bottom (fraction of H): clears the caption pill
const R = {anchor: 'right' as const};

export const PitchV4: React.FC<PitchV4Props> = ({plate, plateBlur, audio, voice, showGuides = false}) => {
  const frame = useCurrentFrame();
  const transcript = useMemo(() => pitchTranscriptV3(), []);
  const cam = cameraAt(Math.min(frame, PLATE_END - 1));
  const endT = interpolate(frame, [PLATE_END, PLATE_END + 16], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.inOut});
  const blur = cam.blur + 18 * endT;
  const footage: FootageSource = {
    src: plate, kind: 'video', blurredSrc: plateBlur ?? undefined,
    freezeAt: frame >= PLATE_END ? PLATE_END - 1 : undefined,
    style: {transformOrigin: `${cam.origin[0]}px ${cam.origin[1]}px`, transform: `scale(${(cam.z * (1 + 0.04 * endT)).toFixed(5)})`, filter: blur > 0.05 ? `blur(${blur.toFixed(2)}px)` : undefined},
  };

  // slot helpers: in/out in frames; entrances never start before the picture cut they would otherwise straddle
  const after = (f: number, seg: number) => Math.max(f, cutF(seg) + 2);
  const timerFrom = fr(0.3);
  const chartFrom = after(w('Ofcom') - 3, 2);
  const tilesFrom = after(w('Netflix') - 4, 3);
  const voiceFrom = w('Sky Q voice search') - 6;
  const chatFrom = after(w('Imagine asking') - 2, 7);
  const idleFrom = w('Cast AI') - 4;
  const ddnFrom = w("DDN's Infinia") - 4;
  const caFrom = w('Canal Plus') - 4;
  const askFrom = w('pilot') - 5;
  const bbFrom = w('Blockbuster') - 5;

  return (
    <Footage source={footage}>
      {audio ? <Html5Audio src={staticFile(audio)} /> : null}

      {/* 0 Hook: the clock starts on "Sorry"; the idle chip waits for data near the AI chair (above its sign). */}
      <PitchTimer from={timerFrom} durationInFrames={fr(2.6) - timerFrom} clockZero={w('Sorry')} anchor="right" bottom={0.3} />
      <ChipStatus from={w("That's AI chips") - 3} durationInFrames={fr(6.0) - w("That's AI chips") + 3} {...R} bottom={0.37} emphAt={w('waiting for data') - (w("That's AI chips") - 3)} />

      {/* Progress: presents at each section seam, then a slim strip. */}
      <SectionBar sections={plan.sections_for_progress_bar.map((s) => ({label: s.label, from: fr(s.start)}))} from={fr(plan.sections_for_progress_bar[0].start)}
        durationInFrames={fr(70.9) - fr(plan.sections_for_progress_bar[0].start)} />

      {/* Why change */}
      <LineChartFall from={chartFrom} durationInFrames={fr(16.4) - chartFrom} {...R} bottom={G} valueAt={w('12%') - chartFrom} value="12%" source="Ofcom Media Nations 2026"
        chartW={400} chartH={100} scale={0.74} countUp glow />
      <LogoTiles from={tilesFrom} durationInFrames={fr(19.25) - tilesFrom} {...R} bottom={G} items={[{logo: 'netflix', at: 3}, {logo: 'youtube', at: w('YouTube') - 4 - tilesFrom}]} />

      {/* Why now */}
      <VoicePill from={voiceFrom} durationInFrames={fr(26.15) - voiceFrom} {...R} bottom={G} text="Sky Q voice search" voice={voice} />
      <VoiceChat from={chatFrom} durationInFrames={fr(32.4) - chatFrom} {...R} bottom={G} text="Sky, make me scared." voice={voice}
        typeStart={w('Sky, make me scared') - chatFrom} typeEnd={fr(32.25) - chatFrom} />

      {/* Why DDN: one chip-use grid that evolves (idle 5 %, then data flows in, 99 % busy, cost per token down 75 %) */}
      <ChipGrid from={idleFrom} durationInFrames={fr(41.0) - idleFrom} {...R} bottom={0.83} mode="idle" landAt={w('5%') - idleFrom} source="Cast AI, enterprise average" />
      <ChipGrid from={ddnFrom} durationInFrames={fr(54.35) - ddnFrom} {...R} bottom={0.83} mode="ddn" flowAt={w('data flowing to the chips') - ddnFrom - 4}
        landAt={w('99%') - ddnFrom} countFrames={Math.min(34, w('99%') - w('customers'))} costFrom={w('cut costs per token') - ddnFrom - 2} costLandAt={w('75%') - ddnFrom} source="per DDN" />
      <LogoTiles from={caFrom} durationInFrames={fr(58.5) - caFrom} {...R} bottom={G} items={[{logo: 'canalplus', at: 3}, {logo: 'starz', at: w('Starz') - 4 - caFrom}]} />

      {/* The ask: "30 day pilot" pill on "pilot", grows into the measure card on "Then measure", holds through "So Sky",
          leaves before "Blockbuster". Upper right: clear of the face in all four shots and of the AI sign. */}
      <MeasureCard from={askFrom} durationInFrames={fr(69.3) - askFrom} {...R} bottom={0.45}
        tag="30 day pilot" tagAt={w('pilot') - askFrom - 1} itemsAt={after(w('Then measure'), 16) - askFrom} width={500} labelSize={32} barLabelSize={24} pad={24} gap={12}
        items={[{label: 'How busy the chips are', at: after(w('Then measure'), 16) - askFrom + 2, before: 0.22, after: 0.9}, {label: 'What each answer costs', at: after(w('Then measure'), 16) - askFrom + 10, before: 0.85, after: 0.3}]} />
      <ObsoleteLogo from={bbFrom} durationInFrames={fr(70.4) - bbFrom} {...R} bottom={0.44} logo="blockbuster" greyAt={24} logoH={96} />

      <Subtitles transcript={transcript} look={PITCH_CAPTION_LOOK} anchor="center" joinGapFrames={6}
        suppress={[{from: chatFrom, to: fr(32.4)}, {from: PLATE_END - 6, to: 2400}]} />

      <EndBuild from={PLATE_END} durationInFrames={2226 - PLATE_END} />

      {showGuides ? <Guides frame={frame} z={cam.z} /> : null}
    </Footage>
  );
};

const Guides: React.FC<{frame: number; z: number}> = ({frame, z}) => {
  const i = segIndexAt(Math.min(frame, PLATE_END - 1));
  const r = (b: Box, c: string, k: string) => <div key={k} style={{position: 'absolute', left: b.x, top: b.y, width: b.w, height: b.h, border: `3px solid ${c}`}} />;
  return <>{[r(faceAt(i, z), '#00ff66', 'f'), ...keepOutZoomed(i, z).map((b, j) => r(b, '#ffcc00', `k${j}`))]}</>;
};
