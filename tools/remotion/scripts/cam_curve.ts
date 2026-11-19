// Dump the per-frame camera scale of PitchFinal (v6) as JSON lines: frame, z, blur, shot.
import {cameraV6} from '../src/pitch/layout_v4';
const out: string[] = [];
for (let f = 0; f < 2227; f++) {
  const c = cameraV6(f);
  out.push(`${f},${c.z.toFixed(5)},${c.blur.toFixed(2)},${c.i}`);
}
console.log(out.join('\n'));
