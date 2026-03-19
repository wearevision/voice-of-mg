#!/usr/bin/env python3
"""
build.py — The Voice of MG 2026
Generates output/index.html from extracted assets.

Critical fixes applied:
1. Modals use data-modal / data-close (no onclick in HTML)
2. .modal-overlay has pointer-events:none when closed
3. Single CSS block, no duplicates
4. Leaflet map with invalidateSize in IntersectionObserver
5. Updated prices: base $87M, Intelligence +$24M, total $111M
"""

import json
import re
import shutil
from pathlib import Path

BASE = Path(__file__).parent
ASSETS = BASE / "assets"
OUTPUT = BASE / "output"


def read_file(path):
    return Path(path).read_text(encoding="utf-8")


def load_font_base64(family, weight):
    fname = ASSETS / "fonts" / f"{family}_w{weight}.b64"
    return fname.read_text(encoding="utf-8")


def build_font_faces():
    declarations = json.loads((ASSETS / "font_declarations.json").read_text())
    css = ""
    for d in declarations:
        b64 = load_font_base64(d["family"], d["weight"])
        css += (
            f"@font-face{{font-family:'{d['family']}';"
            f"src:url('{b64}');"
            f"font-weight:{d['weight']}}}\n"
        )
    return css


def fix_css(raw_css):
    """Deduplicate CSS rules and apply modal fix."""
    # Remove duplicate .mod-mosaic and .mod-card blocks
    # The CSS has two .mod-mosaic definitions — keep the second (more complete) one
    # Split into rules and deduplicate
    css = raw_css

    # Modal overlay fixes are now applied directly in styles.css

    # Remove first duplicate .mod-mosaic block (4-column generic version)
    # Keep the second (1fr 2fr 1fr — detailed version used in the page)
    first_block = "/* MODERATORS MOSAIC */\n"
    idx = css.find(first_block)
    if idx == -1:
        # Fallback: find the first .mod-mosaic with repeat(4
        idx = css.find(".mod-mosaic{display:grid;grid-template-columns:repeat(4,1fr)")
    if idx > -1:
        # Find where this block ends (before the next major comment or the second .mod-mosaic)
        second_mosaic = css.find("/* MOD MOSAIC */")
        if second_mosaic > -1 and second_mosaic > idx:
            css = css[:idx] + css[second_mosaic:]
        else:
            # Remove from first .mod-mosaic{repeat(4 to just before second .mod-mosaic{1fr 2fr
            end = css.find(".mod-mosaic{display:grid;grid-template-columns:1fr 2fr")
            if end > idx:
                css = css[:idx] + css[end:]

    return css


def fix_sections(html):
    """Apply content fixes to section HTML."""
    # Prices: base $87M, Intelligence +$24M, total $111M

    # 1. Hero/investment base: $80M -> $87M
    # Large display number: $80<span...>M</span>
    html = html.replace('">$80<span', '">$87<span')
    html = html.replace("$80 M CLP", "$87 M CLP")
    # Per-session: $87M / 4 = $21.75M
    html = html.replace(
        "$20M por sesión trimestral",
        "$21,75M por sesión trimestral"
    )
    html = html.replace(
        ">$20M</div>",
        ">$21,75M</div>"
    )
    # Cost per participant: $87M / 240 = $362.5K
    html = html.replace(
        "$333K costo por participante",
        "$362K costo por participante"
    )
    html = html.replace("$333.333", "$362.500")

    # 2. ROI section — base line item
    html = html.replace(
        'Propuesta Base · 4 sesiones</div><div class="roi-val" style="font-size:26px">$80M',
        'Propuesta Base · 4 sesiones</div><div class="roi-val" style="font-size:26px">$87M'
    )
    # Intelligence add-on: was +$20M, now +$24M
    html = html.replace(
        'roi-val" style="font-size:26px;color:var(--smoke)">+$20M',
        'roi-val" style="font-size:26px;color:var(--smoke)">+$24M'
    )
    # Total: was $100M, now $111M
    html = html.replace(
        'Total programa completo anual</div><div class="roi-val">$100M',
        'Total programa completo anual</div><div class="roi-val">$111M'
    )
    # ROI box text
    html = html.replace(
        "La inversión adicional de $20M",
        "La inversión adicional de $24M"
    )

    # 3. Comparativa table header
    html = html.replace("Propuesta Base ($80M)", "Propuesta Base ($87M)")
    html = html.replace("+ WAV Intelligence ($100M)", "+ WAV Intelligence ($24M)")

    # 4. Other $80M references -> $87M
    html = html.replace("$80M", "$87M")

    # 5. Cost per contact WAV Intelligence
    html = html.replace("$278.000", "$308.333")

    # Fix: remove all onclick attributes from sections
    html = re.sub(r'\s*onclick="openModal\(\'(m-[^\']+)\'\)"', r' data-modal="\1"', html)

    return html


