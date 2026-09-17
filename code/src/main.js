// Viewer bootstrap and camera (SPEC §6): EllipsoidTerrainProvider + OpenStreetMap imagery, no
// Cesium ion token — deliberate, do not "improve" it. Cesium is the pinned CDN global.
import './styles.css';
import { CAMERA_HOME, GLOBE, MODEL_BBOX, OSM_TILES, EXAGGERATION, CESIUM_VERSION } from './config.js';
import { checkExtent, meta } from './zones.js';
import { StrataModel } from './strata.js';
import { buildUI } from './ui.js';

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

  let model = null;
  const root = document.getElementById('ui');
  const ui = buildUI(root, {
    exaggeration: (f) => { if (model) model.setExaggeration(f); },
    stratum: (s, on) => model?.setStratumVisible(s, on),
    zone: (id, on) => model?.setZoneVisible(id, on),
    home: () => flyHome(),
  });

  const viewer = new Cesium.Viewer('cesiumContainer', {
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

  // Minimal URL state for now (Phase 4 makes it shareable both ways):
  //   ?cam=lon,lat,height,heading,pitch  ?ex=<factor>  ?hide=airspace,subsoil,<zone-id>,...
  const params = new URLSearchParams(location.search);

  function flyHome(duration = 0) {
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(CAMERA_HOME.lon, CAMERA_HOME.lat, CAMERA_HOME.height),
      orientation: { heading: Cesium.Math.toRadians(CAMERA_HOME.heading), pitch: Cesium.Math.toRadians(CAMERA_HOME.pitch), roll: 0 },
      duration,
    });
  }
  const cam = params.get('cam')?.split(',').map(Number);
  if (cam && cam.length === 5 && cam.every(Number.isFinite)) {
    viewer.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(cam[0], cam[1], cam[2]),
      orientation: { heading: Cesium.Math.toRadians(cam[3]), pitch: Cesium.Math.toRadians(cam[4]), roll: 0 },
    });
  } else {
    flyHome(0);
  }

  model = new StrataModel(scene);
  const t0 = performance.now();
  model.build();
  const tBuild = performance.now() - t0;
  const ex = Number(params.get('ex'));
  const initial = Number.isFinite(ex) && ex >= EXAGGERATION.min && ex <= EXAGGERATION.max ? ex : EXAGGERATION.initial;
  for (const h of (params.get('hide') ?? '').split(',').filter(Boolean)) {
    if (['airspace', 'watercolumn', 'seabed', 'subsoil'].includes(h)) model.hidden.strata.add(h); else model.hidden.zones.add(h);
  }
  ui.setExaggeration(initial);
  const tPrim = model.setExaggeration(initial);
  console.info(`zones.json ${meta.generated}: ${model.stats.meshes} volumes, ${model.stats.vertices} vertices, ${model.stats.triangles} triangles; meshing ${tBuild.toFixed(0)} ms, primitives ${tPrim.toFixed(0)} ms`);

  globalThis.__model = { viewer, model, ui }; // for the console and device tests only
}

main();
