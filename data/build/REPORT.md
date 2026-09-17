# Build report — data/build/zones.json

Generated 2026-09-17T12:32:50+00:00. Simplification: arcs 100.0 m, coast 300.0 m, islands ≥ 3.0 km². Exempt: baselines (layer 0); agreed delimitation lines (layers 8, 10); other states' 200 nm limits (layer 11); continental-shelf outer limit (layer 9).

| Zone | Geography | Strata | Vertices | Source |
|---|---|---|---:|---|
| `mainland-internal-waters` | mainland | airspace, watercolumn, seabed, subsoil | 22181 | N1000 Kartdata Havflate (Kartverket, Geonorge GML EPSG:4258), topologically simplified, clipped to the landward side of 'Norges grunnlinje' (Route A layer 0, exact) |
| `mainland-territorial-sea` | mainland | airspace, watercolumn, seabed, subsoil | 345 | Kartverket Norges maritime grenser (Geonorge GML EPSG:4258) - Sjøterritorium: Sjøterritorium ved Fastlands-Norge |
| `svalbard-internal-waters` | svalbard | airspace, watercolumn, seabed, subsoil | 3671 | Svalbard baselines (Route A layer 0, exact, closed loops) minus Kartverket 'Landareal' (land=SJ, Norsk Polarinstitutt coastline as delivered in Norges maritime grenser, topologically simplified) |
| `svalbard-territorial-sea` | svalbard | airspace, watercolumn, seabed, subsoil | 718 | Kartverket Norges maritime grenser (Geonorge GML EPSG:4258) - Sjøterritorium: Sjøterritorium ved Hopen, Svalbard; Sjøterritorium ved Kvitøya, Svalbard; Sjøterritorium ved Kong Karls Land, Svalbard; Sjøterritorium ved Bjørnøya, Svalbard; Sjøterritorium ved Spitsbergen, Nordaustlandet og Edgeøya, Svalbard |
| `janmayen-internal-waters` | janmayen | airspace, watercolumn, seabed, subsoil | 257 | Kartverket Norges maritime grenser - IndreFarvann: Indre farvann ved Jan Mayen; Indre farvann ved Jan Mayen; Indre farvann ved Jan Mayen (as delivered; coastline vertices 6-decimal) |
| `janmayen-territorial-sea` | janmayen | airspace, watercolumn, seabed, subsoil | 222 | Kartverket Norges maritime grenser (Geonorge GML EPSG:4258) - Sjøterritorium: Sjøterritorium ved Jan Mayen |
| `mainland-contiguous-zone` | mainland | watercolumn | 317 | Kartverket Norges maritime grenser (Geonorge GML EPSG:4258) - TilstøtendeSone: Tilstøtende sone ved Fastlands-Norge |
| `mainland-eez` | mainland | watercolumn | 393 | Kartverket Norges maritime grenser (Geonorge GML EPSG:4258) - NorgesØkonomiskeSone: Norges økonomiske sone |
| `svalbard-fpz` | svalbard | watercolumn | 709 | Kartverket Norges maritime grenser (Geonorge GML EPSG:4258) - Fiskevernsone: Fiskevernsonen ved Svalbard |
| `janmayen-fisheries-zone` | janmayen | watercolumn | 255 | Kartverket Norges maritime grenser (Geonorge GML EPSG:4258) - Fiskerisone: Fiskerisonen ved Jan Mayen |
| `continental-shelf` | all | seabed, subsoil | 1322 | Kartverket Norges maritime grenser (Geonorge GML EPSG:4258) - Kontinentalsokkel: Norges kontinentalsokkel **+contestedExtent** (709 v.) **+contestedExtentInterval** (153 v.) |
| `high-seas` | all | watercolumn | 807 | Derived. Banana Hole: faces of the noded network of Norway's 200 nm lines (layer 7), agreed delimitation lines (layer 8) and other states' 200 nm limits (layer 11). Loop Hole: same network plus Marine Regions 'Russia 200 NM' (line_id 3697) and the Special Area ring (line_id 4697), Flanders Marine Institute Maritime Boundaries v12, CC BY 4.0, snapped (≤100 m) onto Kartverket lines. Nansen Basin: Norway's continental-shelf polygon beyond every 200 nm zone. |
| `the-area` | all | seabed, subsoil | 84 | Derived: Marine Regions high-seas pockets minus every Marine Regions extended-continental-shelf polygon (CLCS recommendation, submission, overlapping claim, DOALOS deposit; ECS v2, CC BY 4.0) minus Kartverket's Norwegian shelf and 200 nm zones; parts ≥ 1000 km² |
| `national-airspace` | all | airspace | 1115 | Mainland: Kartverket Norges maritime grenser - Territorialområde ved Fastlands-Norge (12 nm limit + delimitation lines + Riksgrense land border, border simplified); Svalbard and Jan Mayen: the 12 nm limits as closed loops (exterior rings of the territorial-sea polygons) |
| `airspace-beyond-territorial-sea` | all | airspace | 0 | — (derived from mainland-contiguous-zone, mainland-eez, svalbard-fpz, janmayen-fisheries-zone, high-seas) |

| Overlay | Vertices |
|---|---:|

**Zone polygon vertices:** 32396 (SPEC §8 target 35000); zones.json 856 KB.

## Checks

- all hard checks passed (closure, validity, antimeridian, bbox, schema, byte-identity of layers 0/8/9/10)
- WARN: 9-yttergrense-kontinentalsokkel: [36.980199999630315,84.505780556427567] not emitted — bounds no modelled zone (nearest boundary 254.4 km)
- WARN: 9-yttergrense-kontinentalsokkel: [35.203827305885511,84.564505610645483] not emitted — bounds no modelled zone (nearest boundary 128.6 km)
- WARN: 9-yttergrense-kontinentalsokkel: [33.390542777826965,84.617926750319327] not emitted — bounds no modelled zone (nearest boundary 46.3 km)
- WARN: 10-avgrensningslinje-kontinentalsokkel: [32.064266666773278,84.69463055625522] not emitted — bounds no modelled zone (nearest boundary 4.6 km)
- WARN: 11-andre-staters-eez: [-6.6373233610000009,67.611380360336426] on a boundary but represented by the coincident Norwegian-line vertex (junction end)
- WARN: 11-andre-staters-eez: [-0.4886949470000001,64.432816143266351] on a boundary but represented by the coincident Norwegian-line vertex (junction end)
- WARN: 11-andre-staters-eez: [-2.789716667,76.914005555584609] on a boundary but represented by the coincident Norwegian-line vertex (junction end)
- WARN: 11-andre-staters-eez: [-5.0076944439999993,74.363027777511036] on a boundary but represented by the coincident Norwegian-line vertex (junction end)
- WARN: 11-andre-staters-eez: [7.0887772780000002,83.889729999800664] on a boundary but represented by the coincident Norwegian-line vertex (junction end)
- WARN: 11-andre-staters-eez: [7.9279609170000001,83.71345655579502] on a boundary but represented by the coincident Norwegian-line vertex (junction end)
- verbatim:0-grunnlinje: 485/485
- verbatim:8-avtalt-avgrensningslinje: 389/389
- verbatim:9-yttergrense-kontinentalsokkel: 199/202
- verbatim:10-avgrensningslinje-kontinentalsokkel: 49/50
- verbatim:11-andre-staters-eez: 354/360
