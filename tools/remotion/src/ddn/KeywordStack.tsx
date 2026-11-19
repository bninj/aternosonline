import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {display, FONT} from './fonts';
import {FrostedGlass} from './primitives';
import {onScreen} from './sanitize';
import {Slot, SlotProps} from './Slot';
import {C, EASE, TYPE} from './tokens';
import {Logo, LOGOS, LogoId} from './logos';

// Spoken names ("Netflix", "YouTube", "Canal Plus", "Starz"). Each one is its own frosted chip that rises in when
// it is said. Per item (or for the whole stack) choose the official logo or the plain name: logos already visible on
// a screen in the footage can stay text, or the stack can move with anchor / offset / avoid.
// Logo chips are light frost so official colour artwork is used unmodified; text chips are the dark smoked glass.
export type KeywordItem = {text: string; at: number; logo?: LogoId; show?: 'logo' | 'text'};
export type KeywordStackProps = SlotProps & {items: KeywordItem[]; size?: number; show?: 'logo' | 'text'; logoHeight?: number; direction?: 'column' | 'row'};

const Chip: React.FC<{item: KeywordItem; size: number; mode: 'logo' | 'text'; logoHeight: number}> = ({item, size, mode, logoHeight}) => {
  const frame = useCurrentFrame();
  const c = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
  const p = interpolate(frame, [item.at, item.at + 14], [0, 1], {...c, easing: EASE.out});
  const o = interpolate(frame, [item.at, item.at + 10], [0, 1], {...c, easing: EASE.inOut});
  const b = 1 - interpolate(frame, [item.at, item.at + 14], [0, 1], {...c, easing: EASE.soft});
  const style: React.CSSProperties = {opacity: o, transform: `translateY(${((1 - p) * 18).toFixed(2)}px)`, filter: b > 0.01 ? `blur(${(8 * b).toFixed(2)}px)` : undefined};
  if (mode === 'logo' && item.logo) {
    const l = LOGOS[item.logo];
    const pad = Math.round(logoHeight * l.clear);
    return (
      <div style={style}>
        <FrostedGlass tone="light" padX={pad + 8} padY={pad} radius={20}>
          <Logo id={item.logo} height={logoHeight} />
        </FrostedGlass>
      </div>
    );
  }
  return (
    <div style={style}>
      <FrostedGlass padX={44} padY={24} radius={20}>
        <div style={{...display('medium', size, -0.015), lineHeight: 1.12, color: C.white, whiteSpace: 'nowrap'}}>{item.text}</div>
      </FrostedGlass>
    </div>
  );
};

const Inner: React.FC<{p: KeywordStackProps; side: string}> = ({p, side}) => {
  useCurrentFrame();
  p.items.forEach((i) => onScreen(i.text, 'KeywordStack'));
  const size = p.size ?? TYPE.word;
  const logoHeight = p.logoHeight ?? 64;
  return (
    <div style={{display: 'flex', flexDirection: p.direction ?? 'column', gap: 16, alignItems: side === 'right' ? 'flex-end' : 'flex-start'}}>
      {/* Every chip is laid out from frame 0 (invisible until its word), so earlier chips never jump. */}
      {p.items.map((it, n) => <Chip key={n} item={it} size={size} logoHeight={logoHeight} mode={it.show ?? p.show ?? (it.logo ? 'logo' : 'text')} />)}
    </div>
  );
};

export const KeywordStack: React.FC<KeywordStackProps> = (p) => (
  <Slot {...p} name={p.name ?? `Keywords ${p.items.map((i) => i.text).join(' ')}`}>{({side}) => <Inner p={p} side={side} />}</Slot>
);
