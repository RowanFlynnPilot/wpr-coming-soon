# Widget spec (deferred — build after at least one source is live)

Embeddable React widget, same pattern as the other WPR tools: static build,
consumes exactly one file (`public/locations.json`), no runtime backend.

- **Layout:** card list, newest signal first; optional map view can come later
  (geocode at widget-build time, not in the pipeline).
- **Card:** name, category chip, address + municipality, status badge
  (`Coming soon` / `Now open`), editor note, and the receipts — each signal
  rendered as "Sign permit · Aug 1 · #WAU-2026-001" linking to `url` when set.
- **Receipts are non-negotiable UI.** They're the credibility difference
  between this and a rumor thread.
- **Sponsor slots:** title sponsor strip ("Presented by …") + a highlighted
  "Now Open" spotlight card type — the upsell for the businesses the tracker
  itself discovers.
- **Filters:** municipality and category. Nothing else in v1.
