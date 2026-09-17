#!/usr/bin/env python3
"""Fetch a coarse GEBCO 2020 elevation grid over the model area (SPEC §3.3, §5.2).

The seabed in the model is *schematic* (SPEC §1). GEBCO is used only to derive indicative
depth figures and a coarse class map (shelf / Norwegian Trench / slope / abyssal / deep basin)
that `build_seabed.py` writes to data/build/. Nothing survey-grade is shipped.

Source: GEBCO Compilation Group (2020) GEBCO 2020 Grid, doi:10.5285/a29c5465-b138-234d-e053-6c86abc040b9,
served by NOAA CoastWatch ERDDAP (dataset GEBCO_2020, 15 arc-second grid). Requested with a
stride so that the cell spacing is 0.25° lat x 0.5° lon (about 28 km x 10-25 km). The response
body is written verbatim; SHA-256 in FETCH_LOG.json. Stdlib only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repository root (scripts live in code/scripts/)

ERDDAP = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/GEBCO_2020.json"
# Model bbox (build_zones.BBOX) and stride in 15" cells: 60 = 0.25°, 120 = 0.5°.
LAT = (55.0, 86.0, 60)
LON = (-15.0, 46.0, 120)
USER_AGENT = "norway-jurisdiction/0.1 (teaching model, UiO)"
CITATION = ("GEBCO Compilation Group (2020) GEBCO 2020 Grid "
            "(doi:10.5285/a29c5465-b138-234d-e053-6c86abc040b9), via NOAA CoastWatch ERDDAP dataset GEBCO_2020")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "data/raw/gebco")
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    q = f"elevation[({LAT[0]}):{LAT[2]}:({LAT[1]})][({LON[0]}):{LON[2]}:({LON[1]})]"
    url = f"{ERDDAP}?{q}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=600) as r:
        body = r.read()
    table = json.loads(body)["table"]
    assert table["columnNames"] == ["latitude", "longitude", "elevation"], table["columnNames"]
    name = "gebco2020_0p25x0p5deg.json"
    (args.out / name).write_bytes(body)
    log = {"fetched_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
           "url": url, "citation": CITATION,
           "licence": "GEBCO grids are placed in the public domain and may be used free of charge (GEBCO terms of use); attribution requested",
           "files": {name: {"rows": len(table["rows"]), "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                            "lat": LAT, "lon": LON}}}
    (args.out / "FETCH_LOG.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{name}: {len(table['rows'])} cells, {len(body)} B, sha256 {log['files'][name]['sha256'][:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
