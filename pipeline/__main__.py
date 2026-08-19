"""Entry point: fetch signals from all sources, merge, build.

    python -m pipeline
"""

from pathlib import Path

from .build import build
from .merge import load_overrides, merge
from .sources import licenses, permits, transfers


def main() -> None:
    signals = [*permits.fetch(), *transfers.fetch(), *licenses.fetch()]
    overrides = load_overrides(Path("data/overrides/locations.yaml"))
    locations = merge(signals, overrides)
    counts = build(locations, Path("public"))
    print(f"published={counts['published']} queue={counts['queue']}")


if __name__ == "__main__":
    main()
