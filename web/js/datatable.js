/* مرحله ۱۷ — جدول داده‌ی مشترک + فرم ایجاد + صفحه‌های CRUD (جایگزین simple()).
   - صفحه‌بندی سمت سرور با limit/offset و هدر X-Total-Count (برای endpointهایی که پشتیبانی می‌کنند)؛
     در غیر این صورت صفحه‌بندی روی کل داده‌ی دریافتی انجام می‌شود.
   - جست‌وجو و مرتب‌سازی فقط روی ردیف‌های بارگذاری‌شده‌ی همین صفحه (بک‌اند هنوز sort/search ندارد) — در UI هم همین نوشته می‌شود.
   - انتخاب ستون (ذخیره در localStorage)، خروجی CSV، Loading/Error/Empty، escape کامل، بدون handler درون‌خطی.
   باید بعد از app.js و sales.js بارگذاری شود (extraPages را نمی‌سازد، فقط تکمیل می‌کند). */
const RAI={edit:'✎',toggle:'⏻',del:'🗑',view:'👁',tg:'⏻',ret:'↩',recv:'📥',hist:'🕘',end:'➜'};

(() => {
  'use strict';
  const { api, apiPage, escapeHtml: E, fa, money, jget, jset } = Shared;
  const SIZES = [10, 25, 50, 100];
  const toast = m => (window.toast ? window.toast(m) : alert(m));
  const csvCell = v => {
    let s = String(v == null ? '' : v);
    if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;           // جلوگیری از formula injection در Excel
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const cmp = (a, b) => {
    const na = Number(a), nb = Number(b);
    if (a !== '' && b !== '' && a != null && b != null && Number.isFinite(na) && Number.isFinite(nb)) return na - nb;
    return String(a ?? '').localeCompare(String(b ?? ''), 'fa');
  };
  const cellText = (f, r) => {
    const v = typeof f.get === 'function' ? f.get(r) : r[f.k];
    if (v == null || v === '') return '—';
    if (f.fmt === 'money') return money(v);
    if (f.fmt === 'bool') return v ? 'بله' : 'خیر';
    if (f.map) return f.map[v] || v;
    return v;
  };

  /* ---------- جدول ---------- */
  function DataTable(host, cfg) {
    const colKey = 'dt:' + cfg.id + ':hidden';
    const st = { page: 0, size: jget('dt:' + cfg.id + ':size', 25), q: '', sort: null, hidden: new Set(jget(colKey, [])), rows: [], total: 0, paged: false, busy: false, err: '' };
    host.innerHTML = `<div class="dt" data-dt="${E(cfg.id)}"></div>`;
    const root = host.firstChild;

    const visible = () => cfg.fields.filter(f => !st.hidden.has(f.k));
    const view = () => {
      let rows = st.rows;
      if (st.q) {
        const q = st.q.toLowerCase();
        rows = rows.filter(r => cfg.fields.some(f => String(cellText(f, r)).toLowerCase().includes(q)));
      }
      if (st.sort) {
        const f = cfg.fields.find(x => x.k === st.sort.k);
        if (f) rows = [...rows].sort((a, b) => cmp(typeof f.get === 'function' ? f.get(a) : a[f.k], typeof f.get === 'function' ? f.get(b) : b[f.k]) * st.sort.dir);
      }
      return rows;
    };
    async function load() {
      st.busy = true; st.err = ''; draw();
      try {
        if (cfg.static) { st.rows = cfg.static; st.total = cfg.static.length; st.paged = false; st.busy = false; draw(); return; }
        const sep = cfg.path.includes('?') ? '&' : '?';
        const res = await apiPage(`${cfg.path}${sep}limit=${cfg.serverLimit === false ? 1000 : st.size}&offset=${cfg.serverLimit === false ? 0 : st.page * st.size}`);
        st.rows = res.rows; st.total = res.total; st.paged = res.paged && cfg.serverLimit !== false;
      } catch (e) { st.err = e.message || 'خطا در دریافت اطلاعات'; st.rows = []; st.total = 0; }
      st.busy = false; draw();
    }
    function draw() {
      const rows = view();
      const clientPaged = !st.paged;
      const shown = clientPaged ? rows.slice(st.page * st.size, (st.page + 1) * st.size) : rows;
      const total = clientPaged ? rows.length : st.total;
      const pages = Math.max(1, Math.ceil(total / st.size));
      const cols = visible();
      const head = cols.map(f => {
        const on = st.sort && st.sort.k === f.k;
        return `<th scope="col" ${on ? `aria-sort="${st.sort.dir > 0 ? 'ascending' : 'descending'}"` : ''}><button type="button" class="dt-sort" data-sort="${E(f.k)}">${E(f.t)}<span aria-hidden="true">${on ? (st.sort.dir > 0 ? ' ▲' : ' ▼') : ''}</span></button></th>`;
      }).join('') + (cfg.rowActions ? '<th></th>' : '');
      let body;
      if (st.busy) body = `<tr><td colspan="${cols.length + 1}" class="dt-state">در حال بارگذاری...</td></tr>`;
      else if (st.err) body = `<tr><td colspan="${cols.length + 1}" class="dt-state dt-err" role="alert">${E(st.err)} <button type="button" data-act="retry">تلاش دوباره</button></td></tr>`;
      else if (!shown.length) body = `<tr><td colspan="${cols.length + 1}" class="dt-state">${st.q ? 'نتیجه‌ای برای این جست‌وجو پیدا نشد.' : E(cfg.empty || 'هنوز موردی ثبت نشده است.')}</td></tr>`;
      else body = shown.map((r, i) => `<tr data-i="${i}">${cols.map(f => `<td>${E(cellText(f, r))}</td>`).join('')}${cfg.rowActions ? `<td class="dt-act">${cfg.rowActions(r).map(a => `<button type="button" data-ra="${E(a.id)}" title="${E(a.label||a.t)}" aria-label="${E(a.label||a.t)}">${RAI[a.id]?`<span aria-hidden="true">${RAI[a.id]}</span> `:''}${E(a.label||a.t)}</button>`).join('')}</td>` : ''}</tr>`).join('');
      root.innerHTML = `<div class="dt-bar">
        <input type="search" class="dt-q" placeholder="جست‌وجو در ردیف‌های این صفحه..." value="${E(st.q)}" aria-label="جست‌وجو">
        <details class="dt-cols"><summary>ستون‌ها</summary><div class="dt-colbox">${cfg.fields.map(f => `<label><input type="checkbox" data-col="${E(f.k)}" ${st.hidden.has(f.k) ? '' : 'checked'}> ${E(f.t)}</label>`).join('')}</div></details>
        <button type="button" data-act="csv">خروجی CSV</button>
        ${cfg.create ? `<button type="button" class="primary" data-act="create">+ ${E(cfg.create.label || 'جدید')}</button>` : ''}
      </div>
      <div class="tablewrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>
      <div class="dt-foot"><span>${fa(total)} ردیف${st.paged ? '' : ''}${st.paged && (st.q || st.sort) ? ' — جست‌وجو/مرتب‌سازی فقط روی همین صفحه' : ''}</span>
        <span class="dt-pg"><button type="button" data-act="prev" ${st.page <= 0 ? 'disabled' : ''}>قبلی</button><span>صفحه ${fa(st.page + 1)} از ${fa(pages)}</span><button type="button" data-act="next" ${st.page + 1 >= pages ? 'disabled' : ''}>بعدی</button>
        <select class="dt-size" aria-label="تعداد در صفحه">${SIZES.map(n => `<option ${n === st.size ? 'selected' : ''}>${n}</option>`).join('')}</select></span></div>`;
      root._shown = shown;
    }
    root.addEventListener('click', e => {
      const b = e.target.closest('button');
      if (!b) { const tr = e.target.closest('tbody tr[data-i]'); if (tr && root.contains(tr) && !e.target.closest('a,input,select,summary')) Detail(cfg, root._shown[+tr.dataset.i]); return; }
      if (!root.contains(b)) return;
      if (b.dataset.sort) { const k = b.dataset.sort; st.sort = st.sort && st.sort.k === k ? (st.sort.dir === 1 ? { k, dir: -1 } : null) : { k, dir: 1 }; draw(); return; }
      if (b.dataset.ra) { const tr = b.closest('tr'); const r = root._shown[+tr.dataset.i]; const a = cfg.rowActions(r).find(x => x.id === b.dataset.ra); if (a) Promise.resolve(a.run(r, api)).then(load).catch(err => toast(err.message)); return; }
      const act = b.dataset.act; if (!act) return;
      if (act === 'prev' && st.page > 0) { st.page--; st.paged ? load() : draw(); }
      else if (act === 'next') { st.page++; st.paged ? load() : draw(); }
      else if (act === 'retry') load();
      else if (act === 'csv') {
        const cols = visible(); const lines = [cols.map(f => csvCell(f.t)).join(',')].concat(view().map(r => cols.map(f => csvCell(cellText(f, r))).join(',')));
        const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob(['﻿' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' })); a.download = cfg.id + '.csv'; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
      } else if (act === 'create') (cfg.create.custom ? cfg.create.custom(cfg.reload || load) : FormDialog(cfg.create, cfg.reload || load));
    });
    root.addEventListener('input', e => {
      if (e.target.classList.contains('dt-q')) { st.q = e.target.value; st.page = 0; const pos = e.target.selectionStart; draw(); const q = root.querySelector('.dt-q'); q.focus(); try { q.setSelectionRange(pos, pos); } catch (_) {} }
    });
    root.addEventListener('change', e => {
      if (e.target.dataset.col) { const k = e.target.dataset.col; e.target.checked ? st.hidden.delete(k) : st.hidden.add(k); if (st.hidden.size >= cfg.fields.length) { st.hidden.delete(k); } jset(colKey, [...st.hidden]); const open = true; draw(); root.querySelector('.dt-cols').open = open; }
      else if (e.target.classList.contains('dt-size')) { st.size = +e.target.value; st.page = 0; jset('dt:' + cfg.id + ':size', st.size); st.paged ? load() : draw(); }
    });
    load();
    return { reload: load };
  }

  /* ---------- فرم ایجاد (مودال) ---------- */
  function FormDialog(spec, done) {
    const back = document.createElement('div'); back.className = 'fd-back';
    const f = (x, i) => {
      const id = 'fd' + i, req = x.req ? ' required' : '';
      const ctl = x.type === 'select'
        ? `<select id="${id}" name="${E(x.k)}"${req}>${(x.options || []).map(o => `<option value="${E(o[0])}"${spec.values && String(spec.values[x.k] ?? '') === String(o[0]) ? ' selected' : ''}>${E(o[1])}</option>`).join('')}</select>`
        : x.type === 'textarea' ? `<textarea id="${id}" name="${E(x.k)}" rows="3"${req}></textarea>`
        : `<input id="${id}" name="${E(x.k)}" type="${x.type === 'number' ? 'number' : x.type === 'date' ? 'date' : x.type === 'password' ? 'password' : 'text'}" ${x.type === 'number' ? 'step="any" inputmode="decimal"' : ''} ${x.dir ? `dir="${x.dir}"` : ''} value="${E((spec.values && spec.values[x.k] != null ? spec.values[x.k] : x.def) ?? '')}"${req}>`;
      return `<div class="fd-f"><label for="${id}">${E(x.t)}${x.req ? ' <b aria-hidden="true">*</b>' : ''}</label>${ctl}</div>`;
    };
    back.innerHTML = `<form class="fd" role="dialog" aria-modal="true" aria-label="${E(spec.title)}"><h3>${E(spec.title)}</h3><div class="fd-grid">${spec.fields.map(f).join('')}</div><p class="fd-err" role="alert" hidden></p><div class="fd-btn"><button type="button" data-x>انصراف</button><button class="primary">ذخیره</button></div></form>`;
    document.body.appendChild(back);
    const form = back.firstChild, err = form.querySelector('.fd-err'), close = () => { back.remove(); document.removeEventListener('keydown', onKey); };
    const onKey = e => { if (e.key === 'Escape') close(); };
    document.addEventListener('keydown', onKey);
    form.querySelector('[data-x]').onclick = close;
    back.addEventListener('mousedown', e => { if (e.target === back) close(); });
    form.querySelector('input,select,textarea')?.focus();
    form.addEventListener('submit', async e => {
      e.preventDefault(); err.hidden = true;
      const body = {};
      for (const x of spec.fields) {
        let v = x.type === 'password' ? form.elements[x.k].value : form.elements[x.k].value.trim();
        if (x.req && v === '') { err.textContent = `«${x.t}» الزامی است.`; err.hidden = false; return; }
        if (v === '') { if (x.nullable) body[x.k] = null; else if (x.type !== 'number' && x.type !== 'date') body[x.k] = ''; continue; }
        if (x.type === 'number') { v = Number(v); if (!Number.isFinite(v)) { err.textContent = `«${x.t}» باید عدد باشد.`; err.hidden = false; return; } if (x.min != null && v < x.min) { err.textContent = `«${x.t}» نباید کمتر از ${x.min} باشد.`; err.hidden = false; return; } }
        body[x.k] = v;
      }
      const btn = form.querySelector('.primary'); btn.disabled = true;
      try { { const pl = spec.map ? spec.map(body) : body; if (spec.method === 'PATCH') await Shared.patch(spec.path, pl); else if (spec.method === 'GET') { const q = new URLSearchParams(Object.entries(pl).filter(([, v]) => v !== '' && v != null)); const res = await Shared.api(spec.path + '?' + q); err.textContent = `قیمت واحد: ${money(res.unit_price)} | جمع: ${money(res.total)} | ${res.reason}`; err.hidden = false; btn.disabled = false; return; } else await Shared.post(spec.path, pl); } close(); toast('ذخیره شد'); done && done(); }
      catch (ex) { err.textContent = ex.message || 'خطا در ذخیره'; err.hidden = false; btn.disabled = false; }
    });
  }

  /* ---------- مودال عمومی، جزئیات ردیف، فرم خرید ---------- */
  function Modal(html, label) {
    const prev = document.activeElement, back = document.createElement('div'); back.className = 'fd-back';
    back.innerHTML = `<div class="fd" role="dialog" aria-modal="true" aria-label="${E(label)}" tabindex="-1">${html}</div>`;
    document.body.appendChild(back);
    const box = back.firstChild;
    const close = () => { back.remove(); document.removeEventListener('keydown', onKey); if (prev && prev.focus) prev.focus(); };
    const onKey = e => {
      if (e.key === 'Escape') close();
      if (e.key === 'Tab') {                                   // تله‌ی فوکوس داخل مودال
        const f = [...box.querySelectorAll('button,input,select,textarea,a[href]')].filter(x => !x.disabled && x.offsetParent !== null);
        if (!f.length) return; const first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener('keydown', onKey);
    back.addEventListener('mousedown', e => { if (e.target === back) close(); });
    (box.querySelector('input,select,textarea') || box).focus();
    return { box, close };
  }
  function Detail(cfg, row) {
    if (!row) return;
    const m = Modal(`<h3>جزئیات</h3><dl class="dt-dl">${cfg.fields.map(f => `<dt>${E(f.t)}</dt><dd>${E(cellText(f, row))}</dd>`).join('')}</dl><div class="fd-btn"><button type="button" data-x class="primary">بستن</button></div>`, 'جزئیات');
    m.box.querySelector('[data-x]').onclick = m.close;
  }
  async function StockDialog(done) {
    let ws = [], ps = [];
    try { [ws, ps] = await Promise.all([Shared.api('/warehouses'), Shared.api('/products?limit=1000')]); } catch (e) { toast(e.message || 'خطا'); return; }
    if (!ws.length) return toast('ابتدا یک انبار تعریف کنید.');
    if (!ps.length) return toast('ابتدا یک کالا تعریف کنید.');
    FormDialog({ title: 'ثبت موجودی کالا', path: '/stock/adjust', fields: [
      { k: 'warehouse_id', t: 'انبار', type: 'select', req: 1, options: ws.map(w => [w.id, w.name]) },
      { k: 'product_id', t: 'کالا', type: 'select', req: 1, options: ps.map(x => [x.id, x.name + ' (' + x.sku + ')']) },
      { k: 'kind', t: 'نوع', type: 'select', options: [['in', 'ورود به انبار'], ['out', 'خروج از انبار']] },
      { k: 'quantity', t: 'تعداد', type: 'number', req: 1, min: 0.0001 },
      { k: 'reference', t: 'توضیح / مرجع', def: 'manual' }],
      map: b => ({ ...b, warehouse_id: Number(b.warehouse_id), product_id: Number(b.product_id) }) }, done);
  }

  async function PurchaseReturnDialog(row, done) {
    let d; try { d = await api('/purchases/' + Number(row.id)); } catch (e) { return toast(e.message); }
    const items = (d.items || []).filter(i => Number(i.quantity) - Number(i.returned_qty || 0) > 0);
    if (!items.length) return toast('همهٔ اقلام این خرید برگشت خورده‌اند.');
    const m = Modal(`<h3>برگشت از خرید ${E(d.number)}</h3><form><div class="tablewrap"><table class="ac-t"><thead><tr><th>کالا</th><th>قابل برگشت</th><th>تعداد برگشتی</th></tr></thead><tbody>${items.map(i => { const left = Number(i.quantity) - Number(i.returned_qty || 0); return `<tr><td>${E(i.product || i.product_id)}</td><td>${E(String(left))}</td><td><input type="number" min="0" max="${left}" step="any" value="0" data-pid="${Number(i.product_id)}" aria-label="تعداد برگشتی ${E(i.product || '')}"></td></tr>`; }).join('')}</tbody></table></div><div class="fd-f"><label>دلیل (اختیاری)<input name="reason"></label></div><p class="fd-err" role="alert" hidden></p><div class="fd-btn"><button type="button" data-x>انصراف</button><button class="primary">ثبت برگشت</button></div></form>`, 'برگشت از خرید');
    const form = m.box.querySelector('form'), err = form.querySelector('.fd-err');
    form.querySelector('[data-x]').onclick = m.close;
    form.onsubmit = async e => {
      e.preventDefault(); err.hidden = true;
      const its = [...form.querySelectorAll('[data-pid]')].map(i => ({ product_id: Number(i.dataset.pid), quantity: Number(i.value) })).filter(i => i.quantity > 0);
      if (!its.length) { err.textContent = 'حداقل یک قلم با تعداد مثبت وارد کنید.'; err.hidden = false; return; }
      try { await Shared.post('/purchases/' + Number(row.id) + '/return', { items: its, reason: form.elements.reason.value.trim() }); m.close(); toast('برگشت ثبت شد'); done && done(); }
      catch (ex) { err.textContent = ex.message || 'خطا'; err.hidden = false; }
    };
  }
  async function EndorseDialog(row, done) {
    let sup; try { sup = await api('/suppliers'); } catch (e) { return toast(e.message); }
    if (!sup.length) return toast('ابتدا تأمین‌کننده تعریف کنید.');
    FormDialog({ title: 'خرج چک ' + row.number, path: '/checks/' + Number(row.id) + '/endorse', fields: [{ k: 'supplier_id', t: 'تأمین‌کننده (گیرندهٔ چک)', type: 'select', req: 1, options: sup.map(x => [x.id, x.name]) }], map: b => ({ supplier_id: Number(b.supplier_id) }) }, done);
  }

  /* تغییر وضعیت چک؛ اگر حساب بانکی تعریف شده باشد و چک هنوز به حسابی وصل نباشد، حساب پرسیده می‌شود (ایداع/وصول دریافتی، وصول پرداختی) */
  async function CheckStatusDialog(row, to, label, done) {
    let accs = []; try { accs = (await api('/bank-accounts')).filter(a => a.active); } catch (_) {}
    const ask = accs.length && !row.bank_account_id && (to === 'cleared' || (to === 'deposited' && row.kind === 'received'));
    if (!ask) {
      if (!confirm(label + '؟')) return;
      try { await Shared.patch('/checks/' + Number(row.id), { status: to }); toast('انجام شد'); done && done(); } catch (e) { toast(e.message); }
      return;
    }
    FormDialog({ title: label + ' — چک ' + row.number, path: '/checks/' + Number(row.id), method: 'PATCH',
      fields: [{ k: 'bank_account_id', t: 'حساب بانکی', type: 'select', nullable: 1, options: [['', '— بدون حساب (بانک عمومی) —']].concat(accs.map(a => [a.id, a.name])) }, { k: 'note', t: 'توضیح' }],
      map: b => ({ status: to, bank_account_id: b.bank_account_id == null || b.bank_account_id === '' ? null : Number(b.bank_account_id), note: b.note || '' }) }, done);
  }
  async function CheckHistoryDialog(row) {
    let h; try { h = await api('/checks/' + Number(row.id) + '/history'); } catch (e) { return toast(e.message); }
    const A = { created: 'ثبت', status: 'تغییر وضعیت', endorse: 'خرج', void_leaf: 'ابطال برگ' };
    const m = Modal(`<h3>تاریخچهٔ چک ${E(row.number)}</h3><div class="tablewrap"><table><thead><tr><th>زمان</th><th>رویداد</th><th>از</th><th>به</th><th>کاربر</th><th>توضیح</th></tr></thead><tbody>${h.length ? h.map(x => `<tr><td>${E(String(x.created_at || '').replace('T', ' ').slice(0, 16))}</td><td>${E(A[x.action] || x.action)}</td><td>${E(CK_ST[x.from_status] || x.from_status || '—')}</td><td>${E(CK_ST[x.to_status] || x.to_status || '—')}</td><td>${E(x.user || '—')}</td><td>${E(x.note || '')}</td></tr>`).join('') : '<tr><td colspan="6">رویدادی ثبت نشده است.</td></tr>'}</tbody></table></div><div class="fd-btn"><button type="button" data-x>بستن</button></div>`, 'تاریخچهٔ چک');
    m.box.querySelector('[data-x]').onclick = m.close;
  }

  async function PayrollView(row) {
    let d; try { d = await api('/payroll/runs/' + Number(row.id)); } catch (e) { return toast(e.message); }
    const m = Modal(`<h3>حقوق ${E(d.period)}</h3><div class="tablewrap"><table class="ac-t"><thead><tr><th>کارمند</th><th>پایه</th><th>پاداش</th><th>روز بدون‌حقوق</th><th>کسر</th><th>خالص</th></tr></thead><tbody>${d.lines.map(l => `<tr><td>${E(l.employee)}</td><td>${E(money(l.base))}</td><td>${E(money(l.bonus))}</td><td>${E(String(l.unpaid_days))}</td><td>${E(money(l.deduction))}</td><td><b>${E(money(l.net))}</b></td></tr>`).join('')}</tbody></table></div><p>جمع خالص: <b>${E(money(d.total_net))}</b></p><div class="fd-btn"><button type="button" data-x>بستن</button></div>`, 'فیش حقوق');
    m.box.querySelector('[data-x]').onclick = m.close;
  }

  async function PurchaseDialog(done) {
    let sup, wh, prod;
    try { [sup, wh, prod] = await Promise.all([api('/suppliers'), api('/warehouses'), api('/products?limit=1000')]); }
    catch (e) { return toast(e.message); }
    if (!sup.length || !wh.length || !prod.length) return toast('ابتدا باید حداقل یک تأمین‌کننده، انبار و کالا ثبت شده باشد.');
    const opt = (a, n) => a.map(x => `<option value="${E(x.id)}">${E(x[n || 'name'])}</option>`).join('');
    const rowHtml = () => `<div class="pu-row"><select name="product" aria-label="کالا">${opt(prod)}</select><input name="qty" type="number" step="any" min="0" placeholder="تعداد" aria-label="تعداد" required><input name="cost" type="number" step="any" min="0" placeholder="بهای واحد" aria-label="بهای واحد" required><input name="disc" type="number" step="any" min="0" placeholder="تخفیف" aria-label="تخفیف"><button type="button" data-rm aria-label="حذف ردیف">✕</button></div>`;
    const m = Modal(`<form><h3>ثبت خرید جدید</h3><div class="fd-grid"><div class="fd-f"><label for="pu-s">تأمین‌کننده</label><select id="pu-s" name="supplier">${opt(sup)}</select></div><div class="fd-f"><label for="pu-w">انبار</label><select id="pu-w" name="wh">${opt(wh)}</select></div><div class="fd-f"><label for="pu-f">هزینه‌ی حمل</label><input id="pu-f" name="freight" type="number" step="any" min="0" value="0"></div></div><h4>اقلام</h4><div id="pu-rows">${rowHtml()}</div><button type="button" data-add>+ ردیف</button><p class="fd-err" role="alert" hidden></p><div class="fd-btn"><button type="button" data-x>انصراف</button><button class="primary">ثبت خرید</button></div></form>`, 'ثبت خرید');
    const form = m.box.querySelector('form'), rows = form.querySelector('#pu-rows'), err = form.querySelector('.fd-err');
    form.querySelector('[data-x]').onclick = m.close;
    form.addEventListener('click', e => {
      if (e.target.closest('[data-add]')) rows.insertAdjacentHTML('beforeend', rowHtml());
      const rm = e.target.closest('[data-rm]'); if (rm && rows.children.length > 1) rm.parentElement.remove();
    });
    form.addEventListener('submit', async e => {
      e.preventDefault(); err.hidden = true;
      const items = [...rows.children].map(r => ({ product_id: Number(r.querySelector('[name=product]').value), quantity: Number(r.querySelector('[name=qty]').value), unit_cost: Number(r.querySelector('[name=cost]').value), discount: Number(r.querySelector('[name=disc]').value || 0) }));
      if (items.some(i => !(i.quantity > 0) || i.unit_cost < 0 || i.discount < 0)) { err.textContent = 'تعداد باید بزرگ‌تر از صفر و مبالغ نامنفی باشند.'; err.hidden = false; return; }
      const btn = form.querySelector('.primary'); btn.disabled = true;
      try { await api('/purchases', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Idempotency-Key': (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random()) }, body: JSON.stringify({ supplier_id: Number(form.elements.supplier.value), warehouse_id: Number(form.elements.wh.value), freight: Number(form.elements.freight.value || 0), items }) }); m.close(); toast('خرید ثبت شد'); done && done(); }
      catch (ex) { err.textContent = ex.message || 'خطا در ثبت'; err.hidden = false; btn.disabled = false; }
    });
  }

  /* ---------- صفحه‌ها ---------- */
  const mount = (title, cfg, extra = '') => {
    content.innerHTML = `<h1>${E(title)}</h1>${extra}<div id="dt-host"></div>`;
    return DataTable(document.getElementById('dt-host'), cfg);
  };
  const CK_KIND = { received: 'دریافتی', issued: 'پرداختی' };
  const CK_ST = { pending: 'در انتظار', deposited: 'به بانک سپرده', returned: 'عودت‌شده', received: 'دریافت‌شده', in_collection: 'در جریان وصول', cleared: 'وصول‌شده', bounced: 'برگشتی', endorsed: 'خرج‌شده', cancelled: 'باطل‌شده' };
  const P = {
    customers: () => mount(pages.customers, { id: 'customers', path: '/customers', empty: 'مشتری‌ای ثبت نشده است.',
      fields: [{ k: 'code', t: 'کد' }, { k: 'name', t: 'نام' }, { k: 'phone', t: 'تلفن' }, { k: 'region', t: 'منطقه' }, { k: 'customer_group', t: 'گروه' }, { k: 'credit_limit', t: 'سقف اعتبار', fmt: 'money' }, { k: 'balance', t: 'مانده', fmt: 'money' }],
      create: { label: 'مشتری جدید', title: 'مشتری جدید', path: '/customers', fields: [{ k: 'code', t: 'کد', req: 1, dir: 'ltr' }, { k: 'name', t: 'نام', req: 1 }, { k: 'phone', t: 'تلفن', dir: 'ltr' }, { k: 'region', t: 'منطقه' }, { k: 'customer_group', t: 'گروه مشتری' }, { k: 'address', t: 'نشانی', type: 'textarea' }, { k: 'credit_limit', t: 'سقف اعتبار', type: 'number', min: 0 }, { k: 'lat', t: 'عرض جغرافیایی', type: 'number', nullable: 1 }, { k: 'lng', t: 'طول جغرافیایی', type: 'number', nullable: 1 }] } }),
    products: async () => {
      let brands = [], cats = [];
      try { [brands, cats] = await Promise.all([Shared.api('/brands'), Shared.api('/categories')]); } catch (_) {}
      const bn = Object.fromEntries(brands.map(b => [b.id, b.name])), cn = Object.fromEntries(cats.map(c => [c.id, c.name]));
      const opt = (list, none) => [['', none]].concat(list.map(x => [x.id, x.name]));
      const nn = v => (v == null || v === '' ? null : Number(v));
      const ref = b => ({ ...b, brand_id: nn(b.brand_id), category_id: nn(b.category_id) });
      const refs = [{ k: 'brand_id', t: 'برند', type: 'select', options: opt(brands, '— بدون برند —'), nullable: 1 }, { k: 'category_id', t: 'دسته', type: 'select', options: opt(cats, '— بدون دسته —'), nullable: 1 }];
      const base = [{ k: 'name', t: 'نام کالا', req: 1 }, { k: 'unit', t: 'واحد', def: 'عدد' }, { k: 'base_price', t: 'قیمت پایه', type: 'number', min: 0 }, { k: 'min_stock', t: 'حداقل موجودی', type: 'number', min: 0 }];
      return mount(pages.products, { id: 'products', path: '/products', empty: 'کالایی ثبت نشده است.',
        fields: [{ k: 'sku', t: 'SKU' }, { k: 'name', t: 'کالا' }, { k: 'brand_id', t: 'برند', map: bn }, { k: 'category_id', t: 'دسته', map: cn }, { k: 'unit', t: 'واحد' }, { k: 'base_price', t: 'قیمت پایه', fmt: 'money' }, { k: 'min_stock', t: 'حداقل موجودی', fmt: 'money' }, { k: 'active', t: 'فعال', fmt: 'bool' }],
        rowActions: r => [{ id: 'edit', label: 'ویرایش', run: row => new Promise(res => FormDialog({ title: 'ویرایش کالا', path: '/products/' + Number(row.id), method: 'PATCH', values: { ...row, brand_id: row.brand_id ?? '', category_id: row.category_id ?? '' }, fields: base.concat(refs), map: ref }, res)) },
          { id: 'toggle', label: r.active === false ? 'فعال‌سازی' : 'غیرفعال‌سازی', run: row => Shared.patch('/products/' + Number(row.id), { active: row.active === false }) }],
        create: { label: 'کالای جدید', title: 'کالای جدید', path: '/products', map: ref, fields: [{ k: 'sku', t: 'SKU', req: 1, dir: 'ltr' }].concat(base, refs) } });
    },
    brands: () => mount(pages.brands, { id: 'brands', path: '/brands', serverLimit: false, empty: 'برندی ثبت نشده است.', fields: [{ k: 'name', t: 'برند' }],
      rowActions: () => [{ id: 'del', label: 'حذف', run: r => confirm('این برند حذف شود؟') ? Shared.api('/brands/' + Number(r.id), { method: 'DELETE' }) : null }],
      create: { label: 'برند جدید', title: 'برند جدید', path: '/brands', fields: [{ k: 'name', t: 'نام برند', req: 1 }] } }),
    categories: () => mount(pages.categories, { id: 'categories', path: '/categories', serverLimit: false, empty: 'دسته‌ای ثبت نشده است.', fields: [{ k: 'name', t: 'دسته' }, { k: 'parent_id', t: 'والد (شناسه)' }],
      rowActions: () => [{ id: 'del', label: 'حذف', run: r => confirm('این دسته حذف شود؟') ? Shared.api('/categories/' + Number(r.id), { method: 'DELETE' }) : null }],
      create: { label: 'دستهٔ جدید', title: 'دستهٔ جدید', path: '/categories', fields: [{ k: 'name', t: 'نام دسته', req: 1 }, { k: 'parent_id', t: 'شناسهٔ دستهٔ والد (اختیاری)', type: 'number', min: 1 }] } }),
    leaves: async () => {
      let emps = []; try { emps = await Shared.api('/employees'); } catch (_) {}
      const en = Object.fromEntries(emps.map(e => [e.id, e.name]));
      const LK = { annual: 'استحقاقی', sick: 'استعلاجی', unpaid: 'بدون حقوق' }, LS = { pending: 'در انتظار', approved: 'تأیید‌شده', rejected: 'ردشده' };
      const dec = (id, label, act) => ({ id, label, run: row => confirm(label + '؟') ? Shared.post('/leaves/' + Number(row.id) + '/' + act, {}) : null });
      return mount(pages.leaves, { id: 'leaves', path: '/leaves', serverLimit: false, empty: 'درخواست مرخصی‌ای ثبت نشده است.',
        fields: [{ k: 'employee_id', t: 'کارمند', map: en }, { k: 'kind', t: 'نوع', map: LK }, { k: 'start_date', t: 'از' }, { k: 'end_date', t: 'تا' }, { k: 'status', t: 'وضعیت', map: LS }, { k: 'reason', t: 'توضیح' }],
        rowActions: r => r.status === 'pending' ? [dec('ok', 'تأیید', 'approve'), dec('no', 'رد', 'reject')] : [],
        create: { label: 'درخواست مرخصی', title: 'درخواست مرخصی', path: '/leaves', map: b => ({ ...b, employee_id: Number(b.employee_id) }), fields: [{ k: 'employee_id', t: 'کارمند', type: 'select', req: 1, options: emps.map(e => [e.id, e.name]) }, { k: 'kind', t: 'نوع', type: 'select', options: Object.entries(LK) }, { k: 'start_date', t: 'از تاریخ', type: 'date', req: 1 }, { k: 'end_date', t: 'تا تاریخ', type: 'date', req: 1 }, { k: 'reason', t: 'توضیح' }] } });
    },
    payroll: () => {
      const PS = { draft: 'پیش‌نویس', posted: 'ثبت‌شده', paid: 'پرداخت‌شده' };
      const act = (id, label, path, method) => ({ id, label, run: row => confirm(label + '؟') ? Shared.api('/payroll/runs/' + Number(row.id) + path, { method: method || 'POST' }) : null });
      return mount(pages.payroll, { id: 'payroll', path: '/payroll/runs', serverLimit: false, empty: 'لیست حقوقی ساخته نشده است.',
        fields: [{ k: 'period', t: 'دوره' }, { k: 'status', t: 'وضعیت', map: PS }, { k: 'total_base', t: 'جمع پایه', fmt: 'money' }, { k: 'total_bonus', t: 'پاداش', fmt: 'money' }, { k: 'total_deduction', t: 'کسورات', fmt: 'money' }, { k: 'total_net', t: 'خالص پرداختی', fmt: 'money' }],
        rowActions: r => [{ id: 'view', label: 'فیش‌ها', run: row => PayrollView(row) }].concat(r.status === 'draft' ? [act('post', 'ثبت سند حقوق', '/post'), act('del', 'حذف', '', 'DELETE')] : r.status === 'posted' ? [act('pay', 'پرداخت حقوق', '/pay')] : []),
        create: { label: 'محاسبهٔ حقوق ماه', title: 'محاسبهٔ حقوق', path: '/payroll/runs', fields: [{ k: 'period', t: 'دوره (YYYY-MM، مثلاً 2026-10)', req: 1, dir: 'ltr' }] } },
        '<p class="mu">حقوق = پایه + پاداش − کسر مرخصی بدون‌حقوقِ تأییدشده (ماه ۳۰ روزه). پس از «ثبت سند» حقوق پرداختنی و پس از «پرداخت» از بانک ثبت می‌شود.</p>');
    },
    pricing: async () => {
      let ps = []; try { ps = await Shared.api('/products?limit=1000'); } catch (_) {}
      const pn = Object.fromEntries(ps.map(x => [x.id, x.name]));
      const tog = r => ({ id: 'tg', label: r.active ? 'غیرفعال' : 'فعال‌سازی', run: row => Shared.patch('/price-rules/' + Number(row.id) + '?active=' + (row.active ? 'false' : 'true'), {}) });
      const del = { id: 'del', label: 'حذف', run: row => confirm('این قانون حذف شود؟') ? Shared.api('/price-rules/' + Number(row.id), { method: 'DELETE' }) : null };
      const quote = '<div class="fd-btn"><button type="button" data-quote>محاسبهٔ قیمت (quote)</button></div>';
      const t = mount(pages.pricing, { id: 'pricing', path: '/price-rules', serverLimit: false, empty: 'قانون قیمتی ثبت نشده است.',
        fields: [{ k: 'product_id', t: 'کالا', map: pn }, { k: 'customer_group', t: 'گروه مشتری' }, { k: 'min_qty', t: 'از تعداد' }, { k: 'price', t: 'قیمت ثابت', fmt: 'money' }, { k: 'discount_percent', t: 'درصد تخفیف' }, { k: 'active', t: 'فعال', fmt: 'bool' }],
        rowActions: r => [tog(r), del],
        create: { label: 'قانون قیمت جدید', title: 'قانون قیمت', path: '/price-rules', map: b => ({ ...b, product_id: Number(b.product_id) }), fields: [{ k: 'product_id', t: 'کالا', type: 'select', req: 1, options: ps.map(x => [x.id, x.name + ' (' + x.sku + ')']) }, { k: 'customer_group', t: 'گروه مشتری (خالی = همه)' }, { k: 'min_qty', t: 'حداقل تعداد (پله‌ای)', type: 'number', min: 0.001, def: '1' }, { k: 'price', t: 'قیمت ثابت (یا درصد تخفیف)', type: 'number', min: 0 }, { k: 'discount_percent', t: 'درصد تخفیف', type: 'number', min: 0 }] } },
        '<p class="mu">برای هر کالا ارزان‌ترین قانونِ معتبر اعمال می‌شود؛ قانون اختصاصی گروه بر عمومی اولویت دارد. قانون با «از تعداد» بزرگ‌تر از ۱ یعنی تخفیف پله‌ای.</p>' + quote);
      content.querySelector('[data-quote]').onclick = () => FormDialog({ title: 'محاسبهٔ قیمت', path: '/pricing/quote', method: 'GET', fields: [{ k: 'product_id', t: 'کالا', type: 'select', req: 1, options: ps.map(x => [x.id, x.name]) }, { k: 'quantity', t: 'تعداد', type: 'number', req: 1, min: 0.001, def: '1' }, { k: 'customer_id', t: 'شناسهٔ مشتری (اختیاری)', type: 'number', min: 1 }] });
      return t;
    },
    transfers: async () => {
      let ws = [], ps = []; try { [ws, ps] = await Promise.all([Shared.api('/warehouses'), Shared.api('/products?limit=1000')]); } catch (_) {}
      const wn = Object.fromEntries(ws.map(w => [w.id, w.name])), pn = Object.fromEntries(ps.map(x => [x.id, x.name]));
      const TS = { in_transit: 'در راه', received: 'دریافت‌شده', cancelled: 'لغوشده' };
      const act = (id, label, path) => ({ id, label, run: row => confirm(label + '؟') ? Shared.post('/stock/transfers/' + Number(row.id) + path, {}) : null });
      return mount(pages.transfers, { id: 'transfers', path: '/stock/transfers', serverLimit: false, empty: 'انتقالی ثبت نشده است.',
        fields: [{ k: 'number', t: 'شماره' }, { k: 'from_warehouse_id', t: 'از انبار', map: wn }, { k: 'to_warehouse_id', t: 'به انبار', map: wn }, { k: 'products', t: 'اقلام' }, { k: 'quantity', t: 'جمع تعداد' }, { k: 'status', t: 'وضعیت', map: TS }],
        rowActions: r => r.status === 'in_transit' ? [act('rcv', 'دریافت در مقصد', '/receive'), act('cx', 'لغو انتقال', '/cancel')] : [],
        create: { label: 'انتقال جدید', title: 'انتقال بین انبارها', path: '/stock/transfers', map: b => ({ ...b, from_warehouse_id: Number(b.from_warehouse_id), to_warehouse_id: Number(b.to_warehouse_id), product_id: Number(b.product_id) }), fields: [{ k: 'from_warehouse_id', t: 'انبار مبدأ', type: 'select', req: 1, options: ws.map(w => [w.id, w.name]) }, { k: 'to_warehouse_id', t: 'انبار مقصد', type: 'select', req: 1, options: ws.map(w => [w.id, w.name]) }, { k: 'product_id', t: 'کالا', type: 'select', req: 1, options: ps.map(x => [x.id, x.name]) }, { k: 'quantity', t: 'تعداد', type: 'number', req: 1, min: 0.001 }, { k: 'note', t: 'توضیح' }] } });
    },
    stock: () => mount(pages.stock, { id: 'stock', path: '/stock', serverLimit: false, empty: 'موجودی‌ای ثبت نشده است. با دکمهٔ «ثبت موجودی» کالاهای تعریف‌شده را وارد انبار کنید تا در سفارش قابل انتخاب شوند.',
      create: { label: 'ثبت موجودی', custom: StockDialog },
      fields: [{ k: 'warehouse', t: 'انبار' }, { k: 'product', t: 'کالا' }, { k: 'quantity', t: 'موجودی', fmt: 'money' }, { k: 'reserved', t: 'رزرو', fmt: 'money' }, { k: 'available', t: 'قابل فروش', fmt: 'money' }] }),
    purchases: () => mount(pages.purchases, { id: 'purchases', path: '/purchases', empty: 'خریدی ثبت نشده است.',
      fields: [{ k: 'number', t: 'شماره' }, { k: 'supplier_id', t: 'تأمین‌کننده (شناسه)' }, { k: 'warehouse_id', t: 'انبار (شناسه)' }, { k: 'status', t: 'وضعیت' }, { k: 'total', t: 'مبلغ', fmt: 'money' }], create: { label: 'خرید جدید', custom: PurchaseDialog },
      rowActions: r => r.status === 'received' ? [{ id: 'ret', label: 'برگشت', run: row => new Promise(res => PurchaseReturnDialog(row, res)) }] : r.status === 'draft' ? [{ id: 'recv', label: 'دریافت کالا', run: row => confirm('کالا به انبار وارد و سند حسابداری ثبت می‌شود. ادامه؟') ? Shared.post('/purchases/' + Number(row.id) + '/receive', {}) : null }] : [] }),
    treasury: async () => {
      let accs = [], books = [];
      try { [accs, books] = await Promise.all([api('/bank-accounts'), api('/chequebooks')]); } catch (_) {}
      const an = Object.fromEntries(accs.map(a => [a.id, a.name]));
      const sel = (rows, none, label) => [['', none]].concat(rows.map(label));
      const stDlg = (id, label, to) => ({ id, label, run: row => new Promise(res => CheckStatusDialog(row, to, label, res)) });
      return mount(pages.treasury, { id: 'checks', path: '/checks', empty: 'چکی ثبت نشده است.',
        fields: [{ k: 'number', t: 'شماره' }, { k: 'kind', t: 'نوع', map: CK_KIND }, { k: 'party', t: 'طرف حساب' }, { k: 'bank', t: 'بانک' }, { k: 'bank_account_id', t: 'حساب بانکی', get: r => an[r.bank_account_id] || '' }, { k: 'amount', t: 'مبلغ', fmt: 'money' }, { k: 'due_date', t: 'سررسید' }, { k: 'status', t: 'وضعیت', map: CK_ST }],
        create: { label: 'چک جدید', title: 'ثبت چک', path: '/checks', map: b => ({ ...b, bank_account_id: b.bank_account_id == null || b.bank_account_id === '' ? null : Number(b.bank_account_id), chequebook_id: b.chequebook_id == null || b.chequebook_id === '' ? null : Number(b.chequebook_id) }),
          fields: [{ k: 'number', t: 'شماره چک (با انتخاب دسته‌چک خالی = برگ بعدی)', dir: 'ltr' }, { k: 'kind', t: 'نوع', type: 'select', options: [['received', 'دریافتی'], ['issued', 'پرداختی']] }, { k: 'amount', t: 'مبلغ', type: 'number', req: 1, min: 0.01 }, { k: 'due_date', t: 'سررسید', type: 'date', req: 1 }, { k: 'bank', t: 'بانک' }, { k: 'party', t: 'طرف حساب' },
            { k: 'chequebook_id', t: 'دسته‌چک (فقط چک پرداختی)', type: 'select', nullable: 1, options: sel(books.filter(b => b.status === 'active'), '— بدون دسته‌چک —', b => [b.id, `${b.bank_account} · ${b.start_no}–${b.end_no} (${b.remaining} برگ)`]) },
            { k: 'bank_account_id', t: 'حساب بانکی (فقط چک پرداختی بدون دسته‌چک)', type: 'select', nullable: 1, options: sel(accs.filter(a => a.active), '— بدون حساب —', a => [a.id, a.name]) },
            { k: 'notes', t: 'توضیحات', type: 'textarea' }] },
        rowActions: r => {
          const hist = { id: 'hist', label: 'تاریخچه', run: row => { CheckHistoryDialog(row); return null; } };
          if (r.status === 'pending') return [stDlg('dep', 'ایداع به بانک', 'deposited'), stDlg('clr', 'وصول', 'cleared'), stDlg('bnc', 'برگشت‌خورده', 'bounced')].concat(r.kind === 'received' ? [{ id: 'end', label: 'خرج چک', run: row => new Promise(res => EndorseDialog(row, res)) }] : []).concat([hist]);
          if (r.status === 'deposited') return [stDlg('clr', 'وصول', 'cleared'), stDlg('bnc', 'برگشت‌خورده', 'bounced'), hist];
          return [hist];
        } });
    },
    hr: () => mount(pages.hr, { id: 'employees', path: '/employees', serverLimit: false, empty: 'کارمندی ثبت نشده است.',
      fields: [{ k: 'name', t: 'کارمند' }, { k: 'position', t: 'سمت' }, { k: 'phone', t: 'تلفن' }, { k: 'salary', t: 'حقوق', fmt: 'money' }],
      create: { label: 'کارمند جدید', title: 'کارمند جدید', path: '/employees', fields: [{ k: 'name', t: 'نام', req: 1 }, { k: 'position', t: 'سمت' }, { k: 'phone', t: 'تلفن', dir: 'ltr' }, { k: 'salary', t: 'حقوق پایه', type: 'number', min: 0 }] } }),
    audit: () => mount(pages.audit, { id: 'audit', path: '/audit', serverLimit: false, empty: 'رویدادی ثبت نشده است.',
      fields: [{ k: 'created_at', t: 'زمان' }, { k: 'action', t: 'عملیات' }, { k: 'entity', t: 'موجودیت' }, { k: 'entity_id', t: 'شناسه' }, { k: 'user_id', t: 'کاربر (شناسه)' }] }, '<p class="mu">آخرین ۱۰۰۰ رویداد؛ این لاگ فقط خواندنی است.</p>'),
    organizations: async () => {
      const d = await api('/organizations');
      const name = id => (d.companies.find(c => c.id === id) || {}).name || '—';
      content.innerHTML = `<h1>${E(pages.organizations)}</h1><div class="card"><h3>گروه: ${E(d.group.name)}</h3><div id="org-c"></div></div><div class="card"><h3>شعب</h3><div id="org-b"></div></div>`;
      DataTable(document.getElementById('org-c'), { id: 'org-companies', path: '/organizations', serverLimit: false, empty: 'شرکتی ثبت نشده است.', static: d.companies, reload: () => P.organizations(),
        fields: [{ k: 'name', t: 'شرکت' }, { k: 'code', t: 'کد' }, { k: 'parent_company_id', t: 'شرکت والد', get: r => r.parent_company_id ? name(r.parent_company_id) : 'ریشه' }],
        create: { label: 'شرکت جدید', title: 'شرکت جدید', path: '/organizations/company', fields: [{ k: 'name', t: 'نام', req: 1 }, { k: 'code', t: 'کد', req: 1, dir: 'ltr' }, { k: 'parent_company_id', t: 'شرکت والد', type: 'select', options: [['', 'بدون والد (ریشه)']].concat(d.companies.map(c => [c.id, c.name])), nullable: 1 }], map: b => ({ ...b, parent_company_id: b.parent_company_id ? Number(b.parent_company_id) : null }) } });
      DataTable(document.getElementById('org-b'), { id: 'org-branches', path: '/organizations', serverLimit: false, empty: 'شعبه‌ای ثبت نشده است.', static: d.branches, reload: () => P.organizations(),
        fields: [{ k: 'name', t: 'شعبه' }, { k: 'company_id', t: 'شرکت', get: r => name(r.company_id) }, { k: 'address', t: 'نشانی' }],
        create: { label: 'شعبه جدید', title: 'شعبه جدید', path: '/organizations/branch', map: b => ({ ...b, company_id: Number(b.company_id) }), fields: [{ k: 'company_id', t: 'شرکت', type: 'select', req: 1, options: d.companies.map(c => [c.id, c.name]) }, { k: 'name', t: 'نام شعبه', req: 1 }, { k: 'address', t: 'نشانی', type: 'textarea' }] } });
    }
  };
  window.extraPages = window.extraPages || {};
  pages.pricing = pages.pricing || 'قیمت‌گذاری'; pages.transfers = pages.transfers || 'انتقال بین انبارها'; pages.leaves = pages.leaves || 'مرخصی'; pages.payroll = pages.payroll || 'حقوق و دستمزد'; pages.brands = pages.brands || 'برندها'; pages.categories = pages.categories || 'دسته‌بندی کالا';
  for (const k of Object.keys(P)) if (!extraPages[k]) extraPages[k] = () => Promise.resolve(P[k]()).catch(e => { content.innerHTML = `<div class="error" role="alert">${E(e.message)}</div>`; });
  window.DataTable = DataTable; window.FormDialog = FormDialog; window.Modal = Modal;
})();
