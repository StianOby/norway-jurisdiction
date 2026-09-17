// Panels, toggles, slider, share (SPEC §7). Three panels: the main panel (exaggeration, strata,
// zones, preset views), the column panel (result of a column query) and the section panel
// (cross-section canvas). On narrow screens the column and section panels share one bottom sheet,
// at most ~40 % of the viewport, and opening either collapses the main panel.
import { EXAGGERATION, VIEWS } from './config.js';
import { t, setLanguage, language } from './i18n.js';
import { zones, colourOf } from './zones.js';
import { renderStack } from './columnQuery.js';

const STRATA = ['airspace', 'watercolumn', 'seabed', 'subsoil'];
const NARROW = window.matchMedia('(max-width: 600px)');

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
  const ui = {};
  const notify = () => callbacks.changed?.();

  // ---- attribution (also Cesium's credit container, so OSM/Cesium credits land in the same line)
  const attribution = el('div', { id: 'attribution', role: 'contentinfo' });
  const attributionText = el('span', { class: 'attribution-text' });
  const credits = el('span', { class: 'attribution-credits' });
  attribution.append(attributionText, credits);
  attribution.addEventListener('click', (e) => { if (!e.target.closest('a')) attribution.classList.toggle('expanded'); });

  // ---- main panel
  const panel = el('div', { id: 'panel', role: 'region' });
  const toggleBtn = el('button', { id: 'panel-toggle', type: 'button', 'aria-controls': 'panel', 'aria-expanded': 'true' });
  const setPanelOpen = (open) => {
    panel.classList.toggle('collapsed', !open);
    toggleBtn.setAttribute('aria-expanded', String(open));
  };
  toggleBtn.addEventListener('click', () => {
    const open = panel.classList.contains('collapsed');
    setPanelOpen(open);
    if (open && NARROW.matches) { columnOpen = false; sectionOpen = false; applySheets(); }
    notify();
  });

  const title = el('h1');
  const subtitle = el('p', { class: 'subtitle' });
  const langBtn = el('button', { type: 'button', class: 'lang' });
  const homeBtn = el('button', { type: 'button', class: 'home', onclick: () => callbacks.home() });
  const shareBtn = el('button', { type: 'button', class: 'share' });
  shareBtn.addEventListener('click', async () => {
    const url = callbacks.shareUrl();
    try {
      await navigator.clipboard.writeText(url);
      shareBtn.textContent = t('shareCopied');
      setTimeout(() => { shareBtn.textContent = t('share'); }, 1800);
    } catch {
      window.prompt(t('share'), url); // clipboard blocked (e.g. some iframes): let the user copy by hand
    }
  });
  const header = el('div', { class: 'panel-header' }, title, el('div', { class: 'buttons' }, homeBtn, langBtn));
  const scope = el('p', { class: 'scope' });
  const columnHint = el('p', { class: 'hint' });

  // preset views + section + share
  const viewsTitle = el('h2');
  const viewButtons = new Map();
  const viewList = el('div', { class: 'views' });
  for (const id of Object.keys(VIEWS)) {
    const b = el('button', { type: 'button', class: 'view', onclick: () => callbacks.view(id) });
    viewButtons.set(id, b);
    viewList.append(b);
  }
  const sectionBtn = el('button', { type: 'button', class: 'view section-open', onclick: () => { openSection(); callbacks.sectionOpened?.(); } });
  const actions = el('div', { class: 'views actions' }, sectionBtn, shareBtn);
  const viewsSection = el('section', {}, viewsTitle, viewList, actions);

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
    readout.textContent = factor === 1 ? `1× (${t('trueScale')})` : `${factor}× · ${t('airspaceTrueScale')}`;
    for (const b of detents.children) b.classList.toggle('active', Number.parseInt(b.textContent, 10) === factor);
  };
  const onSlide = (immediate) => {
    factor = snap(toFactor(Number(slider.value)));
    showReadout();
    clearTimeout(timer);
    timer = setTimeout(() => { callbacks.exaggeration(factor); notify(); }, immediate ? 0 : EXAGGERATION.debounceMs);
  };
  slider.addEventListener('input', () => onSlide(false));
  slider.addEventListener('change', () => onSlide(true));
  const exSection = el('section', { class: 'exaggeration' }, el('div', { class: 'row' }, exLabel, readout), slider, detents);

  // strata toggles
  const strataTitle = el('h2');
  const strataList = el('div', { class: 'toggles' });
  const strataLabels = {};
  const strataBoxes = {};
  for (const s of STRATA) {
    const cb = el('input', { type: 'checkbox', id: `stratum-${s}`, checked: '' });
    cb.addEventListener('change', () => { callbacks.stratum(s, cb.checked); notify(); });
    const lab = el('label', { for: `stratum-${s}`, class: `stratum ${s}` }, cb, el('span'));
    strataLabels[s] = lab.lastChild;
    strataBoxes[s] = cb;
    strataList.append(lab);
  }
  const strataSection = el('section', {}, strataTitle, strataList);

  // zone toggles
  const zonesTitle = el('h2');
  const zoneList = el('div', { class: 'toggles zones' });
  const zoneLabels = new Map();
  const zoneBoxes = new Map();
  for (const z of zones) {
    const modelled = Boolean(z.horizontal || z.derivedFrom);
    const cb = el('input', { type: 'checkbox', id: `zone-${z.id}` });
    if (modelled) cb.checked = true; else cb.disabled = true;
    cb.addEventListener('change', () => { callbacks.zone(z.id, cb.checked); notify(); });
    const swatch = el('span', { class: `swatch${z.contested ? ' hatched' : ''}`, style: `--c:${colourOf(z.id)}` });
    const name = el('span', { class: 'name' });
    const note = el('span', { class: 'note' });
    const lab = el('label', { for: `zone-${z.id}`, class: `zone${modelled ? '' : ' disabled'}` }, cb, swatch, name, note);
    zoneLabels.set(z.id, { name, note, modelled, zone: z });
    zoneBoxes.set(z.id, cb);
    zoneList.append(lab);
  }
  const legend = el('p', { class: 'legend' });
  const zonesSection = el('section', {}, zonesTitle, zoneList, legend);

  const seabedNote = el('p', { class: 'note-block' });

  panel.append(header, subtitle, scope, columnHint, viewsSection, exSection, strataSection, zonesSection, seabedNote);

  let sectionOpen = false;
  let columnOpen = false;

  // ---- column panel (SPEC §7 column query)
  const columnPanel = el('div', { id: 'column-panel', class: 'sheet hidden', role: 'region' });
  const columnTitle = el('h2');
  const columnClose = el('button', { type: 'button', class: 'close', onclick: () => { closeColumn(); callbacks.columnClosed?.(); } }, '×');
  const columnBody = el('div', { class: 'sheet-body' });
  columnPanel.append(el('div', { class: 'sheet-header' }, columnTitle, columnClose), columnBody);
  let stack = null;

  // ---- section panel (SPEC §7 cross-section)
  const sectionPanel = el('div', { id: 'section-panel', class: 'sheet hidden', role: 'region' });
  const sectionTitle = el('h2');
  const sectionClose = el('button', { type: 'button', class: 'close', onclick: () => { closeSection(); callbacks.sectionClosed?.(); } }, '×');
  const sectionPresets = el('div', { class: 'views' });
  const presetSelect = el('select', { class: 'view preset-select' });
  const presetOptions = new Map();
  const customOption = el('option', { value: '' });
  presetSelect.append(customOption);
  for (const [id, v] of Object.entries(VIEWS)) {
    if (!v.transect) continue;
    const o = el('option', { value: id });
    presetOptions.set(id, o);
    presetSelect.append(o);
  }
  presetSelect.addEventListener('change', () => { if (presetSelect.value) callbacks.sectionPreset(presetSelect.value); });
  const pickLong = el('span', { class: 'long' });
  const pickShort = el('span', { class: 'short' });
  const pickBtn = el('button', { type: 'button', class: 'view pick', onclick: () => callbacks.sectionPick() }, pickLong, pickShort);
  sectionPresets.append(presetSelect, pickBtn);
  const sectionStatus = el('p', { class: 'status' });
  const sectionCaption = el('span', { class: 'caption' });
  const canvasBox = el('div', { class: 'canvas-box' });
  const canvas = el('canvas', { class: 'section-canvas' });
  canvasBox.append(canvas);
  const sectionNote = el('span', { class: 'note-block' });
  sectionPanel.append(
    el('div', { class: 'sheet-header' }, sectionTitle, sectionPresets, sectionClose),
    el('div', { class: 'sheet-body' }, sectionStatus, canvasBox, el('p', { class: 'footer' }, sectionCaption, ' ', sectionNote)),
  );

  root.append(toggleBtn, panel, columnPanel, sectionPanel, attribution);
  // the sheets sit above the attribution line, whatever its wrapped height (SPEC §7: persistent)
  new ResizeObserver(() => root.style.setProperty('--attr-h', `${attribution.offsetHeight}px`)).observe(attribution);

  // On narrow screens only one sheet is visible and it replaces the main panel (SPEC §7 budget).
  function applySheets() {
    const narrow = NARROW.matches;
    const showColumn = columnOpen && !(narrow && sectionOpen && activeSheet === 'section');
    const showSection = sectionOpen && !(narrow && columnOpen && activeSheet === 'column');
    columnPanel.classList.toggle('hidden', !showColumn);
    sectionPanel.classList.toggle('hidden', !showSection);
    root.classList.toggle('section-open', showSection);
    if (narrow && (showColumn || showSection)) setPanelOpen(false);
  }
  let activeSheet = null; // the sheet opened last: the one shown on narrow screens
  function openColumn() { columnOpen = true; activeSheet = 'column'; applySheets(); }
  function openSection() { sectionOpen = true; activeSheet = 'section'; applySheets(); }
  function closeColumn() { columnOpen = false; activeSheet = sectionOpen ? 'section' : null; applySheets(); }
  function closeSection() { sectionOpen = false; activeSheet = columnOpen ? 'column' : null; applySheets(); }
  NARROW.addEventListener('change', applySheets);

  if (NARROW.matches) setPanelOpen(false); // collapsed by default on phones

  function applyLanguage() {
    const lang = language();
    title.textContent = t('title');
    subtitle.textContent = t('subtitle');
    scope.textContent = t('scope');
    columnHint.textContent = t('columnHint');
    viewsTitle.textContent = t('views');
    for (const [id, b] of viewButtons) b.textContent = t(`view-${id}`);
    for (const [id, o] of presetOptions) o.textContent = t(`view-${id}`);
    customOption.textContent = t('sectionCustom');
    sectionBtn.textContent = t('sectionTitle');
    shareBtn.textContent = t('share');
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
    columnTitle.textContent = t('column');
    columnClose.setAttribute('aria-label', t('close'));
    columnClose.title = t('close');
    sectionTitle.textContent = t('sectionTitle');
    sectionClose.setAttribute('aria-label', t('close'));
    sectionClose.title = t('close');
    pickLong.textContent = t('sectionPick');
    pickShort.textContent = t('sectionPickShort');
    sectionNote.textContent = t('sectionNote');
    if (stack) renderStack(columnBody, stack, lang, colourOf); else columnBody.replaceChildren(el('p', { class: 'empty' }, t('columnEmpty')));
    showReadout();
    callbacks.language?.(lang);
  }
  langBtn.addEventListener('click', () => {
    setLanguage(language() === 'no' ? 'en' : 'no');
    applyLanguage();
    notify();
  });
  applyLanguage();

  ui.creditContainer = credits;
  ui.exaggeration = () => factor;
  ui.setExaggeration = (f) => { factor = snap(f); slider.value = String(toPos(factor)); showReadout(); };
  ui.applyLanguage = applyLanguage;
  ui.setLanguage = (lang) => { setLanguage(lang); applyLanguage(); };
  ui.setStratum = (s, on) => { strataBoxes[s].checked = on; };
  ui.setZone = (id, on) => { const cb = zoneBoxes.get(id); if (cb && !cb.disabled) cb.checked = on; };
  ui.hidden = () => ({
    strata: STRATA.filter((s) => !strataBoxes[s].checked),
    zones: [...zoneBoxes].filter(([, cb]) => !cb.disabled && !cb.checked).map(([id]) => id),
  });
  ui.setPanelOpen = setPanelOpen;
  ui.isPanelOpen = () => !panel.classList.contains('collapsed');
  ui.showColumn = (s) => { stack = s; renderStack(columnBody, s, language(), colourOf); columnBody.scrollTop = 0; openColumn(); };
  ui.clearColumn = () => { stack = null; closeColumn(); applyLanguage(); };
  ui.isColumnOpen = () => columnOpen;
  ui.openSection = openSection;
  ui.closeSection = closeSection;
  ui.isSectionOpen = () => sectionOpen;
  ui.sectionCanvas = canvas;
  ui.setSectionStatus = (text) => { sectionStatus.textContent = text || t('sectionHint'); sectionStatus.classList.toggle('muted', !text); };
  ui.setSectionCaption = (text) => { sectionCaption.textContent = text; };
  ui.setActiveView = (id) => { for (const [k, b] of viewButtons) b.classList.toggle('active', k === id); presetSelect.value = presetOptions.has(id) ? id : ''; };
  ui.setSectionStatus('');
  return ui;
}
