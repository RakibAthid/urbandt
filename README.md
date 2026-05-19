# urbandt — Urban Digital Twin toolkit

A small, reproducible Python library that turns Dutch open geodata
(BAG, BGT, CBS, Enexis, Zonnedakje, KNMI, 3D BAG / CityJSON, Landsat thermal)
into a neighbourhood-scale digital twin dashboard.

This package is the generalised pipeline behind the **Twekkelerveld Digital
Twin** prototype — an MSc thesis at the Faculty of Geo-Information Science
and Earth Observation (ITC), University of Twente.

> **Status:** research preview, version 0.1.0. The API is stable enough for
> thesis reproduction but may change before 1.0.

---

## What you get

| Component | Reproduces | Required inputs |
|---|---|---|
| `StudyArea` | Building footprints, AOI, CRS handling | BAG pand `.gpkg` |
| `EnergyModule` | EUI, PV potential, PV scenarios, CO2 reduction | Enexis `.xlsx` + Zonnedakje `.gpkg` |
| `EcologyModule` | UHI rural baseline (KNMI), tree-canopy CO2 storage (CHM) | KNMI `uurgeg_*.txt` + CHM `.tif` |
| `urbandt.viz.build_dashboard` | Three-tab CesiumJS dashboard (index / energy / ecology) | the three HTML templates |

A `PrivacyMode` enum (`local` / `private` / `public`) controls which fields
are exposed in the exported GeoJSON, mirroring the
*For Local Host / For Private / For Public* folder split used in the thesis.

---

## Install

This package is not on PyPI. Install directly from GitHub:

```bash
pip install git+https://github.com/RakibAthid/urbandt.git
```

For a local checkout (recommended while iterating):

```bash
git clone https://github.com/RakibAthid/urbandt.git
cd urbandt
pip install -e ".[viz,dev]"
```

### Windows / system dependencies

The geospatial stack (GDAL / PROJ / GEOS) is fragile to install with plain
`pip` on Windows. The reliable path is **conda**:

```bash
conda create -n urbandt python=3.11 -y
conda activate urbandt
conda install -c conda-forge geopandas rasterio fiona shapely pyproj openpyxl scipy matplotlib -y
pip install git+https://github.com/RakibAthid/urbandt.git
```

On macOS / Linux, plain `pip install` usually works, but conda is still a
safe choice.

---

## Quick start — Python API

```python
from urbandt import StudyArea, EnergyModule, EcologyModule
from urbandt.viz import build_dashboard

# 1. Load the neighbourhood
area = StudyArea.from_gpkg(
    "twekkelerveld_pand_aggregated.gpkg",
    name="Twekkelerveld",
)

# 2. Energy indicators
EnergyModule(area).compute_all(
    enexis_xlsx="enexis_filtered_final_twekkelerveld.xlsx",
    pv_gpkg="zonnedakje_twekkelerveld_only.gpkg",
    pv_factor=1.0,                          # 100% of technical PV potential
)

# 3. Ecology indicators (optional)
eco = EcologyModule(area)
eco.compute_uhi_baseline("uurgeg_290_2021-2030.txt", month="2022-08")
eco.compute_tree_co2("CHM_VegetationOnly_correct.tif")

# 4. Render the three-tab dashboard
build_dashboard(
    area,
    out_dir="./dashboard",
    mode="public",                          # "private" / "local"
    html_source_dir="./viewer_html",        # the three .html files
    r2_base="https://pub-XXXX.r2.dev",      # blank for local-file mode
)
```

---

## Quick start — command line

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

## Validation against the thesis output

The reference result is `twekkelerveld_buildings_energy_master_wgs84.geojson`
produced during the original thesis work. The library reproduces this file
**numerically identically** for all indicators that survive the public
privacy filter:

| Metric | Library output | Thesis master |
|---|---|---|
| Number of buildings | 1,465 | 1,465 |
| Sum of `EUI_base_kwh_m2` | 231,195 | 231,195 |
| Sum of `pv_kwh_pot` (kWh/yr) | 9,794,010 | 9,794,010 |
| Sum of `pv_coverage_el` | 1,718 | 1,718 |
| Sum of `co2_reduction_kg` | 3,427,904 | 3,427,904 |

To re-run this comparison on your machine, see `examples/reproduce_twekkelerveld.py`.

---

## Three privacy modes

| Mode | What is kept | When to use |
|---|---|---|
| `local`   | All input columns | On your own machine; Live Server |
| `private` | Drops free-text and personally identifying fields (VBO etc.) | Sharing with named collaborators |
| `public`  | Whitelist: indicators + bag_id + geometry only | Public Cloudflare R2 host or GitHub Pages |

See `urbandt.privacy` for the exact field lists.

---

## Data assumptions and how to adapt to another neighbourhood

* **CRS:** all internal layers are in **EPSG:28992** (Dutch RD New).
  Cesium output is reprojected to **EPSG:4326**.
* **Join key:** every layer is joined on a 16-digit numeric BAG pand id.
  Use `urbandt.io.normalize_bag_id` to clean an id column before joining.
* **Floor area:** the column `oppervlakte_sum` must exist on the buildings
  layer. Override via `urbandt.config.AREA_FIELD`.
* **Allocation method:** Enexis consumption is *area-share allocated* because
  the source is postcode-level. Override `EnergyModule.allocate_demand` if
  you have metered per-building data.
* **Tree CO2 model:** simple allometric `CO2_kg = 0.55 * h^2`. Override via
  `urbandt.config.TREE_CO2_COEF`.

For a non-Dutch neighbourhood you typically substitute the Enexis-equivalent
(a postcode-level annual consumption table) and the BAG equivalent (an
authoritative building register), then keep everything else.

---

## What this library does NOT do

* Generate the 3D LoD2.2 mesh. You still need 3D BAG tiles (or another
  CityJSON source) and a clipping step — see the helpers in
  `urbandt.solar`.
* Run UMEP / SOLWEIG. Solar irradiance rasters are pre-computed externally
  and referenced by the dashboard; the library does not produce them.
* Render charts inside Python. The dashboards use Chart.js in the browser.

---

## Citing

If this code or pipeline supports your work, please cite:

> Athid, R. (2026). *Towards a privacy-aware neighbourhood digital twin:
> integrating energy and ecology indicators for Twekkelerveld, Enschede.*
> MSc Thesis, Faculty of Geo-Information Science and Earth Observation (ITC),
> University of Twente.

A machine-readable `CITATION.cff` is included in the repo root, so GitHub
displays a "Cite this repository" button.

---

## Development

```bash
git clone https://github.com/RakibAthid/urbandt.git
cd urbandt
pip install -e ".[dev]"
pytest -q
```

Contributions are welcome — open an issue at
https://github.com/RakibAthid/urbandt/issues before sending a pull request.

---

## License

MIT — see `LICENSE`.

---

## Acknowledgements

Developed at the Faculty of Geo-Information Science and Earth Observation
(ITC), University of Twente, as part of the MSc thesis project on
neighbourhood-scale digital twins. Data sources: **Kadaster** (BAG, BGT,
3D BAG), **CBS**, **Enexis**, **Zonnedakje**, **KNMI**, **USGS Landsat**.
