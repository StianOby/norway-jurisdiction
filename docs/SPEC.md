# Norwegian Maritime Jurisdiction — Interactive 3D Teaching Model

**Specification for implementation.** Hand this to Claude Code as the project brief.

Owner: Stian Øby Johansen, Professor of international and European law, University of Oslo, Faculty of Law.
Purpose: a browser-based 3D model of Norway's jurisdictional zones — maritime, seabed and airspace — that students on university courses in the international law of jurisdiction can fly around to see where zones begin and end and how they overlap vertically.

---

## 1. Fixed decisions

These are settled. Do not re-litigate them without asking.

> **Amendments by the owner, 2026-09-17** (recorded here so §1 stays authoritative; details in `data/PROVENANCE.md` §6):
> - Geographic scope is **Fastlands-Norge, Svalbard, Jan Mayen**. Bouvetøya is removed; the UI must state that the model covers only these three.
> - Coastline source: **N1000 Kartdata**, simplified to budget (§3.2 resolved).
> - Zone polygons are taken from Kartverket's official polygons in the Geonorge (Route B) delivery rather than polygonised from lines (§6.1 method amended; §10 unchanged).
> - The Norway–Iceland–Denmark/Faroes continental-shelf line is an agreed delimitation (in force December 2022).
> - §4.1: Norges økonomiske sone has the stratum **water column only**; the seabed beneath it is the continental shelf.
> - §8: zone-polygon vertex budget **35 000** (was 12 000); the `dist/index.html` size target is read as gzipped transfer size. Coastline simplified at 300 m, islands ≥ 3 km².
> - No historical fisheries lines (1/4/6/10 nm) ship — current, UNCLOS-relevant lines only (the §2.3 overlay is dropped).
> - Neighbouring states' lines: UN DOALOS deposits first; where DOALOS holds charts only, Marine Regions (CC BY 4.0) verified against the deposited chart. Attribution to Marine Regions is required in the UI.
> - The Area: the 16 806 km² patch in the north-west Banana Hole in no shelf polygon of any status is asserted as the Area (PROVENANCE §15.1); it continues beyond the model extent.
> - Contested shelf marker: one neutral extent = the shelf generated from Svalbard, within 200 nm and the Nansen Basin beyond, with no distinction between them; the Svalbard Treaty dispute is not litigated on the map (PROVENANCE §15.2).
> - §4.1 citations: the two fisheries zones also cite UNCLOS arts 55–58 (owner, 2026-09-17). petroleumsloven § 1-6, luftfartsloven § 1-1 and UNCLOS art. 303 are dropped (owner, 2026-09-17; the owner prefers public-international-law sources); the two zone regulations (1977 nr. 6, 1980 nr. 4) are quoted in full. Kontinentalsokkelen cites lov 18. juni 2021 nr. 89 § 1 for "kontinentalsokkelloven" (owner, 2026-09-17; PROVENANCE §16.3) and HR-2023-491-P avsnitt 220 (owner, 2026-09-17).
> - §6 layout: everything AGPL-licensed (front end, scripts, `package.json`, the AGPL text) lives under `code/`; `data/` (NLOD/CC BY) and `docs/` (AGPL, aligned with the code) stay at the root; the root `LICENSE.md` maps the three. `npm` runs inside `code/`; `dist/` is written at the root. Hosting: GitHub Pages via GitHub Actions.

| Decision | Choice |
|---|---|
| Geographic scope | Fastlands-Norge, Svalbard, Jan Mayen, Bouvetøya |
| Vertical strata | Airspace, water column, seabed + subsoil — all as distinct 3D volumes |
| Seabed representation | **Schematic** profile, not real bathymetry |
| Delivery | Single self-contained HTML file, externally hosted, embedded in Canvas via `<iframe>` |
| Engine | CesiumJS, full globe |
| Language | Bilingual, runtime toggle (Norwegian bokmål / English) |
| Legal annotation depth | Citation **plus verbatim quoted provision** |
| Contested zones | Neutral visual marker only — **no characterising text** |
| Extra layers | **None.** No FIR boundaries, no petroleum blocks, no cables/pipelines, no Barents Sea Special Area polygon. In the Barents Sea, use the agreed delimitation coordinates only. |

That last row matters: the 2010 Norway–Russia treaty enters the model *only* as the agreed delimitation line already present in the Kartverket dataset. Do not construct a Special Area polygon.

---

## 2. Data sources — verified

