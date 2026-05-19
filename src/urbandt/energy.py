"""
EnergyModule — computes per-building energy indicators following the
Twekkelerveld pipeline (see ``Idea 2/Energy_01.ipynb``).

The math:

    el_kwh   = (area_share) * total_el_kwh        # from Enexis
    gas_m3   = (area_share) * total_gas_m3
    gas_kwh  = gas_m3 * GAS_KWH_PER_M3
    tot_kwh  = el_kwh + gas_kwh
    EUI      = tot_kwh / floor_area               # kWh / m^2 / year

    pv_kwh_used      = pv_kwh_pot * scenario_pv_factor
    el_kwh_net_pv    = max(0, el_kwh - pv_kwh_used)
    EUI_net_pv       = (el_kwh_net_pv + gas_kwh) / floor_area
    pv_coverage_el   = pv_kwh_used / el_kwh                  (capped at 200%)

    co2_elec_base    = el_kwh * EF_ELEC_KG_PER_KWH
    co2_gas          = gas_m3 * CO2_KG_PER_M3_GAS
    co2_total_base   = co2_elec_base + co2_gas
    co2_saved_pv     = pv_kwh_used * EF_ELEC_KG_PER_KWH
    co2_total_after  = co2_total_base - co2_saved_pv
    co2_reduction_%  = co2_saved_pv / co2_total_base

The two main inputs are:

- Enexis postcode-level annual consumption (xlsx with
  ``productsoort``, ``aansluiting_aantal``, ``sja_gemiddeld``).
- Zonnedakje rooftop-PV potential (gpkg with ``BAG_ID``,
  ``Totale_potentie_kwh_per_jaar`` etc.).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from . import config, io as _io
from .study_area import StudyArea


class EnergyModule:
    """
    Computes neighbourhood-allocated energy indicators on a ``StudyArea``.

    The Enexis dataset is *postcode-level*, so consumption is allocated to
    individual buildings proportionally to their floor area (the same method
    used in the thesis). For per-building metered data, override
    ``allocate_demand``.
    """

    # --- column candidates ------------------------------------------------
    ENEXIS_PRODUCT_COL = "productsoort"
    ENEXIS_COUNT_COL = "aansluiting_aantal"
    ENEXIS_USE_COL = "sja_gemiddeld"
    ENEXIS_EL_PATTERN = "el|lek|stroom"
    ENEXIS_GAS_PATTERN = "gas"

    PV_ID_COL = "BAG_ID"
    PV_COLS = {
        "Dak_oppervlakte_m2": "dak_opp_m2",
        "Dak_oppervlakte_geschikt_m2": "dak_opp_geschikt_m2",
        "Potentie_n_panelen": "pv_panels_pot",
        "Totale_potentie_kwh_per_jaar": "pv_kwh_pot",
        "CO2_ton_bespaard_per_jaar": "pv_co2_ton_saving",
    }

    def __init__(self, area: StudyArea):
        self.area = area
        self.totals_: dict = {}
        self._pv_factor: float = config.DEFAULT_PV_FACTOR

    # ------------------------------------------------------------------
    # Step 1 — read Enexis and split electricity vs gas
    # ------------------------------------------------------------------
    def read_enexis(self, xlsx_path: str | Path) -> dict:
        """Load Enexis xlsx and return totals dict {el_kwh, gas_m3}."""
        df = pd.read_excel(xlsx_path)
        df[self.ENEXIS_COUNT_COL] = pd.to_numeric(
            df[self.ENEXIS_COUNT_COL], errors="coerce"
        )
        # Enexis sometimes uses comma as decimal separator
        df[self.ENEXIS_USE_COL] = (
            df[self.ENEXIS_USE_COL].astype(str).str.replace(",", ".")
        )
        df[self.ENEXIS_USE_COL] = pd.to_numeric(
            df[self.ENEXIS_USE_COL], errors="coerce"
        )
        df["row_use"] = df[self.ENEXIS_COUNT_COL] * df[self.ENEXIS_USE_COL]

        el_mask = df[self.ENEXIS_PRODUCT_COL].str.contains(
            self.ENEXIS_EL_PATTERN, case=False, na=False
        )
        gas_mask = df[self.ENEXIS_PRODUCT_COL].str.contains(
            self.ENEXIS_GAS_PATTERN, case=False, na=False
        )

        totals = {
            "el_kwh": float(df.loc[el_mask, "row_use"].sum()),
            "gas_m3": float(df.loc[gas_mask, "row_use"].sum()),
        }
        self.totals_ = totals
        return totals

    # ------------------------------------------------------------------
    # Step 2 — allocate area-share of totals to each building
    # ------------------------------------------------------------------
    def allocate_demand(self, totals: dict | None = None) -> "EnergyModule":
        totals = totals or self.totals_
        if not totals:
            raise RuntimeError("Call read_enexis() first or pass totals=")

        b = self.area.buildings
        area_col = config.AREA_FIELD
        b[area_col] = pd.to_numeric(b[area_col], errors="coerce")
        b = b[b[area_col] > 0].copy()
        total_area = b[area_col].sum()

        b["area_share"] = b[area_col] / total_area
        b["el_kwh"] = b["area_share"] * totals["el_kwh"]
        b["gas_m3"] = b["area_share"] * totals["gas_m3"]
        b["gas_kwh"] = b["gas_m3"] * config.GAS_KWH_PER_M3
        b["co2_gas_kg"] = b["gas_m3"] * config.CO2_KG_PER_M3_GAS
        b["tot_kwh"] = b["el_kwh"] + b["gas_kwh"]

        # EUI baseline
        b["EUI_base_kwh_m2"] = b["tot_kwh"] / b[area_col]
        b["EUI_el_kwh_m2"] = b["el_kwh"] / b[area_col]
        b["EUI_gas_kwh_m2"] = b["gas_kwh"] / b[area_col]

        self.area.buildings = b
        return self

    # ------------------------------------------------------------------
    # Step 3 — merge Zonnedakje rooftop PV potential
    # ------------------------------------------------------------------
    def merge_pv(self, pv_gpkg: str | Path) -> "EnergyModule":
        """Merge per-building PV potential from a Zonnedakje GeoPackage."""
        gdf_pv = _io.load_gpkg(pv_gpkg)
        if gdf_pv is None:
            raise FileNotFoundError(f"Could not read PV potential from {pv_gpkg}")

        keep = ["BAG_ID"] + [c for c in self.PV_COLS if c in gdf_pv.columns]
        df = gdf_pv[keep].copy()
        # rename to clean names
        df = df.rename(columns=self.PV_COLS)
        # normalise BAG id to digits-only
        df["bag_id"] = df["BAG_ID"].apply(_io.normalize_bag_id)
        df = df.drop(columns=["BAG_ID"]).drop_duplicates(subset=["bag_id"])

        # find ID col in buildings
        b = self.area.buildings
        b_id_col = _io.pick_first_existing(b, config.BAG_ID_CANDIDATES)
        if b_id_col is None:
            raise KeyError(
                f"Buildings layer has no recognisable BAG id column. "
                f"Tried: {config.BAG_ID_CANDIDATES}"
            )
        b["bag_id"] = b[b_id_col].apply(_io.normalize_bag_id)

        self.area.buildings = b.merge(df, on="bag_id", how="left")
        return self

    # ------------------------------------------------------------------
    # Step 4 — PV scenarios
    # ------------------------------------------------------------------
    def compute_pv_scenario(self, factor: float = 1.0) -> "EnergyModule":
        """
        Apply a PV deployment scenario. ``factor`` is the share of *technical*
        PV potential actually deployed (1.0 = full potential, 0.5 = half).
        """
        self._pv_factor = factor
        b = self.area.buildings
        area_col = config.AREA_FIELD

        if "pv_kwh_pot" not in b.columns:
            b["pv_kwh_pot"] = 0.0
        b["pv_kwh_pot"] = pd.to_numeric(b["pv_kwh_pot"], errors="coerce").fillna(0)
        b["pv_kwh_used"] = b["pv_kwh_pot"] * factor
        b["el_kwh_net_pv"] = (b["el_kwh"] - b["pv_kwh_used"]).clip(lower=0)
        b["tot_kwh_net_pv"] = b["el_kwh_net_pv"] + b["gas_kwh"]
        b["EUI_net_pv_kwh_m2"] = b["tot_kwh_net_pv"] / b[area_col]

        # PV coverage ratio, capped at 200%
        cov = b["pv_kwh_used"] / b["el_kwh"]
        cov = cov.replace([np.inf, -np.inf], np.nan)
        b["pv_coverage_el"] = cov.clip(lower=0, upper=config.PV_COVERAGE_CAP)

        self.area.buildings = b
        return self

    # ------------------------------------------------------------------
    # Step 5 — CO2 budget + reduction
    # ------------------------------------------------------------------
    def compute_co2(self) -> "EnergyModule":
        b = self.area.buildings
        b["co2_elec_base_kg"] = b["el_kwh"] * config.EF_ELEC_KG_PER_KWH
        b["co2_saved_pv_kg"] = b.get("pv_kwh_used", 0) * config.EF_ELEC_KG_PER_KWH
        if "co2_gas_kg" in b.columns:
            b["co2_total_base_kg"] = b["co2_elec_base_kg"] + b["co2_gas_kg"]
        else:
            b["co2_total_base_kg"] = b["co2_elec_base_kg"]
        b["co2_total_after_pv_kg"] = b["co2_total_base_kg"] - b["co2_saved_pv_kg"]
        b["co2_reduction_kg"] = b["co2_saved_pv_kg"]
        with np.errstate(divide="ignore", invalid="ignore"):
            b["co2_reduction_pct"] = (
                b["co2_reduction_kg"] / b["co2_total_base_kg"]
            ).replace([np.inf, -np.inf], np.nan)
        self.area.buildings = b
        return self

    # ------------------------------------------------------------------
    # Convenience: do it all
    # ------------------------------------------------------------------
    def compute_all(
        self,
        enexis_xlsx: str | Path,
        pv_gpkg: str | Path,
        pv_factor: float = 1.0,
    ) -> "EnergyModule":
        """Run the full energy pipeline end-to-end."""
        self.read_enexis(enexis_xlsx)
        self.allocate_demand()
        self.merge_pv(pv_gpkg)
        self.compute_pv_scenario(factor=pv_factor)
        self.compute_co2()
        return self
