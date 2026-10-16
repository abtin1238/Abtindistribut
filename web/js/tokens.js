/* لایهٔ استایل داینامیک: رنگ برند، شعاع گوشه، مقیاس فونت، پالت و حالت تم از دیتابیس (/api/settings/theme) خوانده می‌شود.
   مقادیر فقط در یک stylesheet (CSSStyleSheet / عنصر style) به‌صورت CSS variable روی :root نوشته می‌شوند؛ هیچ style="" یا element.style روی صفحه ست نمی‌شود.
   رنگ‌های JS (نقشه، نمودار) با Tokens.v('--ok') از همین متغیرها خوانده می‌شوند. */
const Tokens=(()=>{
 const R=document.documentElement,CSSV=n=>getComputedStyle(R).getPropertyValue(n).trim(),DEFAULT={color:CSSV('--bl'),radius:16,font_scale:100,mode:'system'},HEX=/^#[0-9a-fA-F]{6}$/,
 KEYS=['ads_token','token','vtoken','dtoken'],key=()=>{for(const k of KEYS){const v=localStorage.getItem(k);if(v)return v}return null},
 mix=(c,w,p)=>`color-mix(in srgb,${c} ${p}%,${w})`,vars={};let rule=null,el=null,cur=null;
 const ensure=()=>{if(rule||el)return;
  try{const sh=new CSSStyleSheet();sh.replaceSync(':root:root:root{}');document.adoptedStyleSheets=[...document.adoptedStyleSheets,sh];rule=sh.cssRules[0]}
  catch(_){el=document.createElement('style');el.id='abtin-tokens';(document.head||R).appendChild(el)}};
 const flush=()=>{ensure();if(rule){for(const k in vars)rule.style.setProperty(k,vars[k])}else el.textContent=':root:root:root{'+Object.entries(vars).map(([k,v])=>k+':'+v).join(';')+'}'};
 const set=o=>{Object.assign(vars,o);flush()};
 const v=n=>getComputedStyle(R).getPropertyValue(n).trim();
 const brand=c=>{c=HEX.test(c||'')?c:DEFAULT.color;set({'--bl':c,'--brand':c,'--bl2':mix(c,'var(--c-d14f9016)',72),'--btn':`linear-gradient(180deg,${mix(c,'var(--c-d14f9016)',88)},${mix(c,'var(--c-598b32b7)',86)})`})};
 const apply=t=>{if(!t)return;cur=t;brand(t.color);set({'--r':(t.radius||DEFAULT.radius)+'px','font-size':(t.font_scale||100)+'%',...Object.fromEntries(Object.entries(t.vars||{}).filter(([k,x])=>/^--(ctl|ds)-[a-z0-9-]+$/.test(k)&&/^[#a-z0-9 .%(),-]+$/i.test(x))),...Object.fromEntries(Object.entries(t.palette||{}).filter(([k,x])=>/^[a-z0-9-]+$/.test(k)&&HEX.test(x)).map(([k,x])=>['--'+k,x]))});
  localStorage.abtin_tokens=JSON.stringify(t);if(t.mode&&t.mode!=='system'&&!localStorage.abtin_theme)localStorage.abtin_theme=t.mode;
  window.Theme?Theme.apply():mode()};
 const mode=()=>{const m=localStorage.abtin_theme||(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light');R.dataset.theme=m};
 const cached=()=>{try{return JSON.parse(localStorage.abtin_tokens)}catch(_){return null}};
 async function load(){apply(cached());const k=key();if(!k)return;try{const r=await fetch('/api/settings/theme',{headers:{Authorization:'Bearer '+k}});if(r.ok)apply(await r.json())}catch(_){}}
 const toggle=()=>{localStorage.abtin_theme=R.dataset.theme==='dark'?'light':'dark';mode()};
 mode();apply(cached());addEventListener('DOMContentLoaded',load);
 return{apply,load,toggle,mode,set,v,brand,DEFAULT,get cur(){return cur}};
})();

/* کارت «ظاهر و تم» در تنظیمات: تغییر زنده + ذخیره در دیتابیس برای همهٔ کاربران شرکت (وب و موبایل) */
addEventListener('DOMContentLoaded',()=>{const o=window.settingsPage;if(!o)return;
 window.settingsPage=async()=>{await o();const t=Tokens.cur||JSON.parse(localStorage.abtin_tokens||'{}'),c=t.color||CSSV('--bl');
  content.insertAdjacentHTML('beforeend',`<div class="cd ds-card ds-settings-card ds-mt-2"><h3>ظاهر و تم</h3><label>رنگ اصلی<input id=tc type=color value="${c}"></label><label>گردی گوشه‌ها: <span id=trv>${t.radius||16}</span>px<input id=tr type=range min=6 max=28 value="${t.radius||16}"></label><label>اندازهٔ متن: <span id=tfv>${t.font_scale||100}</span>٪<input id=tf type=range min=90 max=120 value="${t.font_scale||100}"></label><label>حالت پیش‌فرض<select id=tm><option value=system>مطابق سیستم</option><option value=dark>تیره</option><option value=light>روشن</option></select></label><button class=btn onclick="saveTheme()">ذخیره برای همه</button></div>`);
  tm.value=t.mode||'system';const live=()=>{trv.textContent=tr.value;tfv.textContent=tf.value;Tokens.apply({color:tc.value,radius:+tr.value,font_scale:+tf.value,mode:tm.value})};[tc,tr,tf].forEach(e=>e.oninput=live);tm.onchange=()=>{localStorage.removeItem('abtin_theme');live()}};
 window.saveTheme=async()=>{try{const r=await api('/settings/theme',{method:'PUT',body:JSON.stringify({color:tc.value,radius:+tr.value,font_scale:+tf.value,mode:tm.value})});Tokens.apply(r);alert('ذخیره شد')}catch(e){alert(e.message)}}});
