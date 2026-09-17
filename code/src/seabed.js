// Schematic seabed (SPEC §1, §5.2): a class map derived from GEBCO 2020 (data/build/seabed.json,
// code/scripts/build_seabed.py) turned into a smooth depth field using the named levels in
// config.js. Illustrative, not survey data — the UI says so.
import seabedData from '../../data/build/seabed.json';
import { SEABED } from './config.js';

const { grid } = seabedData.meta;
const { nlat, nlon, lat0, dlat, lon0, dlon } = grid;

// Separable Gaussian, edge-clamped — identical to build_seabed.py::smooth.
function smooth(field, sigma) {
  const r = Math.max(1, Math.ceil(3 * sigma));
  const k = [];
  let ks = 0;
  for (let d = -r; d <= r; d++) {
    const v = Math.exp(-0.5 * (d / sigma) ** 2);
    k.push(v);
    ks += v;
  }
  for (let i = 0; i < k.length; i++) k[i] /= ks;
  const tmp = new Float32Array(nlat * nlon);
  const out = new Float32Array(nlat * nlon);
  for (let i = 0; i < nlat; i++) {
    for (let j = 0; j < nlon; j++) {
      let s = 0;
      for (let d = -r; d <= r; d++) s += k[d + r] * field[i * nlon + Math.min(nlon - 1, Math.max(0, j + d))];
      tmp[i * nlon + j] = s;
    }
  }
  for (let i = 0; i < nlat; i++) {
    for (let j = 0; j < nlon; j++) {
      let s = 0;
      for (let d = -r; d <= r; d++) s += k[d + r] * tmp[Math.min(nlat - 1, Math.max(0, i + d)) * nlon + j];
      out[i * nlon + j] = s;
    }
  }
  return out;
}

function buildField() {
  const levels = new Float32Array(nlat * nlon);
  const rows = seabedData.rows;
  for (let i = 0; i < nlat; i++) {
    const row = rows[i];
    for (let j = 0; j < nlon; j++) levels[i * nlon + j] = SEABED.levels[row[j]];
  }
  return smooth(levels, SEABED.smoothingSigmaCells);
}

const depthField = buildField();

/** Schematic seabed depth (m, negative) at a lon/lat in degrees; bilinear between cell centres. */
export function seabedDepth(lon, lat) {
  const fi = (lat - lat0) / dlat;
  const fj = (lon - lon0) / dlon;
  const i0 = Math.min(nlat - 2, Math.max(0, Math.floor(fi)));
  const j0 = Math.min(nlon - 2, Math.max(0, Math.floor(fj)));
  const ti = Math.min(1, Math.max(0, fi - i0));
  const tj = Math.min(1, Math.max(0, fj - j0));
  const a = depthField[i0 * nlon + j0];
  const b = depthField[i0 * nlon + j0 + 1];
  const c = depthField[(i0 + 1) * nlon + j0];
  const d = depthField[(i0 + 1) * nlon + j0 + 1];
  return (1 - ti) * ((1 - tj) * a + tj * b) + ti * ((1 - tj) * c + tj * d);
}

export const seabedMeta = seabedData.meta;
