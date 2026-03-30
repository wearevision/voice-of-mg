# Coding Conventions

**Analysis Date:** 2025-03-25

## Naming Patterns

**Files:**
- Python scripts: snake_case (`build.py`)
- HTML asset files: snake_case (`sections.html`, `modals_data.json`, `dashboard_mockup.html`)
- CSS files: snake_case (`styles.css`)
- JavaScript: script.js (single file)

**Functions (Python):**
- All lowercase with underscores: `read_file()`, `load_font_base64()`, `build_font_faces()`, `fix_css()`, `fix_sections()`, `fix_modals()`, `build_js()`, `build()`
- Descriptive names indicating intent: `fix_*` for transformation functions, `build_*` for generation functions, `load_*` for file reading
- No camelCase used in Python codebase

**Variables (Python):**
- Lowercase with underscores: `raw_css`, `modals_raw`, `out_path`, `mapInitAttempts`, `activeMarker`
- Short variable names in loops: `s`, `e`, `m`, `d`, `i`, `j`, `v`, `p` (following Python conventions for iteration)
- HTML/DOM variables use camelCase in JavaScript context

**Variables (JavaScript):**
- camelCase for variables: `startX`, `currentSection`, `activeMarker`, `autoTimer`
- snake_case for HTML data attributes: `data-modal`, `data-close`, `data-count`, `data-mod`, `data-idx`
- CONSTANT_CASE for venue/metro data identifiers: `VENUE_DATA`

**CSS:**
- BEM-adjacent naming: `.modal-overlay`, `.modal-box`, `.modal-close`, `.nav-link`, `.scroll-indicator`
- Hyphenated classes: `.grid-2`, `.grid-3`, `.section-title`, `.stag-word`, `.modal-photo`
- CSS custom properties (variables): lowercase with hyphens: `--mg-red`, `--bg-primary`, `--text-primary`, `--mono`, `--sans`, `--script`

## Code Style

**Formatting:**
- No linter or formatter configured (project uses raw Python, HTML, JS, CSS)
- Python follows PEP 8 style (implicit, not enforced):
  - 4-space indentation
  - Docstrings for modules and functions
  - Single blank line between functions, two between classes

**Indentation:**
- Python: 4 spaces
- JavaScript: Minified/compact in `assets/script.js`, but expanded JavaScript in `build_js()` function output uses 2-4 space indentation
- CSS: Single-line declarations (minified approach)

**Comments:**
- Python: Docstrings with `"""..."""` for module and function documentation
- Python: Inline comments explain intent: `# fix: observe each`, `# Modal overlay fixes are now applied directly`
- JavaScript: Block comments with `// ──` dividers for sections
- HTML comments: `<!-- ════════════════════════════════════════════════\n     MODALES\n════════════════════════════════════════════════ -->`

**Code Organization (Python):**
- Imports at top: `import json`, `import re`, `import shutil`, `from pathlib import Path`
- Constants defined early: `BASE = Path(__file__).parent`, `ASSETS`, `OUTPUT`
- Helper functions grouped by purpose: `read_file()`, `load_font_base64()`, `build_*()` functions, `fix_*()` transformation functions
- Main `build()` function orchestrates the build pipeline
- Entry point: `if __name__ == "__main__": build()`

## String Usage

**Python:**
- f-strings for formatting: `f"@font-face{{font-family:'{d['family']}'..."`
- Triple-quoted strings for large blocks: `build_js()` returns a multi-line JavaScript string
- String replacement operations: `.replace()` for HTML content fixes

**JavaScript:**
- Template literals for DOM construction: `` `<div>...</div>` ``
- Inline styles in HTML strings: `style="width:${size}px;..."`
- String concatenation in object literals: `'<div style="...' + content + '...</div>'`

## Import Organization

**Python imports (all at top of `build.py`):**
1. Standard library: `json`, `re`, `shutil`
2. Pathlib: `from pathlib import Path`

**JavaScript imports:**
- External libraries loaded via CDN in HTML `<script>` tags, not as imports
- Leaflet library: `https://unpkg.com/leaflet@1.9.4/dist/leaflet.js`
- No module system (ES6 imports not used)

## Error Handling

**Python:**
- Minimal explicit error handling
- Uses `.find()` with index checks: `if idx > -1:` before string operations
- File operations assume paths exist: `Path(path).read_text(encoding="utf-8")`
- No try-catch blocks observed

**JavaScript:**
- DOM safety checks before operations: `if(!track || !dots) return;`
- Nullish coalescing: `var metro = L.marker([m.lat, m.lng], {icon: makeMetroIcon(m.name)}).addTo(map);` only if map exists
- Defensive iteration: `if(sections.length === 0) return;`
- Global error safety: `if(typeof L === 'undefined')` before using Leaflet library
- Type checking: `if(e.target.tagName === 'A')` for event delegation

## Logging

**Framework:** console operations in JavaScript, Python `print()` statements

**Patterns:**
- Python build system prints progress: `print("Building The Voice of MG 2026...")`, `print(f"\n✓ Built: {out_path}")`
- Statistics output: `print(f"  Size: {size_kb:.0f} KB ({lines} lines)")`
- No logging framework used (console/print only)

## Comments

**When to Comment:**
- Explain non-obvious transformations: `# Remove first duplicate .mod-mosaic block (4-column generic version)`
- Document critical fixes: `# 1. Modals use data-modal / data-close (no onclick in HTML)`
- Section dividers in JavaScript: `// ── PROGRESS`, `// ── NAV activo`, `// ── LEAFLET MAP ──────────────────────────────────────`

**JSDoc/TSDoc:**
- Not used in this codebase
- Python docstrings for functions: `"""Deduplicate CSS rules and apply modal fix."""`
- Brief function documentation only, no detailed parameter descriptions

## Function Design

**Size:**
- Utility functions: 2-10 lines (`read_file()`, `load_font_base64()`)
- Transformation functions: 10-50 lines (`fix_css()`, `fix_sections()`, `fix_modals()`)
- Complex functions (JavaScript): 20-100+ lines (carousel logic, map initialization)
- Main build function: 35+ lines with orchestration logic

**Parameters:**
- Functions take explicit required parameters, no optional args pattern
- Python: Uses keyword args for dict items: `d["family"]`, `d["weight"]`
- JavaScript: Objects passed as configuration: `{threshold: 0.4}`, `{center: [...], zoom: 14}`

**Return Values:**
- Python utility functions return generated strings
- `build_js()` returns entire minified + formatted JavaScript block as string
- `fix_*()` functions return modified strings/dicts
- JavaScript functions modify DOM in-place (no return values)

## Module Design

**Exports:**
- Python: No module exports (single-purpose build script)
- JavaScript: Global functions exposed for HTML onclick/data attributes (but data-modal pattern preferred)

**Barrel Files:**
- Not applicable (single HTML output, no module bundling)

**Data Files:**
- `font_declarations.json`: Declarative list of font families and weights
- `modals_data.json`: Centralized modal content definitions (400KB+)
- Asset separation: CSS, JS, HTML sections kept in separate files, assembled by build script

---

*Convention analysis: 2025-03-25*
