import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Card, PageHead, StatusBadge, TlItem } from '../../components/ui.jsx';
import Icon from '../../components/Icon.jsx';
import { invoiceApi } from '../../api/invoices.js';

const money = (v) => Number(v || 0).toLocaleString('fa-IR');
const dateFa = (v) => v ? new Date(v).toLocaleDateString('fa-IR') : '—';
const timeFa = (v) => v ? new Date(v).toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' }) : '—';
const pct = (v) => `${Number(v || 0).toLocaleString('fa-IR', { maximumFractionDigits: 2 })}٪`;

function SignaturePad({ value, onChange }) {
  const canvasRef = useRef(null);
  const drawing = useRef(false);
  useEffect(() => {
    const c = canvasRef.current;
    if (!c) return;
    const ctx = c.getContext('2d');
    ctx.clearRect(0, 0, c.width, c.height);
    if (!value) return;
    const img = new Image();
    img.onload = () => ctx.drawImage(img, 0, 0, c.width, c.height);
    img.src = value;
  }, [value]);
  const point = (e) => {
    const c = canvasRef.current, r = c.getBoundingClientRect();
    return { x: (e.clientX - r.left) * c.width / r.width, y: (e.clientY - r.top) * c.height / r.height };
  };
  const start = (e) => { e.currentTarget.setPointerCapture(e.pointerId); drawing.current = true; const p = point(e); const ctx = canvasRef.current.getContext('2d'); ctx.beginPath(); ctx.moveTo(p.x, p.y); };
  const move = (e) => { if (!drawing.current) return; const p = point(e); const ctx = canvasRef.current.getContext('2d'); ctx.lineWidth = 3; ctx.lineCap = 'round'; ctx.strokeStyle = '#155eef'; ctx.lineTo(p.x, p.y); ctx.stroke(); };
  const end = () => { if (!drawing.current) return; drawing.current = false; onChange(canvasRef.current.toDataURL('image/png')); };
  const clear = () => { const c = canvasRef.current; c.getContext('2d').clearRect(0, 0, c.width, c.height); onChange(''); };
  return <div className="signature-wrap"><canvas ref={canvasRef} width="900" height="260" onPointerDown={start} onPointerMove={move} onPointerUp={end} onPointerCancel={end} /><div className="signature-hint">امضای مشتری را با انگشت یا قلم روی صفحه رسم کنید</div><button className="btn btn-ghost btn-sm" type="button" onClick={clear}>پاک کردن امضا</button></div>;
}

function PaymentForm({ invoice, onSaved }) {
  const [method, setMethod] = useState('cash');
  const [amount, setAmount] = useState(String(invoice.balance || ''));
  const [reference, setReference] = useState('');
  const [chequeNumber, setChequeNumber] = useState('');
  const [chequeDate, setChequeDate] = useState('');
  const [chequeBank, setChequeBank] = useState('');
  const [saving, setSaving] = useState(false); const [error, setError] = useState('');
  const submit = async () => {
    setSaving(true); setError('');
    try { await invoiceApi.receivePayment({ invoice: invoice.id, method, amount: Number(amount), reference, cheque_number: chequeNumber, cheque_date: chequeDate || null, cheque_bank: chequeBank }); onSaved(); }
    catch (e) { setError(e.message); } finally { setSaving(false); }
  };
  return <Card title="ثبت دریافت وجه" sub="دریافت واقعی و ثبت رسید مالی"><div className="payment-grid"><div className="field"><label>روش پرداخت</label><select value={method} onChange={e => setMethod(e.target.value)}><option value="cash">نقدی</option><option value="card">کارت</option><option value="transfer">واریز</option><option value="cheque">چک</option></select></div><div className="field"><label>مبلغ</label><input inputMode="numeric" value={amount} onChange={e => setAmount(e.target.value)} /></div>{method !== 'cheque' ? <div className="field"><label>شماره پیگیری / مرجع</label><input value={reference} onChange={e => setReference(e.target.value)} /></div> : <><div className="field"><label>شماره چک</label><input value={chequeNumber} onChange={e => setChequeNumber(e.target.value)} /></div><div className="field"><label>تاریخ چک</label><input type="date" value={chequeDate} onChange={e => setChequeDate(e.target.value)} /></div><div className="field"><label>بانک</label><input value={chequeBank} onChange={e => setChequeBank(e.target.value)} /></div></>}<button className="btn btn-primary" disabled={saving || Number(amount) <= 0} onClick={submit}>{saving ? 'در حال ثبت…' : 'ثبت دریافت و رسید'}</button></div>{error && <div className="form-error">{error}</div>}</Card>;
}

