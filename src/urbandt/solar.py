"""
Solar / CityJSON utilities — clip 3D BAG (LoD22) tiles to an AOI and inject
solar attributes from a CSV.

Direct port of the helpers in
``Idea 2/Solar Calculation/AOI_Clipping/clip_cityjson_aoi_solar.ipynb``,
distilled to a small reusable API.

Heavy operations on the full CityJSON tile (vertex closure, transform handling)
are intentionally left as helpers so the user can build a custom clipper from
them — they are too tile-specific to wrap into a one-shot function safely.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Iterable

import pandas as pd

_SCI_RE = re.compile(r"^[+-]?\d+(\.\d+)?[eE][+-]?\d+$")


def norm_id(x) -> str:
    """Permissive BAG id normaliser used in the solar pipeline.

    Differs slightly from :func:`urbandt.io.normalize_bag_id`: this one returns
    an empty string for missing/invalid inputs rather than None, which is what
    the CityJSON closure algorithm expects.
    """
    if x is None:
        return ""
    s = str(x).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if _SCI_RE.match(s):
        try:
            getcontext().prec = 60
            s = format(Decimal(s), "f").split(".")[0]
        except Exception:
            return ""
    return re.sub(r"\D", "", s)


def find_bag_id(attrs: dict) -> str:
    """Find a BAG id inside a CityObject attributes dict."""
    if not isinstance(attrs, dict):
        return ""
    preferred = [
        "b3_bag_pand_id", "b3_bag_id", "bag_id", "pand_id",
        "identificatie", "id", "uid", "clean_id",
    ]
    for k in preferred:
        if k in attrs and attrs[k] not in (None, ""):
            v = norm_id(attrs[k])
            if v:
                return v
    for k, v in attrs.items():
        kk = str(k).lower()
        if any(t in kk for t in ("bag", "pand", "identif")) or kk in ("uid", "clean_id"):
            vid = norm_id(v)
            if vid:
                return vid
    return ""


def load_solar_csv(
    csv_path: str | Path,
    id_col: str = "identifica",
    solar_col: str = "solar_Ener",
    year_col: str = "bouwjaar",
) -> dict:
    """Read the solar/BAG CSV and return ``{normalised_bag_id: {solar, year}}``.

    Defaults match the column names found in
    ``Twekklerveld_bag_pand.csv``.
    """
    df = pd.read_csv(csv_path, dtype=str)
    lut: dict = {}
    for _, row in df.iterrows():
        nid = norm_id(row.get(id_col))
        if not nid:
            continue
        lut[nid] = {
            solar_col: row.get(solar_col),
            year_col: row.get(year_col),
        }
    return lut


def list_cityjson_pand_ids(cityjson_path: str | Path) -> list[str]:
    """Quick utility: enumerate normalised BAG ids inside a CityJSON tile."""
    with open(cityjson_path, "r", encoding="utf-8") as f:
        cj = json.load(f)
    ids = []
    for oid, obj in cj.get("CityObjects", {}).items():
        nid = norm_id(oid) or find_bag_id(obj.get("attributes", {}))
        if nid:
            ids.append(nid)
    return ids


def collect_closure(cityobjects: dict, seed_ids: set) -> set:
    """Expand a set of CityObject ids to include all parents and children.

    Equivalent to the closure step in the original notebook — needed because a
    BAG pand is usually split into ``building`` parent + ``buildingPart``
    children, and CityJSON references go both ways.
    """
    keep = set(seed_ids)
    changed = True
    while changed:
        changed = False
        for oid in list(keep):
            obj = cityobjects.get(oid)
            if not obj:
                continue
            for child in obj.get("children", []) or []:
                if child not in keep:
                    keep.add(child); changed = True
            for parent in obj.get("parents", []) or []:
                if parent not in keep:
                    keep.add(parent); changed = True
    return keep
