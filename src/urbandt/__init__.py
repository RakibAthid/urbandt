"""
urbandt — Urban Digital Twin toolkit
====================================

A lightweight, reproducible pipeline for building neighbourhood-scale
digital-twin dashboards (energy + ecology) from open Dutch geospatial data
sources: BAG, BGT, CBS, Enexis, Zonnedakje, KNMI uurgegevens, 3D BAG /
CityJSON, and Landsat thermal.

This package was extracted from the MSc thesis prototype "Twekkelerveld
Digital Twin" (Rakib Athid, ITC — University of Twente) and generalised so
that other researchers can reproduce or adapt the workflow to a different
neighbourhood.

High-level entry points
-----------------------
::

    from urbandt import StudyArea, EnergyModule, EcologyModule
    from urbandt.viz import build_dashboard

    area = StudyArea.from_gpkg("my_buildings.gpkg")
    EnergyModule(area).compute_all(
        enexis_xlsx="enexis.xlsx",
        pv_gpkg="zonnedakje.gpkg",
    )
    EcologyModule(area).compute_uhi_baseline(
        "uurgeg_290.txt", month="2022-08",
    )
    build_dashboard(area, out_dir="./dashboard",
                    mode="public",
                    html_source_dir="./viewer_html")

Cite
----
If this code supports your work, please cite the MSc thesis (see
``CITATION.cff`` in the repository root).

Repository: https://github.com/RakibAthid/urbandt
License:    MIT
"""

from .study_area import StudyArea
from .energy import EnergyModule
from .ecology import EcologyModule
from .privacy import PrivacyMode, apply_privacy
from . import config

__all__ = [
    "StudyArea",
    "EnergyModule",
    "EcologyModule",
    "PrivacyMode",
    "apply_privacy",
    "config",
]

__version__ = "0.1.0"
__author__ = "Rakib Athid"
__license__ = "MIT"
