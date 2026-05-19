"""
Very small smoke tests — verify the package imports cleanly and that the
pure-Python helpers behave correctly (no GIS data needed).
"""
import pytest

import urbandt
from urbandt import config
from urbandt.io import normalize_bag_id, pick_first_existing
from urbandt.privacy import PrivacyMode, apply_privacy
from urbandt.solar import norm_id, find_bag_id


def test_version():
    assert urbandt.__version__


def test_constants():
    assert config.GAS_KWH_PER_M3 == pytest.approx(8.8)
    assert config.CRS_RD == "EPSG:28992"
    assert config.CRS_WGS == "EPSG:4326"


@pytest.mark.parametrize("inp,expected", [
    ("NL.IMBAG.Pand.0153100000267845", "0153100000267845"),
    ("0153100000267845", "0153100000267845"),
    ("1.53E+14",         "153000000000000"),
    (None,               None),
    ("",                 None),
])
def test_normalize_bag_id(inp, expected):
    assert normalize_bag_id(inp) == expected


def test_solar_norm_id_returns_empty_string_for_missing():
    assert norm_id(None) == ""
    assert norm_id("") == ""


def test_find_bag_id_prefers_b3_keys():
    attrs = {"b3_bag_pand_id": "NL.IMBAG.Pand.0001", "junk": "x"}
    assert find_bag_id(attrs) == "0001"


def test_privacy_mode_enum():
    assert PrivacyMode("public") == PrivacyMode.PUBLIC
    assert PrivacyMode("private") == PrivacyMode.PRIVATE
    assert PrivacyMode("local") == PrivacyMode.LOCAL


def test_pick_first_existing():
    import pandas as pd
    df = pd.DataFrame({"a": [1], "b": [2]})
    assert pick_first_existing(df, ["x", "b", "a"]) == "b"
    assert pick_first_existing(df, ["x"]) is None
