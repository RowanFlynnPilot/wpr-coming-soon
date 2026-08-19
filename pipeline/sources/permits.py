"""Permit signals from wpr-permit-tracker output.

Wiring decision (2026-08-19): reads the ledger wpr-permit-tracker's monthly
Actions run commits to its repo, via the raw GitHub URL — the one mechanism
that works both locally and in this repo's Actions cron. The ledger currently
starts at 2026-05-01 (first ingested monthly report), which IS the backfill
window; no date filter needed.

Feed reality (see tests/fixtures/permit_ledger_sample.json for real records):
records carry a ``template`` class, not a commercial/residential flag or an
applicant. Wausau's feed does not separate new commercial construction from
alterations — both land in "Com Building" — so the kind mapping below is
deterministic-by-template, and the description in the summary is what tells
the editor which it is. There is no applicant field; the summary carries the
work description only (owner/contractor are visible in the source PDF via
``url``).

Keep:    template "Sign"            -> SignalKind.SIGN_PERMIT
         template "Com Early Start" -> SignalKind.NEW_COMMERCIAL_CONSTRUCTION
         template "Com Building"    -> SignalKind.COMMERCIAL_ALTERATION
Drop:    every other template (residential classes and maintenance-only
         permits: Excavation, Plumbing *, Heating, HVAC, Electrical *,
         Fence, Roofing-type exterior work, Demolition, Paving, ...).
Map:     id        -> f"permit:{municipality_code}-{permit_number}"
         observed  -> issue date
         summary   -> work description, one line
         receipt   -> {"permit_number": ..., "municipality": ..., "issued": ...}
         url       -> the municipality's published monthly report PDF
Address: ledger addresses are "STREET, CITY"; the trailing city segment must
         match the jurisdiction or we fail loudly. Keys via resolve_key() —
         AddressError propagates; fixes are alias entries, not code.
"""

from __future__ import annotations

from datetime import date

from ..models import Signal, SignalKind, Source
from . import get_json, resolve_key

__all__ = ["fetch", "signals_from_ledger", "LEDGER_URL"]

LEDGER_URL = ("https://raw.githubusercontent.com/RowanFlynnPilot/"
              "wpr-permit-tracker/master/data/ledger.json")

_KEEP = {
    "Sign": SignalKind.SIGN_PERMIT,
    "Com Early Start": SignalKind.NEW_COMMERCIAL_CONSTRUCTION,
    "Com Building": SignalKind.COMMERCIAL_ALTERATION,
}

_MUNICIPALITIES = {
    "wausau": ("Wausau", "WAU"),
    "schofield": ("Schofield", "SCH"),
    "rib_mountain": ("Rib Mountain", "RIB"),
}


def signals_from_ledger(ledger: dict, aliases: dict[str, str]) -> list[Signal]:
    signals = []
    for permit_id in sorted(ledger):
        record = ledger[permit_id]
        kind = _KEEP.get(record["template"])
        if kind is None:
            continue

        jurisdiction = record["jurisdiction"]
        if jurisdiction not in _MUNICIPALITIES:
            raise ValueError(
                f"permit {permit_id}: unmapped jurisdiction {jurisdiction!r}"
            )
        municipality, code = _MUNICIPALITIES[jurisdiction]

        street, _, city = record["address"].rpartition(",")
        if not street or city.strip().upper() != municipality.upper():
            raise ValueError(
                f"permit {permit_id}: address {record['address']!r} does not "
                f"end in expected municipality {municipality!r}"
            )

        summary = " ".join((record["description"] or record["template"]).split())
        signals.append(Signal(
            id=f"permit:{code}-{permit_id}",
            location_key=resolve_key(street, municipality, aliases),
            source=Source.PERMIT,
            kind=kind,
            observed=date.fromisoformat(record["issue_date"]),
            summary=summary,
            receipt={
                "permit_number": permit_id,
                "municipality": municipality,
                "issued": record["issue_date"],
            },
            url=record.get("source_document"),
        ))
    return signals


def fetch(aliases: dict[str, str]) -> list[Signal]:
    return signals_from_ledger(get_json(LEDGER_URL), aliases)
