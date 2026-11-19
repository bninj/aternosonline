// v6 components (final film): clean subtitles, stopwatch, name super, Arsenal gag, "scale it" kinetic line,
// logo plates. Layout is in 1920x1080 px; the whole film is scaled to 3840x2160 by PitchV6 (vector-sharp).
import React, {useMemo} from 'react';
import {AbsoluteFill, interpolate, Sequence, useCurrentFrame, useVideoConfig} from 'remotion';
import {measureText} from '@remotion/layout-utils';
import {C, display, EASE, FONT, FrostedGlass, Logo, LogoId, LOGOS, onScreen, Slot, SlotProps, Transcript, useFontsReady} from '../ddn';
import {phraseWindows} from '../ddn/Subtitles';

const cl = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// ---------------------------------------------------------------------------------------------------------------
// Subtitles v6: no box. White Inter Tight semibold, bottom centre at a fixed position (baseline band at about 87 % H),
// a soft shadow plus a very faint feathered dark "layer" (a blurred ellipse sized to the line) for legibility.
// Emphasis: a slightly heavier weight plus a thin Brand Red underline (red text was illegible over the dark room; no blocks). Phrase to phrase: a 4 f crossfade; runs fade 6 f in/out.
export const CleanSubtitles: React.FC<{transcript: Transcript; snapTo?: number[]; suppress?: {from: number; to: number}[]; size?: number; centerY?: number}> = ({transcript, snapTo = [], suppress = [], size = 64, centerY = 940}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const ready = useFontsReady();
  const ws = useMemo(() => {
    const w = phraseWindows(transcript, fps, 0.45);
    w.forEach((p) => onScreen(p.words.map((x) => x.text).join(' '), 'subtitle'));
    w.forEach((wnd, k) => {
      const c = snapTo.find((cf) => cf > wnd.from && cf - wnd.from <= 8);
      if (c !== undefined) {
        wnd.from = c;
        if (k > 0 && w[k - 1].to >= wnd.from - 8) w[k - 1].to = c;
      }
    });
    return w.map((p) => {
      let {from, to} = p;
      for (const r of suppress) {
        if (r.from <= from && r.to >= to) return null;
        if (r.from > from && r.from < to) to = r.from;
        else if (r.to > from && r.to < to && r.from <= from) from = r.to;
      }
      return to - from >= 6 ? {...p, from, to} : null;
    }).filter((x): x is NonNullable<typeof x> => x !== null);
  }, [transcript, fps, snapTo, suppress]);
  if (!ready) return null;
  const lab = display('bold', size, -0.005);
  const els: React.ReactNode[] = [];
  ws.forEach((p, k) => {
    const prev = ws[k - 1];
    const next = ws[k + 1];
    const joinedIn = prev && p.from - prev.to <= 2;
    const joinedOut = next && next.from - p.to <= 2;
    const inF = joinedIn ? 4 : 6;
    const outF = joinedOut ? 4 : 6;
    if (frame < p.from - (joinedIn ? 0 : 0) || frame >= p.to + (joinedOut ? 4 : 0)) return;
    const oIn = interpolate(frame, [p.from, p.from + inF], [0, 1], {...cl, easing: EASE.inOut});
    const oOut = joinedOut ? interpolate(frame, [p.to, p.to + outF], [1, 0], {...cl, easing: EASE.inOut}) : interpolate(frame, [p.to - outF, p.to], [1, 0], {...cl, easing: EASE.inOut});
    const o = Math.min(oIn, oOut);
    if (o <= 0.001) return;
    const text = p.words.map((x) => x.text).join(' ');
    const tw = measureText({text, fontFamily: FONT.displayFamilyLoaded, fontSize: lab.fontSize, fontWeight: String(lab.fontWeight), letterSpacing: lab.letterSpacing}).width;
    const y = joinedIn ? 0 : 6 * (1 - oIn);
    els.push(
      <div key={k} style={{position: 'absolute', left: 0, right: 0, top: centerY - size * 0.62, height: size * 1.25, display: 'flex', justifyContent: 'center', opacity: o, transform: `translateY(${y.toFixed(2)}px)`}}>
        {/* the "layer": a very faint feathered dark ellipse behind the line */}
        <div style={{position: 'absolute', left: '50%', top: '50%', width: tw + 260, height: size * 2.3, transform: 'translate(-50%, -50%)',
          background: 'radial-gradient(closest-side, rgba(12,8,10,0.42), rgba(12,8,10,0.22) 55%, rgba(12,8,10,0) 100%)', filter: 'blur(6px)'}} />
        <div style={{position: 'relative', ...lab, lineHeight: `${size * 1.25}px`, color: '#FFFFFF', whiteSpace: 'nowrap', fontFeatureSettings: '"kern" 1, "tnum" 1',
          textShadow: '0 2px 3px rgba(0,0,0,0.45), 0 2px 14px rgba(0,0,0,0.5)'}}>
          {p.words.map((w, i) => {
            const m = w.text.match(/^(.*?)([.,!?;:]*)$/);
            const core = m ? m[1] : w.text;
            const tail = m ? m[2] : '';
            const emph = w.emphasis ?? /\d/.test(core);
            return (
              <React.Fragment key={i}>
                {i > 0 ? ' ' : ''}
                {emph ? <span style={{fontWeight: 780, backgroundImage: `linear-gradient(${C.red}, ${C.red})`, backgroundSize: '100% 4px', backgroundPosition: '0 92%', backgroundRepeat: 'no-repeat', paddingBottom: 2}}>{core}</span> : core}
                {tail}
              </React.Fragment>
            );
          })}
        </div>
      </div>,
    );
  });
  return <AbsoluteFill style={{pointerEvents: 'none'}}>{els}</AbsoluteFill>;
};

