/* نقشهٔ مسیر امروز: Leaflet+OSM (تایل‌های تیره با فیلتر CSS) وقتی آنلاین است؛ در غیر این صورت نقشهٔ SVG آفلاین. بدون هیچ داده‌ی ثابت — فقط نقاطی که پاس می‌دهید. */
const AbtinMap=(()=>{
 const L_JS='https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js',L_CSS='https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css';let lp=null;
 const load=()=>lp||(lp=new Promise((ok,no)=>{if(window.L)return ok();const l=document.createElement('link');l.rel='stylesheet';l.href=L_CSS;document.head.appendChild(l);const s=document.createElement('script');s.src=L_JS;s.onload=ok;s.onerror=no;document.head.appendChild(s);setTimeout(no,6000)}));
 const svg=(el,pts,me)=>{const all=[...pts,...(me?[me]:[])].filter(p=>p.lat!=null);if(!all.length){el.innerHTML='<div class="empty">مختصاتی برای نمایش نیست</div>';return}
  const W=400,H=270,P=40,la=all.map(p=>p.lat),ln=all.map(p=>p.lng),a=Math.min(...la),b=Math.max(...la),c=Math.min(...ln),d=Math.max(...ln),k=Math.max(b-a,d-c,1e-4),
  X=p=>P+(p.lng-c)/k*(W-2*P)+((W-2*P)-(d-c)/k*(W-2*P))/2,Y=p=>H-P-(p.lat-a)/k*(H-2*P)-((H-2*P)-(b-a)/k*(H-2*P))/2,line=[...(me?[me]:[]),...pts].filter(p=>p.lat!=null).map(p=>X(p)+','+Y(p)).join(' ');
  el.innerHTML=`<svg viewBox="0 0 ${W} ${H}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice"><defs><pattern id="g" width="26" height="26" patternUnits="userSpaceOnUse"><path d="M26 0H0V26" fill="none" stroke="var(--bd)" stroke-width="1"/></pattern></defs><rect width="${W}" height="${H}" fill="url(#g)"/><polyline points="${line}" fill="none" stroke="var(--route)" stroke-width="9" opacity=".25" stroke-linejoin="round"/><polyline points="${line}" fill="none" stroke="var(--route)" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"/>${pts.filter(p=>p.lat!=null).map(p=>`<circle cx="${X(p)}" cy="${Y(p)}" r="14" fill="var(--card2)" stroke="var(--route)" stroke-width="2.5"/><text x="${X(p)}" y="${Y(p)+5}" text-anchor="middle" font-size="14" font-weight="700" fill="var(--tx)">${fa(p.n)}</text>`).join('')}${me?`<circle cx="${X(me)}" cy="${Y(me)}" r="16" fill="var(--bl)" opacity=".25"/><circle cx="${X(me)}" cy="${Y(me)}" r="8" fill="var(--bl)" stroke="var(--c-d14f9016)" stroke-width="3"/>`:''}</svg>`};
 let inst=null;
 async function render(el,{pts=[],me=null}){
  const ok=pts.filter(p=>p.lat!=null&&p.lng!=null);if(inst){try{inst.remove()}catch(_){}inst=null}el.innerHTML='';
  if(!navigator.onLine)return svg(el,ok,me);
  try{await load();const m=L.map(el,{zoomControl:false,attributionControl:false}),pl=[...(me?[me]:[]),...ok].map(p=>[p.lat,p.lng]);
   L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19}).addTo(m);if(pl.length>1){L.polyline(pl,{color:Tokens.v('--cy'),weight:9,opacity:.25}).addTo(m);L.polyline(pl,{color:Tokens.v('--cy'),weight:3.5}).addTo(m)}
   ok.forEach(p=>L.marker([p.lat,p.lng],{icon:L.divIcon({className:'',html:`<div class="nd">${fa(p.n)}</div>`,iconSize:[28,28]})}).addTo(m));
   if(me)L.marker([me.lat,me.lng],{icon:L.divIcon({className:'',html:'<div class="me"></div>',iconSize:[20,20]})}).addTo(m);
   if(pl.length)m.fitBounds(pl,{padding:[44,44],maxZoom:16});else m.setView([35.7,51.4],11);inst=m;el._m=m;el._pl=pl}catch(_){svg(el,ok,me)}}
 return{render,recenter:el=>{if(el&&el._m&&el._pl&&el._pl.length)el._m.fitBounds(el._pl,{padding:[44,44],maxZoom:16})}};
})();
