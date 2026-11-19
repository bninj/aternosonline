import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {display, FONT} from './fonts';
import {FrostedGlass, Hairline, MonoTag, Rise} from './primitives';
import {onScreen} from './sanitize';
import {Slot, SlotProps} from './Slot';
import {C, EASE, T, TYPE} from './tokens';

// The ask: "measure two values, before and after". Each metric gets a before bar (quiet) and an after bar (Brand Red)
// that grows or shrinks to its target, so the direction of "better" reads without inventing numbers (bars are
// illustrative, no figures, so no source tag is needed). Optional mono tag, e.g. "30 day pilot" (no DDN logo: the pilot
// is the speaker's proposal). Built to HOLD: give it a long slot (through the next line); it exits smoothly at the end.
export type MeasureItem = {label: string; at: number; before: number; after: number}; // before/after: 0..1 bar length
export type MeasureCardProps = SlotProps & {items: MeasureItem[]; tag?: string; tagAt?: number; width?: number};

const Bar: React.FC<{label: string; value: number; color: string; textAlpha: number; grow: number}> = ({label, value, color, textAlpha, grow}) => (
  <div style={{display: 'flex', alignItems: 'center', gap: 16, height: 34}}>
    <div style={{width: 92, fontFamily: FONT.mono, fontSize: 24, color: `rgba(255,255,255,${textAlpha})`}}>{label}</div>
    <div style={{flex: 1, position: 'relative', height: 10, borderRadius: 5, background: 'rgba(255,255,255,0.12)', overflow: 'hidden'}}>
      <div style={{position: 'absolute', left: 0, top: 0, bottom: 0, width: `${(value * grow * 100).toFixed(3)}%`, borderRadius: 4, background: color}} />
    </div>
  </div>
);

const Inner: React.FC<{p: MeasureCardProps}> = ({p}) => {
  const frame = useCurrentFrame();
  p.items.forEach((i) => onScreen(i.label, 'MeasureCard'));
  if (p.tag) onScreen(p.tag, 'MeasureCard tag');
  const c = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
  return (
    <FrostedGlass padX={48} padY={40}>
      <div style={{width: p.width ?? 640}}>
        {p.tag ? <div style={{height: TYPE.tagBar, marginBottom: 26}}><MonoTag text={p.tag} startFrame={p.tagAt ?? T.firstOffset + 4} /></div> : null}
        {p.items.map((it, i) => {
          const at = Math.max(T.firstOffset, it.at);
          const b = interpolate(frame, [at + 6, at + 20], [0, 1], {...c, easing: EASE.out});
          const a = interpolate(frame, [at + 16, at + 16 + T.countFrames], [0, 1], {...c, easing: EASE.inOut});
          // after bar morphs from the before value to its own value: the change itself is the message
          const afterVal = it.before + (it.after - it.before) * a;
          return (
            <div key={i} style={{marginTop: i ? 30 : 0}}>
              <Hairline width="100%" startFrame={at - 2} />
              <Rise startFrame={at} style={{marginTop: 14}}>
                <div style={{...display('regular', TYPE.headline - 8, -0.01), lineHeight: 1.15, color: C.white, whiteSpace: 'nowrap'}}>{it.label}</div>
              </Rise>
              <div style={{marginTop: 14, opacity: interpolate(frame, [at + 4, at + 14], [0, 1], {...c, easing: EASE.inOut})}}>
                <Bar label="before" value={it.before} color="rgba(255,255,255,0.45)" textAlpha={0.6} grow={b} />
                <Bar label="after" value={afterVal} color={C.red} textAlpha={0.92} grow={b} />
              </div>
            </div>
          );
        })}
      </div>
    </FrostedGlass>
  );
};

export const MeasureCard: React.FC<MeasureCardProps> = (p) => (
  <Slot {...p} name={p.name ?? 'MeasureCard'} exitFrames={p.exitFrames ?? 14}>{() => <Inner p={p} />}</Slot>
);
