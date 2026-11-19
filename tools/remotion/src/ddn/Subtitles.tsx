import React, {useMemo} from 'react';
import {AbsoluteFill, interpolate, Sequence, useCurrentFrame, useVideoConfig} from 'remotion';
import {measureText} from '@remotion/layout-utils';
import {C, EASE, FRAME, SAFE, T, TYPE} from './tokens';
import {display, FONT, TypeRole, useFontsReady} from './fonts';
import {EnvelopeProvider, FrostedGlass, makeEnvelope, MotionBlurWhileMoving, Reveal} from './primitives';
import {onScreen} from './sanitize';
import {Box, obstacles, overlaps} from './layout';

// Input JSON shape (seconds). Phrases are inclusive word index ranges: one short phrase per card.
export type Word = {text: string; start: number; end: number; emphasis?: boolean}; // emphasis: explicit flag wins over the list
export type PhraseGroup = {from: number; to: number};
export type Transcript = {words: Word[]; phrases: PhraseGroup[]};

export type SubtitlesProps = {
  transcript: Transcript;
  emphasis?: string[]; // whole words to mark, besides any token with a digit
  anchor?: 'center' | 'left' | 'right' | 'auto';
  faceBox?: Box;
  avoid?: Box[];
  holdAfterLastWord?: number; // s a card stays after its last word if the next card is later
  strict?: boolean; // dash sanitiser: throw (default) or only warn
  suppress?: {from: number; to: number}[]; // frame ranges with no caption (e.g. a chat bubble already shows the words) [4.6]
  joinGapFrames?: number; // phrases closer than this share one plate and swap softly (default 8)
  look?: Partial<CaptionLook>;
};

// Caption look. DDN 2026 default: 78 px regular on an 18 px radius plate, two lines allowed. The pitch film uses the
// short-form preset (PITCH_CAPTION_LOOK): one line, 48 px semi-bold, frosted pill, 8 % bottom margin.
export type CaptionLook = {size: number; role: TypeRole; emphRole: TypeRole; padX: number; padY: number; radius: number; bottomPx: number; maxLines: number};
export const DDN_CAPTION_LOOK: CaptionLook = {size: TYPE.caption, role: 'regular', emphRole: 'medium', padX: 56, padY: 30, radius: 18, bottomPx: FRAME.h * SAFE.margin, maxLines: 2};
export const PITCH_CAPTION_LOOK: CaptionLook = {size: 46, role: 'bold', emphRole: 'bold', padX: 30, padY: 14, radius: 999, bottomPx: Math.round(FRAME.h * 0.08), maxLines: 1};

export const DEFAULT_EMPHASIS = ['DDN', 'Sky'];
const isEmph = (core: string, list: string[], flag?: boolean) => (flag !== undefined ? flag : /\d/.test(core) || list.includes(core));

// Split "Sky." into core "Sky" and trailing punctuation so only the word is marked.
const splitWord = (w: string) => {
  const m = w.match(/^([^A-Za-z0-9%£$€]*)(.*?)([^A-Za-z0-9%]*)$/);
  return m ? {lead: m[1], core: m[2], trail: m[3]} : {lead: '', core: w, trail: ''};
};

export const phraseWindows = (t: Transcript, fps: number, hold = 0.5) =>
  t.phrases.map((p, i) => {
    const s = t.words[p.from].start;
    const e = t.words[p.to].end;
    const next = t.phrases[i + 1] ? t.words[t.phrases[i + 1].from].start : Infinity;
    const from = Math.max(0, Math.round(s * fps) - T.captionLeadFrames);
    const to = Math.min(Math.round((e + hold) * fps), Math.round(next * fps) - T.captionLeadFrames);
    return {from, to, words: t.words.slice(p.from, p.to + 1)};
  });

type Laid = {lines: {words: {lead: string; core: string; trail: string; emph: boolean; start: number}[]}[]; w: number; h: number; look: CaptionLook};
const lineH = (l: CaptionLook) => Math.round(l.size * 1.25);

