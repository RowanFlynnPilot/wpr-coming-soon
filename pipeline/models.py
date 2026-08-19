"""Core data model.

The unit is the LOCATION, not the signal. Scrapers emit Signals keyed to a
normalized address; merge() accrues them into Locations; the editor promotes
a Location through the lifecycle via data/overrides/locations.yaml.

Lifecycle (one direction, editor-driven):

    signal  ->  coming_soon  ->  open
    (internal)  (published)      (published)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class Source(str, Enum):
    PERMIT = "permit"      # wpr-permit-tracker
    TRANSFER = "transfer"  # wpr-property-transactions
    LICENSE = "license"    # marathon-meetings agenda items


class SignalKind(str, Enum):
    SIGN_PERMIT = "sign_permit"
    NEW_COMMERCIAL_CONSTRUCTION = "new_commercial_construction"
    COMMERCIAL_ALTERATION = "commercial_alteration"
    COMMERCIAL_SALE = "commercial_sale"
    ALCOHOL_LICENSE_APPLICATION = "alcohol_license_application"


class Status(str, Enum):
    SIGNAL = "signal"            # internal only — never rendered publicly
    COMING_SOON = "coming_soon"  # editor-confirmed, published
    OPEN = "open"                # published


@dataclass(frozen=True)
class Signal:
    """One observation from one source, pinned to a normalized address.

    ``receipt`` is the proof shown to readers (permit number, transfer doc
    number, agenda item reference). Every published entry shows its receipts —
    that is the product's differentiator, so a Signal without one is invalid.
    """

    id: str                  # stable, source-prefixed: "permit:WAU-2026-00123"
    location_key: str        # normalize.normalize_address() output
    source: Source
    kind: SignalKind
    observed: date
    summary: str             # one human-readable line
    receipt: dict[str, str]
    url: str | None = None

    def __post_init__(self) -> None:
        if not self.receipt:
            raise ValueError(f"signal {self.id}: empty receipt")


@dataclass
class Location:
    """An address accruing signals. Curated fields are set ONLY from overrides."""

    key: str
    address: str             # display form, derived from key
    municipality: str        # display form, derived from key
    signals: list[Signal] = field(default_factory=list)
    status: Status = Status.SIGNAL
    name: str | None = None
    category: str | None = None
    note: str | None = None
    opened: date | None = None

    @property
    def latest(self) -> date:
        return max(s.observed for s in self.signals)
