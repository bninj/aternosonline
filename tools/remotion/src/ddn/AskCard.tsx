import React from 'react';
import {useCurrentFrame} from 'remotion';
import {display, FONT} from './fonts';
import {GlassPlate, Hairline, Rise} from './primitives';
import {onScreen} from './sanitize';
import {Slot, SlotProps} from './Slot';
import {C, T, TYPE} from './tokens';

// Two item ask card. Each item rises from under a hairline [4.5] when it is said (at = frame in slot).
export type AskCardProps = SlotProps & {items: {text: string; at: number}[]};

const Inner: React.FC<{items: AskCardProps['items']}> = ({items}) => {
  useCurrentFrame();
  items.forEach((i) => onScreen(i.text, 'AskCard'));
  return (
    <GlassPlate padX={48} padY={36}>
      {items.map((it, i) => {
        const at = Math.max(T.firstOffset, it.at);
        return (
          <div key={i} style={{marginTop: i ? 22 : 0}}>
            <Hairline width="100%" startFrame={at - 2} />
            <Rise startFrame={at} style={{marginTop: 16}}>
              <div style={{...display('regular', TYPE.headline, -0.01), lineHeight: 1.15, color: C.white, whiteSpace: 'nowrap'}}>{it.text}</div>
            </Rise>
          </div>
        );
      })}
    </GlassPlate>
  );
};

export const AskCard: React.FC<AskCardProps> = (p) => (
  <Slot {...p} name={p.name ?? 'AskCard'}>{() => <Inner items={p.items} />}</Slot>
);
