// Extrusion + exaggeration (SPEC §5). Every zone/stratum pair becomes one translucent volume:
// a stack of "rows" (the polygon mesh lifted to a height that may vary per vertex, e.g. the
// schematic seabed), joined by walls along the polygon boundary. Nominal heights are kept per
// vertex, so changing the exaggeration is a cheap position recompute + primitive swap
// (Cesium's Scene.verticalExaggeration does not apply to primitives — SPEC §5.1).
//
// Cesium is the CDN global (see index.html / vite.config.js), not an import.
import { AIRSPACE, SUBSOIL, MESH, STRATUM_ALPHA, HATCH, SEABED_CLEARANCE } from './config.js';
import { seabedDepth } from './seabed.js';
import { zones, footprint, colourOf } from './zones.js';

const Cesium = globalThis.Cesium;
const RAD = Math.PI / 180;

// ---------------------------------------------------------------------------------------------
// Mesh preparation: triangulate a polygon part (outer ring + holes) and subdivide until no edge
// exceeds MESH.maxEdgeDeg, so that per-vertex heights (the seabed) are followed.

function prepareMesh(rings) {
  const lon = [];
  const lat = [];
  const holes = [];
  for (const ring of rings) {
    const n = ring.length - 1; // GeoJSON rings repeat the first vertex; earcut must not see it
    if (holes.length || lon.length) holes.push(lon.length);
    for (let i = 0; i < n; i++) {
      lon.push(ring[i][0]);
      lat.push(ring[i][1]);
    }
  }
  // holes[] currently holds the start index of every ring but the first
  const latMid = lat.reduce((a, b) => a + b, 0) / lat.length;
  const cx = Math.cos(latMid * RAD);
  const positions2D = new Array(lon.length);
  for (let i = 0; i < lon.length; i++) positions2D[i] = new Cesium.Cartesian2(lon[i] * cx, lat[i]);
  let tris = Cesium.PolygonPipeline.triangulate(positions2D, holes);
  if (tris.length < 3) return null;

  const maxEdge = MESH.maxEdgeDeg;
  const maxEdge2 = maxEdge * maxEdge;
  const d2 = (a, b) => {
    const dx = (lon[a] - lon[b]) * cx;
    const dy = lat[a] - lat[b];
    return dx * dx + dy * dy;
  };
  for (let pass = 0; pass < 12; pass++) {
    const mid = new Map();
    const key = (a, b) => (a < b ? a * 4294967296 + b : b * 4294967296 + a);
    let created = 0;
    const midpoint = (a, b) => {
      const k = key(a, b);
      let m = mid.get(k);
      if (m === undefined) {
        m = lon.length;
        lon.push((lon[a] + lon[b]) / 2);
        lat.push((lat[a] + lat[b]) / 2);
        mid.set(k, m);
        created++;
      }
      return m;
    };
    for (let t = 0; t < tris.length; t += 3) {
      const a = tris[t], b = tris[t + 1], c = tris[t + 2];
      if (d2(a, b) > maxEdge2) midpoint(a, b);
      if (d2(b, c) > maxEdge2) midpoint(b, c);
      if (d2(c, a) > maxEdge2) midpoint(c, a);
    }
    if (!created) break;
    const next = [];
    for (let t = 0; t < tris.length; t += 3) {
      const a = tris[t], b = tris[t + 1], c = tris[t + 2];
      const ab = mid.get(key(a, b)), bc = mid.get(key(b, c)), ca = mid.get(key(c, a));
      const n = (ab !== undefined) + (bc !== undefined) + (ca !== undefined);
      if (n === 0) next.push(a, b, c);
      else if (n === 3) next.push(a, ab, ca, ab, b, bc, ca, bc, c, ab, bc, ca);
      else if (n === 1) {
        if (ab !== undefined) next.push(a, ab, c, ab, b, c);
        else if (bc !== undefined) next.push(a, b, bc, a, bc, c);
        else next.push(a, b, ca, ca, b, c);
      } else {
        // two edges split: the quad is cut along its shorter diagonal
        if (ca === undefined) { // ab, bc
          if (d2(a, bc) < d2(ab, c)) next.push(a, ab, bc, a, bc, c, ab, b, bc);
          else next.push(a, ab, c, ab, bc, c, ab, b, bc);
        } else if (ab === undefined) { // bc, ca
          if (d2(b, ca) < d2(a, bc)) next.push(a, b, ca, b, bc, ca, ca, bc, c);
          else next.push(a, b, bc, a, bc, ca, ca, bc, c);
        } else { // ab, ca
          if (d2(b, ca) < d2(ab, c)) next.push(a, ab, ca, ab, b, ca, ca, b, c);
          else next.push(a, ab, ca, ab, c, ca, ab, b, c);
        }
      }
    }
    tris = next;
  }
  // boundary edges = edges used by exactly one triangle (outer ring and holes alike)
  const count = new Map();
  const key = (a, b) => (a < b ? a * 4294967296 + b : b * 4294967296 + a);
  for (let t = 0; t < tris.length; t += 3) {
    const a = tris[t], b = tris[t + 1], c = tris[t + 2];
    for (const k of [key(a, b), key(b, c), key(c, a)]) count.set(k, (count.get(k) ?? 0) + 1);
  }
  const boundary = [];
  for (const [k, n] of count) {
    if (n === 1) boundary.push(Math.floor(k / 4294967296), k % 4294967296);
  }
  return {
    lon: Float64Array.from(lon),
    lat: Float64Array.from(lat),
    tris: Uint32Array.from(tris),
    boundary: Uint32Array.from(boundary),
  };
}

