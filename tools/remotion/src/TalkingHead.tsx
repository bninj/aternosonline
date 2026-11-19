import React, {useEffect, useMemo, useState} from 'react';
import {AbsoluteFill, Sequence, staticFile, useCurrentFrame, useVideoConfig, spring, interpolate, useDelayRender} from 'remotion';
import {Video, Audio} from '@remotion/media';
import {createTikTokStyleCaptions, Caption} from '@remotion/captions';
import {fontFamily} from './fonts';

const ACCENT = '#E4002B';

const LowerThird: React.FC<{name: string; role: string}> = ({name, role}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const s = width / 1920;
  const p = spring({frame, fps, config: {damping: 200}});
  return (
    <div style={{position: 'absolute', left: 110 * s, bottom: 130 * s, fontFamily, transform: `translateX(${(1 - p) * -60 * s}px)`, opacity: p}}>
      <div style={{color: '#fff', fontSize: 46 * s, fontWeight: 700, borderLeft: `${6 * s}px solid ${ACCENT}`, paddingLeft: 18 * s}}>{name}</div>
      <div style={{color: '#fff', background: ACCENT, display: 'inline-block', fontSize: 22 * s, padding: `${4 * s}px ${10 * s}px`, marginTop: 8 * s,
        fontFamily: 'monospace', letterSpacing: 1 * s}}>{role}</div>
    </div>
  );
};

const CaptionPage: React.FC<{page: ReturnType<typeof createTikTokStyleCaptions>['pages'][number]}> = ({page}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const s = width / 1920;
  const tMs = page.startMs + (frame / fps) * 1000;
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 70 * s}}>
      <div style={{fontFamily, fontWeight: 700, fontSize: 52 * s, color: '#fff', textShadow: `0 ${2 * s}px ${12 * s}px rgba(0,0,0,.6)`, whiteSpace: 'pre'}}>
        {page.tokens.map((t) => (
          <span key={t.fromMs} style={{color: tMs >= t.fromMs && tMs < t.toMs ? ACCENT : '#fff'}}>{t.text}</span>
        ))}
      </div>
    </AbsoluteFill>
  );
};

export const TalkingHead: React.FC<{src: string; captionsSrc: string; name: string; role: string}> = ({src, captionsSrc, name, role}) => {
  const {fps} = useVideoConfig();
  const [captions, setCaptions] = useState<Caption[] | null>(null);
  const {delayRender, continueRender} = useDelayRender();
  const [handle] = useState(() => delayRender('captions'));
  useEffect(() => {
    fetch(staticFile(captionsSrc)).then((r) => r.json()).then((c) => {setCaptions(c); continueRender(handle);});
  }, [captionsSrc, continueRender, handle]);
  const pages = useMemo(() => captions ? createTikTokStyleCaptions({captions, combineTokensWithinMilliseconds: 1200}).pages : [], [captions]);
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <Video src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      <Sequence from={15} durationInFrames={90} premountFor={15}><LowerThird name={name} role={role} /></Sequence>
      <Sequence from={10} durationInFrames={30}><Audio src={staticFile('sfx/whoosh_short.wav')} volume={0.5} /></Sequence>
      {pages.map((p, i) => {
        const next = pages[i + 1]?.startMs ?? p.startMs + p.durationMs;
        const from = Math.round((p.startMs / 1000) * fps);
        const dur = Math.max(1, Math.round((Math.min(next, p.startMs + p.durationMs) / 1000) * fps) - from);
        return <Sequence key={i} from={from} durationInFrames={dur}><CaptionPage page={p} /></Sequence>;
      })}
    </AbsoluteFill>
  );
};