### 2.1 Primary: Kartverket, "Norges maritime grenser"

The authoritative Norwegian dataset. Covers all four geographies. Two access routes, both verified working on 2026-09-17:

**Route A — ArcGIS REST (used for the committed snapshot).** Fiskeridirektoratet hosts a mirror that serves GeoJSON in WGS84 directly, no key, no conversion:

```
https://portal.fiskeridir.no/arcgis/rest/services/Norges_maritime_grenselinjer/MapServer/{LAYER}/query
  ?where=1%3D1&outFields=*&returnGeometry=true&outSR=4326&f=geojson
```

**Route B — Geonorge (authoritative, for citation and re-verification).**
Dataset UUID `e106adf4-c9d8-4fce-a9b5-7886a4126d23`.
Formats: FGDB, GML, SOSI, PostGIS. Projections: EPSG:25833 (EUREF89 UTM 33N) or EPSG:4258 (ETRS89 geographic).
Capabilities: `https://nedlasting.geonorge.no/api/capabilities/e106adf4-c9d8-4fce-a9b5-7886a4126d23`

Route A is a convenience mirror. **Before shipping, re-verify a sample of Route A geometry against a Route B download** — at minimum the mainland baseline and the 12 nm territorial limit — and record the result in `data/PROVENANCE.md`. Note the datum difference is negligible here (ETRS89 vs WGS84 diverge by a few decimetres in Norway) but state it rather than ignore it.

A snapshot of Route A is already committed at `data/raw/`. Re-fetch with `code/scripts/fetch_boundaries.py`.

### 2.2 Layer inventory (as fetched, 2026-09-17)

Total: **9 301 vertices, ~400 KB** of GeoJSON. All geometries are polylines.

| # | Layer | Feat. | Vert. | Features present |
|---|---|---|---|---|
| 0 | Grunnlinje | 7 | 485 | Norges grunnlinje (mainland); Spitsbergen/Nordaustlandet/Edgeøya; Kong Karls Land; Kvitøya; Hopen; Bjørnøya; Jan Mayen |
| 1 | 1 nautisk mil | 1 | 329 | mainland |
| 2 | 4 nautiske mil | 1 | 398 | mainland |
| 3 | 6 nautiske mil | 1 | 477 | mainland |
| 4 | 10 nautiske mil | 1 | 649 | mainland |
| 5 | Territorialgrense 12 nm | 8 | 3 461 | Fastlands-Norge; Spitsbergen m.fl.; Bjørnøya; Hopen; Kvitøya; Kong Karls Land; Jan Mayen; **Bouvetøya** |
| 6 | Tilstøtende sone 24 nm | 1 | 679 | mainland only |
| 7 | 200 nautiske mil | 3 | 1 822 | Fastlands-Norge; Jan Mayen; Svalbard |
| 8 | Avtalt avgrensningslinje | 11 | 389 | Storbritannia; Russland; Russland (Varangerfjorden); Sverige (×3, incl. Iddefjorden/Grisebåen); Danmark; Danmark (Færøyene); Jan Mayen–Danmark (Grønland); Jan Mayen–Island; Svalbard–Danmark (Grønland) |
| 9 | Yttergrense for kontinentalsokkel | 1 | 202 | outer limit beyond 200 nm |
| 10 | Avgrensningslinje for kontinentalsokkel | 2 | 50 | Norge–Russland; Norge/Island (Jan Mayen area) |
| 11 | Andre staters økonomiske soner | 4 | 360 | Island; Danmark ×3 |

### 2.3 Legally significant features of the data

Read these before modelling — they are not incidental.

- **Layer 7 "200 nautiske mil ved Svalbard" is the fiskevernsonen**, not an EEZ. Norway has not claimed a full exclusive economic zone around Svalbard. The geometry is a 200 nm line; the zone it bounds is a fisheries protection zone. Label and model it as such.
- **Layer 7 "200 nautiske mil ved Jan Mayen" is the fiskerisonen**, likewise not a full EEZ.
- **Layer 6 exists for the mainland only.** Norway's contiguous zone was established for Fastlands-Norge and does not extend to Svalbard, Jan Mayen or Bouvetøya. This asymmetry is pedagogically useful — surface it rather than smoothing it over.
- **Bouvetøya appears only in layer 5** (12 nm territorial sea). There is no Bouvetøya baseline and no 200 nm line in this dataset. See §3 (gaps).
- **Layers 1/4/6/10 nm are historical fisheries limits**, mainland only. The 4 nm limit is the one at issue in *Fisheries (United Kingdom v. Norway)*, ICJ Reports 1951 p. 116. Ship these as an optional overlay — they cost almost nothing and carry a case the course almost certainly covers.

