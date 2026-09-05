"""Signals ledger — accrue-only memory across nightly runs. Exercised with
real permit records from the committed fixture."""

import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from pipeline import ledger
from pipeline.sources import permits

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2026, 9, 5)


def fresh_signals(aliases=None):
    records = json.loads(
        (FIXTURES / "permit_ledger_sample.json").read_text(encoding="utf-8"))
    return permits.signals_from_ledger(records, aliases or {})


def test_merge_stamps_first_seen_and_counts_new():
    led = {}
    assert ledger.merge(led, fresh_signals(), TODAY) == 4
    assert all(r["first_seen"] == "2026-09-05" for r in led.values())
    assert ledger.merge(led, fresh_signals(), date(2026, 9, 6)) == 0
    assert all(r["first_seen"] == "2026-09-05" for r in led.values())


def test_signals_outlive_the_source_forgetting_them():
    led = {}
    ledger.merge(led, fresh_signals(), TODAY)
    ledger.merge(led, [], date(2026, 10, 1))          # source came back empty
    assert len(ledger.to_signals(led, {})) == 4
    (parker,) = [s for s in ledger.to_signals(led, {}) if s.id == "permit:WAU-202607376"]
    assert parker.first_seen == TODAY
    assert parker.location_key == "2510 STEWART AVE|WAUSAU"


def test_wording_and_dates_update_without_a_halt_but_the_place_may_not_change():
    led = {}
    ledger.merge(led, fresh_signals(), TODAY)
    (sign,) = [s for s in fresh_signals() if s.id == "permit:WAU-202604904"]
    # Reworded, and (as a rescheduled meeting would) re-dated: updates in place.
    ledger.merge(led, [replace(sign, summary="Lit channel letters (revised)",
                               observed=date(2026, 5, 9))], TODAY)
    assert led["permit:WAU-202604904"]["summary"] == "Lit channel letters (revised)"
    assert led["permit:WAU-202604904"]["observed"] == "2026-05-09"
    assert led["permit:WAU-202604904"]["first_seen"] == "2026-09-05"
    with pytest.raises(ValueError, match="conflict"):
        ledger.merge(led, [replace(sign, address="1 ELSEWHERE ST")], TODAY)


def test_future_signals_are_provisional_past_ones_are_permanent():
    led = {}
    (sign,) = [s for s in fresh_signals() if s.id == "permit:WAU-202604904"]
    upcoming = replace(sign, id="license:wausau-2469-3.b", observed=date(2026, 9, 21))
    ledger.merge(led, [sign, upcoming], TODAY)
    assert set(led) == {sign.id, upcoming.id}
    # The source stops reporting both: the future one is withdrawn, the past
    # one is history.
    ledger.merge(led, [], date(2026, 9, 10))
    assert set(led) == {sign.id}
    # Once its date has passed, an item that vanishes upstream still stays.
    ledger.merge(led, [upcoming], date(2026, 9, 10))
    ledger.merge(led, [], date(2026, 9, 22))
    assert set(led) == {sign.id, upcoming.id}


def test_keys_are_rederived_so_aliases_stay_retroactive():
    led = {}
    ledger.merge(led, fresh_signals(), TODAY)
    before = {s.id: s.location_key for s in ledger.to_signals(led, {})}
    assert before["permit:WAU-202604904"] == "2620 STEWART AVE|WAUSAU"
    # A raw-variant alias added after ingest re-keys the ledgered signal:
    # the ledger stores "2620 STEWART AVE" + "Wausau", not the key.
    after = {s.id: s.location_key for s in ledger.to_signals(
        led, {"2620 STEWART AVE|WAUSAU": "2600 STEWART AVE|WAUSAU"})}
    assert after["permit:WAU-202604904"] == "2600 STEWART AVE|WAUSAU"


def test_roundtrip_through_disk(tmp_path):
    led = {}
    ledger.merge(led, fresh_signals(), TODAY)
    path = tmp_path / "signals_ledger.json"
    ledger.save(led, path)
    assert ledger.load(path) == led
    assert ledger.load(tmp_path / "missing.json") == {}


def test_signal_without_raw_address_cannot_be_ledgered():
    (sign,) = [s for s in fresh_signals() if s.id == "permit:WAU-202604904"]
    with pytest.raises(ValueError, match="no raw address"):
        ledger.merge({}, [replace(sign, address="")], TODAY)
