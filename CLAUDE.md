# CLAUDE.md — working notes for this repo

The project brief is [docs/SPEC.md](docs/SPEC.md). Read it before doing anything.
**§1 (fixed decisions) and §10 (standing rules) are binding.** This file does not
restate the spec; it records conventions, gotchas and where the work stands.
Owner amendments to §1 are recorded at the top of §1 itself (dated).

## Layout deviations from SPEC §6

- **All AGPL material lives under `code/`** (owner decision 2026-09-17, for clean licence
  separation): `code/src/`, `code/index.html`, `code/scripts/`, `code/package.json`,
  `code/vite.config.js`, `code/LICENSE`. `data/` (NLOD/CC BY) and `docs/` (AGPL, aligned
  with the code) stay at the root; the root `LICENSE.md` maps the three trees. `npm` commands
  run inside `code/`; the scripts anchor `data/` to the repo root (`ROOT`), so they run from
  anywhere; `vite build` writes `../dist/`.
- `SPEC.md` lives at `docs/SPEC.md` (owner's choice, commit `8af848d`), not at root.
- `docs/renders/` holds the visual-check PNGs (coastline sources, tolerance comparisons, zone overview).
- `data/raw/geonorge/` holds the Route B (Geonorge) sources next to the Route A snapshot.
- `code/scripts/` has, beyond §6's list: `fetch_geonorge.py` (Route B), `fetch_marineregions.py`
  (Russian 200 nm line, ECS polygons), `fetch_gebco.py` + `build_seabed.py` (schematic seabed class
  map), `build_legal.py` (provisions from `data/raw/legal/` → `data/build/legal.json` + `LEGAL.md`),
  `verify_geonorge.py` (Route A ↔ B cross-check), `gml.py` (GML reader), `proj.py` (transverse Mercator).
- `data/raw/legal/` — the fetched legal sources (Lovdata XHTML, DOALOS HTML, Supreme Court PDFs);
  `data/legal/summaries.json` — hand-maintained zone summaries with an approval status.
- `code/src/seabed.js` (not in §6's list): the schematic depth field sampled by `strata.js`.
- `data/raw/gebco/` — coarse GEBCO 2020 subset (public domain), only for the seabed class map.
- `data/raw/marineregions/` — third source (CC BY 4.0), used only where Kartverket has nothing.
- Hosting: GitHub Pages from `.github/workflows/pages.yml` (builds `code/`, deploys `dist/`).
- Everything else follows §6.

## Toolchain (pinned)

| Thing | Version | Notes |
|---|---|---|
| Node | 24.x (Vite 8 needs ≥22.12) | |
| Vite | 8.3.0 | `code/vite.config.js`, `vite-plugin-singlefile` 2.3.3 |
| CesiumJS (CDN) | **1.145.0** exact | SPEC §6: never a floating tag. `https://cdn.jsdelivr.net/npm/cesium@1.145.0/Build/Cesium/` (fallback `cesium.com/downloads/cesiumjs/releases/1.145/`). Not an npm dependency; Vite treats `cesium` as an external global. |
| Python | 3.13 (Microsoft Store build) | scripts only |
| shapely | 2.1 | geometry (`code/scripts/requirements.txt`) |
| pypdf | 6.x | `build_legal.py` only: paragraphs of HR-2023-491-P from the Court's PDFs (pure Python, so Application Control is not an issue) |

**pyproj does not work on this machine**: Windows Application Control blocks its
PROJ DLL wherever it is installed (user site, venv). `code/scripts/proj.py` implements
EPSG:25833 instead (Krüger series; validated in PROVENANCE §4). Don't add pyproj back.

## Conventions

- **Python scripts are idempotent CLIs** with `--help`; they read `data/raw/` and write
  `data/build/`. Never write into `data/raw/` except from the fetch scripts, deliberately.
- **Raw snapshot is byte-exact.** `data/raw/*.geojson` are ArcGIS response bodies verbatim
  (compact JSON, UTF-8, no BOM, no trailing newline). `fetch_boundaries.py --compare data/raw`
  must report "all files byte-identical" after a re-fetch. Never re-serialise these files.
- **Coordinates are text, not floats, all the way through.** `polygonise.py` indexes the
  Route A coordinate *tokens* and re-emits them verbatim; computed vertices (coastline,
  intersections) are `%.6f`. `build_zones.py --check` proves every vertex of layers 0/8/9/10
  that bounds a modelled zone appears byte-identical in `zones.json`. Anything that would
  round-trip those numbers through `float` → `json.dumps` is a bug.
- **Simplification is per source line, shared by every polygon** (`SourceIndex.keep`), so
  polygons that share the 12 nm line get the same vertices — no slivers. Exempt layers:
  0 (baselines), 8/10 (delimitation), 9 (shelf outer limit), 11 (other states' 200 nm).
- **Topology in EPSG:25833, output in EPSG:4326** (§6.1). Output coordinates are never taken
  from a projection round-trip; they come from source text or from `%.6f` of the inverse.
- **Zone ids** are stable kebab-case (`mainland-territorial-sea`, `svalbard-fpz`, …); the
  registry is `build_zones.py::registry()`. Renaming one is a breaking change (last one:
  `airspace-beyond-territorial-sea` → `international-airspace`, owner, 2026-09-17, before any release). Extensions to
  the SPEC §4 interface: `geography: 'all'` (shelf, high seas, the Area, airspace zones),
  `derivedFrom` (international airspace = union of member zones, no duplicated geometry),
  `notModelled` (`the-area`: beyond-model-extent; `high-seas`: beyond-outer-limit), `contestedExtent` on
  `continental-shelf` (neutral marker inside the extent: the Svalbard-generated shelf incl. the
  Nansen Basin, one extent, no readings distinguished — owner decision round 4), `provenance`, `notes`. `contested: true` = whole zone.
- **Three geodata sources, in order of authority**: Kartverket (Route B polygons, Route A text),
  UN DOALOS (checked; charts only for Russia), Marine Regions (only the Russian 200 nm line, the
  Special Area ring and ECS polygons). Never take Norwegian lines from Marine Regions — their
  Svalbard 200 nm line is an old Kartverket version, up to 2.5 km off.
- **No overlays.** Layers 1–4 (1/4/6/10 nm) are indexed but nothing is emitted from them.
- Numeric constants for Phase 2 (stratum depths, detents, colours) live in `code/src/config.js` only.
  `build_seabed.py` *reads* `config.js` (regex on `SEABED.levels`) for its verification render, so
  the levels have one home.
- **Cesium is the CDN global `globalThis.Cesium`**, never `import`ed: Vite emits ES modules, so a
  bare `import 'cesium'` would fail in the browser. Custom appearances must declare
  `in float batchId;` (Cesium's Primitive injects a batch table) or the vertex shader fails to compile.
- **Volumes are custom `Geometry`** (strata.js): polygon → earcut (`Cesium.PolygonPipeline.triangulate`)
  → midpoint subdivision to `MESH.maxEdgeDeg` → rows at per-vertex heights + walls along boundary
  edges (edges used by exactly one triangle, so holes get walls too). Nominal heights are cached per
  vertex; exaggeration = recompute positions + swap primitives (≈ 60 ms desktop for 380k vertices).
- Coincident surfaces are separated by `SEABED_CLEARANCE` (30 m nominal) to avoid z-fighting.
- Bilingual strings: `no` / `en`. Norwegian statutory quotations stay Norwegian in both modes.
- **Legal text is never typed, only extracted** (§10.1). `fetch_legal.py` stores the source documents
  verbatim; `build_legal.py::PROVISIONS` maps each citation `source` (SPEC §4.1 short form, plus
  `pinpoint` for judgment paragraphs) to a selector in a fetched file and writes `legal.json`;
  `build_zones.py::fill_legal` merges quotes by that key and `--check` fails on any citation without
  one. Change a citation → add a PROVISIONS entry, never a string. `LEGAL.md` is the owner's review copy.
- **Summaries ship only when approved**: `data/legal/summaries.json` entries with `status: "draft"`
  are dropped by `build_zones.py` (summary = "" and `summaryStatus`). Legal characterisation is the
  owner's (§10.4); drafts cite the quoted provision in every sentence.
- Commit messages: imperative, English. Data re-fetches get their own commit with the date.

## Gotchas

- **Route B ≠ Route A in scope.** The Geonorge GML has official zone *polygons*
  (`Sjøterritorium`, `IndreFarvann`, `TilstøtendeSone`, `NorgesØkonomiskeSone`,
  `Fiskevernsone`, `Fiskerisone`, `Kontinentalsokkel`, `Territorialområde`), `Riksgrense`,
  coarse `Kystkontur`/`Landareal`, a Bouvetøya baseline, and `grensestatus`/`gyldigFra`
  per feature. The ArcGIS mirror has only the 12 line layers. Route B is the source of
  truth for zone extents (owner decision); Route A supplies full-precision coordinates.
- Route B GML is EPSG:4258 with **lat lon axis order**, 6 decimals; rings are
  `gml:LinearRing` *or* `gml:Ring` of several `curveMember` LineStrings — `gml.py` handles both.
- Kartverket's polygons contain nodes *on* delimitation lines that are not vertices of the
  line (e.g. `[38.000000, 77.322179]` where EEZ and FPZ meet the Norway–Russia line).
  `polygonise.py` accepts those if within 1 m of an exempt segment and logs them in `stats`.
- Line ends that should meet differ by ~0.1 mm between layers 7 and 11; the high-seas
  network snaps them (1 m) or `polygonize` never closes the Banana Hole.
- Jan Mayen's baseline is partly the low-water line: its territorial-sea inner ring and
  internal-waters polygons contain coast vertices. Handled explicitly (`coast=True`).
- N1000/N250 cover the mainland only. Svalbard/Jan Mayen coastlines come from the maritime
  dataset (Norsk Polarinstitutt). Kartverket's own mainland `Kystkontur` there is crude (1997).
- Route A layer 9 has 3 vertices east of the Norway–Russia line and layer 10 ends at treaty
  point 8 beyond the outer limit; they bound nothing Norwegian and are not emitted (WARN, not FAIL).
- The Fiskeridirektoratet mirror returns `MultiLineString` for some features; layer 11
  carries the full Kartverket attribute schema; `NAVN` is truncated at ~60 chars.
- Windows: `core.autocrlf=true`; `.gitattributes` forces LF for data and source files.
  The PowerShell console mangles `ø/å`; set `PYTHONIOENCODING=utf-8` when printing them.
- The Bash tool's heredocs choke on some multi-line Python with quotes — write patch
  scripts with the Write tool and run them, rather than fighting the shell.
- Three IndreFarvann features share the name "Indre farvann ved Jan Mayen": never key
  Route B features by name alone.
- Headless rendering for checks: Chrome `--headless=new --use-angle=swiftshader --enable-unsafe-swiftshader
  --virtual-time-budget=40000 --screenshot=…` against `python -m http.server --directory dist`; it
  takes minutes in software GL and console messages come via `--enable-logging=stderr`.

## State of play

_Update this section at the end of every session._

**2026-09-17 (session 1, continued) — Phase 1 committed and pushed; Phase 2 geometry built.**

Phase 1 is on `main` (4 commits, pushed). Repo restructured so all AGPL material is under `code/`
(root `LICENSE.md` maps code/docs/data); GitHub Pages workflow added (`.github/workflows/pages.yml`)
— the owner must set Settings → Pages → Source: GitHub Actions once.

Phase 2 done in this session: schematic seabed (GEBCO 2020 class map, levels in `config.js`,
verification render `docs/renders/seabed-schematic.png`, PROVENANCE §14); `seabed.js`, `zones.js`,
`strata.js` (custom-geometry volumes: airspace fence with top fade, water column to the seabed,
seabed surface, bounded-but-open subsoil; hatched contested markers for `svalbard-fpz` and the
shelf's contestedExtent), `ui.js` (log slider with detents + readout, stratum and zone
toggles, NO/EN toggle, scope note, persistent attribution incl. Cesium credits), `main.js`
(EllipsoidTerrainProvider + OSM, translucent globe inside the bbox, camera may go underground,
requestRenderMode). Bundle 897 KB raw / 341 KB gzip. Verified in headless Chrome.

All Phase 1 questions are resolved (PROVENANCE §12/§15). Seabed levels and airspace exaggeration
accepted for now. Still open: Canvas CSP allow-listing of github.io; Pages source setting.

Phase 3 built (same day): `fetch_legal.py` (Lovdata packages → 8 documents, DOALOS UNCLOS parts,
HR-2023-491-P PDFs, all verbatim with SHA-256 logs), `build_legal.py` (22 provisions → `legal.json`,
review copy `LEGAL.md`, cross-checked against the DOALOS PDF and Lovdata's HTML of the judgment),
`build_zones.py` merges them (78 citations, all quoted; UNCLOS arts 55–58 added to both fisheries zones; petroleumsloven § 1-6, luftfartsloven § 1-1, UNCLOS art. 303 and judgment paragraph 16 dropped by the owner; the two zone regulations quoted in full; summaries cite UNCLOS first). Summaries for all 15 zones in
`data/legal/summaries.json` reviewed and **approved by the owner** (30/30 payloads ship); judgment
paragraph 220 confirmed. **Phase 3 exit criterion met.** All §16.3 choices confirmed by the owner
(kontinentalsokkelloven = 2021 act § 1; the Court's English translation stays on `en`, to be shown
with the Court's caveat in Phase 4; the Court's PDFs are public domain as official government
documents). Still open: licence wording for the DOALOS text in `data/LICENSE.md`. The UI does not yet show legal text (Phase 4).

Next: Phase 4 (column query with citations + quotes + summaries, cross-section, preset viewpoints,
URL state), Phase 5 (device matrix, Canvas test).
