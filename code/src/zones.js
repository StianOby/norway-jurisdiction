// Zone records from data/build/zones.json (SPEC §4). This module only reads and checks the
// data; it never constructs geometry (SPEC §10.2). Geometry text is inlined by Vite at build.
import zonesData from '../../data/build/zones.json';
import { MODEL_BBOX, ZONE_COLOURS } from './config.js';

export const meta = zonesData.meta;
export const zones = zonesData.zones;
const byId = new Map(zones.map((z) => [z.id, z]));

export function zone(id) {
  return byId.get(id);
}

/** Polygon parts of a GeoJSON Polygon/MultiPolygon as arrays of rings (outer first). */
export function partsOf(geom) {
  if (!geom) return [];
  if (geom.type === 'Polygon') return [geom.coordinates];
  if (geom.type === 'MultiPolygon') return geom.coordinates;
  throw new Error(`unsupported geometry ${geom.type}`);
}

/**
 * The polygons a zone occupies. A zone with `derivedFrom` (international airspace)
 * has no geometry of its own: it is the union of its members, so their parts are returned.
 */
export function footprint(z) {
  if (z.derivedFrom) return z.derivedFrom.flatMap((id) => partsOf(byId.get(id).horizontal));
  return partsOf(z.horizontal);
}

/**
 * Polygons of the opaque render mask (data/build/zones.json `renderMask`): the complement of the
 * water-column zones, rebuilt from references into the zones' own rings plus literal points.
 * Returns GeoJSON-style parts (outer ring first, closed rings) — a render aid, not legal geometry.
 */
export function renderMaskParts() {
  const mask = zonesData.renderMask;
  if (!mask) return [];
  const ringOf = (id, part, ring) => {
    const g = byId.get(id).horizontal;
    return (g.type === 'Polygon' ? [g.coordinates] : g.coordinates)[part][ring];
  };
  const rebuild = (runs) => {
    const out = [];
    for (const r of runs) {
      if (r.length === 2) { out.push([r[0], r[1]]); continue; }
      const [id, part, ring, start, count, step] = r;
      const src = ringOf(id, part, ring);
      const n = src.length - 1;
      for (let k = 0; k < count; k++) out.push(src[(((start + k * (step || 1)) % n) + n) % n]);
    }
    out.push(out[0]);
    return out;
  };
  return mask.parts.map((rings) => rings.map(rebuild));
}

export function colourOf(id) {
  return ZONE_COLOURS[id] ?? '#888888';
}

/** SPEC §6.1: assert nothing wraps the antimeridian and everything sits inside the model bbox. */
export function checkExtent() {
  const problems = [];
  for (const z of zones) {
    const geoms = [z.horizontal, z.contestedExtent].filter(Boolean);
    for (const g of geoms) {
      for (const part of partsOf(g)) {
        for (const ring of part) {
          for (const [lon, lat] of ring) {
            if (lon < MODEL_BBOX.west || lon > MODEL_BBOX.east || lat < MODEL_BBOX.south || lat > MODEL_BBOX.north) {
              problems.push(`${z.id}: vertex ${lon},${lat} outside model bbox`);
              break;
            }
          }
        }
      }
    }
  }
  if (problems.length) throw new Error(problems.slice(0, 5).join('\n'));
  return true;
}
