# Architecture

**Analysis Date:** 2025-03-25

## Pattern Overview

**Overall:** Single-page static application with Python-driven build system

**Key Characteristics:**
- Static HTML output with embedded styles and scripts
- Component-based architecture (sections, modals, dashboard)
- Python build pipeline orchestrates asset assembly and transformations
- Client-side event delegation for interactivity
- Leaflet map integration with lazy initialization

## Layers

**Build Layer (Python):**
- Purpose: Assembly, transformation, and optimization of source assets into a single HTML file
- Location: `build.py`
- Contains: Build orchestration, CSS deduplication, pricing fixes, modal transformations, font embedding
- Depends on: Assets directory, JSON modal data, styles, sections HTML
- Used by: Deploy pipeline

**HTML Content Layer (Sections):**
- Purpose: Define page structure and semantic content sections
- Location: `assets/sections.html`
- Contains: 13 major sections (hero, contexto, campo, convocatoria, incentivos, locaciones, catering, tecnica, moderadores, entregables, inversion, intelligence, comparativa, cierre)
- Depends on: CSS classes, modal references
- Used by: Build layer, displayed in output HTML

**Modal Data Layer (JSON):**
- Purpose: Centralized storage of modal content organized by category
- Location: `assets/modals_data.json`
- Contains: 34 modal HTML templates grouped by feature (observaciones, pasos, entregables, intelligence, superpoderes, venues, moderadores)
- Depends on: CSS classes
- Used by: Build layer, injected into final HTML

**Style Layer (CSS):**
- Purpose: Visual design, responsive behavior, animations
- Location: `assets/styles.css`
- Contains: Base variables (colors, fonts, sizes), layout components (sections, cards, grids, modals), animations (scroll, countup, transitions)
- Depends on: Font base64 embedding, CSS variables
- Used by: All layers

**Font Layer:**
- Purpose: Embed MG brand fonts (Favorit, Favorit Mono, Heatwood) as base64 to avoid external dependencies
- Location: `assets/font_declarations.json`, `assets/fonts/` (individual weight files as .b64)
- Contains: Font metadata and encoded font files
- Depends on: `build_font_faces()` function
- Used by: CSS font-face declarations

**JavaScript Layer (Client-side):**
- Purpose: Interactivity, animations, state management
- Location: `build.py` (build_js() function), outputs to final HTML
- Contains: Event delegation system, scroll animations, modal management, carousel control, map initialization, count-up animations, progress tracking
- Depends on: Leaflet.js CDN for map functionality
- Used by: Browser DOM

**Asset Resources:**
- Purpose: Static media
- Location: `assets/bg_photos/` (background images)
- Depends on: Referenced in CSS
- Used by: Output HTML styles, copied to `output/img/`

## Data Flow

**Build-time Flow:**

1. **Asset Loading**
   - Read `sections.html` (14 major sections)
   - Read `styles.css` (546 lines of UI styling)
   - Read `modals_data.json` (34 modals, 405KB)
   - Load font declarations and individual font files (base64)

2. **Content Transformation**
   - `fix_sections()`: Replace price values (base $87M, intelligence +$24M, total $111M)
   - `fix_css()`: Deduplicate modal CSS blocks (remove duplicate `.mod-mosaic` definitions)
   - `fix_modals()`: Convert modals from `onclick="closeModal()"` to `data-close` pattern, add modal-overlay class
   - `build_font_faces()`: Generate @font-face rules with base64 font data

3. **Component Assembly**
   - Build font CSS block (all @font-face rules)
   - Build JavaScript block from build_js() function
   - Group modals by category (observaciones, pasos, entregables, intelligence, etc.)
   - Build final HTML document with DOCTYPE, head (metadata, Leaflet CDN links, style blocks), body (preloader, sections, modals, script)

4. **Asset Copying**
   - Copy background images from `assets/bg_photos/` to `output/img/`

5. **Output Generation**
   - Write single HTML file: `output/index.html` (1.4MB, ~7000 lines)
   - Stats logged: file size, line count, onclick references, style blocks, data-modal triggers

**Runtime Data Flow (Client-side):**

1. **Page Load**
   - Preloader displayed (300ms fade)
   - Fonts load from embedded base64
   - Leaflet library loaded from CDN

2. **User Scroll**
   - Progress bar updates (scroll position)
   - Scroll indicator dots update (IntersectionObserver)
   - Section navigation links activate
   - Scroll animations trigger (elements fade/slide in at 0.1 threshold)
   - Count-up animations begin for numbers (1200ms easing)

