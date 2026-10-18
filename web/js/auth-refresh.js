/* تمدید خودکار نشست: وقتی access token منقضی شد (۴۰۱)، با refresh token در کوکی HttpOnly توکن تازه می‌گیرد و درخواست را یک‌بار تکرار می‌کند.
   refresh token هرگز به JS نمی‌رسد. فقط درخواست‌های هم‌مبدأ به /api/ (به‌جز login/refresh) را تحت‌تأثیر قرار می‌دهد. */
(function(){
 'use strict';
 if(window.AbtinAuth||!window.fetch)return;
 var KEYS=['ads_token','token','vtoken','dtoken'],orig=window.fetch.bind(window),replaced={},inflight=null;
 function isApi(u){try{var x=new URL(u,location.href);return x.origin===location.origin&&/^\/api\/(v1\/)?/.test(x.pathname)&&!/\/auth\/(login|refresh)$/.test(x.pathname)}catch(e){return false}}
 function bearer(h){if(!h)return null;var v=h instanceof Headers?h.get('Authorization'):(h.Authorization||h.authorization);return v&&/^Bearer (?!abk_)/.test(v)?v.slice(7):null}
 function withToken(init,tok){var h=new Headers(init.headers||{});h.set('Authorization','Bearer '+tok);var o={};for(var k in init)o[k]=init[k];o.headers=h;return o}
 function store(oldTok,newTok){replaced[oldTok]=newTok;try{KEYS.forEach(function(k){if(localStorage.getItem(k)===oldTok)localStorage.setItem(k,newTok)})}catch(e){}}
 function doRefresh(){
  if(!inflight)inflight=orig('/api/auth/refresh',{method:'POST',credentials:'same-origin',headers:{'X-Requested-With':'abtin'}})
   .then(function(r){return r.ok?r.json():null}).catch(function(){return null}).then(function(d){inflight=null;return d&&d.token||null});
  return inflight;
 }
 function latest(t){var n=0;while(replaced[t]&&n++<20)t=replaced[t];return t}
 window.fetch=function(input,init){
  var url=typeof input==='string'?input:(input&&input.url);
  if(typeof input!=='string'||!isApi(url))return orig(input,init);
  init=init||{};var tok=bearer(init.headers);
  if(!tok)return orig(input,init);
  var cur=latest(tok);if(cur!==tok)init=withToken(init,cur);
  return orig(input,init).then(function(resp){
   if(resp.status!==401)return resp;
   return doRefresh().then(function(nt){
    if(!nt){var again=latest(cur);if(again!==cur)return orig(input,withToken(init,again));return resp}
    store(cur,nt);return orig(input,withToken(init,nt));
   });
  });
 };
 window.AbtinAuth={refresh:doRefresh};
})();