// Deterministic layout: greedy wrap, then balance two lines. The plate size is known per phrase, so it can tween.
const layoutPhrase = (words: Word[], emphasis: string[], maxText: number, look: CaptionLook): Laid => {
  const CAP = display(look.role, look.size);
  const EMPH = display(look.emphRole, look.size);
  const measure = (text: string, weight: '400' | '500') => {
    const t = weight === '500' ? EMPH : CAP;
    return measureText({text, fontFamily: FONT.displayFamilyLoaded, fontSize: t.fontSize, fontWeight: String(t.fontWeight), letterSpacing: t.letterSpacing}).width;
  };
  const space = measure('a a', '400') - measure('aa', '400');
  const items = words.map((w) => {
    const s = splitWord(w.text.trim());
    const emph = isEmph(s.core, emphasis, w.emphasis);
    const width = measure(s.lead, '400') + measure(s.core, emph ? '500' : '400') + measure(s.trail, '400');
    return {...s, emph, start: w.start, width};
  });
  const lineW = (arr: typeof items) => arr.reduce((a, it, i) => a + it.width + (i ? space : 0), 0);
  let lines: (typeof items)[] = [];
  let cur: typeof items = [];
  for (const it of items) {
    if (look.maxLines > 1 && cur.length && lineW([...cur, it]) > maxText) {
      lines.push(cur);
      cur = [];
    }
    cur.push(it);
  }
  if (cur.length) lines.push(cur);
  if (lines.length === 2) {
    const all = [...lines[0], ...lines[1]];
    let best = lines;
    let bestW = Math.max(lineW(lines[0]), lineW(lines[1]));
    for (let k = 1; k < all.length; k++) {
      const a = all.slice(0, k);
      const b = all.slice(k);
      const m = Math.max(lineW(a), lineW(b));
      if (m < bestW && lineW(a) <= maxText && lineW(b) <= maxText) {
        best = [a, b];
        bestW = m;
      }
    }
    lines = best;
  }
  const w = Math.max(...lines.map(lineW));
  return {lines: lines.map((l) => ({words: l})), w: Math.ceil(w) + 2 * look.padX + 6, h: lines.length * lineH(look) + 2 * look.padY, look};
};

// Emphasis: white text on a Brand Red marker that wipes in (ddn-out, 7 f) as the word is spoken.
// White on #ED2738 is 3.9:1 (large text AA); red text on smoked glass over a cream wall could not be guaranteed.
const Marked: React.FC<{text: string; startFrame: number; look: CaptionLook}> = ({text, startFrame, look}) => {
  const EMPH = display(look.emphRole, look.size);
  const frame = useCurrentFrame();
  const p = interpolate(frame, [startFrame, startFrame + 9], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.inOut});
  return (
    <span style={{position: 'relative', display: 'inline-block', fontWeight: EMPH.fontWeight, letterSpacing: EMPH.letterSpacing}}>
      <span style={{position: 'absolute', left: -Math.round(look.size * 0.12), right: -Math.round(look.size * 0.12), top: '17%', bottom: '11%', background: C.red, borderRadius: Math.round(look.size * 0.12), transformOrigin: 'left center', transform: `scaleX(${p})`, opacity: p > 0 ? 1 : 0}} />
      <span style={{position: 'relative'}}>{text}</span>
    </span>
  );
};

const PhraseText: React.FC<{laid: Laid; opacity: number; y: number; blur: number; fps: number; runFrom: number}> = ({laid, opacity, y, blur, fps, runFrom}) => (
  <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', opacity,
    transform: `translateY(${y.toFixed(2)}px)`, filter: blur > 0.05 ? `blur(${blur.toFixed(2)}px)` : undefined}}>
    {laid.lines.map((l, i) => (
      <div key={i} style={{height: lineH(laid.look), lineHeight: `${lineH(laid.look)}px`, whiteSpace: 'nowrap', ...display(laid.look.role, laid.look.size),
        color: 'rgba(255,255,255,0.97)', fontFeatureSettings: '"tnum" 1', textShadow: '0 1px 12px rgba(20,10,14,0.25)'}}>
        {l.words.map((w, j) => (
          <React.Fragment key={j}>
            {j > 0 ? ' ' : ''}
            {w.lead}
            {w.emph ? <Marked text={w.core} startFrame={Math.round(w.start * fps) - runFrom} look={laid.look} /> : w.core}
            {w.trail}
          </React.Fragment>
        ))}
      </div>
    ))}
  </div>
);

type Run = {from: number; to: number; phrases: {from: number; to: number; laid: Laid}[]};

