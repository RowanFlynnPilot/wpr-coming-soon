"""Accrue signals into locations and apply editorial overrides.

Two responsibilities, two functions:

- load_overrides(): parse and STRICTLY validate data/overrides/locations.yaml.
  Every editor typo (unknown field, bad status, alias chain, contradictory
  entry) raises OverrideError at load time.
- merge(): group signals by (aliased) location key, apply overrides, and
  enforce the editorial gate: a location cannot be published (coming_soon /
  open) without a curated name. Publication happens ONLY through overrides.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

import yaml

from .models import Location, Signal, Status

__all__ = ["GateError", "OverrideError", "Overrides", "load_overrides", "merge"]


class OverrideError(ValueError):
    pass


class GateError(ValueError):
    pass


_TOP_LEVEL_KEYS = {"address_aliases", "locations"}
_LOCATION_KEYS = {"status", "name", "category", "note", "opened", "suppress"}


@dataclass(frozen=True)
class Overrides:
    aliases: dict[str, str]
    locations: dict[str, dict]


def load_overrides(path: Path) -> Overrides:
    data = yaml.safe_load(path.read_text()) or {}

    unknown_top = set(data) - _TOP_LEVEL_KEYS
    if unknown_top:
        raise OverrideError(f"unknown top-level keys: {sorted(unknown_top)}")

    aliases: dict[str, str] = data.get("address_aliases") or {}
    locations: dict[str, dict] = data.get("locations") or {}

    for variant, canonical in aliases.items():
        if canonical in aliases:
            raise OverrideError(
                f"alias chain: {variant!r} -> {canonical!r} -> "
                f"{aliases[canonical]!r}; point both at the canonical key"
            )

    for key, entry in locations.items():
        unknown = set(entry) - _LOCATION_KEYS
        if unknown:
            raise OverrideError(f"{key}: unknown fields {sorted(unknown)}")

        if entry.get("suppress"):
            if set(entry) != {"suppress"}:
                raise OverrideError(
                    f"{key}: suppress must be the only field in the entry"
                )
            continue

        if "status" in entry:
            try:
                status = Status(entry["status"])
            except ValueError:
                raise OverrideError(
                    f"{key}: bad status {entry['status']!r} "
                    f"(use coming_soon or open)"
                ) from None
            if status is Status.SIGNAL:
                raise OverrideError(
                    f"{key}: never set status to signal; delete the field"
                )

        if "opened" in entry:
            if entry.get("status") != Status.OPEN.value:
                raise OverrideError(f"{key}: opened requires status: open")
            if not isinstance(entry["opened"], date):
                raise OverrideError(f"{key}: opened must be a date (YYYY-MM-DD)")

    return Overrides(aliases=aliases, locations=locations)


def merge(signals: Iterable[Signal], overrides: Overrides) -> list[Location]:
    by_key: dict[str, list[Signal]] = defaultdict(list)
    for signal in signals:
        key = overrides.aliases.get(signal.location_key, signal.location_key)
        by_key[key].append(signal)

    orphaned = set(overrides.locations) - set(by_key)
    if orphaned:
        raise OverrideError(
            f"overrides reference locations with no signals: {sorted(orphaned)}"
        )

    locations: list[Location] = []
    for key in sorted(by_key):
        entry = overrides.locations.get(key, {})
        if entry.get("suppress"):
            continue

        number_street, _, municipality = key.partition("|")
        location = Location(
            key=key,
            address=number_street.title(),
            # Title-case, but "TOWN OF X" displays as "Town of X".
            municipality=municipality.title().replace(" Of ", " of "),
            signals=sorted(by_key[key], key=lambda s: (s.observed, s.id)),
            status=Status(entry["status"]) if "status" in entry else Status.SIGNAL,
            name=entry.get("name"),
            category=entry.get("category"),
            note=entry.get("note"),
            opened=entry.get("opened"),
        )

        if location.status is not Status.SIGNAL and not location.name:
            raise GateError(
                f"{key}: status {location.status.value} requires a curated name"
            )

        locations.append(location)

    return locations
