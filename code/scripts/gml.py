"""Minimal reader for Kartverket's "Norges maritime grenser" GML 3.2 delivery (Route B, SPEC §2.1).

Coordinates are returned as the *decimal strings* found in the file, not floats,
so that byte-level comparison with Route A is possible.  Convert with float()
when you need numbers.

Only the subset of GML this dataset uses is handled: LineString and Surface
(PolygonPatch with exterior/interior LinearRings), all via gml:posList.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

NS = {
    "gml": "http://www.opengis.net/gml/3.2",
    "app": "http://skjema.geonorge.no/SOSI/produktspesifikasjon/NorgesMaritimeGrenser/20211115",
}
SKIP_PROPS = {"identifikasjon", "kvalitet", "grense", "område", "posisjon"}


@dataclass
class Feature:
    ftype: str                     # e.g. "Territorialgrense"
    gml_id: str
    props: dict[str, str]
    srs: str                       # e.g. "EPSG:25833"
    geom_type: str                 # "LineString" | "Polygon" | "Point"
    # LineString: [ring]; Polygon: [exterior, *interiors]; each ring = list of (x, y) strings
    rings: list[list[tuple[str, str]]] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.props.get("virkeområdenavn", "")

    def as_float_rings(self) -> list[list[tuple[float, float]]]:
        return [[(float(x), float(y)) for x, y in r] for r in self.rings]


def _pos_list(el: ET.Element) -> list[tuple[str, str]]:
    toks = el.text.split()
    return [(toks[i], toks[i + 1]) for i in range(0, len(toks), 2)]


def _local(tag: str) -> str:
    return tag.split("}", 1)[1]


def _inside_surface(el: ET.Element, ft: ET.Element) -> bool:
    """True if el is a LineString nested inside a Surface (a ring curve member), not a top-level geometry."""
    if _local(el.tag) != "LineString":
        return False
    parents = {c: p for p in ft.iter() for c in p}
    p = parents.get(el)
    while p is not None:
        if _local(p.tag) == "Surface":
            return True
        p = parents.get(p)
    return False


def _ring(boundary: ET.Element) -> list[tuple[str, str]]:
    """A gml:exterior/gml:interior holds either a gml:LinearRing, or a gml:Ring of one or
    more curveMember LineStrings — concatenate those, dropping the duplicated join vertex."""
    lr = boundary.find("gml:LinearRing/gml:posList", NS)
    if lr is not None:
        return _pos_list(lr)
    ring: list[tuple[str, str]] = []
    for ls in boundary.findall("gml:Ring/gml:curveMember/gml:LineString", NS):
        pts = _pos_list(ls.find("gml:posList", NS))
        if ring and ring[-1] == pts[0]:
            pts = pts[1:]
        ring.extend(pts)
    if not ring:
        raise ValueError("empty ring")
    return ring


def read(path) -> list[Feature]:
    """`path` may be a filename or an open binary file object (e.g. from a zip)."""
    root = ET.parse(path).getroot()
    out: list[Feature] = []
    for fm in root.findall("gml:featureMember", NS):
        ft = fm[0]
        props: dict[str, str] = {}
        for child in ft:
            t = _local(child.tag)
            if t in SKIP_PROPS:
                continue
            props[t] = (child.text or "").strip()
        srs = ""
        geom_type = ""
        rings: list[list[tuple[str, str]]] = []
        geoms = [el for el in ft.iter() if _local(el.tag) in ("LineString", "Surface", "Point") and not _inside_surface(el, ft)]
        if len(geoms) != 1:
            raise ValueError(f"{ft.get('{%s}id' % NS['gml'])}: expected one geometry, found {len(geoms)}")
        el = geoms[0]
        t = _local(el.tag)
        srs = el.get("srsName", "")
        if t == "LineString":
            geom_type = "LineString"
            rings = [_pos_list(el.find("gml:posList", NS))]
        elif t == "Surface":
            geom_type = "Polygon"
            patches = el.findall("gml:patches/gml:PolygonPatch", NS)
            if len(patches) != 1:
                raise ValueError(f"{ft.get('{%s}id' % NS['gml'])}: {len(patches)} patches")
            p = patches[0]
            rings = [_ring(p.find("gml:exterior", NS))]
            for inner in p.findall("gml:interior", NS):
                rings.append(_ring(inner))
        elif t == "Point":
            geom_type = "Point"
            pos = el.find("gml:pos", NS).text.split()
            rings = [[(pos[0], pos[1])]]
        srs = srs.replace("urn:ogc:def:crs:EPSG::", "EPSG:")
        out.append(Feature(_local(ft.tag), ft.get("{%s}id" % NS["gml"], ""), props, srs, geom_type, rings))
    return out


def axis_order_is_lat_lon(srs: str) -> bool:
    """EPSG:4258 in GML 3.2 uses lat,lon axis order.  Check with a sample before trusting."""
    return srs == "EPSG:4258"
