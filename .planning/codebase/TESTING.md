# Testing Patterns

**Analysis Date:** 2025-03-25

## Test Framework

**Status:** No testing framework detected

**Runner:**
- No automated test runner configured
- No Jest, Vitest, Pytest, or other test framework found
- No test files (*.test.js, *.spec.py, etc.) in codebase

**Assertion Library:**
- Not applicable

**Run Commands:**
```bash
# No test commands available
# Build system only
python3 build.py              # Run build pipeline
```

## Test File Organization

**Location:**
- No test files exist
- No `/tests/` or `__tests__/` directory

**Naming:**
- Not applicable

**Structure:**
- Not applicable

## Manual Testing & Validation

The build system includes implicit validation through:

**Build Statistics (printed to console):**
```python
print(f"  Size: {size_kb:.0f} KB ({lines} lines)")
print(f"  Style blocks: {style_blocks}")
print(f"  onclick in HTML: {onclick_count}")
print(f"  data-modal triggers: {data_modal_count}")
print(f"  data-close buttons: {data_close_count}")
```

**Test Approach in `build.py`:**
- Assertions embedded in build process: `if idx == -1:`, `if idx > -1:`
- Validation of modal structure: `if 'class="modal-overlay"' not in content:`
- String search verification: `if second_mosaic > -1 and second_mosaic > idx:`

**Validation Rules:**
- Modal counts must match (data-modal triggers should equal data-close buttons for proper open/close pairing)
- CSS deduplication: Ensures first duplicate .mod-mosaic block removed before second
- Price updates applied consistently: All $80M replaced with $87M, all +$20M with +$24M
- File encoding: UTF-8 enforced: `.read_text(encoding="utf-8")`, `.write_text(html, encoding="utf-8")`

## Browser Testing

**Manual verification approach (implied by codebase structure):**
- CSS hover states tested manually: `.card:hover`, `.nav-link:hover`
- Modal interactions: `data-modal` click opens, `data-close` or Escape closes
- IntersectionObserver triggers: Section animations, nav active state, progress bar
- Leaflet map rendering: Multiple `setTimeout()` calls for `invalidateSize()` ensure map renders after layout
- Touch/swipe: `.touchstart`, `.touchend` handlers for carousel on mobile
- Responsive breakpoint: `@media(max-width:768px)` and `@media(max-width:900px)`

## Mocking

**Framework:** None

**Patterns:**
- No mocks needed (pure HTML/CSS/JS with no API calls or external dependencies beyond Leaflet)
- DOM elements accessed directly: `document.getElementById()`, `document.querySelectorAll()`
- No service dependencies or async operations to mock

**What NOT to Mock:**
- DOM operations (IntersectionObserver, event listeners are real)
- Leaflet library (loaded from CDN, too heavy to mock)
- CSS rendering (browser handles it)

## Fixtures and Factories

**Test Data:**
- Hardcoded venue data in JavaScript:
```javascript
var VENUE_DATA = {
  'm-v1': {name:'Galpón Italia', addr:'Italia 1242, Ñuñoa', cap:'80 pax', ...},
  'm-v2': {...},
  // ... 6 venues total
};
```

- Metro station coordinates in array:
```javascript
var metros = [
  {lat:-33.4251, lng:-70.6098, name:'Baquedano'},
  // ... 6 stations total
];
```

- Parking locations as array of lat/lng objects
- Venue/Metro/Parking data duplicated in `build_js()` within build.py (not DRY)

**Location:**
- In-memory fixtures defined in `build.py`'s `build_js()` function string
- Duplicate data also in `assets/script.js` for development
- Font declarations in `assets/font_declarations.json`
- Modal content in `assets/modals_data.json` (400KB+ JSON file)

## Coverage

**Requirements:** No coverage requirement enforced

