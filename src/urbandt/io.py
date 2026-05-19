"""
IO helpers: safe loading, CRS handling, BAG id normalisation, geometry hygiene.

Most of this is lifted from ``GIS_Output/gis_pipeline.py`` and the
``Connect_csv_estimation`` notebook, then generalised.
"""
from __future__ import annotations

import re
from pathlib import Path
from decimal import Decimal, getcontext
from typing import Iterable

import pandas as pd

try:
    import geopandas as gpd
    import fiona
    from shapely.validation import make_valid
    HAS_GPD = True
except ImportError:  # pragma: no cover
    HAS_GPD = False

from . import config

# ---------------------------------------------------------------------------
# BAG id normalisation
# ---------------------------------------------------------------------------
_SCI_RE = re.compile(r"^[+-]?\d+(\.\d+)?[eE][+-]?\d+$")


def normalize_bag_id(x) -> str | None:
    """
    Reduce any messy representation of a Dutch BAG pand id to its 16-digit
    numeric form. Handles:

    - 'NL.IMBAG.Pand.0153100000267845'  -> '0153100000267845'
    - '0153100000267845'                -> '0153100000267845'
    - '1.53E+14'  (scientific notation) -> '153100000267845'
    - NaN / None / empty                -> None
    """
    if x is None:
        return None
    if isinstance(x, float) and pd.isna(x):
        return None
    s = str(x).strip()
    if not s or s.lower() == "nan":
        return None
    s = s.replace("NL.IMBAG.Pand.", "").replace("NL.IMBAG.PAND.", "")
    if s.endswith(".0"):
        s = s[:-2]
    if _SCI_RE.match(s):
        try:
            getcontext().prec = 60
            s = format(Decimal(s), "f").split(".")[0]
        except Exception:
            return None
    digits = re.sub(r"\D", "", s)
    return digits if digits else None


def pick_first_existing(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    """Return the first column name in *candidates* that exists in *df*."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


# ---------------------------------------------------------------------------
# CRS helpers
# ---------------------------------------------------------------------------
def ensure_crs(gdf, target: str = config.CRS_RD):
    """
    Reproject a GeoDataFrame to *target*. Treats EPSG:7415 (RD+NAP) as RD
    since the XY values are identical.
    """
    if not HAS_GPD:
        raise ImportError("geopandas is required for CRS operations")
    target_epsg = int(target.split(":")[1])
    if gdf.crs is None:
        return gdf.set_crs(target)
    current_epsg = gdf.crs.to_epsg()
    if current_epsg == 7415:
        gdf = gdf.set_crs(config.CRS_RD, allow_override=True)
        current_epsg = 28992
    if current_epsg != target_epsg:
        gdf = gdf.to_crs(target)
    return gdf


# ---------------------------------------------------------------------------
# Geometry hygiene
# ---------------------------------------------------------------------------
def fix_geometries(gdf):
    """Drop null/empty geometries; repair invalid ones with shapely.make_valid."""
    gdf = gdf[gdf.geometry.notna()].copy()
    gdf = gdf[~gdf.geometry.is_empty].copy()
    invalid = ~gdf.geometry.is_valid
    if invalid.any():
        gdf.loc[invalid, "geometry"] = gdf.loc[invalid, "geometry"].apply(
            lambda g: make_valid(g) if g is not None else g
        )
    return gdf.reset_index(drop=True)


def dedup_geometries(gdf):
    """Drop duplicate geometries (keep first)."""
    wkts = gdf.geometry.apply(lambda g: g.wkt if g is not None else "")
    dup = wkts.duplicated(keep="first")
    return gdf[~dup].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
def load_gpkg(path: str | Path, layer: str | None = None,
              preferred_layer_keywords: Iterable[str] | None = None):
    """Load first (or named) layer from a GeoPackage. Returns None on error."""
    path = Path(path)
    if not path.exists():
        return None
    avail = fiona.listlayers(str(path))
    if not avail:
        return None
    if layer and layer in avail:
        lyr = layer
    elif preferred_layer_keywords:
        lyr = next(
            (a for a in avail
             for kw in preferred_layer_keywords
             if kw in a.lower()),
            avail[0],
        )
    else:
        lyr = avail[0]
    return gpd.read_file(str(path), layer=lyr)


def clean_columns(gdf, max_len: int = 10):
    """
    Lowercase + safe-ascii rename all columns (geometry preserved).
    Useful before exporting to Shapefile (10-char limit).
    """
    def _clean(name: str) -> str:
        s = str(name).lower().strip()
        s = re.sub(r"[^a-z0-9_]", "_", s)
        s = re.sub(r"_+", "_", s).strip("_")
        return s[:max_len]

    rename, seen = {}, {"geometry"}
    for col in gdf.columns:
        if col == "geometry":
            continue
        new = _clean(col)
        base, i = new, 1
        while new in seen:
            suffix = f"_{i}"
            new = base[:max_len - len(suffix)] + suffix
            i += 1
        rename[col] = new
        seen.add(new)
    return gdf.rename(columns=rename)
