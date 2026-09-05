"""Shared plumbing for source adapters.

Every adapter is one function, ``fetch(aliases) -> list[Signal]``, where
``aliases`` is the ``address_aliases`` table from the overrides file. Keys are
built with :func:`resolve_key`, which completes the documented
"AddressError -> alias entry" workflow: an address ``normalize_address()``
can't parse (fire numbers, "Vacant Land on ...") stops the build, and the fix
is an ``address_aliases`` entry keyed on the verbatim variant form
``"<RAW UPPERCASED>|<MUNICIPALITY UPPERCASED>"`` (whitespace collapsed).
Exact string lookup only — no fuzzy matching.
"""

from __future__ import annotations

import http.client
import json
import re
import time
import urllib.error
import urllib.request

from ..normalize import normalize_address

__all__ = ["get_json", "resolve_key"]

_UA = "wpr-coming-soon (github.com/RowanFlynnPilot/wpr-coming-soon)"
_WS = re.compile(r"\s+")
_TRANSIENT = (urllib.error.URLError, TimeoutError, ConnectionError,
              http.client.IncompleteRead)


def get_json(url: str, attempts: int = 3):
    """GET a JSON document.

    Transport blips (timeouts, resets, 5xx) are retried a couple of times
    with a short backoff — those are the network's problem, not the data's.
    Anything else (4xx, malformed JSON) and a still-failing third attempt
    stop the build.
    """
    request = urllib.request.Request(
        url, headers={"User-Agent": _UA, "Accept": "application/json"}
    )
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code < 500 or attempt == attempts:
                raise
        except _TRANSIENT:
            if attempt == attempts:
                raise
        time.sleep(2 * attempt)


def resolve_key(raw: str, municipality: str, aliases: dict[str, str]) -> str:
    """Location key for one source record.

    Checks ``aliases`` for the verbatim variant form first, then falls back
    to ``normalize_address()`` and lets AddressError propagate. (Aliases on
    *normalized* keys are applied again in merge(); both lookups read the
    same ``address_aliases`` table.)
    """
    variant = f"{_WS.sub(' ', raw.strip().upper())}|{municipality.strip().upper()}"
    if variant in aliases:
        return aliases[variant]
    return normalize_address(raw, municipality)
