// captions_v2.json -> Transcript for <Subtitles>, re-chunked to the pitch caption rule (RESEARCH_ROUND2 P3):
// one line, 3 to 6 words, at most 42 characters. Long phrases split at the best balanced point, preferring a comma.
import raw from './captions_v2.json';
import raw3 from './captions_v3.json';
import type {Transcript, Word} from '../ddn';

const MAX_WORDS = 6;
const MAX_CHARS = 42;
const len = (ws: Word[]) => ws.map((w) => w.text).join(' ').length;

const split = (ws: Word[]): Word[][] => {
  if (ws.length <= MAX_WORDS && len(ws) <= MAX_CHARS) return [ws];
  let best = 1;
  let bestScore = Infinity;
  for (let k = 2; k <= ws.length - 2; k++) {
    const a = ws.slice(0, k);
    const b = ws.slice(k);
    const score = Math.abs(len(a) - len(b)) - (/[,.;:?!]$/.test(ws[k - 1].text) ? 12 : 0);
    if (score < bestScore) {
      bestScore = score;
      best = k;
    }
  }
  return [...split(ws.slice(0, best)), ...split(ws.slice(best))];
};

type RawPhrase = {words: {text: string; start: number; end: number; emphasis: boolean}[]};
export const pitchTranscript = (): Transcript => makeTranscript(raw as RawPhrase[]);
// v4: also enforce a minimum on-screen time (0.35 s): a chunk shorter than that joins its neighbour when the
// joined phrase still fits the one-line rule, so tight pacing never makes the caption flicker.
export const pitchTranscriptV3 = (): Transcript => {
  const t = makeTranscript(raw3 as RawPhrase[]);
  const out: {from: number; to: number}[] = [];
  for (const ph of t.phrases) {
    const dur = t.words[ph.to].end - t.words[ph.from].start;
    const prev = out[out.length - 1];
    if (prev && dur < 0.35) {
      const ws = t.words.slice(prev.from, ph.to + 1);
      if (ws.length <= MAX_WORDS && len(ws) <= MAX_CHARS) {
        prev.to = ph.to;
        continue;
      }
    }
    out.push({...ph});
  }
  return {words: t.words, phrases: out};
};

const makeTranscript = (rawPhrases: RawPhrase[]): Transcript => {
  const words: Word[] = [];
  const phrases: {from: number; to: number}[] = [];
  for (const p of rawPhrases as {words: {text: string; start: number; end: number; emphasis: boolean}[]}[]) {
    for (const chunk of split(p.words.map((w) => ({text: w.text, start: w.start, end: w.end, emphasis: w.emphasis})))) {
      phrases.push({from: words.length, to: words.length + chunk.length - 1});
      words.push(...chunk);
    }
  }
  return {words, phrases};
};
