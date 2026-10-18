/* Service worker فقط برای Web Push؛ هیچ داده‌ای کش نمی‌شود. */
self.addEventListener('push',e=>{let d={};try{d=e.data?e.data.json():{}}catch(_){}
 e.waitUntil(self.registration.showNotification(d.title||'Abtin Distribution',{body:d.body||'',tag:d.tag||undefined,data:{url:d.url||'/'},dir:'rtl',lang:'fa'}))});
self.addEventListener('notificationclick',e=>{e.notification.close();const u=(e.notification.data&&e.notification.data.url)||'/';
 e.waitUntil(clients.matchAll({type:'window'}).then(l=>{for(const c of l){if('focus' in c)return c.focus()}return clients.openWindow(u.startsWith('/')?u:'/')}))});
