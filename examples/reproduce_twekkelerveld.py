"""
Worked example: reproduce the Twekkelerveld thesis dashboard end-to-end.

Adjust the DATA_DIR constant to point at your local copy of the
"Idea 2" folder, then run:

    python examples/reproduce_twekkelerveld.py
"""
from pathlib import Path

from urbandt import StudyArea, EnergyModule, EcologyModule
from urbandt.viz import build_dashboard

# === EDIT THIS ===============================================================
DATA_DIR = Path(r"C:\Users\rakib\OneDrive - University of Twente"
                r"\Desktop\MSc Thesis\Workable Link\DT Prototype\Idea 2")
TEMPLATE_DIR = DATA_DIR.parent / "For Public"
OUT_DIR = DATA_DIR.parent / "urbandt_output"
# =============================================================================


def main():
    area = StudyArea.from_gpkg(
        DATA_DIR / "twekkelerveld_pand_aggregated.gpkg",
        name="Twekkelerveld",
    )
    print(area)
    print(f"Total floor area: {area.total_floor_area:,.0f} m^2")

    # --- Energy ---
    EnergyModule(area).compute_all(
        enexis_xlsx=DATA_DIR / "enexis_filtered_final_twekkelerveld.xlsx",
        pv_gpkg=DATA_DIR / "zonnedakje_twekkelerveld_only.gpkg",
        pv_factor=1.0,
    )

    # --- Ecology (optional) ---
    knmi = DATA_DIR / "Ecology" / "Tables+KNMI" / "uurgeg_290_2021-2030" / "uurgeg_290_2021-2030.txt"
    if knmi.exists():
        eco = EcologyModule(area)
        eco.compute_uhi_baseline(knmi, month="2022-08", hours=(10, 11))
        print(f"UHI rural baseline (Aug 2022, 10-11h): {eco.uhi_baseline_c:.2f} °C")

    # --- Dashboard ---
    out = build_dashboard(
        area,
        out_dir=OUT_DIR,
        mode="public",
        html_source_dir=TEMPLATE_DIR if TEMPLATE_DIR.exists() else None,
    )
    print("\nDashboard files written:")
    for k, v in out.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
