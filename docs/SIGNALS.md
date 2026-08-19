# Signal extraction spec

Three sources for v1. Two are pipelines that already run in sibling repos —
the adapters here consume their output rather than re-scraping anything. Each
adapter is one function, `fetch(aliases) -> list[Signal]`, where `aliases` is
the `address_aliases` table from the overrides file.

The shared rule for all three: build `location_key` with
`sources.resolve_key()`, which checks `aliases` for the verbatim raw variant
(`"RAW UPPERCASED|MUNICIPALITY UPPERCASED"`, whitespace collapsed) and
otherwise calls `normalize_address()`, letting `AddressError` propagate. A
crashed build with the offending record in the traceback beats a silently
dropped signal. The fix is always an `address_aliases` entry — keyed on the
normalized variant when two sources write one building two ways, or on the
raw variant when the address can't be normalized at all (fire numbers,
"Vacant Land on ...").

---

## 1. Permits — `pipeline/sources/permits.py`

**Feed:** the parsed permit records `wpr-permit-tracker` already produces for
Wausau, Schofield, and Rib Mountain (pdfplumber output). Decide at wiring time
whether this adapter reads the tracker's committed JSON from its repo raw URL
or the repos share a data path — pick one, document it in the adapter
docstring, done.

**Keep:**

| permit type                  | `SignalKind`                  | why it matters                                   |
| ---------------------------- | ----------------------------- | ------------------------------------------------ |
| sign permit                  | `SIGN_PERMIT`                 | the gold signal — usually names the tenant       |
| new commercial construction  | `NEW_COMMERCIAL_CONSTRUCTION` | something is being built                         |
| commercial alteration/remodel| `COMMERCIAL_ALTERATION`       | tenant build-out (noisiest — suppress handles it)|

**Drop:** all residential classes; maintenance-only permits (roofing, HVAC,
electrical service, razing) even on commercial parcels.

**Mapping:**

- `id`: `permit:{municipality_code}-{permit_number}` (e.g. `permit:WAU-2026-00123`)
- `observed`: issue date; application date if that's what the PDF gives
- `summary`: one line from the work description; include the applicant when
  the permit names a tenant rather than a contractor
- `receipt`: `{"permit_number": ..., "municipality": ..., "issued": ...}`

**Known noise:** commercial alterations are mostly existing businesses
remodeling. They stay in the feed — the editor suppresses, the pipeline
doesn't guess.

---

## 2. Property transfers — `pipeline/sources/transfers.py`

**Feed:** the DOR TAP real-estate transfer returns `wpr-property-transactions`
already scrapes for Marathon County.

**Feed caveat:** the sibling's `transactions.json` is a rolling 30-day
window, overwritten weekly. Kept records therefore accrue into a committed,
accrue-only ledger (`data/transfers_ledger.json`) and signals are emitted
from the ledger, never the raw feed — otherwise signals would vanish ~30
days after recording and a published location could orphan its override. A
changed record for a known document number stops the build.

**Keep:** commercial property classes only.

**Drop:** residential, agricultural, and nominal-consideration transfers
(< $1,000 — quitclaims, intra-family, LLC reshuffles). A reshuffle can precede
a real project, but it carries no readable story on its own; the permit or
license that follows will surface the location anyway.

**Mapping:**

- `id`: `transfer:{document_number}`
- `observed`: conveyance date
- `summary`: `"Sold for ${consideration:,} to {grantee}"`
- `receipt`: `{"document_number": ..., "grantor": ..., "grantee": ...,
  "consideration": ...}`

---

## 3. Alcohol license applications — `pipeline/sources/licenses.py`

**Feed (as wired 2026-08-19):** Wausau Public Health & Safety Committee
agenda items, read from the public CivicClerk OData API — the same endpoints
marathon-meetings uses. (The original plan to consume marathon-meetings
output didn't survive contact: its summaries are AI-condensed and its PHS
coverage was 1 meeting in 5. See the adapter docstring.)

**Keep:** the item types that name a business and a premises address in the
item text — license *transfers to a new location* and *90-day extensions to
open for business*. Both are strong coming-soon signals.

**Drop:** renewals (the annual June wall of them), operator/bartender
licenses, agent changes, and temporary Class B "picnic" licenses.

**Extraction:** match on the agenda item title/text. A matched item that
then fails the full parse raises — don't guess an address into the merge.

**The batched-PDF dead end (checked 2026-08-19, do not re-attempt naively):**
genuinely *new* Class A/B applications never appear as their own agenda
items — they batch under one "Approval or denial of various license
applications" item whose detail is an attached "Licenses List" PDF. That
report names the class, applicant, and business (d/b/a), but its Address
column is the **licensee's mailing address, not the premises** — the
2026-06-01 list shows "2510 Deli & Bakery" against the applicant's home
address in Edgar. Auto-keying those rows would merge wrong addresses (and
PO-box rows can't normalize at all), so they stay a manual editor step: the
signal's `url` lands on the portal event page with the PDF one click away.
A future source for premises-accurate applications would be the full agenda
packet's AT-106/AT-115 application forms, not this summary report.

**Mapping:**

- `id`: `license:wausau-{event_id}-{outline}` (e.g. `license:wausau-2069-6.c`)
- `observed`: meeting date
- `summary`: `"License transfer to new location: {trade_name} ({applicant})"`
  / `"Extension to open for business: {trade_name} ({applicant})"`
- `receipt`: `{"body": ..., "meeting_date": ..., "agenda_item": ...,
  "applicant": ..., "trade_name": ...}`
- `url`: the CivicClerk portal event page (attachments one click away)

---

## Implementation order

Licenses → permits → transfers. Licenses have the highest
story-per-signal ratio and the smallest volume; transfers are the noisiest and
benefit from the other two already being in place when tuning the filters.
