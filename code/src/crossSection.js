// Cross-section (SPEC §7): a 2D slice along a transect, showing the stacked columns — airspace,
// water column, seabed and subsoil — and which regime occupies each stratum where. It samples the
// transect with the same point-in-polygon lookup as the column query and draws on a canvas.
//
// Scale: the water column and the seabed profile are drawn at the model's vertical exaggeration
// with the horizontal scale of the distance axis (capped to what fits, and then labelled so). The
// airspace (0–100 km, upper limit undefined in law) would dwarf the rest at any useful
// exaggeration, so it is a fixed band with a scale break, labelled as not to scale; the subsoil
// has no fixed lower limit (SPEC §5.2) and is a fixed band that fades out, with no floor drawn.
import { SECTION, AIRSPACE, STRATA_ORDER } from './config.js';
import { stackAt } from './columnQuery.js';
import { t } from './i18n.js';

const R_EARTH_KM = 6371.0088;

function haversineKm(a, b) {
  const rad = Math.PI / 180;
  const dLat = (b.lat - a.lat) * rad;
  const dLon = (b.lon - a.lon) * rad;
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLon / 2) ** 2;
  return 2 * R_EARTH_KM * Math.asin(Math.min(1, Math.sqrt(s)));
}

function niceStep(span, target) {
  const raw = span / target;
  const mag = 10 ** Math.floor(Math.log10(raw));
  for (const m of [1, 2, 5, 10]) if (m * mag >= raw) return m * mag;
  return 10 * mag;
}

/** Sample the transect: [{ lon, lat, km, seabed, zones: { stratum: [zone] } }]. */
export function sampleTransect(a, b, n = SECTION.samples) {
  const out = [];
  let km = 0;
  let prev = null;
  for (let i = 0; i <= n; i++) {
    const f = i / n;
    const p = { lon: a.lon + (b.lon - a.lon) * f, lat: a.lat + (b.lat - a.lat) * f };
    if (prev) km += haversineKm(prev, p);
    const stack = stackAt(p.lon, p.lat);
    const zones = {};
    for (const { stratum, zones: zs } of stack.strata) zones[stratum] = zs;
    out.push({ lon: p.lon, lat: p.lat, km, seabed: stack.seabed, zones, marked: stack.marked, inside: stack.inside });
    prev = p;
  }
  return out;
}

// Consecutive samples with the same zone list in a stratum form a run: [{ from, to, zones }].
function runs(samples, stratum) {
  const result = [];
  let cur = null;
  samples.forEach((s, i) => {
    const key = s.zones[stratum].map((z) => (s.marked.has(z.id) ? `${z.id}*` : z.id)).join('|');
    if (cur && cur.key === key) cur.to = i;
    else { cur = { key, from: i, to: i, zones: s.zones[stratum], marked: s.marked }; result.push(cur); }
  });
  return result;
}

export class CrossSection {
  /**
   * @param canvas   the <canvas> to draw on (sized to its CSS box; hi-DPI aware)
   * @param options  { colourOf(id) → CSS colour, onPick({lon, lat}) }
   */
  constructor(canvas, options) {
    this.canvas = canvas;
    this.colourOf = options.colourOf;
    this.onPick = options.onPick;
    this.samples = null;
    this.transect = null;
    this.exaggeration = 1;
    this.cursorKm = null;
    this.layout = null;
    canvas.addEventListener('click', (e) => this.handleClick(e));
    this.observer = new ResizeObserver(() => this.draw());
    this.observer.observe(canvas.parentElement ?? canvas);
  }

  setTransect(a, b) {
    this.transect = a && b ? [a, b] : null;
    this.samples = this.transect ? sampleTransect(a, b) : null;
    this.cursorKm = null;
    this.draw();
  }

  setExaggeration(f) { this.exaggeration = f; this.draw(); }

  /** True when no sample of the transect lies in any modelled zone. */
  isEmpty() {
    return !this.samples || this.samples.every((s) => STRATA_ORDER.every((st) => s.zones[st].length === 0));
  }

