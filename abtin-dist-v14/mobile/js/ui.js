/* آیکون‌ها + تم روشن/تیره (پیش‌فرض: تنظیم سیستم؛ انتخاب کاربر در localStorage) */
const ICONS={
 logo:'<path d="M12 2 2.5 22h5l4.5-10.5L16.5 22h5z" fill="currentColor" stroke="none"/>',
 users:'<circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-5.5 6-5.5s6 2.2 6 5.5"/><circle cx="17" cy="9" r="2.4"/><path d="M17 14.5c2.4.2 4 2 4 4.5"/>',
 check:'<circle cx="12" cy="12" r="9"/><path d="m8 12.5 2.8 2.8L16 9.5"/>',
 map:'<path d="m3 6 6-2 6 2 6-2v14l-6 2-6-2-6 2z"/><path d="M9 4v14M15 6v14"/>',
 car:'<path d="M5 16V11l2-5h10l2 5v5M3 16h18M7 16v2M17 16v2"/><circle cx="8" cy="13" r=".8"/><circle cx="16" cy="13" r=".8"/>',
 clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
 pin:'<path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.4"/>',
 nav:'<path d="m21 3-9.5 18-2-7.5L2 11.5z"/>',
 cal:'<rect x="3.5" y="5" width="17" height="16" rx="3"/><path d="M8 3v4M16 3v4M3.5 10h17"/>',
 trend:'<path d="m3 17 6-6 4 4 8-9"/><path d="M15 6h6v6"/>',
 bars:'<path d="M6 21V11M12 21V4M18 21v-7"/>',
 box:'<path d="m12 3 8 4.5v9L12 21l-8-4.5v-9z"/><path d="m4 7.5 8 4.5 8-4.5M12 12v9"/>',
 pen:'<path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16z"/><path d="M13 7l4 4M13 20h8"/>',
 cam:'<path d="M4 8h3l2-2.5h6L17 8h3v11H4z"/><circle cx="12" cy="13.5" r="3.5"/>',
 wallet:'<path d="M4 7h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h11"/><circle cx="16.5" cy="13.5" r="1.2"/>',
 cloud:'<path d="M7 18a4.5 4.5 0 0 1-.6-9A6 6 0 0 1 18 9.5 4 4 0 0 1 17.5 18z"/><path d="M12 10v6m-2.5-2.5L12 16l2.5-2.5"/>',
 left:'<path d="m15 5-7 7 7 7"/>',right:'<path d="m9 5 7 7-7 7"/>',
 sun:'<circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8"/>',
 moon:'<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4 8.5 8.5 0 1 0 20 14.5z"/>',
 loc:'<circle cx="12" cy="12" r="3.5"/><circle cx="12" cy="12" r="8"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>',
 doc:'<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h6"/>',
 clip:'<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4h6v3H9zM9 12h6M9 16h4"/>',
 store:'<path d="M4 9 5.5 4h13L20 9M4 9v11h16V9M4 9c0 2 3 2 4 0 1 2 3 2 4 0 1 2 3 2 4 0 1 2 4 2 4 0M10 20v-5h4v5"/>',
 target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2"/>'
};
const ic=(n,c='')=>`<svg class="ic ${c}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[n]||''}</svg>`;
/* Thin mobile adapter: actual theme state and persistence live in the shared token engine. */
const Theme={get(){return document.documentElement.dataset.theme||Tokens.mode()||'light'},
 apply(){Tokens.mode();const m=document.querySelector('meta[name=theme-color]');if(m)m.content=getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()||m.content},
 toggle(){Tokens.toggle();this.apply();window.onTheme&&window.onTheme()}};
