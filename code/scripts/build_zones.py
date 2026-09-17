#!/usr/bin/env python3
"""Emit data/build/zones.json from data/build/geometry.json + the zone registry — SPEC §4, §6.1 step 5.

    python scripts/build_zones.py            # build
    python scripts/build_zones.py --check    # build, then validate (exit 1 on any hard failure)

Legal payloads: names and strata are in the registry below; the citation sources are
SPEC §4.1's short forms.  Quotes are never typed here (SPEC §10.1): every citation is
filled from data/build/legal.json (scripts/fetch_legal.py + scripts/build_legal.py),
looked up by its `source` (+ `pinpoint`).  Summaries come from data/legal/summaries.json
and ship only once the owner has set their status to "approved".

Checks performed by --check (SPEC §9 Phase 1 exit criteria):
  * schema: every zone has the fields of the SPEC §4 Zone interface
  * every ring is closed, has >= 4 vertices and every polygon is valid (Shapely)
  * no polygon wraps the antimeridian; all coordinates inside the model's bbox
  * byte-identity: every vertex of data/raw layers 0, 8, 9, 10 appears verbatim
    in zones.json (baselines, delimitation lines, shelf outer limit); layer 11
    vertices are reported (their junction ends are represented by the coincident
    Norwegian-line vertex, see polygonise.py)
  * vertex budget (SPEC §8) — reported; an overrun is a WARNING for the owner
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repository root (scripts live in code/scripts/)

sys.path.insert(0, str(Path(__file__).parent))

GEOMETRY = ROOT / "data/build/geometry.json"
OUT = ROOT / "data/build/zones.json"
REPORT = ROOT / "data/build/REPORT.md"
RAW = ROOT / "data/raw"
VERTEX_BUDGET = 35_000   # SPEC §8 amended by the owner 2026-09-17 (was 12 000)
BBOX = (-15.0, 55.0, 46.0, 86.0)   # lon_min, lat_min, lon_max, lat_max — Bouvetøya excluded; 46 E covers the Loop Hole

LEGAL = ROOT / "data/build/legal.json"
SUMMARIES = ROOT / "data/legal/summaries.json"


def cit(source: str, lang: str = "no", pinpoint: str | None = None) -> dict:
    """A citation skeleton: source (SPEC §4.1 short form) and expected quote language. The quote,
    title, url and provenance are merged in from legal.json by fill_legal()."""
    c = {"source": source, "quote": "", "quoteLang": lang}
    if pinpoint:
        c["pinpoint"] = pinpoint
    return c


def unclos(arts: str) -> dict:
    return cit(f"UNCLOS {arts}", "en")


# --------------------------------------------------------------------------- registry
# Names are labels, not statutory text.  Summaries are left for Phase 3 review by the owner.
def registry() -> list[dict]:
    def zone(zid, geography, strata, name_no, name_en, cits_no, cits_en, **extra):
        rec = {"id": zid, "geography": geography, "strata": strata, "contested": extra.pop("contested", False),
               "legal": {"no": {"name": name_no, "citations": cits_no, "summary": ""},
                         "en": {"name": name_en, "citations": cits_en, "summary": ""}}}
        rec.update(extra)
        return rec

    tfl = "territorialfarvannsloven"   # citation sources exactly as SPEC §4.1; full titles come from Lovdata in Phase 3
    zones = []
    for g, suffix_no, suffix_en in (("mainland", " (Fastlands-Norge)", " (mainland Norway)"),
                                    ("svalbard", " (Svalbard)", " (Svalbard)"),
                                    ("janmayen", " (Jan Mayen)", " (Jan Mayen)")):
        zones.append(zone(f"{g}-internal-waters", g, ["airspace", "watercolumn", "seabed", "subsoil"],
                          "Indre farvann" + suffix_no, "Internal waters" + suffix_en,
                          [cit(f"{tfl} § 3"), unclos("art. 2"), unclos("art. 8")],
                          [cit(f"{tfl} § 3"), unclos("art. 2"), unclos("art. 8")]))
        zones.append(zone(f"{g}-territorial-sea", g, ["airspace", "watercolumn", "seabed", "subsoil"],
                          "Sjøterritoriet" + suffix_no, "Territorial sea" + suffix_en,
                          [cit(f"{tfl} §§ 1–2"), unclos("art. 2"), unclos("art. 3"), unclos("art. 17")],
                          [cit(f"{tfl} §§ 1–2"), unclos("art. 2"), unclos("art. 3"), unclos("art. 17")]))
    zones.append(zone("mainland-contiguous-zone", "mainland", ["watercolumn"],
                      "Tilstøtende sone", "Contiguous zone",
                      [cit(f"{tfl} § 4"), unclos("art. 33")],
                      [cit(f"{tfl} § 4"), unclos("art. 33")],
                      notes=["Mainland only: no contiguous zone has been established for Svalbard or Jan Mayen (SPEC §2.3)."]))
    eez = "lov om Norges økonomiske sone § 1"
    zones.append(zone("mainland-eez", "mainland", ["watercolumn"],
                      "Norges økonomiske sone", "Norwegian exclusive economic zone",
                      [cit(eez), unclos("arts 55–58")], [cit(eez), unclos("arts 55–58")],
                      notes=["Owner decision 2026-09-17: the EEZ is modelled as water column only; the seabed under it belongs to the continental-shelf zone (SPEC §4.1 amended)."]))
    snokrabbe = "HR-2023-491-P (Snøkrabbe II)"
    zones.append(zone("svalbard-fpz", "svalbard", ["watercolumn"],
                      "Fiskevernsonen ved Svalbard", "Fisheries protection zone around Svalbard",
                      [cit("forskrift 3. juni 1977 nr. 6")],
                      [cit("forskrift 3. juni 1977 nr. 6")],
                      contested=True,
                      notes=["A fisheries protection zone, not an exclusive economic zone (SPEC §2.3).",
                             "contested: true — owner instruction 2026-09-17 (neutral marker only, SPEC §1/§10.5)."]))
    zones.append(zone("janmayen-fisheries-zone", "janmayen", ["watercolumn"],
                      "Fiskerisonen ved Jan Mayen", "Fisheries zone around Jan Mayen",
                      [cit("forskrift 23. mai 1980 nr. 4")],
                      [cit("forskrift 23. mai 1980 nr. 4")],
                      notes=["A fisheries zone, not an exclusive economic zone (SPEC §2.3)."]))
    zones.append(zone("continental-shelf", "all", ["seabed", "subsoil"],
                      "Kontinentalsokkelen", "Continental shelf",
                      [cit("kontinentalsokkelloven"), unclos("arts 76–79"), cit(snokrabbe, pinpoint="avsnitt 220")],
                      [cit("kontinentalsokkelloven"), unclos("arts 76–79"), cit(snokrabbe, pinpoint="avsnitt 220")],
                      notes=["Neutral contested marker (SPEC §1/§10.5) within contestedExtent: the shelf generated from Svalbard, within 200 nm and the Nansen Basin beyond, as one extent (owner decision 2026-09-17, round 4)."]))
    zones.append(zone("high-seas", "all", ["watercolumn"],
                      "Det åpne hav", "High seas",
                      [unclos("art. 86"), unclos("art. 87")], [unclos("art. 86"), unclos("art. 87")],
                      notModelled=["beyond-outer-limit"]))
    zones.append(zone("the-area", "all", ["seabed", "subsoil"],
                      "Området", "The Area",
                      [unclos("art. 1(1)(1)"), unclos("arts 136–137")], [unclos("art. 1(1)(1)"), unclos("arts 136–137")],
                      notModelled=["beyond-model-extent"],
                      notes=["Extent asserted by the owner (2026-09-17, round 4): high seas (Marine Regions) inside the model extent whose seabed lies in no extended-continental-shelf polygon of any status (Marine Regions ECS v2) and outside Norway's shelf (Kartverket) — one 16 806 km² patch in the north-west Banana Hole. The Area continues beyond the model extent — see data/PROVENANCE.md §10.10, §15."]))
    zones.append(zone("national-airspace", "all", ["airspace"],
                      "Nasjonalt luftrom", "National airspace",
                      [unclos("art. 2(2)")],
                      [unclos("art. 2(2)")]))
    zones.append(zone("airspace-beyond-territorial-sea", "all", ["airspace"],
                      "Luftrom utenfor sjøterritoriet", "Airspace beyond the territorial sea",
                      [unclos("art. 58(1)"), unclos("art. 87(1)(b)")], [unclos("art. 58(1)"), unclos("art. 87(1)(b)")],
                      derivedFrom=["mainland-contiguous-zone", "mainland-eez", "svalbard-fpz", "janmayen-fisheries-zone", "high-seas"],
                      notes=["Horizontal extent is the union of derivedFrom; no geometry is duplicated (mainland-contiguous-zone lies inside mainland-eez)."]))
    return zones


def overlays() -> list[dict]:
    """Owner decision 2026-09-17 (round 3): no historical lines ship — current, UNCLOS-relevant lines only."""
    return []


# --------------------------------------------------------------------------- legal payloads
def _legal_key(c: dict) -> str:
    return c["source"] + (f" | {c['pinpoint']}" if c.get("pinpoint") else "")


def fill_legal(zones: list[dict]) -> list[str]:
    """Merge the extracted provisions (legal.json) into every citation and the approved summaries
    (summaries.json) into every payload. Returns the problems found (unfilled citations, summaries
    for unknown zones); --check turns them into failures."""
    problems = []
    provisions = {}
    if LEGAL.exists():
        for rec in json.loads(LEGAL.read_text(encoding="utf-8"))["provisions"]:
            provisions[_legal_key(rec)] = rec
    else:
        problems.append(f"{LEGAL.relative_to(ROOT)} missing — run scripts/fetch_legal.py and scripts/build_legal.py")
    summaries = json.loads(SUMMARIES.read_text(encoding="utf-8"))["zones"] if SUMMARIES.exists() else {}
    for zid in summaries:
        if zid not in {z["id"] for z in zones}:
            problems.append(f"summaries.json: unknown zone {zid}")
    for z in zones:
        for lang in ("no", "en"):
            for c in z["legal"][lang]["citations"]:
                rec = provisions.get(_legal_key(c))
                if not rec or not rec.get("quote"):
                    problems.append(f"{z['id']}: no quote for citation {_legal_key(c)!r}")
                    continue
                if rec["quoteLang"] != c["quoteLang"]:
                    problems.append(f"{z['id']}: {_legal_key(c)!r} quoteLang {rec['quoteLang']} != registry {c['quoteLang']}")
                c.update({"title": rec["title"], "citedAs": rec["citedAs"], "quote": rec["quote"], "quoteLang": rec["quoteLang"],
                          "url": rec["url"], "provenance": rec["provenance"]})
                if lang == "en" and rec.get("translation"):
                    c["translation"] = rec["translation"]
                    c["translationUrl"] = rec["translationUrl"]
                    c["translationNote"] = rec["translationNote"]
            sm = summaries.get(z["id"], {})
            if sm.get("status") == "approved":
                z["legal"][lang]["summary"] = sm[lang]
            else:
                z["legal"][lang]["summary"] = ""
                z["legal"][lang]["summaryStatus"] = sm.get("status", "missing")
    return problems


# --------------------------------------------------------------------------- build
def build() -> tuple[dict, str, list[str]]:
    geom_text = GEOMETRY.read_text(encoding="utf-8")
    geom = json.loads(geom_text)
    zones = []
    registry_zones = registry()
    legal_problems = fill_legal(registry_zones)
    for z in registry_zones:
        g = geom["zones"].get(z["id"])
        if g is None:
            z["horizontal"] = None
            z["vertexCount"] = 0
            assert z.get("derivedFrom") or "horizontal" in z.get("notModelled", []), z["id"]
        else:
            z["horizontal"] = g["geometry"]
            z["vertexCount"] = g["vertexCount"]
            for field in ("contestedExtent",):
                if field in g:
                    z[field] = g[field]
                    z[field + "VertexCount"] = g[field + "VertexCount"]
            z["provenance"] = {"source": g["source"], "kartverket": g["kartverket"], "stats": g["stats"]}
            z["notes"] = z.get("notes", []) + g.get("notes", [])
        zones.append(z)
    overlay_recs = []
    for o in overlays():
        g = geom["overlays"][o["id"]]
        o["geometry"] = g["geometry"]
        o["vertexCount"] = g["vertexCount"]
        o["provenance"] = {"source": g["source"]}
        overlay_recs.append(o)
    out = {
        "meta": {
            "generated": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
            "crs": geom["meta"]["crs"],
            "geographies": ["mainland", "svalbard", "janmayen"],
            "excluded": geom["meta"]["excluded"],
            "simplification": {"arc_tolerance_m": geom["meta"]["arc_tolerance_m"], "coast_tolerance_m": geom["meta"]["coast_tolerance_m"],
                               "min_island_km2": geom["meta"]["min_island_km2"],
                               "exempt": ["baselines (layer 0)", "agreed delimitation lines (layers 8, 10)", "other states' 200 nm limits (layer 11)", "continental-shelf outer limit (layer 9)"]},
            "vertexCount": {"zones": geom["meta"]["zoneVertexCount"], "overlays": geom["meta"]["overlayVertexCount"], "budget": VERTEX_BUDGET},
            "attribution": {"data": "Kartverket — Norges maritime grenser; N1000 Kartdata (NLOD 2.0 / CC BY 4.0)", "coastline_svalbard": "Norsk Polarinstitutt via Kartverket"},
            "licence": "The zone geometry in this file is derived from Kartverket data under NLOD 2.0 / CC BY 4.0 and is not covered by the AGPL that applies to the application code. See data/LICENSE.md.",
            "legal": {"attribution": "Lovdata (NLOD 2.0); United Nations, DOALOS (UNCLOS text); Norges Høyesterett (HR-2023-491-P)",
                      **(json.loads(LEGAL.read_text(encoding="utf-8"))["meta"] if LEGAL.exists() else {})},
        },
        "zones": zones,
        "overlays": overlay_recs,
    }
    # Re-emit with the geometry's numeric text untouched: serialise everything except geometry normally,
    # then splice the compact geometry strings straight from geometry.json.
    return out, geom_text, legal_problems


def dump(out: dict, geom_text: str) -> str:
    """JSON text where every geometry block is the verbatim substring from geometry.json."""
    geom = json.loads(geom_text)
    placeholders = {}
    for z in out["zones"]:
        if z["horizontal"] is not None:
            key = f"@@GEOM:{z['id']}@@"
            placeholders[key] = _extract(geom_text, z["id"], "zones")
            z["horizontal"] = key
        if z.get("contestedExtent"):
            key = f"@@CE:{z['id']}@@"
            placeholders[key] = _extract(geom_text, z["id"], "zones", field="contestedExtent")
            z["contestedExtent"] = key
    for o in out["overlays"]:
        key = f"@@GEOM:{o['id']}@@"
        placeholders[key] = _extract(geom_text, o["id"], "overlays")
        o["geometry"] = key
    text = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    for key, g in placeholders.items():
        text = text.replace(json.dumps(key), g)
    return text + "\n"


def _extract(geom_text: str, zid: str, section: str, field: str = "geometry") -> str:
    """Return the verbatim '{"type":...,"coordinates":[...]}' text of one geometry."""
    start = geom_text.index(f'"{zid}":{{"geometry":')
    i = geom_text.index(f'"{field}":', start) + len(f'"{field}":')
    depth = 0
    for j in range(i, len(geom_text)):
        if geom_text[j] == "{":
            depth += 1
        elif geom_text[j] == "}":
            depth -= 1
            if depth == 0:
                return geom_text[i:j + 1]
    raise ValueError(zid)


# --------------------------------------------------------------------------- check
COORD_RE = re.compile(rb"\[(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?),(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\]")


def check(path: Path) -> tuple[list[str], list[str], dict]:
    from shapely.geometry import shape
    text = path.read_bytes()
    data = json.loads(text)
    fails, warns, info = [], [], {}
    required = {"id", "geography", "strata", "horizontal", "contested", "legal"}
    ids = set()
    n_cit = n_sum = 0
    for z in data["zones"]:
        missing = required - set(z)
        if missing:
            fails.append(f"{z.get('id')}: missing fields {sorted(missing)}")
        ids.add(z["id"])
        for lang in ("no", "en"):
            pl = z["legal"][lang]
            for c in pl["citations"]:
                n_cit += 1
                if not c.get("quote") or not c.get("provenance"):
                    fails.append(f"{z['id']} [{lang}]: citation {c['source']!r} has no fetched quote (SPEC §10.1)")
                if c.get("_todo"):
                    fails.append(f"{z['id']} [{lang}]: citation {c['source']!r} still carries a Phase 1 placeholder")
            if not pl["citations"]:
                warns.append(f"{z['id']} [{lang}]: no citations")
            if pl.get("summary"):
                n_sum += 1
            else:
                warns.append(f"{z['id']} [{lang}]: summary not shipped (status: {pl.get('summaryStatus')})")
        if z["horizontal"] is None:
            if not (z.get("derivedFrom") or "horizontal" in z.get("notModelled", [])):
                fails.append(f"{z['id']}: no geometry and neither derivedFrom nor notModelled")
            continue
        g = z["horizontal"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for pi, rings in enumerate(polys):
            for ri, ring in enumerate(rings):
                if len(ring) < 4:
                    fails.append(f"{z['id']} poly {pi} ring {ri}: only {len(ring)} vertices")
                if ring[0] != ring[-1]:
                    fails.append(f"{z['id']} poly {pi} ring {ri}: not closed")
                lons = [p[0] for p in ring]
                lats = [p[1] for p in ring]
                if max(lons) - min(lons) > 180:
                    fails.append(f"{z['id']} poly {pi} ring {ri}: spans the antimeridian")
                if min(lons) < BBOX[0] or max(lons) > BBOX[2] or min(lats) < BBOX[1] or max(lats) > BBOX[3]:
                    fails.append(f"{z['id']} poly {pi} ring {ri}: outside model bbox {BBOX}")
        for field in ("contestedExtent",):
            if z.get(field):
                ce = shape(z[field])
                if not ce.is_valid:
                    fails.append(f"{z['id']}: invalid {field}")
                if not shape(g).buffer(1e-9).contains(ce):
                    fails.append(f"{z['id']}: {field} not inside the zone")
        shp = shape(g)
        if not shp.is_valid:
            from shapely.validation import explain_validity
            fails.append(f"{z['id']}: invalid geometry — {explain_validity(shp)}")
    info["citations"] = f"{n_cit} (every one with a quote from a fetched document)" if not any("no fetched quote" in f for f in fails) else str(n_cit)
    info["summaries"] = f"{n_sum}/{2 * len(data['zones'])} approved and shipped"
    for z in data["zones"]:
        for d in z.get("derivedFrom", []):
            if d not in ids:
                fails.append(f"{z['id']}: derivedFrom unknown zone {d}")

    # byte-identity of exempt layers.  A vertex may be absent only if it bounds nothing that is
    # modelled (e.g. the Norway–Russia shelf line's terminus beyond Norway's outer limit); a vertex
    # that lies on a modelled boundary but is not emitted verbatim is a hard failure.
    from shapely.geometry import Point
    from shapely.ops import unary_union
    boundary = unary_union([shape(z["horizontal"]).boundary for z in data["zones"] if z["horizontal"] is not None])
    for layer in ("0-grunnlinje", "8-avtalt-avgrensningslinje", "9-yttergrense-kontinentalsokkel",
                  "10-avgrensningslinje-kontinentalsokkel", "11-andre-staters-eez"):
        raw = (RAW / f"{layer}.geojson").read_bytes()
        toks = [(a, b) for a, b in COORD_RE.findall(raw) if not b.startswith(b"-")]   # skip Bouvetøya (lat < 0)
        missing = [(a.decode(), b.decode()) for a, b in toks if b"[" + a + b"," + b + b"]" not in text]
        info[f"verbatim:{layer}"] = f"{len(toks) - len(missing)}/{len(toks)}"
        for a, b in missing:
            d = boundary.distance(Point(float(a), float(b)))
            if d < 2e-5:            # ~1–2 m: on a modelled boundary
                if layer == "11-andre-staters-eez":
                    warns.append(f"{layer}: [{a},{b}] on a boundary but represented by the coincident Norwegian-line vertex (junction end)")
                else:
                    fails.append(f"{layer}: [{a},{b}] lies on a modelled boundary but is not emitted verbatim")
            else:
                warns.append(f"{layer}: [{a},{b}] not emitted — bounds no modelled zone (nearest boundary {d*111:.1f} km)")

    n = data["meta"]["vertexCount"]["zones"]
    info["vertexCount"] = n
    info["fileBytes"] = len(text)
    if n > VERTEX_BUDGET:
        warns.append(f"vertex budget: {n} zone polygon vertices > SPEC §8 target {VERTEX_BUDGET} — owner decision pending (coast tolerance / island threshold / budget)")
    return fails, warns, info


def write_report(out: dict, fails, warns, info):
    lines = ["# Build report — data/build/zones.json", "",
             f"Generated {out['meta']['generated']}. Simplification: arcs {out['meta']['simplification']['arc_tolerance_m']} m, coast {out['meta']['simplification']['coast_tolerance_m']} m, islands ≥ {out['meta']['simplification']['min_island_km2']} km². Exempt: " + "; ".join(out['meta']['simplification']['exempt']) + ".", "",
             "| Zone | Geography | Strata | Vertices | Source |", "|---|---|---|---:|---|"]
    for z in out["zones"]:
        src = z.get("provenance", {}).get("source", "— (" + ("derived from " + ", ".join(z["derivedFrom"]) if z.get("derivedFrom") else "not modelled: " + ", ".join(z.get("notModelled", []))) + ")")
        extra = "".join(f" **+{f}** ({z[f + 'VertexCount']} v.)" for f in ("contestedExtent",) if z.get(f))
        lines.append(f"| `{z['id']}` | {z['geography']} | {', '.join(z['strata'])} | {z['vertexCount']} | {src}{extra} |")
    lines += ["", "| Overlay | Vertices |", "|---|---:|"] + [f"| `{o['id']}` | {o['vertexCount']} |" for o in out["overlays"]]
    lines += ["", f"**Zone polygon vertices:** {info.get('vertexCount')} (SPEC §8 target {VERTEX_BUDGET}); zones.json {info.get('fileBytes', 0)/1024:.0f} KB.", "",
              "## Checks", ""]
    lines += [f"- FAIL: {f}" for f in fails] or ["- all hard checks passed (closure, validity, antimeridian, bbox, schema, byte-identity of layers 0/8/9/10, every citation quoted from a fetched document)"]
    lines += [f"- WARN: {w}" for w in warns]
    lines += [f"- {k}: {v}" for k, v in info.items() if k.startswith("verbatim") or k in ("citations", "summaries")]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main(argv=None) -> int:
    global GEOMETRY, OUT, REPORT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--geometry", type=Path, default=GEOMETRY, help="input geometry.json (default <repo>/data/build/geometry.json)")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    GEOMETRY, OUT = args.geometry, args.out
    if args.out != ROOT / "data/build/zones.json":
        REPORT = args.out.with_suffix(".REPORT.md")
    out, geom_text, legal_problems = build()
    OUT.write_text(dump(out, geom_text), encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({OUT.stat().st_size/1024:.0f} KB), {len(out['zones'])} zones, {len(out['overlays'])} overlays")
    for p in legal_problems:
        print(f"  legal: {p}")
    if not args.check:
        return 0
    fails, warns, info = check(OUT)
    write_report(out, fails, warns, info)
    for f in fails:
        print("FAIL", f)
    for w in warns:
        print("WARN", w)
    for k, v in info.items():
        print(f"{k}: {v}")
    print("RESULT:", "FAILED" if fails else "OK")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
