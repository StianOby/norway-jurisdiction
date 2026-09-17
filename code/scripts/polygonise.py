#!/usr/bin/env python3
"""Build zone polygons — SPEC §6.1 step 2/3, as amended 2026-09-17 (see CLAUDE.md).

Source of truth for zone extents is Kartverket's *official* zone polygons in the
Route B (Geonorge) delivery.  Route A (data/raw/*.geojson) supplies the
full-precision coordinate *text* for every vertex that lies on a Kartverket
line, so those vertices are emitted byte-identical to data/raw.

What this script does, all topology in EPSG:25833 via scripts/proj.py:

  1. Index every Route A vertex (text tokens, not floats) for exact re-emission.
  2. Decide, per Route A line, which vertices survive simplification
     (Douglas-Peucker, --arc-tolerance metres).  Exempt - never simplified -
     are: baselines (layer 0), delimitation lines (8, 10), other states' EEZ
     limits (11) and the continental-shelf outer limit (9).  This gives one
     consistent simplification for every polygon that shares a line.
  3. Rebuild each Kartverket polygon ring from Route B, dropping vertices that
     the shared-line simplification removed; every remaining vertex is either a
     Route A text token or (coastline only) a 6-decimal number.
  4. Mainland internal waters: N1000 'Havflate' (sea surface) clipped to the
     region landward of 'Norges grunnlinje'.  Coast simplified with
     --coast-tolerance, islands below --min-island km2 dropped, baseline exact.
  5. Svalbard / Jan Mayen internal waters: Kartverket's IndreFarvann polygons
     (their NPI-sourced coastline; no N-series coverage there), coast simplified.
  6. High-seas pockets: faces of the noded 200 nm + EEZ-limit + delimitation
     line network that lie in no Norwegian 200 nm zone (the Banana Hole).  The
     Loop Hole cannot be closed (no Russian 200 nm line in the data) and is
     reported as not modelled.
  7. Bouvetoya is excluded (owner decision 2026-09-17).

Output: data/build/geometry.json - {id: {geometry, vertexCount, source, notes}} plus stats.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repository root (scripts live in code/scripts/)

sys.path.insert(0, str(Path(__file__).parent))
import gml  # noqa: E402
from proj import UTM33N  # noqa: E402
from shapely.geometry import LineString, MultiPolygon, Point, Polygon  # noqa: E402
from shapely.ops import polygonize, snap, unary_union  # noqa: E402

RAW = ROOT / "data/raw"
GEONORGE_ZIP = RAW / "geonorge" / "Basisdata_0000_Norge_4258_NorgesMaritimeGrenser_GML.zip"
N1000 = RAW / "geonorge" / "n1000-coast.geojson"
OUT = ROOT / "data/build/geometry.json"

RAW_LAYERS = ["0-grunnlinje", "1-1nm", "2-4nm", "3-6nm", "4-10nm", "5-territorialgrense-12nm",
              "6-tilstotende-sone-24nm", "7-200nm", "8-avtalt-avgrensningslinje",
              "9-yttergrense-kontinentalsokkel", "10-avgrensningslinje-kontinentalsokkel", "11-andre-staters-eez"]
EXEMPT_FROM_SIMPLIFICATION = {"0-grunnlinje", "8-avtalt-avgrensningslinje", "9-yttergrense-kontinentalsokkel",
                              "10-avgrensningslinje-kontinentalsokkel", "11-andre-staters-eez"}
COORD_RE = re.compile(rb"\[(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?),(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\]")
MATCH_TOL_M = 0.25   # Route B is delivered with 6 decimals (~0.06 m); anything closer than this is the same vertex

fwd = UTM33N.forward
inv = UTM33N.inverse


# ---------------------------------------------------------------- Route A index
class SourceIndex:
    """Every Route A vertex with its original text, findable by position."""

    def __init__(self):
        self.lines: dict[str, list[tuple[float, float]]] = {}       # line key -> projected coords
        self.text: dict[str, list[tuple[str, str]]] = {}            # line key -> (lon_text, lat_text)
        self.layer_of: dict[str, str] = {}
        self.cells: dict[tuple[int, int], list[tuple[str, int]]] = defaultdict(list)
        self.keep: dict[str, set[int]] = {}

    @staticmethod
    def _cell(x, y):
        return (int(x // 10), int(y // 10))

    def load(self):
        for layer in RAW_LAYERS:
            raw = (RAW / f"{layer}.geojson").read_bytes()
            fc = json.loads(raw)
            tokens = COORD_RE.findall(raw)
            ti = 0
            for f in fc["features"]:
                g = f["geometry"]
                parts = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
                for pi, part in enumerate(parts):
                    key = f"{layer}#{f['id']}.{pi}"
                    self.layer_of[key] = layer
                    pts, txt = [], []
                    for lon, lat in part:
                        tlon, tlat = tokens[ti]
                        ti += 1
                        assert float(tlon) == lon and float(tlat) == lat, (key, tlon, tlat, lon, lat)
                        if lat < 0:            # Bouvetoya - excluded from the model
                            continue
                        pts.append(fwd(lon, lat))
                        txt.append((tlon.decode(), tlat.decode()))
                    if not pts:
                        continue
                    self.lines[key] = pts
                    self.text[key] = txt
                    for i, (x, y) in enumerate(pts):
                        self.cells[self._cell(x, y)].append((key, i))
            assert ti == len(tokens), (layer, ti, len(tokens))

    def match(self, x: float, y: float) -> list[tuple[str, int]]:
        cx, cy = self._cell(x, y)
        hits = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for key, i in self.cells.get((cx + dx, cy + dy), ()):
                    px, py = self.lines[key][i]
                    if math.hypot(px - x, py - y) <= MATCH_TOL_M:
                        hits.append((key, i))
        return hits

    def simplify(self, tol_m: float):
        for key, pts in self.lines.items():
            if self.layer_of[key] in EXEMPT_FROM_SIMPLIFICATION or len(pts) < 3:
                self.keep[key] = set(range(len(pts)))
                continue
            simp = LineString(pts).simplify(tol_m, preserve_topology=True)
            kept = set(simp.coords)
            self.keep[key] = {i for i, p in enumerate(pts) if p in kept}

    def keep_vertex(self, hits) -> bool:
        return any(i in self.keep[key] for key, i in hits)

    def on_exempt_segment(self, x: float, y: float, tol_m: float = 1.0) -> str | None:
        """Key of an exempt (never-simplified) line whose segment passes within tol_m of (x, y).
        Kartverket's polygons carry a few nodes *on* delimitation lines (where two zones meet a
        treaty line) that are not vertices of the line itself; those are legitimate."""
        pt = Point(x, y)
        for key, pts in self.lines.items():
            if self.layer_of[key] not in EXEMPT_FROM_SIMPLIFICATION:
                continue
            if LineString(pts).distance(pt) <= tol_m:
                return key
        return None


# ---------------------------------------------------------------- ring assembly
class Vertex:
    """An output vertex: either exact source text or a rounded computed position."""
    __slots__ = ("x", "y", "text")

    def __init__(self, x, y, text=None):
        self.x, self.y, self.text = x, y, text

    def emit(self) -> list:
        if self.text:
            return [_Raw(self.text[0]), _Raw(self.text[1])]
        lon, lat = inv(self.x, self.y)
        return [_Raw(f"{lon:.6f}"), _Raw(f"{lat:.6f}")]


class _Raw(str):
    """Marker so the JSON writer can emit numeric text verbatim."""


def ring_from_routeb(ring_latlon, src: SourceIndex, stats: dict) -> list[Vertex]:
    out: list[Vertex] = []
    for lat, lon in ring_latlon:
        x, y = fwd(float(lon), float(lat))
        hits = src.match(x, y)
        if hits:
            stats["matched"] += 1
            if not src.keep_vertex(hits):
                stats["simplified_away"] += 1
                continue
            key, i = hits[0]
            out.append(Vertex(*src.lines[key][i], src.text[key][i]))
        elif (seg := src.on_exempt_segment(x, y)):
            stats.setdefault("on_delimitation_segment", []).append({"lon": lon, "lat": lat, "line": seg})
            out.append(Vertex(x, y))            # emitted as Kartverket's 6-decimal value
        else:
            stats["unmatched"] += 1
            out.append(Vertex(x, y))
    if out and (out[0].x, out[0].y) != (out[-1].x, out[-1].y):
        out.append(out[0])
    return out


def ring_from_shapely(coords, exact_lookup: dict) -> list[Vertex]:
    return [Vertex(x, y, exact_lookup.get((x, y))) for x, y in coords]


def poly_vertices(rings: list[list[Vertex]]):
    return [[v.emit() for v in r] for r in rings]


def to_shapely(rings: list[list[Vertex]]) -> Polygon:
    return Polygon([(v.x, v.y) for v in rings[0]], [[(v.x, v.y) for v in r] for r in rings[1:]])


def drop_small_holes(poly: Polygon, min_area_m2: float) -> Polygon:
    return Polygon(poly.exterior.coords, [r.coords for r in poly.interiors if Polygon(r).area >= min_area_m2])


def parts_of(geom) -> list[Polygon]:
    return [g for g in (geom.geoms if hasattr(geom, "geoms") else [geom]) if isinstance(g, Polygon) and not g.is_empty]


def snap_to_source(coords, src: "SourceIndex"):
    """Replace Route B 6-decimal points by the exact Route A point they coincide with."""
    out = []
    for x, y in coords:
        h = src.match(x, y)
        out.append(src.lines[h[0][0]][h[0][1]] if h else (x, y))
    return out


def rings_of(g: Polygon, exact: dict) -> list[list[Vertex]]:
    return [ring_from_shapely(g.exterior.coords, exact)] + [ring_from_shapely(r.coords, exact) for r in g.interiors]


# ---------------------------------------------------------------- main build
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arc-tolerance", type=float, default=100.0, help="metres, DP tolerance for computed limit lines (12/24/200 nm)")
    ap.add_argument("--coast-tolerance", type=float, default=300.0, help="metres, topology-preserving DP tolerance for coastlines")
    ap.add_argument("--min-island", type=float, default=3.0, help="km2, islands smaller than this are not cut out of internal waters")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)

    src = SourceIndex()
    src.load()
    src.simplify(args.arc_tolerance)
    print(f"Route A: {sum(len(v) for v in src.lines.values())} vertices indexed (Bouvetoya excluded); "
          f"{sum(len(v) for v in src.keep.values())} survive simplification at {args.arc_tolerance} m")

    with zipfile.ZipFile(GEONORGE_ZIP) as z:
        name = next(n for n in z.namelist() if n.endswith(".gml"))
        with z.open(name) as fh:
            feats = gml.read(fh)
    polys = [f for f in feats if f.geom_type == "Polygon"]

    def kv(ftype, needle):
        hits = [f for f in polys if f.ftype == ftype and needle in f.name]
        assert hits, (ftype, needle)
        return hits

    zones: dict[str, dict] = {}
    notes: dict[str, list[str]] = defaultdict(list)
    exact = {p: t for k in src.lines for p, t in zip(src.lines[k], src.text[k])}     # projected point -> text
    exact_pts = set(exact)
    KV_KEYS = ("virkeområdenavn", "gyldigFra", "datafangstdato", "oppdateringsdato", "grensestatus", "land", "informasjon")

    def add_routeb(zid, ftype, needle, coast=False):
        """coast=True: the polygon boundary legitimately includes coastline (Jan Mayen, whose
        baseline is partly the low-water line); unmatched vertices are then coast, kept as delivered."""
        feats_ = kv(ftype, needle)
        geoms, stats = [], {"matched": 0, "unmatched": 0, "simplified_away": 0}
        for f in feats_:
            rings = [ring_from_routeb(r, src, stats) for r in f.rings]
            geoms.append([r for r in rings if len(r) >= 4])
        if stats["unmatched"] and not coast:
            raise SystemExit(f"{zid}: {stats['unmatched']} vertices of Kartverket's polygon are not on any Route A line")
        shp = [to_shapely(r) for r in geoms]
        if coast:
            stats["coast_vertices_kept_as_delivered"] = stats.pop("unmatched")
        for s in shp:
            if not s.is_valid:
                raise SystemExit(f"{zid}: invalid polygon after simplification")
        zones[zid] = {"rings": geoms, "shapely": MultiPolygon(shp) if len(shp) > 1 else shp[0],
                      "source": f"Kartverket Norges maritime grenser (Geonorge GML EPSG:4258) - {ftype}: " + "; ".join(f.name for f in feats_),
                      "kartverket": [{k: v for k, v in f.props.items() if k in KV_KEYS} for f in feats_],
                      "stats": stats}
        print(f"  {zid:34s} {sum(len(r) for g in geoms for r in g):6d} vertices  {stats}")

    print("Kartverket polygons:")
    add_routeb("mainland-territorial-sea", "Sjøterritorium", "Fastlands-Norge")
    add_routeb("mainland-contiguous-zone", "TilstøtendeSone", "Fastlands-Norge")
    add_routeb("mainland-eez", "NorgesØkonomiskeSone", "økonomiske sone")
    add_routeb("svalbard-territorial-sea", "Sjøterritorium", "Svalbard")
    add_routeb("svalbard-fpz", "Fiskevernsone", "Svalbard")
    add_routeb("janmayen-territorial-sea", "Sjøterritorium", "Jan Mayen", coast=True)
    add_routeb("janmayen-fisheries-zone", "Fiskerisone", "Jan Mayen")
    add_routeb("continental-shelf", "Kontinentalsokkel", "kontinentalsokkel")

    # ---- internal waters, mainland: N1000 Havflate (topologically simplified) clipped landward of the exact baseline
    print("Internal waters:")
    n1000 = json.loads(N1000.read_text(encoding="utf-8"))
    hav = unary_union([Polygon([fwd(x, y) for x, y in f["geometry"]["coordinates"][0]],
                               [[fwd(x, y) for x, y in r] for r in f["geometry"]["coordinates"][1:]]).buffer(0)
                       for f in n1000["features"] if f["properties"]["type"] == "Havflate"])
    hav = hav.simplify(args.coast_tolerance, preserve_topology=True)
    bl_key = next(k for k in src.lines if k.startswith("0-grunnlinje#4."))          # 'Norges grunnlinje'
    bl = src.lines[bl_key]
    # inland closure through Sweden/Finland - far from any water, never emitted
    inland = [fwd(*p) for p in [(30.5, 69.0), (28.0, 68.3), (24.0, 67.5), (18.0, 65.5), (14.0, 62.5), (12.5, 59.8), (11.6, 58.9)]]
    region = Polygon(list(reversed(bl)) + inland)
    iw = region.intersection(hav)
    parts = [drop_small_holes(g, args.min_island * 1e6) for g in parts_of(iw) if g.area >= args.min_island * 1e6 * 0.1]
    assert all(g.is_valid for g in parts)
    zones["mainland-internal-waters"] = {"rings": [rings_of(g, exact) for g in parts], "shapely": MultiPolygon(parts),
        "source": "N1000 Kartdata Havflate (Kartverket, Geonorge GML EPSG:4258), topologically simplified, clipped to the landward side of 'Norges grunnlinje' (Route A layer 0, exact)",
        "kartverket": [], "stats": {"parts": len(parts), "holes": sum(len(g.interiors) for g in parts), "coast_tolerance_m": args.coast_tolerance, "min_island_km2": args.min_island, "area_km2": round(iw.area / 1e6)}}
    print(f"  {'mainland-internal-waters':34s} {sum(len(r) for g in zones['mainland-internal-waters']['rings'] for r in g):6d} vertices  parts={len(parts)} holes={zones['mainland-internal-waters']['stats']['holes']} area={iw.area/1e6:.0f} km2")

    # ---- internal waters, Svalbard: exact baseline loops minus Kartverket/NPI land (topologically simplified)
    land_sj = unary_union([Polygon([fwd(float(lon), float(lat)) for lat, lon in f.rings[0]],
                                   [[fwd(float(lon), float(lat)) for lat, lon in r] for r in f.rings[1:]]).buffer(0)
                           for f in feats if f.ftype == "Landareal" and f.props.get("land") == "SJ"])
    land_sj = land_sj.simplify(args.coast_tolerance, preserve_topology=True)
    parts = []
    for key in sorted(k for k in src.lines if k.startswith("0-grunnlinje#") and k != bl_key and src.lines[k][0] == src.lines[k][-1]):
        loop = Polygon(src.lines[key])
        if loop.centroid.y < fwd(0, 74)[1] or not loop.is_valid:       # Svalbard loops only (Bjørnøya is at 74.4 N)
            continue
        for g in parts_of(loop.difference(land_sj)):
            if g.area >= args.min_island * 1e6 * 0.1:
                parts.append(drop_small_holes(g, args.min_island * 1e6))
    assert all(g.is_valid for g in parts)
    zones["svalbard-internal-waters"] = {"rings": [rings_of(g, exact) for g in parts], "shapely": MultiPolygon(parts),
        "source": "Svalbard baselines (Route A layer 0, exact, closed loops) minus Kartverket 'Landareal' (land=SJ, Norsk Polarinstitutt coastline as delivered in Norges maritime grenser, topologically simplified)",
        "kartverket": [], "stats": {"parts": len(parts), "holes": sum(len(g.interiors) for g in parts), "coast_tolerance_m": args.coast_tolerance, "min_island_km2": args.min_island}}
    print(f"  {'svalbard-internal-waters':34s} {sum(len(r) for g in zones['svalbard-internal-waters']['rings'] for r in g):6d} vertices  parts={len(parts)}")

    # ---- internal waters, Jan Mayen: Kartverket polygons as delivered (baseline is partly the low-water line), no simplification
    feats_ = kv("IndreFarvann", "Jan Mayen")
    parts = []
    for f in feats_:
        p = Polygon(snap_to_source([fwd(float(lon), float(lat)) for lat, lon in f.rings[0]], src),
                    [snap_to_source([fwd(float(lon), float(lat)) for lat, lon in r], src) for r in f.rings[1:]])
        assert p.is_valid, f.name
        parts.append(p)
    zones["janmayen-internal-waters"] = {"rings": [rings_of(g, exact) for g in parts], "shapely": MultiPolygon(parts),
        "source": "Kartverket Norges maritime grenser - IndreFarvann: " + "; ".join(f.name for f in feats_) + " (as delivered; coastline vertices 6-decimal)",
        "kartverket": [{k: v for k, v in f.props.items() if k in ("virkeområdenavn", "gyldigFra", "land")} for f in feats_],
        "stats": {"parts": len(parts)}}
    print(f"  {'janmayen-internal-waters':34s} {sum(len(r) for g in zones['janmayen-internal-waters']['rings'] for r in g):6d} vertices  parts={len(parts)}")

    # ---- high seas, part 1: pockets closed by Norwegian lines + other states' 200 nm limits (Banana Hole)
    print("High seas:")
    # Layer 10 (shelf-only delimitation) is deliberately left out: it delimits seabed, not water column,
    # and would split the pockets.
    net_keys = [k for k in src.lines if src.layer_of[k] in ("7-200nm", "8-avtalt-avgrensningslinje", "11-andre-staters-eez")]
    # Line ends that should meet differ by ~0.1 mm between layers (e.g. layer 11 vs layer 7 at the
    # Iceland/Jan Mayen junction).  Snap every end to the coincident vertex of the lowest-numbered layer.
    ends = [(src.lines[k][i], k) for k in net_keys for i in (0, -1)]
    canon: dict = {}
    for (p, k) in sorted(ends, key=lambda e: int(src.layer_of[e[1]].split("-")[0])):
        for q in list(canon.values()):
            if math.hypot(p[0] - q[0], p[1] - q[1]) <= 1.0:
                canon[p] = q
                break
        else:
            canon[p] = p

    def snapped(k):
        pts = list(src.lines[k])
        pts[0] = canon.get(pts[0], pts[0])
        pts[-1] = canon.get(pts[-1], pts[-1])
        return LineString(pts)

    filled = unary_union([Polygon(g.exterior.coords) for z in ("mainland-eez", "svalbard-fpz", "janmayen-fisheries-zone", "mainland-contiguous-zone", "mainland-territorial-sea")
                          for g in parts_of(zones[z]["shapely"])])

    # ---- high seas, part 2: the Loop Hole.  Kartverket has no Russian 200 nm line; owner decision
    # 2026-09-17: take it from Marine Regions (Flanders Marine Institute, Maritime Boundaries v12,
    # CC BY 4.0), snapped onto Kartverket's lines where they meet.  Also from Marine Regions: the
    # Norwegian 200 nm arc east of the treaty line (edge of the treaty's Special Area, which is itself
    # not modelled — SPEC §1).  Every vertex on a Kartverket line is emitted as Kartverket's text.
    mr = json.loads((RAW / "marineregions" / "eez_boundaries_barents.json").read_text(encoding="utf-8"))["features"]
    mr_by_id = {f["properties"]["line_id"]: f for f in mr}
    def mr_line(lid, bbox=None):
        g = mr_by_id[lid]["geometry"]
        parts = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        out_ = []
        for part in parts:
            pts = [fwd(x, y) for x, y in part if bbox is None or (bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3])]
            if len(pts) >= 2:
                out_.append(LineString(pts))
        return out_
    russia_200 = mr_line(3697, bbox=(20, 68, 60, 82))            # "Russia 200 NM", Barents Sea segment
    special_area_edges = mr_line(4697)                           # "Joint regime Norway - Russia" ring (the Special Area)
    kart_lines = unary_union([snapped(k) for k in net_keys])
    foreign = unary_union([snap(l, kart_lines, 100.0) for l in russia_200 + special_area_edges])
    network = unary_union([kart_lines, foreign])
    faces = list(polygonize(network))
    special_area = unary_union(list(polygonize(unary_union(special_area_edges))))
    pockets = [f for f in faces if f.area > 1e6 and f.intersection(filled).area < 0.01 * f.area
               and (special_area.is_empty or f.intersection(special_area).area < 0.01 * f.area)]
    print(f"  network faces: {len(faces)}; pockets outside Norwegian zones and the Special Area: {len(pockets)}")
    mr_pts = {c for l in russia_200 + special_area_edges for c in l.coords}
    hs_parts, hs_src = [], []
    for p in pockets:
        c = p.representative_point()
        lon, lat = inv(c.x, c.y)
        name = "loop-hole" if lon > 30 else "banana-hole"
        print(f"    {name:12s} {p.area/1e6:9.0f} km2 near ({lon:.2f}, {lat:.2f})")
        thin = [(x, y) for x, y in p.exterior.coords if not (h := src.match(x, y)) or src.keep_vertex(h)]
        q = Polygon(thin)
        assert q.is_valid, name
        hs_parts.append(q); hs_src.append(name)

    # ---- high seas, part 3: water column above the Norwegian shelf beyond 200 nm that is in no pocket
    # (the Nansen Basin north of Svalbard).  Its outer edge is Norway's shelf outer limit = the model's
    # extent; the high seas continue beyond it (notModelled).
    beyond = zones["continental-shelf"]["shapely"].difference(filled).difference(unary_union(hs_parts))
    for g in parts_of(beyond):
        if g.area > 1e9:
            c = g.representative_point(); lon, lat = inv(c.x, c.y)
            print(f"    {'beyond-200nm':12s} {g.area/1e6:9.0f} km2 near ({lon:.2f}, {lat:.2f}) — shelf beyond 200 nm outside pockets")
            hs_parts.append(Polygon(g.exterior.coords)); hs_src.append("nansen-basin")
    zones["high-seas"] = {"rings": [[ring_from_shapely(g.exterior.coords, exact)] for g in hs_parts], "shapely": MultiPolygon(hs_parts),
        "source": "Derived. Banana Hole: faces of the noded network of Norway's 200 nm lines (layer 7), agreed delimitation lines (layer 8) and other states' 200 nm limits (layer 11). "
                  "Loop Hole: same network plus Marine Regions 'Russia 200 NM' (line_id 3697) and the Special Area ring (line_id 4697), Flanders Marine Institute Maritime Boundaries v12, CC BY 4.0, snapped (≤100 m) onto Kartverket lines. "
                  "Nansen Basin: Norway's continental-shelf polygon beyond every 200 nm zone.",
        "kartverket": [], "stats": {"parts": hs_src, "area_km2": round(sum(g.area for g in hs_parts) / 1e6)}}
    notes["high-seas"].append("Loop Hole: Russia's 200 nm limit is not Norwegian data; it is taken from Marine Regions (their own computation) and was compared visually with the chart Russia deposited with the UN (M.Z.N.124.2016, chart 10100). The sliver east of the 2010 line between 74.94 N and the continuation of the Svalbard 200 nm arc is treated as high seas, following Marine Regions — not verified.")
    notes["high-seas"].append("Nansen Basin: the high seas continue north beyond Norway's shelf outer limit; the model stops at the outer limit (notModelled: beyond-outer-limit).")
    print(f"  {'high-seas':34s} {sum(len(r) for g in zones['high-seas']['rings'] for r in g):6d} vertices  parts={hs_src}")

    # ---- the Area: candidate extent = Marine Regions high seas inside the model extent minus every
    # extended-continental-shelf polygon (any status) minus Norway's shelf and zones.  A data finding for
    # the owner to characterise, emitted as candidateExtent, not as the zone's horizontal extent.
    ecs = json.loads((RAW / "marineregions" / "ecs_north_atlantic.json").read_text(encoding="utf-8"))["features"]
    hsp = json.loads((RAW / "marineregions" / "high_seas_pockets.json").read_text(encoding="utf-8"))["features"]
    from shapely.geometry import box as _box, shape as _shape
    from shapely.ops import transform as _transform
    model_bbox = _box(-15.0, 55.0, 45.0, 86.0)        # lon/lat; keeps the pole (lat 90) out of the projection
    def to_proj_poly(g):
        clipped = _shape(g).buffer(0).intersection(model_bbox)
        return _transform(lambda xs, ys: tuple(zip(*[fwd(x, y) for x, y in zip(xs, ys)])), clipped).buffer(0) if not clipped.is_empty else Polygon()
    ecs_u = unary_union([to_proj_poly(f["geometry"]) for f in ecs])
    hs_mr = unary_union([to_proj_poly(f["geometry"]) for f in hsp])
    unclaimed = hs_mr.difference(ecs_u).difference(zones["continental-shelf"]["shapely"]).difference(filled)
    # near-coincident lines (Marine Regions vs Kartverket) leave hairline slivers: open by 100 m, simplify 50 m
    unclaimed = unclaimed.buffer(-100).buffer(100).simplify(50, preserve_topology=True)
    cand = [Polygon(g.exterior.coords) for g in parts_of(unclaimed) if g.area >= 1e9]
    zones["the-area-candidate"] = {"rings": [[ring_from_shapely(g.exterior.coords, exact)] for g in cand], "shapely": MultiPolygon(cand),
        "source": "Derived: Marine Regions high-seas pockets minus every Marine Regions extended-continental-shelf polygon (CLCS recommendation, submission, overlapping claim, DOALOS deposit; ECS v2, CC BY 4.0) minus Kartverket's Norwegian shelf and 200 nm zones; parts ≥ 1000 km²",
        "kartverket": [], "stats": {"parts": len(cand), "area_km2": round(sum(g.area for g in cand) / 1e6)}}
    for g in cand:
        c = g.representative_point(); lon, lat = inv(c.x, c.y)
        print(f"  the-area candidate: {g.area/1e6:.0f} km2 near ({lon:.2f}, {lat:.2f})")

    # ---- national airspace: everything landward of the 12 nm limit (land + internal waters + territorial sea)
    print("National airspace:")
    feats_ = kv("Territorialområde", "Fastlands-Norge") if any(f.ftype == "Territorialområde" and "Fastlands" in f.name for f in polys) \
        else [f for f in polys if f.ftype == "Territorialområde" and f.props.get("land") == "NO"]
    assert len(feats_) == 1, [f.name for f in feats_]
    stats = {"matched": 0, "unmatched": 0, "simplified_away": 0}
    rings = [ring_from_routeb(r, src, stats) for r in feats_[0].rings]
    # The land border (Riksgrense) is the only unmatched run: simplify it, keeping every matched vertex.
    def simplify_unmatched_runs(ring: list[Vertex], tol: float) -> list[Vertex]:
        out: list[Vertex] = []
        i, n = 0, len(ring)
        while i < n:
            if ring[i].text is not None:
                out.append(ring[i]); i += 1; continue
            j = i
            while j < n and ring[j].text is None:
                j += 1
            run = ring[max(i - 1, 0):min(j + 1, n)]
            simp = LineString([(v.x, v.y) for v in run]).simplify(tol, preserve_topology=True).coords
            keep = set(simp)
            out.extend(v for v in ring[i:j] if (v.x, v.y) in keep)
            i = j
        return out
    rings = [simplify_unmatched_runs(r, args.coast_tolerance) for r in rings]
    land_border_vertices = sum(1 for r in rings for v in r if v.text is None)
    mainland_air = to_shapely(rings)
    assert mainland_air.is_valid, "national airspace (mainland) invalid after land-border simplification"
    parts = [mainland_air] + [Polygon(g.exterior.coords) for z in ("svalbard-territorial-sea", "janmayen-territorial-sea") for g in parts_of(zones[z]["shapely"])]
    zones["national-airspace"] = {"rings": [rings] + [[ring_from_shapely(g.exterior.coords, exact)] for g in parts[1:]], "shapely": MultiPolygon(parts),
        "source": "Mainland: Kartverket Norges maritime grenser - Territorialområde ved Fastlands-Norge (12 nm limit + delimitation lines + Riksgrense land border, border simplified); Svalbard and Jan Mayen: the 12 nm limits as closed loops (exterior rings of the territorial-sea polygons)",
        "kartverket": [{k: v for k, v in feats_[0].props.items() if k in KV_KEYS}], "stats": {**stats, "land_border_vertices": land_border_vertices, "land_border_tolerance_m": args.coast_tolerance}}
    print(f"  {'national-airspace':34s} {sum(len(r) for g in zones['national-airspace']['rings'] for r in g):6d} vertices  parts={len(parts)}  {stats} land-border={land_border_vertices}")

    # ---- contested extent on the continental shelf (owner instruction 2026-09-17): the part of the
    # shelf lying within the 200 nm zone around Svalbard.  Proxy extent — see PROVENANCE §8.
    fpz_filled = unary_union([Polygon(g.exterior.coords) for g in parts_of(zones["svalbard-fpz"]["shapely"])])
    ce = zones["continental-shelf"]["shapely"].intersection(fpz_filled)
    ce_parts = parts_of(ce)   # holes kept: the territorial seas are not continental shelf
    zones["continental-shelf"]["contestedExtent"] = {"rings": [rings_of(g, exact) for g in ce_parts],
                                                     "area_km2": round(sum(g.area for g in ce_parts) / 1e6)}
    print(f"  continental-shelf contested extent: {sum(len(r) for g in zones['continental-shelf']['contestedExtent']['rings'] for r in g)} vertices, {zones['continental-shelf']['contestedExtent']['area_km2']} km2")
    # Interval between the two readings (owner instruction, round 3): the Norwegian shelf beyond 200 nm
    # that adjoins the Svalbard zone and no other Norwegian 200 nm zone (the Nansen Basin) — inside the
    # wider reading (all shelf generated from Svalbard), outside the narrower one (within 200 nm).
    other_filled = unary_union([Polygon(g.exterior.coords) for z in ("mainland-eez", "janmayen-fisheries-zone") for g in parts_of(zones[z]["shapely"])])
    interval = [Polygon(g.exterior.coords) for g in parts_of(zones["continental-shelf"]["shapely"].difference(filled))
                if g.area > 1e9 and g.distance(fpz_filled) < 1.0 and g.distance(other_filled) > 1000.0]
    zones["continental-shelf"]["contestedExtentInterval"] = {"rings": [[ring_from_shapely(g.exterior.coords, exact)] for g in interval],
                                                             "area_km2": round(sum(g.area for g in interval) / 1e6)}
    print(f"  continental-shelf contested interval: {len(interval)} part(s), {zones['continental-shelf']['contestedExtentInterval']['area_km2']} km2")

    # ---- write
    total = 0
    out = {"meta": {"crs": "EPSG:4326 (ETRS89/WGS84 treated as identical; see PROVENANCE)", "arc_tolerance_m": args.arc_tolerance,
                    "coast_tolerance_m": args.coast_tolerance, "min_island_km2": args.min_island,
                    "excluded": [{"geography": "bouvetoya", "reason": "Owner decision 2026-09-17: out of scope"}]},
           "zones": {}}
    for zid, z in zones.items():
        polys_ = [poly_vertices(r) for r in z["rings"]]
        n = sum(len(r) for p in polys_ for r in p)
        total += n
        geom = {"type": "MultiPolygon", "coordinates": polys_} if len(polys_) != 1 else {"type": "Polygon", "coordinates": polys_[0]}
        out["zones"][zid] = {"geometry": geom, "vertexCount": n, "source": z["source"], "kartverket": z["kartverket"], "stats": z["stats"], "notes": notes.get(zid, [])}
        for field in ("contestedExtent", "contestedExtentInterval"):
            if field in z:
                cps = [poly_vertices(r) for r in z[field]["rings"]]
                out["zones"][zid][field] = {"type": "MultiPolygon", "coordinates": cps} if len(cps) != 1 else {"type": "Polygon", "coordinates": cps[0]}
                out["zones"][zid][field + "VertexCount"] = sum(len(r) for c in cps for r in c)
    # Owner decision 2026-09-17 (round 3): no historical lines at all — only current, UNCLOS-relevant
    # lines are used.  Layers 1–4 (1/4/6/10 nm) are read for indexing but nothing is emitted from them.
    out["overlays"] = {}
    out["meta"]["zoneVertexCount"] = total
    out["meta"]["overlayVertexCount"] = sum(o["vertexCount"] for o in out["overlays"].values())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(dumps(out), encoding="utf-8", newline="\n")
    print(f"\nTotal zone polygon vertices: {total}  (budget 35 000, SPEC §8 as amended)   overlays: {out['meta']['overlayVertexCount']}\nWrote {args.out}")
    return 0


def dumps(obj) -> str:
    """Compact JSON where _Raw strings are emitted verbatim (numeric text)."""
    def enc(o):
        if isinstance(o, _Raw):
            return str.__str__(o)
        if isinstance(o, dict):
            return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + enc(v) for k, v in o.items()) + "}"
        if isinstance(o, (list, tuple)):
            return "[" + ",".join(enc(v) for v in o) + "]"
        return json.dumps(o, ensure_ascii=False)
    return enc(obj) + "\n"


if __name__ == "__main__":
    sys.exit(main())
