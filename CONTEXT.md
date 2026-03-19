# The Voice of MG 2026 — WAV BTL
## Contexto completo para Claude Code

---

## Cliente
**MG Motor Chile (SMIL)**
- Kyle — GM, aprueba presupuesto
- Alfredo Guzmán — Product Manager / Market Research & Intelligence, contacto operativo
- Sistema SOR de 3 rondas de negociación antes de adjudicación
- Deadline propuesta: 19 marzo 2026

## WAV BTL
- Agencia BTL y marketing experiencial chilena (wearevision.cl)
- Director del proyecto: Federico Elgueta Edwards (federico@wearevision.cl)
- **Ventaja competitiva clave:** WAV ejecutó el focus group de enero 2026. Somos los únicos que conocemos a los clientes MG de primera mano. Ningún competidor tiene ese contexto.

---

## Estructura de la propuesta

### Parte I — Propuesta Base
- 4 sesiones anuales (Mar / Jun / Sep / Dic)
- 60 participantes por sesión = **240 voces al año**
- 3 días × 2 sub-sesiones / día × 10 invitados + 3 MG + 1 moderador = 14 personas por sala
- **Precio: $87M CLP neto anual** ($21,75M/sesión · $362K/pax)
- Entregables: 4 videos (1 día grabado/sesión) + 4 informes PDF bilingüe ESP+ENG

### Parte II — WAV Intelligence (upgrade)
- 90 participantes por sesión = **360 voces al año** (+50%)
- 20× micrófonos lavalier individuales (grabación 32-bit float, microSD independiente)
- Cámara 360° como eje de sincronización audio/video
- Dashboard navegable: timeline, keypoints, búsqueda semántica, pregunta libre
- Diarización automática con atribución por nombre
- **Precio adicional: +$24M CLP neto anual**
- **Total programa completo: $111M CLP neto anual** ($305K/pax · −16% vs base)

---

## Hallazgos enero 2026 — argumento de venta principal
*(WAV los descubrió — son propietarios de este conocimiento)*

1. **"Victoria Visual, Fracaso Digital"** — el diseño atrae y enamora, el infotainment frustra y aleja
2. **Garantía "rehén"** — clientes forzados a elegir entre garantía de fábrica y seguridad vehicular
3. **Lealtad tribal orgánica** — comunidad MG sin incentivo corporativo, completamente espontánea
4. **Sensación de "engaño"** — en el proceso de venta, expectativas vs realidad
5. **Cinismo hacia "precio desde"** — los asteriscos y letra chica generan desconfianza activa

---

## Sistema visual MG (Brandbook V1.0)

### Colores oficiales
| Nombre | HEX | Uso |
|--------|-----|-----|
| MG Red | `#A00022` | Color principal, acento, Heatwood |
| MG Burgundy | `#28001E` | Fondos oscuros Parte II |
| MG Smoke | `#FD2F33` | Acento en secciones WAV Intelligence |
| MG White | `#F7F3EF` | Fondo warm off-white |
| Pure White | `#FFFFFF` | Fondo puro |
| MG Black | `#000000` | Texto principal |

### Tipografía oficial
- **Favorit** (Light/Regular/Medium/Bold) — cuerpo y headlines. En `MG_Fonts.zip`
- **Favorit Mono** — etiquetas UPPERCASE, tracking +10%. En `MG_Fonts.zip`
- **Heatwood** — script, máximo 2 palabras, SOLO en rojo `#A00022`, siempre acompañado de Favorit. En `MG_Fonts.zip`

### Reglas de diseño
- Logo solo en negro / blanco / rojo
- No rotar texto
- Heatwood NUNCA sin Favorit
- No costos de ítems individuales visibles
- No ratings de Google de venues
- No mencionar marcas de equipos (solo cualidades técnicas)
- No análisis facial (eliminado del scope)

---

## Arquitectura técnica del HTML

### Sistema de modales (CRÍTICO)
- Usar `data-modal="id"` en elementos clickeables — NUNCA `onclick="openModal()"`
- Usar `data-close="id"` en botones de cerrar — NUNCA `onclick="closeModal()"`
- `.modal-overlay` debe tener `pointer-events:none` en estado cerrado
- `.modal-overlay.open` debe tener `visibility:visible` + `opacity:1` + `pointer-events:all`
- `.mod-overlay` (overlay de fotos de moderadores) debe tener `pointer-events:none` siempre
- z-index de modales: `9999`
- Al abrir modal: bloquear scroll en `document.documentElement` Y `document.body`
- Al cerrar modal: restaurar ambos

