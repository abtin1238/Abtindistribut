/* مرکز اعلان‌ها: فید درون‌برنامه، تنظیمات کانال×رویداد، اطلاعات تماس، Web Push. منطق همه در بک‌اند. */
(()=>{
const E=escapeHtml,FA=v=>Number(v||0).toLocaleString('fa-IR');
const D=s=>{if(!s)return'—';const d=new Date(s);return isNaN(d)?E(s):new Intl.DateTimeFormat('fa-IR-u-ca-persian',{dateStyle:'short',timeStyle:'short'}).format(d)};
const b64=s=>{const p='='.repeat((4-s.length%4)%4),r=atob((s+p).replace(/-/g,'+').replace(/_/g,'/'));return Uint8Array.from([...r].map(c=>c.charCodeAt(0)))};
const ab=buf=>btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
let EV=null,PR=null;
window.ntBadge=async()=>{try{const r=await api('/notifications/unread-count');const el=document.getElementById('nb');if(el){el.hidden=!r.unread;el.textContent=FA(r.unread)}}catch(e){}};
window.ntRead=async(id,el)=>{await api('/notifications/read-all',{method:'POST'}).catch(()=>{});ntBadge();notifications()};
function feedHtml(items){return items.map(n=>`<div class="nt-item ${n.read?'':'nt-new'}"><b>${E(n.title)}</b><p>${E(n.body||'')}</p><small>${D(n.created_at)}</small></div>`).join('')||'<div class=empty>اعلانی وجود ندارد</div>'}
window.ntMore=async()=>{const last=document.querySelector('#nt-feed').dataset.last;const r=await api('/notifications/feed?before_id='+last);const box=document.querySelector('#nt-feed');box.insertAdjacentHTML('beforeend',feedHtml(r.items).replace('<div class=empty>اعلانی وجود ندارد</div>',''));if(r.items.length)box.dataset.last=r.items[r.items.length-1].id;else document.querySelector('#nt-more').hidden=true};
window.ntSavePrefs=async()=>{const prefs={};document.querySelectorAll('.nt-cb').forEach(c=>{(prefs[c.dataset.e]=prefs[c.dataset.e]||{})[c.dataset.c]=c.checked});try{await api('/notifications/preferences',{method:'PUT',body:JSON.stringify({prefs})});alert('تنظیمات ذخیره شد')}catch(e){alert(e.message)}};
window.ntSaveContact=async()=>{try{await api('/me/contact',{method:'PUT',body:JSON.stringify({email:ntEmail.value,phone:ntPhone.value})});alert('اطلاعات تماس ذخیره شد')}catch(e){alert(e.message)}};
window.ntTest=async c=>{try{const r=await api('/notifications/test',{method:'POST',body:JSON.stringify({channel:c})});alert(r.status==='sent'?'ارسال شد':'نتیجه: '+r.status+(r.error?' — '+r.error:''))}catch(e){alert(e.message)}};
window.ntPush=async()=>{try{if(!('serviceWorker' in navigator)||!('PushManager' in window))return alert('مرورگر شما از Web Push پشتیبانی نمی‌کند');
 if(await Notification.requestPermission()!=='granted')return alert('اجازهٔ اعلان داده نشد');
 const k=await api('/push/vapid-public-key'),reg=await navigator.serviceWorker.register('/web/sw.js'),sub=await reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:b64(k.key)});
 await api('/push/subscribe',{method:'POST',body:JSON.stringify({endpoint:sub.endpoint,keys:{p256dh:ab(sub.getKey('p256dh')),auth:ab(sub.getKey('auth'))}})});alert('این مرورگر برای اعلان ثبت شد');notifications()}catch(e){alert(e.message)}};
window.ntUnpush=async()=>{try{const reg=await navigator.serviceWorker.getRegistration('/web/'),sub=reg&&await reg.pushManager.getSubscription();if(sub){await api('/push/unsubscribe',{method:'POST',body:JSON.stringify({endpoint:sub.endpoint})});await sub.unsubscribe()}alert('لغو شد');notifications()}catch(e){alert(e.message)}};
window.notifications=async()=>{
 const [f,ev,pr]=await Promise.all([api('/notifications/feed'),api('/notifications/events'),api('/notifications/preferences')]);EV=ev;PR=pr;
 const av=Object.fromEntries(ev.channels.map(c=>[c.code,c.available]));
 content.innerHTML=`<div class=acc-h><div><h1>اعلان‌ها</h1><p>${FA(f.unread)} اعلان خوانده‌نشده</p></div><div class=acc-act><button class=btn onclick="ntRead()">علامت‌گذاری همه به‌عنوان خوانده</button></div></div>
 <div class="nt-grid"><section class=cd><h3>فید</h3><div id=nt-feed data-last="${f.items.length?f.items[f.items.length-1].id:0}">${feedHtml(f.items)}</div>${f.items.length>=30?'<button id=nt-more class=btn onclick="ntMore()">قدیمی‌تر</button>':''}</section>
 <section class=cd><h3>تنظیمات اعلان</h3><div class=tablewrap><table><thead><tr><th>رویداد</th>${ev.channels.map(c=>`<th>${E(c.label)}${c.available?'':'<small class=nt-off> (پیکربندی نشده)</small>'}</th>`).join('')}</tr></thead><tbody>${ev.events.map(e=>`<tr><td>${E(e.title)}</td>${ev.channels.map(c=>`<td><input type=checkbox class=nt-cb data-e="${E(e.code)}" data-c="${E(c.code)}" ${pr.prefs[e.code]&&pr.prefs[e.code][c.code]?'checked':''} ${c.code==='inapp'?'':av[c.code]?'':'disabled'} aria-label="${E(e.title)} ${E(c.label)}"></td>`).join('')}</tr>`).join('')}</tbody></table></div><button class="btn pri" onclick="ntSavePrefs()">ذخیره تنظیمات</button>
 <h3>اطلاعات تماس</h3><div class=rp-filters><label>ایمیل<input id=ntEmail type=email value="${E(pr.contact.email)}" dir=ltr></label><label>موبایل<input id=ntPhone value="${E(pr.contact.phone)}" dir=ltr placeholder="+989123456789"></label></div><button class=btn onclick="ntSaveContact()">ذخیره</button>
 <h3>ارسال آزمایشی</h3><div class=acc-act>${['email','sms','webpush'].map(c=>`<button class=btn ${av[c]?'':'disabled'} onclick="ntTest('${c}')">${E((ev.channels.find(x=>x.code===c)||{}).label||c)}</button>`).join('')}</div>
 <h3>اعلان مرورگر</h3><p class=rp-note>${FA(pr.push_subscriptions)} مرورگر ثبت‌شده</p><div class=acc-act><button class=btn ${av.webpush?'':'disabled'} onclick="ntPush()">فعال‌سازی در این مرورگر</button><button class=btn onclick="ntUnpush()">لغو در این مرورگر</button></div></section></div>`;
 ntBadge()};
if(window.extraPages)extraPages.notifications=window.notifications;
setInterval(()=>{if(typeof token!=='undefined'&&token&&document.visibilityState==='visible')ntBadge()},60000);
})();
