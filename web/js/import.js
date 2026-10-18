(function(){
const FILES=[];let OV={},LAST=null;
const ENT={products:'کالا و قیمت (+موجودی)',stock:'موجودی انبار',customers:'مشتریان و مانده',suppliers:'تأمین‌کنندگان و مانده'};
const ST={ok:'آماده',error:'خطا',denied:'عدم دسترسی',unrecognized:'تشخیص داده نشد',skipped:'نادیده'};
function fd(commit){const f=new FormData();FILES.forEach(x=>f.append('files',x));f.append('overrides',JSON.stringify(OV));if(commit){f.append('strict',document.getElementById('imp_strict').checked?'true':'false')}return f}
async function run(commit){const out=document.getElementById('imp_out');if(!FILES.length){out.innerHTML='<div class=error>ابتدا فایل را انتخاب کنید</div>';return}
 if(commit&&!confirm('داده‌ها در سیستم ثبت می‌شوند. ادامه می‌دهید؟'))return;
 out.innerHTML='<div class=loading>در حال پردازش...</div>';
 try{const d=await api('/import/'+(commit?'commit':'preview'),{method:'POST',body:fd(commit)});LAST=d;render(d,commit)}catch(e){out.innerHTML=`<div class=error>${esc(e.message)}</div>`}}
function render(d,commit){const out=document.getElementById('imp_out');
 let h=commit?(d.committed?'<div class=card><b>✓ ثبت شد.</b></div>':`<div class=error>${esc(d.message||'ثبت نشد')}</div>`):'<div class=card>پیش‌نمایش (چیزی ثبت نشده است). نگاشت ستون‌ها را بررسی کنید.</div>';
 d.tables.forEach((t,i)=>{const key=t.file+'|'+t.sheet;
  h+=`<div class=card><h3>${esc(t.file)} — ${esc(t.sheet||'')} <small>${esc(ST[t.status]||t.status)}</small></h3>`;
  if(t.message)h+=`<p>${esc(t.message)}</p>`;
  if(t.entity||t.headers){h+=`<p>نوع داده: <select onchange="impOv('${esc(key).replace(/'/g,"\\'")}','entity',this.value)">${Object.entries(ENT).map(([k,v])=>`<option value=${k} ${k===t.entity?'selected':''}>${v}</option>`).join('')}<option value="" ${t.entity?'':'selected'}>—</option></select> سطر سرستون: <input type=number min=1 class="ds-w-sm" value="${t.header_row||1}" onchange="impOv('${esc(key).replace(/'/g,"\\'")}','header_row',this.value)"> <label><input type=checkbox onchange="impOv('${esc(key).replace(/'/g,"\\'")}','skip',this.checked)"> نادیده</label></p>`}
  if(t.mapping)h+='<p>'+t.mapping.map(m=>`<span class=tag>${esc(m.header)} ← <b>${esc(m.label)}</b></span>`).join(' ')+'</p>'+(t.unmapped&&t.unmapped.length?`<p><small>ستون‌های نگاشت‌نشده: ${t.unmapped.map(esc).join('، ')}${t.entity==='products'?' (در مشخصات کالا نگه‌داری می‌شوند)':''}</small></p>`:'');
  if(t.counts)h+=`<p>جدید: <b>${money(t.counts.created)}</b> | به‌روزرسانی: <b>${money(t.counts.updated)}</b> | بدون تغییر: ${money(t.counts.unchanged)} | ردشده: <b>${money(t.error_count)}</b> | ردیف نادیده: ${money(t.skipped)}${t.counts.stock_moves!=null?` | حرکت موجودی: ${money(t.counts.stock_moves)}`:''}${t.counts.balance_adjusted?` | مانده تعدیل‌شده: ${money(t.counts.balance_adjusted)}`:''}</p>`;
  if(t.sample&&t.sample.length)h+=`<details><summary>نمونه ردیف‌ها</summary>${t.sample.map(x=>`<div>#${x.line} ${esc(x.action)} — ${esc(x.text)}</div>`).join('')}</details>`;
  if(t.errors&&t.errors.length)h+=`<details open><summary>خطاها (${money(t.error_count)})</summary>${t.errors.map(x=>`<div class=negative>ردیف ${x.line}: ${esc(x.message)}</div>`).join('')}</details>`;
  h+='</div>'});
 if(!commit)h+='<button class=btn onclick="impRun(true)">ثبت نهایی</button> <label><input type=checkbox id=imp_strict2 onchange="document.getElementById(\'imp_strict\').checked=this.checked"> اگر خطا بود هیچ‌چیز ثبت نشود</label> <button class=btn onclick="impRun(false)">بازبینی دوباره</button>';
 out.innerHTML=h}
window.impOv=(k,f,v)=>{OV[k]=OV[k]||{};OV[k][f]=f==='skip'?!!v:v;if(f==='entity'&&!v)delete OV[k][f]};
window.impRun=run;
window.impPick=e=>{FILES.length=0;[...e.target.files].forEach(f=>FILES.push(f));OV={};document.getElementById('imp_out').innerHTML=''};
window.impDrop=e=>{e.preventDefault();FILES.length=0;[...e.dataTransfer.files].forEach(f=>FILES.push(f));OV={};document.getElementById('imp_names').textContent=FILES.map(f=>f.name).join('، ')};
window.extraPages=window.extraPages||{};
extraPages.import=async()=>{content.innerHTML=`<h1>${pages.import}</h1><div class=card ondragover="event.preventDefault()" ondrop="impDrop(event)"><p>خروجی هلو یا هر نرم‌افزار دیگر (Excel، CSV، DBF، HTML، XML، JSON، ODS) را انتخاب یا رها کنید. نوع داده و ستون‌ها خودکار تشخیص داده می‌شوند: کالا و قیمت، موجودی انبار، مشتریان و تأمین‌کنندگان (با مانده حساب).</p><input type=file multiple aria-label="انتخاب فایل برای ورود اطلاعات" onchange="impPick(event);document.getElementById('imp_names').textContent=[...event.target.files].map(f=>f.name).join('، ')"><span id=imp_names></span><br><br><label><input type=checkbox id=imp_strict> اگر خطا بود هیچ‌چیز ثبت نشود</label> <button class=btn onclick="impRun(false)">پیش‌نمایش</button></div><div id=imp_out></div>`};
})();
