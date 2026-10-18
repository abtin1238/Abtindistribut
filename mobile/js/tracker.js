/* ردیاب موقعیت مشترک اپ‌های موبایل (مرحله ۱۳). نیازمند: api(path) ، queue(event) ، sync() از اپ میزبان.
   - فقط با رضایت صریح کاربر؛ هر زمان قابل خاموش‌کردن (Tracker.setConsent(false)).
   - فقط داخل ساعت/روز کاری تنظیم‌شده‌ی شرکت ثبت می‌شود (سرور هم دوباره بررسی و رد می‌کند).
   - آفلاین: نقاط در صف IndexedDB (همان صف sync) می‌مانند و با اتصال ارسال می‌شوند؛ هر نقطه client_id یکتا دارد (idempotent).
   - محدودیت پلتفرم: مرورگر/PWA فقط وقتی صفحه باز و فعال است موقعیت می‌دهد؛ ردیابی پس‌زمینه‌ی واقعی نیازمند اپ native است. */
const Tracker=(()=>{
 let P='app',host=null,cfg=null,watch=null,last=null,lastAt=0,buf=[],timer=null;
 const K=s=>P+'_gps_'+s,jget=Shared.jget,jset=Shared.jset;
 const uid=()=>crypto.randomUUID?crypto.randomUUID():String(Date.now())+Math.random().toString(16).slice(2);
 function dist(a,b,c,d){const R=6371008.8,r=x=>x*Math.PI/180,dp=r(c-a),dl=r(d-b),h=Math.sin(dp/2)**2+Math.cos(r(a))*Math.cos(r(c))*Math.sin(dl/2)**2;return 2*R*Math.asin(Math.min(1,Math.sqrt(h)))}
 function inHours(c,ms){const l=new Date(ms+c.tz_offset_min*60000),wd=(l.getUTCDay()+6)%7,hm=String(l.getUTCHours()).padStart(2,'0')+':'+String(l.getUTCMinutes()).padStart(2,'0');return c.work_days.includes(wd)&&c.work_start<=hm&&hm<=c.work_end}
 async function loadCfg(){try{cfg=await host.api('/gps/config');jset(K('cfg'),cfg)}catch(_){cfg=jget(K('cfg'),null)}return cfg}
 async function flush(){if(!buf.length)return;const pts=buf.splice(0,500);jset(K('buf'),buf);try{await host.queue({type:'gps.points',payload:{points:pts}})}catch(_){buf.unshift(...pts);jset(K('buf'),buf);return}try{await host.sync()}catch(_){}}
 function onPos(p){
  const now=Date.now(),c=p.coords;if(!cfg||!cfg.enabled||!inHours(cfg,now))return;if(c.accuracy!=null&&c.accuracy>200)return;
  const el=(now-lastAt)/1000,mv=last?dist(last.lat,last.lng,c.latitude,c.longitude):1e9,iv=cfg.interval_s||60;
  if(last&&!((el>=iv&&mv>=(cfg.min_distance_m||25))||el>=iv*5))return;
  last={lat:c.latitude,lng:c.longitude};lastAt=now;
  buf.push({client_id:uid(),lat:c.latitude,lng:c.longitude,accuracy_m:c.accuracy??null,speed_mps:c.speed!=null&&c.speed>=0?c.speed:null,recorded_at:new Date(p.timestamp||now).toISOString()});jset(K('buf'),buf);
  if(buf.length>=10)flush();
 }
 const consent=()=>localStorage.getItem(K('consent'));
 async function start(h){
  host=h;P=h.prefix||P;buf=jget(K('buf'),[]);
  if(consent()===null){const ok=confirm('برای ثبت مسیر کاری، موقعیت شما فقط در ساعات کاری ثبت و برای مدیران مجاز نمایش داده می‌شود. اجازه می‌دهید؟');localStorage.setItem(K('consent'),ok?'1':'0')}
  if(consent()!=='1'||!navigator.geolocation)return false;
  await loadCfg();if(!cfg||!cfg.enabled)return false;
  if(watch==null)watch=navigator.geolocation.watchPosition(onPos,()=>{},{enableHighAccuracy:true,maximumAge:10000,timeout:30000});
  if(!timer)timer=setInterval(()=>{flush();loadCfg()},120000);
  addEventListener('pagehide',()=>{flush()});document.addEventListener('visibilitychange',()=>{if(document.hidden)flush()});
  flush();return true;
 }
 function stop(){if(watch!=null)navigator.geolocation.clearWatch(watch);watch=null;if(timer)clearInterval(timer);timer=null;flush()}
 function setConsent(v){localStorage.setItem(K('consent'),v?'1':'0');if(!v)stop();else if(host)start(host)}
 return{start,stop,setConsent,flush,enabled:()=>consent()==='1'&&watch!=null};
})();
