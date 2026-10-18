/* Service worker shared by both mobile PWAs. API responses are never cached. */
const CACHE_VERSION = 'abtin-mobile-v12';
const SHELL = [
  '/web/styles/core.css',
  '/web/styles/primitives.css',
  '/web/styles/controls.css',
  '/web/styles/uikit.css',
  '/web/styles/components/surface.css',
  '/web/styles/palette.css',
  '/web/styles/theme-tokens.css',
  '/web/styles/design-system.css',
  '/web/js/auth-refresh.js',
  '/web/js/tokens.js',
  '/web/js/styles.js',
  '/web/js/styles-bridge.js',
  '/mobile/styles/shared.css',
  '/mobile/js/common.js',
  '/web/js/shared/core.js',
  '/mobile/js/offline.js',
  '/mobile/js/ui.js',
  '/mobile/js/map.js',
  '/mobile/js/tracker.js',
  '/mobile/visitor/',
  '/mobile/js/visitor-app.js',
  '/mobile/visitor/manifest.json',
  '/mobile/driver/',
  '/mobile/js/driver-app.js',
  '/mobile/driver/manifest.json'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_VERSION)
      .then(cache => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE_VERSION).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;

  event.respondWith(
    fetch(request).then(response => {
      if (response.ok) {
        const copy = response.clone();
        caches.open(CACHE_VERSION).then(cache => cache.put(request, copy));
      }
      return response;
    }).catch(() => caches.match(request, { ignoreSearch: true }).then(cached => {
      if (cached) return cached;
      if (request.mode === 'navigate') {
        return caches.match(url.pathname.startsWith('/mobile/driver') ? '/mobile/driver/' : '/mobile/visitor/');
      }
      return Response.error();
    }))
  );
});