3. **User Interaction**
   - Modal open: Click element with `data-modal="id"` → Find modal by ID → Add `.open` class → Lock scroll
   - Modal close: Click button with `data-close` or ESC key → Remove `.open` class → Unlock scroll
   - Carousel: Click prev/next or dots → Update slide index → Transform translate X
   - Map: Click venue marker → Fly to coordinates → Show sidebar with venue details → Initialize map if needed

**State Management:**

Client-side state maintained via:
- CSS classes (`.open`, `.active`, `.in`)
- DOM attributes (`data-idx`, `data-modal`, `data-count`)
- JavaScript variables (current slide, active marker, current section)

No persistent storage; state resets on page reload.

## Key Abstractions

**Modal System:**
- Purpose: Display detailed content in lightbox overlays without page navigation
- Examples: `m-conv` (Convocatoria), `m-micro` (Microfonía), `m-v1` through `m-v6` (Venues), `m-mod1` through `m-mod5` (Moderadores)
- Pattern: Event delegation on document click → detect `data-modal` attribute → add `.open` class → overlay + modal-box both visible

**Section Component:**
- Purpose: Full-height logical division of content
- Structure: `<section id="[section-id]"><div class="inner">content</div></section>`
- Features: Background images, parallax effects, stag labels (vertical text), animations

**Animation Framework:**
- Purpose: Progressive enhancement via IntersectionObserver
- Patterns:
  - `.anim` triggers fade-in at 0.1 threshold
  - `.anim-d1`, `.anim-d2`, `.anim-d3`, `.anim-d4` create staggered delays
  - Scroll bar and progress indicator via scroll listener
  - Count-up numbers via requestAnimationFrame

**Responsive Grid System:**
- Purpose: Flexible layout at multiple breakpoints
- Pattern: CSS Grid (`.grid-2`, `.counter-grid`)
- Breakpoint: 900px (nav layout changes), 768px (section padding, stag hidden)

## Entry Points

**Build Entry:**
- Location: `build.py` main block (line 610-611)
- Triggers: `python3 build.py`
- Responsibilities:
  - Load all assets
  - Apply transformations
  - Assemble HTML
  - Write output
  - Log statistics

**HTML Entry:**
- Location: `output/index.html`
- Triggers: Browser load (served over HTTP)
- Responsibilities:
  - Load CSS (including fonts)
  - Render DOM
  - Load Leaflet from CDN
  - Execute inline JavaScript

**JavaScript Entry:**
- Location: `<script>` block at end of HTML (from build_js())
- Triggers: DOMContentLoaded
- Responsibilities:
  - Preloader fade
  - Progress bar tracking
  - Scroll indicator setup
  - Modal event delegation
  - Carousel initialization
  - Map initialization (lazy, on IntersectionObserver)

## Error Handling

**Strategy:** Progressive enhancement with graceful degradation

**Patterns:**

1. **Map Initialization (Leaflet):**
   - Retry loop: If L is undefined, retry every 300ms (max 30 attempts)
   - If map never initializes, modals and other features still work
   - IntersectionObserver ensures initialization only when map section enters viewport

2. **Modals:**
   - No error thrown if modal ID not found — silently ignored
   - Backdrop click and ESC both close modals
   - Body overflow locked/unlocked on both open and close

3. **DOM Queries:**
   - All element references checked for existence before access
   - Example: `if(!track || !dots) return;` prevents errors in carousel

4. **Font Loading:**
   - Fonts embedded as base64, no external dependency
   - If base64 decode fails, system font stack applies

## Cross-Cutting Concerns

**Logging:** None (client-side only, no analytics)

**Validation:**
- Build-time: Python validates JSON structure, CSS syntax
- Runtime: Client validates DOM element existence before manipulation

**Authentication:** Not applicable (static site, no backend)

**Performance Optimizations:**
- Single HTML file avoids multiple requests
- Inline CSS and scripts (no separate file requests)
- Base64 fonts eliminate font CDN requests
- Leaflet loaded from CDN only when map needed (lazy)
- IntersectionObserver gates animations and map initialization (avoid unnecessary reflow)
- RequestAnimationFrame for smooth count-up animations

**Browser Compatibility:**
- IntersectionObserver (all modern browsers)
- CSS Grid and Flexbox (all modern browsers)
- Leaflet.js (all modern browsers)
- No IE11 support

---

*Architecture analysis: 2025-03-25*
