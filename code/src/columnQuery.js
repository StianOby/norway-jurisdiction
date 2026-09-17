// Column query (SPEC §4.2, §7): click anywhere → every regime in that vertical column, ordered
// top to bottom, each with citation, verbatim provision and summary. The lookup is a plain
// point-in-polygon test against the zone footprints in zones.json (the volumes are not pickable,
// and a click on the sea surface must report the seabed and subsoil below it too). No geometry
// is derived here beyond "is this point inside that polygon" (SPEC §10.2).
//
// Cesium is the CDN global (see index.html), not an import.
import { MODEL_BBOX, STRATA_ORDER, AIRSPACE, SUBSOIL, PROBE } from './config.js';
import { zones, footprint, partsOf } from './zones.js';
import { seabedDepth } from './seabed.js';
import { t } from './i18n.js';

const Cesium = globalThis.Cesium;

// ---------------------------------------------------------------------------------------------
// Point in polygon (even-odd ray casting in lon/lat), with a bbox pre-check per polygon part.

function ringContains(ring, lon, lat) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function bboxOf(ring) {
  let w = Infinity, s = Infinity, e = -Infinity, n = -Infinity;
  for (const [x, y] of ring) {
    if (x < w) w = x;
    if (x > e) e = x;
    if (y < s) s = y;
    if (y > n) n = y;
  }
  return { w, s, e, n };
}

// [{ zone, parts: [{ bbox, rings }], marked: [{ bbox, rings }] }] — built once. `marked` is the
// zone's contestedExtent (a neutral marker inside the extent, hatched in 3D — SPEC §1, §10.5).
const prep = (rings) => ({ bbox: bboxOf(rings[0]), rings });
const index = zones
  .map((z) => ({ zone: z, parts: footprint(z).map(prep), marked: partsOf(z.contestedExtent).map(prep) }))
  .filter((entry) => entry.parts.length);

function partContains(part, lon, lat) {
  const b = part.bbox;
  if (lon < b.w || lon > b.e || lat < b.s || lat > b.n) return false;
  if (!ringContains(part.rings[0], lon, lat)) return false;
  for (let i = 1; i < part.rings.length; i++) if (ringContains(part.rings[i], lon, lat)) return false;
  return true;
}

/** Zones whose footprint contains the point, in registry order, and the ids whose contested-extent marker covers it. */
export function zonesAt(lon, lat) {
  const hits = [];
  const marked = new Set();
  for (const { zone, parts, marked: m } of index) {
    if (parts.some((part) => partContains(part, lon, lat))) {
      hits.push(zone);
      if (m.some((part) => partContains(part, lon, lat))) marked.add(zone.id);
    }
  }
  return { hits, marked };
}

export function insideModel(lon, lat) {
  return lon >= MODEL_BBOX.west && lon <= MODEL_BBOX.east && lat >= MODEL_BBOX.south && lat <= MODEL_BBOX.north;
}

/**
 * The full stack at a point: one entry per stratum, top to bottom, each listing the zones that
 * occupy that stratum there (a stratum may hold several regimes at once — SPEC §4.2).
 */
export function stackAt(lon, lat) {
  const { hits, marked } = zonesAt(lon, lat);
  return {
    lon,
    lat,
    inside: insideModel(lon, lat),
    seabed: seabedDepth(lon, lat),
    marked, // zone ids whose contested-extent marker covers the point (visual only)
    strata: STRATA_ORDER.map((stratum) => ({ stratum, zones: hits.filter((z) => z.strata.includes(stratum)) })),
  };
}

// ---------------------------------------------------------------------------------------------
// Screen position → lon/lat on the ellipsoid. The camera may be below the surface (SPEC §6), where
// Camera.pickEllipsoid returns nothing, so the pick ray is intersected with the ellipsoid directly
// and the first intersection in front of the camera is used.

const scratchRay = new Cesium.Ray();
const scratchCartesian = new Cesium.Cartesian3();

export function pickLonLat(scene, windowPosition) {
  const ray = scene.camera.getPickRay(windowPosition, scratchRay);
  if (!ray) return null;
  const hit = Cesium.IntersectionTests.rayEllipsoid(ray, Cesium.Ellipsoid.WGS84);
  if (!hit) return null;
  const s = hit.start >= 0 ? hit.start : hit.stop;
  if (s < 0) return null;
  const point = Cesium.Ray.getPoint(ray, s, scratchCartesian);
  const carto = Cesium.Cartographic.fromCartesian(point);
  return { lon: Cesium.Math.toDegrees(carto.longitude), lat: Cesium.Math.toDegrees(carto.latitude) };
}

// ---------------------------------------------------------------------------------------------
// The probe: a vertical line on the globe through the whole queried column, from the bottom of the
// (nominal) subsoil to the top of the airspace, at the current exaggeration.

