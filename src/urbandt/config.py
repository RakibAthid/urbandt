"""
Constants and default parameters used across the pipeline.

These are the values used in the Twekkelerveld thesis. They are exposed here
so any downstream user can override them for their own neighbourhood without
patching the source.
"""

# === CRS ===================================================================
CRS_RD = "EPSG:28992"   # Dutch RD New — mandatory for all *internal* layers
CRS_WGS = "EPSG:4326"   # WGS-84 — required by CesiumJS dashboards
CRS_WEB = "EPSG:3857"   # WebMercator — only used for contextily basemaps
CRS_RD_NAP = "EPSG:7415"  # RD New + NAP — what 3D BAG tiles arrive in

# === Energy conversion factors ============================================
# These are the values used by the Twekkelerveld pipeline. Override per region.
GAS_KWH_PER_M3 = 8.8     # average net calorific value of Dutch natural gas
CO2_KG_PER_M3_GAS = 1.79 # CO2 emission factor for natural gas combustion
EF_ELEC_KG_PER_KWH = 0.35  # Dutch grid electricity emission factor (2022-ish)

# === PV scenario defaults ==================================================
DEFAULT_PV_FACTOR = 1.0    # 1.0 = 100% of technical PV potential is used
PV_COVERAGE_CAP = 2.0      # cap PV coverage ratio at 200% (anything above is unrealistic)

# === Tree CO2 sequestration (CHM allometric) ==============================
# Simple quadratic allometric model used in the thesis: co2_kg = a * h^2
TREE_CO2_COEF = 0.55           # kg CO2 per m^2 of tree height squared
TREE_MIN_HEIGHT_M = 3.0        # ignore canopy < 3 m (shrubs / hedges)
TREE_DETECT_GAUSSIAN_SIGMA = 1 # CHM smoothing kernel
TREE_DETECT_WINDOW = 5         # local-maxima window size (pixels)

# === Default field/column names ===========================================
# Used by the IO layer when normalising input data. Override if needed.
BAG_ID_CANDIDATES = [
    "identificatie", "pand_id_1", "pand_id", "bag_id", "BAG_ID",
    "b3_bag_pand_id", "b3_bag_id",
]
AREA_FIELD = "oppervlakte_sum"     # building floor area (m^2)
BUILD_YEAR_FIELD = "bouwjaar"
