# Technology Stack

**Analysis Date:** 2025-03-25

## Languages

**Primary:**
- Python 3 - Build system, asset compilation, and HTML generation via `build.py`

**Secondary:**
- HTML5 - Final deliverable template structure
- CSS3 - Styling with custom properties (CSS variables) for MG brand colors
- JavaScript (ES5+) - Client-side interactivity, event handling, animations

## Runtime

**Environment:**
- Python 3.x (standard library: `json`, `re`, `shutil`, `pathlib`)

**Execution:**
- Local build process: `python3 build.py` generates `/output/index.html`
- No server-side runtime required
- Final output: Static HTML file for deployment or GitHub Pages

## Build System

**Builder:**
- Custom Python build script at `build.py` - 612 lines
- Orchestrates asset compilation, CSS deduplication, price updates, modal fixes

**Build Process:**
- Reads component files from `assets/` directory
- Applies transformations: font injection, content fixes, modal refactoring
- Outputs single self-contained `output/index.html`
- No package manager (npm, pip, etc.)

## Frameworks

**Frontend:**
- **Leaflet.js** v1.9.4 - Interactive map for venue locations
  - CDN: `https://unpkg.com/leaflet@1.9.4/dist/leaflet.css`
  - CDN: `https://unpkg.com/leaflet@1.9.4/dist/leaflet.js`
- **OpenStreetMap Tiles** - CartoDB dark_matter with custom MG color filter

**Styling:**
- No CSS framework (Tailwind, Bootstrap, etc.)
- Custom CSS with CSS variables for theming
- All styling in single `<style>` block (41KB in `assets/styles.css`)

## Key Dependencies

**Fonts (Embedded as Base64):**
- **Favorit** (weights 300, 400, 500, 700) - MG official sans-serif
  - Source: `MG_Fonts.zip` → embedded in CSS via `build_font_faces()`
  - Base64-encoded WOFF2 files in `assets/fonts/Favorit_w{weight}.b64`
- **Favorit Mono** (weight 400) - Monospace for labels and UI
  - Embedded in CSS, used for `.label`, `.axis`, `.nav-link`, `.modal-*` elements
- **Heatwood** (weight 400) - Script typeface for MG brand accent text
  - Used only in MG Red (#A00022), max 2 words per brand guidelines

**Browser APIs (Native):**
- IntersectionObserver - Scroll animations, lazy loading, modal triggers
- requestAnimationFrame - Count-up animations, smooth scrolling
- Fetch API - Not used (static HTML only)
- Local Storage - Not used
- Web Workers - Not used

## Configuration

**Environment:**
- No environment variables required
- No `.env` file (static generation only)
- All configuration embedded in source files

**Build Configuration:**
- `assets/font_declarations.json` - List of fonts to inject (6 entries)
- `assets/sections.html` - Main content template (515KB)
- `assets/styles.css` - All styling rules (41KB)
- `assets/dashboard_mockup.html` - Dashboard section (77KB)
- `assets/modals_data.json` - Modal content definitions (404KB)
- `assets/script.js` - Initial JavaScript reference (5KB, replaced by `build_js()`)

## Platform Requirements

**Development:**
- Python 3.x (any recent version)
- Text editor or IDE
- File system with read/write access
- No database
- No external services required

**Production/Deployment:**
- Any static file hosting:
  - GitHub Pages (`.nojekyll` file present in `/docs`)
  - CDN (Vercel, Netlify, CloudFlare)
  - Web server serving `output/index.html`
- Browser with ES5+ support and Leaflet.js CDN access
- Internet connection required for Leaflet tiles and CSS fonts CDN

## Asset Pipeline

**Input Assets:**
- Fonts: `assets/fonts/Favorit_w*.b64` (base64-encoded WOFF2)
- Images: `assets/bg_photos/*.jpg` (background images, copied to `output/img/`)
- Moderator photos: `assets/mod_photos/` (referenced in modals)
- Venue photos: `assets/venue_photos/` (referenced in modals)
- Content templates: `assets/sections.html`, `assets/modals_data.json`, `assets/dashboard_mockup.html`

**Output:**
- `output/index.html` (1.4 MB, ~1400 lines with embedded base64)
- `output/img/*.jpg` (copied background images)
- `docs/index.html` (published version on GitHub Pages)

## Size & Performance

**Output File Size:**
- HTML: ~1.4 MB (single file, no splitting)
- Includes: All fonts (base64), all CSS, all JavaScript, full modal content
- Structure: Minified CSS, unminified JS for maintainability

**Load Performance:**
- No lazy loading (fonts are base64-embedded)
- Leaflet.js loaded asynchronously (retry loop if CDN unavailable)
- Map initialization deferred to IntersectionObserver (loads when section visible)
- Progress bar and preloader: instant (inline JS)

## Deployment

**Current Deployment:**
- GitHub Pages at `docs/` directory
- File: `docs/index.html`
- Marker: `docs/.nojekyll` (disables Jekyll processing)

**Build-to-Deploy:**
```bash
python3 build.py                    # Generates output/index.html
cp output/index.html docs/          # Copy to GitHub Pages directory
git add docs/index.html && git commit
```

---

*Stack analysis: 2025-03-25*
