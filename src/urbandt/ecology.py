"""
EcologyModule — ecology / climate indicators.

Two pieces of logic are ported directly from your notebooks:

1. UHI rural baseline (KNMI uurgegevens)
   - reads the KNMI hourly station file (e.g. station 290 = Twenthe)
   - picks a daytime window (default 10:00 + 11:00 UTC, August)
   - returns mean rural temperature, used as the rural baseline against which
     urban LST anomalies are computed.
   (port of: Idea 2/Ecology/UHI_ruarl_baseline.ipynb)

2. Tree CO2 sequestration from a Canopy Height Model (CHM)
   - detects tree-tops as local maxima > MIN_HEIGHT
   - estimates CO2 storage per tree using a simple quadratic allometric model
   (port of: Idea 2/Ecology/Preprocessed/BGT/CO2_Sequestration.ipynb)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from . import config
from .study_area import StudyArea


class EcologyModule:
    """Compute UHI baseline and tree-CO2 indicators on a ``StudyArea``."""

    def __init__(self, area: StudyArea):
        self.area = area
        self.uhi_baseline_c: Optional[float] = None
        self.uhi_table: Optional[pd.DataFrame] = None
        self.trees = None  # GeoDataFrame after compute_tree_co2

    # ------------------------------------------------------------------
    # UHI rural baseline from KNMI uurgegevens
    # ------------------------------------------------------------------
    def compute_uhi_baseline(
        self,
        knmi_txt: str | Path,
        month: str = "2022-08",
        hours: tuple = (10, 11),
    ) -> "EcologyModule":
        """
        Compute rural baseline temperature from a KNMI ``uurgeg_*`` file.

        Parameters
        ----------
        knmi_txt : str | Path
            Path to the KNMI hourly station text file (e.g. uurgeg_290_2021-2030.txt).
        month : str
            ISO month string ('YYYY-MM') to filter, default August 2022.
        hours : tuple of int
            Daytime hours to keep (KNMI ``HH`` column is 1-24, UTC-like).

        Returns
        -------
        self, with ``self.uhi_baseline_c`` and ``self.uhi_table`` populated.
        """
        df = pd.read_csv(
            knmi_txt,
            skiprows=31,           # KNMI header is 31 lines
            sep=",",
            na_values=["     ", "    "],
        )
        df.rename(
            columns=lambda x: x.strip().replace("# ", "").replace(" ", ""),
            inplace=True,
        )
        df["date"] = pd.to_datetime(df["YYYYMMDD"], format="%Y%m%d")

        start = pd.Timestamp(month + "-01")
        end = start + pd.offsets.MonthEnd(0)
        mask = (df["date"] >= start) & (df["date"] <= end)
        sel = df.loc[mask & df["HH"].isin(list(hours))].copy()

        # KNMI stores temperature in 0.1 °C
        sel["T"] = sel["T"] / 10.0
        self.uhi_table = sel[["date", "HH", "T"]].reset_index(drop=True)
        self.uhi_baseline_c = float(self.uhi_table["T"].mean())
        return self

    # ------------------------------------------------------------------
    # Tree CO2 sequestration from CHM
    # ------------------------------------------------------------------
    def compute_tree_co2(
        self,
        chm_path: str | Path,
        min_height_m: float = config.TREE_MIN_HEIGHT_M,
        sigma: float = config.TREE_DETECT_GAUSSIAN_SIGMA,
        window: int = config.TREE_DETECT_WINDOW,
        co2_coef: float = config.TREE_CO2_COEF,
    ) -> "EcologyModule":
        """
        Detect tree tops from a vegetation-only CHM raster and estimate CO2.

        Steps (mirrors ``CO2_Sequestration.ipynb``):

        1. Gaussian smooth with *sigma* px.
        2. Find local maxima in a *window* x *window* footprint.
        3. Keep only canopy > *min_height_m*.
        4. Apply allometric model: CO2 [kg] = *co2_coef* * h^2.
        """
        import rasterio
        from scipy.ndimage import gaussian_filter, maximum_filter
        import geopandas as gpd
        from shapely.geometry import Point

        with rasterio.open(chm_path) as src:
            chm = src.read(1).astype("float32")
            transform = src.transform
            crs = src.crs

        chm[chm < 0] = 0
        smooth = gaussian_filter(chm, sigma=sigma)
        neigh = maximum_filter(smooth, size=window)
        local_max = (smooth == neigh) & (smooth > min_height_m)

        rows, cols = np.where(local_max)
        heights, pts = [], []
        for r, c in zip(rows, cols):
            h = float(chm[r, c])
            if h > min_height_m:
                x, y = rasterio.transform.xy(transform, r, c)
                pts.append(Point(x, y))
                heights.append(h)

        gdf = gpd.GeoDataFrame(
            {"height_m": heights},
            geometry=pts,
            crs=crs or config.CRS_RD,
        )
        gdf["co2_kg"] = co2_coef * (gdf["height_m"] ** 2)
        self.trees = gdf
        return self

    # ------------------------------------------------------------------
    # Persist
    # ------------------------------------------------------------------
    def write_trees(self, out_path: str | Path) -> Path:
        if self.trees is None:
            raise RuntimeError("Run compute_tree_co2() first")
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        driver = "GeoJSON" if out_path.suffix.lower() == ".geojson" else "GPKG"
        self.trees.to_file(str(out_path), driver=driver)
        return out_path