def fix_modals(modals_dict):
    """Convert modals from onclick to data-close pattern."""
    fixed = {}
    for mid, content in modals_dict.items():
        # Replace onclick="closeModal('m-xxx')" with data-close
        content = re.sub(
            r'onclick="closeModal\(\'[^\']+\'\)"',
            'data-close',
            content
        )
        # Ensure modal-overlay class is present
        if 'class="modal-overlay"' not in content:
            content = content.replace(
                f'id="{mid}"',
                f'class="modal-overlay" id="{mid}"'
            )
        fixed[mid] = content
    return fixed


def build_js():
    """Build clean JavaScript with all fixes per CONTEXT.md."""
    return """
// ── PROGRESS BAR ──
window.addEventListener('scroll', function(){
  var p = (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100;
  document.getElementById('prog').style.width = p + '%';
});

// ── NAV ACTIVE STATE ──
document.querySelectorAll('section[id]').forEach(function(s){
  new IntersectionObserver(function(entries){
    entries.forEach(function(e){
      if(e.isIntersecting){
        var id = e.target.id;
        document.querySelectorAll('.nav-link').forEach(function(l){
          l.classList.toggle('active', l.getAttribute('href') === '#' + id);
        });
      }
    });
  }, {threshold: 0.4}).observe(s);
});

// ── SCROLL ANIMATIONS ──
document.querySelectorAll('.anim').forEach(function(el){
  new IntersectionObserver(function(entries){
    entries.forEach(function(e){ if(e.isIntersecting) e.target.classList.add('in'); });
  }, {threshold: 0.1, rootMargin: '0px 0px -40px 0px'}).observe(el);
});

// ── MODALS — event delegation, scroll lock on body + documentElement ──
function lockScroll(){
  document.body.style.overflow = 'hidden';
  document.documentElement.style.overflow = 'hidden';
}
function unlockScroll(){
  document.body.style.overflow = '';
  document.documentElement.style.overflow = '';
}

document.addEventListener('click', function(e){
  // Open: any element with [data-modal]
  var opener = e.target.closest('[data-modal]');
  if(opener){
    var id = opener.getAttribute('data-modal');
    var modal = document.getElementById(id);
    if(modal){ modal.classList.add('open'); lockScroll(); }
    return;
  }
  // Close: button with [data-close]
  if(e.target.closest('[data-close]')){
    var overlay = e.target.closest('.modal-overlay');
    if(overlay){ overlay.classList.remove('open'); unlockScroll(); }
    return;
  }
  // Close: click on overlay backdrop
  if(e.target.classList.contains('modal-overlay') && e.target.classList.contains('open')){
    e.target.classList.remove('open'); unlockScroll();
  }
});

document.addEventListener('keydown', function(e){
  if(e.key === 'Escape'){
    document.querySelectorAll('.modal-overlay.open').forEach(function(m){
      m.classList.remove('open');
    });
    unlockScroll();
  }
});

// ── MODERATOR CAROUSEL ──
(function(){
  var track = document.getElementById('mod-track');
  var dots = document.getElementById('mod-dots');
  var prev = document.getElementById('mod-prev');
  var next = document.getElementById('mod-next');
  if(!track || !dots) return;

  var slides = track.querySelectorAll('.mod-slide');
  var dotEls = dots.querySelectorAll('.mod-dot');
  var current = 0;
  var total = slides.length;

  function goTo(idx){
    if(idx < 0) idx = total - 1;
    if(idx >= total) idx = 0;
    current = idx;
    track.style.transform = 'translateX(-' + (current * 100) + '%)';
    for(var i = 0; i < slides.length; i++){
      slides[i].classList.toggle('active', i === current);
    }
    for(var j = 0; j < dotEls.length; j++){
      dotEls[j].classList.toggle('active', j === current);
    }
  }

  if(prev) prev.addEventListener('click', function(){ goTo(current - 1); });
  if(next) next.addEventListener('click', function(){ goTo(current + 1); });
  dots.addEventListener('click', function(e){
    var dot = e.target.closest('.mod-dot');
    if(!dot) return;
    goTo(parseInt(dot.getAttribute('data-mod'), 10));
  });

  // Auto-advance every 6s
  var autoTimer = setInterval(function(){ goTo(current + 1); }, 6000);
  track.addEventListener('mouseenter', function(){ clearInterval(autoTimer); });
  track.addEventListener('mouseleave', function(){
    autoTimer = setInterval(function(){ goTo(current + 1); }, 6000);
  });

  // Touch swipe
  var startX = 0;
  track.addEventListener('touchstart', function(e){ startX = e.touches[0].clientX; clearInterval(autoTimer); }, {passive:true});
  track.addEventListener('touchend', function(e){
    var diff = startX - e.changedTouches[0].clientX;
    if(Math.abs(diff) > 50){ goTo(diff > 0 ? current + 1 : current - 1); }
  }, {passive:true});
})();

// ── MOBILE NAV HAMBURGER ──
(function(){
  var toggle = document.getElementById('nav-toggle');
  var links = document.getElementById('nav-links');
  if(!toggle || !links) return;
  toggle.addEventListener('click', function(){
    toggle.classList.toggle('open');
    links.classList.toggle('open');
  });
  links.addEventListener('click', function(e){
    if(e.target.tagName === 'A'){
      toggle.classList.remove('open');
      links.classList.remove('open');
    }
  });
})();

// ── LEAFLET MAP — flyTo + sidebar + IntersectionObserver ──
document.addEventListener('DOMContentLoaded', function(){
  var mapEl = document.getElementById('leaflet-map');
  if(!mapEl) return;

  var map = null;
  var mapInitAttempts = 0;
  var activeMarker = null;

  // Venue data with details for sidebar
  var VENUE_DATA = {
    'm-v1': {name:'Galpón Italia',addr:'Italia 1242, Ñuñoa',cap:'80 pax',feat:'Espacio industrial reconvertido · techos altos · acceso vehicular directo · estacionamiento privado 20 autos',vibe:'Industrial premium. Ideal para mostrar autos en contexto urbano.'},
    'm-v2': {name:'Club Providencia',addr:'Av. Providencia 2124',cap:'120 pax',feat:'Salón principal + terraza · equipamiento AV incluido · cocina industrial · valet disponible',vibe:'Clásico elegante. Ubicación céntrica, fácil acceso metro.'},
    'm-v3': {name:'Castillo Ñuñoa',addr:'Jorge Washington 201',cap:'60 pax',feat:'Casa patrimonial · jardín interior · iluminación ambiental · acceso vehicular lateral',vibe:'Íntimo y exclusivo. Grupos pequeños de alto perfil.'},
    'm-v4': {name:'Providencia Casa',addr:'Guardia Vieja 255',cap:'50 pax',feat:'Casa remodelada · 3 salones conectables · patio trasero cubierto · cocina equipada',vibe:'Residencial cálido. Focus groups que requieren confianza.'},
    'm-v5': {name:'Galería Patricia Ready',addr:'Espoz 3125, Vitacura',cap:'100 pax',feat:'Galería de arte · espacios blancos amplios · acceso vehicular + rampa · iluminación profesional',vibe:'Vanguardia. El auto como pieza central de una galería.'},
    'm-v6': {name:'Centro Lyon',addr:'Av. Lyon 0123',cap:'90 pax',feat:'Edificio corporativo · sala conferencias + breakout rooms · catering integrado',vibe:'Corporativo moderno. Sesiones ejecutivas con servicios incluidos.'}
  };

  // Create sidebar early (before initMap)
  var sidebar = document.createElement('div');
  sidebar.className = 'map-sidebar';
  sidebar.id = 'map-sidebar';
  sidebar.innerHTML = '<div style="font-family:var(--mono);font-size:8px;letter-spacing:2px;color:rgba(255,255,255,.3);text-transform:uppercase;padding:20px">Haz click en un pin para ver el detalle</div>';
  var mapContainer = document.getElementById('map-container');
  if(mapContainer) mapContainer.appendChild(sidebar);

  function showVenue(vid){
    var d = VENUE_DATA[vid];
    if(!d) return;
    sidebar.innerHTML = '<div style="padding:20px;position:relative">' +
      '<button id="map-sidebar-close" style="position:absolute;top:12px;right:14px;background:none;border:none;color:rgba(255,255,255,.4);cursor:pointer;font-size:14px">✕</button>' +
      '<div style="font-family:var(--mono);font-size:7px;letter-spacing:2px;color:var(--smoke);text-transform:uppercase;margin-bottom:8px">Venue</div>' +
      '<div style="font-size:18px;font-weight:700;color:white;margin-bottom:4px">' + d.name + '</div>' +
      '<div style="font-family:var(--mono);font-size:9px;color:rgba(255,255,255,.4);margin-bottom:16px">' + d.addr + '</div>' +
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px">' +
        '<div style="background:rgba(255,255,255,.04);padding:10px;border-radius:3px"><div style="font-family:var(--mono);font-size:7px;letter-spacing:1px;color:rgba(255,255,255,.3);text-transform:uppercase;margin-bottom:3px">Capacidad</div><div style="font-size:14px;font-weight:600;color:white">' + d.cap + '</div></div>' +
        '<div style="background:rgba(255,255,255,.04);padding:10px;border-radius:3px"><div style="font-family:var(--mono);font-size:7px;letter-spacing:1px;color:rgba(255,255,255,.3);text-transform:uppercase;margin-bottom:3px">Acceso auto</div><div style="font-size:14px;font-weight:600;color:#4CAF78">✓ Sí</div></div>' +
      '</div>' +
      '<div style="font-size:12px;color:rgba(255,255,255,.55);line-height:1.7;margin-bottom:14px">' + d.feat + '</div>' +
      '<div style="padding:12px;background:rgba(160,0,34,.06);border:1px solid rgba(160,0,34,.12);border-radius:4px">' +
        '<div style="font-family:var(--mono);font-size:7px;letter-spacing:1px;color:var(--smoke);text-transform:uppercase;margin-bottom:4px">Ambiente</div>' +
        '<div style="font-size:12px;color:rgba(255,255,255,.6);font-style:italic;line-height:1.5">' + d.vibe + '</div>' +
      '</div>' +
      '<div data-modal="' + vid + '" style="margin-top:14px;text-align:center;font-family:var(--mono);font-size:8px;letter-spacing:2px;text-transform:uppercase;color:var(--smoke);cursor:pointer;padding:8px;border:1px solid rgba(160,0,34,.2);border-radius:3px">Ver galería completa →</div>' +
    '</div>';
    sidebar.classList.add('active');
    var closeBtn = document.getElementById('map-sidebar-close');
    if(closeBtn) closeBtn.addEventListener('click', function(){ sidebar.classList.remove('active'); });
  }

  function initMap(){
    if(map) return true;
    if(typeof L === 'undefined'){
      mapInitAttempts++;
      if(mapInitAttempts < 30) setTimeout(initMap, 300);
      return false;
    }
    map = L.map('leaflet-map', {
      center: [-33.435, -70.610], zoom: 13,
      zoomControl: true, attributionControl: false
    });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, attribution: ''
    }).addTo(map);

    function makeIcon(label, color, isActive){
      color = color || '#A00022';
      var size = isActive ? 44 : 34;
      var border = isActive ? '3px solid #FD2F33' : '2.5px solid #fff';
      var shadow = isActive ? '0 0 16px rgba(253,47,51,.6)' : '0 2px 10px rgba(0,0,0,.5)';
      return L.divIcon({
        className: '',
        html: '<div style="width:'+size+'px;height:'+size+'px;background:'+color+';border:'+border+';border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:FavoritMono,monospace;font-weight:700;font-size:'+(isActive?14:11)+'px;color:#fff;box-shadow:'+shadow+';cursor:pointer;transition:all .3s">'+label+'</div>',
        iconSize: [size,size], iconAnchor: [size/2,size/2]
      });
    }
    function makeMetroIcon(name){
      return L.divIcon({
        className: '',
        html: '<div style="background:#0055AA;border:2px solid #fff;border-radius:4px;padding:3px 6px;font-family:FavoritMono,monospace;font-size:8px;font-weight:700;color:#fff;white-space:nowrap;box-shadow:0 1px 6px rgba(0,0,0,.4)">M '+name+'</div>',
        iconSize: [null,22], iconAnchor: [0,11]
      });
    }
    function makeParkIcon(){
      return L.divIcon({
        className: '',
        html: '<div style="width:20px;height:20px;background:#1E7A45;border:2px solid #fff;border-radius:3px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:10px;color:#fff;box-shadow:0 1px 5px rgba(0,0,0,.4)">P</div>',
        iconSize: [20,20], iconAnchor: [10,10]
      });
    }

    var venues = [
      {id:'m-v1',lat:-33.4454,lng:-70.6256,label:'1',name:'Galpón Italia'},
      {id:'m-v2',lat:-33.4318,lng:-70.5921,label:'2',name:'Club Providencia'},
      {id:'m-v3',lat:-33.4553,lng:-70.6197,label:'3',name:'Castillo Ñuñoa'},
      {id:'m-v4',lat:-33.4130,lng:-70.6070,label:'4',name:'Providencia Casa'},
      {id:'m-v5',lat:-33.3967,lng:-70.5981,label:'5',name:'Galería P. Ready'},
      {id:'m-v6',lat:-33.4388,lng:-70.6038,label:'6',name:'Centro Lyon'}
    ];
    var venueMarkers = {};
    venues.forEach(function(v){
      var m = L.marker([v.lat, v.lng], {icon: makeIcon(v.label)}).addTo(map);
      venueMarkers[v.id] = {marker: m, data: v};
      m.bindTooltip('<span style="font-family:FavoritMono,monospace;font-size:10px;font-weight:700">' + v.name + '</span>', {permanent:false, direction:'top'});
      m.on('click', function(){
        // Reset previous active marker
        if(activeMarker && venueMarkers[activeMarker]){
          var prev = venueMarkers[activeMarker];
          prev.marker.setIcon(makeIcon(prev.data.label));
        }
        // Activate this marker
        activeMarker = v.id;
        m.setIcon(makeIcon(v.label, '#A00022', true));
        // Fly to venue
        map.flyTo([v.lat, v.lng], 16, {duration: 0.8});
        // Show sidebar
        showVenue(v.id);
        // Resize after fly
        setTimeout(function(){ map.invalidateSize(); }, 900);
      });
    });

    var metros = [
      {lat:-33.4251,lng:-70.6098,name:'Baquedano'},
      {lat:-33.4249,lng:-70.6115,name:'Ped. Valdivia'},
      {lat:-33.4237,lng:-70.6094,name:'Tobalaba'},
      {lat:-33.4387,lng:-70.6038,name:'Los Leones'},
      {lat:-33.4165,lng:-70.5952,name:'Esc. Militar'},
      {lat:-33.4553,lng:-70.6197,name:'Irarrázaval'}
    ];
    metros.forEach(function(m){ L.marker([m.lat, m.lng], {icon: makeMetroIcon(m.name)}).addTo(map); });

    var parkings = [
      {lat:-33.4320,lng:-70.5950},
      {lat:-33.4440,lng:-70.6210},
      {lat:-33.4390,lng:-70.6055},
      {lat:-33.4270,lng:-70.6080}
    ];
    parkings.forEach(function(p){ L.marker([p.lat, p.lng], {icon: makeParkIcon()}).addTo(map); });

    mapEl.style.filter = 'sepia(20%) hue-rotate(315deg) brightness(0.9)';
    return true;
  }

  var mapSection = document.getElementById('map-section') || mapEl.closest('section');
  if(mapSection){
    new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        if(e.isIntersecting){
          initMap();
          setTimeout(function(){ if(map) map.invalidateSize(); }, 200);
          setTimeout(function(){ if(map) map.invalidateSize(); }, 600);
          setTimeout(function(){ if(map) map.invalidateSize(); }, 1200);
        }
      });
    }, {threshold: 0.05}).observe(mapSection);
  }
});
"""


