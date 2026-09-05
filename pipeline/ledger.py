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
The location-defining facts (source, kind, observed, address, municipality)
are immutable: a known id whose facts changed raises, because a filing that
moves house is a sign something upstream is wrong. Summary, receipt, and
url track the source's latest wording (agenda revisions, name corrections)
without a halt. Recovery from a genuine upstream correction is by hand, in
a commit that says why.
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
_IDENTITY = ("source", "kind", "observed", "address", "municipality")


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save(ledger: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8")


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


def merge(ledger: dict, signals: Iterable[Signal], today: date) -> int:
    """Fold freshly fetched signals into the ledger; return how many are new."""
    new = 0
    for signal in signals:
        if not signal.address or not signal.municipality:
            raise ValueError(f"signal {signal.id}: no raw address to ledger")
        record = _record(signal)
        known = ledger.get(signal.id)
        if known is None:
            ledger[signal.id] = {**record, "first_seen": today.isoformat()}
            new += 1
            continue
        changed = [f for f in _IDENTITY if known[f] != record[f]]
        if changed:
            raise ValueError(
                f"signals ledger conflict: {signal.id} changed {changed} "
                f"between runs (was {[known[f] for f in changed]}, "
                f"now {[record[f] for f in changed]})"
            )
        known.update(record)   # latest wording wins; first_seen is kept
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