export class Probe {
  constructor(viewer) {
    this.viewer = viewer;
    this.point = null;
    this.exaggeration = 1;
    this.entity = viewer.entities.add({
      show: false,
      polyline: { positions: [], width: PROBE.width, material: Cesium.Color.fromCssColorString(PROBE.colour), arcType: Cesium.ArcType.NONE },
    });
  }

  set(point, exaggeration = this.exaggeration) {
    this.point = point;
    this.exaggeration = exaggeration;
    if (!point) { this.entity.show = false; this.viewer.scene.requestRender(); return; }
    const bottom = (seabedDepth(point.lon, point.lat) - SUBSOIL.thickness) * exaggeration;
    const top = AIRSPACE.top * exaggeration;
    this.entity.polyline.positions = [
      Cesium.Cartesian3.fromDegrees(point.lon, point.lat, bottom),
      Cesium.Cartesian3.fromDegrees(point.lon, point.lat, top),
    ];
    this.entity.show = true;
    this.viewer.scene.requestRender();
  }

  setExaggeration(f) { this.set(this.point, f); }
}

// ---------------------------------------------------------------------------------------------
// Panel content. Everything legal comes from zones.json: the zone's name and summary (owner-
// approved, Phase 3), and its citations with the verbatim quote. Norwegian quotations stay
// Norwegian in both languages (SPEC §7); on `en`, a citation that carries the Supreme Court's own
// translation shows it after the original, under the Court's caveat (translationNote, verbatim).

function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v;
    else e.setAttribute(k, v);
  }
  for (const c of children) e.append(c);
  return e;
}

const LANG_NAME = { no: 'norsk', en: 'English' };

function fmtCoord(v, pos, neg) {
  const a = Math.abs(v);
  const d = Math.floor(a);
  const m = (a - d) * 60;
  return `${d}°${m.toFixed(1).padStart(4, '0')}′${v >= 0 ? pos : neg}`;
}

export function fmtPoint(p) {
  return `${fmtCoord(p.lat, 'N', 'S')} ${fmtCoord(p.lon, 'E', 'W')}`;
}

function renderCitation(c, lang, colour) {
  const details = el('details', { class: 'citation' });
  const summary = el('summary', {}, c.citedAs);
  const quote = el('blockquote', { lang: c.quoteLang, class: 'quote' }, c.quote);
  const body = [summary];
  if (c.quoteLang !== lang) body.push(el('p', { class: 'quote-lang' }, `${t('quoteIn')} ${LANG_NAME[c.quoteLang] ?? c.quoteLang}`));
  body.push(quote);
  if (lang === 'en' && c.translation) {
    body.push(el('p', { class: 'caveat' }, c.translationNote ?? ''));
    body.push(el('blockquote', { lang: 'en', class: 'quote translation' }, c.translation));
  }
  const links = el('p', { class: 'source-link' }, el('a', { href: c.url, target: '_blank', rel: 'noopener' }, c.title));
  if (lang === 'en' && c.translation && c.translationUrl) {
    links.append(' · ', el('a', { href: c.translationUrl, target: '_blank', rel: 'noopener' }, t('translationLink')));
  }
  body.push(links);
  details.append(...body);
  details.style.setProperty('--c', colour);
  return details;
}

function renderZone(z, lang, colourOf, hatched) {
  const legal = z.legal[lang];
  const box = el('div', { class: `column-zone${hatched ? ' contested' : ''}` });
  box.style.setProperty('--c', colourOf(z.id));
  box.append(el('h4', {}, el('span', { class: `swatch${hatched ? ' hatched' : ''}` }), legal.name));
  if (legal.summary) box.append(el('p', { class: 'summary' }, legal.summary));
  const list = el('div', { class: 'citations' });
  for (const c of legal.citations) list.append(renderCitation(c, lang, colourOf(z.id)));
  box.append(list);
  return box;
}

/** Fill `container` with the stack for `lang`. `colourOf` maps zone id → CSS colour. */
export function renderStack(container, stack, lang, colourOf) {
  container.replaceChildren();
  container.append(el('p', { class: 'position' }, fmtPoint(stack)));
  if (!stack.inside) {
    container.append(el('p', { class: 'empty' }, t('outsideModel')));
    return;
  }
  for (const { stratum, zones: zs } of stack.strata) {
    const section = el('section', { class: `column-stratum ${stratum}` });
    section.append(el('h3', {}, t(stratum)));
    if (!zs.length) section.append(el('p', { class: 'empty' }, t('noZoneHere')));
    for (const z of zs) section.append(renderZone(z, lang, colourOf, z.contested || stack.marked.has(z.id)));
    container.append(section);
  }
}
