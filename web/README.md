# Coming Soon widget

Embeddable React widget (docs/WIDGET.md) in the WPR house branding, plus
the internal editor queue page. Two pages, two files:

- `index.html` — the public widget; consumes exactly `./locations.json`
- `queue.html` — the editor queue (noindex, internal by convention);
  consumes `./queue.json` and offers copy-ready override YAML per entry

At deploy time build.yml copies the pipeline's real `public/*.json` next to
`dist/index.html` and runs `scripts/enrich_geo.py` over the copies (map
lat/lon from the permit tracker's geocodes), so the widget and its data
ship together. Deployed at https://rowanflynnpilot.github.io/wpr-coming-soon/.

The JSON files in `web/public/` are **dev samples only** so `npm run dev`
has something to render; the deploy step overwrites them with the real
files. Nothing here publishes anything — the pipeline's editorial gate
decides what reaches the real locations.json.

Branding/sponsor config lives in `src/config.js` (same contract as the
paper's other widgets; `?demo` previews open sponsor slots).

- `npm install`
- `npm run dev` — local preview with the sample data
- `npm run build` — static build to `dist/`
