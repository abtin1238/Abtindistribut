window.extraPages=window.extraPages||{};
/* مرحله ۱۳ — صفحه‌ی «نقشه و GPS»: مشتریان (خوشه‌بندی)، موقعیت زنده، مسیر روز، زمان حضور نزد مشتری، تنظیمات ردیابی.
   همه‌ی داده از /api/gps/*؛ هیچ مقدار نمایشی وجود ندارد. تمام متن‌های دینامیک escape می‌شوند. */
(()=>{
const X=Shared.esc;
const FA=Shared.fa,TM=i=>i?new Date(i).toLocaleTimeString('fa-IR',{hour:'2-digit',minute:'2-digit'}):'—';
const KIND={visitor:['ok','بازاریاب'],driver:['info','مأمور پخش'],other:['warn','سایر']};
const DAYS=[['5','شنبه'],['6','یکشنبه'],['0','دوشنبه'],['1','سه‌شنبه'],['2','چهارشنبه'],['3','پنجشنبه'],['4','جمعه']];
let M=null,LC=null,LL=null,TL=null,liveTimer=null,custTruncated=false;
const dot=c=>L.divIcon({className:'',html:`<i class="pin ds-pin-color" data-tone="${c}"></i>`,iconSize:[14,14],iconAnchor:[7,7]});
const localToday=Shared.today;
function loadScript(src){return new Promise((ok,no)=>{if([...document.scripts].some(s=>s.src===src))return ok();const s=document.createElement('script');s.src=src;s.onload=ok;s.onerror=no;document.head.appendChild(s)})}
function loadCss(href){if(![...document.styleSheets].some(s=>s.href===href)){const l=document.createElement('link');l.rel='stylesheet';l.href=href;document.head.appendChild(l)}}
async function ensureCluster(){const b='https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/';loadCss(b+'MarkerCluster.css');loadCss(b+'MarkerCluster.Default.css');if(!L.markerClusterGroup)await loadScript(b+'leaflet.markercluster.js')}
async function loadCustomers(bbox){
 const d=await api('/gps/customers?limit=5000'+(bbox?'&bbox='+bbox:''));custTruncated=d.truncated;LC.clearLayers();
 d.customers.forEach(c=>L.marker([c.lat,c.lng],{icon:dot('warn')}).bindPopup(`<b>${X(c.name)}</b><br>${X(c.code)} ${X(c.region)}`).addTo(LC));
 const n=document.getElementById('gpsnote');if(n)n.textContent=`مشتری روی نقشه: ${FA(d.customers.length)}${d.truncated?' (محدود‌شده؛ نقشه را بزرگ‌نمایی کنید)':''} — بدون مختصات: ${FA(d.without_gps)}`;
}
async function loadLive(){
 if(!document.getElementById('gpsmap')){clearInterval(liveTimer);liveTimer=null;return}
 const d=await api('/gps/live?minutes=15').catch(()=>null);if(!d||!LL)return;LL.clearLayers();
 const s=document.getElementById('gpslive');
 if(!d.active){if(s)s.textContent='خارج از ساعت کاری؛ ردیابی زنده غیرفعال است.';return}
 d.users.forEach(u=>{const k=KIND[u.kind]||KIND.other;L.marker([u.lat,u.lng],{icon:dot(k[0])}).bindPopup(`<b>${X(u.name)}</b><br>${X(k[1])}<br>${FA(Math.round(u.age_s/60))} دقیقه پیش`).addTo(LL)});
 if(s)s.textContent=`موقعیت زنده (۱۵ دقیقه‌ی اخیر): ${FA(d.users.length)} نفر`;
}
async function showTrack(){
 const uid=document.getElementById('gpsu').value,day=document.getElementById('gpsd').value;TL.clearLayers();
 const out=document.getElementById('gpsres');out.innerHTML='در حال بارگذاری...';
 let d;try{d=await api('/gps/track?user_id='+encodeURIComponent(uid)+'&day='+encodeURIComponent(day))}catch(e){out.innerHTML=`<div class=error>${X(e.message)}</div>`;return}
 const ll=d.points.map(p=>[p.lat,p.lng]);
 if(ll.length){L.polyline(ll,{color:Tokens.v('--info'),weight:4,opacity:.85}).addTo(TL);
  L.marker(ll[0],{icon:dot('ok')}).bindPopup('شروع: '+TM(d.points[0].t)).addTo(TL);L.marker(ll[ll.length-1],{icon:dot('bad')}).bindPopup('آخرین موقعیت: '+TM(d.points[d.points.length-1].t)).addTo(TL);
  M.fitBounds(L.latLngBounds(ll).pad(.2),{maxZoom:16})}
 d.visits.filter(v=>v.lat!=null).forEach(v=>L.circleMarker([v.lat,v.lng],{radius:7,color:Tokens.v('--pur'),fillOpacity:.8}).bindPopup(`ویزیت ${X(v.customer_name)}<br>${TM(v.started_at)}–${TM(v.ended_at)}`).addTo(TL));
 d.deliveries.filter(v=>v.lat!=null).forEach(v=>L.circleMarker([v.lat,v.lng],{radius:7,color:Tokens.v('--warn'),fillOpacity:.8}).bindPopup(`تحویل ${X(v.customer_name)} (${X(v.order_number)})<br>${TM(v.at)}`).addTo(TL));
 const row=a=>'<tr>'+a.map(c=>`<td>${c}</td>`).join('')+'</tr>',tb=(h,r,e)=>`<div class=tablewrap><table><tr>${h.map(x=>`<th>${x}</th>`).join('')}</tr>${r.length?r.join(''):`<tr><td colspan=${h.length}>${e}</td></tr>`}</table></div>`;
 out.innerHTML=`<div class=card><b>${X(d.user.name)}</b> — ${X(d.day)} — ${FA(d.point_count)} نقطه — مسافت: ${FA(d.distance_km)} کیلومتر — از ${TM(d.first_at)} تا ${TM(d.last_at)} <small>(شعاع حضور: ${FA(d.radius_m)} متر)</small></div>
 <h3>زمان حضور نزد مشتری (از GPS)</h3>${tb(['مشتری','ورود','خروج','مدت (دقیقه)','نزدیک‌ترین فاصله (متر)'],d.stays.map(s=>row([X(s.customer_name),TM(s.enter),TM(s.exit),FA(s.minutes),FA(Math.round(s.min_distance_m))])),'حضور ≥ ۳ دقیقه‌ای نزد مشتری ثبت نشده')}
 <h3>ویزیت‌های ثبت‌شده و تطبیق با GPS</h3>${tb(['مشتری','شروع','پایان','وضعیت GPS ویزیت','حضور واقعی (GPS)'],d.visits.map(v=>row([X(v.customer_name),TM(v.started_at),TM(v.ended_at),X(v.gps_status||'—'),v.gps_presence==null?'<span class="ds-color-muted">بدون داده‌ی مسیر</span>':v.gps_presence?'✓ '+FA(v.presence_minutes)+' دقیقه':'<b class="ds-text-danger">✗ حضور ثبت نشد</b>'])),'ویزیتی نیست')}
 <h3>تحویل‌ها</h3>${tb(['سفارش','مشتری','وضعیت','زمان','GPS'],d.deliveries.map(v=>row([X(v.order_number),X(v.customer_name),X(v.status),TM(v.at),X(v.gps_status||'—')])),'تحویلی نیست')}`;
}
async function saveCfg(){
 const days=DAYS.filter(([k])=>document.getElementById('gd'+k).checked).map(([k])=>+k),g=id=>document.getElementById(id);
 try{await api('/settings/tracking',{method:'PUT',body:JSON.stringify({enabled:g('ge').checked,work_start:g('gs').value,work_end:g('gz').value,work_days:days,interval_s:+g('gi').value,min_distance_m:+g('gm').value,retention_days:+g('gr').value,tz_offset_min:+g('gt').value})});alert('تنظیمات ذخیره شد')}catch(e){alert(e.message)}
}
extraPages.map=async()=>{
 await Promise.all([ensureCluster()]);
 const [users,cfg]=await Promise.all([api('/gps/users').catch(()=>[]),api('/settings/tracking').catch(()=>null)]);
 content.innerHTML=`<h1>${X(pages.map)}</h1>
 <div class=card><select id=gpsu>${users.map(u=>`<option value="${+u.id}">${X(u.name)} — ${X((KIND[u.kind]||KIND.other)[1])}</option>`).join('')}</select> <input type=date id=gpsd value="${localToday()}"> <button onclick="gpsShow()">نمایش مسیر روز</button> <button onclick="gpsLive()">به‌روزرسانی موقعیت زنده</button> <span id=gpslive></span><br><small id=gpsnote></small></div>
 <div id=gpsmap class="ds-map"></div><div id=gpsres></div>
 ${cfg?`<details class=card><summary><b>تنظیمات ردیابی و حریم خصوصی</b></summary>
 <label><input type=checkbox id=ge ${cfg.enabled?'checked':''}> ردیابی فعال</label> ساعت کاری: <input id=gs value="${X(cfg.work_start)}" size=5> تا <input id=gz value="${X(cfg.work_end)}" size=5> (HH:MM)<br>
 روزهای کاری: ${DAYS.map(([k,n])=>`<label><input type=checkbox id=gd${k} ${cfg.work_days.includes(+k)?'checked':''}> ${n}</label>`).join(' ')}<br>
 فاصله‌ی ثبت (ثانیه): <input id=gi type=number value="${+cfg.interval_s}" class="ds-table-input"> حداقل جابجایی (متر): <input id=gm type=number value="${+cfg.min_distance_m}" class="ds-table-input"> نگهداری (روز): <input id=gr type=number value="${+cfg.retention_days}" class="ds-table-input"> اختلاف ساعت از UTC (دقیقه): <input id=gt type=number value="${+cfg.tz_offset_min}" class="ds-table-input"><br>
 <button onclick="gpsSave()">ذخیره</button> <small>نقاط خارج از ساعت/روز کاری هرگز ذخیره نمی‌شوند؛ مشاهده‌ی مسیر دیگران در حسابرسی ثبت می‌شود.</small></details>`:''}`;
 if(M){M.remove();M=null}
 M=L.map('gpsmap').setView([35.7,51.4],11);L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'}).addTo(M);
 LC=L.markerClusterGroup({chunkedLoading:true,maxClusterRadius:50}).addTo(M);LL=L.layerGroup().addTo(M);TL=L.layerGroup().addTo(M);
 await loadCustomers();const pts=[];LC.eachLayer(l=>pts.push(l.getLatLng()));if(pts.length)M.fitBounds(L.latLngBounds(pts).pad(.1),{maxZoom:14});
 M.on('moveend',()=>{if(custTruncated){const b=M.getBounds();loadCustomers([b.getWest(),b.getSouth(),b.getEast(),b.getNorth()].join(',')).catch(()=>{})}});
 await loadLive();clearInterval(liveTimer);liveTimer=setInterval(loadLive,30000);setTimeout(()=>M&&M.invalidateSize(),150);
};
window.gpsShow=showTrack;window.gpsLive=loadLive;window.gpsSave=saveCfg;
})();
