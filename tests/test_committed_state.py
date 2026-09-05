"""Offline end-to-end check of what is actually committed.

Runs the committed signals ledger through the committed overrides exactly
as the nightly does after its fetch (no network), so a GateError, an
orphaned override, a removed alias, or a normalize-rule regression fails
in CI at push time instead of at 5 a.m. — when it would also stop the
ledger from being committed.
"""

import json
from pathlib import Path

from pipeline import ledger
from pipeline.build import build
from pipeline.merge import load_overrides, merge

ROOT = Path(__file__).parents[1]


def test_committed_ledger_builds_under_committed_overrides(tmp_path):
    overrides = load_overrides(ROOT / "data/overrides/locations.yaml")
    led = ledger.load(ROOT / "data/signals_ledger.json")
    assert led, "the signals ledger must never be empty"

    signals = ledger.to_signals(led, overrides.aliases)       # AddressError here = alias removed
    locations = merge(signals, overrides)                     # GateError / orphan here
    counts = build(locations, tmp_path)
    assert counts["published"] + counts["queue"] == len(locations)

    built = json.loads((tmp_path / "queue.json").read_text(encoding="utf-8"))
    assert all(l["first_seen"] <= l["last_arrival"] for l in built["locations"])


def test_every_ledger_record_is_complete():
    led = ledger.load(ROOT / "data/signals_ledger.json")
    required = {"source", "kind", "observed", "summary", "receipt", "url",
                "address", "municipality", "first_seen"}
    for signal_id, record in led.items():
        assert required <= set(record), f"{signal_id} is missing {required - set(record)}"
        assert record["receipt"], f"{signal_id} has an empty receipt"
        assert record["first_seen"] <= "2026-12-31"