// ---------------------------------------------------------------------------------------------
// Volume assembly. rows: [{ h: (lon, lat) => metres, alpha, cap }], bottom to top or top to
// bottom — walls join consecutive rows. Returns typed arrays with nominal (1x) heights.

function hexToRgb(hex) {
  const v = parseInt(hex.slice(1), 16);
  return [(v >> 16) & 255, (v >> 8) & 255, v & 255];
}

function assemble(mesh, rows, rgb, hatch, wallAlphaFactor = 1.35) {
  const n = mesh.lon.length;
  const lon = [], lat = [], h = [], rgba = [], hatchA = [], idx = [];
  const push = (i, height, alpha) => {
    lon.push(mesh.lon[i]);
    lat.push(mesh.lat[i]);
    h.push(height);
    rgba.push(rgb[0], rgb[1], rgb[2], Math.round(255 * Math.min(1, alpha)));
    hatchA.push(hatch);
    return lon.length - 1;
  };
  // caps
  for (const row of rows) {
    if (!row.cap) continue;
    const base = lon.length;
    for (let i = 0; i < n; i++) push(i, row.h(mesh.lon[i], mesh.lat[i]), row.alpha);
    for (let t = 0; t < mesh.tris.length; t++) idx.push(base + mesh.tris[t]);
  }
  // walls: boundary vertices only, one copy per row
  if (rows.length > 1) {
    const bverts = Array.from(new Set(mesh.boundary));
    const local = new Map(bverts.map((v, k) => [v, k]));
    const rowBase = [];
    for (const row of rows) {
      rowBase.push(lon.length);
      for (const v of bverts) push(v, row.h(mesh.lon[v], mesh.lat[v]), row.alpha * wallAlphaFactor);
    }
    for (let r = 0; r + 1 < rows.length; r++) {
      const b0 = rowBase[r], b1 = rowBase[r + 1];
      for (let e = 0; e < mesh.boundary.length; e += 2) {
        const p = local.get(mesh.boundary[e]), q = local.get(mesh.boundary[e + 1]);
        idx.push(b0 + p, b0 + q, b1 + q, b0 + p, b1 + q, b1 + p);
      }
    }
  }
  return {
    lon: Float64Array.from(lon),
    lat: Float64Array.from(lat),
    h: Float32Array.from(h),
    rgba: Uint8Array.from(rgba),
    hatch: Float32Array.from(hatchA),
    indices: Uint32Array.from(idx),
  };
}

