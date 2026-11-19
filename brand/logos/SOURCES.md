# Logo sources (third party marks)

All files are the original artwork, downloaded unmodified from Wikimedia Commons on 2026-11-18. They are used unchanged in `tools/remotion/public/logos/` (copies). The only exception is `Canal_plus_logo.svg`, where a `viewBox` attribute was added to the root `<svg>` so it scales. Paths, colours and proportions are untouched.

Commons marks these files as **public domain** because they are below the threshold of originality (simple text or geometric shapes). They are still **registered trademarks** of their owners. Using them to refer to the companies (nominative use, e.g. "families drift to Netflix") is the intended use here. Do not imply endorsement, and do not alter, recolour or animate the marks themselves. Our motion is applied to the plate the mark sits on, never to the mark.

| File | Mark | Source page | Direct file | Licence (Commons) | Trademark |
|---|---|---|---|---|---|
| `Netflix_2015_logo.svg` | Netflix wordmark (2015, current) | https://commons.wikimedia.org/wiki/File:Netflix_2015_logo.svg | https://upload.wikimedia.org/wikipedia/commons/0/08/Netflix_2015_logo.svg | Public domain | TM/® Netflix, Inc. |
| `YouTube_Logo_2017.svg` | YouTube logo (2017, current; dark text, for light backgrounds) | https://commons.wikimedia.org/wiki/File:YouTube_Logo_2017.svg | https://upload.wikimedia.org/wikipedia/commons/b/b8/YouTube_Logo_2017.svg | Public domain | TM Google LLC (YouTube) |
| `Blockbuster_logo.svg` | Blockbuster ticket logo | https://commons.wikimedia.org/wiki/File:Blockbuster_logo.svg | https://upload.wikimedia.org/wikipedia/commons/4/46/Blockbuster_logo.svg | Public domain | TM Blockbuster (Dish Network) |
| `Canal_plus_logo.svg` | Canal+ logo (1995 design, still in use) | https://commons.wikimedia.org/wiki/File:Logo_Canal%2B_1995.svg | https://upload.wikimedia.org/wikipedia/commons/5/5d/Logo_Canal%2B_1995.svg | Public domain | TM Groupe Canal+ |
| `Starz_logo.svg` | Starz logo (2022, current) | https://commons.wikimedia.org/wiki/File:Starz_2022.svg | https://upload.wikimedia.org/wikipedia/commons/0/03/Starz_2022.svg | Public domain | TM Starz Entertainment, LLC |

DDN marks come from DDN's own brand page (`brand/`, see `research/DDN_STYLE_GUIDE.md` section 0). On light plates and the end card we use `ddn-logo-primary-color.svg`. On dark glass we use `main-logo-small.svg` (colour ring with a white wordmark), copied as `public/logos/ddn-logo-white.svg`. Note that DDN's own SVGs embed the ring as a 173 px PNG, so keep the logo at or below about 170 px tall.

**Sky: not included.** Sky's current (2020) gradient wordmark is not on Commons; it is above the threshold of originality, so it is not public domain. Sky's press site was not reachable from this environment. To add it, download the official SVG from Sky's brand or press centre (skygroup.sky/press) and save it as `brand/logos/Sky_logo.svg` and `tools/remotion/public/logos/Sky_logo.svg`. Then add a `sky` entry in `tools/remotion/src/ddn/logos.tsx`. Until then, "Sky" appears only as text (and as caption emphasis).
