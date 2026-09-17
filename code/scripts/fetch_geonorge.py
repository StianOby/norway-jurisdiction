#!/usr/bin/env python3
"""Fetch Route B (Geonorge) sources — SPEC §2.1 / §3.2.

1. Norges maritime grenser, GML, EPSG:4258, whole country  -> data/raw/geonorge/<zip as delivered>
   (the authoritative dataset; holds Kartverket's official zone polygons)
2. N1000 Kartdata, GML, EPSG:4258, whole country           -> data/raw/geonorge/n1000-coast.geojson
   Only Kystkontur (coastline) and Havflate (sea surface) from the Arealdekke file
   are kept, as a compact GeoJSON; the 21 MB zip itself is not committed.

Geonorge's download API takes an "order" and returns direct links; no login is
needed for these open datasets.  Every file's SHA-256 is written to
data/raw/geonorge/FETCH_LOG.json.  Stdlib only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repository root (scripts live in code/scripts/)

ORDER_URL = "https://nedlasting.geonorge.no/api/order"
MARITIME_UUID = "e106adf4-c9d8-4fce-a9b5-7886a4126d23"   # Norges maritime grenser
N1000_UUID = "aee42bb6-d0e9-4d70-86fe-6ea76c381055"      # N1000 Kartdata
USER_AGENT = "norway-jurisdiction/0.1 (teaching model, UiO)"


def order(uuids: list[str]) -> list[dict]:
    body = {"email": "", "orderLines": [
        {"metadataUuid": u, "areas": [{"code": "0000", "type": "landsdekkende", "name": "Hele landet"}],
         "projections": [{"code": "4258"}], "formats": [{"name": "GML"}]} for u in uuids]}
    req = urllib.request.Request(ORDER_URL, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["files"]


def download(url: str, dest: Path) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    h = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=600) as r, dest.open("wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
            h.update(chunk)
    return h.hexdigest()


def extract_n1000_coast(zip_path: Path, out: Path) -> dict:
    """Pull Kystkontur + Havflate out of the Arealdekke GML with a streaming regex.

    Axis order in EPSG:4258 GML is lat lon; GeoJSON wants lon lat.  Coordinates are
    kept as the 6-decimal strings Kartverket delivered."""
    with zipfile.ZipFile(zip_path) as z:
        name = next(n for n in z.namelist() if "Arealdekke" in n)
        text = z.read(name).decode("utf-8")
    feats = []
    counts = {"Kystkontur": 0, "Havflate": 0}
    for tag in ("Kystkontur", "Havflate"):
        for m in re.finditer(rf"<app:{tag}\b.*?</app:{tag}>", text, re.S):
            block = m.group(0)
            gid = re.search(r'gml:id="([^"]+)"', block).group(1)
            if tag == "Kystkontur":
                pl = re.search(r"<gml:posList>([^<]+)</gml:posList>", block).group(1).split()
                coords = [[pl[i + 1], pl[i]] for i in range(0, len(pl), 2)]
                geom = {"type": "LineString", "coordinates": coords}
            else:
                ext = re.search(r"<gml:exterior>(.*?)</gml:exterior>", block, re.S).group(1)
                rings = [_ring(ext)]
                for inner in re.findall(r"<gml:interior>(.*?)</gml:interior>", block, re.S):
                    rings.append(_ring(inner))
                geom = {"type": "Polygon", "coordinates": rings}
            feats.append({"type": "Feature", "id": gid, "properties": {"type": tag}, "geometry": geom})
            counts[tag] += 1
    # Write compact; coordinate strings become JSON numbers verbatim via a tiny custom encoder.
    s = json.dumps({"type": "FeatureCollection", "source": f"{zip_path.name} / {name}", "features": feats},
                   separators=(",", ":"), ensure_ascii=False)
    s = re.sub(r'"(-?\d+\.\d+)"', r"\1", s)  # unquote numeric strings
    out.write_text(s, encoding="utf-8", newline="\n")
    return counts


def _ring(xml: str) -> list[list[str]]:
    pts: list[list[str]] = []
    for pl in re.findall(r"<gml:posList>([^<]+)</gml:posList>", xml):
        v = pl.split()
        seg = [[v[i + 1], v[i]] for i in range(0, len(v), 2)]
        if pts and pts[-1] == seg[0]:
            seg = seg[1:]
        pts.extend(seg)
    return pts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "data/raw/geonorge")
    ap.add_argument("--keep-zips", type=Path, default=ROOT / "data/tmp/geonorge-zips", help="where the big zips are kept")
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    args.keep_zips.mkdir(parents=True, exist_ok=True)

    log = {"fetched_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(), "files": {}}
    for f in order([MARITIME_UUID, N1000_UUID]):
        assert f["status"] == "ReadyForDownload", f
        is_maritime = f["metadataUuid"] == MARITIME_UUID
        dest = (args.out if is_maritime else args.keep_zips) / f["name"]
        sha = download(f["downloadUrl"], dest)
        entry = {"url": f["downloadUrl"], "metadataUuid": f["metadataUuid"], "projection": f["projection"],
                 "bytes": dest.stat().st_size, "sha256": sha, "committed": is_maritime}
        print(f"{f['name']:64s} {dest.stat().st_size:10d} B  {sha[:12]}")
        if not is_maritime:
            coast = args.out / "n1000-coast.geojson"
            entry["extracted"] = {"to": coast.name, **extract_n1000_coast(dest, coast)}
            entry["extracted"]["sha256"] = hashlib.sha256(coast.read_bytes()).hexdigest()
            print(f"  -> {coast} {entry['extracted']}")
        log["files"][f["name"]] = entry
    (args.out / "FETCH_LOG.json").write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
