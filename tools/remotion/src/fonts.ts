import {loadFont} from '@remotion/fonts';
import {staticFile} from 'remotion';
// Local fonts: headless Chrome does not trust the egress proxy CA, so never fetch Google Fonts at render time.
export const fontFamily = 'Inter';
for (const w of ['400', '500', '700']) {
  loadFont({family: fontFamily, url: staticFile(`fonts/inter-latin-${w}-normal.woff2`), weight: w});
}
