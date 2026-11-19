import React from 'react';
import {useVideoConfig} from 'remotion';
import {BigWord, MeasureCard, Box, BusyGauge, ChatBubble, EndCard, Footage, FootageSource, KeywordStack, LineChartFall, PitchTimer, SectionProgress, StatCard, Subtitles, Transcript} from './ddn';
import {buildDemo} from './ddn/demoScript';

export const DEMO = buildDemo();
// Face box of the stand-in plate (Paul Bloch frame, speaker right). px @1920x1080.
export const DEMO_FACE: Box = {x: 1285, y: 140, w: 310, h: 430};
// Stand-in footage: 3 s "empty room" (crop of the plate's wall, stands in for the empty AI chip chair), then the
// interview plate with a slow 5 % push-in, so the frost alignment is tested on moving footage.
export const DEMO_FOOTAGE: FootageSource = {src: 'demo/standin_footage.mp4', blurredSrc: 'demo/standin_footage_blur34.mp4', blurredPx: 34, kind: 'video'};
export const CHAIR_SHOT_S = 3.0;
export const CLOCK_ZERO_S = 1.5; // the empty chair holds alone for 1.5 s, then the 90 s begin

export type GraphicsDemoProps = {footage: FootageSource | null; faceBox: Box; avoid: Box[]; showProgress: boolean; showTimer: boolean; logos: boolean};

export const GraphicsDemo: React.FC<GraphicsDemoProps> = ({footage, faceBox, avoid, showProgress, showTimer, logos}) => {
  const {fps} = useVideoConfig();
  const {transcript, lines, sections} = DEMO;
  const L = Object.fromEntries(lines.map((l) => [l.key, l]));
  const f = (s: number) => Math.round(s * fps);
  const w = (i: number) => transcript.words[i];
  const place = {faceBox, avoid};
  // A graphic lives for its line: from first word (3 f early) to last word + 0.3 s, clipped to the next line.
  const slot = (key: string, fromWord?: number) => {
    const l = L[key];
    const idx = lines.indexOf(l);
    const next = lines[idx + 1];
    const s = fromWord !== undefined ? w(fromWord).start : l.start;
    const from = f(s) - 3;
    const end = Math.min(f(l.end + 0.3), next ? f(next.start) - 3 : Infinity);
    return {from, durationInFrames: end - from, ...place};
  };
  const wordIdx = (key: string, text: string) => {
    const l = L[key];
    for (let i = l.firstWord; i <= l.lastWord; i++) if (w(i).text.replace(/[^A-Za-z0-9%]/g, '') === text) return i;
    throw new Error(`word ${text} not in ${key}`);
  };
  const rel = (key: string, text: string) => f(w(wordIdx(key, text)).start) - slot(key).from - 3;
  const end = slot('end');
  const sub: Transcript = transcript;
  const logo = logos ? 'logo' : 'text';

  // Section spans for the progress indicator: each section runs to the next one; the ask runs to the end card.
  const labels: Record<string, {label: string; weight: number}> = {
    'Why change': {label: 'Why change', weight: 25}, 'Why now': {label: 'Why now', weight: 20},
    'Why DDN': {label: 'Why DDN', weight: 40}, Ask: {label: 'The ask', weight: 0}, // text label: the real Why DDN shots already show a DDN logo on a monitor
  };
  const prog = sections.map((s, i) => ({...labels[s.name], from: f(s.start) - 3, to: i + 1 < sections.length ? f(sections[i + 1].start) - 3 : end.from}));

  return (
    <Footage source={footage}>
      {showTimer ? <PitchTimer from={f(CLOCK_ZERO_S) - 14} durationInFrames={f(CHAIR_SHOT_S + 1.3 - CLOCK_ZERO_S) + 14} clockZero={f(CLOCK_ZERO_S)} anchor="center" bottom={0.6} scale={1.2} /> : null}
      {showProgress ? <SectionProgress sections={prog} from={prog[0].from} durationInFrames={end.from + 10 - prog[0].from} {...place} /> : null}

      <LineChartFall {...slot('chart')} valueAt={rel('chart', '12%') + 3} value="12%" source="Ofcom Media Nations 2026" />
      <KeywordStack {...slot('streamers', wordIdx('streamers', 'Netflix'))} show={logo} items={[{text: 'Netflix', logo: 'netflix', at: 3}, {text: 'YouTube', logo: 'youtube', at: f(w(wordIdx('streamers', 'YouTube')).start - w(wordIdx('streamers', 'Netflix')).start) + 3}]} />
      <ChatBubble {...slot('chat')} text="Find me a show my kids will love." breakAfterComma={false} />
      <StatCard {...slot('five')} value="5%" source="Cast AI, enterprise average" />
      <BusyGauge {...slot('gauge')} fromValue={5} toValue={99} source="per DDN" />
      <StatCard {...slot('ninetynine')} value="99% busy," lines={['75% lower cost per token']} source="per DDN" />
      <KeywordStack {...slot('customers')} show={logo} items={[{text: 'Canal Plus', logo: 'canalplus', at: 3}, {text: 'Starz', logo: 'starz', at: rel('customers', 'Starz') + 3}]} />
      {/* The ask: appears on "Then measure", holds through the next line, leaves just before the Blockbuster payoff. */}
      <MeasureCard from={f(w(wordIdx('measure', 'Then')).start) - 3} durationInFrames={f(w(wordIdx('blockbuster', 'Blockbuster')).start) - 8 - (f(w(wordIdx('measure', 'Then')).start) - 3)} {...place}
        tag="30 day pilot" items={[{label: 'How busy the chips are', at: 6, before: 0.22, after: 0.9}, {label: 'What each answer costs', at: f(w(wordIdx('measure', 'before')).start - w(wordIdx('measure', 'Then')).start) + 3, before: 0.85, after: 0.3}]} />
      {/* The payoff lands on its word and holds into the end card's dissolve (its exit overlaps the grey fade-in). */}
      <BigWord {...slot('blockbuster', wordIdx('blockbuster', 'Blockbuster'))} durationInFrames={end.from + 14 - slot('blockbuster', wordIdx('blockbuster', 'Blockbuster')).from} text="Blockbuster" logo="blockbuster" show={logo} />

      <Subtitles transcript={sub} faceBox={faceBox} avoid={avoid} anchor="auto" suppress={[{from: slot('chat').from, to: slot('chat').from + slot('chat').durationInFrames}, {from: end.from, to: end.from + 600}]} />
      <EndCard from={end.from} durationInFrames={Math.ceil((DEMO.total + 1.5) * fps) - end.from} logo={logos} />
    </Footage>
  );
};
