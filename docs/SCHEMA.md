# Schema

## The one design decision everything follows from

The unit is the **location**, not the signal. Scrapers never publish anything;
they emit `Signal` records keyed to a normalized address. Signals accrue to a
`Location`, and a Location moves through a one-way, editor-driven lifecycle:

```
signal ──────────────► coming_soon ──────────► open
(internal only)        (published)             (published)
```

Promotion happens **only** through `data/overrides/locations.yaml`. There is no
code path that publishes a location automatically, and the merge step throws
(`GateError`) if an override sets a published status without a curated `name`.
That gate is the editorial policy, expressed as a precondition — same
philosophy as the court tracker.

## Location key

`normalize.normalize_address(raw, municipality)` produces the canonical key:

```
"1300 N. 3rd Street, Ste 200" + "Wausau"  →  "1300 N 3RD ST|WAUSAU"
```

Uppercase, punctuation stripped, unit dropped, USPS suffix/direction
abbreviations, spelled-out ordinals numbered. Deterministic only — no fuzzy
matching, no geocoding. An address the rules can't handle raises
`AddressError` and stops the build; the fix is an `address_aliases` entry, not
looser code. Two sources writing the same building two ways is also an alias
entry. One mechanism for both problems.

## Signal

| field          | type              | notes                                          |
| -------------- | ----------------- | ---------------------------------------------- |
| `id`           | str               | stable, source-prefixed: `permit:WAU-2026-001` |
| `location_key` | str               | normalized address                             |
| `source`       | enum              | `permit` / `transfer` / `license`              |
| `kind`         | enum              | see `SignalKind` in `pipeline/models.py`       |
| `observed`     | date              | when the public record surfaced                |
| `summary`      | str               | one human-readable line                        |
| `receipt`      | dict[str, str]    | the proof — **required, never empty**          |
| `url`          | str \| None       | link to the record where one exists            |

Receipts are the product: every published entry shows the permit number,
transfer document, or agenda item behind it. That's what separates this from
a Facebook rumor thread.

## Location

Derived fields (`key`, `address`, `municipality`, `signals`) come from the
merge. Curated fields (`status`, `name`, `category`, `note`, `opened`) come
**only** from overrides.

## Overrides file (`data/overrides/locations.yaml`)

```yaml
address_aliases:
  "1300 N THIRD ST|WAUSAU": "1300 N 3RD ST|WAUSAU"

locations:
  "301 WASHINGTON ST|WAUSAU":
    status: coming_soon          # or: open
    name: "Example Coffee Co."   # required once status is set
    category: restaurant
    note: "Confirmed by owner 8/12; targeting October."

  "123 GRAND AVE|SCHOFIELD":
    suppress: true               # not a new opening; must be the only field
```

`load_overrides()` validates strictly and raises `OverrideError` on: unknown
fields, bad status values, `status: signal` (delete the field instead),
`suppress` combined with anything else, `opened` without `status: open`,
`opened` that isn't a date, alias chains, and overrides pointing at addresses
with no signals (catches stale entries and key typos).

## Build outputs

`python -m pipeline` writes two files to `public/`:

- **`locations.json`** — published entries only (`coming_soon` + `open`),
  newest signal first. The widget consumes exactly this file.
- **`queue.json`** — same shape, `signal`-status locations awaiting editorial
  review. Internal by convention, not secrecy (it's all public record).

```json
{
  "generated": "2026-08-19T15:30:00+00:00",
  "locations": [
    {
      "key": "301 WASHINGTON ST|WAUSAU",
      "status": "coming_soon",
      "name": "Example Coffee Co.",
      "category": "restaurant",
      "address": "301 Washington St",
      "municipality": "Wausau",
      "note": "Confirmed by owner 8/12; targeting October.",
      "opened": null,
      "signals": [
        {
          "id": "permit:WAU-2026-001",
          "source": "permit",
          "kind": "sign_permit",
          "observed": "2026-08-01",
          "summary": "Sign permit issued",
          "receipt": { "permit_number": "WAU-2026-001", "municipality": "Wausau" },
          "url": null
        }
      ]
    }
  ]
}
```

## Deliberately not in v1

- **Geocoding / map pins** — add lat/lng at widget time if the map needs it;
  don't complicate the pipeline for it.
- **DFI registrations** — name-keyed search, not address-keyed; it's a manual
  verification step for the editor, not a pipeline source.
- **`closed` status** — this is a Coming Soon tracker; closures are a
  different product.
- **Signal aging/expiry** — Marathon County volume doesn't need it. Suppress
  handles noise.
