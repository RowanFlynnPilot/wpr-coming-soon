import json
from datetime import date
from pathlib import Path

import pytest

from pipeline.build import build
from pipeline.merge import GateError, OverrideError, Overrides, load_overrides, merge
from pipeline.models import Signal, SignalKind, Source, Status
from pipeline.normalize import AddressError, normalize_address


def sig(key: str, id: str = "permit:WAU-1", observed: date = date(2026, 8, 1),
        kind: SignalKind = SignalKind.SIGN_PERMIT,
        source: Source = Source.PERMIT) -> Signal:
    return Signal(id=id, location_key=key, source=source, kind=kind,
                  observed=observed, summary="Sign permit issued",
                  receipt={"permit_number": "WAU-2026-001"})


NO_OVERRIDES = Overrides(aliases={}, locations={})


# --- normalize -------------------------------------------------------------

@pytest.mark.parametrize("raw, muni, expected", [
    ("301 Washington St.", "Wausau", "301 WASHINGTON ST|WAUSAU"),
    ("301 washington street", "Wausau", "301 WASHINGTON ST|WAUSAU"),
    ("1300 N. Third Street, Ste 200", "wausau", "1300 N 3RD ST|WAUSAU"),
    ("2200 Grand Avenue #4", "Schofield", "2200 GRAND AVE|SCHOFIELD"),
    ("4000 Rib Mountain Drive", "Rib Mountain", "4000 RIB MOUNTAIN DR|RIB MOUNTAIN"),
    ("500  West   Thomas   St", "Wausau", "500 W THOMAS ST|WAUSAU"),
])
def test_normalize(raw, muni, expected):
    assert normalize_address(raw, muni) == expected


@pytest.mark.parametrize("raw, muni", [
    ("Washington St", "Wausau"),   # no street number
    ("", "Wausau"),
    ("301 Washington St", ""),
    ("R156 County Rd NN", "Marathon"),  # fire-number address: alias it instead
])
def test_normalize_fails_fast(raw, muni):
    with pytest.raises(AddressError):
        normalize_address(raw, muni)


# --- merge -----------------------------------------------------------------

def test_signals_accrue_to_one_location_sorted_by_date():
    key = "301 WASHINGTON ST|WAUSAU"
    later = sig(key, id="transfer:2", observed=date(2026, 8, 10),
                kind=SignalKind.COMMERCIAL_SALE, source=Source.TRANSFER)
    earlier = sig(key, id="permit:WAU-1", observed=date(2026, 8, 1))
    locations = merge([later, earlier], NO_OVERRIDES)
    assert len(locations) == 1
    loc = locations[0]
    assert [s.id for s in loc.signals] == ["permit:WAU-1", "transfer:2"]
    assert loc.status is Status.SIGNAL
    assert loc.address == "301 Washington St"
    assert loc.municipality == "Wausau"


def test_alias_redirects_signal_to_canonical_key():
    overrides = Overrides(
        aliases={"1300 N THIRD ST|WAUSAU": "1300 N 3RD ST|WAUSAU"}, locations={})
    locations = merge([sig("1300 N THIRD ST|WAUSAU"),
                       sig("1300 N 3RD ST|WAUSAU", id="permit:WAU-2")], overrides)
    assert len(locations) == 1
    assert locations[0].key == "1300 N 3RD ST|WAUSAU"
    assert len(locations[0].signals) == 2


def test_override_publishes_location():
    key = "301 WASHINGTON ST|WAUSAU"
    overrides = Overrides(aliases={}, locations={
        key: {"status": "coming_soon", "name": "Example Coffee Co.",
              "category": "restaurant", "note": "Opening in October."}})
    (loc,) = merge([sig(key)], overrides)
    assert loc.status is Status.COMING_SOON
    assert loc.name == "Example Coffee Co."


def test_gate_status_without_name_raises():
    key = "301 WASHINGTON ST|WAUSAU"
    overrides = Overrides(aliases={}, locations={key: {"status": "coming_soon"}})
    with pytest.raises(GateError):
        merge([sig(key)], overrides)


