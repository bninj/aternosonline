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
export type MeasureCardProps = SlotProps & {
  items: MeasureItem[];
  tag?: string; // mono header, e.g. "30 day pilot"
  tagAt?: number; // frame in slot the tag types on
  itemsAt?: number; // frame in slot the card grows to show the items (before that it is a tag-only pill)
  width?: number; // content width px (default 640)
  labelSize?: number; // metric label px (default 56)
  barLabelSize?: number; // "before" / "after" mono px (default 26: readable on a laptop)
  pad?: number;
  gap?: number;
};

const Bar: React.FC<{label: string; value: number; color: string; textAlpha: number; grow: number; size: number}> = ({label, value, color, textAlpha, grow, size}) => (
  <div style={{display: 'flex', alignItems: 'center', gap: 14, height: Math.round(size * 1.15)}}>
    <div style={{width: Math.round(size * 0.6 * 6.4), fontFamily: FONT.mono, fontSize: size, color: `rgba(255,255,255,${textAlpha})`}}>{label}</div>
    <div style={{flex: 1, position: 'relative', height: 10, borderRadius: 5, background: 'rgba(255,255,255,0.13)', overflow: 'hidden'}}>
      <div style={{position: 'absolute', left: 0, top: 0, bottom: 0, width: `${(value * grow * 100).toFixed(3)}%`, borderRadius: 5, background: color}} />
    </div>
  </div>
);

const Inner: React.FC<{p: MeasureCardProps}> = ({p}) => {
  const frame = useCurrentFrame();
  p.items.forEach((i) => onScreen(i.label, 'MeasureCard'));
  if (p.tag) onScreen(p.tag, 'MeasureCard tag');
  const c = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
  const labelSize = p.labelSize ?? 56;
  const barSize = p.barLabelSize ?? 26;
  const labelH = Math.round(labelSize * 0.966 * 1.15);
  const itemH = 1 + 8 + labelH + 8 + 2 * Math.round(barSize * 1.15);
  const gap = p.gap ?? 18;
  const fullH = p.items.length * itemH + (p.items.length - 1) * gap + (p.tag ? 14 : 0);
  // Tag-only pill first; the card grows (in-out, 18 f) when the metrics are said. Height is computed, not measured.
  const grow = p.itemsAt === undefined ? 1 : interpolate(frame, [p.itemsAt - 4, p.itemsAt + 14], [0, 1], {...c, easing: EASE.inOut});
  const w = p.width ?? 640;
  const wNow = p.tag && p.itemsAt !== undefined ? 300 + (w - 300) * grow : w;
  return (
    <FrostedGlass padX={p.pad ?? 30} padY={Math.round((p.pad ?? 30) * 0.8)}>
      <div style={{width: wNow}}>
        {p.tag ? <div style={{height: TYPE.tagBar}}><MonoTag text={p.tag} startFrame={p.tagAt ?? T.firstOffset + 4} /></div> : null}
        <div style={{height: fullH * grow, overflow: 'hidden', opacity: grow > 0 ? 1 : 0}}>
          <div style={{width: w, paddingTop: p.tag ? 14 : 0}}>
            {p.items.map((it, i) => {
              const at = Math.max(T.firstOffset, it.at);
              const b = interpolate(frame, [at + 6, at + 20], [0, 1], {...c, easing: EASE.out});
              const a = interpolate(frame, [at + 16, at + 16 + T.countFrames], [0, 1], {...c, easing: EASE.inOut});
              const afterVal = it.before + (it.after - it.before) * a; // the change itself is the message
              return (
                <div key={i} style={{marginTop: i ? gap : 0}}>
                  <Hairline width="100%" startFrame={at - 2} />
                  <Rise startFrame={at} style={{marginTop: 8}}>
                    <div style={{...display('medium', labelSize, -0.01), lineHeight: 1.15, color: C.white, whiteSpace: 'nowrap'}}>{it.label}</div>
                  </Rise>
                  <div style={{marginTop: 8, opacity: interpolate(frame, [at + 4, at + 14], [0, 1], {...c, easing: EASE.inOut})}}>
                    <Bar label="before" value={it.before} color="rgba(255,255,255,0.5)" textAlpha={0.72} grow={b} size={barSize} />
                    <Bar label="after" value={afterVal} color={C.red} textAlpha={1} grow={b} size={barSize} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </FrostedGlass>
  );
};

export const MeasureCard: React.FC<MeasureCardProps> = (p) => (
  <Slot {...p} name={p.name ?? 'MeasureCard'} exitFrames={p.exitFrames ?? 14}>{() => <Inner p={p} />}</Slot>
);
