#!/usr/bin/env python3
"""Derive the schematic seabed class map from the coarse GEBCO grid (SPEC §3.3, §5.2).

Input : data/raw/gebco/gebco2020_0p25x0p5deg.json   (fetch_gebco.py, verbatim ERDDAP response)
Output: data/build/seabed.json   — one class letter per 0.25° x 0.5° cell plus per-class GEBCO
                                   statistics (so the owner can check the levels in code/src/config.js)
        docs/renders/seabed-schematic.png — class map, schematic surface, and GEBCO-vs-schematic
                                   cross-sections (with --render)

Classes (thresholds on a 3x3-median-filtered GEBCO elevation z, metres):
  L  land                      z >= 0
  T  Norwegian Trench          z <  -250 inside the trench box (lon 2–12 E, lat 56.5–62.5 N)
  S  continental shelf         -500 <= z < 0
  P  slope / plateau           -2500 <= z < -500
  A  abyssal plain             -3900 <= z < -2500
  N  deep Arctic basin         z < -3900
The *depths* the model draws for these classes are not here: they are the named levels in
code/src/config.js (SEABED.levels), read by this script only to draw the verification render.
The model smooths the level field with a Gaussian (SEABED.smoothingSigmaCells) — the same
algorithm as code/src/seabed.js — which is what produces the continental slope.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repository root (scripts live in code/scripts/)
RAW = ROOT / "data/raw/gebco/gebco2020_0p25x0p5deg.json"
OUT = ROOT / "data/build/seabed.json"
CONFIG = ROOT / "code/src/config.js"
RENDER = ROOT / "docs/renders/seabed-schematic.png"

TRENCH_BOX = (2.0, 56.5, 12.0, 62.5)   # lon_min, lat_min, lon_max, lat_max
THRESHOLDS = {"trench": -250, "shelf": -500, "slope": -2500, "abyssal": -3900}

# Cross-sections for the render: (label, (lon0, lat0), (lon1, lat1))
TRANSECTS = [
    ("Møre, 62.5°N westwards", (6.5, 62.5), (-3.0, 62.5)),
    ("Lofoten → Lofoten Basin", (14.5, 68.0), (2.0, 70.5)),
    ("Bergen, 60.4°N westwards (Norwegian Trench, North Sea plateau)", (5.2, 60.4), (0.0, 60.4)),
    ("Skagerrak, 8°E southwards", (8.0, 58.4), (8.0, 56.6)),
    ("Barents Sea, 29°E northwards to the Nansen Basin", (29.0, 70.8), (29.0, 83.0)),
    ("Svalbard west coast, 78°N → Fram Strait", (14.0, 78.0), (-2.0, 78.0)),
    ("Jan Mayen towards the south-east", (-8.5, 71.0), (-1.0, 69.0)),
]


def load_grid():
    rows = json.loads(RAW.read_text(encoding="utf-8"))["table"]["rows"]
    lats = sorted({r[0] for r in rows}); lons = sorted({r[1] for r in rows})
    li = {v: i for i, v in enumerate(lats)}; lo = {v: i for i, v in enumerate(lons)}
    z = [[None] * len(lons) for _ in lats]
    for lat, lon, e in rows:
        z[li[lat]][lo[lon]] = e
    assert all(v is not None for row in z for v in row)
    dlat = statistics.mean(b - a for a, b in zip(lats, lats[1:])); dlon = statistics.mean(b - a for a, b in zip(lons, lons[1:]))
    return lats, lons, z, dlat, dlon


def median3(z):
    n, m = len(z), len(z[0]); out = [[0] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            w = [z[a][b] for a in range(max(0, i - 1), min(n, i + 2)) for b in range(max(0, j - 1), min(m, j + 2))]
            out[i][j] = statistics.median(w)
    return out


def classify(z, lats, lons):
    n, m = len(z), len(z[0]); c = [[""] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            v = z[i][j]; lon, lat = lons[j], lats[i]
            if v >= 0:
                k = "L"
            elif TRENCH_BOX[0] <= lon <= TRENCH_BOX[2] and TRENCH_BOX[1] <= lat <= TRENCH_BOX[3] and v < THRESHOLDS["trench"]:
                k = "T"
            elif v >= THRESHOLDS["shelf"]:
                k = "S"
            elif v >= THRESHOLDS["slope"]:
                k = "P"
            elif v >= THRESHOLDS["abyssal"]:
                k = "A"
            else:
                k = "N"
            c[i][j] = k
    return c


def read_config_levels():
    s = CONFIG.read_text(encoding="utf-8")
    block = re.search(r"levels:\s*\{(.*?)\}", s, re.S).group(1)
    levels = {k: float(v) for k, v in re.findall(r"\b([LSTPAN]):\s*(-?\d+)", block)}
    sigma = float(re.search(r"smoothingSigmaCells:\s*([\d.]+)", s).group(1))
    return levels, sigma


def smooth(field, sigma):
    """Separable Gaussian, edge-clamped — identical to code/src/seabed.js."""
    r = max(1, int(math.ceil(3 * sigma))); k = [math.exp(-0.5 * (d / sigma) ** 2) for d in range(-r, r + 1)]; ks = sum(k)
    k = [v / ks for v in k]
    n, m = len(field), len(field[0])
    tmp = [[sum(k[d + r] * field[i][min(m - 1, max(0, j + d))] for d in range(-r, r + 1)) for j in range(m)] for i in range(n)]
    return [[sum(k[d + r] * tmp[min(n - 1, max(0, i + d))][j] for d in range(-r, r + 1)) for j in range(m)] for i in range(n)]


def bilinear(field, lats, lons, dlat, dlon, lon, lat):
    fi = (lat - lats[0]) / dlat; fj = (lon - lons[0]) / dlon
    i0 = min(len(lats) - 2, max(0, int(math.floor(fi)))); j0 = min(len(lons) - 2, max(0, int(math.floor(fj))))
    ti = min(1.0, max(0.0, fi - i0)); tj = min(1.0, max(0.0, fj - j0))
    return ((1 - ti) * ((1 - tj) * field[i0][j0] + tj * field[i0][j0 + 1]) + ti * ((1 - tj) * field[i0 + 1][j0] + tj * field[i0 + 1][j0 + 1]))


def render(lats, lons, zmed, classes, levels, sigma, dlat, dlon, stats):
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype("arial.ttf", 13); small = ImageFont.truetype("arial.ttf", 11)
    except OSError:
        font = small = ImageFont.load_default()
    W, H = 1700, 1500
    im = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(im)
    n, m = len(lats), len(lons)
    colours = {"L": (200, 190, 170), "S": (170, 210, 240), "T": (60, 110, 200), "P": (90, 150, 210), "A": (30, 70, 150), "N": (10, 30, 90)}
    level_field = [[levels[classes[i][j]] for j in range(m)] for i in range(n)]
    schematic = smooth(level_field, sigma)

    def draw_map(x0, y0, w, h, colour_of, title):
        # equirectangular, lon scaled by cos(70°)
        sx = w / (m * dlon * math.cos(math.radians(70))); sy = h / (n * dlat); s = min(sx, sy)
        cw = dlon * math.cos(math.radians(70)) * s; ch = dlat * s
        for i in range(n):
            for j in range(m):
                x = x0 + j * cw; y = y0 + h - (i + 1) * ch
                d.rectangle([x, y, x + cw + 0.5, y + ch + 0.5], fill=colour_of(i, j))
        d.text((x0, y0 - 18), title, fill="black", font=font)
        for lat in range(60, 86, 10):
            y = y0 + h - (lat - lats[0]) / dlat * ch; d.text((x0 - 34, y - 6), f"{lat}°N", fill="black", font=small)
        for lon in range(-10, 46, 10):
            x = x0 + (lon - lons[0]) / dlon * cw; d.text((x - 10, y0 + h + 4), f"{lon}°E", fill="black", font=small)

    draw_map(60, 40, 760, 560, lambda i, j: colours[classes[i][j]], "GEBCO 2020 classified: L land · S shelf · T Norwegian Trench · P slope/plateau · A abyssal · N deep basin")
    zmin = min(levels.values())
    def shade(v):
        t = min(1.0, max(0.0, v / zmin)); return (int(200 - 190 * t), int(215 - 180 * t), int(240 - 150 * t))
    draw_map(900, 40, 760, 560, lambda i, j: shade(schematic[i][j]) if classes[i][j] != "L" else (200, 190, 170),
             f"Schematic seabed the model draws: config.js levels {', '.join(f'{k} {int(v)} m' for k, v in levels.items() if k != 'L')}, σ = {sigma} cells")
    # legend for stats
    y = 640
    d.text((60, y), "GEBCO depth per class (median-filtered cells): mean / 10th–90th percentile — compare with the config.js level", fill="black", font=font); y += 18
    for k in "STPAN":
        s = stats[k]; d.text((60, y), f"  {k}: {s['cells']:5d} cells   mean {s['mean']:6.0f} m   p10 {s['p10']:6.0f}   p90 {s['p90']:6.0f}   config level {int(levels[k])} m", fill="black", font=font); y += 16
    # transects
    px, py, pw, ph = 60, 800, 500, 200
    for t, (label, a, b) in enumerate(TRANSECTS):
        x0 = px + (t % 3) * (pw + 60); y0 = py + (t // 3) * (ph + 60)
        d.rectangle([x0, y0, x0 + pw, y0 + ph], outline="black")
        d.text((x0, y0 - 16), label, fill="black", font=small)
        N = 200; pts_g = []; pts_s = []
        length_km = 0.0
        for q in range(N + 1):
            f = q / N; lon = a[0] + (b[0] - a[0]) * f; lat = a[1] + (b[1] - a[1]) * f
            if q:
                plon = a[0] + (b[0] - a[0]) * (q - 1) / N; plat = a[1] + (b[1] - a[1]) * (q - 1) / N
                length_km += math.hypot((lon - plon) * 111.32 * math.cos(math.radians(lat)), (lat - plat) * 111.32)
            g = min(0.0, bilinear(zmed, lats, lons, dlat, dlon, lon, lat)); s_ = bilinear(schematic, lats, lons, dlat, dlon, lon, lat)
            pts_g.append((length_km, g)); pts_s.append((length_km, s_))
        L = max(1.0, pts_g[-1][0]); depth_max = 4500.0
        def P(pt): return (x0 + pt[0] / L * pw, y0 + min(ph, -pt[1] / depth_max * ph))
        d.line([P(p) for p in pts_g], fill=(120, 120, 120), width=2)
        d.line([P(p) for p in pts_s], fill=(220, 60, 40), width=2)
        for dep in (1000, 2000, 3000, 4000):
            yy = y0 + dep / depth_max * ph; d.line([x0, yy, x0 + pw, yy], fill=(225, 225, 225)); d.text((x0 + 2, yy - 12), f"-{dep} m", fill=(120, 120, 120), font=small)
        d.text((x0 + pw - 60, y0 + ph + 2), f"{L:.0f} km", fill="black", font=small)
    d.text((px, py - 40), "Cross-sections: grey = GEBCO 2020 (coarse grid), red = schematic seabed as drawn by the model. Vertical scale 0 to -4500 m.", fill="black", font=font)
    RENDER.parent.mkdir(parents=True, exist_ok=True); im.save(RENDER)
    print(f"wrote {RENDER}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--render", action="store_true", help="also write docs/renders/seabed-schematic.png")
    args = ap.parse_args(argv)
    lats, lons, z, dlat, dlon = load_grid()
    zmed = median3(z)
    classes = classify(zmed, lats, lons)
    stats = {}
    for k in "LSTPAN":
        vals = sorted(zmed[i][j] for i in range(len(lats)) for j in range(len(lons)) if classes[i][j] == k)
        if vals:
            stats[k] = {"cells": len(vals), "mean": round(statistics.mean(vals)), "p10": vals[int(0.1 * (len(vals) - 1))], "p90": vals[int(0.9 * (len(vals) - 1))]}
    levels, sigma = read_config_levels()
    out = {"meta": {"generated": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
                    "source": "GEBCO Compilation Group (2020) GEBCO 2020 Grid, coarse 0.25° x 0.5° subset (data/raw/gebco/), 3x3 median filtered",
                    "purpose": "schematic seabed class map — illustrative, not survey data (SPEC §1, §3.3)",
                    "classes": {"L": "land", "S": "continental shelf", "T": "Norwegian Trench", "P": "slope / plateau", "A": "abyssal plain", "N": "deep Arctic basin"},
                    "thresholds_m": THRESHOLDS, "trench_box": TRENCH_BOX,
                    "grid": {"lat0": lats[0], "dlat": round(dlat, 6), "nlat": len(lats), "lon0": lons[0], "dlon": round(dlon, 6), "nlon": len(lons),
                             "order": "rows south to north, characters west to east, cell centres"},
                    "gebcoStats": stats, "configLevelsAtBuild": levels},
           "rows": ["".join(row) for row in classes]}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({OUT.stat().st_size} B)")
    for k, s in stats.items():
        print(f"  {k}: {s['cells']:5d} cells  mean {s['mean']:6d}  p10 {s['p10']:6d}  p90 {s['p90']:6d}  config {levels.get(k)}")
    if args.render:
        render(lats, lons, zmed, classes, levels, sigma, dlat, dlon, stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