const seabed = (lon, lat) => seabedDepth(lon, lat);
const flat = (v) => () => v;

function rowsFor(stratum) {
  const a = STRATUM_ALPHA[stratum];
  switch (stratum) {
    case 'airspace':
      // No caps: the sea surface belongs to the water column below, and the upper limit is
      // undefined in law — the walls fade out over the top 20 km (SPEC §5.2).
      return [
        { h: flat(0), alpha: a, cap: false },
        { h: flat(AIRSPACE.fadeFrom), alpha: a, cap: false },
        { h: flat(AIRSPACE.top), alpha: 0, cap: false },
      ];
    case 'watercolumn':
      return [
        { h: flat(0), alpha: a, cap: true },
        { h: (lo, la) => seabed(lo, la) + SEABED_CLEARANCE, alpha: a, cap: true },
      ];
    case 'seabed':
      return [{ h: seabed, alpha: a, cap: true }];
    case 'subsoil':
      // Bounded-but-open: no floor is drawn; the slab fades out below SUBSOIL.fadeFrom.
      return [
        { h: (lo, la) => seabed(lo, la) - SEABED_CLEARANCE, alpha: a, cap: false },
        { h: (lo, la) => seabed(lo, la) - SUBSOIL.fadeFrom, alpha: a, cap: false },
        { h: (lo, la) => seabed(lo, la) - SUBSOIL.thickness, alpha: 0, cap: false },
      ];
    default:
      throw new Error(`unknown stratum ${stratum}`);
  }
}

// ---------------------------------------------------------------------------------------------
// Cesium side: one Primitive per volume, custom flat appearance with per-vertex colour and a
// screen-space hatch for contested markers (SPEC §1: visual only).

const VS = `
in vec3 position3DHigh;
in vec3 position3DLow;
in vec4 color;
in float hatch;
in float batchId; // added by Cesium's Primitive (batch table); must be declared even if unused
out vec4 v_color;
out float v_hatch;
void main() {
  vec4 p = czm_computePosition();
  v_color = color;
  v_hatch = hatch;
  gl_Position = czm_modelViewProjectionRelativeToEye * p;
}`;
const FS = `
in vec4 v_color;
in float v_hatch;
void main() {
  vec4 c = v_color;
  if (v_hatch > 0.5) {
    float on = step(mod(gl_FragCoord.x + gl_FragCoord.y, ${HATCH.period.toFixed(1)}), ${HATCH.width.toFixed(1)});
    if (v_hatch > 1.5) on = max(on, step(mod(gl_FragCoord.x - gl_FragCoord.y, ${HATCH.period.toFixed(1)}), ${HATCH.width.toFixed(1)}));
    c.a *= mix(0.3, 1.0, on);
  }
  out_FragColor = c;
}`;

function makeAppearance() {
  return new Cesium.Appearance({
    translucent: true,
    closed: false,
    renderState: Cesium.Appearance.getDefaultRenderState(true, false, { cull: { enabled: false } }),
    vertexShaderSource: VS,
    fragmentShaderSource: FS,
  });
}

const scratch = new Cesium.Cartesian3();

