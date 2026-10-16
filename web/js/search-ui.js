/* جستجوی سراسری + جستجوی پیشرفته (فیلتر، مرتب‌سازی، ذخیرهٔ فیلتر). اعتبارسنجی و دسترسی در بک‌اند است. */
(()=>{
const E=escapeHtml,FA=v=>Number(v||0).toLocaleString('fa-IR');
const OPL={eq:'برابر',ne:'نابرابر',contains:'شامل',starts:'شروع با',gt:'بزرگ‌تر',gte:'بزرگ‌تر یا مساوی',lt:'کوچک‌تر',lte:'کوچک‌تر یا مساوی',in:'یکی از',between:'بین',isnull:'خالی'};
let SC=null,ST={entity:'customers',q:'',filters:[],sort:null,order:'desc',page:1};
const cell=(c,v)=>v==null||v===''?'—':c.kind==='money'||c.kind==='qty'?FA(v):c.kind==='bool'?(v?'بله':'خیر'):c.kind==='date'?new Intl.DateTimeFormat('fa-IR-u-ca-persian',{dateStyle:'short'}).format(new Date(v)):E(v);
pages.search='جستجوی پیشرفته';
window.doSearch=async e=>{e.preventDefault();const t=q.value.trim();if(!t)return;content.innerHTML='<div class=loading>در حال جستجو...</div>';
 try{const r=await api('/search/global?q='+encodeURIComponent(t));
  content.innerHTML=`<div class=acc-h><div><h1>نتایج جستجو</h1><p>«${E(t)}»</p></div><div class=acc-act><button class=btn onclick="srAdv()">جستجوی پیشرفته</button></div></div>`+Object.entries(r.results).map(([k,v])=>`<div class=cd><h3>${E(v.label)} (${FA(v.items.length)})</h3>${v.items.map(x=>`<button class="row sr-hit" data-go="${E(v.page)}">${E(x.title)}<small>${E(x.sub||'')}</small></button>`).join('')||'<div class=empty>—</div>'}</div>`).join('')||'<div class=empty>نتیجه‌ای یافت نشد</div>';
  content.querySelectorAll('.sr-hit').forEach(b=>b.onclick=()=>go(b.dataset.go));
 }catch(err){content.innerHTML=`<div class=error>${E(err.message)}</div>`}};
function fRow(f,i){const fs=SC[ST.entity].fields,fd=fs.find(x=>x.name===f.field)||fs[0];
 return`<div class=sr-f><select data-i=${i} data-k=field>${fs.map(x=>`<option value="${E(x.name)}" ${x.name===fd.name?'selected':''}>${E(x.name)}</option>`).join('')}</select><select data-i=${i} data-k=op>${fd.ops.map(o=>`<option value="${o}" ${o===f.op?'selected':''}>${OPL[o]||o}</option>`).join('')}</select><input data-i=${i} data-k=value value="${E(Array.isArray(f.value)?f.value.join(','):f.value??'')}" ${f.op==='isnull'?'disabled':''}><button class=btn data-rm=${i} aria-label="حذف شرط">×</button></div>`}
const val=(f,raw)=>f.op==='in'||f.op==='between'?String(raw).split(',').map(x=>x.trim()).filter(Boolean):f.op==='isnull'?true:raw;
function bind(){
 const $=s=>content.querySelector(s);
 $('#sr-ent').onchange=e=>{ST={entity:e.target.value,q:'',filters:[],sort:null,order:'desc',page:1};srAdv()};
 $('#sr-q').oninput=e=>ST.q=e.target.value;
 content.querySelectorAll('.sr-f [data-i]').forEach(el=>el.onchange=()=>{const f=ST.filters[+el.dataset.i],k=el.dataset.k;if(k==='value')f.value=val(f,el.value);else{f[k]=el.value;if(k==='field'){f.op=SC[ST.entity].fields.find(x=>x.name===el.value).ops[0];f.value=''}if(k==='op'&&el.value==='isnull')f.value=true;srForm()}});
 content.querySelectorAll('[data-rm]').forEach(b=>b.onclick=()=>{ST.filters.splice(+b.dataset.rm,1);srForm()});
 $('#sr-add').onclick=()=>{ST.filters.push({field:SC[ST.entity].fields[0].name,op:SC[ST.entity].fields[0].ops[0],value:''});srForm()};
 $('#sr-go').onclick=()=>{ST.page=1;srRun()};
 $('#sr-save').onclick=async()=>{const n=prompt('نام فیلتر:');if(!n)return;try{await api('/search/saved',{method:'POST',body:JSON.stringify({entity:ST.entity,name:n,query:{q:ST.q,filters:ST.filters,sort:ST.sort,order:ST.order}})});srAdv(true)}catch(e){alert(e.message)}};
 $('#sr-sort').onchange=e=>{ST.sort=e.target.value||null};$('#sr-ord').onchange=e=>ST.order=e.target.value;
}
window.srForm=()=>{content.querySelector('#sr-filters').innerHTML=ST.filters.map(fRow).join('');bind()};
window.srApply=i=>{const s=window.__srSaved[i];ST={...ST,entity:s.entity,q:s.query.q||'',filters:s.query.filters||[],sort:s.query.sort||null,order:s.query.order||'desc',page:1};srAdv(true).then(srRun)};
window.srDel=async id=>{if(!confirm('حذف فیلتر ذخیره‌شده؟'))return;await api('/search/saved/'+id,{method:'DELETE'}).catch(e=>alert(e.message));srAdv(true)};
window.srPage=p=>{ST.page=p;srRun()};
window.srSort=k=>{ST.order=ST.sort===k&&ST.order==='asc'?'desc':'asc';ST.sort=k;srRun()};
window.srRun=async()=>{const box=content.querySelector('#sr-res');box.innerHTML='<div class=loading>...</div>';
 try{const r=await api('/search/advanced',{method:'POST',body:JSON.stringify({entity:ST.entity,q:ST.q,filters:ST.filters,sort:ST.sort,order:ST.order,page:ST.page,page_size:25})}),pg=Math.max(1,Math.ceil(r.total/25));
  box.innerHTML=`<p class=rp-note>${FA(r.total)} نتیجه</p><div class=tablewrap><table><thead><tr>${r.columns.map(c=>`<th><button class="btn sr-th" onclick="srSort('${E(c.key)}')">${E(c.label)}</button></th>`).join('')}</tr></thead><tbody>${r.rows.map(x=>`<tr>${r.columns.map(c=>`<td class=num>${cell(c,x[c.key])}</td>`).join('')}</tr>`).join('')||`<tr><td colspan=${r.columns.length} class=empty>نتیجه‌ای نیست</td></tr>`}</tbody></table></div><div class=acc-act><button class=btn ${ST.page<=1?'disabled':''} onclick="srPage(${ST.page-1})">قبلی</button><span>${FA(ST.page)} / ${FA(pg)}</span><button class=btn ${ST.page>=pg?'disabled':''} onclick="srPage(${ST.page+1})">بعدی</button></div>`;
 }catch(e){box.innerHTML=`<div class=error>${E(e.message)}</div>`}};
window.srAdv=async keep=>{SC=SC||await api('/search/schema');const keys=Object.keys(SC);if(!keys.length){content.innerHTML='<div class=empty>به هیچ بخش قابل‌جستجویی دسترسی ندارید</div>';return}
 if(!SC[ST.entity])ST.entity=keys[0];const sv=await api('/search/saved?entity='+ST.entity).catch(()=>[]);window.__srSaved=sv;const sp=SC[ST.entity];
 content.innerHTML=`<div class=acc-h><div><h1>جستجوی پیشرفته</h1></div></div><div class=cd><div class=rp-filters><label>بخش<select id=sr-ent>${keys.map(k=>`<option value="${k}" ${k===ST.entity?'selected':''}>${E(SC[k].label)}</option>`).join('')}</select></label><label>متن<input id=sr-q value="${E(ST.q)}"></label><label>مرتب‌سازی<select id=sr-sort><option value="">پیش‌فرض</option>${sp.sort.map(k=>`<option ${k===ST.sort?'selected':''}>${E(k)}</option>`).join('')}</select></label><label>ترتیب<select id=sr-ord><option value=desc ${ST.order==='desc'?'selected':''}>نزولی</option><option value=asc ${ST.order==='asc'?'selected':''}>صعودی</option></select></label></div>
 <div id=sr-filters>${ST.filters.map(fRow).join('')}</div><div class=acc-act><button id=sr-add class=btn>+ شرط</button><button id=sr-go class="btn pri">جستجو</button><button id=sr-save class=btn>ذخیرهٔ فیلتر</button></div>
 ${sv.length?`<div class=sr-saved>${sv.map((s,i)=>`<span class=sr-chip><button class=btn onclick="srApply(${i})">${E(s.name)}${s.shared?' (اشتراکی)':''}</button>${s.mine?`<button class=btn aria-label="حذف" onclick="srDel(${s.id})">×</button>`:''}</span>`).join('')}</div>`:''}</div><div id=sr-res class=cd></div>`;
 bind()};
extraPages.search=window.srAdv;
})();
