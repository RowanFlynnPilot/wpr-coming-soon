"""Produce the static JSON artifacts.

- public/locations.json — editor-confirmed entries (coming_soon / open) with
  full receipts. This is the only file the widget consumes.
- public/queue.json — locations still at ``signal`` status, for the editor.
  Same shape, kept out of the widget by convention, not secrecy: everything in
  it is already public record.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
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


def _location_dict(location: Location, first_seen: str) -> dict:
    return {
        "key": location.key,
        "status": location.status.value,
        "name": location.name,
        "category": location.category,
        "address": location.address,
        "municipality": location.municipality,
        "note": location.note,
        "opened": location.opened.isoformat() if location.opened else None,
        "first_seen": first_seen,
        "signals": [_signal_dict(s) for s in location.signals],
    }


def _first_seen_index(out_dir: Path) -> dict[str, str]:
    """first_seen per key from the previously built artifacts, if any.

    The date a location first entered a build is carried forward build to
    build (the committed public/ files are the memory), so the editor queue
    can show what arrived since the last visit. Permits surface in monthly
    batches weeks after their issue dates, so signal dates alone can't tell
    "new to us" from "old news". An artifact written before this field
    existed contributes each location's newest signal date instead.
    """
    index: dict[str, str] = {}
    for name in ("locations.json", "queue.json"):
        path = out_dir / name
        if not path.exists():
            continue
        for entry in json.loads(path.read_text(encoding="utf-8"))["locations"]:
            index[entry["key"]] = (entry.get("first_seen")
                                   or max(s["observed"] for s in entry["signals"]))
    return index


def _write(path: Path, locations: list[Location], first_seen: dict[str, str]) -> None:
    ordered = sorted(locations, key=lambda l: l.latest, reverse=True)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "locations": [_location_dict(l, first_seen[l.key]) for l in ordered],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build(locations: list[Location], out_dir: Path,
          today: date | None = None) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = (today or date.today()).isoformat()
    previous = _first_seen_index(out_dir)
    first_seen = {l.key: previous.get(l.key, stamp) for l in locations}
    published = [l for l in locations if l.status is not Status.SIGNAL]
    queue = [l for l in locations if l.status is Status.SIGNAL]
    _write(out_dir / "locations.json", published, first_seen)
    _write(out_dir / "queue.json", queue, first_seen)
    return {"published": len(published), "queue": len(queue)}
