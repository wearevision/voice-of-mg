# Codebase Concerns

**Analysis Date:** 2025-02-25

## Security

### XSS Vulnerabilities (CRITICAL)

**Issue:** Extensive use of `innerHTML` with unsanitized user input and string concatenation

**Files:**
- `build.py` (lines 381-403): Sidebar content built with string concatenation → `innerHTML`
- `assets/dashboard_mockup.html` (lines 715-724, 759-766, 785-795, 849-861, 889, 916-918, 923-925): All search results, profile cards, and tooltips use `innerHTML` with concatenated strings

**Problem:** While current data is hardcoded and not user-sourced, the dashboard interaction code builds HTML strings by concatenating:
- Participant names from `PARTICIPANTS` array (lines 852, 856-860)
- Quote text from `VERBATIMS` array (lines 719, 881)
- User search input is processed but still inserted into HTML (line 763, 766)
- Tooltip content from SVG attributes (lines 912-918, 922-925)

Example vulnerable pattern:
```javascript
html += '<div style="font-size:18px;font-weight:700;color:white;line-height:1.2">' + p.name + '</div>';
searchResults.innerHTML = html; // Line 766
```

**Impact:** If participant data or verbatims ever come from an external API or user input without sanitization, XSS injection is possible. Even hardcoded data could be vulnerable to indirect attacks if stored values contain malicious strings.

**Fix approach:**
1. Replace all `innerHTML` assignments with safe DOM methods (`textContent`, `createElement`, `appendChild`)
2. For complex HTML structures, use template elements or DOM builder libraries
3. Add input validation for search queries (currently minimal normalization at line 707-708)
4. Use Content Security Policy (CSP) headers if deployed on a server
5. If data must remain in HTML: sanitize with `DOMPurify` library

**Priority:** High — Easy to exploit if dashboard is extended with dynamic data sources

---

### Third-party CDN Dependencies

**Issue:** Critical functionality relies on unpinned CDN resources

**Files:**
- `build.py` (line 566-567): Leaflet map via unpkg CDN without version lock
- `assets/dashboard_mockup.html` (line 42): YouTube embed with `?enablejsapi=1&origin=*`

**Files affected:**
- `build.py` (line 420-421): OpenStreetMap tiles (CartoDB) — if service changes, map styling fails
- Leaflet loaded from `https://unpkg.com/leaflet@1.9.4/dist/leaflet.{css,js}`

**Problem:**
1. `origin=*` in YouTube embed allows any page to control the player (security risk)
2. CDN resources could change or become unavailable
3. No fallback if Leaflet fails to load (retry loop at lines 411-414 maxes out at 30 attempts)
4. CartoDB tiles have usage restrictions not documented in code

**Impact:**
- Map section fails silently if Leaflet CDN is down (only retries for 9 seconds)
- YouTube video could be hijacked if origin is misconfigured
- Production deployment vulnerability if CDN goes down

**Fix approach:**
1. Pin exact Leaflet version and host locally if possible
2. Change YouTube embed `origin` to actual domain (remove `*` wildcard)
3. Add user-facing error message if Leaflet fails to load (currently silent)
4. Cache map tiles locally for offline resilience
5. Document CartoDB usage limits and fallback strategy

**Priority:** Medium — affects reliability, not immediate data risk

---

## Tech Debt

### Fragile Price Update System

**Issue:** Pricing logic is hardcoded in build.py with brittle string replacements

**Files:** `build.py` (lines 76-134: `fix_sections()` function)

**Problem:** 17 separate string replacements for pricing updates:
```python
html = html.replace('">$80<span', '">$87<span')
html = html.replace("$80 M CLP", "$87 M CLP")
html = html.replace("$20M por sesión trimestral", "$21,75M por sesión trimestral")
# ... 14 more
```

**Why fragile:**
1. If HTML structure changes even slightly (whitespace, spacing), replacements fail silently
2. No validation that replacements succeeded
3. Multiple places with same number but different context (hard to update consistently)
4. Related calculations ($87M ÷ 4 = $21.75M) live in comments, not as code

**Impact:**
- Single typo in `assets/sections.html` breaks price updates
- No way to know if a replacement failed — wrong prices could go to client
- Extending pricing (e.g., new currency, add-ons) requires modifying build.py

