"""Alcohol-license signals from marathon-meetings agenda items.

Contract (see docs/SIGNALS.md for the full extraction spec)
-----------------------------------------------------------
Input:   agenda items marathon-meetings already ingests (Wausau Public Health
         & Safety Committee and the equivalent bodies in other
         municipalities).
Keep:    NEW Class A / Class B beer and liquor license applications only.
         Drop renewals, operator (bartender) licenses, agent changes, and
         temporary Class B picnic licenses.
Map:     kind      -> SignalKind.ALCOHOL_LICENSE_APPLICATION
         id        -> f"license:{meeting_id}-{item_index}"
         observed  -> meeting date
         summary   -> "Class B application: <trade name> (<applicant>)"
         receipt   -> {"body": ..., "meeting_date": ..., "agenda_item": ...,
                       "applicant": ..., "trade_name": ...}
Address: the premises address from the agenda item text via
         normalize.normalize_address().
"""

from ..models import Signal


def fetch() -> list[Signal]:
    raise NotImplementedError("wire to marathon-meetings items; see docstring")
