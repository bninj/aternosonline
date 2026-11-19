// Stand-in pitch script with synthetic word timestamps, in the same JSON shape real transcripts use.
// Durations approximate speech at ~2.7 words/s. Replace with faster-whisper word times for the real cut.
import {Transcript, Word} from './Subtitles';

export type Line = {key: string; phrases: string[]};

export const SCRIPT: {section: string; lines: Line[]}[] = [
  {section: 'Why change', lines: [
    {key: 'chart', phrases: ['Live TV viewing', 'fell 12% in a year.']},
    {key: 'streamers', phrases: ['Families drift', 'to Netflix and YouTube.']},
  ]},
  {section: 'Why now', lines: [
    {key: 'ask', phrases: ['Parents ask Sky', 'for one thing.']},
    {key: 'chat', phrases: ['Find me a show', 'my kids will love.']},
  ]},
  {section: 'Why DDN', lines: [
    {key: 'five', phrases: ['Most enterprise chips', 'sit at 5% busy.']},
    {key: 'gauge', phrases: ['With DDN,', 'they run near 99%.']},
    {key: 'ninetynine', phrases: ['99% busy,', '75% lower cost per token.']},
    {key: 'customers', phrases: ['Canal Plus and Starz', 'already run on it.']},
  ]},
  {section: 'Ask', lines: [
    {key: 'measure', phrases: ['Run a 30 day pilot.', 'Then measure the values', 'before and after.']},
    {key: 'blockbuster', phrases: ['That is how Sky finds', 'its next Blockbuster.']},
    {key: 'end', phrases: ['DDN.', 'Keep the chips busy.']},
  ]},
];

const wordDur = (w: string) => (/\d/.test(w) ? 0.55 : 0.14 + 0.05 * w.replace(/[^A-Za-z]/g, '').length);

export type LineSpan = {key: string; section: string; start: number; end: number; firstWord: number; lastWord: number};

export const buildDemo = (startAt = 4.6) => {
  const words: Word[] = [];
  const phrases: {from: number; to: number}[] = [];
  const lines: LineSpan[] = [];
  const sections: {name: string; start: number}[] = [];
  let t = startAt;
  SCRIPT.forEach((sec, si) => {
    if (si > 0) t += 0.5;
    sections.push({name: sec.section, start: t});
    sec.lines.forEach((ln) => {
      const first = words.length;
      const lineStart = t;
      ln.phrases.forEach((ph, pi) => {
        if (pi > 0) t += 0.16;
        const from = words.length;
        ph.split(' ').forEach((w) => {
          const d = wordDur(w);
          words.push({text: w, start: +t.toFixed(3), end: +(t + d).toFixed(3)});
          t += d + 0.04;
        });
        phrases.push({from, to: words.length - 1});
      });
      lines.push({key: ln.key, section: sec.section, start: lineStart, end: words[words.length - 1].end, firstWord: first, lastWord: words.length - 1});
      t += 0.42;
    });
  });
  const transcript: Transcript = {words, phrases};
  return {transcript, lines, sections, total: t + 0.3};
};
