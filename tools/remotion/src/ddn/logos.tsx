import React from 'react';
import {Img, staticFile} from 'remotion';

// Official logo artwork only, unmodified (no recolour, no crop, no distortion: width always follows the file's own
// aspect ratio). Sources and trademark notes: brand/logos/SOURCES.md. Files are copied to public/logos/.
// tone: the background the artwork is drawn for. Colour logos go on the light frosted plate, white ones on dark.
// Sky: no official SVG is available on Wikimedia Commons (its 2020 mark is not public domain) and Sky's press kit is
// not reachable from here. Add it as 'sky' with Sky's own artwork when supplied; until then Sky stays text.
export type LogoId = 'ddn' | 'ddn-white' | 'netflix' | 'youtube' | 'blockbuster' | 'canalplus' | 'starz' | 'arsenal';

export const LOGOS: Record<LogoId, {file: string; aspect: number; name: string; tone: 'light' | 'dark'; clear: number}> = {
  // clear = minimum clear space around the mark, as a fraction of its height
  ddn: {file: 'logos/ddn-logo-primary-color.svg', aspect: 280 / 93, name: 'DDN', tone: 'light', clear: 0.5},
  'ddn-white': {file: 'logos/ddn-logo-white.svg', aspect: 80 / 27, name: 'DDN', tone: 'dark', clear: 0.5},
  netflix: {file: 'logos/Netflix_2015_logo.svg', aspect: 1024 / 276.742, name: 'Netflix', tone: 'light', clear: 0.5},
  youtube: {file: 'logos/YouTube_Logo_2017.svg', aspect: 512 / 114.301, name: 'YouTube', tone: 'light', clear: 0.5},
  blockbuster: {file: 'logos/Blockbuster_logo.svg', aspect: 593.91 / 356.35, name: 'Blockbuster', tone: 'light', clear: 0.3},
  canalplus: {file: 'logos/Canal_plus_logo.svg', aspect: 312.80124 / 78.459503, name: 'Canal+', tone: 'light', clear: 0.5},
  arsenal: {file: 'logos/Arsenal_FC.svg', aspect: 322.793 / 379.84, name: 'Arsenal', tone: 'light', clear: 0.2},
  starz: {file: 'logos/Starz_logo.svg', aspect: 1000 / 231.29093, name: 'Starz', tone: 'light', clear: 0.5},
};

export const Logo: React.FC<{id: LogoId; height: number; style?: React.CSSProperties}> = ({id, height, style}) => {
  const l = LOGOS[id];
  return <Img src={staticFile(l.file)} style={{height, width: height * l.aspect, display: 'block', objectFit: 'contain', ...style}} />;
};
