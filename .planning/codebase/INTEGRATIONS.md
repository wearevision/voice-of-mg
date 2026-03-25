# External Integrations

**Analysis Date:** 2025-03-25

## APIs & External Services

**Mapping:**
- **Leaflet.js** (OSM-based) - Interactive venue map
  - SDK: Leaflet v1.9.4 JavaScript library
  - Tiles: OpenStreetMap (CartoDB dark_matter)
  - Tiles API: `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`
  - No authentication required
  - Embedded in `build.py` lines 416-422, 420-421

**Fonts (via CDN):**
- **Google Fonts / Custom Font Providers** - Not used
- Fonts are embedded as base64 in CSS (self-hosted via data URLs)
- No external font CDN dependency

**Analytics & Tracking:**
- No analytics (Google Analytics, Mixpanel, etc.)
- No user tracking
- No event logging

## Data Storage

**Databases:**
- None - Static HTML generation only
- No backend database required
- No persistent user data

**File Storage:**
- Local filesystem only
  - Assets directory: `assets/` (fonts, images, content files)
  - Output directory: `output/` (generated HTML)
  - Published: `docs/` (GitHub Pages)
- No cloud storage (AWS S3, Google Cloud Storage, etc.)

**Caching:**
- Browser cache: Controlled by HTTP headers (not configured)
- No server-side caching
- Static files cached by CDN (if deployed to Vercel/Netlify)

## Authentication & Identity

**Auth Provider:**
- None required - Static content
- No user login
- No session management
- No identity provider (OAuth, Auth0, Firebase Auth)

**Access Control:**
- Public (no authentication)
- Entire proposal visible to anyone with URL
- No role-based access

## Content Delivery

**CDN:**
- Leaflet JS library: `https://unpkg.com/leaflet@1.9.4/dist/leaflet.js` (unpkg CDN)
- Leaflet CSS: `https://unpkg.com/leaflet@1.9.4/dist/leaflet.css` (unpkg CDN)
- Fonts: Embedded as base64 (no CDN)
- Images: Served locally from `output/img/` or `docs/img/`

**Deployment Hosting:**
- GitHub Pages (primary): `https://fede.github.io/voice-of-mg/` (via `/docs` directory)
- Can be deployed to: Vercel, Netlify, any static web host

## Monitoring & Observability

**Error Tracking:**
- None (browser console errors only)
- No error reporting service (Sentry, Rollbar, etc.)

**Logs:**
- None - Static HTML with client-side JavaScript
- Browser console logs available (dev tools only)
- Custom logging in `build.py` for build output (lines 602-607)

**Analytics:**
- None configured
- No page views tracked
- No event tracking

## CI/CD & Deployment

**Hosting:**
- GitHub Pages (docs directory)
- Supports deployment to: Vercel, Netlify, CloudFlare Pages

**CI Pipeline:**
- None configured (manual build + push)
- Note: Vercel plugin context detected (observability capability available)
- Could add: GitHub Actions workflow for auto-build on push

**Build Trigger:**
- Manual: `python3 build.py` locally
- No automated build pipeline
- No deploy hooks

## External Webhooks

**Incoming:**
- None - Static HTML generation
- No webhook endpoints

**Outgoing:**
- None - No server-side communication
- Entire application is client-side rendered

## Third-Party Integrations

**Maps & Geolocation:**
- **OpenStreetMap / CartoDB** - Free tile provider
  - No API key required
  - Data attribution: Included in map (can be hidden per leaflet config)
  - Rate limiting: Standard free tier limits apply

**Browser Compatibility:**
- JavaScript ES5+ (modern browser support required)
- No polyfills included
- Requires: Chrome, Firefox, Safari, Edge (last 2 versions)

## Environment Configuration

**Required Environment:**
- Python 3.x (for build process)
- No environment variables needed
- No secrets required

**Configuration Files:**
- `assets/font_declarations.json` - Font list to embed
- `assets/sections.html` - Content template
- `assets/modals_data.json` - Modal content
- `assets/styles.css` - Styling rules
- `assets/dashboard_mockup.html` - Dashboard section

**Secrets/Credentials:**
- None required (static HTML)
- No API keys used
- No authentication tokens needed

## Performance & Rate Limiting

**CDN Rate Limiting:**
- Leaflet CDN (unpkg): Standard free tier limits
  - Likely sufficient for single static file deployment
  - No rate limiting visible in code

**Map Tile Requests:**
- OpenStreetMap/CartoDB: Free tier rate limit ~1 tile request/second typical
- Implemented in `build.py` line 420 with tile loading
- No rate limiting configuration in JavaScript

## Data Privacy

**User Data Collection:**
- None - Static HTML only
- No form submissions
- No user input stored
- No cookies (not configured)

**Third-Party Data Sharing:**
- None - No external services receive user data
- Leaflet tiles: Limited to viewing map (no user tracking)

## Browser APIs Used

**Network:**
- Fetch: Not used
- XMLHttpRequest: Not used
- WebSockets: Not used
- Service Workers: Not used

**Local Storage:**
- localStorage: Not used
- sessionStorage: Not used
- IndexedDB: Not used

**Media:**
- Canvas: Not used (only for Leaflet map rendering)
- Audio/Video: Not used
- Geolocation: Not used

---

*Integration audit: 2025-03-25*
