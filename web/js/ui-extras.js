/* ۱) alert بومی (با عنوان دامنه، مسدودکننده) → toast درون‌برنامه. ۲) جایگزین انتخاب‌گر رنگ بومی (در RTL معکوس عمل می‌کرد و صفحه را می‌پوشاند). */
(()=>{
const OK=/شد|ذخیره|ثبت|ارسال|موفق|فعال|لغو/;
let box=null;
function host(){if(box&&box.isConnected)return box;box=document.createElement('div');box.className='toast-host';box.setAttribute('role','status');box.setAttribute('aria-live','polite');(document.body||document.documentElement).appendChild(box);return box}
window.toast=(msg,kind)=>{const t=document.createElement('div'),k=kind||(OK.test(String(msg))?'ok':'err');t.className='toast toast-'+k;t.textContent=String(msg==null?'':msg);host().appendChild(t);
 const rm=()=>{t.classList.add('toast-out');setTimeout(()=>t.remove(),250)};t.onclick=rm;setTimeout(rm,k==='ok'?2500:6000)};
window.alert=m=>window.toast(m);
/* ---- انتخاب‌گر رنگ ----
   مقدارهای پویا (رنگ فعلی و گرادیان نوارها) فقط به‌صورت CSS variable داخل یک stylesheet ساخته‌شده نوشته می‌شوند؛ element.style / style="" استفاده نمی‌شود. */
const sheet=(()=>{try{const s=new CSSStyleSheet();document.adoptedStyleSheets=[...document.adoptedStyleSheets,s];return{kind:'cssom',s}}catch(_){const el=document.createElement('style');el.id='abtin-cf';(document.head||document.documentElement).appendChild(el);return{kind:'el',el,rules:{}}}})();
let cfSeq=0;
function cfRule(id){const sel='.cf[data-cfid="'+id+'"]';
 if(sheet.kind==='cssom'){const i=sheet.s.insertRule(sel+'{}',sheet.s.cssRules.length);const r=sheet.s.cssRules[i];return vars=>{for(const k in vars)r.style.setProperty(k,vars[k])}}
 return vars=>{sheet.rules[id]=Object.entries(vars).map(([k,v])=>k+':'+v).join(';');sheet.el.textContent=Object.entries(sheet.rules).map(([i,b])=>'.cf[data-cfid="'+i+'"]{'+b+'}').join('')}}
const hex2hsv=h=>{const m=/^#?([0-9a-f]{6})$/i.exec(h||'');if(!m)return null;const n=parseInt(m[1],16),r=(n>>16&255)/255,g=(n>>8&255)/255,b=(n&255)/255,mx=Math.max(r,g,b),mn=Math.min(r,g,b),d=mx-mn;let hh=0;
 if(d){hh=mx===r?((g-b)/d)%6:mx===g?(b-r)/d+2:(r-g)/d+4;hh*=60;if(hh<0)hh+=360}return[Math.round(hh),Math.round(mx?d/mx*100:0),Math.round(mx*100)]};
const hsv2hex=(h,s,v)=>{s/=100;v/=100;const f=n=>{const k=(n+h/60)%6;return v-v*s*Math.max(0,Math.min(k,4-k,1))},x=a=>Math.round(a*255).toString(16).padStart(2,'0');return'#'+x(f(5))+x(f(3))+x(f(1))};
function upgrade(inp){if(inp.dataset.cf)return;inp.dataset.cf='1';const val=inp.value||'#2f7bff';inp.type='text';inp.value=val;inp.classList.add('cf-in');inp.setAttribute('dir','ltr');inp.setAttribute('maxlength','7');inp.setAttribute('spellcheck','false');inp.setAttribute('inputmode','text');
 const wrap=document.createElement('span');wrap.className='cf';inp.parentNode.insertBefore(wrap,inp);
 const sw=document.createElement('button');sw.type='button';sw.className='cf-sw';sw.setAttribute('aria-label','انتخاب رنگ');sw.setAttribute('aria-expanded','false');
 const pn=document.createElement('div');pn.className='cf-pn';pn.hidden=true;pn.setAttribute('dir','ltr');
 pn.innerHTML='<div class=cf-row><span>رنگ‌مایه</span><input type=range class=cf-range data-k=h min=0 max=360 aria-label="رنگ‌مایه"></div><div class=cf-row><span>اشباع</span><input type=range class=cf-range data-k=s min=0 max=100 aria-label="اشباع"></div><div class=cf-row><span>روشنایی</span><input type=range class=cf-range data-k=v min=0 max=100 aria-label="روشنایی"></div>';
 wrap.append(sw,inp,pn);
 let hsv=hex2hsv(val)||[215,82,100];
 const rg={h:pn.querySelector('[data-k=h]'),s:pn.querySelector('[data-k=s]'),v:pn.querySelector('[data-k=v]')};
 const setVars=cfRule(wrap.dataset.cfid=String(++cfSeq));
 const paint=()=>{const c=hsv2hex(...hsv);rg.h.value=hsv[0];rg.s.value=hsv[1];rg.v.value=hsv[2];
  setVars({'--cf-c':c,'--cf-th':'linear-gradient(to right,#f00,#ff0,#0f0,#0ff,#00f,#f0f,#f00)','--cf-ts':`linear-gradient(to right,${hsv2hex(hsv[0],0,hsv[2])},${hsv2hex(hsv[0],100,hsv[2])})`,'--cf-tv':`linear-gradient(to right,#000,${hsv2hex(hsv[0],hsv[1],100)})`})};
 const emit=()=>inp.dispatchEvent(new Event('input',{bubbles:true}));
 Object.values(rg).forEach(r=>r.oninput=()=>{hsv=[+rg.h.value,+rg.s.value,+rg.v.value];inp.value=hsv2hex(...hsv);paint();emit()});
 inp.addEventListener('input',e=>{const p=hex2hsv(inp.value);if(p&&e.isTrusted){hsv=p;paint()}});
 inp.addEventListener('blur',()=>{if(!hex2hsv(inp.value)){inp.value=hsv2hex(...hsv)}else if(inp.value[0]!=='#')inp.value='#'+inp.value});
 sw.onclick=()=>{pn.hidden=!pn.hidden;sw.setAttribute('aria-expanded',String(!pn.hidden))};
 const val0=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value');   // مقدار تنظیم‌شده از کد هم پنل را همگام کند
 Object.defineProperty(inp,'value',{get(){return val0.get.call(inp)},set(v){val0.set.call(inp,v);const p=hex2hsv(v);if(p){hsv=p;paint()}}});
 paint()}
const scan=r=>(r.querySelectorAll?r.querySelectorAll('input[type=color]'):[]).forEach(upgrade);
const start=()=>{scan(document);new MutationObserver(ms=>ms.forEach(m=>m.addedNodes.forEach(n=>{if(n.nodeType===1){if(n.matches&&n.matches('input[type=color]'))upgrade(n);else scan(n)}}))).observe(document.body,{childList:true,subtree:true})};
if(document.body)start();else addEventListener('DOMContentLoaded',start);
})();
