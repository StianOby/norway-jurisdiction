# Provenance

## data/raw/ — Norges maritime grenser

**Fetched:** 2026-09-17
**Source:** Fiskeridirektoratet ArcGIS REST mirror of Kartverket's official dataset
`https://portal.fiskeridir.no/arcgis/rest/services/Norges_maritime_grenselinjer/MapServer/{LAYER}/query`
Query: `where=1=1&outFields=*&returnGeometry=true&outSR=4326&f=geojson`

**Authoritative equivalent:** Geonorge dataset UUID `e106adf4-c9d8-4fce-a9b5-7886a4126d23`
(FGDB / GML / SOSI / PostGIS; EPSG:25833 or EPSG:4258)

**Licence:** Kartverket, NLOD / CC BY 4.0 — attribution required in the UI.

**Contents:** 12 polyline layers, 9 301 vertices, ~400 KB.

| File | Features | Vertices |
|---|---|---|
| 0-grunnlinje | 7 | 485 |
| 1-1nm | 1 | 329 |
| 2-4nm | 1 | 398 |
| 3-6nm | 1 | 477 |
| 4-10nm | 1 | 649 |
| 5-territorialgrense-12nm | 8 | 3 461 |
| 6-tilstotende-sone-24nm | 1 | 679 |
| 7-200nm | 3 | 1 822 |
| 8-avtalt-avgrensningslinje | 11 | 389 |
| 9-yttergrense-kontinentalsokkel | 1 | 202 |
| 10-avgrensningslinje-kontinentalsokkel | 2 | 50 |
| 11-andre-staters-eez | 4 | 360 |

## Outstanding verification

- [ ] Cross-check Route A (ArcGIS mirror) geometry against a Route B (Geonorge) download — at minimum the mainland baseline and the 12 nm territorial limit. Record the maximum deviation found.
- [ ] Note the ETRS89 / WGS84 datum difference explicitly (sub-metre in Norway) rather than treating the two as identical.
- [ ] Record coastline source and generalisation level once chosen (N250 vs N1000).
- [ ] Record source for the schematic seabed depth figures.
