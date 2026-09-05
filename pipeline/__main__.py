"""Entry point: fetch signals from all sources, ledger them, merge, build.

    python -m pipeline

Each adapter validates its own feed (an empty feed raises there), so a
quiet upstream breakage can't slip through as "no new signals tonight".
"""

from datetime import date
from pathlib import Path

from . import ledger
from .build import build
from .merge import load_overrides, merge
from .sources import licenses, permits, transfers


def main() -> None:
    overrides = load_overrides(Path("data/overrides/locations.yaml"))
    aliases = overrides.aliases

    fresh = []
    for source in (permits, transfers, licenses):
        fresh.extend(source.fetch(aliases))

    led = ledger.load(ledger.LEDGER_PATH)
    new = ledger.merge(led, fresh, date.today(), aliases)
    ledger.save(led, ledger.LEDGER_PATH)

    locations = merge(ledger.to_signals(led, aliases), overrides)
    counts = build(locations, Path("public"))
    print(f"fetched={len(fresh)} new={new} ledgered={len(led)} "
          f"published={counts['published']} queue={counts['queue']}")


if __name__ == "__main__":
    main()
