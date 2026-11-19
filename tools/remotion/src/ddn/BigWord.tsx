import React from 'react';
import {display, FONT} from './fonts';
import {FrostedGlass, Hairline, Rise} from './primitives';
import {onScreen} from './sanitize';
import {Slot, SlotProps} from './Slot';
import {C, T, TYPE} from './tokens';
import {Logo, LOGOS, LogoId} from './logos';

// One big payoff word for the last line ("Blockbuster"): hairline, then the word rises from under it [4.5].
// With logo + show="logo" the official artwork rises instead (light frost, unmodified colours); text is the fallback.
export type BigWordProps = SlotProps & {text: string; size?: number; at?: number; logo?: LogoId; show?: 'logo' | 'text'; logoHeight?: number};

export const BigWord: React.FC<BigWordProps> = (p) => {
  onScreen(p.text, 'BigWord');
  const at = Math.max(T.firstOffset + 2, p.at ?? T.firstOffset + 2);
  const mode = p.show ?? (p.logo ? 'logo' : 'text');
  return (
    <Slot {...p} name={p.name ?? `BigWord ${p.text}`}>
      {() =>
        mode === 'logo' && p.logo ? (
          <FrostedGlass tone="light" padX={Math.round((p.logoHeight ?? 150) * LOGOS[p.logo].clear) + 16} padY={Math.round((p.logoHeight ?? 150) * LOGOS[p.logo].clear)} radius={26}>
            <Rise startFrame={at} frames={14}>
              <Logo id={p.logo} height={p.logoHeight ?? 150} />
            </Rise>
          </FrostedGlass>
        ) : (
          <FrostedGlass padX={56} padY={34}>
            <Hairline width="100%" startFrame={at - 2} />
            <Rise startFrame={at} style={{marginTop: 10}}>
              <div style={{...display('medium', p.size ?? TYPE.big, -0.025), lineHeight: 1.08, color: C.white, whiteSpace: 'nowrap'}}>{p.text}</div>
            </Rise>
          </FrostedGlass>
        )
      }
    </Slot>
  );
};
