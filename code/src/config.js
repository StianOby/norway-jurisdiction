// ALL numeric constants for the 3D model live here (SPEC §5.2, §6). No magic numbers elsewhere.
// Depths are metres relative to the sea surface, negative downwards. Nothing here is survey data:
// the seabed is schematic (SPEC §1) and its levels are indicative values derived from GEBCO 2020
// class means (data/PROVENANCE.md §14) for the owner to sanity-check.

export const CESIUM_VERSION = '1.145.0';

// Matches build_zones.BBOX; used for the antimeridian assertion and globe translucency region.
export const MODEL_BBOX = { west: -15, south: 55, east: 46, north: 86 };

export const GEOGRAPHIES = ['mainland', 'svalbard', 'janmayen'];

// SPEC §5.1: logarithmic slider, detents, "true scale" at 1x.
export const EXAGGERATION = {
  min: 1,
  max: 200,
  initial: 20,
  detents: [1, 5, 20, 50, 100, 200],
  snapFraction: 0.05, // snap to a detent when within 5 % of it (log space)
  debounceMs: 150,
};

// SPEC §5.2 stratum extents, pre-exaggeration.
export const AIRSPACE = {
  top: 100_000, // m — Kármán line; the upper limit of national airspace is undefined in law
  fadeFrom: 80_000, // m — the top 20 km fade to transparent rather than end in a surface
};
export const SUBSOIL = {
  thickness: 10_000, // m below the seabed — nominal; the legal concept has no fixed lower limit
  fadeFrom: 6_000, // m below the seabed where the slab starts fading (bounded-but-open)
};

// Schematic seabed. The class map (data/build/seabed.json, derived from GEBCO 2020 by
// code/scripts/build_seabed.py) assigns each 0.25° x 0.5° cell one of these classes; the model
// gives each class a single named depth and smooths across class boundaries, which is what
// produces the continental slope. Change a level here and the model, the cross-section and the
// verification render (build_seabed.py reads this file) all follow.
export const SEABED = {
  levels: {
    L: -50, // land cells, only so that interpolation near the coast does not spike
    S: -250, // continental shelf
    T: -500, // the Norwegian Trench (Skagerrak and along the south/west coast) — a nearshore deep
    P: -1500, // slope and plateaus (e.g. Vøringplatået)
    A: -3300, // abyssal plains (Norskehavet, Lofoten Basin, Greenland Sea)
    N: -4000, // deep Arctic basin (Nansen Basin)
  },
  smoothingSigmaCells: 0.8, // Gaussian sigma in grid cells (≈ 20–25 km; the slope spans about ±3σ) applied to the level field
};

// Vertical clearance between coincident surfaces (water-column floor, seabed, subsoil roof) so
// they do not z-fight. Metres, pre-exaggeration; invisible at any zoom that matters.
export const SEABED_CLEARANCE = 30;

// Volume meshing: triangles are subdivided until no edge exceeds this, so that volume bottoms
// follow the schematic seabed. Degrees of arc (0.5° ≈ 55 km).
export const MESH = { maxEdgeDeg: 0.5 };

// Colours per zone id (CSS hex) and alpha per stratum.
export const ZONE_COLOURS = {
  'mainland-internal-waters': '#1c9c8f',
  'svalbard-internal-waters': '#1c9c8f',
  'janmayen-internal-waters': '#1c9c8f',
  'mainland-territorial-sea': '#2f6fd6',
  'svalbard-territorial-sea': '#2f6fd6',
  'janmayen-territorial-sea': '#2f6fd6',
  'mainland-contiguous-zone': '#8a4fd1',
  'mainland-eez': '#3aa655',
  'svalbard-fpz': '#e9862c',
  'janmayen-fisheries-zone': '#d9b52a',
  'continental-shelf': '#8c5a2b',
  'high-seas': '#9fb7c9',
  'the-area': '#4b4b4b',
  'national-airspace': '#6fc3f7',
  'airspace-beyond-territorial-sea': '#c5b8f0',
};
export const STRATUM_ALPHA = { airspace: 0.07, watercolumn: 0.32, seabed: 0.85, subsoil: 0.28 };

// Neutral contested marker: screen-space hatching (SPEC §1/§7 — visual only, no text).
export const HATCH = { period: 14, width: 5 }; // pixels

export const CAMERA_HOME = { lon: 12.0, lat: 60.0, height: 5_500_000, heading: 0, pitch: -70 };

// Globe translucency inside MODEL_BBOX so volumes below the sea surface are visible.
export const GLOBE = { frontFaceAlpha: 0.55, backFaceAlpha: 1.0, undergroundColor: '#5b7f9b', translucentInsideBboxOnly: false };

export const OSM_TILES = 'https://tile.openstreetmap.org/';
