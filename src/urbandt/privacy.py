"""
Privacy modes for dashboard exports.

Your three HTML folders ("For Local Host", "For Public", "For Private") differ
mainly in *which fields* are exposed in the GeoJSON. This module encodes that
distinction so callers can pick a mode and get a correctly-filtered GeoDataFrame.

Defaults are conservative — anything not in PUBLIC_FIELDS is dropped for
mode=public. Override per project.
"""
from __future__ import annotations

from enum import Enum
from typing import Iterable


class PrivacyMode(str, Enum):
    LOCAL = "local"      # everything — for your own machine / Live Server
    PRIVATE = "private"  # restricted-share — full detail, but for trusted viewers
    PUBLIC = "public"    # anonymised — no per-occupant data


# Always kept regardless of mode (the dashboard needs them).
ESSENTIAL_FIELDS = {
    "bag_id", "geometry",
    "oppervlakte_sum", "bouwjaar",
    "EUI_base_kwh_m2", "EUI_net_pv_kwh_m2",
    "pv_kwh_pot", "pv_coverage_el",
    "co2_total_base_kg", "co2_reduction_kg",
}

# Allowed in public exports (aggregate-only / non-identifying).
PUBLIC_FIELDS = ESSENTIAL_FIELDS | {
    "dak_opp_m2", "dak_opp_geschikt_m2",
    "EUI_el_kwh_m2", "EUI_gas_kwh_m2",
    "pv_panels_pot",
}

# Things to strip in private mode (free-text / personally identifying).
PRIVATE_STRIP = {
    "rdf_seealso", "vbo_oppervlakte", "vbo_status", "vbo_gebruiksdoel",
    "vbo_bouwjaar",
}


def apply_privacy(gdf, mode: str | PrivacyMode, extra_keep: Iterable[str] = ()):
    """
    Return a copy of *gdf* filtered for the chosen :class:`PrivacyMode`.

    Parameters
    ----------
    gdf : GeoDataFrame
    mode : "local" | "private" | "public" | PrivacyMode
    extra_keep : iterable of str
        Field names to retain even in public mode.
    """
    mode = PrivacyMode(mode) if isinstance(mode, str) else mode
    if mode == PrivacyMode.LOCAL:
        return gdf.copy()
    if mode == PrivacyMode.PRIVATE:
        return gdf.drop(
            columns=[c for c in PRIVATE_STRIP if c in gdf.columns],
            errors="ignore",
        ).copy()
    # PUBLIC: whitelist
    keep = set(PUBLIC_FIELDS) | set(extra_keep) | {"geometry"}
    cols = [c for c in gdf.columns if c in keep]
    return gdf[cols].copy()
