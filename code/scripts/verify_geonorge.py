#!/usr/bin/env python3
"""Cross-check Route A (ArcGIS mirror, data/raw) against Route B (Geonorge GML) — SPEC §2.1.

For every polyline feature in data/raw, find the Route B features of the matching
feature type and compare vertex-by-vertex: each Route A vertex is matched to its
nearest Route B vertex of that type, and the great-circle distance is reported.
Route B (EPSG:4258) is delivered with 6 decimals (~0.1 m); Route A carries full
double precision, so agreement is expected at the ~0.05 m level, not byte level.

Usage: python scripts/verify_geonorge.py <path-to-4258.gml> [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repository root (scripts live in code/scripts/)

sys.path.insert(0, str(Path(__file__).parent))
import gml  # noqa: E402

# Route A layer file -> Route B feature type(s) holding the same lines.
LAYER_TO_FTYPE = {
    "0-grunnlinje": ["Grunnlinje"],
    "1-1nm": ["LovVirkeområdeGrense"],
    "2-4nm": ["LovVirkeområdeGrense"],
    "3-6nm": ["LovVirkeområdeGrense"],
    "4-10nm": ["LovVirkeområdeGrense"],
    "5-territorialgrense-12nm": ["Territorialgrense"],
    "6-tilstotende-sone-24nm": ["YttergrenseTilstøtendeSone"],
    "7-200nm": ["Grense200NautiskeMil"],
    "8-avtalt-avgrensningslinje": ["AvtaltAvgrensningslinje"],
    "9-yttergrense-kontinentalsokkel": ["YttergrenseSokkel"],
    "10-avgrensningslinje-kontinentalsokkel": ["AvtaltAvgrensningslinjeSokkel"],
    "11-andre-staters-eez": ["Grense200NautiskeMil"],
}

R = 6_371_008.8  # mean Earth radius, m — adequate for sub-metre residuals


def haversine_m(lon1, lat1, lon2, lat2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def raw_vertices(fc: dict):
    for f in fc["features"]:
        g = f["geometry"]
        parts = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        yield f["properties"]["NAVN"], [tuple(p) for part in parts for p in part]


class Grid:
    """Cheap nearest-vertex lookup on a lon/lat grid (cell = 0.01°)."""

    def __init__(self, pts: list[tuple[float, float]], cell: float = 0.01):
        self.cell = cell
        self.cells: dict[tuple[int, int], list[tuple[float, float]]] = {}
        for lon, lat in pts:
            self.cells.setdefault(self._key(lon, lat), []).append((lon, lat))

    def _key(self, lon, lat):
        return (math.floor(lon / self.cell), math.floor(lat / self.cell))

    def nearest_m(self, lon, lat) -> float:
        kx, ky = self._key(lon, lat)
        best = math.inf
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for plon, plat in self.cells.get((kx + dx, ky + dy), ()):
                    d = haversine_m(lon, lat, plon, plat)
                    if d < best:
                        best = d
        return best


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gml_4258", type=Path)
    ap.add_argument("--raw", type=Path, default=ROOT / "data/raw")
    ap.add_argument("--json", type=Path, help="write machine-readable results here")
    args = ap.parse_args(argv)

    feats = gml.read(args.gml_4258)
    by_type: dict[str, list[tuple[float, float]]] = {}
    for f in feats:
        if f.geom_type != "LineString":
            continue
        assert f.srs == "EPSG:4258", f.srs
        # GML 3.2 + EPSG:4258 => lat lon axis order
        by_type.setdefault(f.ftype, []).extend((float(lon), float(lat)) for lat, lon in f.rings[0])

    results = {}
    worst = 0.0
    for layer, ftypes in LAYER_TO_FTYPE.items():
        pts = [p for t in ftypes for p in by_type[t]]
        grid = Grid(pts)
        fc = json.loads((args.raw / f"{layer}.geojson").read_bytes())
        for name, verts in raw_vertices(fc):
            ds = [grid.nearest_m(lon, lat) for lon, lat in verts]
            mx = max(ds)
            worst = max(worst, mx)
            results[f"{layer} | {name}"] = {"vertices": len(verts), "max_m": round(mx, 3), "mean_m": round(sum(ds) / len(ds), 3), "over_1m": sum(d > 1 for d in ds)}
            print(f"{layer:40s} {name[:52]:52s} n={len(verts):5d}  max {mx:8.3f} m  mean {sum(ds)/len(ds):6.3f} m  >1m: {sum(d > 1 for d in ds)}")

    # Route B-only content worth knowing about
    a_names = {n for layer in LAYER_TO_FTYPE for n, _ in raw_vertices(json.loads((args.raw / f"{layer}.geojson").read_bytes()))}
    b_only = sorted({f.name for f in feats if f.geom_type == "LineString" and f.ftype in {t for ts in LAYER_TO_FTYPE.values() for t in ts} and f.name not in a_names and not any(f.name.startswith(a[:50]) for a in a_names)})
    print(f"\nWorst vertex deviation across all layers: {worst:.3f} m")
    print("Route B line features with no Route A counterpart:")
    for n in b_only:
        print("  -", n)
    if args.json:
        args.json.write_text(json.dumps({"worst_m": worst, "features": results, "route_b_only": b_only}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