**Coverage Status:**
- **Python (`build.py`)**: Not measured
  - Core transformation functions: `fix_css()`, `fix_sections()`, `fix_modals()` exercised on every build
  - `build_js()` output tested implicitly through HTML generation
  - Estimated coverage: ~80% (happy path covered, error paths not)

- **JavaScript (browser code)**: Not measured
  - Navigation: active state tracking via IntersectionObserver
  - Modals: data-modal/data-close event delegation
  - Carousel: auto-advance, manual navigation, touch swipe
  - Map: Leaflet integration, marker clicks, sidebar display
  - Animations: scroll trigger, count-up numbers
  - Estimated coverage: ~75% (core features work, edge cases untested)

**View Coverage:**
- No coverage reports generated
- Manual build output inspection: `python3 build.py` prints statistics

## Test Types

**Unit Tests:**
- Not implemented
- Would test: `fix_css()` string transformations, price replacement rules, modal deduplication

**Integration Tests:**
- Not implemented
- Build process itself serves as integration test: assemble HTML + CSS + JS + modals, verify output size and structure

**E2E Tests:**
- Not implemented
- Browser testing only: manual click through sections, modals, map, carousel
- No Playwright/Cypress tests despite project having `.playwright-mcp` directory (MCP agent context, not test suite)

## Test Gaps

**Untested Areas:**

1. **String transformation logic (`build.py`):**
   - No tests for `fix_sections()` price replacement correctness
   - No verification that all price values updated consistently
   - Risk: Missed price field → confusing user

2. **CSS deduplication (`fix_css()`):**
   - No tests that both `.mod-mosaic` blocks properly merged
   - Risk: Broken grid layout if wrong block kept

3. **Modal structure validation:**
   - No tests verifying modal-overlay class added correctly
   - No tests for data-modal/data-close pairing
   - Risk: Modals fail to open/close

4. **Leaflet map initialization:**
   - No tests for map rendering with 6 venues + metro stations + parking
   - Polling for `typeof L === 'undefined'` not tested
   - Risk: Map renders only if timing allows

5. **Event delegation (JavaScript):**
   - No tests for click handler scope (modal close vs overlay close)
   - No tests for Escape key handler
   - Risk: Multiple modals don't handle escape correctly

6. **IntersectionObserver animations:**
   - No tests for scroll trigger thresholds (0.1, 0.3, 0.4, 0.5)
   - No tests for count-up animation easing
   - Risk: Animations don't fire at expected scroll positions

7. **Responsive design:**
   - No media query tests
   - No viewport size variation tests
   - Risk: Mobile layout broken at untested breakpoint

8. **Carousel auto-advance:**
   - No tests for 6-second interval
   - No tests for pause-on-hover behavior
   - No tests for touch swipe delta calculation (>50px threshold)
   - Risk: Carousel behavior inconsistent

## Validation Without Tests

The codebase validates correctness through:

1. **Build statistics** - Output metrics printed: file size, line count, HTML element counts
2. **Manual visual inspection** - Run `python3 build.py`, open `output/index.html` in browser
3. **Assertion-driven code** - Build fails if expected files/data missing (implicit, not explicit)
4. **String matching** - Regex searches confirm modal class structure, data attributes present

---

*Testing analysis: 2025-03-25*

## Recommendations

To add testing coverage:

1. **Python unit tests** using pytest:
   - Test `fix_sections()` price replacement with sample HTML inputs
   - Test `fix_css()` deduplication with mock CSS
   - Test `fix_modals()` class injection

2. **JavaScript integration tests** using Vitest/Playwright:
   - Render full HTML, test modal open/close behavior
   - Test IntersectionObserver animations trigger on scroll
   - Test Leaflet map renders with all markers

3. **Visual regression tests** using Percy/Chromatic:
   - Screenshot comparison of full page at breakpoints
   - Compare against reference screenshots after each build

4. **E2E tests** using Playwright:
   - Click each modal trigger, verify modal displays
   - Scroll through page, verify animations fire
   - Click venue markers, verify sidebar updates
