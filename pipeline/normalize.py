"""Deterministic address normalization.

One canonical form: ``"<NUMBER> <STREET TOKENS>|<MUNICIPALITY>"``, all upper
case, punctuation stripped, unit/suite dropped, directions and street suffixes
abbreviated to USPS short forms.

    "1300 N. 3rd Street, Ste 200" + "Wausau"  ->  "1300 N 3RD ST|WAUSAU"

There is no fuzzy matching. Anything this module can't normalize raises
AddressError and stops the build — the fix is an ``address_aliases`` entry in
data/overrides/locations.yaml, not looser code here. (Rural Marathon County
fire-number addresses like "R156..." intentionally fail; alias them.)
"""

from __future__ import annotations

import re

__all__ = ["AddressError", "normalize_address"]


class AddressError(ValueError):
    pass


_SUFFIXES = {
    "AVENUE": "AVE", "AV": "AVE",
    "BOULEVARD": "BLVD",
    "CIRCLE": "CIR",
    "COURT": "CT",
    "DRIVE": "DR",
    "HIGHWAY": "HWY",
    "LANE": "LN",
    "PARKWAY": "PKWY",
    "PLACE": "PL",
    "ROAD": "RD",
    "SQUARE": "SQ",
    "STREET": "ST", "STR": "ST",
    "TERRACE": "TER",
    "TRAIL": "TRL",
}

_DIRECTIONS = {"NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W"}

_ORDINALS = {
    "FIRST": "1ST", "SECOND": "2ND", "THIRD": "3RD", "FOURTH": "4TH",
    "FIFTH": "5TH", "SIXTH": "6TH", "SEVENTH": "7TH", "EIGHTH": "8TH",
    "NINTH": "9TH", "TENTH": "10TH",
}

_UNIT_RE = re.compile(r"\s+(?:STE|SUITE|UNIT|APT|#)\s*[\w-]+$")
_LEADING_NUMBER_RE = re.compile(r"^(\d+)\s+(.+)$")


def normalize_address(raw: str, municipality: str) -> str:
    """Return the canonical location key, or raise AddressError."""
    if not raw or not raw.strip():
        raise AddressError("empty address")
    if not municipality or not municipality.strip():
        raise AddressError(f"empty municipality for address {raw!r}")

    text = raw.upper()
    text = re.sub(r"[.,]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = _UNIT_RE.sub("", text)

    match = _LEADING_NUMBER_RE.match(text)
    if match is None:
        raise AddressError(f"no leading street number: {raw!r}")
    number, rest = match.groups()

    tokens = []
    for token in rest.split(" "):
        token = _DIRECTIONS.get(token, token)
        token = _ORDINALS.get(token, token)
        tokens.append(token)
    # Street-type abbreviation is positional: only the final token is the
    # suffix. "Terrace Court" -> "TERRACE CT", never "TER CT".
    tokens[-1] = _SUFFIXES.get(tokens[-1], tokens[-1])

    return f"{number} {' '.join(tokens)}|{municipality.strip().upper()}"
