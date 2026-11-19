import React, {createContext, useContext, useLayoutEffect, useRef, useState} from 'react';
import {AbsoluteFill, Freeze, Img, Internals, OffthreadVideo, staticFile, useVideoConfig} from 'remotion';

// Deterministic frosted glass, v2.
// CSS backdrop-filter dropped plates on ~1 % of frames in headless Chrome (critique log v1, round 3), so the frost
// is rendered by us: every glass plate draws a copy of the footage layer, aligned pixel for pixel with the main
// layer, inside its own rounded clip, then blurs it (CSS `filter`, which is deterministic) or uses an ffmpeg
// pre-blurred proxy of the same footage (faster, and identical every render).
//
// Usage: wrap the whole composition in <Footage source={...}>. The main layer is drawn by Footage itself, so the
// glass copies can never drift from it. Without a source (alpha overlay renders) plates fall back to a tinted fill.

export type FootageSource = {
  src: string; // staticFile() name or URL of the footage layer
  kind: 'image' | 'video';
  blurredSrc?: string; // optional pre-blurred proxy, same size and timing (scripts/make-blur-proxy.sh)
  blurredPx?: number; // blur already baked into blurredSrc (px @1080), for reference only
  style?: React.CSSProperties; // extra style shared by main layer and copies (e.g. a punch-in transform)
  trimBefore?: number; // frames of the source skipped at composition frame 0
  volume?: number; // main layer only
  freezeAt?: number; // main layer: hold this absolute frame (e.g. the last frame under an end card handoff)
};

type Ctx = {source: FootageSource | null; rootRef: React.RefObject<HTMLDivElement | null>};
const BackdropCtx = createContext<Ctx>({source: null, rootRef: {current: null}});
export const useFootage = () => useContext(BackdropCtx);

const resolve = (src: string) => (/^(https?:|data:|blob:|\/)/.test(src) ? src : staticFile(src));

const Layer: React.FC<{source: FootageSource; blurred: boolean; muted?: boolean; offset?: number}> = ({source, blurred, muted = true, offset = 0}) => {
  const src = resolve(blurred && source.blurredSrc ? source.blurredSrc : source.src);
  const style: React.CSSProperties = {position: 'absolute', inset: 0, width: '100%', height: '100%', ...source.style};
  // <OffthreadVideo>: frames are extracted by Remotion's ffmpeg compositor, exact and memory-safe. (@remotion/media
  // <Video> showed wrong frames on one tab under memory pressure; see critique log v2, round 3.)
  if (source.kind === 'video') {
    const trim = (source.trimBefore ?? 0) + offset;
    return <OffthreadVideo src={src} style={{...style, objectFit: 'cover'}} muted={muted} volume={muted ? 0 : source.volume ?? 1} trimBefore={trim > 0 ? trim : undefined} pauseWhenBuffering={false} />;
  }
  return <Img src={src} style={{...style, objectFit: 'cover'}} />;
};

export const Footage: React.FC<{source: FootageSource | null; background?: string; children: React.ReactNode}> = ({source, background = '#1E1E22', children}) => {
  const rootRef = useRef<HTMLDivElement>(null);
  return (
    <AbsoluteFill ref={rootRef} data-ddn-footage-root="" style={{backgroundColor: source ? background : 'transparent'}}>
      {source ? (source.freezeAt !== undefined ? <Freeze frame={source.freezeAt}><Layer source={source} blurred={false} muted /></Freeze> : <Layer source={source} blurred={false} muted={source.volume === undefined ? true : false} />) : null}
      <BackdropCtx.Provider value={{source, rootRef}}>{children}</BackdropCtx.Provider>
    </AbsoluteFill>
  );
};

// The frost itself: fills its (rounded, overflow hidden) parent with the aligned, blurred, smoked footage.
// Alignment is measured after layout on every frame (getBoundingClientRect relative to the Footage root, so it
// includes every transform on the way: rises, Studio preview scale, scale animations). React applies the
// measured offset synchronously in the same commit (useLayoutEffect), before Chrome paints the frame.
export const Frost: React.FC<{blurPx: number; filter: string; radius: number | string}> = ({blurPx, filter, radius}) => {
  const {source, rootRef} = useFootage();
  const {width, height} = useVideoConfig();
  const ref = useRef<HTMLDivElement>(null);
  const [m, setM] = useState<{x: number; y: number; s: number} | null>(null);
  const seq = useContext(Internals.SequenceContext);
  const absOffset = seq ? seq.cumulatedFrom + seq.relativeFrom : 0;

  useLayoutEffect(() => {
    const el = ref.current;
    // Refs of parents attach after children's layout effects on mount, so find the root through the DOM.
    const root = rootRef.current ?? (el ? (el.closest('[data-ddn-footage-root]') as HTMLDivElement | null) : null);
    if (!el || !root) return;
    const r = el.getBoundingClientRect();
    const R = root.getBoundingClientRect();
    const k = R.width / width || 1; // Studio preview scale
    const s = el.offsetWidth > 0 ? r.width / (el.offsetWidth * k) : 1; // our own scale animations
    const next = {x: (r.left - R.left) / k, y: (r.top - R.top) / k, s: s || 1};
    
    if (!m || Math.abs(next.x - m.x) > 0.01 || Math.abs(next.y - m.y) > 0.01 || Math.abs(next.s - m.s) > 0.0005) setM(next);
  });

  if (!source) return null;
  const css = source.blurredSrc ? filter : `blur(${blurPx}px) ${filter}`;
  return (
    <div ref={ref} style={{position: 'absolute', inset: 0, overflow: 'hidden', borderRadius: radius}}>
      {m ? (
        <div style={{position: 'absolute', left: 0, top: 0, width, height, transformOrigin: '0 0', transform: `scale(${1 / m.s}) translate(${-m.x}px, ${-m.y}px)`, filter: css}}>
          {/* Re-anchor to composition frame 0 so a video copy shows the same frame as the main layer. */}
          <Layer source={source} blurred offset={absOffset} />
        </div>
      ) : null}
    </div>
  );
};
