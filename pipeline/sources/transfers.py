"""Property-sale signals from wpr-property-transactions output.

Contract (see docs/SIGNALS.md for the full extraction spec)
-----------------------------------------------------------
Input:   the DOR TAP transfer-return records wpr-property-transactions
         already scrapes for Marathon County.
Keep:    commercial property classes only. Drop residential, ag, and
         intra-family / nominal-consideration transfers (< $1,000).
Map:     kind      -> SignalKind.COMMERCIAL_SALE
         id        -> f"transfer:{document_number}"
         observed  -> conveyance date
         summary   -> "Sold for $X to <grantee>"
         receipt   -> {"document_number": ..., "grantor": ..., "grantee": ...,
                       "consideration": ...}
Address: normalize.normalize_address(property_address, municipality).
"""

from ..models import Signal


def fetch(aliases: dict[str, str]) -> list[Signal]:
    raise NotImplementedError(
        "wire to wpr-property-transactions output; see docstring"
    )
