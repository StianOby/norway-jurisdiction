# Licensing — read this first

This repository holds two kinds of material under two different licences,
kept in separate directory trees so that each carries only its own terms.

| Tree | What it is | Licence | Full terms |
|---|---|---|---|
| `code/` | The application (Vite/CesiumJS front end in `code/src/`, `code/index.html`) and the data-pipeline scripts (`code/scripts/`) | **GNU Affero General Public License v3.0** | [`code/LICENSE`](code/LICENSE) |
| `docs/` | Project brief (`docs/SPEC.md`) and visual-check renders | **GNU Affero General Public License v3.0** | [`code/LICENSE`](code/LICENSE) |
| `data/` | Geodata — raw snapshots from Kartverket (via Fiskeridirektoratet and Geonorge), Norsk Polarinstitutt and Marine Regions, and the zone geometry derived from them | **NLOD 2.0 / CC BY 4.0** (Kartverket, Norsk Polarinstitutt) and **CC BY 4.0** (Marine Regions / Flanders Marine Institute) — attribution required | [`data/LICENSE.md`](data/LICENSE.md) |

`README.md` and `CLAUDE.md` at the root are documentation of the code and follow the code's licence.

## How the two relate

- The AGPL applies to the code and the documentation, and to nothing in `data/`.
  It cannot be imposed on Kartverket's or Marine Regions' data, and this
  repository does not attempt to.
- The data licences (NLOD 2.0, CC BY 4.0) apply to `data/` and to any geometry
  derived from it, wherever it ends up — including inside the built
  application. Their attribution requirement is met by a persistent
  attribution line in the application's user interface (SPEC §2.4).
- The built single-file application (`dist/index.html`, not committed) inlines
  the zone geometry from `data/build/zones.json` into the AGPL code. That file
  is a **mere aggregation**: the code parts remain under the AGPL and the data
  parts remain under their own licences. Neither licence is extended to the
  other by being shipped in the same file.
- CesiumJS is loaded at run time from a CDN and is not part of this repository
  (Apache-2.0). OpenStreetMap imagery, if displayed, carries its own
  attribution requirement (ODbL), met in the same attribution line.

NLOD 2.0: <https://data.norge.no/nlod/no/2.0> · CC BY 4.0: <https://creativecommons.org/licenses/by/4.0/> · AGPL v3: <https://www.gnu.org/licenses/agpl-3.0.html>