  /** Highlight the column at a lon/lat if it lies (nearly) on the transect. */
  setCursor(point) {
    this.cursorKm = null;
    if (point && this.samples) {
      let best = null;
      for (const s of this.samples) {
        const d = haversineKm(s, point);
        if (best === null || d < best.d) best = { d, km: s.km };
      }
      const step = this.samples[this.samples.length - 1].km / this.samples.length;
      if (best && best.d < 3 * step) this.cursorKm = best.km;
    }
    this.draw();
  }

  handleClick(e) {
    if (!this.layout || !this.samples) return;
    const rect = this.canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const { x0, kmToPx, totalKm } = this.layout;
    const km = (x - x0) / kmToPx;
    if (km < 0 || km > totalKm) return;
    const i = Math.round((km / totalKm) * (this.samples.length - 1));
    const s = this.samples[i];
    this.cursorKm = s.km;
    this.draw();
    this.onPick?.({ lon: s.lon, lat: s.lat });
  }

  // -------------------------------------------------------------------------------------------

  draw() {
    const canvas = this.canvas;
    const box = (canvas.parentElement ?? canvas).getBoundingClientRect();
    const cssW = Math.max(200, Math.floor(box.width));
    if (!this.samples) { this.layout = null; canvas.width = 0; canvas.height = 0; canvas.style.height = '0px'; return; }

    const M = SECTION.margin;
    const plotW = cssW - M.left - M.right;
    const cssH = Math.max(SECTION.minHeight, Math.floor(box.height));
    const plotH = cssH - M.top - M.bottom;
    const S = this.samples;
    const totalKm = S[S.length - 1].km;
    const deepest = Math.min(...S.map((s) => s.seabed)); // negative metres
    const kmToPx = plotW / totalKm;
    // The water column is drawn at the slider's exaggeration unless that would not fit between the
    // airspace and subsoil bands; then the largest factor that fits is used and the readout says so.
    const waterH = plotH * (1 - SECTION.airspaceShare - SECTION.subsoilShare);
    const fFit = waterH / ((-deepest / 1000) * kmToPx);
    const f = Math.min(this.exaggeration, fFit);
    const fitted = f < this.exaggeration;
    const seaH = (-deepest / 1000) * f * kmToPx;
    const subH = plotH * SECTION.subsoilShare;
    const airH = plotH - seaH - subH; // at least airspaceShare of the plot
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(cssW * dpr);
    canvas.height = Math.round(cssH * dpr);
    canvas.style.height = `${cssH}px`;
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const x0 = M.left;
    const ySurface = M.top + airH;
    const mToPx = kmToPx * f / 1000; // exaggerated metres → px
    const X = (km) => x0 + km * kmToPx;
    const Y = (m) => ySurface - m * mToPx; // m negative below the surface
    const yFloor = M.top + plotH; // bottom of the subsoil band (drawn open: it fades out before this)
    this.layout = { x0, kmToPx, totalKm, ySurface, mToPx };

    const style = getComputedStyle(canvas);
    const fg = style.getPropertyValue('--section-fg').trim() || '#eef2f6';
    const muted = style.getPropertyValue('--section-muted').trim() || '#b7c2cc';
    ctx.clearRect(0, 0, cssW, cssH);
    ctx.font = '12px system-ui, sans-serif';
    ctx.textBaseline = 'middle';

    // ---- strata, per run
    const hatchPattern = this.hatchPattern(ctx, fg);
    for (const stratum of STRATA_ORDER) {
      for (const run of runs(S, stratum)) {
        if (!run.zones.length) continue;
        const k = run.zones.length;
        const xa = X(S[run.from].km) - 0.5;
        const xb = X(S[run.to].km) + 0.5;
        run.zones.forEach((z, j) => {
          const colour = this.colourOf(z.id);
          const hatched = z.contested || run.marked.has(z.id); // neutral marker, as in 3D (SPEC §1)
          ctx.beginPath();
          if (stratum === 'airspace') {
            // fixed band; fade towards the top (upper limit undefined)
            const yTop = M.top, yBot = ySurface;
            const g = ctx.createLinearGradient(0, yTop, 0, yBot);
            g.addColorStop(0, 'rgba(0,0,0,0)');
            g.addColorStop(1, colour);
            ctx.fillStyle = g;
            ctx.globalAlpha = 0.45;
            ctx.rect(xa, yTop, xb - xa, yBot - yTop);
            ctx.fill();
          } else if (stratum === 'watercolumn') {
            // between the surface and the seabed profile; overlapping regimes share it as stripes
            const t0 = j / k, t1 = (j + 1) / k;
            for (let i = run.from; i <= run.to; i++) ctx.lineTo(X(S[i].km), ySurface + (Y(S[i].seabed) - ySurface) * t0);
            for (let i = run.to; i >= run.from; i--) ctx.lineTo(X(S[i].km), ySurface + (Y(S[i].seabed) - ySurface) * t1);
            ctx.closePath();
            ctx.fillStyle = colour;
            ctx.globalAlpha = 0.75;
            ctx.fill();
            if (hatched) { ctx.fillStyle = hatchPattern; ctx.globalAlpha = 1; ctx.fill(); }
          } else if (stratum === 'seabed') {
            const band = SECTION.seabedBand;
            const y0 = -band / 2 + (j * band) / k, y1 = -band / 2 + ((j + 1) * band) / k;
            for (let i = run.from; i <= run.to; i++) ctx.lineTo(X(S[i].km), Y(S[i].seabed) + y0);
            for (let i = run.to; i >= run.from; i--) ctx.lineTo(X(S[i].km), Y(S[i].seabed) + y1);
            ctx.closePath();
            ctx.fillStyle = colour;
            ctx.globalAlpha = 1;
            ctx.fill();
            if (hatched) { ctx.fillStyle = hatchPattern; ctx.fill(); }
          } else { // subsoil: bounded-but-open — a band below the seabed that fades out; no floor is drawn
            const yA = Y(deepest) + SECTION.seabedBand, yB = yFloor;
            const g = ctx.createLinearGradient(0, yA, 0, yB);
            g.addColorStop(0, colour);
            g.addColorStop(0.45, colour);
            g.addColorStop(1, 'rgba(0,0,0,0)');
            const w = (xb - xa) / k;
            for (let i = run.from; i <= run.to; i++) ctx.lineTo(X(S[i].km), Y(S[i].seabed) + SECTION.seabedBand / 2);
            ctx.lineTo(X(S[run.to].km), yFloor);
            ctx.lineTo(X(S[run.from].km), yFloor);
            ctx.closePath();
            ctx.save();
            ctx.clip();
            ctx.fillStyle = g;
            ctx.globalAlpha = 0.6;
            ctx.fillRect(xa + j * w, M.top, w, cssH);
            if (hatched) { ctx.fillStyle = hatchPattern; ctx.fillRect(xa + j * w, M.top, w, cssH); }
            ctx.restore();
          }
          ctx.globalAlpha = 1;
        });
      }
    }

    // ---- surface, seabed profile, scale break
    ctx.globalAlpha = 1;
    ctx.strokeStyle = fg;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(X(0), ySurface);
    ctx.lineTo(X(totalKm), ySurface);
    ctx.stroke();
    ctx.strokeStyle = 'rgba(0,0,0,0.6)';
    ctx.beginPath();
    for (let i = 0; i < S.length; i++) ctx.lineTo(X(S[i].km), Y(S[i].seabed));
    ctx.stroke();
    const yBreak = M.top + airH * 0.32;
    ctx.strokeStyle = muted;
    ctx.setLineDash([]);
    ctx.beginPath();
    for (let x = x0, up = false; x <= X(totalKm); x += 6, up = !up) ctx.lineTo(x, yBreak + (up ? -3 : 3));
    ctx.stroke();

    // ---- labels on the runs (only where they fit)
    ctx.fillStyle = fg;
    ctx.textAlign = 'center';
    const label = (text, xc, yc, maxW) => {
      if (ctx.measureText(text).width + 8 > maxW) return;
      ctx.fillText(text, xc, yc);
    };
    const lang = document.documentElement.lang === 'en' ? 'en' : 'no';
    for (const stratum of ['airspace', 'watercolumn', 'subsoil']) {
      for (const run of runs(S, stratum)) {
        const k = run.zones.length;
        if (!k) continue;
        const xa = X(S[run.from].km), xb = X(S[run.to].km);
        const xc = (xa + xb) / 2;
        const mid = Math.round((run.from + run.to) / 2);
        run.zones.forEach((z, j) => {
          const name = z.legal[lang].name;
          let yc;
          if (stratum === 'airspace') yc = yBreak + ((ySurface - yBreak) * (j + 0.5)) / k;
          else if (stratum === 'watercolumn') {
            const ySb = Y(S[mid].seabed);
            if (ySb - ySurface < 14 * k) return; // too thin to label (true scale)
            yc = ySurface + ((ySb - ySurface) * (j + 0.5)) / k;
          } else {
            const ySb = Y(S[mid].seabed);
            const yEnd = ySb + (yFloor - ySb) * 0.6;
            if (yEnd - ySb < 14 * k) return;
            yc = ySb + ((yEnd - ySb) * (j + 0.5)) / k;
          }
          label(name, xc, yc, xb - xa);
        });
      }
    }

    // ---- axes
    ctx.fillStyle = muted;
    ctx.strokeStyle = muted;
    ctx.textAlign = 'center';
    const yAxis = M.top + plotH;
    ctx.beginPath();
    ctx.moveTo(X(0), yAxis + 2);
    ctx.lineTo(X(totalKm), yAxis + 2);
    ctx.stroke();
    const step = niceStep(totalKm, Math.max(3, Math.floor((totalKm * kmToPx) / 80)));
    for (let km = 0; km <= totalKm + 1e-6; km += step) {
      ctx.beginPath();
      ctx.moveTo(X(km), yAxis + 2);
      ctx.lineTo(X(km), yAxis + 6);
      ctx.stroke();
      ctx.fillText(String(Math.round(km)), X(km), yAxis + 15);
    }
    ctx.fillText(t('sectionAxisKm'), X(totalKm / 2), yAxis + 28);
    // depth ticks (exaggerated metres) down to the deepest seabed
    ctx.textAlign = 'right';
    const dStep = niceStep(-deepest, Math.max(2, Math.floor((Y(deepest) - ySurface) / 28)));
    for (let m = 0; m <= -deepest + 1e-6; m += dStep) {
      const y = Y(-m);
      ctx.beginPath();
      ctx.moveTo(x0 - 6, y);
      ctx.lineTo(x0 - 2, y);
      ctx.stroke();
      ctx.fillText(m === 0 ? '0 m' : `−${Math.round(m)}`, x0 - 8, y);
    }
    ctx.textAlign = 'left';
    ctx.fillText(`${t('airspace')} 0–${AIRSPACE.top / 1000} km · ${t('notToScale')}`, x0 + 4, M.top + 9);
    ctx.textAlign = 'right';
    ctx.fillText(fitted ? `${f.toFixed(f < 10 ? 1 : 0)}× (${t('sectionFitted')})` : `${f}×`, x0 - 8, ySurface - 14);
    ctx.textAlign = 'center';
    ctx.fillText('A', x0 - 20, ySurface);
    ctx.fillText('B', X(totalKm) + 8, ySurface);

    // ---- cursor
    if (this.cursorKm !== null) {
      const x = X(this.cursorKm);
      ctx.strokeStyle = fg;
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      ctx.moveTo(x, M.top);
      ctx.lineTo(x, yAxis);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = fg;
      ctx.beginPath();
      ctx.moveTo(x - 5, M.top - 8);
      ctx.lineTo(x + 5, M.top - 8);
      ctx.lineTo(x, M.top - 1);
      ctx.closePath();
      ctx.fill();
    }
  }

  hatchPattern(ctx, colour) {
    if (this._hatch && this._hatchColour === colour) return this._hatch;
    const p = SECTION.hatch.period;
    const c = document.createElement('canvas');
    c.width = c.height = p;
    const g = c.getContext('2d');
    g.strokeStyle = colour;
    g.globalAlpha = 0.7;
    g.lineWidth = SECTION.hatch.width;
    g.beginPath();
    g.moveTo(-p / 2, p * 1.5);
    g.lineTo(p * 1.5, -p / 2);
    g.moveTo(-p / 2, p / 2);
    g.lineTo(p / 2, -p / 2);
    g.moveTo(p / 2, p * 1.5);
    g.lineTo(p * 1.5, p / 2);
    g.stroke();
    this._hatch = ctx.createPattern(c, 'repeat');
    this._hatchColour = colour;
    return this._hatch;
  }
}
