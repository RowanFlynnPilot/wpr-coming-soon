"""Adapter tests. Extraction runs against real records committed as fixtures
(see tests/fixtures/) — never against invented data."""

import json
from datetime import date
from pathlib import Path

import pytest

from pipeline.models import SignalKind, Source
from pipeline.normalize import AddressError
from pipeline.sources import licenses, permits, resolve_key

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


# --- permits -----------------------------------------------------------------
# Fixture: seven real wpr-permit-tracker ledger records — one per kept
# template across all three jurisdictions, plus dropped residential /
# maintenance / unassigned-jurisdiction classes.

def permit_ledger():
    return json.loads(
        (FIXTURES / "permit_ledger_sample.json").read_text(encoding="utf-8"))


def test_permits_keeps_sign_and_commercial_drops_the_rest():
    signals = permits.signals_from_ledger(permit_ledger(), {})
    assert [s.id for s in signals] == [
        "permit:WAU-202604904",   # Sign
        "permit:RIB-202604958",   # Com Building, Rib Mountain
        "permit:SCH-202606400",   # Com Early Start, Schofield
        "permit:WAU-202607376",   # Com Building (Parker Johns BBQ)
    ]
    kinds = {s.id: s.kind for s in signals}
    assert kinds["permit:WAU-202604904"] is SignalKind.SIGN_PERMIT
    assert kinds["permit:SCH-202606400"] is SignalKind.NEW_COMMERCIAL_CONSTRUCTION
    assert kinds["permit:WAU-202607376"] is SignalKind.COMMERCIAL_ALTERATION


def test_permits_mapping_fields():
    parker = [s for s in permits.signals_from_ledger(permit_ledger(), {})
              if s.id == "permit:WAU-202607376"][0]
    assert parker.location_key == "2510 STEWART AVE|WAUSAU"
    assert parker.observed == date(2026, 7, 8)
    assert parker.source is Source.PERMIT
    assert "Parker Johns BBQ" in parker.summary
    assert parker.receipt == {"permit_number": "202607376",
                              "municipality": "Wausau",
                              "issued": "2026-07-08"}
    assert parker.url.startswith("https://www.wausauwi.gov/")


def test_permits_unmapped_jurisdiction_on_kept_template_raises():
    ledger = permit_ledger()
    record = dict(ledger["202604904"], jurisdiction="unassigned")
    with pytest.raises(ValueError, match="unmapped jurisdiction"):
        permits.signals_from_ledger({"202604904": record}, {})


def test_permits_address_city_mismatch_raises():
    ledger = permit_ledger()
    record = dict(ledger["202604904"], address="2620 STEWART AVE, SCHOFIELD")
    with pytest.raises(ValueError, match="expected municipality"):
        permits.signals_from_ledger({"202604904": record}, {})
