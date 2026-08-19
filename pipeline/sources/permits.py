"""Permit signals from wpr-permit-tracker output.

Contract (see docs/SIGNALS.md for the full extraction spec)
-----------------------------------------------------------
Input:   the parsed permit records wpr-permit-tracker already produces for
         Wausau / Schofield / Rib Mountain.
Keep:    sign permits; new commercial construction; commercial alterations.
         Drop residential and pure-maintenance classes (roofing, HVAC, razing).
Map:     kind      -> SignalKind.SIGN_PERMIT / NEW_COMMERCIAL_CONSTRUCTION /
                      COMMERCIAL_ALTERATION
         id        -> f"permit:{municipality_code}-{permit_number}"
         observed  -> permit issue (or application) date
         summary   -> one line from work description, applicant name included
                      when the permit names a tenant
         receipt   -> {"permit_number": ..., "municipality": ...,
                       "issued": ...}
Address: normalize.normalize_address(site_address, municipality) — let
         AddressError propagate; fixes are alias entries, not code.
"""

from ..models import Signal


def fetch(aliases: dict[str, str]) -> list[Signal]:
    raise NotImplementedError("wire to wpr-permit-tracker output; see docstring")
