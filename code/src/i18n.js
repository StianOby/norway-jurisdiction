// UI string tables, no / en (SPEC §7). Zone names come from zones.json (legal.<lang>.name).
// Legal text is never here: quotations are Phase 3 data, fetched, never typed (SPEC §10.1).
// Nothing here characterises a zone or a dispute (SPEC §1, §10.5).

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
    attribution: 'Grenser og kystlinje: © Kartverket (NLOD 2.0/CC BY 4.0); kystlinje Svalbard og Jan Mayen: © Norsk Polarinstitutt · Russlands 200 nm-grense og sokkelpolygoner: Marine Regions / Flanders Marine Institute (CC BY 4.0) · Havbunn: skjematisk, etter GEBCO 2020 · Lovtekst: Lovdata (NLOD 2.0); UNCLOS: FN/DOALOS; HR-2023-491-P: Norges Høyesterett · Bakgrunnskart: © OpenStreetMap-bidragsytere · CesiumJS',
    panelToggle: 'Meny',
    language: 'English',
    home: 'Start',
    share: 'Del lenke',
    shareCopied: 'Lenke kopiert',
    views: 'Utsnitt',
    'view-mainland-section': 'Fastlandet: snitt fra Møre',
    'view-svalbard': 'Svalbard',
    'view-janmayen': 'Jan Mayen',
    'view-barents-delimitation': 'Barentshavet: delelinjen',
    'view-shelf-outer-limit': 'Sokkelens yttergrense',
    column: 'Søyle',
    columnHint: 'Klikk hvor som helst i modellen for å se alle regimene i den loddrette søylen der, ovenfra og ned.',
    columnEmpty: 'Ingen søyle valgt. Klikk i modellen.',
    noZoneHere: 'ingen sone i modellen her',
    outsideModel: 'Utenfor modellens område.',
    quoteIn: 'Sitat på',
    translationLink: 'Høyesteretts engelske oversettelse',
    close: 'Lukk',
    section: 'Snitt',
    sectionTitle: 'Tverrsnitt',
    sectionHint: 'Velg et forhåndsdefinert snitt, eller tegn ditt eget: klikk to punkter i modellen. Klikk i snittet for å se søylen der.',
    sectionPick: 'Tegn snitt i modellen',
    sectionCustom: 'Eget snitt',
    sectionPickShort: 'Tegn',
    sectionPicking: 'Klikk startpunkt (A) i modellen …',
    sectionPickingB: 'Klikk sluttpunkt (B) …',
    sectionAxisKm: 'km fra A',
    notToScale: 'ikke i målestokk',
    sectionFitted: 'tilpasset høyden',
    sectionNote: 'Vannsøylen og havbunnsprofilen tegnes med modellens vertikale overdrivelse (begrenset til det som får plass); luftrommet er komprimert (skalabrudd). Undergrunnen har ingen fastlagt nedre grense og tones ut.',
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
    attribution: 'Limits and coastline: © Kartverket (NLOD 2.0/CC BY 4.0); Svalbard and Jan Mayen coastlines: © Norwegian Polar Institute · Russian 200 nm limit and shelf polygons: Marine Regions / Flanders Marine Institute (CC BY 4.0) · Seabed: schematic, after GEBCO 2020 · Statutes: Lovdata (NLOD 2.0); UNCLOS: UN/DOALOS; HR-2023-491-P: Supreme Court of Norway · Basemap: © OpenStreetMap contributors · CesiumJS',
    panelToggle: 'Menu',
    language: 'Norsk',
    home: 'Home',
    share: 'Share link',
    shareCopied: 'Link copied',
    views: 'Views',
    'view-mainland-section': 'Mainland: profile off Møre',
    'view-svalbard': 'Svalbard',
    'view-janmayen': 'Jan Mayen',
    'view-barents-delimitation': 'Barents Sea: the delimitation line',
    'view-shelf-outer-limit': 'Outer limit of the shelf',
    column: 'Column',
    columnHint: 'Click anywhere in the model to see every regime in the vertical column at that point, top to bottom.',
    columnEmpty: 'No column selected. Click in the model.',
    noZoneHere: 'no zone in the model here',
    outsideModel: 'Outside the model’s extent.',
    quoteIn: 'Quoted in',
    translationLink: 'the Supreme Court’s English translation',
    close: 'Close',
    section: 'Section',
    sectionTitle: 'Cross-section',
    sectionHint: 'Choose a preset profile or draw your own: click two points in the model. Click in the section to see the column there.',
    sectionPick: 'Draw a section in the model',
    sectionCustom: 'Custom section',
    sectionPickShort: 'Draw',
    sectionPicking: 'Click the start point (A) in the model …',
    sectionPickingB: 'Click the end point (B) …',
    sectionAxisKm: 'km from A',
    notToScale: 'not to scale',
    sectionFitted: 'fitted to height',
    sectionNote: 'The water column and seabed profile are drawn at the model’s vertical exaggeration (capped to what fits); the airspace is compressed (scale break). The subsoil has no fixed lower limit and fades out.',
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
