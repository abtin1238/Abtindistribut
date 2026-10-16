/* صفحهٔ گزارش‌ها: همهٔ محاسبه‌ها در سرور است؛ اینجا فقط فیلتر، نمایش جدول، drill-down و دانلود. بدون style درون‌خطی. */
(()=>{
const E=escapeHtml,N=v=>Number(v||0),FA=(v,o)=>N(v).toLocaleString('fa-IR',o);
const J=s=>{if(!s)return'—';const d=new Date(String(s).slice(0,10)+'T12:00:00Z');return isNaN(d)?E(s):new Intl.DateTimeFormat('fa-IR-u-ca-persian',{year:'numeric',month:'2-digit',day:'2-digit',timeZone:'UTC'}).format(d).replace(/‏/g,'')};
const CELL={money:v=>FA(v),int:v=>FA(v),qty:v=>FA(v,{maximumFractionDigits:2}),pct:v=>FA(v,{maximumFractionDigits:2})+'٪',date:J,datetime:J,text:v=>E(v)};
const show=(v,k)=>v===null||v===undefined||v===''?'—':(CELL[k]||CELL.text)(v);
const ST={queued:'در صف',running:'در حال ساخت',done:'آماده',failed:'ناموفق'};
const SALES_BY={product:'کالا',customer:'مشتری',seller:'فروشنده',region:'منطقه',branch:'شعبه',day:'روز',category:'دسته‌بندی'},INV_KIND={stock:'موجودی و ارزش',low:'کم‌موجودی',dead:'کالای راکد',movement:'گردش کالا'},PROFIT_BY={product:'کالا',customer:'مشتری',seller:'فروشنده',region:'منطقه'};
/* کدام فیلترها برای کدام گزارش معنا دارند */
const USES={sales:['by','user','region','branch'],customers:['user','region','days'],inventory:['kind','days','branch'],visitors:['user'],drivers:['user'],profit:['by'],aging:[],finance:[]};
const R={name:'sales',params:{},table:null,by:''};
const toJ=iso=>{const d=new Date(String(iso).slice(0,10)+'T12:00:00Z'),p=Object.fromEntries(new Intl.DateTimeFormat('fa-IR-u-ca-persian',{year:'numeric',month:'2-digit',day:'2-digit',timeZone:'UTC'}).formatToParts(d).map(x=>[x.type,x.value]));return p.year+'/'+p.month+'/'+p.day};
const opts=(m,v)=>Object.entries(m).map(([k,t])=>`<option value="${E(k)}" ${k===v?'selected':''}>${E(t)}</option>`).join('');
const qs=p=>new URLSearchParams(Object.entries(p).filter(([,v])=>v!==''&&v!=null)).toString();
const $=id=>document.getElementById(id);
function params(){const p={};[['jstart','rp-js'],['jend','rp-je'],['by','rp-by'],['kind','rp-kind'],['days','rp-days'],['region','rp-reg'],['user_id','rp-user'],['branch_id','rp-br']].forEach(([k,id])=>{const el=$(id);if(el&&!el.closest('[hidden]')&&el.value.trim()!=='')p[k]=el.value.trim()});return p}
async function download(path,name){try{const r=await fetch(API+path,{headers:{Authorization:'Bearer '+token}});if(!r.ok){const d=await r.json().catch(()=>({}));throw Error(typeof d.detail==='string'?d.detail:'خروجی ساخته نشد')}const u=URL.createObjectURL(await r.blob()),a=document.createElement('a');a.href=u;a.download=name;a.click();URL.revokeObjectURL(u)}catch(e){alert(e.message)}}
function modal(title,body){const old=$('rpm');if(old)old.remove();const m=document.createElement('div');m.id='rpm';m.className='ds-modal';m.innerHTML=`<div class="cd ds-modal-card rp-modal"><h3>${E(title)}</h3>${body}<div class=acc-act><button class=btn data-close>بستن</button></div></div>`;m.addEventListener('click',e=>{if(e.target===m||e.target.hasAttribute('data-close'))m.remove()});document.body.appendChild(m)}
function table(t,drill){
 const cols=t.columns,rows=t.rows.slice(0,500);
 return `<div class=tablewrap><table><thead><tr>${cols.map(c=>`<th>${E(c.label)}</th>`).join('')}</tr></thead><tbody>${rows.map((r,i)=>`<tr ${drill?`class=rp-row data-i=${i} tabindex=0`:''}>${cols.map(c=>`<td class=num>${show(r[c.key],c.kind)}</td>`).join('')}</tr>`).join('')||`<tr><td colspan=${cols.length} class=empty>داده‌ای برای این فیلتر نیست</td></tr>`}</tbody></table></div>${t.rows.length>500?`<p class=rp-note>فقط ۵۰۰ ردیف اول نمایش داده شد (${FA(t.rows.length)} ردیف)؛ برای همه‌ی ردیف‌ها خروجی Excel بگیرید.</p>`:''}`}
function summary(t){return t.summary.length?`<div class=rp-sum>${t.summary.map(([l,v,k])=>`<div class=rp-chip><small>${E(l)}</small>${v===''?'':`<b class=num>${show(v,k)}</b>`}</div>`).join('')}</div>`:''}
function canDrill(name){return name==='sales'||name==='customers'||name==='aging'}
async function drill(i){
 const t=R.table,row=t.rows[i];if(!row)return;
 try{
  if(R.name==='sales'){const p={...R.params,by:R.by,key:row._key},d=await api('/reports/sales/detail?'+qs(p));modal(`سفارش‌های «${row.name}»`,summary(d)+table(d,false))}
  else{const d=await api('/customers/'+encodeURIComponent(row._key)+'/ledger');modal('ریز حساب '+d.customer.name,`<div class=tablewrap><table><thead><tr><th>شماره سند</th><th>تاریخ</th><th>شرح</th><th>بدهکار</th><th>بستانکار</th><th>مانده</th></tr></thead><tbody>${d.rows.map(x=>`<tr><td>${E(x.number)}</td><td>${J(x.date)}</td><td>${E(x.description)}</td><td class=num>${FA(x.debit)}</td><td class=num>${FA(x.credit)}</td><td class=num>${FA(x.balance)}</td></tr>`).join('')||'<tr><td colspan=6 class=empty>تراکنشی نیست</td></tr>'}</tbody></table></div><p class=num>مانده: <b>${FA(d.balance)}</b></p>`)}
 }catch(e){alert(e.message)}
}
async function run(){
 const box=$('rpres');box.innerHTML='<div class=loading>در حال محاسبه...</div>';R.params=params();R.by=R.params.by||'';
 try{const t=await api('/reports/run/'+R.name+'?'+qs(R.params));R.table=t;box.innerHTML=`<div class=cd><header><b>${E(t.title)}</b></header>${summary(t)}${table(t,canDrill(R.name))}</div>`;
  if(canDrill(R.name)){box.querySelectorAll('.rp-row').forEach(tr=>{tr.addEventListener('click',()=>drill(+tr.dataset.i));tr.addEventListener('keydown',e=>{if(e.key==='Enter')drill(+tr.dataset.i)})})}
 }catch(e){box.innerHTML=`<div class=error>${E(e.message)}</div>`}
}
async function jobs(){
 const box=$('rpjobs');if(!box)return;let js;try{js=await api('/reports/jobs')}catch(e){box.innerHTML=`<div class=error>${E(e.message)}</div>`;return}
 box.innerHTML=`<header><b>خروجی‌های پس‌زمینه</b><button class=btn data-refresh>به‌روزرسانی</button></header>${js.length?`<div class=tablewrap><table><thead><tr><th>گزارش</th><th>قالب</th><th>وضعیت</th><th>زمان</th><th></th></tr></thead><tbody>${js.map(j=>`<tr><td>${E(j.title||j.report)}</td><td>${E(j.fmt)}</td><td><span class="st ${j.status==='done'?'':'rev'}"><i></i>${E(ST[j.status]||j.status)}</span>${j.error?`<small class=rp-err>${E(j.error)}</small>`:''}</td><td>${J(j.created_at)}</td><td>${j.status==='done'?`<button class=btn data-dl="${j.id}" data-name="${E(j.filename)}">دانلود</button>`:''}</td></tr>`).join('')}</tbody></table></div>`:'<div class=empty>هنوز خروجی‌ای نساخته‌اید. برای گزارش‌های بزرگ از «ساخت در پس‌زمینه» استفاده کنید.</div>'}`;
 box.querySelector('[data-refresh]').onclick=jobs;box.querySelectorAll('[data-dl]').forEach(b=>b.onclick=()=>download('/reports/jobs/'+b.dataset.dl+'/download',b.dataset.name));
 if(js.some(j=>j.status==='queued'||j.status==='running'))setTimeout(jobs,2500)
}
async function queue(fmt){try{await api('/reports/jobs',{method:'POST',body:JSON.stringify({report:R.name,format:fmt,params:params()})});jobs()}catch(e){alert(e.message)}}
function syncFilters(){const u=USES[R.name]||[];document.querySelectorAll('[data-f]').forEach(el=>{const f=el.dataset.f,on=u.includes(f)||(f==='range'&&R.name!=='aging'&&R.name!=='finance')||(f==='end'&&R.name==='aging');el.hidden=!on});
 const by=$('rp-by');if(by)by.innerHTML=opts(R.name==='profit'?PROFIT_BY:SALES_BY,by.value)}
window.openReport=(name,p={})=>{R.name=name;R.preset=p;go('reports')};
extraPages.reports=async()=>{
 let cat;try{cat=await api('/reports/catalog')}catch(e){content.innerHTML=`<div class=error>${E(e.message)}</div>`;return}
 if(!cat.reports.some(r=>r.name===R.name)&&cat.reports[0])R.name=cat.reports[0].name;
 let users=[],branches=[];try{users=await api('/users')}catch(_){}try{branches=(await api('/organizations')).branches||[]}catch(_){}
 content.innerHTML=`<div class=acc-h><div><h1>گزارش‌ها</h1><p>گزارش‌های مدیریتی با فیلتر پیشرفته و خروجی Excel / PDF</p></div></div>
 <div class="cd rp-tabs">${cat.reports.map(r=>`<button class="btn rp-tab ${r.name===R.name?'on':''}" data-r="${E(r.name)}">${E(r.title)}</button>`).join('')}</div>
 <div class="cd rp-filters"><label data-f=range>از تاریخ (شمسی)<input id=rp-js placeholder="۱۴۰۵/۰۷/۰۱" dir=ltr maxlength=10></label><label data-f=range>تا تاریخ (شمسی)<input id=rp-je placeholder="۱۴۰۵/۰۷/۳۰" dir=ltr maxlength=10></label> <label data-f=by>مبنا<select id=rp-by></select></label><label data-f=kind>نوع گزارش<select id=rp-kind>${opts(INV_KIND,'stock')}</select></label><label data-f=days>روز (راکد/غیرفعال)<input id=rp-days type=number min=1 max=3650 value=60></label>
 <label data-f=region>منطقه<input id=rp-reg maxlength=60></label>
 <label data-f=user>کاربر<select id=rp-user><option value="">همه</option>${users.map(u=>`<option value=${u.id}>${E(u.name)}</option>`).join('')}</select></label>
 <label data-f=branch>شعبه<select id=rp-br><option value="">همه</option>${branches.map(b=>`<option value=${b.id}>${E(b.name)}</option>`).join('')}</select></label></div>
 <div class="acc-act rp-act"><button class="btn rp-go" data-go>نمایش گزارش</button><button class=btn data-x=xlsx>Excel</button><button class=btn data-x=pdf>PDF</button><button class=btn data-q=xlsx>ساخت Excel در پس‌زمینه</button><button class=btn data-q=pdf>ساخت PDF در پس‌زمینه</button></div>
 <div id=rpres></div><div class="cd rp-jobs" id=rpjobs></div>`;
 syncFilters();
 content.querySelectorAll('[data-r]').forEach(b=>b.onclick=()=>{R.name=b.dataset.r;R.table=null;content.querySelectorAll('.rp-tab').forEach(x=>x.classList.toggle('on',x===b));syncFilters();$('rpres').innerHTML=''});
 content.querySelector('[data-go]').onclick=run;
 content.querySelectorAll('[data-x]').forEach(b=>b.onclick=()=>{const p=params();download('/reports/run/'+R.name+'/export?'+qs({...p,format:b.dataset.x}),R.name+'.'+b.dataset.x)});
 content.querySelectorAll('[data-q]').forEach(b=>b.onclick=()=>queue(b.dataset.q));
 /* پیش‌تنظیم از drill-down داشبورد: تاریخ میلادی به شمسی تبدیل و در فیلترها نشان داده می‌شود */
 const pre=R.preset;R.preset=null;
 if(pre){if(pre.by&&$('rp-by'))$('rp-by').value=pre.by;if(pre.kind)$('rp-kind').value=pre.kind;if(pre.start)$('rp-js').value=toJ(pre.start);if(pre.end)$('rp-je').value=toJ(pre.end);run()}
 jobs();
};
window.openLedger=async code=>{try{const d=await api('/reports/general-ledger?account_code='+encodeURIComponent(code));modal(`دفتر کل — ${d.account.code} ${d.account.name}`,`<div class=tablewrap><table><thead><tr><th>شماره سند</th><th>تاریخ</th><th>شرح</th><th>بدهکار</th><th>بستانکار</th><th>مانده</th></tr></thead><tbody>${d.rows.slice(-200).map(x=>`<tr><td>${E(x.number)}</td><td>${J(x.date)}</td><td>${E(x.description)}</td><td class=num>${FA(x.debit)}</td><td class=num>${FA(x.credit)}</td><td class=num>${FA(x.balance)}</td></tr>`).join('')||'<tr><td colspan=6 class=empty>سندی نیست</td></tr>'}</tbody></table></div><p class=num>مانده پایان: <b>${FA(d.closing)}</b></p>`)}catch(e){alert(e.message)}};
})();
