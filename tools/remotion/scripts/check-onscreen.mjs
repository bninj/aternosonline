#!/usr/bin/env node
// Lint on-screen text before render: flags "-", "–", "—" (and U+2010..2015, U+2212) in every string of the given JSON files.
// Usage: node scripts/check-onscreen.mjs public/demo_transcript.json other.json   (exit 1 on any dash)
import {readFileSync} from 'node:fs';
const DASH = /[-‐-―−]/;
let bad = 0;
const walk = (v, path, file) => {
  if (typeof v === 'string') { if (DASH.test(v)) { bad++; console.log(`${file} ${path}: "${v}"`); } }
  else if (Array.isArray(v)) v.forEach((x, i) => walk(x, `${path}[${i}]`, file));
  else if (v && typeof v === 'object') for (const [k, x] of Object.entries(v)) walk(x, `${path}.${k}`, file);
};
for (const f of process.argv.slice(2)) walk(JSON.parse(readFileSync(f, 'utf8')), '$', f);
console.log(bad ? `${bad} string(s) contain dashes: rewrite them.` : 'No dashes in on-screen strings.');
process.exit(bad ? 1 : 0);