### 2.4 Licensing and attribution

Kartverket data is released under NLOD / CC BY 4.0 — attribution is required and must appear in the UI, not only in the source. CesiumJS is Apache-2.0. If OpenStreetMap imagery is used, its attribution is likewise mandatory and must remain visible. Build a persistent, legible attribution line into the chrome; do not bury it behind a modal.

---

## 3. Known data gaps — resolve with Øby, do not guess

1. **Bouvetøya beyond 12 nm.** The dataset gives a territorial sea but no baseline and no 200 nm limit. Ask whether Norway has established a zone there and, if so, source it. Until answered, render Bouvetøya with the territorial sea only and mark the outer extent as *not modelled* — an explicit absence, never an inferred circle.
2. **Internal waters require a coastline.** The baseline layer alone cannot close the landward polygon. Use Geonorge N250 Kartdata (or N1000 if N250 proves too heavy) for the coastline, and record which was used. Generalisation level directly affects how internal waters render in fjords — check Vestfjorden and the Oslofjord visually.
3. **Seabed profile parameters.** The schematic profile (§5.2) needs defensible depth figures. Derive indicative values from GEBCO cross-sections and have Øby sanity-check them; they are illustrative, not survey data, and the UI must say so.

---

## 4. Zone model

The legal ontology is the core of this project. Each zone is a record combining geometry, a vertical stratum set, and a bilingual legal-basis payload.

```ts
interface Zone {
  id: string;
  geography: 'mainland' | 'svalbard' | 'janmayen' | 'bouvetoya';
  strata: Array<'airspace' | 'watercolumn' | 'seabed' | 'subsoil'>;
  horizontal: GeoJSON.Polygon | GeoJSON.MultiPolygon;
  contested: boolean;              // drives a neutral marker ONLY — no text
  notModelled?: string[];          // e.g. ['outer-limit'] for Bouvetøya
  legal: {
    no: LegalPayload;
    en: LegalPayload;
  };
}

interface LegalPayload {
  name: string;
  citations: Array<{
    source: string;                // e.g. "territorialfarvannsloven § 4"
    quote: string;                 // verbatim operative wording
    quoteLang: 'no' | 'en';        // Norwegian statutes stay Norwegian in BOTH modes
    url?: string;
  }>;
  summary: string;                 // 2–3 sentences: what Norway may and may not do
}
```

### 4.1 Zones to model

| Zone | Extent | Strata | Norwegian basis | UNCLOS |
|---|---|---|---|---|
| Indre farvann | landward of baseline | air, water, seabed, subsoil | territorialfarvannsloven § 3 | arts 2, 8 |
| Sjøterritoriet | baseline → 12 nm | air, water, seabed, subsoil | territorialfarvannsloven §§ 1–2 | arts 2, 3, 17 |
| Tilstøtende sone | → 24 nm, **mainland only** | water | territorialfarvannsloven § 4 | arts 33, 303 |
| Norges økonomiske sone | → 200 nm, mainland | water, seabed | lov om Norges økonomiske sone § 1 | arts 55–58 |
| Fiskevernsonen ved Svalbard | → 200 nm | water | forskrift 3. juni 1977 nr. 6 | — |
| Fiskerisonen ved Jan Mayen | → 200 nm | water | forskrift 23. mai 1980 nr. 4 | — |
| Kontinentalsokkelen | → 200 nm and beyond to outer limit | seabed, subsoil | kontinentalsokkelloven; petroleumsloven § 1-6 | arts 76–79 |
| Det åpne hav | water beyond 200 nm | water | — | arts 86–87 |
| Området (the Area) | seabed beyond national jurisdiction | seabed, subsoil | — | arts 1(1)(1), 136–137 |
| Nasjonalt luftrom | over land, internal waters, territorial sea | air | luftfartsloven § 1-1 | art 2(2) |
| Luftrom utenfor sjøterritoriet (user-facing label: *internasjonalt luftrom* / *international airspace*, owner 2026-09-17) | above contiguous zone, EEZ, high seas | air | — | arts 58(1), 87(1)(b) |

Plus the optional historical fisheries overlay (1/4/6/10 nm), which carries a citation to the 1951 ICJ judgment rather than a statutory provision.

