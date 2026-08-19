"""Adapter tests. Extraction runs against real records committed as fixtures
(see tests/fixtures/) — never against invented data."""

import json
from datetime import date
from pathlib import Path

import pytest

from pipeline.models import SignalKind, Source
from pipeline.normalize import AddressError
from pipeline.sources import licenses, resolve_key

FIXTURES = Path(__file__).parent / "fixtures"


# --- resolve_key -------------------------------------------------------------

def test_resolve_key_normalizes():
    assert resolve_key("301 Washington St.", "Wausau", {}) == "301 WASHINGTON ST|WAUSAU"


def test_resolve_key_prefers_raw_variant_alias():
    aliases = {
        "VACANT LAND ON SOUTH MADISON STREET|SPENCER": "S MADISON ST VACANT LAND|SPENCER"
    }
    key = resolve_key("Vacant Land On South Madison Street", "Spencer", aliases)
    assert key == "S MADISON ST VACANT LAND|SPENCER"


def test_resolve_key_unparseable_without_alias_raises():
    with pytest.raises(AddressError):
        resolve_key("Vacant Land On South Madison Street", "Spencer", {})


# --- licenses ----------------------------------------------------------------
# Fixture: the five real Wausau PHS agendas, May-Aug 2026, verbatim from the
# CivicClerk API the adapter reads.

def phs_signals():
    meetings = json.loads(
        (FIXTURES / "civicclerk_phs_2026.json").read_text(encoding="utf-8"))
    signals = []
    for m in meetings:
        event = m["event"]
        signals += licenses.extract_signals(
            event_id=event["id"],
            meeting_date=date.fromisoformat(event["startDateTime"][:10]),
            url=f"https://wausauwi.portal.civicclerk.com/event/{event['id']}/overview",
            items=m["items"],
            aliases={},
        )
    return signals


def test_licenses_extracts_the_four_named_items():
    signals = phs_signals()
    assert [s.id for s in signals] == [
        "license:wausau-2069-6.c",   # Story Cellar transfer to 416 N 3rd St
        "license:wausau-2070-3.b",   # True North #855 extension to open
        "license:wausau-2467-3.b",   # Copper Kettle extension to open
        "license:wausau-2468-3.b",   # Venado Wine Bar transfer to 303 N 3rd St
    ]
    assert all(s.source is Source.LICENSE for s in signals)
    assert all(s.kind is SignalKind.ALCOHOL_LICENSE_APPLICATION for s in signals)


def test_licenses_story_cellar_transfer_maps_new_location():
    story = phs_signals()[0]
    assert story.location_key == "416 N 3RD ST|WAUSAU"
    assert story.observed == date(2026, 5, 18)
    assert story.receipt["trade_name"] == "The Story Cellar"
    assert story.receipt["applicant"] == "The Story Cellar LLC"
    assert story.receipt["body"] == "Wausau Public Health & Safety Committee"


def test_licenses_venado_strips_zero_width_and_role_suffix():
    venado = phs_signals()[3]
    assert venado.location_key == "303 N 3RD ST|WAUSAU"
    assert venado.receipt["trade_name"] == "Venado Wine Bar"
    assert venado.receipt["applicant"] == "Onora Hotels LLC"


def test_licenses_extension_names_not_yet_open_business():
    copper = phs_signals()[2]
    assert copper.location_key == "5512 STEWART AVE|WAUSAU"
    assert copper.summary.startswith("Extension to open for business: "
                                     "The Copper Kettle Steakhouse")


def test_licenses_triggered_item_that_fails_to_parse_raises():
    # Real Story Cellar item text, truncated mid-address — the trigger fires
    # but the full pattern can't parse, which must stop the build.
    truncated = [{
        "agendaObjectItemOutlineNumber": "6",
        "agendaObjectItemName": ("Consider approval or denial of Alcohol "
                                 "Beverage License Transfer of the \"Class C\" "
                                 "Wine License for The Story Cellar currently "
                                 "located at 205 Callon Street, Suite 2 "
                                 "to new location at"),
        "childItems": [],
    }]
    with pytest.raises(ValueError, match="didn't parse"):
        licenses.extract_signals(2069, date(2026, 5, 18), "u", truncated, {})
