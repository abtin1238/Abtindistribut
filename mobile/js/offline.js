/* لایه‌ی آفلاین مشترک: IndexedDB (صف رویداد، عکس‌ها) + ثبت service worker. هر اپ با پیشوند خودش جدا می‌شود. */
function offlineDB(prefix){
 const open=()=>new Promise((res,rej)=>{const r=indexedDB.open(prefix+'_offline',1);r.onupgradeneeded=()=>{const d=r.result;d.createObjectStore('queue',{keyPath:'id'});d.createObjectStore('photos',{keyPath:'pid',autoIncrement:true})};r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)});
 let dbp=null;const db=()=>dbp||(dbp=open());
 const tx=async(store,mode,fn)=>{const d=await db();return new Promise((res,rej)=>{const t=d.transaction(store,mode),s=t.objectStore(store);let out;const r=fn(s);if(r)r.onsuccess=()=>{out=r.result};t.oncomplete=()=>res(out);t.onerror=()=>rej(t.error);t.onabort=()=>rej(t.error)})};
 const store=name=>({all:()=>tx(name,'readonly',s=>s.getAll()).then(x=>x||[]),add:v=>tx(name,'readwrite',s=>s.put(v)),del:k=>tx(name,'readwrite',s=>s.delete(k)),
  set:async list=>{const d=await db();return new Promise((res,rej)=>{const t=d.transaction(name,'readwrite'),s=t.objectStore(name);s.clear();list.forEach(v=>s.put(v));t.oncomplete=()=>res();t.onerror=()=>rej(t.error)})}});
 return{Q:store('queue'),Photos:store('photos')};
}
/* کوچک‌کردن عکس پیش از ذخیره/ارسال (سقف حجم سرور ۱۰MB؛ اینجا حداکثر ۱۶۰۰px و JPEG) */
async function shrinkImage(file,max=1600,q=0.8){
 try{const bmp=await createImageBitmap(file),k=Math.min(1,max/Math.max(bmp.width,bmp.height)),c=document.createElement('canvas');c.width=Math.round(bmp.width*k);c.height=Math.round(bmp.height*k);c.getContext('2d').drawImage(bmp,0,0,c.width,c.height);
  return await new Promise(r=>c.toBlob(b=>r(b||file),'image/jpeg',q))}catch(_){return file}
}
if('serviceWorker' in navigator)addEventListener('load',()=>navigator.serviceWorker.register('/mobile/sw.js').catch(()=>{}));