def build():
    print("Building The Voice of MG 2026...")

    # 1. Load components
    font_css = build_font_faces()
    raw_css = read_file(ASSETS / "styles.css")
    sections_html = read_file(ASSETS / "sections.html")
    dashboard_html = read_file(ASSETS / "dashboard_mockup.html")
    modals_raw = json.loads((ASSETS / "modals_data.json").read_text())

    # 2. Apply fixes
    css = fix_css(raw_css)
    sections_html = fix_sections(sections_html)
    # Insert dashboard mockup before comparativa section
    sections_html = sections_html.replace(
        '<!-- ═══ SLIDE 13 — COMPARATIVA ROI',
        dashboard_html + '\n<!-- ═══ SLIDE 13 — COMPARATIVA ROI'
    )
    modals = fix_modals(modals_raw)
    js = build_js()

    # 3. Assemble modals HTML
    modals_html = "\n<!-- ════════════════════════════════════════════════\n     MODALES\n════════════════════════════════════════════════ -->\n"
    # Group modals by category
    groups = {
        "observaciones": ["m-conv", "m-micro", "m-catering-obs", "m-estructura"],
        "pasos": ["m-step1", "m-step2", "m-step3", "m-step4"],
        "entregables": ["m-video", "m-reporte", "m-convoc-report"],
        "intelligence": ["m-lav", "m-360", "m-diar", "m-perfil", "m-sync", "m-dash", "m-search", "m-trend"],
        "superpoderes": ["m-p1", "m-p2", "m-p3", "m-p4", "m-p5"],
        "venues": ["m-v1", "m-v2", "m-v3", "m-v4", "m-v5", "m-v6"],
        "moderadores": ["m-mod1", "m-mod2", "m-mod3", "m-mod4", "m-mod5"],
    }
    for group_name, ids in groups.items():
        modals_html += f"\n<!-- {group_name} -->\n"
        for mid in ids:
            if mid in modals:
                modals_html += modals[mid] + "\n"

    # 4. Assemble full HTML
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Voice of MG 2026 — WAV BTL</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
{font_css}
{css}
</style>
</head>
<body>
{sections_html}
{modals_html}
<script>{js}</script>
</body>
</html>"""

    # 5. Write output
    OUTPUT.mkdir(exist_ok=True)
    out_path = OUTPUT / "index.html"
    out_path.write_text(html, encoding="utf-8")

    # 6. Copy background images to output
    bg_src = ASSETS / "bg_photos"
    bg_dst = OUTPUT / "img"
    if bg_src.exists():
        bg_dst.mkdir(exist_ok=True)
        for img in bg_src.glob("*.jpg"):
            shutil.copy2(img, bg_dst / img.name)

    # Stats
    size_kb = out_path.stat().st_size / 1024
    lines = len(html.splitlines())
    onclick_count = len(re.findall(r"onclick", html))
    style_blocks = len(re.findall(r"<style", html))
    data_modal_count = len(re.findall(r"data-modal", html))
    data_close_count = len(re.findall(r"data-close", html))

    print(f"\n✓ Built: {out_path}")
    print(f"  Size: {size_kb:.0f} KB ({lines} lines)")
    print(f"  Style blocks: {style_blocks}")
    print(f"  onclick in HTML: {onclick_count}")
    print(f"  data-modal triggers: {data_modal_count}")
    print(f"  data-close buttons: {data_close_count}")


if __name__ == "__main__":
    build()
