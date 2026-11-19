import React, {useMemo} from 'react';
import {AbsoluteFill, Html5Audio, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {EASE, Footage, FootageSource, LineChartFall, MeasureCard, SectionBar} from '../ddn';
import plan from './shotplan_v6.json';
import caps from './captions_v4.json';
import {pitchTranscriptV3} from './captions';
import {cameraV6, faceAt, fr, keepOutZoomed, segIndexAt, Box} from './layout_v4';
import {ChairSpotlight, ChipGrid, DepthLogos, DepthShatter, EndBuild, PersonLayer, VoiceChat, VoicePill} from './graphics';
import {ArsenalGag, CleanSubtitles, LogoPlate, NameSuper, ScaleIt, Stopwatch} from './v6';

// PitchFinal v6 (final, 4K): SHOTPLAN_v6 (21 shots, last shot rests to 74.247), end card 74.247 to 77.247.
// Authored in 1920x1080 layout px; the whole film is scaled to the composition size (3840x2160) so text and
// vector graphics rasterise at full 4K resolution.
export type PitchV6Props = {plate: string; plateBlur: string | null; plateFrames: number; audio: string | null; voice: string; showGuides?: boolean};

const PLATE_END = fr(74.247); // 2227
const TOTAL = fr(77.247); // 2317
const W = plan.word_anchors as Record<string, number>;
const w = (k: string) => fr(W[k]);
const cutF = (i: number) => fr(plan.segments[i].start);
const CUTS = plan.segments.slice(1).map((s) => fr(s.start));
const SEAM_DDN = fr(32.592);
const G = 0.79;
const R = {anchor: 'right' as const};
const LOGO_POS = {netflix: [204, 64, 140], youtube: [72, 222, 120]} as const;
const BB = {x: 220, y: 60, h: 300}; // solved with scripts/logo_place.py (<= 3 % tucked behind his hair at one edge)
const PERSON = [{src: 'pitch/person_s3.webm', from: 497, to: 583}, {src: 'pitch/person_s19.webm', from: 2148, to: 2182}];

type CapWord = {text: string; start: number; end: number};
const capWords = (caps as {words: CapWord[]}[]).flatMap((p) => p.words);
const wordAt = (text: string, after: number) => capWords.find((x) => x.text.replace(/[^A-Za-z0-9%]/g, '').toLowerCase() === text.toLowerCase() && x.start >= after - 0.05)!;

export const PitchV6: React.FC<PitchV6Props> = (props) => {
  const {width} = useVideoConfig();
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, transformOrigin: '0 0', transform: `scale(${width / 1920})`}}>
        <Film {...props} />
      </div>
    </AbsoluteFill>
  );
};

