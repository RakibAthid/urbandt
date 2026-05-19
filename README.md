# urbandt — Urban Digital Twin toolkit

A small, reproducible Python library that turns Dutch open geodata
(BAG, BGT, CBS, Enexis, Zonnedakje, KNMI, 3D BAG / CityJSON, Landsat thermal)
into a neighbourhood-scale digital-twin dashboard.

This package is the generalised pipeline behind the **Twekkelerveld Digital
Twin** prototype — an MSc thesis at the Faculty of Geo-Information Science
and Earth Observation (ITC), University of Twente.

> Status: **research-preview / 0.1.0**. The API is stable enough for thesis
> reproduction, but expect breaking changes before 1.0.

---

## What you get

Three composable building blocks plus a viewer:

| Module | Reproduces | Inputs |
|---|---|---|
| `StudyArea` | Loads building footprints, AOI, CRS hygiene | BAG pand .gpkg |
| `EnergyModule` | EUI, PV potential, PV scenarios, CO2 reduction | Enexis xlsx + Zonnedakje gpkg |
| `EcologyModule` | UHI rural baseline (KNMI), tree-canopy CO2 storage (CHM) | KNMI uurgeg .txt + CHM .tif |
| `urbandt.viz.build_dashboard` | Writes a CesiumJS three-tab dashboard (index / energy / ecology) | the three HTML templates |

A `PrivacyMode` enum (`local` / `private` / `public`) controls which fields
are exposed in the exported GeoJSON, mirroring the
*For Local Host / For Private / For Public* folder split used in the thesis.

---

## Install

This package is not on PyPI. Install directly from GitHub:

```bash
pip install git+https://github.com/rakib-athid/urbandt.git
```

Or, for a local checkout (recommended while iterating):

```bash
git clone https://github.com/rakib-athid/urbandt.git
cd urbandt
pip install -e ".[viz,dev]"
```

System dependencies for the geospatial stack (GDAL / PROJ) are pulled in by
`geopandas`, `rasterio`, `fiona`. On Windows the easiest path is **conda**:

```bash
conda create -n urbandt python=3.11 geopandas rasterio fiona shapely pyproj
conda activate urbandt
pip install -e .
```

---

## Quick start — Python API

```python
from urbandt import StudyArea, EnergyModule, EcologyModule
from urbandt.viz import build_dashboard

# 1. Load the neighbourhood
area = StudyArea.from_gpkg("twekkelerveld_pand_aggregated.gpkg",
                           name="Twekkelerveld")

# 2. Energy indicators
EnergyModule(area).compute_all(
    enexis_xlsx="enexis_filtered_final_twekkelerveld.xlsx",
    pv_gpkg="zonnedakje_twekkelerveld_only.gpkg",
    pv_factor=1.0,          # 100% of technical PV potential
)

# 3. Ecology indicators (optional)
eco = EcologyModule(area)
eco.compute_uhi_baseline("uurgeg_290_2021-2030.txt", month="2022-08")
eco.compute_tree_co2("CHM_VegetationOnly_correct.tif")

# 4. Render the three-tab dashboard
build_dashboard(
    area,
    out_dir="./dashboard",
    mode="public",                         # or "private" / "local"
    html_source_dir="./viewer_html",       # the three .html files
    r2_base="https://pub-XXXX.r2.dev",     # blank for local-file mode
)
```

---

## Quick start — CLI

```bash
urbandt build \
    --buildings twekkelerveld_pand_aggregated.gpkg \
    --enexis    enexis_filtered_final_twekkelerveld.xlsx \
    --pv        zonnedakje_twekkelerveld_only.gpkg \
    --knmi      uurgeg_290_2021-2030.txt \
    --chm       CHM_VegetationOnly_correct.tif \
    --templates ./viewer_html \
    --out       ./dashboard \
    --mode      public
```

---

## Pipeline overview

