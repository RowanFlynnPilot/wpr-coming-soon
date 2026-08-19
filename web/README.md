# Coming Soon widget

Embeddable React widget (docs/WIDGET.md). It consumes exactly one file,
`./locations.json`, fetched relative to wherever the build is served — the
same pattern as the other WPR tools: at deploy time the pipeline's
`public/locations.json` is copied next to `dist/index.html`, so the widget
and its data ship together.

`web/public/locations.json` is a **dev sample only** (entries are named
"SAMPLE — ...") so `npm run dev` has something to render; the deploy step
overwrites it with the real file. Nothing here publishes anything — the
pipeline's editorial gate decides what reaches the real locations.json.

- `npm install`
- `npm run dev` — local preview with the sample data
- `npm run build` — static build to `dist/`
