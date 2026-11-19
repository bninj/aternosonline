import React from 'react';
import {AbsoluteFill, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Easing} from 'remotion';
import {Video} from '@remotion/media';
import {fontFamily} from './fonts';

// DDN-ish palette: deep black/navy, signal red accent, white type
const ACCENT = '#E4002B';
export const SmokeTest: React.FC<{title: string; subtitle: string; withVideo?: boolean; src?: string}> = ({title, subtitle, withVideo = true, src = 'test.mp4'}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const s = width / 1920; // scale everything for 4K
  const barIn = spring({frame, fps, config: {damping: 200}});
  const textIn = spring({frame: frame - 8, fps, config: {damping: 200}});
  const out = interpolate(frame, [75, 90], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.cubic)});
  const words = title.split(' ');
  return (
    <AbsoluteFill style={{backgroundColor: withVideo ? '#000' : 'transparent'}}>
      {withVideo && <Video src={staticFile(src)} muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />}
      {/* vignette/gradient overlay */}
      <AbsoluteFill style={{background: 'linear-gradient(90deg, rgba(5,8,20,0.85) 0%, rgba(5,8,20,0.2) 60%, transparent 100%)', opacity: barIn * out}} />
      {/* lower third */}
      <div style={{position: 'absolute', left: 120 * s, bottom: 160 * s, opacity: out, fontFamily}}>
        <div style={{height: 6 * s, width: 140 * s * barIn, background: ACCENT, marginBottom: 24 * s}} />
        <div style={{display: 'flex', gap: 18 * s, overflow: 'hidden'}}>
          {words.map((w, i) => {
            const p = spring({frame: frame - 8 - i * 3, fps, config: {damping: 200}});
            return <span key={i} style={{color: '#fff', fontSize: 84 * s, fontWeight: 700, letterSpacing: -1.5 * s,
              transform: `translateY(${(1 - p) * 100}%)`, opacity: p}}>{w}</span>;
          })}
        </div>
        <div style={{color: 'rgba(255,255,255,0.75)', fontSize: 36 * s, marginTop: 12 * s, opacity: textIn,
          transform: `translateX(${(1 - textIn) * -40 * s}px)`}}>{subtitle}</div>
      </div>
    </AbsoluteFill>
  );
};
