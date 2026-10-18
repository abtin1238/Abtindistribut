/* مدیریت اسناد و پیوست‌ها: فهرست، آپلود، نسخهٔ جدید، تاریخچه، دانلود با توکن، محدودسازی. ACL در بک‌اند است. */
(()=>{
const E=escapeHtml,FA=v=>Number(v||0).toLocaleString('fa-IR');
const EL={customer:'مشتری',product:'کالا',order:'سفارش',invoice:'فاکتور',purchase:'خرید',supplier:'تأمین‌کننده',delivery:'ماموریت',visit:'ویزیت',employee:'کارمند',check:'چک',payment:'دریافت/پرداخت',contract:'قرارداد'};
const SZ=n=>n>=1048576?FA((n/1048576).toFixed(1))+' MB':FA(Math.max(1,Math.round((n||0)/1024)))+' KB';
const D=s=>s?new Intl.DateTimeFormat('fa-IR-u-ca-persian',{dateStyle:'short',timeStyle:'short'}).format(new Date(s)):'—';
let F={entity:'',entity_id:'',q:''};
pages.documents='اسناد و پیوست‌ها';
const tk=()=>localStorage.getItem('ads_token');
window.fiDownload=async(id,ver,name)=>{try{const r=await fetch('/api/documents/'+id+'/download'+(ver?'?version='+ver:''),{headers:{Authorization:'Bearer '+tk()}});if(!r.ok)throw new Error((await r.json().catch(()=>({}))).detail||'خطا در دانلود');const u=URL.createObjectURL(await r.blob()),a=document.createElement('a');a.href=u;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),2000)}catch(e){alert(e.message)}};
async function up(url,file,qs){const fd=new FormData();fd.append('file',file);const r=await fetch('/api'+url+qs,{method:'POST',headers:{Authorization:'Bearer '+tk()},body:fd}),j=await r.json().catch(()=>({}));if(!r.ok)throw new Error(j.detail||'خطا در آپلود');return j}
window.fiUpload=async()=>{const f=fiFile.files[0];if(!f)return alert('فایلی انتخاب نشده');if(!F.entity||!F.entity_id)return alert('نوع و شناسهٔ رکورد را مشخص کنید');
 try{await up('/documents/upload',f,`?entity=${encodeURIComponent(F.entity)}&entity_id=${+F.entity_id}&restricted=${fiRes.checked}&note=${encodeURIComponent(fiNote.value)}`);documents()}catch(e){alert(e.message)}};
window.fiNewVer=id=>{const i=document.createElement('input');i.type='file';i.onchange=async()=>{const n=prompt('توضیح نسخه (اختیاری):')||'';try{await up(`/documents/${id}/versions`,i.files[0],'?note='+encodeURIComponent(n));fiDetail(id)}catch(e){alert(e.message)}};i.click()};
window.fiToggle=async(id,v)=>{try{await api('/documents/'+id,{method:'PATCH',body:JSON.stringify({restricted:v})});fiDetail(id)}catch(e){alert(e.message)}};
window.fiDel=async id=>{if(!confirm('این سند حذف شود؟ (حذف نرم؛ در سابقه می‌ماند)'))return;try{await api('/documents/'+id,{method:'DELETE'});documents()}catch(e){alert(e.message)}};
window.fiDetail=async id=>{try{const d=await api('/documents/'+id);
 content.innerHTML=`<div class=acc-h><div><h1>${E(d.filename)}</h1><p>${E(EL[d.entity]||d.entity)} #${FA(d.entity_id)} — نسخهٔ ${FA(d.current_version)} — ${SZ(d.size)} ${d.restricted?'— <span class="st rev"><i></i>محدود</span>':''}</p></div><div class=acc-act><button class=btn data-nav=documents onclick="documents()">بازگشت</button><button class="btn pri" onclick="fiDownload(${d.id},0,'${E(d.filename).replace(/'/g,'')}')">دانلود</button><button class=btn onclick="fiNewVer(${d.id})">نسخهٔ جدید</button><button class=btn onclick="fiToggle(${d.id},${!d.restricted})">${d.restricted?'رفع محدودیت':'محدودسازی'}</button><button class=btn onclick="fiDel(${d.id})">حذف</button></div></div>
 <div class=cd><h3>تاریخچهٔ نسخه‌ها</h3><div class=tablewrap><table><thead><tr><th>نسخه</th><th>نام</th><th>حجم</th><th>زمان</th><th>توضیح</th><th>SHA-256</th><th></th></tr></thead><tbody>${d.versions.map(v=>`<tr><td class=num>${FA(v.version)}</td><td>${E(v.filename)}</td><td class=num>${SZ(v.size)}</td><td>${D(v.created_at)}</td><td>${E(v.note||'')}</td><td class="num fi-hash" dir=ltr>${E((v.sha256||'').slice(0,12))}</td><td><button class=btn onclick="fiDownload(${d.id},${v.version},'${E(v.filename).replace(/'/g,'')}')">دانلود</button></td></tr>`).join('')}</tbody></table></div></div>`}catch(e){content.innerHTML=`<div class=error>${E(e.message)}</div>`}};