**Fix approach:**
1. Extract prices to `prices.json`:
```json
{
  "base_annual": 87000000,
  "intelligence_addon": 24000000,
  "total_annual": 111000000,
  "sessions_per_year": 4,
  "participants_per_session": 60
}
```
2. Use structured data approach: parse HTML templates, update data structure, serialize back
3. Add build-time assertions: verify all price mentions are updated
4. Use template placeholders in HTML instead of hardcoded numbers

**Priority:** High — Fix before next price update to avoid errors

---

### Duplicate Generated Files

**Issue:** Output HTML is generated to three locations causing sync problems

**Files:**
- `output/index.html` (2,964 lines)
- `docs/index.html` (identical 2,964 lines)
- `.claude/worktrees/loving-moore/output/index.html` (duplicate)
- `.claude/worktrees/loving-moore/docs/index.html` (duplicate)

**Problem:** `build.py` writes to `OUTPUT = BASE / "output"` only (line 583), but `docs/` is identical copy (probably manual copy or git hook). Worktree directories contain additional duplicates.

**Impact:**
- Changes to one copy aren't reflected in others
- No single source of truth
- Deployment ambiguity (which copy deploys to production?)
- Wastes disk space (1.4M × 4)
- Git history cluttered with same file in multiple locations

**Fix approach:**
1. Keep single output directory: `output/index.html`
2. If `docs/` is used for GitHub Pages: use build hook or symlink
3. Remove worktree copies from version control (should be in `.gitignore`)
4. Document which directory is canonical in README

**Priority:** Medium — doesn't affect functionality but creates maintenance confusion

---

### Map Initialization Unreliability

**Issue:** Leaflet map initialization relies on retry loop with no timeout guarantee

**Files:** `build.py` (lines 409-415)

**Code:**
```javascript
if(typeof L === 'undefined'){
  mapInitAttempts++;
  if(mapInitAttempts < 30) setTimeout(initMap, 300);
  return false;
}
```

**Problem:**
1. Retry loop runs for max 30 × 300ms = 9 seconds total
2. If Leaflet loads after 9 seconds, map never initializes
3. No feedback to user that map is broken
4. IntersectionObserver re-triggers initialization every time section becomes visible (line 505-514)
5. Multiple `invalidateSize()` calls at 200ms, 600ms, 1200ms are band-aid fixes for layout issues (lines 509-511)

**Impact:**
- On slow connections, map silently fails
- No error message — users think functionality is missing
- Each scroll back to map section triggers new init attempt (CPU spike)

**Fix approach:**
1. Add timeout with user-facing error message:
```javascript
var mapInitTimeout = setTimeout(function(){
  if(!map) mapEl.innerHTML = '<p>Could not load map. Check internet connection.</p>';
}, 10000);
```
2. Track initialization state to prevent duplicate attempts
3. Remove multiple `invalidateSize()` calls — use single call after `flyTo()` completes
4. Add connection check before attempting initialization

**Priority:** Medium — affects UX on slow networks

---

## Performance Bottlenecks

### Large Monolithic Output File

**Issue:** Single 1.4MB HTML file contains everything (fonts, CSS, JS, data)

**Files:** `output/index.html` and `docs/index.html`

