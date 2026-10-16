/* حساب کاربری: منوی پروفایل، تغییر رمز، نشست‌های فعال، خروج. وابسته به Modal (datatable.js) و Shared. */
(() => {
  'use strict';
  const E = Shared.esc, toast = m => (window.toast ? window.toast(m) : alert(m));
  const call = (path, opt) => Shared.api(path, opt);

  async function sessionsHtml() {
    let rows = [];
    try { rows = await call('/auth/sessions'); } catch (_) { return '<p class="mu">فهرست نشست‌ها در دسترس نیست.</p>'; }
    return `<table class="ac-t"><thead><tr><th>شروع</th><th>IP</th><th>دستگاه</th><th></th></tr></thead><tbody>${rows.map(r => `<tr><td>${E(r.created_at ? r.created_at.replace('T', ' ').slice(0, 16) : '—')}</td><td dir="ltr">${E(r.ip || '—')}</td><td>${E((r.user_agent || '—').slice(0, 40))}</td><td>${r.current ? '<b>این نشست</b>' : ''}</td></tr>`).join('')}</tbody></table>`;
  }

  window.accountMenu = async function () {
    const u = (window.me && me.user) || {};
    const m = Modal(`<h3>حساب کاربری</h3><p class="mu">${E(u.name || '')} — ${E(u.username || '')} (${E(u.role || '')})</p>
      <div class="fd-btn ac-btn"><button type="button" data-pw>تغییر رمز عبور</button><button type="button" data-all>بستن نشست‌های دیگر</button><button type="button" class="primary" data-out>خروج</button></div>
      <h4>نشست‌های فعال</h4><div data-s>…</div><div class="fd-btn"><button type="button" data-x>بستن</button></div>`, 'حساب کاربری');
    const box = m.box || document.querySelector('.fd-back:last-of-type .fd');
    const q = s => box.querySelector(s), close = m.close || (() => box.parentNode.remove());
    q('[data-x]').onclick = close;
    q('[data-out]').onclick = () => { close(); window.logout(); };
    q('[data-pw]').onclick = () => { close(); passwordDialog(); };
    q('[data-all]').onclick = async () => { try { const r = await call('/auth/logout-all', { method: 'POST' }); toast(`${r.revoked} نشست بسته شد`); q('[data-s]').innerHTML = await sessionsHtml(); } catch (e) { toast(e.message); } };
    q('[data-s]').innerHTML = await sessionsHtml();
  };

  function passwordDialog() {
    FormDialog({ title: 'تغییر رمز عبور', path: '/auth/change-password', fields: [
      { k: 'old_password', t: 'رمز فعلی', req: 1, type: 'password' },
      { k: 'new_password', t: 'رمز جدید (حداقل ۸ نویسه؛ در production ۱۲)', req: 1, type: 'password' },
      { k: 'repeat', t: 'تکرار رمز جدید', req: 1, type: 'password' }],
      map: b => { if (b.new_password !== b.repeat) throw new Error('تکرار رمز با رمز جدید یکسان نیست'); const { repeat, ...r } = b; return r; } },
      () => toast('رمز تغییر کرد؛ نشست‌های دیگر بسته شدند'));
  }

  /* ---------- دوره‌های مالی و قفل دوره ---------- */
  pages.fiscal = 'دوره‌های مالی';
  const fiscalPage = async () => {
    content.innerHTML = `<h1>${E(pages.fiscal)}</h1><p class="mu">پس از بستن یک دوره، ثبت یا معکوس‌کردن هر سند حسابداری با تاریخ داخل آن دوره (از جمله فاکتور و دریافت/پرداخت خودکار) رد می‌شود.</p><div class="fd-btn"><button type="button" class="primary" data-new>دورهٔ جدید</button></div><div id="fp-host">…</div>`;
    const host = document.getElementById('fp-host');
    const load = async () => {
      let rows = [];
      try { rows = await call('/fiscal/periods'); } catch (e) { host.innerHTML = `<p class="fd-err">${E(e.message)}</p>`; return; }
      host.innerHTML = rows.length ? `<div class="tablewrap"><table class="ac-t"><thead><tr><th>نام</th><th>از</th><th>تا</th><th>وضعیت</th><th></th></tr></thead><tbody>${rows.map(r => `<tr><td>${E(r.name)}</td><td>${E(r.start_date)}</td><td>${E(r.end_date)}</td><td>${r.closed ? '🔒 بسته' : 'باز'}</td><td><button type="button" data-id="${Number(r.id)}" data-act="${r.closed ? 'reopen' : 'close'}">${r.closed ? 'بازگشایی' : 'بستن دوره'}</button></td></tr>`).join('')}</tbody></table></div>` : '<p class="mu">دوره‌ای تعریف نشده است.</p>';
    };
    content.querySelector('[data-new]').onclick = () => FormDialog({ title: 'دورهٔ مالی جدید', path: '/fiscal/periods', fields: [
      { k: 'name', t: 'نام (مثلاً ۱۴۰۵ یا مهر ۱۴۰۵)', req: 1 }, { k: 'start_date', t: 'شروع', type: 'date', req: 1 }, { k: 'end_date', t: 'پایان', type: 'date', req: 1 }] }, load);
    host.onclick = async e => {
      const b = e.target.closest('button[data-act]'); if (!b) return;
      if (b.dataset.act === 'close' && !confirm('با بستن دوره، ثبت سند در این بازه ممکن نخواهد بود. ادامه؟')) return;
      try { await call(`/fiscal/periods/${Number(b.dataset.id)}/${b.dataset.act}`, { method: 'POST' }); toast('انجام شد'); load(); } catch (ex) { toast(ex.message); }
    };
    load();
  };
  if (window.extraPages) extraPages.fiscal = fiscalPage;
})();
