"""Adapter tests. Extraction runs against real records committed as fixtures
(see tests/fixtures/) — never against invented data."""

import pytest

from pipeline.normalize import AddressError
from pipeline.sources import resolve_key


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
