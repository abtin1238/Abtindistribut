/* مرحله ۲۰ — حساب بانکی، دسته‌چک، انتقال وجه و سررسید چک‌ها.
   وابسته به Shared، DataTable، FormDialog و Modal (datatable.js)؛ باید بعد از datatable.js بارگذاری شود.
   همه‌ی مقادیر با escape در HTML می‌آیند؛ بدون handler درون‌خطی. */
(() => {
  'use strict';
  const { api, escapeHtml: E, money, fa } = Shared;
  const toast = m => (window.toast ? window.toast(m) : alert(m));
  const nn = v => (v == null || v === '' ? null : Number(v));
  const BK_ST = { active: 'فعال', finished: 'تمام‌شده', cancelled: 'لغوشده' };
  const LEAF = { unused: 'مصرف‌نشده', used: 'مصرف‌شده', void: 'باطل‌شده' };
  const CK_KIND = { received: 'دریافتی', issued: 'پرداختی' };
  const CK_ST = { pending: 'در انتظار', deposited: 'به بانک سپرده', cleared: 'وصول‌شده', bounced: 'برگشتی', endorsed: 'خرج‌شده', cancelled: 'باطل‌شده', returned: 'عودت‌شده' };
  const day = v => (v ? String(v).replace('T', ' ').slice(0, 16) : '—');
  pages.bank = 'حساب بانکی و دسته‌چک';
  let tab = 'accounts';

  const accOptions = (rows, none) => (none ? [['', none]] : []).concat(rows.filter(a => a.active).map(a => [a.id, a.name + (a.account_number ? ' — ' + a.account_number : '')]));

  async function statement(row) {
    let d; try { d = await api('/bank-accounts/' + Number(row.id) + '/statement'); } catch (e) { return toast(e.message); }
    const m = Modal(`<h3>صورت‌حساب ${E(d.account.name)}</h3><p class="mu">مانده ابتدا: ${E(money(d.opening))} — مانده پایان: <b>${E(money(d.closing))}</b></p>
      <div class="tablewrap"><table><thead><tr><th>تاریخ</th><th>سند</th><th>شرح</th><th>بدهکار (واریز)</th><th>بستانکار (برداشت)</th><th>مانده</th></tr></thead><tbody>${d.rows.length ? d.rows.map(r => `<tr><td>${E(day(r.date))}</td><td dir="ltr">${E(r.number)}</td><td>${E(r.description)}</td><td>${E(money(r.debit))}</td><td>${E(money(r.credit))}</td><td>${E(money(r.balance))}</td></tr>`).join('') : '<tr><td colspan="6">گردشی ثبت نشده است.</td></tr>'}</tbody></table></div>
      <div class="fd-btn"><button type="button" data-x>بستن</button></div>`, 'صورت‌حساب بانکی');
    m.box.querySelector('[data-x]').onclick = m.close;
  }

  async function leaves(row) {
    let d; try { d = await api('/chequebooks/' + Number(row.id) + '/leaves'); } catch (e) { return toast(e.message); }
    const m = Modal(`<h3>برگ‌های دسته‌چک ${E(d.book.bank_account)} (${E(String(d.book.start_no))}–${E(String(d.book.end_no))})</h3>
      <div class="tablewrap"><table><thead><tr><th>شماره برگ</th><th>وضعیت برگ</th><th>وضعیت چک</th><th>مبلغ</th><th>سررسید</th><th>طرف حساب</th></tr></thead><tbody>${d.leaves.map(l => `<tr><td dir="ltr">${E(l.number)}</td><td>${E(LEAF[l.state] || l.state)}</td><td>${E(l.status ? (CK_ST[l.status] || l.status) : '—')}</td><td>${l.amount == null ? '—' : E(money(l.amount))}</td><td>${E(l.due_date || '—')}</td><td>${E(l.party || '—')}</td></tr>`).join('')}</tbody></table></div>
      <div class="fd-btn"><button type="button" data-x>بستن</button></div>`, 'برگ‌های دسته‌چک');
    m.box.querySelector('[data-x]').onclick = m.close;
  }

  const accountsTab = async host => {
    const rows = await api('/bank-accounts');
    DataTable(host, { id: 'bank-accounts', path: '/bank-accounts', serverLimit: false, empty: 'حساب بانکی ثبت نشده است.', static: rows, reload: () => go('bank'),
      fields: [{ k: 'name', t: 'حساب' }, { k: 'bank_name', t: 'بانک' }, { k: 'account_number', t: 'شماره حساب' }, { k: 'iban', t: 'شبا' }, { k: 'balance', t: 'مانده (از دفتر)', fmt: 'money' }, { k: 'open_issued', t: 'چک پرداختی باز', fmt: 'money' }, { k: 'open_received', t: 'چک دریافتی ایداع‌شده', fmt: 'money' }, { k: 'projected', t: 'مانده پیش‌بینی', fmt: 'money' }, { k: 'active', t: 'فعال', fmt: 'bool' }],
      create: { label: 'حساب بانکی جدید', title: 'حساب بانکی جدید', path: '/bank-accounts', fields: [{ k: 'name', t: 'عنوان حساب', req: 1 }, { k: 'bank_name', t: 'بانک' }, { k: 'branch', t: 'شعبه' }, { k: 'account_number', t: 'شماره حساب', dir: 'ltr' }, { k: 'iban', t: 'شبا (IR…)', dir: 'ltr' }, { k: 'holder', t: 'صاحب حساب' }, { k: 'opening_balance', t: 'مانده اول دوره', type: 'number', min: 0 }] },
      rowActions: r => [
        { id: 'stmt', label: 'صورت‌حساب', run: row => { statement(row); return null; } },
        { id: 'tog', label: r.active ? 'غیرفعال‌سازی' : 'فعال‌سازی', run: row => confirm((r.active ? 'غیرفعال‌سازی' : 'فعال‌سازی') + ' حساب؟') ? Shared.patch('/bank-accounts/' + Number(row.id), { active: !r.active }) : null }] });
  };

  const booksTab = async host => {
    const [rows, accs] = await Promise.all([api('/chequebooks'), api('/bank-accounts')]);
    DataTable(host, { id: 'chequebooks', path: '/chequebooks', serverLimit: false, empty: 'دسته‌چکی ثبت نشده است.', static: rows, reload: () => go('bank'),
      fields: [{ k: 'bank_account', t: 'حساب' }, { k: 'series', t: 'سری' }, { k: 'start_no', t: 'از شماره' }, { k: 'end_no', t: 'تا شماره' }, { k: 'total', t: 'برگ' }, { k: 'used', t: 'مصرف‌شده' }, { k: 'remaining', t: 'باقی‌مانده' }, { k: 'next_no', t: 'برگ بعدی' }, { k: 'status', t: 'وضعیت', map: BK_ST }],
      create: { label: 'دسته‌چک جدید', title: 'ثبت دسته‌چک', path: '/chequebooks', map: b => ({ ...b, bank_account_id: Number(b.bank_account_id), start_no: Number(b.start_no), end_no: Number(b.end_no) }), fields: [{ k: 'bank_account_id', t: 'حساب بانکی', type: 'select', req: 1, options: accOptions(accs) }, { k: 'series', t: 'سری', dir: 'ltr' }, { k: 'start_no', t: 'شمارهٔ اولین برگ', type: 'number', req: 1, min: 1 }, { k: 'end_no', t: 'شمارهٔ آخرین برگ', type: 'number', req: 1, min: 1 }] },
      rowActions: r => {
        const out = [{ id: 'lv', label: 'برگ‌ها', run: row => { leaves(row); return null; } }];
        if (r.status === 'active') {
          out.push({ id: 'void', label: 'باطل‌کردن برگ', run: row => { const n = prompt('شمارهٔ برگی که باطل می‌شود؟'); return n && n.trim() ? Shared.post('/chequebooks/' + Number(row.id) + '/void-leaf', { number: n.trim() }) : null; } });
          out.push({ id: 'cx', label: 'لغو دسته‌چک', run: row => confirm('با لغو، برگ‌های باقی‌مانده دیگر قابل استفاده نیست. ادامه؟') ? Shared.patch('/chequebooks/' + Number(row.id), { status: 'cancelled' }) : null });
        } else if (r.status === 'cancelled') out.push({ id: 'ac', label: 'فعال‌سازی مجدد', run: row => Shared.patch('/chequebooks/' + Number(row.id), { status: 'active' }) });
        return out;
      } });
  };

  const transferTab = async host => {
    const [accs, journal] = await Promise.all([api('/bank-accounts'), api('/journal')]);
    const rows = journal.filter(e => e.source_type === 'bank_transfer').map(e => ({ id: e.id, number: e.number, created_at: e.created_at, description: e.description, amount: e.debit }));
    const opts = accOptions(accs, 'صندوق');
    DataTable(host, { id: 'bank-transfers', path: '/journal', serverLimit: false, empty: 'انتقال وجهی ثبت نشده است.', static: rows, reload: () => go('bank'),
      fields: [{ k: 'number', t: 'سند' }, { k: 'created_at', t: 'زمان', get: r => day(r.created_at) }, { k: 'description', t: 'شرح' }, { k: 'amount', t: 'مبلغ', fmt: 'money' }],
      create: { label: 'انتقال وجه', title: 'انتقال وجه (صندوق ↔ بانک ↔ بانک)', path: '/bank-transfers', map: b => ({ from_account_id: nn(b.from_account_id), to_account_id: nn(b.to_account_id), amount: Number(b.amount), note: b.note || '' }), fields: [{ k: 'from_account_id', t: 'از', type: 'select', options: opts, nullable: 1 }, { k: 'to_account_id', t: 'به', type: 'select', options: opts.slice().reverse(), nullable: 1 }, { k: 'amount', t: 'مبلغ', type: 'number', req: 1, min: 0.01 }, { k: 'note', t: 'توضیح' }] } });
  };

  const dueTab = async (host, days) => {
    const d = await api('/checks/due?days=' + days);
    host.innerHTML = `<div class="cards"><div class="card">چک دریافتی (تا ${E(fa(days))} روز)<br><b>${E(money(d.received.amount))}</b><br><small>${E(fa(d.received.count))} فقره</small></div><div class="card">چک پرداختی (تا ${E(fa(days))} روز)<br><b>${E(money(d.issued.amount))}</b><br><small>${E(fa(d.issued.count))} فقره</small></div><div class="card">سررسیدگذشته<br><b class="${d.overdue_count ? 'ds-text-danger' : ''}">${E(fa(d.overdue_count))}</b></div></div><div id="due-t"></div>`;
    DataTable(host.querySelector('#due-t'), { id: 'checks-due', path: '/checks/due', serverLimit: false, empty: 'چک بازِ سررسیدنزدیکی نیست.', static: d.rows,
      fields: [{ k: 'number', t: 'شماره' }, { k: 'kind', t: 'نوع', map: CK_KIND }, { k: 'party', t: 'طرف حساب' }, { k: 'bank_account', t: 'حساب' }, { k: 'amount', t: 'مبلغ', fmt: 'money' }, { k: 'due_date', t: 'سررسید' }, { k: 'days_left', t: 'روز مانده', get: r => (r.overdue ? 'گذشته (' + fa(-r.days_left) + ')' : fa(r.days_left)) }, { k: 'status', t: 'وضعیت', map: CK_ST }] });
  };

  extraPages.bank = async () => {
    const T = { accounts: 'حساب‌های بانکی', books: 'دسته‌چک‌ها', transfers: 'انتقال وجه', due: 'سررسید چک‌ها' };
    content.innerHTML = `<h1>${E(pages.bank)}</h1><div class="row" role="tablist">${Object.entries(T).map(([k, v]) => `<button type="button" role="tab" class="nav-item${k === tab ? ' is-active' : ''}" aria-selected="${k === tab}" data-tab="${E(k)}">${E(v)}</button>`).join('')}</div>${tab === 'due' ? '<div class="card"><label>بازه: <select id="due-days"><option value="7">۷ روز</option><option value="30">۳۰ روز</option><option value="90">۹۰ روز</option></select></label></div>' : ''}<div id="bank-host"></div>`;
    content.querySelectorAll('[data-tab]').forEach(b => { b.onclick = () => { tab = b.dataset.tab; go('bank'); }; });
    const host = document.getElementById('bank-host');
    try {
      if (tab === 'accounts') await accountsTab(host);
      else if (tab === 'books') await booksTab(host);
      else if (tab === 'transfers') await transferTab(host);
      else {
        const sel = document.getElementById('due-days'); try { sel.value = sessionStorage.getItem('bank-due-days') || '7'; } catch (_) { sel.value = '7'; }
        sel.onchange = () => { try { sessionStorage.setItem('bank-due-days', sel.value); } catch (_) {} dueTab(host, Number(sel.value)).catch(e => { host.innerHTML = `<div class="error" role="alert">${E(e.message)}</div>`; }); };
        await dueTab(host, Number(sel.value));
      }
    } catch (e) { host.innerHTML = `<div class="error" role="alert">${E(e.message)}</div>`; }
  };
})();
