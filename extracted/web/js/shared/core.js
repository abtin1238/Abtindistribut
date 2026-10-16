/* Shared frontend primitives. Keep cross-page behavior here; pages provide only context. */
(function (root) {
  'use strict';
  let tokenProvider = () => null;
  let apiBase = '/api';
  const escapeHtml = value => String(value == null ? '' : value).replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[char]);
  async function api(path, options = {}) {
    const bodyIsForm = typeof FormData !== 'undefined' && options.body instanceof FormData;
    const headers = {
      ...(bodyIsForm ? {} : { 'Content-Type': 'application/json' }),
      ...(tokenProvider() ? { Authorization: `Bearer ${tokenProvider()}` } : {}),
      ...(options.headers || {})
    };
    const response = await fetch(apiBase + path, { ...options, headers });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(typeof data.detail === 'string' ? data.detail : (data.detail?.[0]?.msg || 'خطا'));
      error.http = true; error.status = response.status; error.data = data;
      throw error;
    }
    return data;
  }
  /* لیست صفحه‌بندی‌شده: بدنه آرایه است و کل ردیف‌ها در هدر X-Total-Count می‌آید. */
  async function apiPage(path, options = {}) {
    const response = await fetch(apiBase + path, { ...options, headers: {
      ...(tokenProvider() ? { Authorization: `Bearer ${tokenProvider()}` } : {}), ...(options.headers || {}) } });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(typeof data.detail === 'string' ? data.detail : (data.detail?.[0]?.msg || 'خطا'));
      error.http = true; error.status = response.status; error.data = data;
      throw error;
    }
    const rows = Array.isArray(data) ? data : [];
    const header = Number(response.headers.get('X-Total-Count'));
    return { rows, total: Number.isFinite(header) && response.headers.has('X-Total-Count') ? header : rows.length, paged: response.headers.has('X-Total-Count') };
  }
  /* هر تصویر آپلودی را به کادر ثابت می‌برد: برش مرکزی (cover) یا جا دادن کامل (contain) و کوچک‌سازی.
     برای لوگو/آواتار: {size:512, fit:'cover'}. خروجی File (WebP؛ اگر پشتیبانی نشد PNG). */
  async function normalizeImage(file, { size = 512, fit = 'cover', ratio = 1, quality = 0.9 } = {}) {
    if (!file || !/^image\/(png|jpe?g|webp)$/.test(file.type)) return file;
    const bmp = await createImageBitmap(file).catch(() => null);
    if (!bmp) return file;
    const w = size, h = Math.round(size / ratio);
    const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
    const cx = cv.getContext('2d');
    const k = (fit === 'cover' ? Math.max : Math.min)(w / bmp.width, h / bmp.height);
    const dw = bmp.width * k, dh = bmp.height * k;
    cx.imageSmoothingQuality = 'high';
    cx.drawImage(bmp, (w - dw) / 2, (h - dh) / 2, dw, dh);
    if (bmp.close) bmp.close();
    let type = 'image/webp', blob = await new Promise(r => cv.toBlob(r, type, quality));
    if (!blob || blob.type !== type) { type = 'image/png'; blob = await new Promise(r => cv.toBlob(r, type)); }
    return new File([blob], 'image.' + (type === 'image/webp' ? 'webp' : 'png'), { type });
  }
  const fa = (value, options = {}) => Number(value ?? 0).toLocaleString('fa-IR', options);
  const money = (value, options = {}) => fa(value || 0, options);
  const jget = (key, fallback = null) => {
    try { const value = JSON.parse(localStorage.getItem(key)); return value ?? fallback; }
    catch (_) { return fallback; }
  };
  const jset = (key, value) => {
    try { localStorage.setItem(key, JSON.stringify(value)); return true; }
    catch (_) { return false; }
  };
  const today = (date = new Date()) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  const post = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body || {}) });
  const patch = (path, body) => api(path, { method: 'PATCH', body: JSON.stringify(body || {}) });
  async function syncQueue({ Q, REJ, jget, jset, onResults, flush }) {
    try {
      const queued = await Q.all();
      if (queued.length) {
        const result = await post('/sync', { events: queued });
        const results = result.results || [];
        const keep = new Set(results.filter(item => item.status === 'retry').map(item => item.id));
        const rejected = results.filter(item => item.status === 'rejected');
        await Q.set(queued.filter(item => keep.has(item.id)));
        if (rejected.length) {
          const rejectedLog = rejected.map(item => ({
            type: (queued.find(event => event.id === item.id) || {}).type,
            detail: item.detail
          }));
          jset(REJ, jget(REJ, []).concat(rejectedLog).slice(-20));
        }
        if (onResults) await onResults({ queued, results, rejected });
      }
    } catch (_) { /* Offline: retain queue and retry later. */ }
    if (flush) { try { await flush(); } catch (_) {} }
  }
  root.Shared = Object.freeze({
    configure(options = {}) { if (options.token) tokenProvider = options.token; if (options.apiBase) apiBase = options.apiBase; },
    api, apiPage, normalizeImage, post, patch, escapeHtml, esc: escapeHtml, fa, money, jget, jset, today, syncQueue
  });
})(window);
