"""Property-sale signals from wpr-property-transactions output.

Wiring decision (2026-08-19): reads the data/transactions.json the sibling
repo commits, via the raw GitHub URL — same mechanism as permits.

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

import re
from datetime import date

from ..models import Signal, SignalKind, Source
from . import get_json, resolve_key

__all__ = ["fetch", "signals_from_feed", "FEED_URL"]

FEED_URL = ("https://raw.githubusercontent.com/RowanFlynnPilot/"
            "wpr-property-transactions/main/data/transactions.json")

_MUNICIPALITY = re.compile(r"^(?P<name>.+), (?P<kind>City|Village|Town) of$")


def _municipality(raw: str) -> str:
    match = _MUNICIPALITY.match(raw)
    if match is None:
        raise ValueError(f"unrecognized municipality form: {raw!r}")
    if match["kind"] == "Town":
        return f"Town of {match['name']}"
    return match["name"]


def signals_from_feed(payload: dict, aliases: dict[str, str]) -> list[Signal]:
    signals = []
    for record in payload["transactions"]:
        if (record["county"] != "Marathon"
                or record["property_use"] != "Commercial"
                or record["sale_price"] < 1000):
            continue

        signals.append(Signal(
            id=f"transfer:{record['document_number']}",
            location_key=resolve_key(
                record["address"], _municipality(record["municipality"]), aliases
            ),
            source=Source.TRANSFER,
            kind=SignalKind.COMMERCIAL_SALE,
            observed=date.fromisoformat(record["recorded_date"]),
            summary=f"Sold for ${record['sale_price']:,} to {record['grantee']}",
            receipt={
                "document_number": record["document_number"],
                "grantor": record["grantor"],
                "grantee": record["grantee"],
                "consideration": str(record["sale_price"]),
            },
        ))
    return signals


def fetch(aliases: dict[str, str]) -> list[Signal]:
    return signals_from_feed(get_json(FEED_URL), aliases)