### Mapa Leaflet
- CDN: `https://unpkg.com/leaflet@1.9.4/dist/leaflet.css` y `.js`
- Tiles: CartoDB dark_matter con tinte MG (`sepia(20%) hue-rotate(315deg) brightness(0.9)`)
- Inicializar con retry loop (cada 300ms, máximo 30 intentos)
- Llamar `map.invalidateSize()` cuando la sección entre al viewport (IntersectionObserver)
- Iconos: venues en rojo `#A00022`, metro en azul `#0055AA`, estacionamientos en verde `#1E7A45`

### CSS
- Un solo bloque `<style>` para fuentes (base64 del ZIP)
- Un solo bloque `<style>` para UI CSS
- CERO duplicados de ninguna regla
- Sin CSS inyectado en múltiples pasadas

### JS
- Usar funciones clásicas `function(){}` — no arrow functions en event handlers principales
- Event delegation para modales (un solo `document.addEventListener('click')`)
- Sin template literals con comillas anidadas

---

## Venues (6 opciones)
| # | Nombre | Barrio | Metro | Estac. | Auto MG |
|---|--------|--------|-------|--------|---------|
| 1 | Galpón Italia | Barrio Italia | Irarrázaval 5' | Calle gratis | ✅ Entra directo |
| 2 | Club Providencia | Providencia | Ped. Valdivia 8' | Privado en recinto | ✅ Jardín |
| 3 | Castillo Ñuñoa | Ñuñoa | Irarrázaval 4' | Calle | ✅ Jardín 270m² |
| 4 | Providencia Casa | Providencia | Tobalaba 10' | 8 privados | ✅ Jardín |
| 5 | Galería Patricia Ready | Vitacura | Esc. Militar ~10' auto | Calle | ✅ Ha hecho lanzamientos |
| 6 | Centro Lyon | Providencia | Los Leones 5' | Interior cubierto | ✅ Entrada coordinada |

---

## Moderadores (5 alternativas)
1. **Constanza Del Rosario Merino** — Psicóloga clínica, PUC + Máster Zaragoza + INEFOC Madrid
2. **Gabriel Baeza** — Ingeniero Civil Industrial + periodista automotriz, Fundador Rutamotor, jurado World Car Awards
3. **Leonardo Mellado** — Director editorial Tacómetro/Publimetro, +30 años periodismo automotriz
4. **María Asunción Cekalovick** — Asistente Social INACAP + Magíster USACH, especialista focus groups
5. **Paula Olmedo Kaempffer** — Periodista, editora L'Officiel Chile, +20 años entrevistas en profundidad

---

## Convocatoria — principios clave
- El líder del proyecto (Federico) hace el primer contacto personal — no un call center
- Tono: "dentro de una gran base, buscamos TU opinión específica"
- Flujo: WhatsApp personalizado D-18 → Email confirmación → WhatsApp cupo numerado → 3 recordatorios
- Cupo numerado visible desde mensaje 1: "eres el #7 de 10"
- Incentivo visible desde mensaje 1 (gift card)
- Meta: +85% asistencia efectiva (enero fue 40% con call center)

---

## Microfonía

### Versión Base (Parte I)
Sistema mixto: micrófonos **ambientales** + **caña ambiental** + **semi-direccionales**
- 20 unidades totales (14 activas + 6 respaldo)
- Cada unidad graba en pista independiente
- Post-producción: mezcla en una sola pista limpia y pareja
- Base esencial para transcripción y subtitulado

### WAV Intelligence (Parte II)
- 20× lavalier individual: grabación **32-bit float**, **microSD independiente** por participante
- Cámara 360°: eje de sincronización audio/video, NO análisis facial
- Pipeline: pistas individuales → transcripción + diarización con nombres → sincronización por timestamp → dashboard navegable

---

## Decisiones de negocio clave
- Cuando dudes entre dos opciones de diseño, elige la que maximiza el valor percibido por Kyle y Alfredo
- El argumento más poderoso: WAV ya lo hizo — no es una promesa, es una demostración
- La Parte II no es "el mismo presupuesto con más" — es una inversión adicional de $24M con retorno claro
- No mostrar costos individuales de ningún ítem de producción
- El mapa necesita internet para cargar — documentar esto si hay fallback

---

## Archivos en este directorio
- `MG_Fonts.zip` — fuentes oficiales Favorit, Favorit Mono, Heatwood
- `Sirius_Entrevistadores.pdf` — fotos y datos de los 5 moderadores
- `MG Motor Chile - Reporte Focus Group ESP & ENG.md` — hallazgos enero 2026
- `Brieff.rtf` — brief original del cliente
- `output/` — aquí va el HTML generado