def test_suppress_drops_location():
    key = "123 GRAND AVE|SCHOFIELD"
    overrides = Overrides(aliases={}, locations={key: {"suppress": True}})
    assert merge([sig(key)], overrides) == []


def test_orphaned_override_raises():
    overrides = Overrides(aliases={}, locations={
        "999 NOWHERE ST|WAUSAU": {"status": "open", "name": "Ghost"}})
    with pytest.raises(OverrideError):
        merge([sig("301 WASHINGTON ST|WAUSAU")], overrides)


def test_signal_requires_receipt():
    with pytest.raises(ValueError):
        Signal(id="permit:x", location_key="1 A ST|WAUSAU",
               source=Source.PERMIT, kind=SignalKind.SIGN_PERMIT,
               observed=date(2026, 8, 1), summary="s", receipt={})


# --- load_overrides validation ----------------------------------------------

def write_yaml(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "locations.yaml"
    path.write_text(text)
    return path


def test_load_overrides_roundtrip(tmp_path):
    path = write_yaml(tmp_path, """
address_aliases:
  "1300 N THIRD ST|WAUSAU": "1300 N 3RD ST|WAUSAU"
locations:
  "301 WASHINGTON ST|WAUSAU":
    status: open
    name: "Example Coffee Co."
    opened: 2026-10-01
""")
    overrides = load_overrides(path)
    assert overrides.aliases["1300 N THIRD ST|WAUSAU"] == "1300 N 3RD ST|WAUSAU"
    assert overrides.locations["301 WASHINGTON ST|WAUSAU"]["opened"] == date(2026, 10, 1)


def test_checked_in_overrides_file_is_valid():
    # The live file must always pass strict validation; every key on both
    # sides of an alias is a location key ("STREET|MUNICIPALITY" form).
    overrides = load_overrides(Path("data/overrides/locations.yaml"))
    assert all("|" in v and "|" in c for v, c in overrides.aliases.items())
    assert all("|" in key for key in overrides.locations)


@pytest.mark.parametrize("text", [
    "aliases: {}",                                              # unknown top-level key
    'locations:\n  "K|W":\n    nickname: "x"',                  # unknown field
    'locations:\n  "K|W":\n    status: opening_soon\n    name: "x"',  # bad status
    'locations:\n  "K|W":\n    status: signal\n    name: "x"',  # signal is not settable
    'locations:\n  "K|W":\n    suppress: true\n    name: "x"',  # suppress must be alone
    'locations:\n  "K|W":\n    status: coming_soon\n    name: "x"\n    opened: 2026-10-01',  # opened needs open
    'locations:\n  "K|W":\n    status: open\n    name: "x"\n    opened: "soon"',  # opened not a date
    'address_aliases:\n  "A|W": "B|W"\n  "B|W": "C|W"',         # alias chain
])
def test_load_overrides_rejects(tmp_path, text):
    with pytest.raises(OverrideError):
        load_overrides(write_yaml(tmp_path, text))


# --- build -------------------------------------------------------------------

def test_build_splits_published_and_queue(tmp_path):
    confirmed_key = "301 WASHINGTON ST|WAUSAU"
    pending_key = "2200 GRAND AVE|SCHOFIELD"
    overrides = Overrides(aliases={}, locations={
        confirmed_key: {"status": "coming_soon", "name": "Example Coffee Co."}})
    locations = merge([sig(confirmed_key), sig(pending_key, id="permit:SCH-1")],
                      overrides)

    counts = build(locations, tmp_path)
    assert counts == {"published": 1, "queue": 1}

    published = json.loads((tmp_path / "locations.json").read_text())
    assert "generated" in published
    (entry,) = published["locations"]
    assert entry["name"] == "Example Coffee Co."
    assert entry["status"] == "coming_soon"
    assert entry["signals"][0]["receipt"] == {"permit_number": "WAU-2026-001"}

    queue = json.loads((tmp_path / "queue.json").read_text())
    assert queue["locations"][0]["key"] == pending_key
    assert queue["locations"][0]["name"] is None
