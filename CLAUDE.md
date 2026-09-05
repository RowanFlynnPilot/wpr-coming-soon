# wpr-coming-soon

"What's going in that building?" — signal pipeline for the Wausau Pilot &
Review Coming Soon tracker. Merges building permits, commercial property
transfers, and new alcohol-license applications into location records that an
editor confirms before anything publishes.

## Architecture

```
sources/*.fetch()  →  ledger  →  merge(signals, overrides)  →  build()  →  public/*.json  →  widget
   (live)          accrue-only   address-keyed accrual         static        committed       Pages
                    memory       + editorial gate              JSON          by Actions
```

- `pipeline/models.py` — Signal / Location / lifecycle enums
- `pipeline/normalize.py` — deterministic address → canonical key; raises on
  anything it can't handle
- `pipeline/merge.py` — load_overrides (strict validation) + merge (accrual +
  gate enforcement)
- `pipeline/build.py` — writes `public/locations.json` (published) and
  `public/queue.json` (editor review)
- `pipeline/sources/` — one adapter per source, `fetch(aliases) -> list[Signal]`,
  contracts in docstrings and docs/SIGNALS.md
- `data/overrides/locations.yaml` — the ONLY publication mechanism
- `pipeline/ledger.py` + `data/signals_ledger.json` — accrue-only memory of
  every signal ever fetched, storing raw addresses so keys are re-derived
  each build (aliases stay retroactive) and stamping `first_seen`; the
  build reads the ledger, never the raw fetch (committed back nightly)
- `scripts/enrich_geo.py` — deploy-time lat/lon join against the permit
  ledger's geocodes; committed public/ files are never touched
- `web/` — the widget (index) + internal editor queue page (queue.html),
  deployed to https://rowanflynnpilot.github.io/wpr-coming-soon/ by build.yml

## Principles (do not drift)

- The editorial gate is load-bearing. No code path may publish a location
  without a curated `name` set in overrides. Do not "fix" GateError by
  defaulting a name.
- No fuzzy address matching, ever. AddressError → alias entry.
- Fail fast: bad override files, unparseable addresses, and empty receipts
  stop the build with the offending record in the error.
- One way: aliases are the single merge/fix mechanism; overrides are the
  single curation mechanism; the widget reads a single file.
- Surgical changes; keep functions single-responsibility.

## Commands

- `pip install -e ".[dev]"` — setup
- `pytest` — run before every commit (also gates the nightly build)
- `python -m pipeline` — full build against the live feeds; writes
  `public/*.json` and updates `data/transfers_ledger.json`

## Status / next steps

Fully live (2026-08-19). All three adapters run (wiring decisions in each
docstring — licenses.py reads Wausau's CivicClerk API directly and ingests
posted agendas up to 14 days ahead; transfers accrue into a committed
ledger because the sibling feed is a rolling 30-day window). The nightly
cron tests, builds, commits data, and deploys the widget + editor queue
page to Pages in WPR house branding, with a deploy-time geo join for the
map view. The batched license-PDF idea was investigated and is a documented
dead end (docs/SIGNALS.md) — the report's Address column is the licensee's
mailing address, not the premises.

Review pass 2026-09-05 (17 nightly runs in; 16 green, the one failure a
Pages 502): hardened per the fresh-eyes review, `first_seen` stamped per
location (the committed public/ files are the memory), editor queue sorts
by newest arrivals / strongest signals with "New" markers. Feed cadence to
keep in mind: permits land in monthly batches (a July 31 permit surfaces
~Sept 12), transfers weekly, licenses monthly with ~a week of agenda lead.

1. Editor pass: work /queue.html (copy-ready YAML per entry) — first
   curated `locations:` entries make the public page non-empty
2. Sponsor slots are placeholders — real sponsor config when sold
3. Watch queue growth; signal aging stays out of v1 unless the editor pass
   starts hurting (the ledger makes an age filter trivial if it comes to it)
