# Provenance

Everything under `data/` is **data, not code**: it is derived from Kartverket
datasets under the Norwegian Licence for Open Government Data (NLOD 2.0) /
CC BY 4.0 and is *not* covered by the AGPL that applies to the application code.
See [`data/LICENSE.md`](LICENSE.md). Attribution "© Kartverket" is required in
the UI (SPEC §2.4).

## 1. Route A — `data/raw/*.geojson` (ArcGIS REST mirror)

**Fetched:** 2026-09-17 (snapshot). **Re-fetched for verification:** 2026-09-17 07:05 UTC
with `code/scripts/fetch_boundaries.py --compare data/raw` — **all 12 files byte-identical**.
**Source:** Fiskeridirektoratet ArcGIS REST mirror of Kartverket's "Norges maritime grenser"
`https://portal.fiskeridir.no/arcgis/rest/services/Norges_maritime_grenselinjer/MapServer/{LAYER}/query`
Query: `where=1=1&outFields=*&returnGeometry=true&outSR=4326&f=geojson`.
Files are the HTTP response bodies verbatim (compact JSON, UTF-8, no BOM, no trailing newline).

| File | Feat. | Vert. | SHA-256 (first 12) |
|---|--:|--:|---|
| 0-grunnlinje | 7 | 485 | 655782bbd43b |
| 1-1nm | 1 | 329 | ebbac5f022f9 |
| 2-4nm | 1 | 398 | 213e3b1baa9d |
| 3-6nm | 1 | 477 | 4a84772259e2 |
| 4-10nm | 1 | 649 | 98cc9f59e6c1 |
| 5-territorialgrense-12nm | 8 | 3 461 | ead2e542ed76 |
| 6-tilstotende-sone-24nm | 1 | 679 | 20bc79be0f0c |
| 7-200nm | 3 | 1 822 | 650ba6c315f1 |
| 8-avtalt-avgrensningslinje | 11 | 389 | 4e1f25df6311 |
| 9-yttergrense-kontinentalsokkel | 1 | 202 | a505eaf9a253 |
| 10-avgrensningslinje-kontinentalsokkel | 2 | 50 | b82860eefaaa |
| 11-andre-staters-eez | 4 | 360 | 310fd161b7e7 |

Total 9 301 vertices (182 of them Bouvetøya, excluded from the model — see §6).

## 2. Route B — `data/raw/geonorge/` (Geonorge, authoritative)

**Fetched:** 2026-09-17 with `code/scripts/fetch_geonorge.py` (Geonorge download API, order
`landsdekkende`, GML, EPSG:4258). SHA-256 of every file in `data/raw/geonorge/FETCH_LOG.json`.
Two independent orders on the same day produced byte-identical GML.

| File | Dataset | UUID | Committed |
|---|---|---|---|
| `Basisdata_0000_Norge_4258_NorgesMaritimeGrenser_GML.zip` | Norges maritime grenser (Kartverket), `datauttaksdato` 2025-04-11 | `e106adf4-c9d8-4fce-a9b5-7886a4126d23` | yes (1.5 MB) |
| `n1000-coast.geojson` | N1000 Kartdata (Kartverket), Arealdekke → `Kystkontur` (6 713 lines, 98 764 vert.) + `Havflate` (209 polygons) only | `aee42bb6-d0e9-4d70-86fe-6ea76c381055` | yes (5.2 MB); the 21 MB source zip (SHA-256 `320a0af163c3…`) is not committed |

The Route B maritime dataset is much richer than the mirror: it carries Kartverket's
**official zone polygons** (`Sjøterritorium`, `IndreFarvann`, `TilstøtendeSone`,
`NorgesØkonomiskeSone`, `Fiskevernsone`, `Fiskerisone`, `Kontinentalsokkel`,
`Territorialområde`), coarse `Kystkontur`/`Landareal` (mainland from Kartverket, Svalbard
from Norsk Polarinstitutt), `Riksgrense`, a **Bouvetøya baseline** absent from Route A, and
per-feature status (`grensestatus`: Traktat / RettskraftigDom / Lovfestet / Godkjent /
Foreslått; `gyldigFra`). Owner decision 2026-09-17: these official polygons are the
source of truth for zone extents (SPEC §6.1 amended, see CLAUDE.md).

## 3. Verification — Route A vs Route B

`code/scripts/verify_geonorge.py <4258.gml>` matches every Route A vertex to the nearest Route B
vertex of the same feature type. Route B is delivered with 6 decimals (≈ 0.06 m), Route A
with full double precision, so agreement is measured, not byte-level.

