# wpr-coming-soon

**What's going in that building?** A Wausau Pilot & Review tracker that merges
public-record signals — building permits, commercial property sales, and new
alcohol-license applications — into a single answer to the most-asked question
in every local Facebook group. Every published entry shows its receipts.

## How it works

1. Source adapters read the output of pipelines WPR already runs
   (`wpr-permit-tracker`, `wpr-property-transactions`, `marathon-meetings`)
   and emit signals keyed to normalized addresses.
2. Signals accrue to locations. Locations start at internal `signal` status.
3. An editor confirms what's actually going in and promotes the location to
   `coming_soon` (and later `open`) in `data/overrides/locations.yaml` —
   see `data/overrides/README.md`. Nothing publishes without this step.
4. A nightly GitHub Action rebuilds `public/locations.json`, which the
   embeddable widget consumes.

## Quickstart

```
pip install -e ".[dev]"
pytest                 # 28 tests
python -m pipeline     # NotImplementedError until sources are wired — by design
```

## Repo map

| path                          | what                                          |
| ----------------------------- | --------------------------------------------- |
| `pipeline/`                   | models, normalize, merge, build (implemented) |
| `pipeline/sources/`           | permit / transfer / license adapters (stubs)  |
| `data/overrides/`             | editorial curation — the publication mechanism|
| `docs/SCHEMA.md`              | data model + lifecycle + JSON shape           |
| `docs/SIGNALS.md`             | per-source extraction spec                    |
| `docs/WIDGET.md`              | front-end spec (deferred)                     |
| `public/`                     | build artifacts, committed by Actions         |

## Status

Pipeline core implemented and tested; the three source adapters are stubbed
with their extraction contracts. Implementation order: licenses → permits →
transfers (see docs/SIGNALS.md).
