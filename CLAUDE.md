# wpr-coming-soon

"What's going in that building?" — signal pipeline for the Wausau Pilot &
Review Coming Soon tracker. Merges building permits, commercial property
transfers, and new alcohol-license applications into location records that an
editor confirms before anything publishes.

## Architecture

```
sources/*.fetch()  →  merge(signals, overrides)  →  build()  →  public/*.json  →  widget
   (stubs)             address-keyed accrual         static        committed       deferred
                       + editorial gate              JSON          by Actions
```

- `pipeline/models.py` — Signal / Location / lifecycle enums
- `pipeline/normalize.py` — deterministic address → canonical key; raises on
  anything it can't handle
- `pipeline/merge.py` — load_overrides (strict validation) + merge (accrual +
  gate enforcement)
- `pipeline/build.py` — writes `public/locations.json` (published) and
  `public/queue.json` (editor review)
- `pipeline/sources/` — one adapter per source, `fetch() -> list[Signal]`,
  contracts in docstrings and docs/SIGNALS.md
- `data/overrides/locations.yaml` — the ONLY publication mechanism

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
- `pytest` — 28 tests; run before every commit
- `python -m pipeline` — full build (fails until sources are implemented)

## Status / next steps

1. Implement `sources/licenses.py` (marathon-meetings items) — highest
   story-per-signal, smallest volume
2. Implement `sources/permits.py` (wpr-permit-tracker output)
3. Implement `sources/transfers.py` (wpr-property-transactions output)
4. Enable the cron in `.github/workflows/build.yml`
5. Widget (docs/WIDGET.md)
