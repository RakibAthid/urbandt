"""
urbandt — Urban Digital Twin toolkit
====================================

A lightweight, reproducible pipeline for building neighbourhood-scale digital
twin dashboards (energy + ecology) from open Dutch geospatial data sources
such as BAG, BGT, CBS, Enexis, Zonnedakje, KNMI uurgegevens, Landsat thermal
and 3D BAG (CityJSON / LoD22).

This package was extracted from the MSc Thesis prototype "Twekkelerveld
Digital Twin" (Rakib, ITC — University of Twente) and generalised so that
other researchers can reproduce or adapt the workflow to a different Dutch
neighbourhood.

High-level entry points
-----------------------
    >>> from urbandt import StudyArea, EnergyModule, EcologyModule
    >>> from urbandt.viz import build_dashboard
    >>>
    >>> area = StudyArea.from_gpkg("my_buildings.gpkg")
    >>> energy = EnergyModule(area).compute_all(
    ...     enexis_xlsx="enexis.xlsx",
    ...     pv_gpkg="zonnedakje.gpkg",
    ... )
    >>> ecology = EcologyModule(area).compute_uhi_baseline(
    ...     knmi_txt="uurgeg_290.txt",
    ...     month="2022-08",
    ... )
    >>> build_dashboard(area, energy=energy, ecology=ecology,
    ...                 mode="public", out_dir="./dashboard")
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
