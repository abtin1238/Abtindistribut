/* پنل مدیریت: فاکتورها و ثبت سفارش/فاکتور. همه‌ی مقادیر پویا escape می‌شوند؛ یادداشت‌ها با به‌صورت متن ساده ثبت می‌شوند.
   وابستگی‌ها: app.js (api, content, me, go, pages)، sales.js (extraPages). */
(() => {
  'use strict';
  const plainNote = h => { const d = document.createElement('div'); d.innerHTML = String(h || '').replace(/<\/(p|div|li|h\d)>|<br\s*\/?>/gi, '\n'); return (d.textContent || '').trim(); };
  const E = Shared.esc, F = v => Shared.fa(v, { maximumFractionDigits: 2 }), I = v => parseInt(v, 10) || 0, Num = v => Number(v || 0);
  const ST = { open: ['پرداخت‌نشده', 'bad'], partial: ['پرداخت جزئی', 'warn'], paid: ['پرداخت‌شده', 'ok'], cancelled: ['باطل‌شده', 'mut'] };
  const OST = { draft: 'پیش‌نویس', confirmed: 'تأییدشده', assigned: 'تخصیص‌یافته', delivered: 'تحویل‌شده', cancelled: 'لغوشده' };
  const METHODS = { cash: 'نقد', card: 'کارت', transfer: 'حواله / واریز' };
  const jd = s => { if (!s) return '—'; const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? s : s + 'Z'); return isNaN(d) ? '—' : new Intl.DateTimeFormat('fa-IR-u-ca-persian', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(d).replace(/\u200f/g, ''); };
  const can = p => { const ps = (me && me.user && me.user.permissions) || [], [mo, a] = p.split('.'); return ps.includes('*') || ps.includes(p) || ps.includes(mo + '.*') || (['read', 'collect'].includes(a) && ps.includes(mo + '.write')); };
  const badge = st => { const [t, tone] = ST[st] || [st, 'mut']; return `<span class="inv-badge" data-tone="${E(tone)}">${E(t)}</span>`; };
  const table = (head, rows, empty) => `<div class="tablewrap"><table><thead><tr>${head.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.length ? rows.join('') : `<tr><td colspan="${head.length}" class="inv-empty">${empty}</td></tr>`}</tbody></table></div>`;

  /* ---------- پنجرهٔ مودال ---------- */
  function modal(title, bodyHtml, { wide = false } = {}) {
    const el = document.createElement('div'); el.className = 'ds-modal'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-modal', 'true'); el.setAttribute('aria-label', title);
    el.innerHTML = `<div class="cd ds-modal-card${wide ? ' inv-modal-wide' : ''}"><header><h3>${E(title)}</h3><button type="button" class="ghost" data-close aria-label="بستن">✕</button></header><div class="inv-modal-body">${bodyHtml}</div></div>`;
    const prev = document.activeElement, editors = [];
    const close = () => { editors.forEach(e => e.destroy()); document.removeEventListener('keydown', onKey); el.remove(); if (prev && prev.focus) prev.focus(); };
    const onKey = e => { if (e.key === 'Escape' && !document.querySelector('.re.re-full')) close(); };
    el.addEventListener('mousedown', e => { if (e.target === el) close(); });
    el.querySelector('[data-close]').onclick = close;
    document.addEventListener('keydown', onKey); document.body.appendChild(el);
    const first = el.querySelector('input,select,button:not([data-close]),.re-area'); if (first) first.focus();
    return { el, close, q: s => el.querySelector(s), editor(host, opts) { const h = el.querySelector(host); h.innerHTML = '<textarea rows="' + (opts.minHeight > 150 ? 8 : 4) + '" maxlength="' + (opts.maxLength || 3000) + '" placeholder="' + E(opts.placeholder || '') + '" class="ctl-block"></textarea>'; const t = h.firstChild; t.value = plainNote(opts.value); return { getHTML: () => t.value, destroy() {} }; } };
  }
  const guard = async (fn, btn) => { if (btn) btn.disabled = true; try { return await fn(); } catch (e) { alert(e.message || 'خطا'); } finally { if (btn) btn.disabled = false; } };

  /* ---------- لیست فاکتورها ---------- */
  const invF = { q: '', status: '', start: '', end: '' };
  async function invoicesList() {
    const qs = new URLSearchParams(); Object.entries(invF).forEach(([k, v]) => { if (v) qs.set(k, v); });
    const d = await api('/invoices' + (qs.toString() ? '?' + qs : ''));
    const live = d.filter(x => x.status !== 'cancelled');
    const sum = k => live.reduce((a, x) => a + Num(x[k]), 0), rem = live.reduce((a, x) => a + Math.max(0, Num(x.remaining)), 0);
    const rows = d.map(x => {
      const r = Num(x.remaining), done = x.status === 'cancelled';
      return `<tr><td>${E(x.number)}<div class="ds-muted inv-sub">${E(x.order_number)}</div></td><td>${E(jd(x.issued_at))}</td><td>${E(x.customer_name)}</td><td class="n">${F(x.total)}</td><td class="n">${F(x.paid)}</td>
        <td class="n ${r > 0 && !done ? 'ds-text-danger' : ''}">${done ? '—' : r < 0 ? F(-r) + ' <small>(بستانکار)</small>' : F(r)}</td><td>${badge(x.status)}</td>
        <td class="inv-actions"><a class="ds-link" href="/web/invoice.html?id=${I(x.id)}" target="_blank" rel="noopener">چاپ</a>
        ${!done && r > 0 && can('finance.collect') ? `<button type="button" data-inv="pay" data-id="${I(x.id)}">دریافت</button>` : ''}
        <button type="button" class="ghost" data-inv="files" data-id="${I(x.id)}">پیوست</button>
        ${!done ? `<button type="button" class="ghost" data-inv="note" data-id="${I(x.id)}">یادداشت</button>` : ''}
        ${!done && x.order_status === 'delivered' && can('sales.approve') ? `<button type="button" class="ghost" data-inv="return" data-id="${I(x.id)}">برگشت</button>` : ''}
        ${!done && ['confirmed', 'assigned'].includes(x.order_status) && can('sales.approve') ? `<button type="button" class="ghost ds-danger" data-inv="cancel" data-id="${I(x.id)}" data-order="${I(x.order_id)}">ابطال</button>` : ''}</td></tr>`;
    });
    content.innerHTML = `<h1>${pages.invoices}</h1>
      <div class="inv-toolbar"><button type="button" data-inv="new">+ فاکتور جدید</button>${can('settings.write') ? '<button type="button" class="ghost" data-inv="terms">شرایط و توضیحات پیش‌فرض فاکتور</button>' : ''}</div>
      <div class="cards inv-stats"><div class="card">تعداد فاکتور<br><b>${F(live.length)}</b></div><div class="card">جمع فروش<br><b>${F(sum('total'))}</b></div><div class="card">دریافت‌شده<br><b>${F(sum('paid'))}</b></div><div class="card">مانده مطالبات<br><b class="ds-text-danger">${F(rem)}</b></div></div>
      <form class="inv-filters" id="invf"><input type="search" name="q" placeholder="شماره فاکتور، سفارش یا نام مشتری" value="${E(invF.q)}" aria-label="جست‌وجو">
        <select name="status" aria-label="وضعیت"><option value="">همه‌ی وضعیت‌ها</option>${Object.entries(ST).map(([k, v]) => `<option value="${E(k)}"${k === invF.status ? ' selected' : ''}>${E(v[0])}</option>`).join('')}</select>
        <label>از <input type="date" name="start" value="${E(invF.start)}"></label><label>تا <input type="date" name="end" value="${E(invF.end)}"></label>
        <button type="submit">اعمال</button><button type="button" class="ghost" data-inv="reset">پاک‌کردن</button></form>
      ${table(['شماره', 'تاریخ', 'مشتری', 'جمع کل', 'پرداخت‌شده', 'مانده', 'وضعیت', ''], rows, invF.q || invF.status || invF.start || invF.end ? 'فاکتوری با این فیلتر پیدا نشد.' : 'هنوز فاکتوری صادر نشده است؛ از «فاکتور جدید» شروع کنید.')}`;
    const f = document.getElementById('invf');
    f.onsubmit = e => { e.preventDefault(); const fd = new FormData(f); ['q', 'status', 'start', 'end'].forEach(k => { invF[k] = String(fd.get(k) || '').trim(); }); go('invoices'); };
  }

  async function payModal(id) {
    const d = await api('/invoices/' + id), inv = d.invoice, rem = Math.max(0, Num(d.remaining));
    const m = modal('دریافت وجه — فاکتور ' + inv.number, `<p class="ds-muted">مانده قابل دریافت: <b>${F(rem)}</b></p>
      <div class="inv-form"><label>مبلغ<input type="number" name="amount" min="0" step="any" value="${E(String(rem))}"></label>
      <label>روش<select name="method">${Object.entries(METHODS).map(([k, v]) => `<option value="${E(k)}">${E(v)}</option>`).join('')}</select></label>
      <label class="inv-full">شماره پیگیری / توضیح<input type="text" name="reference" maxlength="120"></label></div>
      <div class="inv-modal-foot"><button type="button" data-ok>ثبت دریافت</button><button type="button" class="ghost" data-close2>انصراف</button></div>`);
    m.q('[data-close2]').onclick = m.close;
    m.q('[data-ok]').onclick = ev => guard(async () => {
      const amount = Num(m.q('[name=amount]').value); if (!(amount > 0)) throw new Error('مبلغ باید بیشتر از صفر باشد');
      if (amount > rem + 0.001) throw new Error('مبلغ بیشتر از مانده فاکتور است');
      await Shared.post('/payments', { invoice_id: inv.id, amount: String(amount), method: m.q('[name=method]').value, kind: 'receipt', reference: m.q('[name=reference]').value.trim() });
      m.close(); go('invoices');
    }, ev.currentTarget);
  }

  async function noteModal(id) {
    const d = await api('/invoices/' + id);
    const m = modal('یادداشت فاکتور ' + d.invoice.number, `<p class="ds-muted">این متن روی نسخهٔ چاپی فاکتور نمایش داده می‌شود.</p><div id="ned"></div><div class="inv-modal-foot"><button type="button" data-ok>ذخیره</button><button type="button" class="ghost" data-close2>انصراف</button></div>`, { wide: true });
    const ed = m.editor('#ned', { value: d.invoice.note || '', placeholder: 'یادداشت یا توضیحات فاکتور…', maxLength: 3000, minHeight: 200 });
    m.q('[data-close2]').onclick = m.close;
    m.q('[data-ok]').onclick = ev => guard(async () => { await Shared.patch('/invoices/' + id + '/note', { note: ed.getHTML() }); m.close(); go('invoices'); }, ev.currentTarget);
  }

  async function returnModal(id) {
    const d = await api('/invoices/' + id), inv = d.invoice;
    const rows = d.lines.map(l => `<tr><td>${E(l.description)}</td><td class="n">${F(l.quantity)} ${E(l.unit)}</td><td><input type="number" class="ds-w-md" data-ret="${I(l.product_id)}" min="0" max="${E(String(l.quantity))}" step="any" value="0" aria-label="تعداد برگشتی ${E(l.description)}"></td></tr>`);
    const m = modal('برگشت از فروش — فاکتور ' + inv.number, `${d.returns.length ? `<p class="ds-muted">برگشتی‌های قبلی: ${d.returns.map(r => E(r.number)).join('، ')}</p>` : ''}${table(['کالا', 'تعداد فاکتور', 'تعداد برگشتی'], rows, '—')}
      <label class="inv-full">دلیل برگشت<input type="text" name="reason" maxlength="500"></label><div class="inv-modal-foot"><button type="button" data-ok>ثبت برگشت</button><button type="button" class="ghost" data-close2>انصراف</button></div>`, { wide: true });
    m.q('[data-close2]').onclick = m.close;
    m.q('[data-ok]').onclick = ev => guard(async () => {
      const items = [...m.el.querySelectorAll('[data-ret]')].map(i => ({ product_id: I(i.dataset.ret), quantity: String(Num(i.value)) })).filter(i => Num(i.quantity) > 0);
      if (!items.length) throw new Error('تعداد برگشتی وارد نشده است');
      await Shared.post('/orders/' + d.order_id + '/return', { items, reason: m.q('[name=reason]').value.trim() }); m.close(); go('invoices');
    }, ev.currentTarget);
  }

  async function termsModal() {
    const d = await api('/settings/invoice-terms');
    const m = modal('شرایط و توضیحات پیش‌فرض فاکتور', `<p class="ds-muted">در لحظهٔ صدور روی هر فاکتور جدید ثبت می‌شود؛ فاکتورهای قبلی تغییر نمی‌کنند.</p><div id="ted"></div><div class="inv-modal-foot"><button type="button" data-ok>ذخیره</button><button type="button" class="ghost" data-close2>انصراف</button></div>`, { wide: true });
    const ed = m.editor('#ted', { value: d.terms || '', placeholder: 'مثلاً: شرایط پرداخت، مهلت اعتراض، اطلاعات حساب بانکی…', maxLength: 3000, minHeight: 200 });
    m.q('[data-close2]').onclick = m.close;
    m.q('[data-ok]').onclick = ev => guard(async () => { await Shared.api('/settings/invoice-terms', { method: 'PUT', body: JSON.stringify({ terms: ed.getHTML() }) }); m.close(); alert('ذخیره شد'); }, ev.currentTarget);
  }

  /* ---------- سفارش / فاکتور جدید ---------- */
  let draft = null;
  const emptyDraft = () => ({ customer_id: '', warehouse_id: '', shipping: '', lines: [{ product_id: '', quantity: '1', discount: '0' }], note: '' });

  async function ordersPage(flash = '') {
    const [customers, warehouses, products, stock, orders, taxR] = await Promise.all([api('/customers'), api('/warehouses'), api('/products'), api('/stock'), api('/orders'), api('/settings/tax').catch(() => null)]);
    draft = draft || emptyDraft();
    if (!draft.warehouse_id && warehouses.length === 1) draft.warehouse_id = String(warehouses[0].id);
    const cname = Object.fromEntries(customers.map(c => [c.id, c.name])), price = Object.fromEntries(products.map(p => [p.id, Num(p.base_price)])), vat = taxR ? Num(taxR.vat_percent) : 0;
    const canDiscount = can('pricing.write');
    const avail = wid => stock.filter(s => String(s.warehouse_id) === String(wid) && Num(s.available) > 0);

    content.innerHTML = `<h1>${pages.orders}</h1>${flash}
      <section class="cd inv-new" aria-labelledby="newh"><header><h3 id="newh">سفارش / فاکتور جدید</h3></header>
        <div class="inv-form"><label>مشتری<select id="o-c"><option value="">انتخاب مشتری…</option>${customers.map(c => `<option value="${I(c.id)}"${String(c.id) === String(draft.customer_id) ? ' selected' : ''}>${E(c.name)} (${E(c.code)})</option>`).join('')}</select></label>
          <label>انبار<select id="o-w"><option value="">انتخاب انبار…</option>${warehouses.map(w => `<option value="${I(w.id)}"${String(w.id) === String(draft.warehouse_id) ? ' selected' : ''}>${E(w.name)}</option>`).join('')}</select></label>
          <label>هزینه حمل<input id="o-s" type="number" min="0" step="any" value="${E(draft.shipping)}" placeholder="۰"></label></div>
        <div id="o-lines"></div><button type="button" class="ghost" id="o-add">+ افزودن ردیف کالا</button>
        <div class="inv-note"><label for="o-note-h">یادداشت فاکتور (روی نسخهٔ چاپی نمایش داده می‌شود)</label><div id="o-note-h"></div></div>
        <div id="o-tot" class="inv-total-box" aria-live="polite"></div>
        <p class="ds-muted inv-sub">جمع‌ها بر پایهٔ قیمت پایه برآورد شده‌اند؛ قیمت نهایی (قوانین قیمت‌گذاری گروه مشتری) هنگام ثبت توسط سرور محاسبه می‌شود.</p>
        <div class="inv-modal-foot"><button type="button" id="o-issue">ثبت و صدور فاکتور</button><button type="button" class="ghost" id="o-save">ذخیرهٔ سفارش (پیش‌نویس)</button><button type="button" class="ghost" id="o-reset">پاک‌کردن فرم</button></div></section>
      <h3 class="inv-list-h">سفارش‌های اخیر</h3>${table(['شماره', 'مشتری', 'وضعیت', 'مبلغ', ''], orders.slice().sort((a, b) => b.id - a.id).map(o => `<tr><td>${E(o.number)}</td><td>${E(cname[o.customer_id] || '—')}</td><td>${E(OST[o.status] || o.status)}</td><td class="n">${F(o.total)}</td>
        <td class="inv-actions">${o.status === 'draft' && can('sales.approve') ? `<button type="button" data-ord="approve" data-id="${I(o.id)}">تأیید و صدور فاکتور</button>` : ''}${['draft', 'confirmed', 'assigned'].includes(o.status) && can('sales.approve') ? `<button type="button" class="ghost ds-danger" data-ord="cancel" data-id="${I(o.id)}">لغو</button>` : ''}</td></tr>`), 'سفارشی ثبت نشده است.')}`;

    const $ = id => document.getElementById(id);
    $('o-note-h').innerHTML = '<textarea id="o-note" rows="3" maxlength="3000" class="ctl-block" placeholder="شرایط ویژه، توضیح تحویل، ارجاع به قرارداد…"></textarea>'; $('o-note').value = draft.note || ''; $('o-note').oninput = e => { draft.note = e.target.value; };
    function totals() {
      let sub = 0; draft.lines.forEach(l => { sub += Math.max(0, Num(l.quantity) * (price[l.product_id] || 0) - Num(l.discount)); });
      const tax = Math.round(sub * vat) / 100, ship = Num(draft.shipping);
      $('o-tot').innerHTML = `<div>جمع اقلام: <b>${F(sub)}</b></div>${vat ? `<div>مالیات (${F(vat)}٪): <b>${F(tax)}</b></div>` : ''}${ship ? `<div>حمل: <b>${F(ship)}</b></div>` : ''}<div class="inv-grand">مبلغ قابل پرداخت (برآورد): <b>${F(sub + tax + ship)}</b></div>`;
    }
    function lines() {
      const opts = avail(draft.warehouse_id), nostock = draft.warehouse_id ? products.filter(p => !opts.some(o => String(o.product_id) === String(p.id))) : [];
      $('o-lines').innerHTML = table(['کالا', 'تعداد', 'تخفیف', 'مبلغ', ''], draft.lines.map((l, i) => {
        const st = opts.find(s => String(s.product_id) === String(l.product_id)), t = Math.max(0, Num(l.quantity) * (price[l.product_id] || 0) - Num(l.discount));
        return `<tr><td><select data-f="product_id" data-i="${i}" aria-label="کالا"><option value="">${draft.warehouse_id ? 'انتخاب کالا…' : 'ابتدا انبار را انتخاب کنید'}</option>${opts.map(s => `<option value="${I(s.product_id)}"${String(s.product_id) === String(l.product_id) ? ' selected' : ''}>${E(s.product)} — موجود ${E(F(s.available))}</option>`).join('')}${nostock.map(p => `<option value="" disabled>${E(p.name)} — بدون موجودی</option>`).join('')}</select></td>
          <td><input type="number" class="ds-w-md" data-f="quantity" data-i="${i}" min="0" step="any" value="${E(l.quantity)}" ${st ? `max="${E(String(st.available))}"` : ''} aria-label="تعداد"></td>
          <td><input type="number" class="ds-w-md" data-f="discount" data-i="${i}" min="0" step="any" value="${E(l.discount)}" ${canDiscount ? '' : 'disabled title="مجوز تخفیف دستی ندارید"'} aria-label="تخفیف"></td>
          <td class="n">${l.product_id ? F(t) : '—'}</td><td>${draft.lines.length > 1 ? `<button type="button" class="ghost ds-danger" data-del="${i}" aria-label="حذف ردیف">✕</button>` : ''}</td></tr>`;
      }), '');
      totals();
    }
    lines();
    $('o-lines').onchange = e => { const t = e.target, i = I(t.dataset.i); if (t.dataset.f) { draft.lines[i][t.dataset.f] = t.value; lines(); } };
    $('o-lines').oninput = e => { const t = e.target; if (t.dataset.f === 'quantity' || t.dataset.f === 'discount') { draft.lines[I(t.dataset.i)][t.dataset.f] = t.value; totals(); } };
    $('o-lines').onclick = e => { const b = e.target.closest('[data-del]'); if (b) { draft.lines.splice(I(b.dataset.del), 1); lines(); } };
    $('o-add').onclick = () => { draft.lines.push({ product_id: '', quantity: '1', discount: '0' }); lines(); };
    $('o-c').onchange = e => { draft.customer_id = e.target.value; };
    $('o-w').onchange = e => { draft.warehouse_id = e.target.value; draft.lines = draft.lines.map(l => ({ ...l, product_id: '' })); lines(); };
    $('o-s').oninput = e => { draft.shipping = e.target.value; totals(); };
    $('o-reset').onclick = () => { if (confirm('فرم پاک شود؟')) { draft = null; ordersPage(); } };
    async function submit(issue, btn) {
      if (!draft.customer_id) throw new Error('مشتری را انتخاب کنید');
      if (!draft.warehouse_id) throw new Error('انبار را انتخاب کنید');
      const items = draft.lines.filter(l => l.product_id && Num(l.quantity) > 0).map(l => ({ product_id: I(l.product_id), quantity: String(Num(l.quantity)), discount: String(Num(l.discount)) }));
      if (!items.length) throw new Error('حداقل یک کالا با تعداد معتبر لازم است');
      const o = await Shared.post('/orders', { customer_id: I(draft.customer_id), warehouse_id: I(draft.warehouse_id), items, shipping: String(Num(draft.shipping)), note: draft.note || '' });
      draft = null;
      if (issue) {
        try { await Shared.post('/orders/' + o.id + '/approve'); } catch (e) { return ordersPage(`<div class="error">سفارش ${E(o.number)} ثبت شد ولی صدور فاکتور انجام نشد: ${E(e.message)}</div>`); }
        const inv = (await api('/invoices?q=' + encodeURIComponent(o.number))).find(x => x.order_id === o.id);
        return ordersPage(`<div class="inv-flash">سفارش ${E(o.number)} ثبت و فاکتور صادر شد. ${inv ? `<a class="ds-link" href="/web/invoice.html?id=${I(inv.id)}" target="_blank" rel="noopener">مشاهده و چاپ فاکتور ${E(inv.number)}</a>` : ''}</div>`);
      }
      return ordersPage(`<div class="inv-flash">سفارش ${E(o.number)} به‌صورت پیش‌نویس ثبت شد.</div>`);
    }
    $('o-issue').onclick = e => guard(() => submit(true), e.currentTarget);
    $('o-save').onclick = e => guard(() => submit(false), e.currentTarget);
  }

  /* ---------- رویدادها (delegation یک‌بار) ---------- */
  document.addEventListener('click', e => {
    const b = e.target.closest('[data-inv],[data-ord]'); if (!b) return;
    const id = I(b.dataset.id);
    if (b.dataset.inv) {
      const a = b.dataset.inv;
      if (a === 'new') return go('orders');
      if (a === 'reset') { Object.keys(invF).forEach(k => { invF[k] = ''; }); return go('invoices'); }
      if (a === 'pay') return guard(() => payModal(id), b);
      if (a === 'note') return guard(() => noteModal(id), b);
      if (a === 'return') return guard(() => returnModal(id), b);
      if (a === 'files') return guard(() => invAttach(id), b);
      if (a === 'terms') return guard(() => termsModal(), b);
      if (a === 'cancel') { if (!confirm('فاکتور و سفارش باطل شود؟ سند حسابداری معکوس و رزرو انبار آزاد می‌شود.')) return; return guard(async () => { await Shared.post('/orders/' + I(b.dataset.order) + '/cancel'); go('invoices'); }, b); }
    }
    if (b.dataset.ord === 'approve') return guard(async () => { await Shared.post('/orders/' + id + '/approve'); go('orders'); }, b);
    if (b.dataset.ord === 'cancel') { if (!confirm('سفارش لغو شود؟')) return; return guard(async () => { await Shared.post('/orders/' + id + '/cancel'); go('orders'); }, b); }
  });

  window.extraPages = window.extraPages || {};
  const fail = e => { content.innerHTML = `<div class="error">${E(e.message || 'خطا')}</div>`; };
  extraPages.invoices = () => invoicesList().catch(fail);
  extraPages.orders = () => ordersPage().catch(fail);
})();