- **All 12 layers, 9 119 non-Bouvetøya vertices: maximum deviation 0.062 m, mean 0.03 m**
  — i.e. exactly the 6-decimal rounding of the Route B delivery. The mainland baseline
  (max 0.058 m) and mainland 12 nm limit (max 0.060 m) required by SPEC §2.1 are included.
- Exceptions, all explained:
  - Layer 9 (shelf outer limit): 3 Route A vertices east of the Norway–Russia line
    (36.98°E–33.39°E, ≈ 84.5°N) have no Route B counterpart. They trace the construction
    geodesic to the westernmost point of Russia's outer limit (Route B's own `informasjon`
    on the terminus: "skjæringspunktet på den geodetiske linjen mellom punktene 7 og 8 og
    den geodetiske linjen som forbinder det østligste punktet på yttergrensen av Norges
    sokkel og det vestligste punktet på yttergrensen av Russlands sokkel"). They bound no
    Norwegian zone and are not emitted.
  - Layer 10 (Norway–Russia shelf line): its last vertex `[32.0643, 84.6946]` (treaty point
    8) lies 4.6 km beyond the intersection with Norway's outer limit; bounds no Norwegian
    zone, not emitted.
  - Layer 11 (Iceland, Faroes and two Greenland 200 nm limits): Route B does not carry the
    Iceland/Faroes/Greenland-west lines at all (only the Greenland line at 83.7°N, which
    matches to 0.052 m). They are Route A-only data and are used as delivered.
