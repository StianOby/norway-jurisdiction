# norway-jurisdiction

An interactive 3D teaching model of the extent of Norway's spatial jurisdiction
under public international law — airspace, water column, seabed and subsoil —
built on CesiumJS for use in university courses on the law of jurisdiction.

**Scope:** mainland Norway, Svalbard and Jan Mayen. Bouvetøya is deliberately
not included.

**Live version:** <https://stianoby.github.io/norway-jurisdiction/>

- Project brief: [docs/SPEC.md](docs/SPEC.md) · working notes: [CLAUDE.md](CLAUDE.md)
- Data provenance and verification: [data/PROVENANCE.md](data/PROVENANCE.md)

## Licensing — code and data are separate

| What | Where | Licence |
|---|---|---|
| Application code and scripts | `code/` | GNU AGPL v3 ([code/LICENSE](code/LICENSE)) |
| Documentation | `docs/`, this file, `CLAUDE.md` | GNU AGPL v3, aligned with the code |
| Geodata (raw and derived) | `data/` and the geometry inlined into `dist/index.html` | © Kartverket, NLOD 2.0 / CC BY 4.0; © Marine Regions / Flanders Marine Institute, CC BY 4.0; GEBCO 2020 (public domain, attribution) ([data/LICENSE.md](data/LICENSE.md)) |

The AGPL does not extend to the data; the bundle is an aggregation of the two.
[LICENSE.md](LICENSE.md) explains the relationship. Attribution to Kartverket,
Norsk Polarinstitutt and Marine Regions must remain visible in the UI.

## Build

All commands run from `code/` (the scripts locate `data/` relative to the repository root):

```
cd code
npm install
pip install -r scripts/requirements.txt
python scripts/fetch_boundaries.py --compare ../data/raw   # re-fetch Route A and diff (optional)
python scripts/fetch_geonorge.py                           # Route B + N1000 coast (optional re-fetch)
python scripts/fetch_marineregions.py                      # Russian 200 nm line, ECS polygons (optional re-fetch)
python scripts/fetch_gebco.py                              # coarse GEBCO 2020 grid for the schematic seabed (optional re-fetch)
python scripts/build_seabed.py --render                    # data/build/seabed.json + docs/renders/seabed-schematic.png
python scripts/fetch_legal.py                              # Lovdata acts/regulations, UNCLOS (DOALOS), HR-2023-491-P → data/raw/legal/ (optional re-fetch; --compare diffs)
python scripts/build_legal.py --check                      # data/build/legal.json + LEGAL.md (the review copy of every quoted provision)
python scripts/polygonise.py                               # data/build/geometry.json
python scripts/build_zones.py --check                      # data/build/zones.json + REPORT.md (fails if any citation lacks a fetched quote)
npm run dev                                                # local dev server
npm run build                                              # ../dist/index.html — the single-file bundle
```

## Using it

Click anywhere in the model for the **column** at that point — every regime from the airspace down
to the subsoil, each with its summary and the verbatim provisions. **Tverrsnitt / Cross-section**
draws a profile along a preset transect or two points you click; clicking in the profile queries
that column. **Del lenke / Share link** copies a URL that reopens the current view, layers,
exaggeration, language, column and section — use it for course links.

## Hosting

`main` is built and deployed to <https://stianoby.github.io/norway-jurisdiction/> by
`.github/workflows/pages.yml` (Settings → Pages → Source: *GitHub Actions*). The app is then embedded in
Canvas with the `<iframe>` in SPEC §9.
