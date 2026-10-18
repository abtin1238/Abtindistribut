/* داشبورد مدیرعامل: همهٔ اعداد از /api/ceo/* (دفتر کل و پایگاه داده)؛ هر کارت با کلیک به گزارش/دفتر کل مربوط می‌رود (Drill-down). */
(()=>{
const E=escapeHtml,N=v=>Number(v||0),UNIT='تومان';
const FA=(v,o)=>N(v).toLocaleString('fa-IR',o);
const cmp=v=>{const a=Math.abs(N(v)),f=x=>x.toLocaleString('fa-IR',{maximumFractionDigits:1});return a>=1e9?[f(N(v)/1e9),'میلیارد']:a>=1e6?[f(N(v)/1e6),'میلیون']:[f(N(v)),'']};
const J=s=>{if(!s)return'—';const d=new Date(String(s).slice(0,10)+'T12:00:00Z');return isNaN(d)?E(s):new Intl.DateTimeFormat('fa-IR-u-ca-persian',{month:'short',day:'numeric',timeZone:'UTC'}).format(d)};
pages.ceo='داشبورد مدیرعامل';
if(!NAV.some(x=>x[0]==='ceo'))NAV.splice(1,0,['ceo','داشبورد مدیرعامل','chart']);
Object.assign(IC,{coins:IC.coins||'M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zM4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6',card:IC.card||'M3 6h18v12H3zM3 10h18M7 15h3',bars:IC.bars||'M6 20V11M12 20V4M18 20v-7'});
let CK={};
function go2(d){if(!d)return;if(d.page)return go(d.page);if(d.report==='general-ledger')return openLedger(d.params.account_code);openReport(d.report,d.params||{})}
function card(key,title,icon,tone,val,sub){const k=CK[key];if(!k)return'';const[a,u]=cmp(val===undefined?k.value:val);return`<button class="cd kpi ceo-kpi" data-d="${E(key)}"><header><small>${E(title)}</small><span class="ic2 ${tone}">${ic(icon)}</span></header><div class="v num">${a}<span>${u} ${UNIT}</span></div>${sub||''}</button>`}
function cnt(key,title,icon,tone){const k=CK[key];if(!k)return'';return`<button class="cd kpi ceo-kpi" data-d="${E(key)}"><header><small>${E(title)}</small><span class="ic2 ${tone}">${ic(icon)}</span></header><div class="v num">${FA(k.value)}</div></button>`}
function line(series){
 const W=640,H=200,L=56,R=12,T=12,B=26,mx=Math.max(1,...series.map(x=>N(x.total))),n=series.length,X=i=>L+(n>1?i*(W-L-R)/(n-1):0),Y=v=>T+(H-T-B)*(1-N(v)/mx),pts=series.map((x,i)=>[X(i),Y(x.total)]);
 if(series.every(x=>!N(x.total)))return'<div class=empty>در این بازه فروشی ثبت نشده است.</div>';
 const step=Math.ceil(n/7);
 return`<svg class="chart ceo-chart" viewBox="0 0 ${W} ${H}" role=img aria-label="روند فروش روزانه">${[0,1,2,3].map(k=>{const v=mx*k/3,y=Y(v);return`<line class=gl x1=${L} x2=${W-R} y1=${y} y2=${y} /><text x=${L-6} y=${y+4} text-anchor=end>${cmp(v).join(' ')}</text>`}).join('')}
 ${series.map((x,i)=>i%step?'':`<text x=${X(i)} y=${H-6} text-anchor=middle>${J(x.day)}</text>`).join('')}
 <polyline class=ceo-line points="${pts.map(p=>p.join(',')).join(' ')}" fill=none stroke-width=2.5 />${pts.map((p,i)=>`<circle class=ceo-dot cx=${p[0]} cy=${p[1]} r=3><title>${J(series[i].day)}: ${FA(series[i].total)} ${UNIT}</title></circle>`).join('')}</svg>`}
const list=(rows,cols)=>`<div class=tablewrap><table><thead><tr>${cols.map(c=>`<th>${c[1]}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${cols.map(c=>`<td class=num>${c[2]?c[2](r[c[0]],r):E(r[c[0]]??'—')}</td>`).join('')}</tr>`).join('')||`<tr><td colspan=${cols.length} class=empty>داده‌ای نیست</td></tr>`}</tbody></table></div>`;
const M=v=>FA(v),P=v=>v==null?'—':FA(v,{maximumFractionDigits:1})+'٪';
const prog=(v,max)=>`<progress max=${Math.max(N(max),1)} value="${Math.min(N(v),Math.max(N(max),1))}"></progress>`;
function checks(c){const L={overdue:'سررسیدگذشته',d7:'تا ۷ روز',d30:'۸ تا ۳۰ روز',later:'بعد از ۳۰ روز'};
 return list(Object.keys(L).map(k=>({b:L[k],ra:c.received[k].amount,rc:c.received[k].count,pa:c.paid[k].amount,pc:c.paid[k].count,k})),[['b','سررسید'],['rc','دریافتی (تعداد)',v=>FA(v)],['ra','دریافتی (مبلغ)',M],['pc','پرداختی (تعداد)',v=>FA(v)],['pa','پرداختی (مبلغ)',M]])}
function holdingTable(h){
 const cs=h.companies,K=[['sales_month','فروش ماه'],['gross_profit_month','سود ناخالص ماه'],['receivables','بدهی مشتریان'],['payables','بدهی به تأمین‌کنندگان'],['cash','نقد و بانک'],['stock_value','ارزش موجودی']];
 const v=(c,k)=>c.kpis[k]?M(c.kpis[k].value):'—';
 return `<div class=tablewrap><table><thead><tr><th>شرکت</th>${K.map(x=>`<th>${x[1]}</th>`).join('')}</tr></thead><tbody>${cs.map(c=>`<tr class="${c.current?'rp-cur':''}"><td>${E(c.name)}${c.current?' <small>(جاری)</small>':''}</td>${K.map(x=>`<td class=num>${v(c,x[0])}</td>`).join('')}</tr>`).join('')}<tr class=rp-total><td>جمع تجمیعی</td>${K.map(x=>`<td class=num>${h.consolidated[x[0]]!==undefined?M(h.consolidated[x[0]]):'—'}</td>`).join('')}</tr></tbody></table></div>${h.warnings.map(w=>`<p class=rp-note>${E(w)}</p>`).join('')}`}
function recon(r){return`<div class=tablewrap><table><thead><tr><th>بررسی</th><th>مقدار اول</th><th>مقدار دوم</th><th>اختلاف</th><th>وضعیت</th></tr></thead><tbody>${r.checks.map(c=>`<tr><td>${E(c.name)}${c.note?`<small class=rp-err>${E(c.note)}</small>`:''}</td><td class=num>${M(c.a)}</td><td class=num>${M(c.b)}</td><td class=num>${M(c.diff)}</td><td><span class="st ${c.ok?'':'rev'}"><i></i>${c.ok?'منطبق':'اختلاف'}</span></td></tr>`).join('')}</tbody></table></div>`}
extraPages.ceo=async()=>{
 const g=p=>api(p).catch(e=>({__err:e.message}));
 const days=+(window.__ceoDays||30),[sm,tr,ho,rc]=await Promise.all([g('/ceo/summary'),g('/ceo/trend?days='+days),g('/ceo/holding'),g('/ceo/reconcile')]);
 if(sm.__err){content.innerHTML=`<div class=error>${E(sm.__err)}</div>`;return}
 CK=sm.kpis;const T=sm.tops||{},S=sm.staff||{},k=CK;
 const fc=k.liquidity?k.liquidity.forecast:[];
 content.innerHTML=`<div class=acc-h><div><h1>داشبورد مدیرعامل</h1><p>همهٔ اعداد از دفتر کل و پایگاه داده؛ با کلیک روی هر کارت به گزارش و سند مربوط بروید.</p></div><div class=acc-act><button class=btn data-nav=reports>گزارش‌ها</button></div></div>
 <div class="kpis ceo-kpis">${card('sales_today','فروش امروز','trend','g')}${card('sales_month','فروش ماه','bars','b')}${card('gross_profit_month','سود ناخالص ماه','coins','t',undefined,k.gross_profit_month?`<span class=chg>حاشیه ${P(k.gross_profit_month.margin_percent)}${k.gross_profit_month.uncosted_lines?` — ${FA(k.gross_profit_month.uncosted_lines)} سطر بدون بها`:''}</span>`:'')}${card('receivables','بدهی مشتریان','alert','r')}
 ${card('cash','نقد و بانک','wallet','t',undefined,k.cash?`<span class=chg>صندوق ${M(k.cash.cash)} — بانک ${M(k.cash.bank)}</span>`:'')}${card('payables','بدهی به تأمین‌کنندگان','card','r')}${card('stock_value','ارزش موجودی (بر پایه بها)','box','b',undefined,k.stock_value&&k.stock_value.unvalued_products?`<span class=chg>${FA(k.stock_value.unvalued_products)} کالا بدون بها</span>`:'')}${cnt('low_stock','کالای کم‌موجودی','alert','o')}
 ${card('payments_today','دریافت امروز','wallet','g')}${cnt('orders_today','سفارش امروز','cart','b')}${cnt('customers','مشتریان فعال','users','o')}${cnt('active_deliveries','ماموریت در جریان','truck','t')}</div>
 <div class=ceo-g><section class=cd><header><b>روند فروش</b><select id=ceo-days>${[7,30,90].map(d=>`<option value=${d} ${d===days?'selected':''}>${FA(d)} روز اخیر</option>`).join('')}</select></header>${tr.__err?`<div class=error>${E(tr.__err)}</div>`:line(tr.series)}</section>
 <section class=cd><header><b>نقدینگی و پیش‌بینی</b></header>${k.liquidity?`<p class=ceo-big>${M(k.liquidity.cash_now)} <small>${UNIT} نقد و بانک</small></p>${list(fc,[['days','افق',v=>FA(v)+' روز'],['inflow','چک دریافتی',M],['outflow','چک پرداختی',M],['projected','پیش‌بینی نقد',M]])}<p class=rp-note>${E(k.liquidity.note)}</p>`:'<div class=empty>دسترسی مالی ندارید</div>'}</section></div>
 <div class=ceo-g><section class=cd><header><b>چک‌ها بر اساس سررسید</b><button class=btn data-nav=treasury>خزانه و چک</button></header>${k.checks?checks(k.checks):'<div class=empty>دسترسی مالی ندارید</div>'}</section>
 <section class=cd><header><b>برترین کالاها (ماه جاری)</b></header>${list(T.product||[],[['name','کالا'],['net','فروش خالص',M],['share','سهم',P]])}<header class=rp-sub><b>برترین مشتریان</b></header>${list(T.customer||[],[['name','مشتری'],['net','فروش خالص',M],['share','سهم',P]])}</section></div>
 <div class=ceo-g><section class=cd><header><b>عملکرد کارکنان</b><button class=btn data-open=visitors>جزئیات بازاریاب‌ها</button></header>${list(S.targets||[],[['user_name','فروشنده'],['actual','فروش ماه',M],['sales_target','هدف',v=>v?M(v):'—'],['attainment_percent','تحقق',(v,r)=>v==null?'—':prog(r.actual,r.sales_target)+' '+P(v)],['commission','پورسانت',M]])}${S.visitors?list(S.visitors,[['name','بازاریاب'],['visits','ویزیت',v=>FA(v)],['conversion','تبدیل',P],['out_of_range','خارج از شعاع',v=>FA(v)]]):''}</section>
 <section class=cd><header><b>مأمورین پخش</b><button class=btn data-open=drivers>جزئیات</button></header>${list(S.drivers||[],[['name','مأمور'],['delivered','تحویل',v=>FA(v)],['failed','ناموفق',v=>FA(v)],['success_rate','موفقیت',P],['avg_minutes','میانگین (دقیقه)',v=>v==null?'—':FA(v,{maximumFractionDigits:0})]])}</section></div>
 <section class=cd><header><b>مقایسه شرکت‌های هلدینگ و تجمیع</b></header>${ho.__err?`<div class=empty>${E(ho.__err)}</div>`:holdingTable(ho)}</section>
 <section class="cd ceo-rec"><header><b>تطبیق عددها با دفتر کل</b>${rc.__err?'':`<span class="st ${rc.all_ok?'':'rev'}"><i></i>${rc.all_ok?'همه منطبق':'اختلاف دارد'}</span>`}</header>${rc.__err?`<div class=empty>${E(rc.__err)}</div>`:recon(rc)}</section>`;
 content.querySelectorAll('[data-d]').forEach(b=>b.onclick=()=>go2((CK[b.dataset.d]||{}).drill));
 content.querySelectorAll('[data-nav]').forEach(b=>b.onclick=()=>go(b.dataset.nav));
 content.querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>openReport(b.dataset.open,{start:sm.month_start,end:sm.date}));
 const sel=document.getElementById('ceo-days');if(sel)sel.onchange=()=>{window.__ceoDays=+sel.value;extraPages.ceo()};
};
})();