### 4.2 Overlap is the point

The teaching payoff is that a single vertical column can sit in several regimes at once — e.g. at 150 nm off Møre: Norwegian sovereign rights over the seabed, Norwegian sovereign rights over water-column resources, and high-seas freedom of overflight above. The UI must make a **column query** possible: click anywhere and get the full stack of regimes at that point, top to bottom, not just the topmost polygon. Build this as a first-class feature, not an afterthought.

---

## 5. Vertical model

### 5.1 The scale problem

At true scale, 200 nm ≈ 370 km horizontally; airspace to the Kármán line ≈ 100 km; shelf depth ≈ 0.2–3 km. The seabed stratum is under 1% of the EEZ's width and is effectively invisible.

**Solution: a vertical-exaggeration slider, logarithmic, range 1×–200×, default 20×, with detents at 1 / 5 / 20 / 50 / 100 / 200.** A permanent readout shows the current factor, and the 1× detent is labelled "true scale". Exaggeration becomes something students see and reason about rather than a hidden distortion.

Cesium's `Scene.verticalExaggeration` applies to terrain and 3D Tiles, **not** to entity heights. Apply the factor yourself when constructing geometry and rebuild the affected primitives on change. Debounce the slider; rebuilding 9 000 vertices of extruded polygons on every frame will stall mobile.

### 5.2 Stratum extents

Nominal, pre-exaggeration:

- **Airspace**: 0 → 100 km. Fade the top 20 km to a gradient rather than a hard surface — the upper limit of national airspace is undefined in international law. Carry a neutral marker there (§1: no characterising text).
- **Water column**: 0 → seabed.
- **Seabed surface (schematic)**: shelf ≈ −200 to −500 m out to the shelf break; continental slope down to ≈ −2 500 to −3 000 m; abyssal ≈ −3 500 to −4 000 m. The Norwegian Trench needs special handling — it is a nearshore deep and will look wrong if the profile is a simple monotonic function of distance from baseline.
- **Subsoil**: seabed → a nominal −10 km slab, rendered as bounded-but-open (the legal concept has no fixed lower limit). Do not draw a crisp floor that implies one.

Make every one of these a named constant in one config module, not a magic number scattered through geometry code.

---

## 6. Architecture

```
/
├─ SPEC.md                    ← this file
├─ CLAUDE.md                  ← working notes, conventions, gotchas
├─ index.html                 ← dev shell
├─ src/
│  ├─ main.js                 ← viewer bootstrap, camera
│  ├─ config.js               ← ALL constants: stratum extents, colours, exaggeration
│  ├─ zones.js                ← zone construction from zones.json
│  ├─ strata.js               ← extrusion + exaggeration
│  ├─ columnQuery.js          ← click → full vertical regime stack
│  ├─ crossSection.js         ← 2D perpendicular slice view
│  ├─ i18n.js                 ← no/en string tables
│  ├─ ui.js                   ← panels, toggles, slider, share-state
│  └─ styles.css
├─ data/
│  ├─ raw/                    ← committed GeoJSON snapshot (present)
│  ├─ build/zones.json        ← generated
│  └─ PROVENANCE.md           ← fetch dates, verification results, licence notes
├─ scripts/
│  ├─ fetch_boundaries.py
│  ├─ polygonise.py
│  ├─ fetch_legal.py          ← Lovdata + UNCLOS text
│  └─ build_zones.py
└─ dist/index.html            ← single-file bundle for hosting
```

**Bundling:** Vite + `vite-plugin-singlefile`. Inline everything except CesiumJS, which loads from CDN at a **pinned exact version** (verify the current release; do not use a floating tag).

**No Cesium ion token.** Use `EllipsoidTerrainProvider` and OpenStreetMap imagery. Rationale: the schematic seabed makes real terrain unnecessary, and a token is a failure mode that will silently break the app mid-semester years from now. This is deliberate — do not "improve" it by adding ion.

### 6.1 Data pipeline

