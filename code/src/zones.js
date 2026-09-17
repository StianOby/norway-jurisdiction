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
 * The polygons a zone occupies. A zone with `derivedFrom` (airspace beyond the territorial sea)
 * has no geometry of its own: it is the union of its members, so their parts are returned.
 */
export function footprint(z) {
  if (z.derivedFrom) return z.derivedFrom.flatMap((id) => partsOf(byId.get(id).horizontal));
  return partsOf(z.horizontal);
}

export function colourOf(id) {
  return ZONE_COLOURS[id] ?? '#888888';
}

/** SPEC §6.1: assert nothing wraps the antimeridian and everything sits inside the model bbox. */
export function checkExtent() {
  const problems = [];
  for (const z of zones) {
    const geoms = [z.horizontal, z.contestedExtent, z.contestedExtentInterval].filter(Boolean);
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
