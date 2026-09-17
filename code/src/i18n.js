// UI string tables, no / en (SPEC §7). Zone names come from zones.json (legal.<lang>.name).
// Legal text is never here: quotations are Phase 3 data, fetched, never typed (SPEC §10.1).

export const STRINGS = {
  no: {
    title: 'Norges jurisdiksjon til havs',
    subtitle: '3D-modell av soner i luftrom, vannsøyle, havbunn og undergrunn',
    scope: 'Modellen dekker Fastlands-Norge, Svalbard og Jan Mayen. Bouvetøya er ikke med.',
    exaggeration: 'Vertikal overdrivelse',
    trueScale: 'sann skala',
    strata: 'Lag',
    zones: 'Soner',
    airspace: 'Luftrom',
    watercolumn: 'Vannsøyle',
    seabed: 'Havbunn',
    subsoil: 'Undergrunn',
    notModelled: 'ikke modellert',
    contestedMarker: 'skravert: omstridt',
    seabedNote: 'Havbunnen er skjematisk (indikative dybder fra GEBCO 2020), ikke kartlagt bunn. Luftrommets øvre grense er ikke fastlagt i folkeretten; toppen tones derfor ut.',
    attribution: 'Grenser og kystlinje: © Kartverket (NLOD 2.0/CC BY 4.0); kystlinje Svalbard og Jan Mayen: © Norsk Polarinstitutt · Russlands 200 nm-grense og sokkelpolygoner: Marine Regions / Flanders Marine Institute (CC BY 4.0) · Havbunn: skjematisk, etter GEBCO 2020 · Bakgrunnskart: © OpenStreetMap-bidragsytere · CesiumJS',
    panelToggle: 'Meny',
    language: 'English',
    home: 'Start',
  },
  en: {
    title: 'Norway’s maritime jurisdiction',
    subtitle: '3D model of zones in airspace, water column, seabed and subsoil',
    scope: 'The model covers mainland Norway, Svalbard and Jan Mayen. Bouvetøya is not included.',
    exaggeration: 'Vertical exaggeration',
    trueScale: 'true scale',
    strata: 'Strata',
    zones: 'Zones',
    airspace: 'Airspace',
    watercolumn: 'Water column',
    seabed: 'Seabed',
    subsoil: 'Subsoil',
    notModelled: 'not modelled',
    contestedMarker: 'hatched: contested',
    seabedNote: 'The seabed is schematic (indicative depths after GEBCO 2020), not surveyed bathymetry. The upper limit of airspace is undefined in international law; the top therefore fades out.',
    attribution: 'Limits and coastline: © Kartverket (NLOD 2.0/CC BY 4.0); Svalbard and Jan Mayen coastlines: © Norwegian Polar Institute · Russian 200 nm limit and shelf polygons: Marine Regions / Flanders Marine Institute (CC BY 4.0) · Seabed: schematic, after GEBCO 2020 · Basemap: © OpenStreetMap contributors · CesiumJS',
    panelToggle: 'Menu',
    language: 'Norsk',
    home: 'Home',
  },
};

let current = 'no';

export function setLanguage(lang) {
  if (!STRINGS[lang]) throw new Error(`no strings for ${lang}`);
  current = lang;
  document.documentElement.lang = lang;
}

export function language() {
  return current;
}

export function t(key) {
  return STRINGS[current][key] ?? STRINGS.no[key] ?? key;
}
