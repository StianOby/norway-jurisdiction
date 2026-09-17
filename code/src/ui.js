// Panels, toggles, slider (SPEC §7). Phase 2 scope: exaggeration slider with detents and
// readout, stratum and zone toggles, language toggle, scope note, persistent attribution.
// Column query, cross-section and URL state are Phase 4.
import { EXAGGERATION } from './config.js';
import { t, setLanguage, language } from './i18n.js';
import { zones, colourOf } from './zones.js';

const STRATA = ['airspace', 'watercolumn', 'seabed', 'subsoil'];

function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  }
  for (const c of children) e.append(c);
  return e;
}

// slider position 0..1000 <-> factor, logarithmic
const LOG_MIN = Math.log(EXAGGERATION.min);
const LOG_MAX = Math.log(EXAGGERATION.max);
const toFactor = (pos) => Math.exp(LOG_MIN + (LOG_MAX - LOG_MIN) * (pos / 1000));
const toPos = (f) => Math.round(1000 * (Math.log(f) - LOG_MIN) / (LOG_MAX - LOG_MIN));
function snap(f) {
  for (const d of EXAGGERATION.detents) {
    if (Math.abs(Math.log(f) - Math.log(d)) < EXAGGERATION.snapFraction * (LOG_MAX - LOG_MIN)) return d;
  }
  return Math.round(f);
}

export function buildUI(root, callbacks) {
  const ui = { lang: language() };

  // ---- attribution (also Cesium's credit container, so OSM/Cesium credits land in the same line)
  const attribution = el('div', { id: 'attribution', role: 'contentinfo' });
  const attributionText = el('span', { class: 'attribution-text' });
  const credits = el('span', { class: 'attribution-credits' });
  attribution.append(attributionText, credits);

  // ---- panel
  const panel = el('div', { id: 'panel', role: 'region' });
  const toggleBtn = el('button', { id: 'panel-toggle', type: 'button', 'aria-controls': 'panel', 'aria-expanded': 'true' });
  toggleBtn.addEventListener('click', () => {
    const open = panel.classList.toggle('collapsed') === false;
    toggleBtn.setAttribute('aria-expanded', String(open));
  });

  const title = el('h1');
  const subtitle = el('p', { class: 'subtitle' });
  const langBtn = el('button', { type: 'button', class: 'lang' });
  const homeBtn = el('button', { type: 'button', class: 'home' });
  homeBtn.addEventListener('click', () => callbacks.home());
  const header = el('div', { class: 'panel-header' }, title, el('div', { class: 'buttons' }, homeBtn, langBtn));
  const scope = el('p', { class: 'scope' });

  // exaggeration
  const exLabel = el('label', { for: 'exaggeration' });
  const readout = el('output', { for: 'exaggeration', class: 'readout' });
  const slider = el('input', { id: 'exaggeration', type: 'range', min: '0', max: '1000', step: '1', value: String(toPos(EXAGGERATION.initial)) });
  const detents = el('div', { class: 'detents' });
  for (const d of EXAGGERATION.detents) {
    const b = el('button', { type: 'button', class: 'detent', style: `left:${toPos(d) / 10}%` }, `${d}×`);
    b.addEventListener('click', () => { slider.value = String(toPos(d)); onSlide(true); });
    detents.append(b);
  }
  let timer = null;
  let factor = EXAGGERATION.initial;
  const showReadout = () => {
    readout.textContent = factor === 1 ? `1× (${t('trueScale')})` : `${factor}×`;
    for (const b of detents.children) b.classList.toggle('active', Number.parseInt(b.textContent, 10) === factor);
  };
  const onSlide = (immediate) => {
    factor = snap(toFactor(Number(slider.value)));
    showReadout();
    clearTimeout(timer);
    timer = setTimeout(() => callbacks.exaggeration(factor), immediate ? 0 : EXAGGERATION.debounceMs);
  };
  slider.addEventListener('input', () => onSlide(false));
  slider.addEventListener('change', () => onSlide(true));
  const exSection = el('section', { class: 'exaggeration' }, el('div', { class: 'row' }, exLabel, readout), slider, detents);

  // strata toggles
  const strataTitle = el('h2');
  const strataList = el('div', { class: 'toggles' });
  const strataLabels = {};
  for (const s of STRATA) {
    const cb = el('input', { type: 'checkbox', id: `stratum-${s}`, checked: '' });
    cb.addEventListener('change', () => callbacks.stratum(s, cb.checked));
    const lab = el('label', { for: `stratum-${s}`, class: `stratum ${s}` }, cb, el('span'));
    strataLabels[s] = lab.lastChild;
    strataList.append(lab);
  }
  const strataSection = el('section', {}, strataTitle, strataList);

  // zone toggles
  const zonesTitle = el('h2');
  const zoneList = el('div', { class: 'toggles zones' });
  const zoneLabels = new Map();
  for (const z of zones) {
    const modelled = Boolean(z.horizontal || z.derivedFrom);
    const cb = el('input', { type: 'checkbox', id: `zone-${z.id}` });
    if (modelled) cb.checked = true; else cb.disabled = true;
    cb.addEventListener('change', () => callbacks.zone(z.id, cb.checked));
    const swatch = el('span', { class: `swatch${z.contested ? ' hatched' : ''}`, style: `--c:${colourOf(z.id)}` });
    const name = el('span', { class: 'name' });
    const note = el('span', { class: 'note' });
    const lab = el('label', { for: `zone-${z.id}`, class: `zone${modelled ? '' : ' disabled'}` }, cb, swatch, name, note);
    zoneLabels.set(z.id, { name, note, modelled, zone: z });
    zoneList.append(lab);
  }
  const legend = el('p', { class: 'legend' });
  const zonesSection = el('section', {}, zonesTitle, zoneList, legend);

  const seabedNote = el('p', { class: 'note-block' });

  panel.append(header, subtitle, scope, exSection, strataSection, zonesSection, seabedNote);
  root.append(toggleBtn, panel, attribution);

  // collapse the panel by default on narrow screens (SPEC §7: ≤ ~40 % of a 375 px viewport)
  if (window.matchMedia('(max-width: 600px)').matches) {
    panel.classList.add('collapsed');
    toggleBtn.setAttribute('aria-expanded', 'false');
  }

  function applyLanguage() {
    const lang = language();
    title.textContent = t('title');
    subtitle.textContent = t('subtitle');
    scope.textContent = t('scope');
    exLabel.textContent = t('exaggeration');
    strataTitle.textContent = t('strata');
    zonesTitle.textContent = t('zones');
    for (const s of STRATA) strataLabels[s].textContent = t(s);
    for (const { name, note, modelled, zone } of zoneLabels.values()) {
      name.textContent = zone.legal[lang].name;
      note.textContent = modelled ? '' : ` (${t('notModelled')})`;
    }
    legend.textContent = t('contestedMarker');
    seabedNote.textContent = t('seabedNote');
    attributionText.textContent = t('attribution') + ' · ';
    langBtn.textContent = t('language');
    homeBtn.textContent = t('home');
    toggleBtn.textContent = t('panelToggle');
    toggleBtn.setAttribute('aria-label', t('panelToggle'));
    showReadout();
  }
  langBtn.addEventListener('click', () => {
    setLanguage(language() === 'no' ? 'en' : 'no');
    applyLanguage();
  });
  applyLanguage();

  ui.creditContainer = credits;
  ui.exaggeration = () => factor;
  ui.setExaggeration = (f) => { factor = snap(f); slider.value = String(toPos(factor)); showReadout(); };
  ui.applyLanguage = applyLanguage;
  return ui;
}
