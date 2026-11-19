// On-screen text policy: no dashes, ever. "-" (hyphen), "–" (en dash), "—" (em dash), plus the
// lookalikes U+2010..U+2015 and U+2212 minus. Every component runs its strings through onScreen().
export const DASH_RE = /[-‐-―−]/;

export type DashFlag = {text: string; index: number; char: string; context: string};

export const findDashes = (text: string, context = ''): DashFlag[] => {
  const out: DashFlag[] = [];
  [...text].forEach((ch, i) => {
    if (DASH_RE.test(ch)) out.push({text, index: i, char: ch, context});
  });
  return out;
};

export class DashError extends Error {}

// Rejects (throws, which fails the render) unless strict is false, in which case it logs a flag.
export const onScreen = (text: string, context = 'on-screen text', strict = true): string => {
  const flags = findDashes(text, context);
  if (flags.length) {
    const msg = `[DDN sanitiser] dash ${flags.map((f) => `"${f.char}" at ${f.index}`).join(', ')} in ${context}: "${text}". Rewrite without dashes.`;
    if (strict) throw new DashError(msg);
    console.warn(msg);
  }
  return text;
};