```
                ┌──────────────┐
   BAG pand ──► │  StudyArea   │ ◄── AOI polygon (optional)
                └───────┬──────┘
                        │
            ┌───────────┼────────────┐
            ▼                        ▼
   ┌──────────────┐         ┌────────────────┐
   │ EnergyModule │         │ EcologyModule  │
   │              │         │                │
   │ Enexis xlsx  │         │ KNMI uurgeg    │
   │ Zonnedakje   │         │ CHM raster     │
   │              │         │                │
   │  → EUI       │         │ → UHI baseline │
   │  → PV cov.   │         │ → tree CO2     │
   │  → CO2 redux │         │                │
   └──────┬───────┘         └──────┬─────────┘
          │                        │
          └────────────┬───────────┘
                       ▼
              ┌─────────────────┐
              │  build_dashboard │  →  index.html
              │  (Cesium + JS)   │  →  energy.html
              │  + privacy mode  │  →  ecology.html
              └─────────────────┘  →  config.js
                                    →  buildings.geojson
```

---

## Reproducing the Twekkelerveld thesis result

The default constants in `urbandt.config` are calibrated for the Netherlands
(gas calorific value, Dutch grid CO2 factor, etc.). To reproduce Chapter 4
of the thesis exactly:

```python
area = StudyArea.from_gpkg("twekkelerveld_pand_aggregated.gpkg",
                           name="Twekkelerveld")
EnergyModule(area).compute_all(
    enexis_xlsx="enexis_filtered_final_twekkelerveld.xlsx",
    pv_gpkg="zonnedakje_twekkelerveld_only.gpkg",
)
EcologyModule(area).compute_uhi_baseline(
    "uurgeg_290_2021-2030.txt", month="2022-08", hours=(10, 11),
)
```

Compare the resulting GeoJSON to
`twekkelerveld_buildings_energy_master_wgs84.geojson` to validate.

---

## How the three privacy modes work

| Mode | What is kept | When to use |
|---|---|---|
| `local`   | All input columns | Working on your own machine; Live Server |
| `private` | Drops free-text and personal fields (VBO etc.) | Sharing with named collaborators |
| `public`  | Whitelist: only indicators + bag_id + geometry | Public Cloudflare R2 host |

See `urbandt.privacy` for the exact field lists.

---

## Data assumptions and how to adapt

* **CRS:** all internal layers are in **EPSG:28992** (Dutch RD New).
  Cesium output is reprojected to **EPSG:4326**.
* **Join key:** every layer is joined on a 16-digit numeric BAG pand id.
  Use `urbandt.io.normalize_bag_id` to clean an ID column before joining.
* **Floor area:** the column `oppervlakte_sum` must exist on the buildings
  layer. Override via `urbandt.config.AREA_FIELD`.
* **Allocation method:** Enexis consumption is *area-share allocated* because
  the source is postcode-level. Override `EnergyModule.allocate_demand` if
  you have metered per-building data.
* **Tree CO2 model:** simple allometric `CO2_kg = 0.55 * h²`. Override via
  `urbandt.config.TREE_CO2_COEF` or pass `co2_coef=` to
  `compute_tree_co2`.

For a non-Dutch neighbourhood you'll typically need to substitute the
Enexis-equivalent (a postcode-level annual consumption table) and the BAG
equivalent (an authoritative building register).

---

## What this library does **not** do

* It does not generate the 3D LoD22 mesh. You still need 3D BAG tiles (or
  another CityJSON source) and a clipping step — see `urbandt.solar`
  helpers, which are the building blocks for a custom clipper.
* It does not run UMEP / SOLWEIG. Solar irradiance rasters are pre-computed
  and *referenced* by the dashboard; they are not produced by this package.
* It does not render charts inside Python. The dashboards use Chart.js in
  the browser.

---

## Citing

If this code or pipeline supports your work, please cite the thesis:

> Rakib (2026). *Towards a privacy-aware neighbourhood digital twin —
> integrating energy and ecology indicators for Twekkelerveld, Enschede.*
> MSc Thesis, ITC, University of Twente.

---

## Development

```bash
pip install -e ".[dev]"
pytest -q
ruff check src/
```

---

## License

MIT — see `LICENSE`.