Theme.apply();
window.fa=Shared.fa; window.money=Shared.money; window.jget=Shared.jget; window.jset=Shared.jset; window.today=Shared.today;
const fd=s=>String(s??'').replace(/\d/g,d=>'۰۱۲۳۴۵۶۷۸۹'[d]);
const jalali=(d=new Date())=>{const f=new Intl.DateTimeFormat('fa-IR-u-ca-persian',{weekday:'long',day:'numeric',month:'long',year:'numeric'}).formatToParts(d),g=t=>(f.find(x=>x.type===t)||{}).value||'';return `${g('weekday')} ${g('day')} ${g('month')} ${g('year')}`};
const hav=(a,b,c,d)=>{const R=6371000,r=x=>x*Math.PI/180,dl=r(c-a),dm=r(d-b),h=Math.sin(dl/2)**2+Math.cos(r(a))*Math.cos(r(c))*Math.sin(dm/2)**2;return 2*R*Math.asin(Math.sqrt(h))};
const dist=m=>m<1000?fa(Math.round(m/10)*10)+' متر':fa((m/1000).toFixed(1))+' کیلومتر';
const greet=()=>{const h=new Date().getHours();return h<12?'صبح بخیر':h<17?'ظهر بخیر':h<20?'عصر بخیر':'شب بخیر'};


/* منوی همبرگری مشترک برای اپ ویزیتور و مأمور پخش */
(function(){
  const menuItems=()=>{
    if(typeof TABS!=='undefined'&&Array.isArray(TABS)&&TABS.length){
      return TABS.map(([id,label,icon])=>({id,label,icon}));
    }
    return [
      {id:'home',label:'ماموریت‌های امروز',icon:'clip'},
      {id:'theme',label:'تغییر پوسته',icon:Theme.get()==='dark'?'sun':'moon'},
      {id:'logout',label:'خروج از حساب',icon:'left'}
    ];
  };
  window.closeMobileMenu=()=>{
    document.body.classList.remove('menu-open');
    const b=document.querySelector('.mobile-menu-toggle');
    if(b)b.setAttribute('aria-expanded','false');
  };
  window.toggleMobileMenu=()=>{
    const open=!document.body.classList.contains('menu-open');
    document.body.classList.toggle('menu-open',open);
    const b=document.querySelector('.mobile-menu-toggle');
    if(b)b.setAttribute('aria-expanded',String(open));
  };
  function mount(){
    const root=document.getElementById('app'),shell=root&&root.querySelector('.shell');
    if(!shell||shell.dataset.menuReady==='1')return;
    const header=shell.querySelector('.hdr');
    if(!header)return;
    shell.dataset.menuReady='1';
    const items=menuItems();
    const title=document.title.includes('visitor')?'منوی ویزیتور':'منوی مأمور پخش';
    header.insertAdjacentHTML('afterbegin',`<button class="mobile-menu-toggle" type="button" aria-label="باز کردن منو" aria-expanded="false" onclick="toggleMobileMenu()"><span></span><span></span><span></span></button>`);
    shell.insertAdjacentHTML('beforebegin',`<div class="mobile-menu-backdrop" onclick="closeMobileMenu()"></div><aside class="mobile-drawer" aria-label="${title}"><div class="drawer-head"><div><b>${title}</b><small>دسترسی سریع به بخش‌ها</small></div><button class="drawer-close" type="button" aria-label="بستن منو" onclick="closeMobileMenu()">×</button></div><nav class="drawer-nav">${items.map(x=>`<button type="button" class="drawer-item" onclick="closeMobileMenu();mobileMenuAction('${x.id}')">${ic(x.icon)}<span>${x.label}</span>${x.id==='today'?' <small>امروز</small>':''}</button>`).join('')}</nav><div class="drawer-foot"><span class="drawer-status"><i></i> سیستم آنلاین</span><button type="button" class="drawer-theme" onclick="Theme.toggle();closeMobileMenu()">${ic(Theme.get()==='dark'?'sun':'moon')} تغییر پوسته</button></div></aside>`);
  }
  window.mobileMenuAction=id=>{
    if(id==='theme'){Theme.toggle();return}
    if(id==='logout'){if(typeof logout==='function')logout();return}
    if(id==='home'){if(typeof home==='function')home();return}
    if(typeof home==='function')home(id);
  };
  const observer=new MutationObserver(mount);
  const start=()=>{const root=document.getElementById('app');if(root){observer.observe(root,{childList:true,subtree:true});mount();}};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeMobileMenu()});
})();
