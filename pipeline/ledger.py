"""The signals ledger: every signal any source has ever emitted, accrue-only.

Why it exists
-------------
Sources forget. The transfer feed is a rolling 30-day window; a CivicClerk
agenda item can be edited or withdrawn; a permit ledger could be rebuilt.
The pipeline must not forget with them: a location would vanish from the
queue before the editor saw it, and a published location whose only signal
disappeared would orphan its override and stop the build. So every nightly
run folds the fresh fetch into ``data/signals_ledger.json`` (committed back
by Actions) and the build reads signals from the LEDGER, never from the raw
fetch.

What a record holds
-------------------
The signal's fields plus the address *as the source wrote it* and the
municipality it was resolved under — not the normalized key. ``to_signals``
re-derives ``location_key`` via ``resolve_key`` on every build, so a new
alias entry or a better normalize rule applies to history too. Each record
also carries ``first_seen``, the date it entered the ledger; permits arrive
in monthly batches weeks after their issue dates, so signal dates alone
can't tell "new to us" from "old news".

Conflict rule
-------------
The location-defining facts (source, kind, address, municipality) are
immutable: a known id whose facts changed raises, because a filing that
moves house is a sign something upstream is wrong. Observed date, summary,
receipt, and url track the source's latest record (a rescheduled meeting,
an agenda revision, a corrected name) without a halt. Recovery from a
genuine upstream correction is by hand, in a commit that says why.

The future is provisional, the past is permanent
-----------------------------------------------
Agenda items are ingested up to two weeks before their meeting, and until
the gavel falls they can be withdrawn, renumbered (a new id) or reworded
past our patterns. So a ledgered signal dated AFTER today that the source no
longer reports is dropped again; once its date has passed it is history and
stays forever, whatever the source does later.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Iterable

from .models import Signal, SignalKind, Source
from .sources import resolve_key

__all__ = ["LEDGER_PATH", "load", "save", "merge", "to_signals"]

LEDGER_PATH = Path("data/signals_ledger.json")
_IDENTITY = ("source", "kind", "address", "municipality")


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save(ledger: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")


def _record(signal: Signal) -> dict:
    return {
        "source": signal.source.value,
        "kind": signal.kind.value,
        "observed": signal.observed.isoformat(),
        "summary": signal.summary,
        "receipt": signal.receipt,
        "url": signal.url,
        "address": signal.address,
        "municipality": signal.municipality,
    }


def _same_place(known: dict, record: dict, aliases: dict[str, str]) -> bool:
    """Same source/kind/municipality, and the raw addresses key to the same
    location under current rules — so "416 N. 3rd Street" edited upstream to
    "416 N 3rd Street" is a rewording, not a move."""
    if any(known[f] != record[f] for f in ("source", "kind", "municipality")):
        return False
    if known["address"] == record["address"]:
        return True
    return (resolve_key(known["address"], known["municipality"], aliases)
            == resolve_key(record["address"], record["municipality"], aliases))


def merge(ledger: dict, signals: Iterable[Signal], today: date,
          aliases: dict[str, str] | None = None) -> int:
    """Fold freshly fetched signals into the ledger; return how many are new.

    A record dated after today is provisional and is simply replaced by
    whatever the fetch now reports under that id (agendas get renumbered);
    provisional records the fetch no longer reports are retracted. Every
    record the fetch did report gets ``last_seen`` = today.
    """
    aliases = aliases or {}
    stamp = today.isoformat()
    new = 0
    fresh_ids = set()
    for signal in signals:
        fresh_ids.add(signal.id)
        if not signal.address or not signal.municipality:
            raise ValueError(f"signal {signal.id}: no raw address to ledger")
        record = _record(signal)
        known = ledger.get(signal.id)
        if known is None:
            ledger[signal.id] = {**record, "first_seen": stamp, "last_seen": stamp}
            new += 1
            continue
        if known["observed"] > stamp:
            ledger[signal.id] = {**record, "first_seen": known["first_seen"],
                                 "last_seen": stamp}
            continue
        if not _same_place(known, record, aliases):
            changed = [f for f in _IDENTITY if known[f] != record[f]]
            raise ValueError(
                f"signals ledger conflict: {signal.id} changed {changed} "
                f"between runs (was {[known[f] for f in changed]}, "
                f"now {[record[f] for f in changed]})"
            )
        known.update(record)   # latest wording wins; first_seen is kept
        known["last_seen"] = stamp

    provisional = [i for i, r in ledger.items()
                   if r["observed"] > today.isoformat() and i not in fresh_ids]
    for signal_id in provisional:
        del ledger[signal_id]
    return new


def to_signals(ledger: dict, aliases: dict[str, str]) -> list[Signal]:
    """Every ledgered signal, keyed afresh under the current aliases/rules."""
    signals = []
    for signal_id in sorted(ledger):
        rec = ledger[signal_id]
        signals.append(Signal(
            id=signal_id,
            location_key=resolve_key(rec["address"], rec["municipality"], aliases),
            source=Source(rec["source"]),
            kind=SignalKind(rec["kind"]),
            observed=date.fromisoformat(rec["observed"]),
            summary=rec["summary"],
            receipt=rec["receipt"],
            url=rec["url"],
            address=rec["address"],
            municipality=rec["municipality"],
            first_seen=date.fromisoformat(rec["first_seen"]),
        ))
    return signals