const Film: React.FC<PitchV6Props> = ({plate, plateBlur, plateFrames, audio, voice, showGuides = false}) => {
  const frame = useCurrentFrame();
  const transcript = useMemo(() => pitchTranscriptV3(), []);
  const cam = cameraV6(Math.min(frame, PLATE_END - 1));
  // End: dissolve to the end card from MOVING footage (no freeze while visible): blur and a 2 % push over 14 f
  // starting 12 f before the last frame of picture.
  const endT = interpolate(frame, [PLATE_END - 12, PLATE_END + 2], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.inOut});
  const blur = cam.blur + 16 * endT;
  const camStyle: React.CSSProperties = {transformOrigin: `${cam.origin[0]}px ${cam.origin[1]}px`, transform: `scale(${(cam.z * (1 + 0.02 * endT)).toFixed(5)})`, filter: blur > 0.05 ? `blur(${blur.toFixed(2)}px)` : undefined};
  const footage: FootageSource = {
    src: plate, kind: 'video', blurredSrc: plateBlur ?? undefined,
    freezeAt: frame >= plateFrames ? plateFrames - 1 : undefined, // only ever under the opaque end card
    style: camStyle,
  };

  const after = (f: number, seg: number) => Math.max(f, cutF(seg) + 2);
  const chartFrom = after(w('Ofcom') - 3, 2);
  const tilesFrom = after(w('Netflix') - 4, 3);
  const voiceFrom = w('Sky Q voice search') - 16;
  const chatFrom = w('AI assistant') - 4;
  const idleFrom = w('Cast AI') - 4;
  const ddnFrom = w("DDN's Infinia") - 4;
  const arsFrom = fr(43.75);
  const caFrom = w('Canal Plus') - 4;
  const askFrom = w('pilot') - 5;
  const bbFrom = w('Blockbuster') - 5;
  const scaleFrom = cutF(17) + 1;
  const scaleTo = cutF(18);
  const sk = [wordAt('if', 67.5), wordAt('both', 67.5), wordAt('improve', 67.5)];
  const chatWords = ['Sky', 'make', 'me', 'scared'].map((t) => wordAt(t, 30.8));

  return (
    <Footage source={footage}>
      {audio ? <Html5Audio src={staticFile(audio)} /> : null}

      <AbsoluteFill style={{transformOrigin: camStyle.transformOrigin, transform: `scale(${cam.z.toFixed(5)})`}}>
        <ChairSpotlight dimIn={[w("That's AI chips"), w("That's AI chips") + 11]} dimOut={[w("That's AI chips") + 44, w("That's AI chips") + 59]}
          lineIn={[w("That's AI chips"), w("That's AI chips") + 12]} offAt={[w("That's AI chips") + 44, w("That's AI chips") + 59]} />
        <DepthLogos from={tilesFrom} durationInFrames={fr(19.25) - tilesFrom} items={[
          {logo: 'netflix', at: 3, x: LOGO_POS.netflix[0], y: LOGO_POS.netflix[1], h: LOGO_POS.netflix[2]},
          {logo: 'youtube', at: w('YouTube') - 4 - tilesFrom, x: LOGO_POS.youtube[0], y: LOGO_POS.youtube[1], h: LOGO_POS.youtube[2]}]} />
        <DepthShatter from={bbFrom} durationInFrames={cutF(20) - bbFrom} x={BB.x} y={BB.y} h={BB.h} crackAt={fr(71.9) - bbFrom} breakAt={fr(71.98) - bbFrom} />
      </AbsoluteFill>
      {PERSON.map((pl) => <PersonLayer key={pl.src} src={pl.src} plateFrom={pl.from} durationInFrames={pl.to - pl.from} style={camStyle} />)}

      {/* Hook: stopwatch from "Sorry" (no total shown), name super top left after he turns to camera. */}
      <Stopwatch from={fr(0.85)} durationInFrames={fr(2.9) - fr(0.85)} clockZero={w('Sorry')} anchor="right" bottom={0.3} />
      <NameSuper from={fr(3.6)} durationInFrames={fr(6.8) - fr(3.6)} name="Eliud Awuah" role="T Level Placement Student" />

      {/* Progress: hidden from "So Sky" (69.943) on: its exit ends on that cut. */}
      <SectionBar sections={plan.sections_for_progress_bar.map((s) => ({label: s.label, from: fr(s.start)}))} from={fr(plan.sections_for_progress_bar[0].start)}
        durationInFrames={cutF(18) - fr(plan.sections_for_progress_bar[0].start)} />

      <LineChartFall from={chartFrom} durationInFrames={fr(16.4) - chartFrom} {...R} bottom={G} valueAt={w('12%') - chartFrom} value="12%" source="Ofcom Media Nations 2026"
        chartW={400} chartH={100} scale={0.66} countUp glow />
      <VoicePill from={voiceFrom} durationInFrames={fr(26.2) - voiceFrom} {...R} bottom={0.645} text="Sky Q voice search" voice={voice} />
      <VoiceChat from={chatFrom} durationInFrames={SEAM_DDN - chatFrom} {...R} bottom={G} text="Sky, make me scared." voice={voice}
        typeStart={fr(chatWords[0].start) - chatFrom} typeEnd={fr(chatWords[3].start) - chatFrom} openAt={w('Imagine asking') - chatFrom}
        wordStarts={chatWords.map((x) => fr(x.start) - chatFrom)} />
      <ChipGrid from={idleFrom} durationInFrames={fr(41.0) - idleFrom} {...R} bottom={0.8} mode="idle" landAt={w('5%') - idleFrom} source="Cast AI, enterprise average" label="AVERAGE USE" />
      <ArsenalGag from={arsFrom} durationInFrames={fr(45.45) - arsFrom} {...R} bottom={G} loseAt={w('Arsenal lose') - arsFrom} />
      <ChipGrid from={ddnFrom} durationInFrames={fr(54.35) - ddnFrom} {...R} bottom={0.8} mode="ddn" flowAt={w('data flowing to the chips') - ddnFrom - 4} label="BUSY, UP TO"
        landAt={w('99%') - ddnFrom} countFrames={Math.min(34, w('99%') - w('customers'))} costFrom={w('cut costs per token') - ddnFrom - 2} costLandAt={w('75%') - ddnFrom} source="per DDN" />
      <LogoPlate from={caFrom} durationInFrames={fr(58.62) - caFrom} anchor="left" bottom={0.6} logo="canalplus" logoH={92} />
      <LogoPlate from={caFrom + 6} durationInFrames={fr(58.62) - caFrom - 6} {...R} bottom={G} logo="starz" logoH={92} />

      {/* Ask card holds long (items from "voice search"); the payoff is its own moment below. */}
      <MeasureCard from={askFrom} durationInFrames={cutF(17) - 2 - askFrom} {...R} bottom={0.45}
        tag="30 day pilot" tagAt={w('pilot') - askFrom - 1} itemsAt={w('voice search (ask)') - askFrom} width={500} labelSize={32} barLabelSize={24} pad={24} gap={12}
        items={[{label: 'How busy the chips are', at: w('voice search (ask)') - askFrom + 2, before: 0.22, after: 0.9}, {label: 'What each answer costs', at: w('voice search (ask)') - askFrom + 10, before: 0.85, after: 0.3}]} />
      <ScaleIt from={scaleFrom} durationInFrames={scaleTo - scaleFrom} x={1000} y={170} landAt={w('scale it') - scaleFrom}
        words={[{text: 'If', at: Math.max(2, fr(sk[0].start) - scaleFrom)}, {text: 'both', at: fr(sk[1].start) - scaleFrom}, {text: 'improve', at: fr(sk[2].start) - scaleFrom}]} />

      <CleanSubtitles transcript={transcript} snapTo={CUTS}
        suppress={[{from: w('Imagine asking'), to: SEAM_DDN}, {from: cutF(17), to: cutF(18)}, {from: PLATE_END - 14, to: TOTAL + 10}]} />

      <EndBuild from={PLATE_END - 12} durationInFrames={TOTAL - (PLATE_END - 12)} />

      {showGuides ? <Guides frame={frame} z={cam.z} /> : null}
    </Footage>
  );
};

const Guides: React.FC<{frame: number; z: number}> = ({frame, z}) => {
  const i = segIndexAt(Math.min(frame, PLATE_END - 1));
  const r = (b: Box, c: string, k: string) => <div key={k} style={{position: 'absolute', left: b.x, top: b.y, width: b.w, height: b.h, border: `3px solid ${c}`}} />;
  return <>{[r(faceAt(i, z), '#00ff66', 'f'), ...keepOutZoomed(i, z).map((b, j) => r(b, '#ffcc00', `k${j}`))]}</>;
};
