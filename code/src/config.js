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
// The slider exaggerates the water column, seabed and subsoil only. The airspace is always drawn
// at true scale (owner decision 2026-09-17): 100 km is legible as it is, and 20× of it was a
// 2 000 km fence. The readout says so whenever the factor is not 1.
export const stratumFactor = (stratum, factor) => (stratum === 'airspace' ? 1 : factor);
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
  'international-airspace': '#c5b8f0',
};
export const STRATUM_ALPHA = { airspace: 0.07, watercolumn: 0.32, seabed: 0.85, subsoil: 0.28 };

// Neutral contested marker: screen-space hatching (SPEC §1/§7 — visual only, no text).
export const HATCH = { period: 14, width: 5 }; // pixels

export const CAMERA_HOME = { lon: 12.0, lat: 60.0, height: 5_500_000, heading: 0, pitch: -70 };

// Order of the strata in a vertical column, top to bottom (SPEC §4.2, §7 column query).
export const STRATA_ORDER = ['airspace', 'watercolumn', 'seabed', 'subsoil'];

// Preset viewpoints (SPEC §7): a camera and, where the view is about a profile, the transect the
// cross-section shows. Transect endpoints are viewing choices, not legal geometry: each was chosen
// so that the profile crosses the zones named in the comment (checked against zones.json). Cameras
// look obliquely from the south so the 100 km airspace walls read as walls.
export const VIEWS = {
  'mainland-section': { // Møre → north-west: internal waters, TS, contiguous zone, EEZ, high seas over the shelf
    camera: { lon: 4.0, lat: 58.5, height: 1_100_000, heading: 0, pitch: -55 },
    transect: [[8.5, 63.4], [-1.5, 68.5]],
  },
  svalbard: { // Isfjorden → north: TS, fisheries protection zone, shelf, high seas beyond 200 nm (Nansen Basin)
    camera: { lon: 15.0, lat: 74.2, height: 1_200_000, heading: 0, pitch: -55 },
    transect: [[15.0, 78.2], [15.0, 85.5]],
  },
  janmayen: { // Jan Mayen → north-east: TS, fisheries zone over the shelf, high seas over the Area
    camera: { lon: -5.5, lat: 66.5, height: 900_000, heading: 0, pitch: -55 },
    transect: [[-8.7, 71.0], [-1.0, 74.8]],
  },
  'barents-delimitation': { // Finnmark → north across the Loop Hole, then the Svalbard zone; the 2010 treaty line to the east
    camera: { lon: 29.0, lat: 67.0, height: 1_000_000, heading: 0, pitch: -55 },
    transect: [[28.0, 71.0], [30.0, 75.5]],
  },
  'shelf-outer-limit': { // Lofoten → north-west: EEZ, high seas over the shelf beyond 200 nm (Banana Hole), Jan Mayen zone
    camera: { lon: 7.5, lat: 62.5, height: 1_100_000, heading: 0, pitch: -55 },
    transect: [[14.5, 68.0], [2.0, 71.5]],
  },
};

// Cross-section drawing (SPEC §7). The water column and seabed profile are drawn at the slider's
// exaggeration with the same horizontal scale as the distance axis (capped to what fits the
// height, and labelled so); the airspace and subsoil bands are fixed shares of the plot height —
// the airspace marked as not to scale (a scale break), the subsoil fading out with no floor.
export const SECTION = {
  samples: 480, // points along the transect
  airspaceShare: 0.22, // of the plot height, at least
  subsoilShare: 0.2, // of the plot height: the open-ended subsoil band
  minHeight: 120, // px — the canvas fills its box; never smaller than this
  seabedBand: 6, // px — the seabed stratum drawn as a band of this thickness on the profile
  margin: { top: 18, right: 14, bottom: 34, left: 46 }, // px
  hatch: { period: 9, width: 3 }, // px, contested marker (visual only, SPEC §1)
};

// The column-query probe on the globe: a vertical line through the whole column.
export const PROBE = { colour: '#ffffff', width: 2 };

// Globe translucency inside MODEL_BBOX so volumes below the sea surface are visible.
export const GLOBE = { frontFaceAlpha: 0.55, backFaceAlpha: 1.0, undergroundColor: '#5b7f9b', translucentInsideBboxOnly: false };

export const OSM_TILES = 'https://tile.openstreetmap.org/';