function makePrimitive(vol, exaggeration, appearance) {
  const n = vol.lon.length;
  const positions = new Float64Array(n * 3);
  for (let i = 0; i < n; i++) {
    Cesium.Cartesian3.fromRadians(vol.lon[i] * RAD, vol.lat[i] * RAD, vol.h[i] * exaggeration, Cesium.Ellipsoid.WGS84, scratch);
    positions[3 * i] = scratch.x;
    positions[3 * i + 1] = scratch.y;
    positions[3 * i + 2] = scratch.z;
  }
  const geometry = new Cesium.Geometry({
    attributes: {
      position: new Cesium.GeometryAttribute({ componentDatatype: Cesium.ComponentDatatype.DOUBLE, componentsPerAttribute: 3, values: positions }),
      color: new Cesium.GeometryAttribute({ componentDatatype: Cesium.ComponentDatatype.UNSIGNED_BYTE, componentsPerAttribute: 4, normalize: true, values: vol.rgba }),
      hatch: new Cesium.GeometryAttribute({ componentDatatype: Cesium.ComponentDatatype.FLOAT, componentsPerAttribute: 1, values: vol.hatch }),
    },
    indices: vol.indices,
    primitiveType: Cesium.PrimitiveType.TRIANGLES,
    boundingSphere: Cesium.BoundingSphere.fromVertices(positions),
  });
  return new Cesium.Primitive({
    geometryInstances: new Cesium.GeometryInstance({ geometry }),
    appearance,
    asynchronous: false,
    allowPicking: false,
    compressVertices: false,
    releaseGeometryInstances: true,
  });
}

// ---------------------------------------------------------------------------------------------

export class StrataModel {
  constructor(scene) {
    this.scene = scene;
    this.appearance = makeAppearance();
    this.volumes = []; // { zoneId, stratum, marker, vol, primitive }
    this.exaggeration = 1;
    this.hidden = { zones: new Set(), strata: new Set() };
    this.stats = { meshes: 0, vertices: 0, triangles: 0 };
  }

  /** Build every volume once (nominal heights). Heavy: call once at start-up. */
  build() {
    const meshCache = new Map();
    const meshesFor = (z) => {
      if (!meshCache.has(z.id)) meshCache.set(z.id, footprint(z).map(prepareMesh).filter(Boolean));
      return meshCache.get(z.id);
    };
    for (const z of zones) {
      const rgb = hexToRgb(colourOf(z.id));
      const hatch = z.contested ? 1 : 0;
      for (const mesh of meshesFor(z)) {
        for (const stratum of z.strata) {
          this.volumes.push({ zoneId: z.id, stratum, marker: false, vol: assemble(mesh, rowsFor(stratum), rgb, hatch) });
        }
      }
      // Contested-extent marker on the seabed (neutral hatching, no text) — data/PROVENANCE.md §15.
      for (const [geom, kind] of [[z.contestedExtent, 1]]) {
        if (!geom) continue;
        for (const rings of (geom.type === 'Polygon' ? [geom.coordinates] : geom.coordinates)) {
          const mesh = prepareMesh(rings);
          if (!mesh) continue;
          const rows = [{ h: (lo, la) => seabed(lo, la) + 2 * SEABED_CLEARANCE, alpha: 0.6, cap: true }];
          this.volumes.push({ zoneId: z.id, stratum: 'seabed', marker: true, vol: assemble(mesh, rows, rgb, kind) });
        }
      }
    }
    for (const v of this.volumes) {
      this.stats.vertices += v.vol.lon.length;
      this.stats.triangles += v.vol.indices.length / 3;
    }
    this.stats.meshes = this.volumes.length;
  }

  setExaggeration(factor) {
    this.exaggeration = factor;
    const t0 = performance.now();
    for (const v of this.volumes) {
      if (v.primitive) this.scene.primitives.remove(v.primitive);
      v.primitive = makePrimitive(v.vol, factor, this.appearance);
      v.primitive.show = this.isVisible(v);
      this.scene.primitives.add(v.primitive);
    }
    this.scene.requestRender();
    return performance.now() - t0;
  }

  isVisible(v) {
    return !this.hidden.zones.has(v.zoneId) && !this.hidden.strata.has(v.stratum);
  }

  setZoneVisible(zoneId, on) {
    if (on) this.hidden.zones.delete(zoneId); else this.hidden.zones.add(zoneId);
    this.applyVisibility();
  }

  setStratumVisible(stratum, on) {
    if (on) this.hidden.strata.delete(stratum); else this.hidden.strata.add(stratum);
    this.applyVisibility();
  }

  applyVisibility() {
    for (const v of this.volumes) if (v.primitive) v.primitive.show = this.isVisible(v);
    this.scene.requestRender();
  }
}