// ---------------------------------------------------------------------------------------------------------------
// Stopwatch: a realistic dial (60 ticks, crown, red sweep hand) and a Geist Mono readout counting real seconds from
// 0 when he starts. No total shown.
export const Stopwatch: React.FC<SlotProps & {clockZero: number}> = (p) => (
  <Slot {...p} name="Stopwatch">{() => <StopwatchInner from={p.from} clockZero={p.clockZero} />}</Slot>
);
const StopwatchInner: React.FC<{from: number; clockZero: number}> = ({from, clockZero}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = Math.max(0, (from + frame - clockZero) / fps);
  const D = 118;
  const R = D / 2;
  const ang = (t / 60) * 360; // one revolution per minute, smooth sweep
  const started = from + frame >= clockZero;
  const s = Math.floor(t);
  const mm = String(Math.floor(s / 60)).padStart(2, '0');
  const ss = String(s % 60).padStart(2, '0');
  const tenth = Math.floor((t * 10) % 10);
  return (
    <FrostedGlass padX={26} padY={20} radius={999}>
      <div style={{display: 'flex', alignItems: 'center', gap: 22}}>
        <svg width={D} height={D + 12} viewBox={`0 -12 ${D} ${D + 12}`} style={{display: 'block', overflow: 'visible'}}>
          <rect x={R - 7} y={-12} width={14} height={9} rx={2} fill="rgba(255,255,255,0.85)" />
          <rect x={R - 3} y={-5} width={6} height={6} fill="rgba(255,255,255,0.7)" />
          <circle cx={R} cy={R} r={R - 1} fill="rgba(20,14,16,0.35)" stroke="rgba(255,255,255,0.85)" strokeWidth={2.5} />
          {Array.from({length: 60}, (_, i) => {
            const a = (i / 60) * Math.PI * 2;
            const long = i % 5 === 0;
            const r1 = R - 6;
            const r2 = r1 - (long ? 9 : 4);
            return <line key={i} x1={R + Math.sin(a) * r1} y1={R - Math.cos(a) * r1} x2={R + Math.sin(a) * r2} y2={R - Math.cos(a) * r2} stroke={long ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.45)'} strokeWidth={long ? 2 : 1} />;
          })}
          {/* elapsed arc */}
          {t > 0 ? <path d={describeArc(R, R, R - 16, 0, Math.min(359.9, ang))} fill="none" stroke={C.red} strokeOpacity={0.35} strokeWidth={6} strokeLinecap="round" /> : null}
          <g transform={`rotate(${ang} ${R} ${R})`}>
            <line x1={R} y1={R + 12} x2={R} y2={12} stroke={C.red} strokeWidth={2.4} strokeLinecap="round" />
          </g>
          <circle cx={R} cy={R} r={5} fill={C.red} />
          <circle cx={R} cy={R} r={2} fill="#FFFFFF" />
        </svg>
        <div style={{fontFamily: FONT.mono, color: C.white, fontSize: 56, lineHeight: 1, fontFeatureSettings: '"tnum" 1', opacity: started ? 1 : 0.6}}>
          {mm}:{ss}<span style={{fontSize: 34, opacity: 0.6}}>.{tenth}</span>
        </div>
      </div>
    </FrostedGlass>
  );
};
const describeArc = (cx: number, cy: number, r: number, a0: number, a1: number) => {
  const p = (a: number) => [cx + r * Math.sin((a * Math.PI) / 180), cy - r * Math.cos((a * Math.PI) / 180)];
  const [x0, y0] = p(a0);
  const [x1, y1] = p(a1);
  return `M ${x0} ${y0} A ${r} ${r} 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${x1} ${y1}`;
};

