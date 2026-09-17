// Viewer bootstrap and camera (SPEC §6): EllipsoidTerrainProvider + OpenStreetMap imagery, no
// Cesium ion token — deliberate, do not "improve" it. Cesium is the pinned CDN global.
// Wires the Phase 4 interaction: column query (click), cross-section, preset views, URL state.
import './styles.css';
import { CAMERA_HOME, GLOBE, MODEL_BBOX, OSM_TILES, EXAGGERATION, CESIUM_VERSION, VIEWS, STRATA_ORDER } from './config.js';
import { checkExtent, meta, colourOf } from './zones.js';
import { StrataModel } from './strata.js';
import { buildUI } from './ui.js';
import { stackAt, pickLonLat, Probe, fmtPoint } from './columnQuery.js';
import { CrossSection } from './crossSection.js';
import { readState, writeState, shareUrl } from './urlState.js';
import { t } from './i18n.js';

const Cesium = globalThis.Cesium;

function fail(message) {
  const box = document.createElement('div');
  box.id = 'fatal';
  box.textContent = message;
  document.body.append(box);
  throw new Error(message);
}

function main() {
  if (!Cesium) fail('CesiumJS did not load from the CDN.');
  if (Cesium.VERSION !== CESIUM_VERSION) console.warn(`Cesium ${Cesium.VERSION} loaded, config expects ${CESIUM_VERSION}`);
  checkExtent(); // SPEC §6.1 antimeridian assertion — throws if any polygon leaves the model bbox

  const initial = readState();
  let model = null;
  let probe = null;
  let section = null;
  let viewer = null;
  const state = { view: initial.view, q: initial.q, xs: initial.xs, picking: null }; // picking: null | 'A' | { a }

  // ---- URL state (SPEC §7): written after every change, read once at start-up
  function cameraState() {
    const c = viewer.camera;
    const carto = c.positionCartographic;
    return {
      lon: Cesium.Math.toDegrees(carto.longitude),
      lat: Cesium.Math.toDegrees(carto.latitude),
      height: carto.height,
      heading: Cesium.Math.toDegrees(c.heading),
      pitch: Cesium.Math.toDegrees(c.pitch),
    };
  }
  function currentState() {
    const hidden = ui.hidden();
    return {
      view: state.view,
      cam: cameraState(),
      ex: ui.exaggeration(),
      exDefault: EXAGGERATION.initial,
      hide: [...hidden.strata, ...hidden.zones],
      lang: document.documentElement.lang,
      q: ui.isColumnOpen() ? state.q : null,
      xs: ui.isSectionOpen() ? state.xs : null,
      panel: ui.isPanelOpen(),
    };
  }
  const changed = () => { if (viewer) writeState(currentState()); };

  // ---- column query
  function query(point) {
    state.q = point;
    probe.set(point, ui.exaggeration());
    ui.showColumn(stackAt(point.lon, point.lat));
    section?.setCursor(point);
    changed();
  }

  // ---- cross-section
  function setTransect(a, b, viewId = null) {
    state.xs = [a, b];
    state.view = viewId;
    ui.setActiveView(viewId);
    ui.openSection();
    section.setExaggeration(ui.exaggeration());
    section.setTransect(a, b);
    ui.setSectionCaption(`A ${fmtPoint(a)} → B ${fmtPoint(b)}`);
    ui.setSectionStatus(section.isEmpty() ? t('outsideModel') : '');
    drawTransectLine(a, b);
    if (state.q) section.setCursor(state.q);
    changed();
  }
  let transectEntity = null;
  function drawTransectLine(a, b) {
    if (transectEntity) viewer.entities.remove(transectEntity);
    transectEntity = null;
    if (!a || !b) { viewer.scene.requestRender(); return; }
    transectEntity = viewer.entities.add({
      polyline: {
        positions: Cesium.Cartesian3.fromDegreesArray([a.lon, a.lat, b.lon, b.lat]),
        width: 2,
        material: new Cesium.PolylineDashMaterialProperty({ color: Cesium.Color.WHITE, dashLength: 12 }),
        clampToGround: false,
        arcType: Cesium.ArcType.NONE,
      },
    });
    viewer.scene.requestRender();
  }
  function startPicking() {
    state.picking = 'A';
    ui.setSectionStatus(t('sectionPicking'));
  }

  // ---- preset views
  function flyTo(cam, duration = 1.2) {
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(cam.lon, cam.lat, cam.height),
      orientation: { heading: Cesium.Math.toRadians(cam.heading), pitch: Cesium.Math.toRadians(cam.pitch), roll: 0 },
      duration,
    });
  }
  function showView(id, duration) {
    const v = VIEWS[id];
    if (!v) return;
    flyTo(v.camera, duration);
    if (v.transect && ui.isSectionOpen()) setTransect({ lon: v.transect[0][0], lat: v.transect[0][1] }, { lon: v.transect[1][0], lat: v.transect[1][1] }, id);
    else { state.view = id; ui.setActiveView(id); changed(); }
  }

  const root = document.getElementById('ui');
  const ui = buildUI(root, {
    exaggeration: (f) => { model?.setExaggeration(f); probe?.setExaggeration(f); section?.setExaggeration(f); },
    stratum: (s, on) => model?.setStratumVisible(s, on),
    zone: (id, on) => model?.setZoneVisible(id, on),
    home: () => { state.view = null; ui.setActiveView(null); flyTo(CAMERA_HOME); },
    view: (id) => showView(id),
    shareUrl: () => shareUrl(currentState()),
    changed,
    language: () => { if (section) section.draw(); },
    sectionOpened: () => {
      if (state.xs) setTransect(state.xs[0], state.xs[1], state.view);
      else showView('mainland-section');
    },
    sectionClosed: () => { state.picking = null; drawTransectLine(null, null); changed(); },
    columnClosed: () => { probe.set(null); section?.setCursor(null); changed(); },
    sectionPreset: (id) => showView(id),
    sectionPick: startPicking,
  });
  if (initial.lang) ui.setLanguage(initial.lang);
  if (!initial.panel) ui.setPanelOpen(false);

  viewer = new Cesium.Viewer('cesiumContainer', {
    terrainProvider: new Cesium.EllipsoidTerrainProvider(),
    baseLayer: new Cesium.ImageryLayer(new Cesium.OpenStreetMapImageryProvider({ url: OSM_TILES })),
    creditContainer: ui.creditContainer,
    animation: false,
    timeline: false,
    geocoder: false,
    homeButton: false,
    sceneModePicker: false,
    baseLayerPicker: false,
    navigationHelpButton: false,
    infoBox: false,
    selectionIndicator: false,
    fullscreenButton: false,
    requestRenderMode: true,
    maximumRenderTimeChange: Infinity,
    scene3DOnly: true,
  });
  const { scene } = viewer;
  scene.globe.enableLighting = false;
  scene.skyAtmosphere.show = true;
  // See below the sea surface: translucent globe inside the model bbox, camera may go underground.
  scene.globe.translucency.enabled = true;
  scene.globe.translucency.frontFaceAlpha = GLOBE.frontFaceAlpha;
  scene.globe.translucency.backFaceAlpha = GLOBE.backFaceAlpha;
  if (GLOBE.translucentInsideBboxOnly) scene.globe.translucency.rectangle = Cesium.Rectangle.fromDegrees(MODEL_BBOX.west, MODEL_BBOX.south, MODEL_BBOX.east, MODEL_BBOX.north);
  scene.globe.undergroundColor = Cesium.Color.fromCssColorString(GLOBE.undergroundColor);
  scene.screenSpaceCameraController.enableCollisionDetection = false;

  // camera: URL > preset view > home
  if (initial.cam) {
    viewer.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(initial.cam.lon, initial.cam.lat, initial.cam.height),
      orientation: { heading: Cesium.Math.toRadians(initial.cam.heading), pitch: Cesium.Math.toRadians(initial.cam.pitch), roll: 0 },
    });
  } else if (initial.view && VIEWS[initial.view]) {
    flyTo(VIEWS[initial.view].camera, 0);
  } else {
    flyTo(CAMERA_HOME, 0);
  }
  viewer.camera.moveEnd.addEventListener(changed);

  model = new StrataModel(scene);
  const t0 = performance.now();
  model.build();
  const tBuild = performance.now() - t0;
  const ex = initial.ex !== null && initial.ex >= EXAGGERATION.min && initial.ex <= EXAGGERATION.max ? initial.ex : EXAGGERATION.initial;
  for (const h of initial.hide) {
    if (STRATA_ORDER.includes(h)) { model.hidden.strata.add(h); ui.setStratum(h, false); } else { model.hidden.zones.add(h); ui.setZone(h, false); }
  }
  ui.setExaggeration(ex);
  const tPrim = model.setExaggeration(ex);
  console.info(`zones.json ${meta.generated}: ${model.stats.meshes} volumes, ${model.stats.vertices} vertices, ${model.stats.triangles} triangles; meshing ${tBuild.toFixed(0)} ms, primitives ${tPrim.toFixed(0)} ms`);

  probe = new Probe(viewer);
  section = new CrossSection(ui.sectionCanvas, { colourOf, onPick: query });

  // click / tap → column query, or a transect endpoint while drawing a section
  const handler = new Cesium.ScreenSpaceEventHandler(scene.canvas);
  handler.setInputAction((e) => {
    const p = pickLonLat(scene, e.position);
    if (!p) return;
    if (state.picking === 'A') {
      state.picking = { a: p };
      ui.setSectionStatus(t('sectionPickingB'));
      probe.set(p, ui.exaggeration());
      return;
    }
    if (state.picking?.a) {
      const a = state.picking.a;
      state.picking = null;
      setTransect(a, p, null);
      return;
    }
    query(p);
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

  // restore the query point and the section from the URL
  if (initial.xs) setTransect(initial.xs[0], initial.xs[1], initial.view && VIEWS[initial.view]?.transect ? initial.view : null);
  else if (initial.view) { ui.setActiveView(initial.view); }
  if (initial.q) query(initial.q);
  changed();

  globalThis.__model = { viewer, model, ui, section, probe, stackAt }; // for the console and device tests only
}

main();
