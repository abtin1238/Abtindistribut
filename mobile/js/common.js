/* Shared helpers for both mobile PWAs (visitor + driver). App files supply only what differs. */
(function (root) {
  'use strict';
  const $ = id => document.getElementById(id);

  const pos = () => new Promise(resolve => navigator.geolocation
    ? navigator.geolocation.getCurrentPosition(p => resolve(p), () => resolve(null), { enableHighAccuracy: true, timeout: 8000 })
    : resolve(null));

  /* Offline event queue: stamps a stable id and stores the event. */
  const makeQueue = Q => async function queue(event) {
    const ev = { ...event, id: event.id || crypto.randomUUID() };
    await Q.add(ev);
    return ev.id;
  };

  /* Location tracking consent/start/stop; state lives here instead of per-app `_trk` flags. */
  function tracking({ prefix, api, queue, sync }) {
    let running = false;
    return {
      start() {
        if (running) return;
        running = true;
        Tracker.start({ prefix, api, queue, sync }).catch(() => { running = false; });
      },
      toggle() {
        if (Tracker.enabled()) {
          if (confirm('ردیابی موقعیت خاموش شود؟')) { Tracker.setConsent(false); running = false; alert('ردیابی خاموش شد'); }
        } else {
          Tracker.setConsent(true); running = true;
          alert('ردیابی روشن شد؛ فقط در ساعات کاری ثبت می‌شود');
        }
      },
      stop() { try { Tracker.stop(); } catch (_) {} running = false; }
    };
  }

  /* Upload queued photos. `target(photo)` returns the entity id (or falsy to skip for now). */
  async function flushPhotos({ Photos, api, path, filename, target }) {
    for (const photo of await Photos.all()) {
      const id = target(photo);
      if (!id) continue;
      try {
        const body = new FormData();
        body.append('file', photo.blob, filename);
        await api(`${path}/${id}/photo`, { method: 'POST', body });
        await Photos.del(photo.pid);
      } catch (e) { if (e.http) await Photos.del(photo.pid); }
    }
  }

  /* Remember the map position in localStorage and repaint. */
  function locate({ key, jset, onFound }) {
    pos().then(p => {
      if (!p) return alert('دسترسی به موقعیت مکانی ممکن نیست');
      const me = { lat: p.coords.latitude, lng: p.coords.longitude };
      jset(key, me);
      onFound(me);
    });
  }

  root.MobileCommon = Object.freeze({ $, pos, makeQueue, tracking, flushPhotos, locate });
})(window);
