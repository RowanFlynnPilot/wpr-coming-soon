"""Deploy-time geo enrichment for the widget (docs/WIDGET.md: geocode at
widget-build time, not in the pipeline).

Joins the deployed copies of locations.json / queue.json against the
wpr-permit-tracker ledger, which already geocodes every permit: a location
gains "lat"/"lon" when one of its permit signals matches a ledger record
with a successful geocode. No geocoding happens here and the committed
public/ files are never touched — this rewrites only the copies shipped
next to the widget build.

    python scripts/enrich_geo.py web/dist/locations.json web/dist/queue.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.sources import get_json                      # noqa: E402
from pipeline.sources.permits import LEDGER_URL            # noqa: E402


def enrich(payload: dict, ledger: dict) -> int:
    """Add lat/lon to locations with a geocoded permit signal; return count."""
    enriched = 0
    for location in payload["locations"]:
        location.setdefault("lat", None)
        location.setdefault("lon", None)
        for signal in location["signals"]:
            if signal["source"] != "permit":
                continue
            record = ledger.get(signal["receipt"]["permit_number"])
            if record and record.get("geocode_status") == "matched":
                location["lat"] = record["lat"]
                location["lon"] = record["lon"]
                enriched += 1
                break
    return enriched


def main(paths: list[str]) -> None:
    if not paths:
        raise SystemExit("usage: enrich_geo.py <locations.json> [more.json ...]")
    ledger = get_json(LEDGER_URL)
    for raw in paths:
        path = Path(raw)
        payload = json.loads(path.read_text(encoding="utf-8"))
        count = enrich(payload, ledger)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"{path}: {count}/{len(payload['locations'])} locations mapped")


if __name__ == "__main__":
    main(sys.argv[1:])
