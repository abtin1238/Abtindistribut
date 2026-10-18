function plainNote(h){const d=document.createElement('div');d.innerHTML=String(h||'').replace(/<\/(p|div|li|h\d)>|<br\s*\/?>/gi,'\n');return (d.textContent||'').trim()}
(function(){
const q=new URLSearchParams(location.search),id=parseInt(q.get('id'),10),sheet=document.getElementById('sheet');
const esc=Shared.esc;
const fa=x=>Shared.fa(x,{maximumFractionDigits:2});
const dt=x=>x?new Date(x.endsWith('Z')||/[+-]\d\d:?\d\d$/.test(x)?x:x+'Z').toLocaleDateString('fa-IR-u-ca-persian'):'';
const ST={open:['پرداخت‌نشده','open'],partial:['پرداخت جزئی',''],paid:['پرداخت‌شده','paid'],cancelled:['باطل‌شده','cancelled']};
document.getElementById('print').onclick=()=>window.print();
document.getElementById('back').onclick=()=>history.length>1?history.back():location.href='/';
function fail(t){sheet.innerHTML='<p class="state err">'+esc(t)+'</p>'}
async function load(){
 const token=Shared.jget('ads_token',null)||localStorage.getItem('ads_token');
 if(!id)return fail('شناسه فاکتور نامعتبر است');
 if(!token)return fail('ابتدا وارد سیستم شوید');
 const r=await fetch('/api/invoices/'+id,{headers:{Authorization:'Bearer '+token}});
 const d=await r.json().catch(()=>({}));
 if(!r.ok)return fail(d.detail||'خطا در دریافت فاکتور');
 render(d);
}
function render(d){
 const i=d.invoice,c=d.customer,co=d.company,b=co.brand||{},st=ST[i.status]||[i.status,''];
 Tokens.set({'--ac':/^#[0-9a-fA-F]{6}$/.test(b.color||'')?b.color:Tokens.DEFAULT.color});
 const logo=b.logo_url?'<img class="logo" alt="" src="'+esc(b.logo_url)+'">':'<div class="logo">لوگو</div>';
 const rows=d.lines.map((l,n)=>'<tr><td>'+fa(n+1)+'</td><td>'+esc(l.description)+'</td><td>'+fa(l.quantity)+' '+esc(l.unit)+'</td><td class="n">'+fa(l.unit_price)+'</td><td class="n">'+fa(l.discount)+'</td><td class="n">'+fa(l.line_total)+'</td></tr>').join('');
 const ret=Number(i.returned)>0?'<tr><td class="mu">برگشت از فروش</td><td class="n">-'+fa(i.returned)+'</td></tr>':'';
 const tax=Number(i.tax)>0?'<tr><td class="mu">مالیات ارزش افزوده</td><td class="n">'+fa(i.tax)+'</td></tr>':'';
 const ship=Number(i.shipping)>0?'<tr><td class="mu">هزینه حمل</td><td class="n">'+fa(i.shipping)+'</td></tr>':'';
 const pays=d.payments.length?'<div class="mu">پرداخت‌ها: '+d.payments.map(p=>fa(p.amount)+' ('+esc(({cash:'نقد',card:'کارت',transfer:'حواله',check:'چک'})[p.method]||p.method)+')').join('، ')+'</div>':'';
 document.title='فاکتور '+i.number;
 sheet.innerHTML='<div class="head"><div class="brand">'+logo+'<div><b>'+esc(b.name||co.name)+'</b><div class="mu">'+esc(b.tagline||'')+' '+esc(co.code)+'</div></div></div>'
 +'<div class="title"><b>فاکتور فروش</b><div class="mu">شماره '+esc(i.number)+'</div><div class="mu">تاریخ '+esc(dt(i.issued_at))+'</div></div></div>'
 +'<div class="parties"><div class="box"><span class="mu">خریدار</span><b>'+esc(c.name)+'</b><span class="mu">کد '+esc(c.code)+(c.customer_group?' · گروه '+esc(c.customer_group):'')+(c.region?' · '+esc(c.region):'')+'</span><div class="mu">'+esc(c.address)+' '+esc(c.phone)+'</div></div>'
 +'<div class="box"><span class="mu">فروشنده / انبار</span><b>'+esc(d.seller)+'</b><span class="mu">'+esc(d.warehouse)+' · سفارش '+esc(d.order_number)+'</span></div></div>'
 +'<table><thead><tr><th>ردیف</th><th>شرح کالا</th><th>تعداد</th><th>قیمت واحد</th><th>تخفیف</th><th>مبلغ</th></tr></thead><tbody>'+rows+'</tbody></table>'
 +'<div class="foot"><div><span class="badge '+st[1]+'">'+esc(st[0])+'</span><div class="mu ds-status-line">پرداخت‌شده '+fa(i.paid)+(Number(i.returned)>0?' · برگشتی '+fa(i.returned):'')+' · مانده '+fa(Math.max(0,Number(d.remaining)))+(Number(d.remaining)<0?' (بستانکار '+fa(-Number(d.remaining))+')':'')+'</div>'+pays+'</div>'
 +'<table class="tot"><tr><td class="mu">جمع اقلام</td><td class="n">'+fa(i.subtotal||i.total)+'</td></tr>'+tax+ship+ret+'<tr class="g"><td>مبلغ قابل پرداخت</td><td class="n">'+fa(Number(i.total)-Number(i.returned||0))+'</td></tr></table></div>'
 +(plainNote(i.note)?'<section class="notes"><b>یادداشت</b><div class="pre-note">'+esc(plainNote(i.note))+'</div></section>':'')
 +(plainNote(i.terms)?'<section class="notes"><b>شرایط و توضیحات</b><div class="pre-note">'+esc(plainNote(i.terms))+'</div></section>':'')
 +'<div class="sign"><span>امضای فروشنده</span><span>امضای خریدار</span></div>';
}
load().catch(e=>fail(e.message||'خطا'));
})();