export default function InvoiceDetailPage({ invoiceId }) {
  const [invoice, setInvoice] = useState(null); const [loading, setLoading] = useState(true); const [error, setError] = useState('');
  const [signer, setSigner] = useState(''); const [signature, setSignature] = useState(''); const [signing, setSigning] = useState(false); const [signError, setSignError] = useState('');
  const load = async () => { setLoading(true); setError(''); try { const d = await invoiceApi.get(invoiceId); setInvoice(d); setSigner(d.customer_signature_name || ''); setSignature(d.customer_signature || ''); } catch (e) { setError(e.message); } finally { setLoading(false); } };
  useEffect(() => { load(); }, [invoiceId]);
  const totalPercent = useMemo(() => (invoice?.items || []).reduce((s, i) => s + Number(i.company_discount_percent || 0) + Number(i.offer_percent || 0), 0), [invoice]);
  if (loading) return <div className="card skeleton" style={{ height: 600 }} />;
  if (error) return <Card title="خطا"><div className="form-error">{error}</div><button className="btn btn-primary mt" onClick={load}>تلاش دوباره</button></Card>;
  const sign = async () => { setSigning(true); setSignError(''); try { const d = await invoiceApi.sign(invoice.id, { signature, signer_name: signer }); setInvoice(d); } catch (e) { setSignError(e.message); } finally { setSigning(false); } };
  return <div className="invoice-detail">
    <PageHead title={`فاکتور فروش ${invoice.number}`} sub={`${invoice.company_name || 'شرکت'} · ${invoice.branch_name || 'شعبه'} · ${dateFa(invoice.created_at)}`} actions={<><button className="btn btn-ghost btn-sm" onClick={() => window.print()}><Icon name="print" size={15} /> چاپ</button><button className="btn btn-primary btn-sm" onClick={load}><Icon name="sync" size={15} /> به‌روزرسانی</button></>} />
    <div className="invoice-layout">
      <main>
        <Card className="print-card"><div className="invoice-paper">
          <div className="invoice-header"><div><div className="brand-name">{invoice.company_name || 'نام شرکت'}</div><div className="muted">{invoice.company_address || 'آدرس شرکت ثبت نشده'}{invoice.company_phone ? ` · ${invoice.company_phone}` : ''}</div></div><div className="invoice-title"><h1>فاکتور فروش</h1><b>{invoice.number}</b><div>{dateFa(invoice.created_at)} · {timeFa(invoice.created_at)}</div></div></div>
          <div className="invoice-meta"><div><b>مشتری</b><span>{invoice.customer_name_snapshot || invoice.customer_name}</span><small>کد مشتری: {invoice.customer}</small></div><div><b>بازاریاب</b><span>{invoice.seller_name || '—'}</span><small>فروشنده حقوقی: {invoice.company_name || '—'}</small></div><div><b>شعبه / انبار</b><span>{invoice.branch_name || '—'}</span><small>{invoice.warehouse_name || '—'}</small></div><div><b>آدرس تحویل</b><span>{invoice.customer_address_snapshot || '—'}</span></div></div>
          <div className="table-wrap"><table className="invoice-table"><thead><tr><th>#</th><th>کالا</th><th>تعداد</th><th>قیمت واحد</th><th>درصد شرکت</th><th>درصد آفر / ویزیتور</th><th>تخفیف</th><th>مالیات</th><th>مبلغ نهایی</th></tr></thead><tbody>{(invoice.items || []).map((i, idx) => <tr key={i.id || idx}><td>{idx + 1}</td><td><b>{i.product_name}</b><small>{i.product}</small></td><td>{money(i.qty)}</td><td>{money(i.unit_price)}</td><td>{pct(i.company_discount_percent)}</td><td>{pct(i.offer_percent)}</td><td>{money(i.discount_amount)}</td><td>{money(i.tax_amount)}</td><td><b>{money(i.line_total)}</b></td></tr>)}</tbody></table></div>
          <div className="invoice-bottom"><div className="notes-box"><b>توضیحات</b><p>شرایط پرداخت و توضیحات فاکتور در این بخش نمایش داده می‌شود.</p><div className="signature-mini"><span>امضای مشتری</span>{invoice.customer_signature ? <img src={invoice.customer_signature} alt="امضای مشتری" /> : <em>ثبت نشده</em>}<small>{invoice.customer_signature_name || '—'} · {invoice.customer_signed_at ? `${dateFa(invoice.customer_signed_at)} ${timeFa(invoice.customer_signed_at)}` : '—'}</small></div></div><div className="totals"><div><span>جمع کالاها</span><b>{money(invoice.subtotal)} ریال</b></div><div><span>جمع تخفیف‌ها</span><b>{money(invoice.discount_total)} ریال</b></div><div><span>مالیات</span><b>{money(invoice.tax_total)} ریال</b></div><div className="total"><span>مبلغ نهایی</span><b>{money(invoice.total)} ریال</b></div><div><span>دریافت‌شده</span><b>{money(invoice.paid_total)} ریال</b></div><div><span>مانده</span><b>{money(invoice.balance)} ریال</b></div></div></div>
          <div className="invoice-footer"><span>کد اقتصادی: {invoice.company_economic_code || '—'}</span><span>وضعیت: <StatusBadge status={invoice.status.toUpperCase()} /></span><span>پرداخت: <StatusBadge status={invoice.payment_status === 'paid' ? 'PAID' : invoice.payment_status === 'partial' ? 'PARTIALLY_PAID' : 'UNPAID'} /></span></div>
        </div></Card>
        <Card title="امضای آنلاین مشتری" sub="امضا مستقیماً روی فاکتور ثبت می‌شود"><div className="signature-grid"><div><div className="field"><label>نام و نام خانوادگی امضاکننده</label><input value={signer} onChange={e => setSigner(e.target.value)} placeholder="نام مشتری" /></div><SignaturePad value={signature} onChange={setSignature}/>{signError && <div className="form-error">{signError}</div>}<button className="btn btn-primary mt" disabled={signing || !signature || !signer.trim()} onClick={sign}>{signing ? 'در حال ثبت…' : 'ثبت و تأیید امضای مشتری'}</button></div><div className="signature-info"><Icon name="check" size={22}/><b>ثبت امن تأیید فاکتور</b><p>امضا همراه با نام امضاکننده و زمان ثبت به همین فاکتور متصل می‌شود.</p></div></div></Card>
        <PaymentForm invoice={invoice} onSaved={load}/>
      </main>
      <aside><Card title="وضعیت فاکتور"><div className="invoice-stepper">{(invoice.status_history || []).map((h) => <TlItem key={h.id} icon="check" tint="green" title={h.to_status_label} desc={h.changed_by} time={timeFa(h.created_at)} />)}</div></Card><Card title="درصدهای اعمال‌شده"><div className="percent-summary"><div><span>جمع درصد شرکت</span><b>{pct((invoice.items || []).reduce((s, i) => s + Number(i.company_discount_percent || 0), 0))}</b></div><div><span>جمع درصد آفر / ویزیتور</span><b>{pct((invoice.items || []).reduce((s, i) => s + Number(i.offer_percent || 0), 0))}</b></div><div><span>جمع درصدها در اقلام</span><b>{pct(totalPercent)}</b></div></div></Card><Card title="پرداخت‌های ثبت‌شده">{invoice.payments?.length ? invoice.payments.map(p => <div className="payment-row" key={p.id}><div><b>{money(p.amount)} ریال</b><span>{p.method_label}</span></div><small>{p.method === 'cheque' ? `چک ${p.cheque_number || '—'} · ${p.cheque_date ? dateFa(p.cheque_date) : 'بدون تاریخ'}${p.cheque_bank ? ` · ${p.cheque_bank}` : ''}` : (p.reference || 'بدون مرجع')}</small></div>) : <div className="muted">هنوز پرداختی ثبت نشده است.</div>}</Card></aside>
    </div>
  </div>;
}