- Route B also contains lines absent from Route A: `Grunnlinje ved Bouvetøya`, and it names
  the 1/4/6/10 nm lines `LovVirkeområdeGrense` ("1 nautisk mil utenfor og parallelt med
  grunnlinjen"; "Fiskerigrense 4/6/10 nautiske mil …").

## 4. Datum and projection

- Route A is served in EPSG:4326 (WGS 84) by the mirror; Route B is EPSG:4258 (ETRS89).
  **They are treated as identical.** In Norway the two frames diverge by a few decimetres
  (ETRS89 is fixed to the Eurasian plate; WGS 84 drifts with ITRF by ~2.5 cm/yr since 1989).
  This is far below the generalisation applied here and below Kartverket's own stated
  accuracy for computed limits. `zones.json` declares `crs: EPSG:4326` on that basis.
- Topology (clipping, simplification, validity) is computed in EPSG:25833 (ETRS89 / UTM 33N)
  as SPEC §6.1 requires. pyproj cannot load on the development machine (Windows Application
  Control blocks its PROJ DLL), so `code/scripts/proj.py` implements the transverse Mercator
  projection (Krüger 6th-order series, GRS80, k₀ 0.9996, λ₀ 15°E, FE 500 000). Validated:
  round-trip of all 9 301 raw vertices ≤ 1.6 × 10⁻¹³°; against Kartverket's own EPSG:25833
  delivery of the same features it agrees to ≤ 0.06 m within 15° of the central meridian
  (all of the mainland and Svalbard), rising smoothly to 3.0 m at 28° west (Jan Mayen–Iceland
  line) — the signature of a truncated Redfearn-type series in whichever tool produced that
  export. Irrelevant to the model: output coordinates are always taken from the geographic
  source, never from a projection round-trip.

## 5. Coastline

- **Mainland: N1000 Kartdata** (owner decision 2026-09-17). N250 was rejected because the
  §8 vertex budget forces any coastline down to a few thousand vertices nationwide, far
  below even N1000's 98 764 — N250's ~2 M vertices would all be simplified away. Visual
  checks of the Oslofjord and Vestfjorden (SPEC §3.2): `docs/renders/coastline-sources-*.png`
  (Kartverket-maritime vs N1000 vs N250) and `docs/renders/*-coast-tolerance.png`
  (750 m vs 300 m simplification).
- Internal waters = N1000 `Havflate` (sea surface, topologically simplified) ∩ the region
  landward of `Norges grunnlinje` (exact). Result 91 186 km² vs Kartverket's own coarse
  `IndreFarvann ved Fastlands-Norge` polygon 97 251 km²; the difference is the crude 1997
  Kartverket coastline (it counts e.g. inland Varanger as water and cuts off inner fjords).
- **Svalbard and Jan Mayen have no N-series coverage.** Svalbard internal waters = exact
  baseline loops minus Kartverket `Landareal` (land=SJ; Norsk Polarinstitutt coastline as
  delivered inside the maritime dataset, simplified). Jan Mayen: Kartverket's `IndreFarvann`
  polygons as delivered (its baseline is partly the low-water line).
- Islands below 10 km² are not cut out of internal waters; coast simplified with a
  topology-preserving 750 m tolerance; computed limit lines (12/24/200 nm) with 100 m.
  Baselines, delimitation lines, other states' 200 nm limits and the shelf outer limit are
  never simplified. All three knobs are flags on `code/scripts/polygonise.py`.

## 6. Owner decisions recorded 2026-09-17

1. **Bouvetøya removed from the model** ("not worth the complications"). A user-facing note
   must say the model covers mainland Norway, Svalbard and Jan Mayen only. (Amends SPEC §1.)
2. **Coastline:** N1000, simplified to budget.
3. **Zone polygons:** Kartverket's official Route B polygons are the source of truth, with
   Route A full-precision coordinates substituted on every shared vertex.
4. **Norway–Iceland–Denmark/Faroes shelf line** (Route B `grensestatus: Foreslått`, dated
   2006): treated as an agreed delimitation like the others. Source supplied by the owner:
   Utenriksdepartementet press release 21.12.2022, "Maritime avgrensningsavtaler med
   Danmark/Færøyene og Island har trådt i kraft" — agreements signed 30 October 2019; the
   Norway–Iceland agreement entered into force 13 December 2022, Norway–Denmark/Faroes
   14 December 2022. <https://www.regjeringen.no/no/aktuelt/maritime-avgrensningsavtaler-med-danmarkfaroyene-og-island-har-tradt-i-kraft/id2952768/>
   Kartverket's status flag is therefore stale.

## 7. Outstanding verification

- [x] Cross-check Route A (ArcGIS mirror) geometry against a Route B (Geonorge) download — at
      minimum the mainland baseline and the 12 nm territorial limit. Record the maximum
      deviation found. → **0.062 m over all layers; 0.058 m baseline; 0.060 m 12 nm limit** (§3).
- [x] Note the ETRS89 / WGS84 datum difference explicitly rather than treating the two as
      identical. → §4.
- [x] Record coastline source and generalisation level once chosen. → **N1000, 750 m /
      10 km²** (§5); Svalbard/Jan Mayen from the maritime dataset's NPI coastline.
- [x] Record source for the schematic seabed depth figures. → **GEBCO 2020 via NOAA ERDDAP**,
      class map + named levels (§14); owner to sanity-check the levels.

## 8. Neighbouring states — UN DOALOS survey (2026-09-17)

Owner instruction: use <https://www.un.org/depts/los/LEGISLATIONANDTREATIES/index.htm> as the
source for neighbouring shelf states' zones. State files checked: RUS, ISL, DNK, GBR, NOR.

| State | What DOALOS holds that bears on this model | Coordinate list? |
|---|---|---|
| Russia | M.Z.N.124.2016.LOS (deposit 7 Sept 2016, art. 76(9)): charts **10100 "Barents Sea Southern Part"** and 10101 "Northern Part", 1:2 000 000, Pulkovo-1942 (SK-42), showing the outer limit of Russia's shelf beyond 200 nm *and* its 200 nm EEZ limit in the Barents Sea. Cautions note on 10100: the seabed "limited by the outer limit of the Russian Exclusive Economic Zone and by the delimitation line defined in accordance with the Treaty … dated September 15, 2010, is the continental shelf of the Russian Federation", and Russia exercises EEZ-equivalent rights in the "Special Area (72°50′N, 38°00′E)" (SPEC §1: the Special Area is *not* modelled). M.Z.N.97.2013 is the Sea of Okhotsk; M.Z.N.121.2016 and 173.2026 are other seas/Baltic. Also the 2010 treaty text (NOR-RUS2010.PDF). | **No — charts only** (scanned JPEG, 12 500 px ≈ 150 m/px at 1:2 M; drawn line width ≈ 1 km; SK-42 datum shift of order 100 m). |
| Iceland | Law No. 41/1979; Regulation 196/1985 (shelf delimitation W/S/E); CLCS submissions 2009 and 2021 (executive summaries carry outer-limit coordinates); treaties with Norway 1980/1981/1997 and Denmark 1997. | No deposited list of 200 nm limits. |
| Denmark | Fishing-territory orders 1976 (Faroes 598/599, Greenland 629), 2009 Faroes decree; EEZ Act 411/1996; CLCS submissions 2009 (Faroes N), 2010, 2012, 2013 (NE Greenland), 2014 (N of Greenland); treaties with Norway 1965/1979/1995/1997; ICJ 1993 Jan Mayen case. | No deposited list of 200 nm limits. |
| UK | M.Z.N.46.2004, 100.2014, 150.2019 with lists of coordinates (EEZ/shelf designation orders 2013). The UK–Norway line is already in Kartverket layer 8. | Yes, but not needed for any pocket. |
| Norway | M.Z.N.32/38/39/40/45/53 (2000–2005) with coordinate lists — baselines and territorial-sea limits (mainland, Svalbard, Jan Mayen). Useful as Phase 3 citations for the baseline/12 nm regulations. | Yes. |

Consequences: (a) the **Loop Hole** cannot be closed from deposited coordinates; see §11 for
how it was closed from Marine Regions and verified against chart 10100; (b) for **the Area**,
see §10.10 — one seabed patch inside the model extent is in no shelf polygon of any status.

## 9. Owner decisions, second round (2026-09-17)

5. **Historical lines:** none ship. Only current, UNCLOS-relevant lines are used (round 3 removed
   the 4 nm line as well). Kartverket's `LovVirkeområdeGrense` lines (1/4/6/10 nm) are indexed
   but nothing is emitted from them.
6. **Contested marker (SPEC §1/§10.5, visual only):** `svalbard-fpz` → `contested: true`;
   `continental-shelf` → `contestedExtent` = the shelf within the 200 nm zone around Svalbard
   (707 600 km², holes = territorial seas) and `contestedExtentInterval` = the shelf beyond
   200 nm that adjoins only the Svalbard zone (Nansen Basin, 14 614 km²), see
   `docs/renders/contested-extent.png`. The interval is the difference between two readings
   of the disputed area: (a) shelf within 200 nm of Svalbard; (b) all Norwegian shelf generated
   from Svalbard, including beyond 200 nm. The UI shows the interval as "disputed extent" with
   a one-line neutral mention of the two readings (owner instruction, round 3). A third notion —
   the Svalbard Treaty Article 1 area — is not modelled. Both zones cited **HR-2023-491-P
   (Snøkrabbe II)** at first; after Phase 3 only the shelf does (§16.3 item 5).

## 10. Owner decisions, third round (2026-09-17)

7. **Coast detail:** 300 m tolerance, islands ≥ 3 km². **SPEC §8 amended**: zone-polygon vertex
   budget 35 000 (was 12 000), and the size target is read as *gzipped* transfer size
   (~350 KB for zones.json). Measured: 32 396 vertices, zones.json 856 KB raw / ~330 KB gzip.
8. **EEZ strata:** water column only — the EEZ ends where the seabed starts; the seabed under it
   is the continental shelf. **SPEC §4.1 amended** (EEZ: water; shelf: seabed + subsoil).
9. **Neighbouring states' lines:** source order UN DOALOS deposits → Marine Regions. DOALOS holds
   no coordinate lists for Russia's Barents Sea limits (charts only, §8), so Russia's 200 nm line
   and the Special Area edge are taken from **Marine Regions** (§11) and **verified against the
   deposited chart** by overlay (§11).
10. **The Area:** `the-area` gets a `candidateExtent` — the 16 806 km² triangle at ≈0.3°E 73.6°N
    (north-west Banana Hole, between the Jan Mayen zone, Norway's CLCS-recommended shelf and
    Greenland's 2013 submission) whose seabed lies in no shelf polygon of any source or status.
    It is a data finding, not an asserted extent; `horizontal` stays null until the owner
    characterises it.

## 11. Marine Regions (Flanders Marine Institute) — third source

Fetched 2026-09-17 with `code/scripts/fetch_marineregions.py` from the WFS
`https://geo.vliz.be/geoserver/MarineRegions/wfs` into `data/raw/marineregions/`
(SHA-256 in `FETCH_LOG.json`). Licence **CC BY 4.0** (Marine Regions products are CC-BY since
Maritime Boundaries v11, 2019). Citation: *Flanders Marine Institute (2023). Maritime Boundaries
Geodatabase, version 12. https://www.marineregions.org/ https://doi.org/10.14284/628*; Extended
Continental Shelves v2, https://doi.org/10.14284/697. Attribution is required in the UI alongside
Kartverket's.

| File | Layer | Used for |
|---|---|---|
| `eez_boundaries_barents.json` | `eez_boundaries`, bbox 15–60°E 68–85°N (56 lines, verbatim) | `line_id 3697` "Russia 200 NM" (their own computation, source "200NM limit"), `line_id 4697` "Joint regime Norway–Russia" = the 2010 treaty's Special Area ring, whose northern edge is Norway's 200 nm arc east of the treaty line. Their "Norway 200 NM" (2054) is identical to Kartverket's (max 0.0 m); their "Svalbard 200 NM" (2055) is an older Kartverket version (up to 2.5 km off) and is **not** used. |
| `high_seas_pockets.json` | `high_seas`, subset: only polygon parts entirely inside −15–45°E 60–86°N (Banana Hole, Loop Hole) | cross-check of our pockets; input to the Area candidate |
| `ecs_north_atlantic.json` | `ecs`, same bbox (18 polygons, verbatim) | extended-continental-shelf polygons by status (CLCS recommendation / submission / overlapping claim / DOALOS deposit); input to the Area candidate |

**How the Loop Hole is built:** the noded network of Kartverket's 200 nm lines (layer 7), the
Norway–Russia and other delimitation lines (layer 8), other states' 200 nm limits (layer 11),
plus Marine Regions 3697 and 4697 snapped (≤ 100 m) onto the Kartverket lines; the faces outside
every Norwegian 200 nm zone and outside the Special Area are the pockets. Every vertex on a
Kartverket line is emitted as Kartverket's text; Russian-side vertices are Marine Regions'
(6 decimals). Layer 10 (shelf-only delimitation) is left out of the water-column network.
Result: Banana Hole 319 720 km², Loop Hole 76 211 km² (Marine Regions' own Loop Hole polygon:
same extent; theirs uses the older Svalbard arc).

**Verification against the UN-deposited chart.** Chart 10100 (M.Z.N.124.2016, 1:2 000 000
Mercator at 70°N, Pulkovo-1942) was georeferenced from its graticule (10°E at x = 813 px,
225.4 px/°; 77°/75°/69°N rows fitted to an ellipsoidal Mercator, residual ≤ 4 px ≈ 0.6 km) and the
Marine Regions Russian line, the Special Area ring, Kartverket's lines and our Loop Hole polygon
were drawn on it: `docs/renders/loop-hole-chart-overlay.png`. They coincide with the chart's
"Exclusive Economic Zone of Russia" and "Special Area" lines to within about one chart
millimetre (≈ 2 km); the SK-42 → WGS 84 datum shift (order 100 m) is below that. Digitising the
chart itself was therefore not done.

**North of 74.94°N** (where Kartverket's Svalbard 200 nm arc ends on the treaty line) the pocket
is bounded on the west by the 2010 treaty line and on the north-east by Russia's 200 nm limit,
exactly as chart 10100 draws it; the overlay covers that segment. The owner reviewed this
(§15.3) and the earlier "not verified" caveat was removed 2026-09-17.

## 12. Questions for the owner

1. ~~Vertex budget~~ — resolved (§10.7).
2. ~~The Area~~ — resolved (§15.1): asserted.
3. ~~Loop Hole~~ — resolved (§11).
4. ~~Historical lines~~ — resolved (§9.5).
5. ~~Contested readings~~ — resolved (§15.2): no Treaty box, no readings; one neutral extent.
6. ~~EEZ strata~~ — resolved (§10.8).
7. ~~Loop Hole sliver~~ — resolved (§15.3): kept; caveat removed.

## 13. Licence

Kartverket data: NLOD 2.0 / CC BY 4.0 — attribution required in the UI (SPEC §2.4). Svalbard
coastline inside the maritime dataset is credited by Kartverket to Norsk Polarinstitutt.
Marine Regions (Flanders Marine Institute): CC BY 4.0 — attribution required (§11).
Code and data licences are separated: see `data/LICENSE.md` and the repository `LICENSE`.

## 14. Schematic seabed (Phase 2, SPEC §3.3 and §5.2)

The seabed is schematic by decision (SPEC §1). To make its depths *defensible rather than
invented*, `code/scripts/fetch_gebco.py` fetched a coarse subset of **GEBCO 2020** (GEBCO
Compilation Group (2020) GEBCO 2020 Grid, doi:10.5285/a29c5465-b138-234d-e053-6c86abc040b9)
from NOAA CoastWatch's ERDDAP server (dataset `GEBCO_2020`, 15″ grid read with a stride):
0.25° × 0.5° cell centres over the model bbox, 15375 cells, 807667 bytes, SHA-256
`68f446ff4d1d46dcee8072476d6d02f4a715a08ba5e2b859d3fc13a7204fc11b`, fetched 2026-09-17T11:42:37+00:00, kept verbatim in `data/raw/gebco/`.

`code/scripts/build_seabed.py` median-filters the grid (3 × 3) and classifies every cell:

| Class | Rule (z = filtered GEBCO elevation, m) |
|---|---|
| L land | z ≥ 0 |
| T Norwegian Trench | z < −250 inside lon 2–12°E, lat 56.5–62.5°N (a nearshore deep — SPEC §5.2 asks for special handling) |
| S continental shelf | −500 ≤ z < 0 |
| P slope / plateau | −2500 ≤ z < −500 |
| A abyssal plain | −3900 ≤ z < −2500 |
| N deep Arctic basin | z < −3900 |

The class map is `data/build/seabed.json` (one letter per cell). **The depths the model draws
are not in the data**: they are the named constants `SEABED.levels` in `code/src/config.js`,
one per class, and the model smooths the level field with a Gaussian
(`SEABED.smoothingSigmaCells`, currently 0.8 cells ≈ 20–25 km) — that smoothing *is* the
continental slope. Change a level and the model, the cross-section and the verification render
follow. The verification render `docs/renders/seabed-schematic.png` overlays the schematic
surface on GEBCO along seven cross-sections (Møre, Lofoten, Bergen/Norwegian Trench, Skagerrak,
Barents Sea to the Nansen Basin, Svalbard west coast/Fram Strait, Jan Mayen).

GEBCO statistics per class versus the level currently drawn (for the owner's sanity check):

| Class | cells | GEBCO mean (m) | 10th … 90th percentile | config level (m) |
|---|---|---|---|---|
| S | 5112 | -191 | -351 … -44 | -250 |
| T | 68 | -318 | -393 … -257 | -500 |
| P | 2508 | -1594 | -2373 … -769 | -1500 |
| A | 3014 | -3225 | -3794 … -2661 | -3300 |
| N | 660 | -3987 | -4076 … -3914 | -4000 |

Notes for the owner: (i) the shelf level −250 m sits between the class mean (−191 m, pulled up
by the shallow North Sea plateau) and the typical Norwegian shelf (200–400 m); (ii) the trench
level −500 m is deeper than the coarse-cell mean (−318 m) because 0.25° cells average the trench
axis with its flanks — the axis is 300–700 m; (iii) subsoil thickness 10 km and the airspace
top 100 km / fade from 80 km are SPEC §5.2 nominal values, in `config.js`. The UI states that the
seabed is schematic and indicative. GEBCO attribution is in `data/LICENSE.md` and the UI line.

## 15. Owner decisions, fourth round (2026-09-17)

1. **The Area is asserted.** The 16 806 km² patch in the north-west Banana Hole (≈ 0.3°E,
   73.6°N; §10.10) is now the horizontal extent of `the-area` (strata seabed + subsoil), with
   `notModelled: ["beyond-model-extent"]` because the Area continues beyond the model bbox. The
   derivation is unchanged: Marine Regions high seas inside the model extent, minus every
   extended-continental-shelf polygon of any status (Marine Regions ECS v2), minus Kartverket's
   Norwegian shelf and 200 nm zones. The `candidateExtent` field is gone.
2. **Contested readings on the shelf — implications of the Treaty Article 1 box** (10–35°E,
   74–81°N), measured on the built geometry (`docs/renders/svalbard-treaty-box.png`):
   - The shelf within 200 nm of Svalbard (reading a, 707 600 km²) splits into **304 200 km² inside
     the box** and **403 400 km² outside it** (223 200 west of 10°E, 145 100 north of 81°N, 37 000
     south of 74°N around Bjørnøya, 34 600 east of 35°E).
   - The Nansen Basin shelf beyond 200 nm (the current interval, 14 600 km²) lies entirely outside
     the box (north of 81°N).
   - 17 600 km² of the **mainland** EEZ and the shelf beneath it lie inside the box (its southern
     edge at 74°N cuts across the mainland zone north of Finnmark). A box-based marking must say
     whether that is included — a legal characterisation the owner makes, not the model.
   - The box lies almost entirely within Norwegian zones (4 km² outside them); 588 km² of the
     Loop Hole is inside it.
   - Consequences for the marker: with the box as reading (b) the *core* (in both readings) would be
     the 200 nm shelf inside the box, and the *interval* (what reading (a) adds) the 403 400 km² of
     200 nm shelf outside the box; the Nansen Basin would either join the interval or become a
     third tier. The whole-zone `contested` flag on `svalbard-fpz` (water column) would face the
     same question: 454 100 km² of the FPZ is inside the box, 404 700 km² outside.
   **Decision (owner, same day, final): the box is not used, and no readings are distinguished.**
   "Show the Nansen Basin as Svalbard's shelf, without any distinction; the Svalbard Treaty dispute
   does not need to be litigated on this map." `contestedExtentInterval` is removed;
   `contestedExtent` on `continental-shelf` is now one extent — the shelf within 200 nm of Svalbard
   (707 600 km²) plus the Nansen Basin shelf beyond 200 nm (14 614 km²) — carrying the single
   neutral marker. `svalbard-fpz` stays `contested: true` as a whole.
3. **Loop Hole sliver — clarification.** The sliver (east of the 2010 line, 74.94–76.96°N) is
   already bounded on the west by the treaty line; "clipping it to the treaty line" changes nothing.
   Kartverket's Svalbard 200 nm arc ends exactly where it meets the treaty line (37°E, 74.9377°N),
   so no Norwegian line crosses the sliver, and on Russia's deposited chart 10100 the Loop Hole's
   boundary runs the same way (up the treaty line, then east along Russia's 200 nm limit) — the
   overlay in `docs/renders/loop-hole-chart-overlay.png` covers that segment. The only decision is
   whether the sliver stays high-seas water column (as now, consistent with both states' lines) or
   is removed from the model. **Decision (owner, same day): keep it; the caveat is removed** and §11
   now records the segment as verified against the chart.

## 16. Legal sources (Phase 3, SPEC §4.1, §6.1 step 4, §10.1)

Every `quote` in `data/build/zones.json` is extracted by `code/scripts/build_legal.py` from a file
under `data/raw/legal/` that `code/scripts/fetch_legal.py` fetched verbatim on 2026-09-17. No
provision, title or act number was typed from memory; the DokIDs in `fetch_legal.py` were found by
searching the titles inside the fetched Lovdata packages.

### 16.1 Sources

| Directory | Source | What is kept | Licence / terms |
|---|---|---|---|
| `raw/legal/lovdata/` | Lovdata, free data packages via `api.lovdata.no/v1/publicData` (`gjeldende-lover` 2026-09-15, `gjeldende-sentrale-forskrifter` 2026-09-17) | the six documents kept (XHTML, byte for byte); `publicData-list.json`; `FETCH_LOG.json` with the archives' SHA-256 | NLOD 2.0 (Lovdata, lovdata.no/info/api) |
| `raw/legal/unclos/` | UN Division for Ocean Affairs and the Law of the Sea, `un.org/depts/los/convention_agreements/texts/unclos/` | Parts I, II, V, VI, VII and XI s. 2 as one HTML file each, plus the table of contents | UN publication of the Convention text; the owner records the terms |
| `raw/legal/hr/` | Norges Høyesterett, domstol.no | HR-2023-491-P: the judgment (PDF) and the Court's English translation (PDF, "provided for information purposes only") | published by the Court; the owner records the terms |

Documents fetched from Lovdata: `NL/lov/2003-06-27-57` (territorialfarvannsloven),
`NL/lov/1976-12-17-91` (økonomiske soneloven), `NL/lov/2021-06-18-89` (lov om Norges
kontinentalsokkel), `NL/lov/1963-06-21-12` (lov om undersjøiske naturforekomster, fetched, not
cited), `SF/forskrift/1977-06-03-6` (fiskevernsonen), `SF/forskrift/1980-05-23-4` (fiskerisonen
ved Jan Mayen). petroleumsloven and luftfartsloven were fetched at first and dropped by the owner
(§16.3).

### 16.2 Extraction

`build_legal.py` writes `data/build/legal.json` (22 provisions) and the review copy
`data/build/LEGAL.md`. Lovdata provisions are taken element by element from the XHTML
(`article.legalArticle` / `section` by `data-name`), keeping headings, ledd and list markers and
dropping amendment notes and footnote markers. UNCLOS articles are parsed from the DOALOS pages
(article heading, numbered paragraphs, lettered items); a sub-reference such as art. 87(1)(b) keeps
the chapeau and the item and marks what is left out with `[…]`. Judgment paragraphs are read from
the PDFs with pypdf by their `(n)` numbers, page furniture removed.

Cross-checks made once, outside the pipeline (2026-09-17): every UNCLOS line quoted was found
verbatim in the DOALOS PDF (`unclos_e.pdf`, only a page-number artefact inside art. 76(6));
paragraphs 16 and 220 of HR-2023-491-P extracted from the Court's PDF are identical, after
whitespace normalisation, to Lovdata's HTML publication of the judgment.

`build_zones.py` merges the provisions into every citation by `source` (+ `pinpoint`) and fails
`--check` if any citation lacks a fetched quote. 78 citations, all filled.

### 16.3 Selection choices — for the owner to confirm (SPEC §9 Phase 3 exit criterion)

Recorded as `selectionNote` in `legal.json` and shown in `LEGAL.md`:

1. **kontinentalsokkelloven.** SPEC §4.1 names no provision. Lovdata's current acts contain lov
   18. juni 2021 nr. 89 om Norges kontinentalsokkel (§ 1 defines the shelf) and lov 21. juni 1963
   nr. 12, whose § 1 now refers to the 2021 act. **§ 1 of the 2021 act is quoted**; the 1963 act
   is fetched but not cited.
2. ~~petroleumsloven § 1-6~~ — **dropped by the owner (2026-09-17)**; the shelf cites the 2021
   act, UNCLOS arts 76–79 and HR-2023-491-P.
3. **forskrift 3. juni 1977 nr. 6** ; **quoted in full**
   (§§ 1–5) on `svalbard-fpz`.
4. **forskrift 23. mai 1980 nr. 4** ; **quoted in full**
   (items 1–5) on `janmayen-fisheries-zone`.
5. **HR-2023-491-P** (not in SPEC §4.1; added with the contested marker in Phase 1). On
   `svalbard-fpz`: ~~paragraph 16~~ — **dropped by the owner (2026-09-17)**, it only restates the
   1977 regulation. On `continental-shelf`: paragraph 220 (conclusion on Treaty art. 2 and
   UNCLOS art. 77), **confirmed by the owner (2026-09-17)**; 227 is the overall conclusion. The
   `en` payload also carries the Court's own English translation of the paragraph as `translation`
   (the `quote` stays Norwegian, SPEC §4); whether the UI shows it is the owner's call.
6. ~~luftfartsloven § 1-1~~ — **dropped by the owner (2026-09-17)**: it says nothing about the
   extent of national airspace; `national-airspace` cites UNCLOS art. 2(2) alone. The document was
   removed from `data/raw/legal/lovdata/`.
6a. ~~UNCLOS art. 303~~ — **dropped by the owner (2026-09-17)** as unnecessary detail for teaching;
   `mainland-contiguous-zone` cites art. 33 alone. `part16.htm` was removed from `data/raw/legal/unclos/`.
6b. Summaries cite the public-international-law source first and the Norwegian provision second
   (owner, 2026-09-17); the "ikke-diskriminerende sone" label on `svalbard-fpz` is the owner's
   characterisation, derived from § 2 of the 1977 regulation.
6c. **UNCLOS arts 55–58** added to `svalbard-fpz` and `janmayen-fisheries-zone` (owner, 2026-09-17;
   SPEC §4.1 had no UNCLOS entry for them). The summary drafts state the Convention's EEZ regime
   (arts 56(1)(a), 57, 58) and then what the Norwegian regulation established — pending approval.
6d. Zone `airspace-beyond-territorial-sea` renamed **`international-airspace`**, labelled
   "Internasjonalt luftrom" / "International airspace" (owner, 2026-09-17).
7. **Summaries.** Drafts for all 15 zones are in `data/legal/summaries.json` with
   `status: "draft"`, written only from the quoted provisions (each sentence cites its provision).
   None ships until the owner sets `status: "approved"`; until then the app has no summaries.

### 16.4 Citation record (SPEC §4 interface, extended)

Each citation: `source` (SPEC §4.1 short form, unchanged), `pinpoint` (judgments only), `title`
(document title as fetched), `citedAs` (e.g. `lov 27. juni 2003 nr. 57`, built from Lovdata's
`legacyID`), `quote`, `quoteLang`, `url` (Lovdata `dokument/…/§n`, DOALOS part page, or the Court's
PDF), `provenance` (publisher, file, SHA-256, selector, and for Lovdata `lastChangeInForce` and the
package date), and on `en` judgment citations `translation` / `translationUrl` / `translationNote`.
