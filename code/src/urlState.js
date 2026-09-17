// Shareable URL state (SPEC §7): camera, active layers, exaggeration, language, and the Phase 4
// additions — column-query point, cross-section transect and preset view — in the query string.
// Written with history.replaceState (no reload, works inside an iframe); course links open a
// configured view directly.
//
//   ?cam=lon,lat,height,heading,pitch   ?ex=<factor>   ?hide=airspace,subsoil,<zone-id>,...
//   ?lang=no|en   ?q=lon,lat (column query)   ?xs=lon,lat,lon,lat (transect)   ?view=<preset>
//   ?panel=0 (start with the main panel collapsed)

const nums = (s, n) => {
  const v = (s ?? '').split(',').map(Number);
  return v.length === n && v.every(Number.isFinite) ? v : null;
};

export function readState(search = location.search) {
  const p = new URLSearchParams(search);
  const cam = nums(p.get('cam'), 5);
  const q = nums(p.get('q'), 2);
  const xs = nums(p.get('xs'), 4);
  const ex = Number(p.get('ex'));
  return {
    cam: cam ? { lon: cam[0], lat: cam[1], height: cam[2], heading: cam[3], pitch: cam[4] } : null,
    ex: Number.isFinite(ex) && ex > 0 ? ex : null,
    hide: (p.get('hide') ?? '').split(',').filter(Boolean),
    lang: ['no', 'en'].includes(p.get('lang')) ? p.get('lang') : null,
    q: q ? { lon: q[0], lat: q[1] } : null,
    xs: xs ? [{ lon: xs[0], lat: xs[1] }, { lon: xs[2], lat: xs[3] }] : null,
    view: p.get('view') || null,
    panel: p.get('panel') !== '0',
  };
}

const f4 = (v) => v.toFixed(4).replace(/\.?0+$/, '');

export function encodeState(s) {
  const p = new URLSearchParams();
  if (s.view) p.set('view', s.view);
  if (s.cam) p.set('cam', [f4(s.cam.lon), f4(s.cam.lat), Math.round(s.cam.height), (((s.cam.heading % 360) + 360) % 360).toFixed(1), s.cam.pitch.toFixed(1)].join(','));
  if (s.ex && s.ex !== s.exDefault) p.set('ex', String(s.ex));
  if (s.hide?.length) p.set('hide', s.hide.join(','));
  if (s.lang && s.lang !== 'no') p.set('lang', s.lang);
  if (s.q) p.set('q', [f4(s.q.lon), f4(s.q.lat)].join(','));
  if (s.xs) p.set('xs', s.xs.flatMap((pt) => [f4(pt.lon), f4(pt.lat)]).join(','));
  if (s.panel === false) p.set('panel', '0');
  const qs = p.toString();
  return qs ? `?${qs}` : '';
}

let pending = null;

/** Replace the current URL's query string (debounced: camera moves fire often). */
export function writeState(state, delayMs = 250) {
  clearTimeout(pending);
  pending = setTimeout(() => {
    const qs = encodeState(state);
    const url = `${location.pathname}${qs}${location.hash}`;
    if (url !== `${location.pathname}${location.search}${location.hash}`) history.replaceState(null, '', url);
  }, delayMs);
}

export function shareUrl(state) {
  return `${location.origin}${location.pathname}${encodeState(state)}`;
}
