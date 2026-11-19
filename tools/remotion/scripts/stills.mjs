// Render many stills from one bundle: node scripts/stills.mjs <compId> <outDir> <frame,frame,...> [scale]
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import path from 'node:path';
const [comp, out, frames, scale = '1', props = '{}', tag = ''] = process.argv.slice(2);
const inputProps = JSON.parse(props);
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
const composition = await selectComposition({serveUrl, id: comp, inputProps});
for (const f of frames.split(',').map(Number)) {
  await renderStill({serveUrl, composition, inputProps, frame: f, output: path.join(out, `${comp}${tag}_f${String(f).padStart(4, '0')}.png`), scale: Number(scale)});
  process.stdout.write(`${f} `);
}
console.log('done');
