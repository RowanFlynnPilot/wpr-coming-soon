"""Property-sale signals from wpr-property-transactions output.

Wiring decision (2026-08-19): reads the data/transactions.json the sibling
repo commits, via the raw GitHub URL — same mechanism as permits.

The ledger (data/transfers_ledger.json)
---------------------------------------
The sibling feed is a ROLLING 30-day window, overwritten weekly — upstream
forgets. Signals must not: a location could vanish from the queue before the
editor sees it, and a published location whose only signal aged out would
orphan its override and stop the build. So every fetch folds the feed's kept
records into a committed, accrue-only ledger and emits signals from the
LEDGER, never the raw feed. Permit-tracker semantics: re-ingesting an
identical record is a no-op; a CHANGED record for a known document number
raises (transfer returns are point-in-time filings — silent mutation means
something upstream is wrong). The nightly Actions run commits the ledger
back, same as public/.

Feed reality (real records in tests/fixtures/transactions_sample.json): the
scrape covers six counties, so this adapter filters to Marathon; the class
field is ``property_use`` and only "Commercial" is kept (Manufacturing /
Utility / Other are not retail-facing stories); the feed carries
``recorded_date`` but not the conveyance date, so recorded_date is what
``observed`` means here. Municipalities arrive as "Wausau, City of" /
"Brighton, Town of": cities and villages map to their bare name (matching
the permit and license feeds), towns keep a "Town of" prefix so the Town of
Wausau can never collide with the City of Wausau.

Keep:    county == "Marathon", property_use == "Commercial",
         sale_price >= $1,000.
Drop:    other counties and property classes; nominal-consideration
         transfers (< $1,000 — quitclaims, intra-family, LLC reshuffles).
         Drops are filtered BEFORE the ledger, so it holds kept records only.
Map:     id        -> f"transfer:{document_number}"
         observed  -> recorded date
         summary   -> "Sold for ${sale_price:,} to {grantee}"
         receipt   -> {"document_number": ..., "grantor": ..., "grantee": ...,
                       "consideration": ...}
Address: via resolve_key() — AddressError propagates; fixes are alias
         entries ("Vacant Land On ..." records are exactly what raw-variant
         aliases exist for).
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from ..models import Signal, SignalKind, Source
from . import get_json, resolve_key

__all__ = ["fetch", "merge_feed", "signals_from_records", "FEED_URL", "LEDGER_PATH"]

FEED_URL = ("https://raw.githubusercontent.com/RowanFlynnPilot/"
            "wpr-property-transactions/main/data/transactions.json")
LEDGER_PATH = Path("data/transfers_ledger.json")

_MUNICIPALITY = re.compile(r"^(?P<name>.+), (?P<kind>City|Village|Town) of$")


def _municipality(raw: str) -> str:
    match = _MUNICIPALITY.match(raw)
    if match is None:
        raise ValueError(f"unrecognized municipality form: {raw!r}")
    if match["kind"] == "Town":
        return f"Town of {match['name']}"
    return match["name"]


def _kept(record: dict) -> bool:
    return (record["county"] == "Marathon"
            and record["property_use"] == "Commercial"
            and record["sale_price"] >= 1000)


def merge_feed(ledger: dict, payload: dict) -> int:
    """Fold the feed's kept records into the ledger; return how many are new.

    Accrue-only: identical re-ingest is a no-op, a changed record for a
    known document number raises.
    """
    new = 0
    for record in payload["transactions"]:
        if not _kept(record):
            continue
        doc = record["document_number"]
        if doc in ledger:
            if ledger[doc] != record:
                raise ValueError(
                    f"transfers ledger conflict: document {doc} changed "
                    f"between runs"
                )
        else:
            ledger[doc] = dict(record)
            new += 1
    return new


def signals_from_records(ledger: dict, aliases: dict[str, str]) -> list[Signal]:
    signals = []
    for doc in sorted(ledger):
        record = ledger[doc]
        signals.append(Signal(
            id=f"transfer:{doc}",
            location_key=resolve_key(
                record["address"], _municipality(record["municipality"]), aliases
            ),
            source=Source.TRANSFER,
            kind=SignalKind.COMMERCIAL_SALE,
            observed=date.fromisoformat(record["recorded_date"]),
            summary=f"Sold for ${record['sale_price']:,} to {record['grantee']}",
            receipt={
                "document_number": doc,
                "grantor": record["grantor"],
                "grantee": record["grantee"],
                "consideration": str(record["sale_price"]),
            },
        ))
    return signals


def fetch(aliases: dict[str, str]) -> list[Signal]:
    ledger = (json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
              if LEDGER_PATH.exists() else {})
    merge_feed(ledger, get_json(FEED_URL))
    LEDGER_PATH.write_text(
        json.dumps(ledger, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return signals_from_records(ledger, aliases)
