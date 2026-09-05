"""Produce the static JSON artifacts.

- public/locations.json — editor-confirmed entries (coming_soon / open) with
  full receipts. This is the only file the widget consumes.
- public/queue.json — locations still at ``signal`` status, for the editor.
  Same shape, kept out of the widget by convention, not secrecy: everything in
  it is already public record.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import Location, Signal, Status

__all__ = ["build"]


def _signal_dict(signal: Signal) -> dict:
    return {
        "id": signal.id,
        "source": signal.source.value,
        "kind": signal.kind.value,
        "observed": signal.observed.isoformat(),
        "summary": signal.summary,
        "receipt": signal.receipt,
        "url": signal.url,
    }


def _location_dict(location: Location) -> dict:
    # Every built signal comes from the ledger and carries its stamp. Permits
    # surface in monthly batches weeks after their issue dates, so signal
    # dates alone can't tell "new to us" from "old news": first_seen is when
    # the location entered our view, last_arrival when its newest signal did.
    stamps = [s.first_seen for s in location.signals]
    if any(stamp is None for stamp in stamps):
        raise ValueError(f"{location.key}: unledgered signal reached the build")
    return {
        "key": location.key,
        "status": location.status.value,
        "name": location.name,
        "category": location.category,
        "address": location.address,
        "municipality": location.municipality,
        "note": location.note,
        "opened": location.opened.isoformat() if location.opened else None,
        "first_seen": min(stamps).isoformat(),
        "last_arrival": max(stamps).isoformat(),
        "signals": [_signal_dict(s) for s in location.signals],
    }


def _write(path: Path, locations: list[Location]) -> None:
    ordered = sorted(locations, key=lambda l: l.latest, reverse=True)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "locations": [_location_dict(l) for l in ordered],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8",
                    newline="\n")


def build(locations: list[Location], out_dir: Path) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    published = [l for l in locations if l.status is not Status.SIGNAL]
    queue = [l for l in locations if l.status is Status.SIGNAL]
    _write(out_dir / "locations.json", published)
    _write(out_dir / "queue.json", queue)
    return {"published": len(published), "queue": len(queue)}