// ---------------------------------------------------------------------------------------------------------------
// Name super, top left: thin Brand Red accent line draws down, the name and role slide out from behind it (masked),
// hold, then retract the same way. Over the footage with a soft shadow; no box.
export const NameSuper: React.FC<{from: number; durationInFrames: number; name: string; role: string; x?: number; y?: number}> = ({from, durationInFrames, name, role, x = 154, y = 70}) => (
  <Sequence from={from} durationInFrames={durationInFrames} name="NameSuper" layout="none">
    <NameSuperInner dur={durationInFrames} name={name} role={role} x={x} y={y} />
  </Sequence>
);
const NameSuperInner: React.FC<{dur: number; name: string; role: string; x: number; y: number}> = ({dur, name, role, x, y}) => {
  const frame = useCurrentFrame();
  onScreen(name, 'NameSuper');
  onScreen(role, 'NameSuper');
  const line = interpolate(frame, [0, 12], [0, 1], {...cl, easing: EASE.out}) * interpolate(frame, [dur - 10, dur], [1, 0], {...cl, easing: EASE.exit});
  const tIn = interpolate(frame, [6, 22], [0, 1], {...cl, easing: EASE.out});
  const rIn = interpolate(frame, [11, 27], [0, 1], {...cl, easing: EASE.out});
  const tOut = interpolate(frame, [dur - 14, dur - 4], [0, 1], {...cl, easing: EASE.exit});
  const H = 108;
  const nameS = display('bold', 58, -0.01);
  return (
    <div style={{position: 'absolute', left: x, top: y, display: 'flex', alignItems: 'stretch', gap: 18, filter: 'drop-shadow(0 2px 10px rgba(0,0,0,0.45))'}}>
      <div style={{width: 4, height: H, borderRadius: 2, background: C.red, transformOrigin: 'top', transform: `scaleY(${line})`}} />
      <div style={{overflow: 'hidden', height: H, display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
        <div style={{...nameS, lineHeight: 1.1, color: '#FFFFFF', whiteSpace: 'nowrap', transform: `translateX(${((1 - tIn) * -40 - tOut * 30).toFixed(2)}px)`, opacity: tIn * (1 - tOut),
          filter: tIn < 1 ? `blur(${(4 * (1 - tIn)).toFixed(2)}px)` : undefined}}>{name}</div>
        <div style={{fontFamily: FONT.mono, fontSize: 25, letterSpacing: '0.02em', color: 'rgba(255,255,255,0.88)', whiteSpace: 'nowrap', marginTop: 6,
          transform: `translateX(${((1 - rIn) * -40 - tOut * 30).toFixed(2)}px)`, opacity: rIn * (1 - tOut)}}>{role}</div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------------------------------------------
// Arsenal "losing": the official crest arrives (light frost plate), holds, then droops (tilts and sinks), desaturates,
// and a small red down arrow (drawn shape) slides down beside it. No score, no invented fact.
export const ArsenalGag: React.FC<SlotProps & {loseAt: number; crestH?: number}> = (p) => (
  <Slot {...p} name="ArsenalGag">{({side}) => <ArsenalInner loseAt={p.loseAt} H={p.crestH ?? 190} reverse={side === 'left'} />}</Slot>
);
const ArsenalInner: React.FC<{loseAt: number; H: number; reverse: boolean}> = ({loseAt, H, reverse}) => {
  const frame = useCurrentFrame();
  const l = interpolate(frame, [loseAt, loseAt + 18], [0, 1], {...cl, easing: EASE.inOut});
  const arrow = interpolate(frame, [loseAt + 4, loseAt + 18], [0, 1], {...cl, easing: EASE.out});
  return (
    <div style={{display: 'flex', flexDirection: reverse ? 'row-reverse' : 'row', alignItems: 'center', gap: 22}}>
      <FrostedGlass tone="light" tint="rgba(250,247,245,0.62)" padX={28} padY={22} radius={22}>
        <div style={{transform: `translateY(${(l * 14).toFixed(2)}px) rotate(${(l * -9).toFixed(2)}deg)`, transformOrigin: '70% 90%',
          filter: `grayscale(${(l * 0.85).toFixed(3)}) brightness(${(1 - 0.12 * l).toFixed(3)})`}}>
          <Logo id="arsenal" height={H} />
        </div>
      </FrostedGlass>
      <svg width={H * 0.3} height={H * 0.55} viewBox="0 0 60 110" style={{opacity: arrow, transform: `translateY(${((1 - arrow) * -24 + arrow * 6).toFixed(2)}px)`, filter: 'drop-shadow(0 2px 8px rgba(0,0,0,0.45))'}}>
        <rect x={22} y={4} width={16} height={60} rx={4} fill={C.red} />
        <path d="M6 58 L30 104 L54 58 Z" fill={C.red} />
      </svg>
    </div>
  );
};

// ---------------------------------------------------------------------------------------------------------------
// "If both improve, scale it": its own kinetic moment. Line 1 builds word by word on his words; a red arrow draws;
// "scale it" lands large with a Brand Red underline that draws in. Over the footage with a soft layer; holds to the
// end of the shot and leaves over the last 5 f.
export const ScaleIt: React.FC<{from: number; durationInFrames: number; words: {text: string; at: number}[]; landAt: number; x: number; y: number}> = (p) => (
  <Sequence from={p.from} durationInFrames={p.durationInFrames} name="ScaleIt" layout="none">
    <ScaleItInner {...p} />
  </Sequence>
);
const ScaleItInner: React.FC<{durationInFrames: number; words: {text: string; at: number}[]; landAt: number; x: number; y: number}> = ({durationInFrames, words, landAt, x, y}) => {
  const frame = useCurrentFrame();
  words.forEach((w) => onScreen(w.text, 'ScaleIt'));
  const out = interpolate(frame, [durationInFrames - 6, durationInFrames], [0, 1], {...cl, easing: EASE.exit});
  const arrow = interpolate(frame, [landAt - 10, landAt + 2], [0, 1], {...cl, easing: EASE.inOut});
  const land = interpolate(frame, [landAt, landAt + 12], [0, 1], {...cl, easing: EASE.out});
  const under = interpolate(frame, [landAt + 6, landAt + 20], [0, 1], {...cl, easing: EASE.inOut});
  const l1 = display('medium', 62, -0.01);
  const l2 = display('bold', 104, -0.02);
  return (
    <div style={{position: 'absolute', left: x, top: y, opacity: 1 - out, filter: out > 0 ? `blur(${(6 * out).toFixed(2)}px)` : undefined}}>
      <div style={{position: 'absolute', left: -120, top: -70, right: -120, bottom: -70, background: 'radial-gradient(closest-side, rgba(12,8,10,0.62), rgba(12,8,10,0.4) 55%, rgba(12,8,10,0) 100%)', filter: 'blur(10px)'}} /> {/* stronger layer: the line sits over the white whiteboard */}
      <div style={{position: 'relative', textShadow: '0 2px 4px rgba(0,0,0,0.55), 0 2px 18px rgba(0,0,0,0.6), 0 0 40px rgba(0,0,0,0.35)'}}>
        <div style={{...l1, color: '#FFFFFF', whiteSpace: 'nowrap', lineHeight: 1.15}}>
          {words.map((w, i) => {
            const a = interpolate(frame, [w.at, w.at + 8], [0, 1], {...cl, easing: EASE.out});
            return (
              <span key={i} style={{display: 'inline-block', opacity: a, transform: `translateY(${((1 - a) * 14).toFixed(2)}px)`, filter: a < 1 ? `blur(${(4 * (1 - a)).toFixed(2)}px)` : undefined, marginRight: '0.26em'}}>{w.text}</span>
            );
          })}
        </div>
        <div style={{display: 'flex', alignItems: 'center', gap: 22, marginTop: 6}}>
          <svg width={110} height={60} viewBox="0 0 110 60" style={{overflow: 'visible', filter: 'drop-shadow(0 2px 8px rgba(0,0,0,0.4))'}}>
            <line x1={4} y1={30} x2={4 + 92 * arrow} y2={30} stroke={C.red} strokeWidth={6} strokeLinecap="round" />
            <path d="M80 12 L102 30 L80 48" fill="none" stroke={C.red} strokeWidth={6} strokeLinecap="round" strokeLinejoin="round" opacity={arrow > 0.85 ? (arrow - 0.85) / 0.15 : 0} />
          </svg>
          <div style={{position: 'relative', opacity: land, transform: `scale(${(0.94 + 0.06 * land).toFixed(4)})`, transformOrigin: 'left center', filter: land < 1 ? `blur(${(6 * (1 - land)).toFixed(2)}px)` : undefined}}>
            <div style={{...l2, color: '#FFFFFF', lineHeight: 1.05, whiteSpace: 'nowrap'}}>scale it</div>
            <div style={{position: 'absolute', left: 2, right: 2, bottom: -10, height: 8, borderRadius: 4, background: C.red, transformOrigin: 'left center', transform: `scaleX(${under})`}} />
          </div>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------------------------------------------
// A single official logo on a light frosted plate (Canal+, Starz: large, beside him, not behind).
export const LogoPlate: React.FC<SlotProps & {logo: LogoId; logoH: number}> = (p) => (
  <Slot {...p} name={`LogoPlate ${p.logo}`}>
    {() => (
      <FrostedGlass tone="light" tint="rgba(250,247,245,0.72)" padX={Math.round(p.logoH * 0.45)} padY={Math.round(p.logoH * 0.38)} radius={22}>
        <Logo id={p.logo} height={p.logoH} />
      </FrostedGlass>
    )}
  </Slot>
);
export {LOGOS};
