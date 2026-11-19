// Single font token module. To switch to the licensed DDN face, drop the Adobe Fonts desktop files into
// public/fonts/ as ArticulatCF-Regular.otf / ArticulatCF-Medium.otf / ArticulatCF-DemiBold.otf /
// ArticulatCF-Bold.otf. Nothing else changes: every component reads FONT.display from here.
import {loadFont} from '@remotion/fonts';
import {useEffect, useState} from 'react';
import {continueRender, delayRender, getStaticFiles, staticFile} from 'remotion';

const ARTICULAT_FILES: {file: string; weight: string}[] = [
  {file: 'fonts/ArticulatCF-Regular.otf', weight: '400'},
  {file: 'fonts/ArticulatCF-Medium.otf', weight: '500'},
  {file: 'fonts/ArticulatCF-DemiBold.otf', weight: '600'},
  {file: 'fonts/ArticulatCF-Bold.otf', weight: '700'},
];
// Measured match (research/FONT_MATCH.md): variable Inter Tight, wght 100 to 900, SIL OFL
// (brand/fonts/InterTight/InterTight[wght].ttf, copied to public/fonts/InterTight-VF.ttf with its OFL.txt).
const INTER_TIGHT_FILES = [{file: 'fonts/InterTight-VF.ttf', weight: '100 900'}];
// Geist Mono, SIL OFL, official Vercel files (npm "geist" 1.9.2, same as the GitHub release).
const GEIST_MONO_FILES = [
  {file: 'fonts/GeistMono-Regular.woff2', weight: '400'},
  {file: 'fonts/GeistMono-Medium.woff2', weight: '500'},
];

const present = new Set(getStaticFiles().map((f) => f.name));
const articulatFound = ARTICULAT_FILES.filter((f) => present.has(f.file));

export const FONT_STATUS = {
  articulat: articulatFound.length > 0 ? `loaded (${articulatFound.map((f) => f.weight).join('/')})` : 'missing: using Inter Tight fallback',
  usingArticulat: articulatFound.length > 0,
};

export const FONT = {
  // CSS stack: Articulat first (if its files exist), then Inter Tight. Never a system default.
  display: '"Articulat CF", "Inter Tight", sans-serif',
  mono: '"Geist Mono", monospace',
  displayFamilyLoaded: articulatFound.length > 0 ? 'Articulat CF' : 'Inter Tight',
} as const;

const load = (family: string, files: {file: string; weight: string}[]) =>
  files.map((f) => loadFont({family, url: staticFile(f.file), weight: f.weight, display: 'block'}));

// Fonts fail silently in Chrome; hold the render until both families are verifiably usable.
const handle = delayRender('DDN fonts');
let ready = false;
export const fontsReady: Promise<void> = Promise.all([...load('Articulat CF', articulatFound), ...load('Inter Tight', INTER_TIGHT_FILES), ...load('Geist Mono', GEIST_MONO_FILES)])
  .then(() => {
    const probes = FONT_STATUS.usingArticulat ? ['400', '500'] : ['340', '480', '620'];
    for (const probe of [...probes.map((w) => `${w} 78px "${FONT.displayFamilyLoaded}"`), '400 24px "Geist Mono"']) {
      if (!document.fonts.check(probe)) throw new Error(`Font not usable: ${probe}`);
    }
    ready = true;
    continueRender(handle);
  })
  .catch((e) => {
    throw e;
  });

// Text measurement must wait for the real fonts, otherwise widths are cached from the fallback face.
// Holds the frame (delayRender) until the re-render with real metrics has happened.
export const useFontsReady = () => {
  const [ok, setOk] = useState(ready);
  const [handle] = useState(() => (ready ? null : delayRender('DDN fonts: measurement')));
  useEffect(() => {
    if (ok) {
      if (handle !== null) continueRender(handle);
      return;
    }
    fontsReady.then(() => setOk(true));
  }, [ok, handle]);
  return ok;
};

// Type roles (research/FONT_MATCH.md, section 2). Inter Tight is set to match Articulat CF: size x0.966 (cap height
// 0.7275 em vs 0.70 em), weights and extra tracking measured per style. With real Articulat files the roles map to
// the desktop styles at size x1 and no extra tracking. `tracking` is DDN's own spec tracking (em), added on top.
export type TypeRole = 'regular' | 'regularDesktop' | 'medium' | 'bold' | 'capsName' | 'caption';
export const DDN_TYPE: Record<TypeRole, {fontWeight: number; letterSpacing: number; sizeScale: number}> = {
  regular: {fontWeight: 340, letterSpacing: 0.014, sizeScale: 0.966}, // body, captions (ddn.com 400 = Articulat Normal)
  regularDesktop: {fontWeight: 380, letterSpacing: 0.022, sizeScale: 0.966}, // Articulat Regular
  medium: {fontWeight: 480, letterSpacing: 0.025, sizeScale: 0.966}, // names, title cards, keywords
  bold: {fontWeight: 620, letterSpacing: 0.023, sizeScale: 0.966}, // headlines (Articulat Demi Bold)
  capsName: {fontWeight: 540, letterSpacing: 0.05, sizeScale: 0.966}, // lower third caps
  caption: {fontWeight: 650, letterSpacing: 0.012, sizeScale: 0.966}, // pitch captions: a touch heavier, tighter set for one-line reading
};
const ARTICULAT_WEIGHT: Record<TypeRole, number> = {regular: 400, regularDesktop: 400, medium: 500, bold: 600, capsName: 500, caption: 600};

export const display = (role: TypeRole, size: number, tracking = 0): {fontFamily: string; fontWeight: number; fontSize: number; letterSpacing: string} =>
  FONT_STATUS.usingArticulat
    ? {fontFamily: FONT.display, fontWeight: ARTICULAT_WEIGHT[role], fontSize: size, letterSpacing: `${tracking}em`}
    : {fontFamily: FONT.display, fontWeight: DDN_TYPE[role].fontWeight, fontSize: +(size * DDN_TYPE[role].sizeScale).toFixed(2), letterSpacing: `${(tracking + DDN_TYPE[role].letterSpacing).toFixed(4)}em`};