**Problem:**
- All fonts embedded as base64 strings (lines ~10-15 in CSS block)
- Entire JavaScript dashboard code inline (~2,500 lines in dashboard_mockup.html)
- Complete Leaflet CSS+JS from CDN
- All modal content pre-rendered in HTML (even modals user won't see)

**Impact:**
- Single file download blocks rendering until complete
- No caching benefits (can't split into vendor/app code)
- Font data duplication: 4 fonts × base64 encoded multiplies size
- Slow initial page load on mobile (4G: ~5+ seconds)
- Hard to update single components

**Current stats:**
- 2,964 lines = ~1.4MB (with embedded base64 fonts)
- If fonts are ~400KB of that, core HTML is only ~1MB

**Fix approach:**
1. Move fonts to separate font files (WOFF2, far better compression)
2. Extract CSS to external stylesheet
3. Extract JS to separate file
4. Lazy-load dashboard script only if dashboard section intersects viewport
5. Use gzip compression (reduces 1.4MB → ~300KB)

**Priority:** Medium — doesn't affect functionality, but improves perceived performance by 50%+

---

### Modal Content Pre-rendering

**Issue:** All 20+ modals are rendered in DOM even if user never opens them

**Files:** `build.py` (lines 543-557), `assets/modals_data.json`, generated HTML

**Problem:** Every modal definition from `modals_data.json` is assembled into the page:
```python
for group_name, ids in groups.items():
    for mid in ids:
        if mid in modals:
            modals_html += modals[mid] + "\n"
```

**Impact:**
- DOM has 20+ hidden elements (observer overhead)
- CSS for `.modal-overlay` applies to all simultaneously
- Browser parses modal content even though 90% of users see <5 modals

**Fix approach:**
1. Keep modal definitions in JSON only
2. Load modal HTML on-demand when user clicks `[data-modal]`
3. Inject into DOM, display, clean up on close
4. Cache in memory to avoid re-parsing

**Priority:** Low — improves DOM performance marginally, better to fix size issue first

---

## Test Coverage Gaps

**Issue:** No automated tests for critical functionality

**Files:** Entire project

**Missing tests:**
1. **Price calculation logic:** Currently checked only by human review. If anyone changes `fix_sections()`, wrong prices could be deployed
2. **Modal interactions:** No test for open/close, scroll lock, keyboard Escape
3. **Map initialization:** No test for retry logic, timeout, or error states
4. **Dashboard search:** No test for accent normalization or ranking
5. **Build pipeline:** No validation that all modals are present in output

**Impact:**
- Single typo in build.py goes undetected until client reviews deployed page
- Modal bugs discovered only by user testing
- Price changes risky — need manual QA for every update

**Fix approach:**
1. Add pytest tests for `fix_sections()` with price assertions
2. Add Jest tests for modal event delegation
3. Add integration test: build → parse output → verify all modals present
4. Add visual regression test (Percy or similar) to catch layout breaks

**Priority:** Medium — crucial for client-facing pricing but low effort to add

---

## Fragile Areas

### CSS Deduplication Logic

**Issue:** `fix_css()` function removes duplicate `.mod-mosaic` blocks with fragile string matching

**Files:** `build.py` (lines 46-73)

**Code:**
```python
first_block = "/* MODERATORS MOSAIC */\n"
idx = css.find(first_block)
if idx == -1:
    idx = css.find(".mod-mosaic{display:grid;grid-template-columns:repeat(4,1fr)")
if idx > -1:
    second_mosaic = css.find("/* MOD MOSAIC */")
    if second_mosaic > idx:
        css = css[:idx] + css[second_mosaic:]
```

**Problem:**
1. Depends on exact comment text (`/* MODERATORS MOSAIC */`) — single space change breaks it
2. Fallback to string search for `.mod-mosaic{display:grid` — fragile if whitespace changes
3. No validation that deduplication succeeded
4. Comments say "this is a workaround" — suggests underlying issue not fixed

**Impact:**
- If CSS structure changes in assets, deduplication silently fails
- Duplicate CSS rules increase file size
- No error logging if removal didn't work

**Fix approach:**
1. Extract CSS properly instead of string manipulation:
   - Parse CSS into AST
   - Remove duplicate selectors
   - Serialize back
2. Or: fix source files to not have duplicates in the first place
3. Add assertion that output CSS doesn't contain duplicate `.mod-mosaic` rules
4. Document why deduplication is needed

**Priority:** Medium — works now but fragile to maintainer changes

---

## Accessibility Issues

### Missing ARIA Labels and Keyboard Navigation

**Files:** `build.py` (JavaScript section), `assets/dashboard_mockup.html`

**Problems:**
1. Modal overlay has no `role="dialog"` or `aria-modal="true"`
2. Search input has no `aria-label` (line 86: `<input ... placeholder="Buscar..."`)
3. Profile cards are divs with `cursor:pointer` — not proper buttons
4. Tab order not managed when modal opens (focus trap not implemented)
5. Moderator carousel (lines 291-339) requires mouse/touch — no keyboard support
6. No skip links for keyboard users

**Impact:**
- Screen reader users can't navigate modals
- Keyboard-only users can't open modals (no Tab support)
- Profile cards not recognized as interactive elements
- Carousel not accessible

**Fix approach:**
1. Add to modal overlay:
```html
<div class="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="modal-title">
```
2. Use `<button>` instead of `<div onclick>`
3. Implement focus trap in modal (focus stays within modal while open)
4. Add `aria-label` to icon-only buttons
5. Keyboard support for carousel: arrow keys to navigate

**Priority:** Low — not blocking but important for inclusive design

---

## Known Issues & Workarounds

### Leaflet Map Doesn't Auto-resize

**Issue:** Map appears blank or misaligned when section scrolls into view

**Files:** `build.py` (lines 500-515)

**Workaround in place:** Call `invalidateSize()` three times at different delays
```javascript
setTimeout(function(){ if(map) map.invalidateSize(); }, 200);
setTimeout(function(){ if(map) map.invalidateSize(); }, 600);
setTimeout(function(){ if(map) map.invalidateSize(); }, 1200);
```

**Root cause:** Leaflet doesn't know when its container resizes via CSS. IntersectionObserver fires before layout is complete.

**Better fix:**
```javascript
// Instead of multiple delays, use ResizeObserver
new ResizeObserver(() => { if(map) map.invalidateSize(); })
  .observe(mapContainer);
```

**Priority:** Low — workaround works, but ResizeObserver is cleaner

---

### Dashboard Data Hardcoded

**Issue:** All dashboard content (participants, verbatims, metrics) hardcoded in dashboard_mockup.html

**Files:** `assets/dashboard_mockup.html` (lines ~300-600)

**Impact:**
- To update dashboard with real data, must edit HTML
- No way to load data from API
- Scaling to multiple sessions requires manual HTML duplication
- If dashboard becomes real feature, major refactor needed

**Fix approach (future):**
1. Extract hardcoded arrays to `dashboard_data.json`
2. Build dashboard HTML from template + JSON data
3. Design API format for dynamic data
4. Implement real backend when needed

**Priority:** Low — acceptable for prototype, plan for future

---

## Scaling Limits

### Single Session Dashboard

**Issue:** Dashboard is hardcoded for "Day 2 PM · Enero 2026" (line 13)

**Files:** `assets/dashboard_mockup.html`

**Problem:**
- 8 hardcoded participants
- 1 hardcoded session's verbatims
- To show multiple sessions, would need separate dashboard HTML for each
- Can't filter across sessions in trends view

**Impact:** When client asks for "show me all 4 sessions together," current architecture requires 4 separate dashboards or major refactoring

**Scaling path:**
1. Design multi-session data schema
2. Build session selector UI
3. Make search/trends aggregation work across sessions
4. Implement backend API to serve session data

**Priority:** Low — not blocking for initial pitch, plan for Phase 2

---

## Missing Documentation

### Build System Not Documented

**Issue:** `build.py` has inline comments but no user-facing docs

**Missing:**
- How to run build: `python3 build.py`?
- Where are inputs (`assets/`)? Output?
- What happens if `assets/fonts/` is missing?
- How to update prices (currently trial-and-error with string.replace)
- What is `fix_css()` fixing and why?

**Fix approach:** Add `BUILD.md`:
```markdown
# Build Process

## Quick Start
python3 build.py

## Process
1. Load assets from `assets/`
2. Encode fonts to base64
3. Replace pricing values
4. Remove duplicate CSS
5. Write to `output/index.html`

## Maintenance
- To update prices: Edit PRICES dict in build.py
- To add modal: Add ID to modals_data.json
```

**Priority:** Low — Low effort, helps future maintainers

---

## Summary by Priority

| Severity | Count | Fix Time | Impact |
|----------|-------|----------|--------|
| **CRITICAL** | 1 | 2h | XSS vulnerability if code extends to dynamic data |
| **HIGH** | 2 | 4h | Price update fragility, accessibility gaps |
| **MEDIUM** | 4 | 6h | Performance, map reliability, CSS fragility, test coverage |
| **LOW** | 4 | 3h | Documentation, scaling planning, minor perf |

**Recommended action order:**
1. Fix XSS vulnerabilities (use `textContent` instead of `innerHTML`)
2. Refactor price system to use data-driven approach
3. Add build-time tests for pricing accuracy
4. Improve Leaflet initialization (timeout + user feedback)
5. Consider splitting output file (fonts, CSS, JS external)

---

*Concerns audit: 2025-02-25*
