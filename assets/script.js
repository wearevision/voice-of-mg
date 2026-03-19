
// Progreso
window.addEventListener('scroll',()=>{
  const p=(window.scrollY/(document.body.scrollHeight-window.innerHeight))*100;
  document.getElementById('prog').style.width=p+'%';
});

// Nav activo
const secs=document.querySelectorAll('section[id], div[id="part-break"]');
const navs=document.querySelectorAll('.nav-link');
new IntersectionObserver(entries=>{
  entries.forEach(e=>{
    if(e.isIntersecting){
      const id=e.target.id;
      navs.forEach(l=>l.classList.toggle('active',l.getAttribute('href')==='#'+id));
    }
  });
},{threshold:0.4}).observe.apply(null,[...secs].map(s=>s));
// fix: observe each
secs.forEach(s=>new IntersectionObserver(entries=>{
  entries.forEach(e=>{if(e.isIntersecting){const id=e.target.id;navs.forEach(l=>l.classList.toggle('active',l.getAttribute('href')==='#'+id));}}
},{threshold:0.4}).observe(s));

// Anims
new IntersectionObserver(entries=>{
  entries.forEach(e=>{if(e.isIntersecting)e.target.classList.add('in');});
},{threshold:0.1,rootMargin:'0px 0px -40px 0px'}).observe.apply(null,[]);
document.querySelectorAll('.anim').forEach(el=>{
  new IntersectionObserver(entries=>{entries.forEach(e=>{if(e.isIntersecting)e.target.classList.add('in');});},{threshold:0.1,rootMargin:'0px 0px -40px 0px'}).observe(el);
});

// Modal
function openModal(id){document.getElementById(id).classList.add('open');document.body.style.overflow='hidden'}
function closeModal(id){document.getElementById(id).classList.remove('open');document.body.style.overflow=''}
document.querySelectorAll('.modal-overlay').forEach(o=>{
  o.addEventListener('click',e=>{if(e.target===o){o.classList.remove('open');document.body.style.overflow=''}});
});
document.addEventListener('keydown',e=>{
  if(e.key==='Escape')document.querySelectorAll('.modal-overlay.open').forEach(m=>{m.classList.remove('open');document.body.style.overflow=''});
});

// ── LEAFLET MAP ──────────────────────────────────────
document.addEventListener('DOMContentLoaded',()=>{
  const map = L.map('leaflet-map',{
    center:[-33.443,-70.614],zoom:14,
    zoomControl:true,attributionControl:false
  });

  // OSM tiles con estilo oscuro-cálido compatible MG
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_matter/{z}/{x}/{y}{r}.png',{
    maxZoom:19,subdomains:'abcd'
  }).addTo(map);

  // Custom icon factory
  function makeIcon(label,color='#A00022'){
    return L.divIcon({
      className:'',
      html:`<div style="width:34px;height:34px;background:${color};border:2.5px solid #fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:'FavoritMono',monospace;font-weight:700;font-size:11px;color:#fff;box-shadow:0 2px 10px rgba(0,0,0,.5);cursor:pointer;transition:transform .2s">${label}</div>`,
      iconSize:[34,34],iconAnchor:[17,17]
    });
  }
  function makeMetroIcon(name){
    return L.divIcon({
      className:'',
      html:`<div style="background:#0066CC;border:2px solid #fff;border-radius:4px;padding:3px 6px;font-family:'FavoritMono',monospace;font-size:8px;font-weight:700;color:#fff;white-space:nowrap;box-shadow:0 1px 6px rgba(0,0,0,.4)">M ${name}</div>`,
      iconSize:[null,22],iconAnchor:[0,11]
    });
  }
  function makeParkIcon(){
    return L.divIcon({
      className:'',
      html:`<div style="width:20px;height:20px;background:#1E7A45;border:2px solid #fff;border-radius:3px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:10px;color:#fff;box-shadow:0 1px 5px rgba(0,0,0,.4)">P</div>`,
      iconSize:[20,20],iconAnchor:[10,10]
    });
  }

  // VENUES
  const venues=[
    {id:'m-v1',lat:-33.4454,lng:-70.6256,label:'1',name:'Galpón Italia'},
    {id:'m-v2',lat:-33.4318,lng:-70.5921,label:'2',name:'Club Providencia'},
    {id:'m-v3',lat:-33.4553,lng:-70.6197,label:'3',name:'Castillo Ñuñoa'},
    {id:'m-v4',lat:-33.4130,lng:-70.6070,label:'4',name:'Providencia Casa'},
    {id:'m-v5',lat:-33.3967,lng:-70.5981,label:'5',name:'Galería P. Ready'},
    {id:'m-v6',lat:-33.4388,lng:-70.6038,label:'6',name:'Centro Lyon'},
  ];
  venues.forEach(v=>{
    const m=L.marker([v.lat,v.lng],{icon:makeIcon(v.label)}).addTo(map);
    m.bindTooltip(`<span style="font-family:'FavoritMono',monospace;font-size:10px;font-weight:700">${v.name}</span>`,{permanent:false,direction:'top',className:'leaflet-tooltip'});
    m.on('click',()=>openModal(v.id));
  });

  // METRO STATIONS (Línea 1 sector)
  const metros=[
    {lat:-33.4251,lng:-70.6098,name:'Baquedano'},
    {lat:-33.4249,lng:-70.6115,name:'Ped. Valdivia'},
    {lat:-33.4237,lng:-70.6094,name:'Tobalaba'},
    {lat:-33.4387,lng:-70.6038,name:'Los Leones'},
    {lat:-33.4165,lng:-70.5952,name:'Esc. Militar'},
    {lat:-33.4553,lng:-70.6197,name:'Irarrázaval'},
  ];
  metros.forEach(m=>{
    L.marker([m.lat,m.lng],{icon:makeMetroIcon(m.name)}).addTo(map);
  });

  // ESTACIONAMIENTOS PÚBLICOS
  const parkings=[
    {lat:-33.4320,lng:-70.5950},
    {lat:-33.4440,lng:-70.6210},
    {lat:-33.4390,lng:-70.6055},
    {lat:-33.4270,lng:-70.6080},
  ];
  parkings.forEach(p=>{
    L.marker([p.lat,p.lng],{icon:makeParkIcon()}).addTo(map);
  });

  // Style map overlay color tint to match MG palette
  document.getElementById('leaflet-map').style.filter='sepia(15%) hue-rotate(320deg)';
});
