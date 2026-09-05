"""Entry point: fetch signals from all sources, merge, build.

    python -m pipeline
"""

from pathlib import Path

from .build import build
from .merge import load_overrides, merge
from .sources import licenses, permits, transfers


def main() -> None:
    overrides = load_overrides(Path("data/overrides/locations.yaml"))
    aliases = overrides.aliases
    signals = []
    for source in (permits, transfers, licenses):
        fetched = source.fetch(aliases)
        # Every source has history now (append-only ledgers, a fixed
        # backfill start), so zero signals means the feed broke quietly.
        if not fetched:
            raise RuntimeError(f"{source.__name__} returned no signals")
        signals.extend(fetched)
    locations = merge(signals, overrides)
    counts = build(locations, Path("public"))
    print(f"published={counts['published']} queue={counts['queue']}")


if __name__ == "__main__":
    main()