window.documents=async()=>{const p=new URLSearchParams();['entity','entity_id','q'].forEach(k=>{if(F[k])p.set(k,F[k])});
 try{const r=await api('/documents?'+p);
 content.innerHTML=`<div class=acc-h><div><h1>اسناد و پیوست‌ها</h1><p>دانلود فقط با احراز هویت و بر پایهٔ دسترسی به رکورد مادر انجام می‌شود.</p></div></div>
 <div class=cd><div class=field-grid><label>نوع رکورد<select id=fiEnt><option value="">همه</option>${Object.entries(EL).map(([k,t])=>`<option value=${k} ${F.entity===k?'selected':''}>${t}</option>`).join('')}</select></label><label>شناسهٔ رکورد<input id=fiId type=number min=1 value="${E(F.entity_id)}"></label><label>نام فایل<input id=fiQ value="${E(F.q)}"></label></div><div class=acc-act><button class=btn onclick="fiFilter()">اعمال فیلتر</button></div></div>
 <div class=cd><h3>آپلود (برای نوع و شناسهٔ بالا)</h3><div class=field-grid><label>فایل<input id=fiFile type=file></label><label>توضیح<input id=fiNote maxlength=300></label><label><input id=fiRes type=checkbox> محدود (فقط سازنده و مدیر)</label></div><button class="btn pri" onclick="fiUpload()">آپلود</button></div>
 <div class=cd><div class=tablewrap><table><thead><tr><th>فایل</th><th>رکورد</th><th>نسخه</th><th>حجم</th><th>زمان</th><th></th></tr></thead><tbody>${r.map(d=>`<tr><td>${E(d.filename)}${d.restricted?' <small>(محدود)</small>':''}</td><td>${E(EL[d.entity]||d.entity)} #${FA(d.entity_id)}</td><td class=num>${FA(d.current_version||1)}</td><td class=num>${SZ(d.size)}</td><td>${D(d.created_at)}</td><td><button class=btn onclick="fiDetail(${d.id})">جزئیات</button></td></tr>`).join('')||'<tr><td colspan=6 class=empty>سندی نیست</td></tr>'}</tbody></table></div></div>`}catch(e){content.innerHTML=`<div class=error>${E(e.message)}</div>`}};
window.fiFilter=()=>{F={entity:fiEnt.value,entity_id:fiId.value,q:fiQ.value};documents()};
extraPages.documents=window.documents;
if(!MORE.includes('documents')){MORE.splice(MORE.indexOf('notifications'),0,'documents','search')}
})();
/* پنجرهٔ پیوست‌ها برای هر رکورد (فاکتور، رسید، قرارداد، ...) — از هر صفحه با attachModal(entity,id,title) */
(()=>{
const E=escapeHtml,FA=v=>Number(v||0).toLocaleString('fa-IR');
const SZ=n=>n>=1048576?FA((n/1048576).toFixed(1))+' MB':FA(Math.max(1,Math.round((n||0)/1024)))+' KB';
const tk=()=>localStorage.getItem('ads_token');
const canW=()=>{const ps=(me&&me.user&&me.user.permissions)||[];return ps.includes('*')||ps.includes('files.write')||ps.includes('files.*')};
async function up(url,file,qs){const fd=new FormData();fd.append('file',file);const r=await fetch('/api'+url+qs,{method:'POST',headers:{Authorization:'Bearer '+tk()},body:fd}),j=await r.json().catch(()=>({}));if(!r.ok)throw new Error(j.detail||'خطا در آپلود');return j}
window.attachModal=(entity,id,title,extra)=>{
 const el=document.createElement('div');el.className='ds-modal';el.setAttribute('role','dialog');el.setAttribute('aria-modal','true');el.setAttribute('aria-label','پیوست‌ها');
 el.innerHTML=`<div class="cd ds-modal-card fi-modal"><header><h3>پیوست‌ها — ${E(title)}</h3><button type="button" class=ghost data-x aria-label="بستن">✕</button></header><div data-body><div class=loading>...</div></div></div>`;
 const close=()=>{document.removeEventListener('keydown',key);el.remove()},key=e=>{if(e.key==='Escape')close()};
 el.addEventListener('mousedown',e=>{if(e.target===el)close()});el.querySelector('[data-x]').onclick=close;document.addEventListener('keydown',key);document.body.appendChild(el);
 const body=el.querySelector('[data-body]'),run=async fn=>{try{await fn();await draw()}catch(e){alert(e.message||'خطا')}};
 async function draw(){const rows=await api(`/documents?entity=${encodeURIComponent(entity)}&entity_id=${+id}`);
  body.innerHTML=`${canW()?`<div class=fi-up><input type=file data-f aria-label="فایل"><label><input type=checkbox data-r> محدود</label><button type=button class="btn pri" data-up>آپلود</button></div>`:''}
  <div class=tablewrap><table><thead><tr><th>فایل</th><th>نسخه</th><th>حجم</th><th></th></tr></thead><tbody>${rows.map(d=>`<tr><td>${E(d.filename)}${d.restricted?' <small>(محدود)</small>':''}</td><td class=num>${FA(d.current_version||1)}</td><td class=num>${SZ(d.size)}</td><td class=fi-act><button type=button class=btn data-dl="${d.id}" data-n="${E(d.filename)}">دانلود</button>${canW()?`<button type=button class=btn data-nv="${d.id}">نسخهٔ جدید</button><button type=button class=btn data-rm="${d.id}">حذف</button>`:''}<button type=button class=btn data-hist="${d.id}">تاریخچه</button></td></tr>`).join('')||'<tr><td colspan=4 class=empty>پیوستی ثبت نشده است</td></tr>'}</tbody></table></div>${extra?`<div data-extra>${extra}</div>`:''}`;
  const q=s=>body.querySelector(s);
  if(q('[data-up]'))q('[data-up]').onclick=()=>run(async()=>{const f=q('[data-f]').files[0];if(!f)throw new Error('فایلی انتخاب نشده');await up('/documents/upload',f,`?entity=${encodeURIComponent(entity)}&entity_id=${+id}&restricted=${q('[data-r]').checked}`)});
  body.querySelectorAll('[data-dl]').forEach(b=>b.onclick=()=>fiDownload(b.dataset.dl,0,b.dataset.n));
  body.querySelectorAll('[data-hist]').forEach(b=>b.onclick=()=>{close();fiDetail(+b.dataset.hist)});
  body.querySelectorAll('[data-rm]').forEach(b=>b.onclick=()=>{if(confirm('این پیوست حذف شود؟ (حذف نرم)'))run(()=>api('/documents/'+b.dataset.rm,{method:'DELETE'}))});
  body.querySelectorAll('[data-nv]').forEach(b=>b.onclick=()=>{const i=document.createElement('input');i.type='file';i.onchange=()=>run(()=>up(`/documents/${b.dataset.nv}/versions`,i.files[0],'?note='));i.click()});
  body.querySelectorAll('[data-att]').forEach(b=>b.onclick=()=>{close();attachModal('payment',+b.dataset.att,b.dataset.t)})}
 draw().catch(e=>{body.innerHTML=`<div class=error>${E(e.message)}</div>`})};
/* قراردادها */
const CS={draft:'پیش‌نویس',active:'فعال',expired:'منقضی',cancelled:'لغوشده'};
const JD=s=>s?new Intl.DateTimeFormat('fa-IR-u-ca-persian',{dateStyle:'short'}).format(new Date(s+'T12:00:00Z')):'—';
pages.contracts='قراردادها';
window.contractNew=async()=>{try{const [cu,su]=await Promise.all([api('/customers').catch(()=>[]),api('/suppliers').catch(()=>[])]);
 content.innerHTML=`<div class=acc-h><div><h1>قرارداد جدید</h1></div><div class=acc-act><button class=btn onclick="contractsPage()">بازگشت</button></div></div><form class=cd id=ctf><div class=field-grid><label>عنوان<input name=title required maxlength=200></label><label>مشتری<select name=customer_id><option value="">—</option>${cu.map(c=>`<option value=${+c.id}>${E(c.name)}</option>`).join('')}</select></label><label>تأمین‌کننده<select name=supplier_id><option value="">—</option>${su.map(c=>`<option value=${+c.id}>${E(c.name)}</option>`).join('')}</select></label><label>شروع<input type=date name=start_date></label><label>پایان<input type=date name=end_date></label><label>مبلغ<input type=number name=amount min=0 step=any value=0></label><label>یادداشت<input name=note maxlength=2000></label></div><button class="btn pri" type=submit>ثبت</button></form>`;
 ctf.onsubmit=async e=>{e.preventDefault();const f=new FormData(ctf),b={};for(const[k,v]of f.entries()){if(v!=='')b[k]=['customer_id','supplier_id'].includes(k)?+v:v}
  try{const c=await api('/contracts',{method:'POST',body:JSON.stringify(b)});contractsPage().then(()=>attachModal('contract',c.id,c.number))}catch(er){alert(er.message)}}}catch(e){alert(e.message)}};
window.contractStatus=async(id,st)=>{if(st==='cancelled'&&!confirm('قرارداد لغو شود؟ برگشت‌پذیر نیست.'))return;try{await api('/contracts/'+id,{method:'PATCH',body:JSON.stringify({status:st})});contractsPage()}catch(e){alert(e.message)}};
window.contractsPage=async()=>{try{const r=await api('/contracts');
 content.innerHTML=`<div class=acc-h><div><h1>قراردادها</h1><p>اسناد قرارداد را از ستون «پیوست» ثبت کنید.</p></div><div class=acc-act>${canW()?'<button class="btn pri" onclick="contractNew()">+ قرارداد</button>':''}</div></div><div class=cd><div class=tablewrap><table><thead><tr><th>شماره</th><th>عنوان</th><th>طرف قرارداد</th><th>شروع</th><th>پایان</th><th>مبلغ</th><th>وضعیت</th><th></th></tr></thead><tbody>${r.map(c=>`<tr><td>${E(c.number)}</td><td>${E(c.title)}</td><td>${E(c.party||'—')}</td><td>${JD(c.start_date)}</td><td>${JD(c.end_date)}</td><td class=num>${FA(c.amount)}</td><td>${E(CS[c.status]||c.status)}</td><td class=fi-act><button class=btn onclick="attachModal('contract',${+c.id},'${E(c.number)}')">پیوست</button>${canW()&&c.status==='draft'?`<button class=btn onclick="contractStatus(${+c.id},'active')">فعال‌سازی</button>`:''}${canW()&&['draft','active'].includes(c.status)?`<button class=btn onclick="contractStatus(${+c.id},'cancelled')">لغو</button>`:''}</td></tr>`).join('')||'<tr><td colspan=8 class=empty>قراردادی ثبت نشده است</td></tr>'}</tbody></table></div></div>`}catch(e){content.innerHTML=`<div class=error>${E(e.message)}</div>`}};
extraPages.contracts=window.contractsPage;
if(!MORE.includes('contracts'))MORE.splice(MORE.indexOf('documents')+1,0,'contracts');
/* فاکتور: پیوست‌های فاکتور + رسیدهای آن */
window.invAttach=async id=>{const d=await api('/invoices/'+id),pays=d.payments||[];
 attachModal('invoice',id,d.invoice.number,pays.length?`<h3>رسیدهای دریافت</h3><div class=tablewrap><table><tbody>${pays.map(p=>`<tr><td class=num>${FA(p.amount)}</td><td>${E(p.created_at||'')}</td><td><button type=button class=btn data-att="${+p.id}" data-t="رسید ${FA(p.amount)}">پیوست رسید</button></td></tr>`).join('')}</tbody></table></div>`:'')};
})();
