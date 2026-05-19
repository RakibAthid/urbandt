"""
Command-line interface: `urbandt build ...`

Minimal end-to-end runner so you can do, from a fresh clone of someone
else's neighbourhood data::

    urbandt build \\
        --buildings my_buildings.gpkg \\
        --enexis enexis.xlsx \\
        --pv zonnedakje.gpkg \\
        --templates ./viewer_html/ \\
        --out ./dashboard/ \\
        --mode public
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import StudyArea, EnergyModule, EcologyModule
from .viz import build_dashboard


def _add_build_parser(sub):
    p = sub.add_parser("build", help="Run the full pipeline and emit a dashboard")
    p.add_argument("--buildings", required=True, help="Buildings GPKG (BAG pand)")
    p.add_argument("--enexis", required=False, help="Enexis XLSX (postcode-level)")
    p.add_argument("--pv", required=False, help="Zonnedakje PV potential GPKG")
    p.add_argument("--knmi", required=False, help="KNMI uurgegevens TXT (for UHI baseline)")
    p.add_argument("--chm", required=False, help="Canopy Height Model raster (for tree CO2)")
    p.add_argument("--templates", required=False, help="Folder with index/energy/ecology HTML templates")
    p.add_argument("--out", required=True, help="Output directory")
    p.add_argument("--mode", default="public", choices=["local", "private", "public"])
    p.add_argument("--name", default=None, help="Study area name")
    p.add_argument("--pv-factor", type=float, default=1.0)
    p.add_argument("--r2-base", default="", help="Optional Cloudflare R2 base URL")


def _cmd_build(args):
    area = StudyArea.from_gpkg(args.buildings, name=args.name)
    print(area)

    if args.enexis and args.pv:
        EnergyModule(area).compute_all(
            enexis_xlsx=args.enexis,
            pv_gpkg=args.pv,
            pv_factor=args.pv_factor,
        )
        print(f"Energy indicators computed for {area.n_buildings} buildings.")
    else:
        print("Skipping energy module (need --enexis and --pv).")

    if args.knmi or args.chm:
        eco = EcologyModule(area)
        if args.knmi:
            eco.compute_uhi_baseline(args.knmi)
            print(f"UHI rural baseline: {eco.uhi_baseline_c:.2f} °C")
        if args.chm:
            eco.compute_tree_co2(args.chm)
            print(f"Detected {len(eco.trees)} trees; "
                  f"total CO2 storage = {eco.trees['co2_kg'].sum():.0f} kg")

    out = build_dashboard(
        area,
        out_dir=args.out,
        mode=args.mode,
        html_source_dir=args.templates,
        r2_base=args.r2_base,
    )
    print(f"Wrote dashboard ({args.mode}) → {Path(args.out).resolve()}")
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(prog="urbandt",
                                     description="Urban Digital Twin toolkit")
    sub = parser.add_subparsers(dest="command", required=True)
    _add_build_parser(sub)

    args = parser.parse_args(argv)
    if args.command == "build":
        return _cmd_build(args)
    parser.print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main() or 0)
