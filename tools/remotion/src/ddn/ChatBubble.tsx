import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {display, FONT} from './fonts';
import {GlassPlate, typedCount} from './primitives';
import {onScreen} from './sanitize';
import {Slot, SlotProps} from './Slot';
import {C, T} from './tokens';

// Chat bubble that types on (stepped, linear). Layout is reserved for the full string so nothing reflows.
// Red underscore cursor [2, 4.7] while typing, removed 12 f after the last character.
// breakAfterComma: layout only (the string is unchanged): first clause on line 1 when it fits.
export type ChatBubbleProps = SlotProps & {text: string; charsPerFrame?: number; size?: number; breakAfterComma?: boolean; typeStart?: number; typeEnd?: number /* frames in slot: type on with the spoken words */};

const Inner: React.FC<{text: string; cpf: number; size: number; tail: 'left' | 'right'; duration: number; brk: boolean; typeStart?: number; typeEnd?: number}> = ({text, cpf, size, tail, duration, brk, typeStart, typeEnd}) => {
  const frame = useCurrentFrame();
  onScreen(text, 'ChatBubble');
  const start = typeStart ?? T.firstOffset + 3;
  // Typing follows the spoken words when typeEnd is given; otherwise it never outlasts 60 % of the line.
  const rate = typeEnd !== undefined ? text.length / Math.max(1, typeEnd - start) : Math.max(cpf, text.length / Math.max(1, duration * 0.6 - start));
  const n = typedCount(frame, start, text.length, rate);
  const doneAt = start + Math.ceil(text.length / rate);
  // v2: characters fade up over 3 f each (no popping); the red cursor fades out after typing.
  const cursorO = interpolate(frame, [doneAt + 10, doneAt + 18], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const ci = brk ? text.indexOf(', ') : -1;
  const cut = ci > 0 ? ci + 1 : -1; // index of the space after the comma becomes a line break (layout only)
  const chars = [...text].map((ch, i) => (i === cut ? '\n' : ch));
  const r = 32;
  const radius = tail === 'left' ? `${r}px ${r}px ${r}px 6px` : `${r}px ${r}px 6px ${r}px`;
  return (
    <GlassPlate padX={44} padY={30} radius={radius} style={{maxWidth: 1000}}>
      <div style={{...display('regular', size, -0.005), lineHeight: 1.22, color: C.white, textWrap: 'pretty', whiteSpace: 'pre-line'}}>
        {chars.map((ch, i) => (
          <React.Fragment key={i}>
            <span style={{opacity: interpolate(frame, [start + i / rate, start + i / rate + 3], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>{ch}</span>
            {i === n - 1 && cursorO > 0 ? <span style={{display: 'inline-block', width: 0, position: 'relative'}}><span style={{position: 'absolute', left: 3, bottom: '0.12em', width: '0.5em', height: '0.09em', background: C.red, opacity: cursorO}} /></span> : null}
          </React.Fragment>
        ))}
      </div>
    </GlassPlate>
  );
};

export const ChatBubble: React.FC<ChatBubbleProps> = (p) => (
  <Slot {...p} name={p.name ?? 'ChatBubble'}>
    {({side, duration}) => <Inner text={p.text} cpf={p.charsPerFrame ?? 1.5} size={p.size ?? 62} tail={side === 'left' ? 'left' : 'right'} duration={duration} brk={p.breakAfterComma ?? true} typeStart={p.typeStart} typeEnd={p.typeEnd} />}
  </Slot>
);
