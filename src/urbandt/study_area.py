"""
StudyArea: the central object that all modules operate on.

It holds:
- a building footprint GeoDataFrame (BAG-pand-style), in RD New (EPSG:28992)
- the AOI polygon (optional)
- a human-readable name

Both EnergyModule and EcologyModule attach their computed indicator columns
back to ``StudyArea.buildings`` so that a final dashboard export can serialise
everything in one GeoJSON.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from . import config, io as _io


@dataclass
class StudyArea:
    """
    A neighbourhood-level digital-twin study area.

    Attributes
    ----------
    name : str
        Human-readable name used in dashboard titles and filenames.
    buildings : GeoDataFrame
        Building footprints with at least: a BAG id column and a floor-area
        column (config.AREA_FIELD). Must be in EPSG:28992.
    aoi : GeoDataFrame | None
        Optional area-of-interest polygon (used for clipping rasters etc.).
    """

    name: str
    buildings: object  # geopandas.GeoDataFrame at runtime
    aoi: Optional[object] = None
    metadata: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------
    @classmethod
    def from_gpkg(
        cls,
        path: str | Path,
        name: str | None = None,
        layer: str | None = None,
        aoi_path: str | Path | None = None,
        aoi_layer: str | None = None,
    ) -> "StudyArea":
        """
        Load a study area from a GeoPackage of building footprints.

        Parameters
        ----------
        path : str | Path
            Path to a .gpkg containing building polygons (BAG pand-style).
        name : str
            Human-readable name. Defaults to the file stem.
        layer : str
            Layer name inside the .gpkg. Defaults to the first layer.
        aoi_path : str | Path, optional
            Path to a separate .gpkg / .shp holding the AOI polygon.
        """
        buildings = _io.load_gpkg(path, layer=layer,
                                  preferred_layer_keywords=["pand", "build"])
        if buildings is None:
            raise FileNotFoundError(f"Could not read buildings from {path}")
        buildings = _io.ensure_crs(buildings, config.CRS_RD)
        buildings = _io.fix_geometries(buildings)

        aoi = None
        if aoi_path is not None:
            aoi = _io.load_gpkg(aoi_path, layer=aoi_layer)
            if aoi is not None:
                aoi = _io.ensure_crs(aoi, config.CRS_RD)

        name = name or Path(path).stem
        return cls(name=name, buildings=buildings, aoi=aoi)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------
    @property
    def crs(self):
        return self.buildings.crs

    @property
    def n_buildings(self) -> int:
        return len(self.buildings)

    @property
    def total_floor_area(self) -> float:
        col = config.AREA_FIELD
        if col not in self.buildings.columns:
            raise KeyError(
                f"Buildings layer is missing '{col}'. "
                f"Available columns: {list(self.buildings.columns)}"
            )
        import pandas as pd
        self.buildings[col] = pd.to_numeric(self.buildings[col], errors="coerce")
        return float(self.buildings.loc[self.buildings[col] > 0, col].sum())

    def to_wgs84(self):
        """Return a copy of *buildings* re-projected to WGS-84 (for Cesium)."""
        return _io.ensure_crs(self.buildings.copy(), config.CRS_WGS)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def write_geojson(self, out_path: str | Path, wgs84: bool = True) -> Path:
        """Write the (current) buildings layer to GeoJSON, default WGS-84."""
        gdf = self.to_wgs84() if wgs84 else self.buildings
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        gdf.to_file(str(out_path), driver="GeoJSON")
        return out_path

    def __repr__(self) -> str:
        return (
            f"StudyArea(name={self.name!r}, n_buildings={self.n_buildings}, "
            f"crs={self.crs})"
        )
