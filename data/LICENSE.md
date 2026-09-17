# Licence for `data/`

The application **code** in this repository is licensed under the GNU AGPL v3
(the text is at `code/LICENSE`; the root `LICENSE.md` maps the whole repository). The AGPL does **not** apply to the contents
of this directory, nor to the zone geometry that the build inlines into
`dist/index.html`. That material is **data**, distributed under its own terms:

| Path | Origin | Licence |
|---|---|---|
| `raw/*.geojson` | Kartverket, "Norges maritime grenser", via Fiskeridirektoratet's ArcGIS mirror | NLOD 2.0 / CC BY 4.0 |
| `raw/geonorge/*NorgesMaritimeGrenser*.zip` | Kartverket, "Norges maritime grenser", via Geonorge (Svalbard coastline therein: Norsk Polarinstitutt) | NLOD 2.0 / CC BY 4.0 |
| `raw/geonorge/n1000-coast.geojson` | Kartverket, "N1000 Kartdata" (Kystkontur, Havflate), via Geonorge | NLOD 2.0 / CC BY 4.0 |
| `raw/marineregions/*.json` | Flanders Marine Institute, Maritime Boundaries Geodatabase v12 / Extended Continental Shelves v2, via the Marine Regions WFS | CC BY 4.0 |
| `raw/gebco/*.json` | GEBCO Compilation Group (2020) GEBCO 2020 Grid, via NOAA CoastWatch ERDDAP — coarse subset used only to derive the schematic seabed class map | GEBCO terms of use: public domain, attribution requested |
| `raw/legal/lovdata/*` | Lovdata, free data packages (`api.lovdata.no`): the cited acts and regulations, verbatim | NLOD 2.0 |
| `raw/legal/unclos/*` | United Nations, Division for Ocean Affairs and the Law of the Sea: the text of the Convention, by Part | UN publication of the Convention text (see `PROVENANCE.md` §16) |
| `raw/legal/hr/*` | Norges Høyesterett (domstol.no): HR-2023-491-P and the Court's English translation | Public domain: official Norwegian government documents (owner's statement, see `PROVENANCE.md` §16) |
| `legal/summaries.json` | Written for this project (zone summaries, bilingual) | CC BY 4.0 |
| `build/*` | Derived from the above by `code/scripts/` | CC BY 4.0-compatible terms of the sources; derivation is documented in `PROVENANCE.md` |

**Attribution required:** "Kartverket" (and, for Svalbard coastlines, "Norsk
Polarinstitutt") and "Marine Regions / Flanders Marine Institute" (Russian 200 nm limit,
extended-shelf polygons) must be credited wherever the data or derived geometry is
displayed, and GEBCO 2020 wherever the schematic seabed is shown — SPEC §2.4 requires a persistent attribution line in the UI. Quoted provisions credit Lovdata (NLOD 2.0 asks for attribution), the UN (UNCLOS) and the Supreme Court (HR-2023-491-P).

NLOD 2.0: <https://data.norge.no/nlod/no/2.0> · CC BY 4.0: <https://creativecommons.org/licenses/by/4.0/>

Why the separation matters: AGPL and NLOD/CC BY are not the same licence, and
the AGPL cannot be imposed on Kartverket's data. Keeping them in separate,
clearly labelled trees (code outside `data/`, data inside it) means each part
carries only its own terms, and the single-file bundle is a mere aggregation
of AGPL code with NLOD data, each still under its own licence.
