import React, {useMemo} from 'react';
import {Html5Audio, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {
  BigWord, BusyGauge, ChatBubble, EASE, EndCard, Footage, FootageSource, KeywordStack, LineChartFall, MeasureCard, PITCH_CAPTION_LOOK,
  PitchTimer, SectionBar, StatCard, Subtitles,
} from '../ddn';
import plan from './shotplan.json';
import {pitchTranscript} from './captions';
import {SEG_LAYOUT, segmentAt, zoomAt, Box} from './layout';

// The 80 s pitch film. Picture plate (edit/plates_noblur/plate.mp4, 2304x1296, 0 to 77.0 s) fitted to 1920x1080,
// per-segment eased push-ins centred on the face (reset at every picture cut), frosted graphics on spoken words,
// short-form captions, end card handed off from a blurred freeze of the last frame. Timing: edit/SHOTPLAN.json (v3).
export type PitchFinalProps = {
  plate: string; // public path, e.g. 'pitch/plate.mp4' or 'pitch/rough_v1.mp4'
  plateBlur: string | null; // pre-blurred proxy for the frost (same timing), or null for CSS blur
  voice: string | null; // preview voice
  showGuides?: boolean; // draw face / keep-out boxes (QA only)
};

const FPS = 30;
const f = (s: number) => Math.round(s * FPS);
const PLATE_END = f(77.0); // 2310: first frame without picture
// Right-anchored graphics sit BELOW the monitors (checked per shot with showGuides), so the monitor boxes are not
// passed as Slot obstacles (they would squeeze the width: the monitor and the graphic share x but not y).
const G_BOTTOM = 0.81; // graphics bottom: clears the one-line caption pill (bottom 8 % H, about 92 px tall)
const PLACE_R = {anchor: 'right' as const, bottom: G_BOTTOM};

export const PitchFinal: React.FC<PitchFinalProps> = ({plate, plateBlur, voice, showGuides = false}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const transcript = useMemo(() => pitchTranscript(), []);

  // Footage with the push-in of the current segment. The same style drives the frost copies, so glass stays aligned.
  const t = Math.min(frame, PLATE_END - 1) / fps;
  const seg = segmentAt(t);
  const z = zoomAt(t);
  const o = SEG_LAYOUT[seg.i].center;
  const endT = interpolate(frame, [PLATE_END, PLATE_END + 18], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.inOut});
  const footage: FootageSource = {
    src: plate, kind: 'video', blurredSrc: plateBlur ?? undefined,
    freezeAt: frame >= PLATE_END ? PLATE_END - 1 : undefined,
    style: {transformOrigin: `${o[0]}px ${o[1]}px`, transform: `scale(${(z * (1 + 0.04 * endT)).toFixed(5)})`, filter: endT > 0 ? `blur(${(18 * endT).toFixed(2)}px)` : undefined},
  };

  const g = Object.fromEntries(plan.graphics.map((x) => [x.id, x]));
  const cut = (i: number) => f(plan.segments[i].start); // picture cut frame

  // Slots from the plan, nudged so no entrance starts on (or before) a picture cut it would otherwise span.
  const chartFrom = Math.max(f(g.ofcom_chart.in), cut(2) + 2);
  const streamFrom = Math.max(f(g.netflix.in) - 4, cut(3) + 2);
  const chatFrom = f(g.chat_bubble.in);
  const statFrom = f(g.stat_5.in);
  const gaugeFrom = f(g.busy_gauge.in);
  const card99From = f(g.stat_99_75.in) - 6; // 6 f overlap: the gauge hands off into the card
  const logosFrom = f(g.canal.in) - 4;
  const askFrom = f(g.pilot_tag.in) - 4;
  const bbFrom = f(g.blockbuster.in) - 4;

  return (
    <Footage source={footage}>
      {voice ? <Html5Audio src={staticFile(voice)} /> : null}

      <PitchTimer from={f(g.timer.in)} durationInFrames={f(g.timer.out) - f(g.timer.in)} clockZero={f(1.85)} anchor="right" bottom={0.3} />

      {/* Progress: presents at each section change (picture cut), then condenses to a slim top strip. */}
      <SectionBar sections={[{label: 'Why change', from: cut(1)}, {label: 'Why now', from: cut(4)}, {label: 'Why DDN', from: cut(7)}, {label: 'The ask', from: cut(13)}]}
        from={cut(1)} durationInFrames={f(g.progress.out) - cut(1)} />

      <LineChartFall from={chartFrom} durationInFrames={f(g.ofcom_chart.out) - chartFrom} {...PLACE_R}
        valueAt={f(14.63) - chartFrom} value="12%" source="Ofcom Media Nations 2026" chartW={420} chartH={104} scale={0.76} />

      <KeywordStack from={streamFrom} durationInFrames={f(g.netflix.out) - streamFrom} {...PLACE_R} show="logo" logoHeight={50}
        items={[{text: 'Netflix', logo: 'netflix', at: 3}, {text: 'YouTube', logo: 'youtube', at: f(g.youtube.in) - 4 - streamFrom}]} />

      <ChatBubble from={chatFrom} durationInFrames={f(g.chat_bubble.out) - chatFrom} {...PLACE_R}
        text="Sky, make me scared." size={50} breakAfterComma={false} typeStart={f(33.47) - chatFrom} typeEnd={f(34.41) - chatFrom} />

      <StatCard from={statFrom} durationInFrames={f(g.stat_5.out) - statFrom} {...PLACE_R}
        value="5%" source="Cast AI, enterprise average" landAt={f(42.43) - statFrom} scale={0.8} />

      <BusyGauge from={gaugeFrom} durationInFrames={f(g.busy_gauge.out) - gaugeFrom} {...PLACE_R}
        fromValue={5} toValue={99} source="per DDN" landAt={f(53.67) - gaugeFrom} riseFrames={30} scale={0.72} />
      <StatCard from={card99From} durationInFrames={f(g.stat_99_75.out) - card99From} {...PLACE_R}
        value="99% busy," countFrom={99} lines={['75% lower cost per token']} source="per DDN" linesAt={f(56.77) - card99From} scale={0.72} />

      <KeywordStack from={logosFrom} durationInFrames={f(g.canal.out) - logosFrom} {...PLACE_R} show="logo" logoHeight={50}
        items={[{text: 'Canal Plus', logo: 'canalplus', at: 3}, {text: 'Starz', logo: 'starz', at: f(g.starz.in) - 4 - logosFrom}]} />

      {/* The ask: a "30 day pilot" pill on "pilot", grows into the measure card on "Then measure", holds across the
          close-up cut (same place, clear of the face in both shots and of the AI sign), leaves before "Blockbuster". */}
      <MeasureCard from={askFrom} durationInFrames={f(g.ask_card.out) - askFrom} anchor="right" bottom={500 / 1080}
        tag="30 day pilot" tagAt={f(65.39) - askFrom - 2} itemsAt={f(69.11) - askFrom} width={500} labelSize={32} barLabelSize={24} pad={24} gap={12}
        items={[{label: 'How busy the chips are', at: f(69.11) - askFrom + 2, before: 0.22, after: 0.9}, {label: 'What each answer costs', at: f(69.11) - askFrom + 12, before: 0.85, after: 0.3}]} />

      <BigWord from={bbFrom} durationInFrames={f(g.blockbuster.out) - bbFrom} anchor="left" bottom={G_BOTTOM}
        text="Blockbuster" logo="blockbuster" show="logo" logoHeight={110} at={4} />

      <Subtitles transcript={transcript} look={PITCH_CAPTION_LOOK} anchor="center"
        suppress={[{from: chatFrom, to: f(g.chat_bubble.out)}, {from: PLATE_END - 8, to: f(80) + 1}]} />

      <EndCard from={PLATE_END} durationInFrames={f(80) - PLATE_END} logo />

      {showGuides ? <Guides i={seg.i} /> : null}
    </Footage>
  );
};

const Guides: React.FC<{i: number}> = ({i}) => {
  const L = SEG_LAYOUT[i];
  const r = (b: Box, c: string, k: string) => <div key={k} style={{position: 'absolute', left: b.x, top: b.y, width: b.w, height: b.h, border: `3px solid ${c}`}} />;
  return <>{[r(L.faceZoomed, '#00ff66', 'f'), ...L.avoidZoomed.map((b, j) => r(b, '#ffcc00', `a${j}`))]}</>;
};
