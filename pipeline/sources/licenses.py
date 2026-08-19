"""Alcohol-license signals from Wausau Public Health & Safety Committee agendas.

Wiring decision (2026-08-19)
----------------------------
docs/SIGNALS.md assumed these agenda items were available from what
marathon-meetings ingests. In practice marathon-meetings commits only
AI-condensed summaries (item text is rewritten, license items are batched)
plus CivicClerk sidecars for the minority of meetings that get a processed
video — one PHS meeting out of five this summer. Too sparse and too lossy for
deterministic extraction, so this adapter reads the same public CivicClerk
OData API that marathon-meetings itself uses (see its fetch_civicclerk_data):

    GET /v1/Events    — PHS committee meetings since BACKFILL_START
    GET /v1/Meetings/{agendaId} — verbatim agenda item text

What the real agendas contain (checked against all five May-Aug 2026 PHS
meetings, committed as tests/fixtures/civicclerk_phs_2026.json):

- NEW Class A/B applications are batched under a single "Approval or denial
  of various license applications" item; the individual applications exist
  only in attached PDFs. There is nothing to extract from item text, so the
  spec's "Application for a Class 'B' ... d/b/a ..." pattern never appears.
- The items that DO name a business and a premises address are the two kept
  patterns below — and both are strong coming-soon signals.

Keep:    - "Alcohol Beverage License Transfer ... to new location at <addr>"
           (a licensed bar/restaurant moving into a new building)
         - "90 day extension to open for business ... located at <addr>"
           (licensed but not yet open)
Drop:    renewals, operator/bartender licenses, agent changes, temporary
         Class B picnic licenses, "temporary extension of premise", and the
         batched "various license applications" item (no per-application
         text). Silent drops are fine here; a KEPT pattern that then fails
         to parse raises — never guess an address into the merge.
Map:     kind      -> SignalKind.ALCOHOL_LICENSE_APPLICATION
         id        -> f"license:wausau-{event_id}-{outline}" (e.g. ...-6.c)
         observed  -> meeting date
         summary   -> one line naming the business and applicant
         receipt   -> {"body": ..., "meeting_date": ..., "agenda_item": ...,
                       "applicant": ..., "trade_name": ...}
         url       -> the CivicClerk portal event page
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from urllib.parse import quote

from ..models import Signal, SignalKind, Source
from . import get_json, resolve_key

__all__ = ["fetch", "extract_signals", "BACKFILL_START"]

API = "https://wausauwi.api.civicclerk.com/v1"
BODY = "Public Health & Safety Committee"
MUNICIPALITY = "Wausau"
BACKFILL_START = date(2026, 5, 18)  # first tracked PHS meeting (~90-day backfill)
# Agendas post ~a week before the meeting, and that lead time IS the story:
# a posted agenda is already a public record, so upcoming meetings within
# this window are ingested too. ``observed`` stays the meeting date.
LOOKAHEAD_DAYS = 14

_TAGS = re.compile(r"<[^>]+>")
_JUNK = re.compile("[\u200b\u200c\ufeff]")  # zero-width chars in CivicClerk text
_WS = re.compile(r"\s+")

_TRANSFER = re.compile(
    r"Alcohol Beverage License Transfer of the (?P<klass>.+?) for "
    r"(?P<trade>.+?) currently located at .+? to new location at "
    r"(?P<addr>[^,]+),\s*(?P<applicant>[^,]+)",
    re.IGNORECASE,
)
_EXTENSION = re.compile(
    r"extension to open for business for good cause for "
    r"(?P<trade>.+?) located at (?P<addr>[^,]+),\s*(?P<applicant>[^,]+)",
    re.IGNORECASE,
)
# Cheap triggers: an item matching one of these MUST parse, or we raise.
_TRANSFER_TRIGGER = re.compile(r"to new location at", re.IGNORECASE)
_EXTENSION_TRIGGER = re.compile(r"extension to open for business", re.IGNORECASE)

_ROLE_SUFFIX = re.compile(r"\s+(owners?|agents?)$", re.IGNORECASE)


def _clean(name: str) -> str:
    return _WS.sub(" ", _JUNK.sub("", _TAGS.sub("", name.replace("\xa0", " ")))).strip()


def _walk(items: list[dict], prefix: str = ""):
    for item in items:
        outline = item.get("agendaObjectItemOutlineNumber", "") or ""
        path = f"{prefix}.{outline}" if prefix else outline
        yield path, _clean(item.get("agendaObjectItemName", "") or "")
        yield from _walk(item.get("childItems", []) or [], path)


def extract_signals(event_id: int, meeting_date: date, url: str,
                    items: list[dict], aliases: dict[str, str]) -> list[Signal]:
    signals = []
    for outline, text in _walk(items):
        if _TRANSFER_TRIGGER.search(text):
            match = _TRANSFER.search(text)
            what = "license transfer to a new location"
        elif _EXTENSION_TRIGGER.search(text):
            match = _EXTENSION.search(text)
            what = "extension to open for business"
        else:
            continue
        if match is None:
            raise ValueError(
                f"PHS agenda item {event_id}-{outline} looks like a "
                f"{what} but didn't parse: {text!r}"
            )

        trade = match["trade"].strip()
        applicant = _ROLE_SUFFIX.sub("", match["applicant"].strip())
        label = ("License transfer to new location"
                 if what.startswith("license") else
                 "Extension to open for business")
        signals.append(Signal(
            id=f"license:wausau-{event_id}-{outline}",
            location_key=resolve_key(match["addr"].strip(), MUNICIPALITY, aliases),
            source=Source.LICENSE,
            kind=SignalKind.ALCOHOL_LICENSE_APPLICATION,
            observed=meeting_date,
            summary=f"{label}: {trade} ({applicant})",
            receipt={
                "body": f"Wausau {BODY}",
                "meeting_date": meeting_date.isoformat(),
                "agenda_item": f"{outline}: {text}",
                "applicant": applicant,
                "trade_name": trade,
            },
            url=url,
        ))
    return signals


def _events():
    """All PHS meetings from BACKFILL_START through today, paged."""
    odata_filter = quote(f"startDateTime ge {BACKFILL_START.isoformat()}T00:00:00Z")
    url = f"{API}/Events?$filter={odata_filter}&$orderby=startDateTime"
    while url:
        page = get_json(url)
        yield from page["value"]
        url = page.get("@odata.nextLink")


def wanted(event: dict, today: date) -> bool:
    """PHS meetings with a published agenda, up to LOOKAHEAD_DAYS ahead."""
    if not event["eventName"].startswith(BODY) or not event.get("agendaId"):
        return False
    meeting_date = date.fromisoformat(event["startDateTime"][:10])
    return meeting_date <= today + timedelta(days=LOOKAHEAD_DAYS)


def fetch(aliases: dict[str, str]) -> list[Signal]:
    signals = []
    for event in _events():
        if not wanted(event, date.today()):
            continue
        meeting = get_json(f"{API}/Meetings/{event['agendaId']}")
        signals.extend(extract_signals(
            event_id=event["id"],
            meeting_date=date.fromisoformat(event["startDateTime"][:10]),
            url=f"https://wausauwi.portal.civicclerk.com/event/{event['id']}/overview",
            items=meeting.get("items", []),
            aliases=aliases,
        ))
    return signals
