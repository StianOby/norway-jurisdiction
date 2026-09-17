#!/usr/bin/env python3
"""Fetch the 12 layers of Kartverket's "Norges maritime grenser" (SPEC §2.1, Route A).

Writes each ArcGIS REST response body *verbatim* (bytes, not re-serialised) to
<out>/<n>-<slug>.geojson, so a re-fetch diffs cleanly against the committed
snapshot in data/raw/.  A fetch log with timestamp and SHA-256 per file is
written to <out>/FETCH_LOG.json.

Usage:
    python scripts/fetch_boundaries.py --out data/tmp/refetch      # safe default target
    python scripts/fetch_boundaries.py --out data/raw               # replace the snapshot (deliberate!)
    python scripts/fetch_boundaries.py --out X --compare data/raw   # fetch and report byte diff

Stdlib only on purpose (see CLAUDE.md).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repository root (scripts live in code/scripts/)

SERVICE = "https://portal.fiskeridir.no/arcgis/rest/services/Norges_maritime_grenselinjer/MapServer"
QUERY = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "true",
    "outSR": "4326",
    "f": "geojson",
}

# Layer index -> file slug.  Order and names match SPEC §2.2 / data/PROVENANCE.md.
LAYERS = {
    0: "grunnlinje",
    1: "1nm",
    2: "4nm",
    3: "6nm",
    4: "10nm",
    5: "territorialgrense-12nm",
    6: "tilstotende-sone-24nm",
    7: "200nm",
    8: "avtalt-avgrensningslinje",
    9: "yttergrense-kontinentalsokkel",
    10: "avgrensningslinje-kontinentalsokkel",
    11: "andre-staters-eez",
}

USER_AGENT = "norway-jurisdiction/0.1 (+https://github.com/stianoby/norway-jurisdiction; teaching model, UiO)"


def layer_url(layer: int) -> str:
    return f"{SERVICE}/{layer}/query?" + urllib.parse.urlencode(QUERY)


def fetch(url: str, retries: int = 3, timeout: float = 60.0) -> bytes:
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json, application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
            # ArcGIS returns HTTP 200 with a JSON error object on failure — detect that.
            head = body.lstrip()[:200]
            if head.startswith(b'{"error"'):
                raise RuntimeError(f"ArcGIS error: {body[:300]!r}")
            return body
        except (urllib.error.URLError, TimeoutError, RuntimeError) as e:  # noqa: PERF203
            last = e
            if attempt < retries:
                time.sleep(2 * attempt)
    raise RuntimeError(f"failed after {retries} attempts: {url}\n{last}")


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "data/tmp/refetch", help="output directory (default: <repo>/data/tmp/refetch)")
    ap.add_argument("--compare", type=Path, help="directory to compare byte-for-byte against after fetching (e.g. data/raw)")
    ap.add_argument("--layers", type=int, nargs="*", help="subset of layer indices (default: all 12)")
    args = ap.parse_args(argv)

    layers = args.layers if args.layers else sorted(LAYERS)
    args.out.mkdir(parents=True, exist_ok=True)
    fetched_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    log: dict = {"fetched_at_utc": fetched_at, "service": SERVICE, "query": QUERY, "files": {}}

    for layer in layers:
        name = f"{layer}-{LAYERS[layer]}.geojson"
        url = layer_url(layer)
        body = fetch(url)
        # Sanity: it must parse as a FeatureCollection.  We validate but never re-serialise.
        fc = json.loads(body)
        if fc.get("type") != "FeatureCollection":
            raise SystemExit(f"{name}: not a FeatureCollection")
        nfeat = len(fc["features"])
        nvert = sum(
            len(g["coordinates"]) if g["type"] == "LineString" else sum(len(p) for p in g["coordinates"])
            for g in (f["geometry"] for f in fc["features"])
        )
        (args.out / name).write_bytes(body)
        log["files"][name] = {"url": url, "bytes": len(body), "sha256": sha256(body), "features": nfeat, "vertices": nvert}
        print(f"{name:48s} {nfeat:3d} feat {nvert:5d} vert {len(body):7d} B  {sha256(body)[:12]}")

    (args.out / "FETCH_LOG.json").write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.compare:
        print(f"\nComparing against {args.compare}:")
        identical = True
        for name in log["files"]:
            ref = args.compare / name
            if not ref.exists():
                print(f"  {name}: MISSING in reference")
                identical = False
                continue
            same = ref.read_bytes() == (args.out / name).read_bytes()
            identical &= same
            print(f"  {name:48s} {'identical' if same else 'DIFFERENT'}")
        print("\nRESULT:", "all files byte-identical" if identical else "DIFFERENCES FOUND")
        return 0 if identical else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