1. `fetch_boundaries.py` — pull all 12 layers, write to `data/raw/`, record fetch timestamp.
2. `polygonise.py` — close zone polygons from lines + N250 coastline, clipped by delimitation lines and by other states' EEZ limits. Use Shapely; work in a projected CRS (EPSG:25833) for the topology, then reproject to EPSG:4326 for output. Do **not** polygonise in geographic coordinates.
3. Simplify to the vertex budget in §8 — **but exempt agreed delimitation lines from simplification.** Those are treaty coordinates; moving them by a kilometre to save bytes is not acceptable in a teaching tool about jurisdiction.
4. `fetch_legal.py` — pull statute text from Lovdata (`https://api.lovdata.no/v1/publicData/list`, free NL and SF packages, no key — verified reachable). Pull UNCLOS articles from an authoritative text. **Never quote a provision from model memory.** Every `quote` field must be traceable to a fetched document.
5. `build_zones.py` — emit `data/build/zones.json`.

Antimeridian handling: Svalbard geometry approaches 180°E in places. Test explicitly for polygons that wrap; Cesium will render a band across the globe if this is missed.

---

## 7. UI specification

- **Free-fly camera**, with preset viewpoints (mainland cross-section, Svalbard, Jan Mayen, Barents delimitation, shelf outer limit).
- **Layer toggles** per zone and per stratum, independently.
- **Column query**: click anywhere → panel listing every regime in that vertical column, ordered top to bottom, each with citation, verbatim provision and summary.
- **Cross-section mode**: a 2D slice perpendicular to the coast, showing the stacked columns. This is usually the single clearest view of the water-column/seabed/airspace distinction — treat it as a headline feature, not a bonus.
- **Vertical-exaggeration slider** per §5.1.
- **Language toggle** (NO/EN). Norwegian statutory quotations remain in Norwegian in both modes, with an English gloss available in EN mode. Do not translate statutory text as if it were authoritative.
- **Contested markers**: neutral visual indicator on affected zones. No explanatory text of any kind — Øby supplies that in teaching.
- **Shareable URL state**: camera position, active layers, exaggeration, language. Course links should open a configured view directly.
- **Attribution line**: persistent and legible (§2.4).

Touch-first: every control must be operable one-handed on a phone. Panels should not occlude more than ~40% of the viewport on a 375 px-wide screen.

---

## 8. Budgets and targets

| Metric | Target |
|---|---|
| `dist/index.html` | ≤ 900 KB including inlined `zones.json` |
| Cesium (CDN, cached) | ~4 MB |
| Time to interactive, mid-range Android on 4G | ≤ 5 s |
| Frame rate while orbiting | ≥ 30 fps |
| Total polygon vertices after simplification | ≤ 12 000 |

**Device targets:** iOS Safari 16+, Firefox for Android (current), Chrome for Android (current), desktop Chrome / Firefox / Safari / Edge. Firefox mobile is a named requirement — test it specifically, it is the one most likely to be skipped.

---

## 9. Build phases

**Phase 1 — data.** Fetch, polygonise, verify against Geonorge, resolve the coastline source. *Done when:* `zones.json` validates, every zone closes, delimitation lines are byte-identical to source, and `PROVENANCE.md` records the verification.

**Phase 2 — geometry.** Cesium viewer, extruded zone volumes, exaggeration slider. *Done when:* all four geographies render, the slider rebuilds cleanly at every detent, and nothing wraps the antimeridian.

**Phase 3 — legal content.** Lovdata and UNCLOS fetch, bilingual payloads. *Done when:* every `quote` traces to a fetched document and Øby has reviewed the zone/citation mapping.

**Phase 4 — interaction.** Column query, cross-section, layer toggles, language toggle, URL state.

**Phase 5 — packaging and device testing.** Single-file bundle, Canvas iframe test, the full device matrix including Firefox mobile.

### Canvas embedding

Canvas's rich content editor strips `<script>`, so the app cannot live inside a Canvas page. Host `dist/index.html` externally and embed:

```html
<iframe src="https://<host>/jurisdiction-3d/"
        width="100%" height="700"
        style="border:0" allowfullscreen
        title="Norwegian maritime jurisdiction — 3D model"></iframe>
```

Confirm the host is permitted by UiO's Canvas CSP before Phase 5 concludes.

---

## 10. Standing rules

1. **Never quote a legal provision from memory.** Fetch it. Every quotation is traceable to a source document or it does not ship.
2. **Never invent geometry.** If a limit is not in the data, mark it *not modelled* and ask. An absent Bouvetøya outer limit is a teaching prompt; a fabricated one is a defect in a tool about the law of jurisdiction.
3. **Never simplify a delimitation line.**
4. **Ask Øby rather than guess** on any legal characterisation. He has asked to verify sources and will.
5. Keep the contested-zone treatment strictly visual. No text.
