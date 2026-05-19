"""
Worked example — reproduce the Twekkelerveld thesis dashboard end-to-end.

This script runs the full urbandt pipeline on the data files from the MSc
thesis prototype and writes a self-contained dashboard folder.

USAGE
-----
1. Edit the DATA_DIR constant below to point at YOUR local copy of the
   thesis "Idea 2" folder. The folder must contain:
       twekkelerveld_pand_aggregated.gpkg
       enexis_filtered_final_twekkelerveld.xlsx
       zonnedakje_twekkelerveld_only.gpkg

2. (Optional) Point TEMPLATE_DIR at a folder with the three HTML viewer
   templates (index.html, energy.html, ecology.html). If left as None, only
   the data files are written, not the viewer.

3. Run:
       python examples/reproduce_twekkelerveld.py

EXPECTED OUTPUT
---------------
The script prints validation stats and writes everything to OUT_DIR. The
emitted GeoJSON should reproduce the indicator columns of
``twekkelerveld_buildings_energy_master_wgs84.geojson`` byte-for-byte (for
all columns not stripped by PrivacyMode.PUBLIC).
"""
from __future__ import annotations

import sys
from pathlib import Path

from urbandt import StudyArea, EnergyModule, EcologyModule
from urbandt.viz import build_dashboard


# === EDIT THESE PATHS FOR YOUR MACHINE ======================================
DATA_DIR = Path(
    r"C:\Users\rakib\OneDrive - University of Twente"
    r"\Desktop\MSc Thesis\Workable Link\DT Prototype\Idea 2"
)
TEMPLATE_DIR = DATA_DIR.parent / "For Public"        # set to None to skip HTML copy
OUT_DIR = DATA_DIR.parent / "urbandt_output"
PRIVACY_MODE = "public"                              # "local" | "private" | "public"
PV_FACTOR = 1.0                                      # share of technical PV potential deployed
# ============================================================================


# --- Required input files (script will tell you which one is missing) ------
REQUIRED = {
    "buildings": DATA_DIR / "twekkelerveld_pand_aggregated.gpkg",
    "enexis":    DATA_DIR / "enexis_filtered_final_twekkelerveld.xlsx",
    "pv":        DATA_DIR / "zonnedakje_twekkelerveld_only.gpkg",
}

# --- Optional inputs --------------------------------------------------------
KNMI_TXT = (
    DATA_DIR
    / "Ecology" / "Tables+KNMI"
    / "uurgeg_290_2021-2030" / "uurgeg_290_2021-2030.txt"
)


def main() -> int:
    # Pre-flight: check required files exist before doing any work
    missing = [name for name, p in REQUIRED.items() if not p.exists()]
    if missing:
        print("ERROR — required input files are missing:")
        for name in missing:
            print(f"  [{name}] {REQUIRED[name]}")
        print("\nEdit DATA_DIR at the top of this script and try again.")
        return 1

    # ---- 1. Study area ------------------------------------------------------
    area = StudyArea.from_gpkg(REQUIRED["buildings"], name="Twekkelerveld")
    print(area)
    print(f"Total floor area: {area.total_floor_area:,.0f} m^2")

    # ---- 2. Energy ----------------------------------------------------------
    EnergyModule(area).compute_all(
        enexis_xlsx=REQUIRED["enexis"],
        pv_gpkg=REQUIRED["pv"],
        pv_factor=PV_FACTOR,
    )

    # ---- 3. Ecology (optional, only if KNMI file is present) ---------------
    if KNMI_TXT.exists():
        eco = EcologyModule(area)
        eco.compute_uhi_baseline(KNMI_TXT, month="2022-08", hours=(10, 11))
        print(f"UHI rural baseline (Aug 2022, 10-11h): "
              f"{eco.uhi_baseline_c:.2f} °C")
    else:
        print(f"KNMI file not found at {KNMI_TXT} — skipping UHI baseline.")

    # ---- 4. Dashboard -------------------------------------------------------
    out = build_dashboard(
        area,
        out_dir=OUT_DIR,
        mode=PRIVACY_MODE,
        html_source_dir=TEMPLATE_DIR if (TEMPLATE_DIR and TEMPLATE_DIR.exists()) else None,
    )

    print("\nDashboard files written:")
    for key, val in out.items():
        print(f"  {key}: {val}")
    print(f"\nDone. Open {OUT_DIR} to inspect the output.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
