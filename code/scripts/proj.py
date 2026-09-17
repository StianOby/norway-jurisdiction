"""Transverse Mercator (Krüger n-series, 6th order) for EPSG:25833 and local variants.

Why this exists: pyproj's PROJ DLL is blocked by the Windows Application Control
policy on the development machine (see CLAUDE.md), and the pipeline only needs one
projection as a *topology workspace*.  The output coordinates are always taken
from source data, never from a round-trip through this code.

ETRS89 (EPSG:4258) and WGS84 (EPSG:4326) are treated as identical here.  They
diverge by a few decimetres in Norway (plate drift since 1989); that is stated,
not ignored, in data/PROVENANCE.md.

Reference: Karney, "Transverse Mercator with an accuracy of a few nanometers",
J. Geodesy 85 (2011) 475–485; the same series PROJ uses for +proj=tmerc (algo=poder_engsager
is a variant; results agree far below the precision of the data).  Validated
against Kartverket's EPSG:25833 delivery in scripts/verify_geonorge.py.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# GRS80 (ETRS89) — for WGS84 the flattening differs in the 12th significant digit.
A_GRS80 = 6_378_137.0
F_GRS80 = 1 / 298.257222101


@dataclass(frozen=True)
class TransverseMercator:
    lon0_deg: float
    k0: float = 0.9996
    false_easting: float = 500_000.0
    false_northing: float = 0.0
    a: float = A_GRS80
    f: float = F_GRS80

    def __post_init__(self):
        n = self.f / (2 - self.f)
        n2, n3, n4, n5, n6 = n**2, n**3, n**4, n**5, n**6
        object.__setattr__(self, "n", n)
        object.__setattr__(self, "A", self.a / (1 + n) * (1 + n2 / 4 + n4 / 64 + n6 / 256))
        object.__setattr__(self, "alpha", (
            n / 2 - 2 * n2 / 3 + 5 * n3 / 16 + 41 * n4 / 180 - 127 * n5 / 288 + 7891 * n6 / 37800,
            13 * n2 / 48 - 3 * n3 / 5 + 557 * n4 / 1440 + 281 * n5 / 630 - 1983433 * n6 / 1935360,
            61 * n3 / 240 - 103 * n4 / 140 + 15061 * n5 / 26880 + 167603 * n6 / 181440,
            49561 * n4 / 161280 - 179 * n5 / 168 + 6601661 * n6 / 7257600,
            34729 * n5 / 80640 - 3418889 * n6 / 1995840,
            212378941 * n6 / 319334400,
        ))
        object.__setattr__(self, "beta", (
            n / 2 - 2 * n2 / 3 + 37 * n3 / 96 - n4 / 360 - 81 * n5 / 512 + 96199 * n6 / 604800,
            n2 / 48 + n3 / 15 - 437 * n4 / 1440 + 46 * n5 / 105 - 1118711 * n6 / 3870720,
            17 * n3 / 480 - 37 * n4 / 840 - 209 * n5 / 4480 + 5569 * n6 / 90720,
            4397 * n4 / 161280 - 11 * n5 / 504 - 830251 * n6 / 7257600,
            4583 * n5 / 161280 - 108847 * n6 / 3991680,
            20648693 * n6 / 638668800,
        ))
        object.__setattr__(self, "delta", (
            2 * n - 2 * n2 / 3 - 2 * n3 + 116 * n4 / 45 + 26 * n5 / 45 - 2854 * n6 / 675,
            7 * n2 / 3 - 8 * n3 / 5 - 227 * n4 / 45 + 2704 * n5 / 315 + 2323 * n6 / 945,
            56 * n3 / 15 - 136 * n4 / 35 - 1262 * n5 / 105 + 73814 * n6 / 2835,
            4279 * n4 / 630 - 332 * n5 / 35 - 399572 * n6 / 14175,
            4174 * n5 / 315 - 144838 * n6 / 6237,
            601676 * n6 / 22275,
        ))
        object.__setattr__(self, "e2n", 2 * math.sqrt(n) / (1 + n))

    def forward(self, lon: float, lat: float) -> tuple[float, float]:
        """(lon, lat) degrees -> (easting, northing) metres."""
        phi = math.radians(lat)
        lam = math.radians(lon - self.lon0_deg)
        sphi = math.sin(phi)
        t = math.sinh(math.atanh(sphi) - self.e2n * math.atanh(self.e2n * sphi))
        xi_ = math.atan2(t, math.cos(lam))
        eta_ = math.atanh(math.sin(lam) / math.sqrt(1 + t * t))
        xi, eta = xi_, eta_
        for j, a in enumerate(self.alpha, start=1):
            xi += a * math.sin(2 * j * xi_) * math.cosh(2 * j * eta_)
            eta += a * math.cos(2 * j * xi_) * math.sinh(2 * j * eta_)
        return self.false_easting + self.k0 * self.A * eta, self.false_northing + self.k0 * self.A * xi

    def inverse(self, x: float, y: float) -> tuple[float, float]:
        """(easting, northing) metres -> (lon, lat) degrees."""
        xi = (y - self.false_northing) / (self.k0 * self.A)
        eta = (x - self.false_easting) / (self.k0 * self.A)
        xi_, eta_ = xi, eta
        for j, b in enumerate(self.beta, start=1):
            xi_ -= b * math.sin(2 * j * xi) * math.cosh(2 * j * eta)
            eta_ -= b * math.cos(2 * j * xi) * math.sinh(2 * j * eta)
        chi = math.asin(math.sin(xi_) / math.cosh(eta_))
        phi = chi
        for j, d in enumerate(self.delta, start=1):
            phi += d * math.sin(2 * j * chi)
        lam = math.atan2(math.sinh(eta_), math.cos(xi_))
        return self.lon0_deg + math.degrees(lam), math.degrees(phi)


# EPSG:25833 — ETRS89 / UTM zone 33N.  Used for everything except Bouvetøya.
UTM33N = TransverseMercator(lon0_deg=15.0)

# Bouvetøya (54.4°S, 3.4°E) is ~12 zones away from UTM 33N; use a local TM
# centred on the island (UTM zone 31S parameters would also do, but a centred
# meridian keeps distortion negligible).  Southern hemisphere: false northing
# 10 000 000 as in UTM south zones, so northings stay positive.
BOUVET_LOCAL = TransverseMercator(lon0_deg=3.4, false_northing=10_000_000.0)


def project_ring(tm: TransverseMercator, ring):
    return [tm.forward(lon, lat) for lon, lat in ring]


def unproject_ring(tm: TransverseMercator, ring):
    return [tm.inverse(x, y) for x, y in ring]
