/* مرحله ۱۷ — میان‌بر کیبورد + دکمه‌ی تم روشن/تاریک. در فیلد متنی فعال نمی‌شود. */
(() => {
  'use strict';
  const NAV = { d: 'dashboard', c: 'customers', p: 'products', o: 'orders', i: 'invoices', s: 'stock', a: 'accounting', r: 'reports', m: 'map' };
  let g = 0;
  const typing = t => t && (/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || t.isContentEditable);
  addEventListener('keydown', e => {
    if (e.ctrlKey || e.metaKey || e.altKey || typing(e.target) || document.querySelector('.fd-back')) return;
    if (g && Date.now() - g < 1500) { g = 0; const p = NAV[e.key]; if (p && typeof go === 'function' && typeof pages !== 'undefined' && pages[p]) { e.preventDefault(); go(p); } return; }
    if (e.key === 'g') { g = Date.now(); return; }
    if (e.key === '/') { const q = document.querySelector('.dt-q'); if (q) { e.preventDefault(); q.focus(); } }
    else if (e.key === 'n') { const b = document.querySelector('[data-act=create]'); if (b) { e.preventDefault(); b.click(); } }
    else if (e.key === '?') {
      e.preventDefault();
      const rows = [['/', 'جست‌وجو در جدول'], ['n', 'مورد جدید'], ['g سپس d', 'داشبورد'], ['g سپس c', 'مشتریان'], ['g سپس p', 'کالا'], ['g سپس o', 'سفارش‌ها'], ['g سپس i', 'فاکتورها'], ['g سپس s', 'انبار'], ['g سپس a', 'حسابداری'], ['g سپس r', 'گزارش‌ها'], ['Esc', 'بستن پنجره'], ['?', 'این راهنما']];
      const m = Modal('<h3>میان‌بر کیبورد</h3><div class="kb-help">' + rows.map(r => `<kbd>${Shared.escapeHtml(r[0])}</kbd><span>${Shared.escapeHtml(r[1])}</span>`).join('') + '</div><div class="fd-btn"><button type="button" data-x class="primary">بستن</button></div>', 'میان‌بر کیبورد');
      m.box.querySelector('[data-x]').onclick = m.close;
    }
  });
  // عنصر role=button با onclick باید با Enter/Space هم کار کند (دسترس‌پذیری کیبورد)
  addEventListener('keydown', e => {
    const t = e.target;
    if ((e.key === 'Enter' || e.key === ' ') && t && t.getAttribute && t.getAttribute('role') === 'button' && !/^(BUTTON|A|INPUT)$/.test(t.tagName)) { e.preventDefault(); t.click(); }
  });
  const addBtn = () => {
    const bar = document.querySelector('.hd-r, .top-actions'); if (!bar || bar.querySelector('[data-theme-toggle]')) return;
    const b = document.createElement('button'); b.type = 'button'; b.className = 'bell'; b.dataset.themeToggle = '1'; b.textContent = '◐';
    b.setAttribute('aria-label', 'تغییر تم روشن/تاریک'); b.title = 'تم روشن/تاریک'; b.onclick = () => { if (typeof Tokens !== 'undefined') Tokens.toggle(); };
    bar.prepend(b);
  };
  new MutationObserver(addBtn).observe(document.body || document.documentElement, { childList: true, subtree: true }); addBtn();
})();