const RunBody: React.FC<{run: Run; fps: number; justify: string; side: number; bottom: number}> = ({run, fps, justify, side, bottom}) => {
  const frame = useCurrentFrame(); // relative to run.from
  const env = makeEnvelope(run.to - run.from, {delay: 0, enter: 10, exit: 8});
  const rel = run.phrases.map((p) => ({...p, from: p.from - run.from, to: p.to - run.from}));
  let i = rel.findIndex((p) => frame >= p.from && frame < p.to);
  if (i < 0) i = frame < rel[0].from ? 0 : rel.length - 1;
  const cur = rel[i];
  const prev = i > 0 ? rel[i - 1] : null;
  const s = T.swapFrames;
  const t = prev ? interpolate(frame, [cur.from, cur.from + s], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.inOut}) : 1; // plate size: in-out, no first-frame snap
  const w = prev ? prev.laid.w + (cur.laid.w - prev.laid.w) * t : cur.laid.w;
  const h = prev ? prev.laid.h + (cur.laid.h - prev.laid.h) * t : cur.laid.h;
  const out = prev ? interpolate(frame, [cur.from - 1, cur.from + 6], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.inOut}) : 1;
  return (
    <EnvelopeProvider value={env}>
      <MotionBlurWhileMoving env={env} samples={5}>
        <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: justify, padding: `0 ${side}px ${bottom}px`}}>
        <Reveal rise={18} blur={10}>
          <FrostedGlass padX={0} padY={0} radius={Math.min(cur.laid.look.radius, h / 2)} style={{width: w, height: h}}>
            <div style={{position: 'relative', width: w, height: h}}>
              {prev && out < 1 ? <PhraseText laid={prev.laid} opacity={1 - out} y={-8 * out} blur={6 * out} fps={fps} runFrom={run.from} /> : null}
              <PhraseText laid={cur.laid} opacity={prev ? interpolate(frame, [cur.from + 2, cur.from + s + 1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.inOut}) : 1} y={prev ? 10 * (1 - t) : 0} blur={prev ? 7 * Math.pow(1 - t, 1.5) : 0} fps={fps} runFrom={run.from} />
            </div>
          </FrostedGlass>
        </Reveal>
        </AbsoluteFill>
      </MotionBlurWhileMoving>
    </EnvelopeProvider>
  );
};

export const Subtitles: React.FC<SubtitlesProps> = ({transcript, emphasis = DEFAULT_EMPHASIS, anchor = 'center', faceBox, avoid = [], holdAfterLastWord = 0.5, strict = true, suppress = [], joinGapFrames = 8, look}) => {
  const L: CaptionLook = {...DDN_CAPTION_LOOK, ...look};
  const {fps} = useVideoConfig();
  const ready = useFontsReady();
  const side = FRAME.w * SAFE.margin;
  const maxText = FRAME.w - 2 * side - 2 * L.padX;

  const runs = useMemo<Run[]>(() => {
    if (!ready) return [];
    const ws = phraseWindows(transcript, fps, holdAfterLastWord);
    ws.forEach((p) => onScreen(p.words.map((x) => x.text.trim()).join(' '), 'subtitle phrase', strict));
    // Clip phrase windows by the suppress ranges.
    const clipped: {from: number; to: number; words: Word[]}[] = [];
    for (const w of ws) {
      let segs = [{from: w.from, to: w.to}];
      for (const r of suppress) segs = segs.flatMap((s) => (r.to <= s.from || r.from >= s.to ? [s] : [{from: s.from, to: r.from}, {from: r.to, to: s.to}]).filter((x) => x.to - x.from >= 20)); // a sliver shorter than enter + exit would have to cut: drop it
      segs.forEach((s) => clipped.push({...s, words: w.words}));
    }
    const out: Run[] = [];
    for (const c of clipped) {
      const laid = layoutPhrase(c.words, emphasis, maxText, L);
      const last = out[out.length - 1];
      if (last && c.from - last.to <= joinGapFrames) {
        last.phrases[last.phrases.length - 1].to = c.from;
        last.phrases.push({from: c.from, to: c.to, laid});
        last.to = c.to;
      } else out.push({from: c.from, to: c.to, phrases: [{from: c.from, to: c.to, laid}]});
    }
    return out;
  }, [ready, transcript, fps, holdAfterLastWord, strict, suppress, emphasis, joinGapFrames, maxText, L.size, L.role, L.emphRole, L.padX, L.padY, L.maxLines]);

  // Centred by default (DDN 2026). If the face or an avoid box drops into the caption band, move to the far side.
  const plateH1 = lineH(L) + 2 * L.padY;
  const band: Box = {x: 0, y: FRAME.h - L.bottomPx - plateH1, w: FRAME.w, h: plateH1};
  let a = anchor;
  if (a === 'auto') {
    const hit = obstacles(faceBox, avoid).find((b) => overlaps(band, b));
    a = hit ? (hit.x + hit.w / 2 > FRAME.w / 2 ? 'left' : 'right') : 'center';
  }
  const justify = a === 'left' ? 'flex-start' : a === 'right' ? 'flex-end' : 'center';

  return (
    <>
      {runs.map((r, i) => (
        <Sequence key={i} from={r.from} durationInFrames={r.to - r.from} name={`Caption run ${i + 1}`} layout="none">
          <RunBody run={r} fps={fps} justify={justify} side={side} bottom={L.bottomPx} />
        </Sequence>
      ))}
    </>
  );
};
