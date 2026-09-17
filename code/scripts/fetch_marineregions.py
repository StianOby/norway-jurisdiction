#!/usr/bin/env python3
"""Fetch neighbouring-state lines from Marine Regions (Flanders Marine Institute) — owner decision 2026-09-17.

Only what the Kartverket dataset cannot supply is taken:
  * eez_boundaries  (Barents Sea bbox)  — Russia's 200 nm limit and the Special Area edges
  * high_seas       (North Atlantic/Arctic bbox) — their high-seas polygons (Banana Hole, Loop Hole)
  * ecs             (same bbox) — extended continental shelf polygons by status (CLCS recommendation /
                                  submission / overlapping claim / DOALOS deposit)
Response bodies are written verbatim to data/raw/marineregions/ with SHA-256 in FETCH_LOG.json.

Licence: CC BY 4.0 (Marine Regions products are CC-BY since Maritime Boundaries v11, 2019).
Citation: Flanders Marine Institute (2023). Maritime Boundaries Geodatabase, version 12.
https://www.marineregions.org/ https://doi.org/10.14284/628 ; Extended Continental Shelves v2
https://doi.org/10.14284/697 .  Accuracy caveat: Marine Regions' 200 nm limits are their own
computation from an ESRI 2014 coastline (see eezmethodology.php) — used here only for Russia,
whose deposit with the UN (M.Z.N.124.2016) is charts without coordinate lists.  Stdlib only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repository root (scripts live in code/scripts/)

WFS = "https://geo.vliz.be/geoserver/MarineRegions/wfs"
LAYERS = {
    "eez_boundaries_barents.json": ("MarineRegions:eez_boundaries", "15,68,60,85"),
    "high_seas_pockets.json": ("MarineRegions:high_seas", "-15,60,45,86"),
    "ecs_north_atlantic.json": ("MarineRegions:ecs", "-15,60,45,86"),
}
USER_AGENT = "norway-jurisdiction/0.1 (teaching model, UiO)"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "data/raw/marineregions")
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    log = {"fetched_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(), "wfs": WFS,
           "licence": "CC BY 4.0", "citation": "Flanders Marine Institute (2023). Maritime Boundaries Geodatabase, version 12. https://doi.org/10.14284/628",
           "files": {}}
    for name, (layer, bbox) in LAYERS.items():
        q = urllib.parse.urlencode({"service": "WFS", "version": "1.0.0", "request": "GetFeature", "typeName": layer,
                                    "outputFormat": "json", "srsName": "EPSG:4326", "bbox": bbox + ",EPSG:4326"})
        req = urllib.request.Request(f"{WFS}?{q}", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=600) as r:
            body = r.read()
        fc = json.loads(body)
        assert fc.get("type") == "FeatureCollection", name
        note = ""
        if layer == "MarineRegions:high_seas":
            # The layer is one global multipolygon (13 MB).  Keep only the parts that lie entirely inside
            # the bbox — the enclosed pockets (Banana Hole, Loop Hole) — as separate features.
            x0, y0, x1, y1 = (float(v) for v in bbox.split(","))
            parts = []
            for f in fc["features"]:
                g = f["geometry"]
                for poly in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
                    xs = [c[0] for c in poly[0]]; ys = [c[1] for c in poly[0]]
                    if min(xs) >= x0 and max(xs) <= x1 and min(ys) >= y0 and max(ys) <= y1:
                        parts.append({"type": "Feature", "properties": {**f["properties"], "part": "pocket"}, "geometry": {"type": "Polygon", "coordinates": poly}})
            fc = {"type": "FeatureCollection", "features": parts, "note": "subset of MarineRegions:high_seas — only polygon parts entirely inside the bbox (enclosed high-seas pockets); coordinates as served"}
            body = json.dumps(fc, separators=(",", ":")).encode()
            note = f" (subset: {len(parts)} pocket polygons kept of a {r.length or 'global'} multipolygon)"
        (args.out / name).write_bytes(body)
        log["files"][name] = {"layer": layer, "bbox": bbox, "features": len(fc["features"]), "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "note": note.strip()}
        print(f"{name:36s} {len(fc['features']):4d} features {len(body):9d} B  {log['files'][name]['sha256'][:12]}")
    (args.out / "FETCH_LOG.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
