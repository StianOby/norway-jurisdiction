# norway-jurisdiction

An interactive 3D teaching model of the extent of Norway's spatial jurisdiction
under public international law — airspace, water column, seabed and subsoil —
built on CesiumJS for use in university courses on the law of jurisdiction.

**Scope:** mainland Norway, Svalbard and Jan Mayen. Bouvetøya is deliberately
not included.

- Project brief: [docs/SPEC.md](docs/SPEC.md) · working notes: [CLAUDE.md](CLAUDE.md)
- Data provenance and verification: [data/PROVENANCE.md](data/PROVENANCE.md)

## Licensing — code and data are separate

| What | Where | Licence |
|---|---|---|
| Application code and scripts | `code/` | GNU AGPL v3 ([code/LICENSE](code/LICENSE)) |
| Documentation | `docs/`, this file, `CLAUDE.md` | GNU AGPL v3, aligned with the code |
| Geodata (raw and derived) | `data/` and the geometry inlined into `dist/index.html` | © Kartverket, NLOD 2.0 / CC BY 4.0; © Marine Regions / Flanders Marine Institute, CC BY 4.0 ([data/LICENSE.md](data/LICENSE.md)) |

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
python scripts/polygonise.py                               # data/build/geometry.json
python scripts/build_zones.py --check                      # data/build/zones.json + REPORT.md
npm run dev                                                # local dev server
npm run build                                              # ../dist/index.html — the single-file bundle
```

## Hosting

`main` is built and deployed to GitHub Pages by `.github/workflows/pages.yml`
(Settings → Pages → Source: *GitHub Actions*). The app is then embedded in
Canvas with the `<iframe>` in SPEC §9.
