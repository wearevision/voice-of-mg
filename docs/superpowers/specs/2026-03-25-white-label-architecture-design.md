# White-Label Architecture — WAV Intelligence Dashboard

**Version:** 2.0
**Date:** 2026-03-25
**Status:** Approved
**Parent spec:** `docs/superpowers/specs/2026-03-25-wav-intelligence-dashboard-design.md`
**ADR:** ADR-001 — Central Platform DB selected over static JSON and per-tenant DB options

---

## Goal

Make WAV Intelligence a white-label SaaS product where each client gets a fully branded experience (colors, logo, fonts, labels, language, feature set, pipeline config). WAV administers all tenants from a central admin portal with cross-tenant access to each client's dashboard.

## Constraints

- 1-3 clients in the next 12 months (MG Motor is first)
- WAV manages all configuration via admin portal (no client self-service)
- Single repo, config-driven per tenant
- Each client gets a separate Vercel project, Supabase instance (data), and R2 bucket
- Central Platform Supabase instance stores all tenant configs
- Admin portal is part of the MVP
- Must integrate cleanly with the existing P1 code without rewriting

## Architecture Overview

```
                    ┌─────────────────────┐
                    │   Platform Supabase  │
                    │  (admin.wavbtl.cl)   │
                    │                      │
                    │  tenant_configs      │
                    │  tenant_locales      │
                    │  wav_admin_users     │
                    │  tenant_registry     │
                    └──────┬───────────────┘
                           │
              ┌────────────┼────────────────┐
              │            │                │
              ▼            ▼                ▼
     ┌──────────────┐ ┌──────────┐  ┌──────────────┐
     │ Admin Portal │ │ MG Motor │  │  Cliente B   │
     │  (Next.js)   │ │ (Next.js)│  │  (Next.js)   │
     │              │ │          │  │              │
     │ Reads/writes │ │ Reads    │  │ Reads        │
     │ ALL configs  │ │ own cfg  │  │ own cfg      │
     └──────────────┘ └────┬─────┘  └──────┬───────┘
                           │               │
                      ┌────┴────┐    ┌─────┴─────┐
                      │MG Motor │    │ Cliente B  │
                      │Supabase │    │ Supabase   │
                      │(data)   │    │(data)      │
                      └─────────┘    └────────────┘
```

Three types of apps share the same repo:
1. **Admin Portal** (`admin.wavbtl.cl`) — manages all tenant configs, WAV-only access
2. **Tenant Dashboard** (per client) — the focus group analysis dashboard
3. All read config from the **Platform Supabase** instance

---

## 1. Platform Database Schema

A dedicated Supabase instance ("Platform DB") stores all tenant configuration. This is separate from each tenant's business data Supabase.

### Tables

#### `tenant_registry`
The master list of tenants and their infrastructure connection info.

```sql
create table tenant_registry (
  id text primary key,                    -- "mg-motor", "cliente-b"
  name text not null,                     -- "MG Motor Chile"
  status text not null default 'active',  -- "active", "suspended", "provisioning"
  domain text,                            -- "intelligence.mgmotor.cl"
  supabase_url text,                      -- tenant's Supabase URL
  supabase_anon_key text,                 -- tenant's anon key (for magic link generation)
  r2_bucket text,                         -- "wav-mg-motor-media"
  vercel_project_id text,                 -- for deploy management
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
```

#### `tenant_configs`
Brand, features, and pipeline settings per tenant.

```sql
create table tenant_configs (
  tenant_id text primary key references tenant_registry(id),
  brand jsonb not null,                   -- { name, logo, logoSmall, favicon, colors, fonts }
  features jsonb not null,                -- { video360: true, ragQA: false, ... }
  pipeline jsonb not null,                -- { transcriptionProvider, videoSources, ... }
  locale text not null default 'es-CL',
  updated_at timestamptz default now()
);
```

#### `tenant_locales`
i18n label overrides per tenant. Stored as rows (not a JSON blob) for easier admin UI editing.

```sql
create table tenant_locales (
  tenant_id text references tenant_registry(id),
  key text not null,                      -- "nav.sessions", "session.status.ready"
  value text not null,                    -- "Sesiones", "Lista"
  primary key (tenant_id, key)
);
```

#### `wav_admin_users`
WAV team members who can access the admin portal and any tenant dashboard.

```sql
create table wav_admin_users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  name text not null,
  role text not null default 'wav_admin', -- "wav_super_admin", "wav_admin"
  created_at timestamptz default now()
);
```

### RLS Policies

- `tenant_configs`, `tenant_locales`: readable by any authenticated user (tenant apps authenticate via service role); writable only by `wav_super_admin` and `wav_admin`
- `tenant_registry`: readable by `wav_admin`+; sensitive columns (`supabase_anon_key`, `supabase_url`) are accessible only via service role (used by admin portal backend, never exposed to client). Tenant apps access Platform DB with anon key and can only read their own config via RLS (`tenant_id = current_setting('app.tenant_id')`)
- `wav_admin_users`: full CRUD for `wav_super_admin` only

### Default config

A `_default.json` file remains in the repo as a fallback. If Platform DB is unreachable at startup, `get-tenant.ts` falls back to this file + logs a warning. This prevents total outage if Platform DB has issues.

---

## 2. Tenant Config Schema

### TypeScript types

```typescript
interface TenantConfig {
  id: string                              // "mg-motor"
  name: string                            // "MG Motor Chile"
  status: "active" | "suspended" | "provisioning"
  domain: string | null

  brand: {
    name: string                          // "MG Motor Chile"
    logo: string                          // URL or path to logo
    logoSmall: string
    favicon: string
    colors: {
      primary: string                     // "#DC0032"
      accent: string
      background: string
      surface: string
      text: string
      muted: string
      border: string
      destructive: string
    }
    fonts: {
      sans: string                        // "Geist Sans"
      mono: string                        // "Geist Mono"
    }
  }

  labels: Record<string, string>          // Merged: tenant_locales + locale file

  features: {
    video360: boolean
    videoDslr: boolean
    audioTracks: boolean
    semanticSearch: boolean
    ragQA: boolean
    pdfExport: boolean
    csvExport: boolean
    trends: boolean
  }

  pipeline: {
    transcriptionProvider: "elevenlabs" | "deepgram" | "whisper"
    videoSources: ("360" | "dslr")[]
    audioTrackCount: number
    aiModel: string
  }

  locale: string                          // "es-CL", "en-US", "pt-BR"
}
```

### Validation

`tenant-schema.ts` exports a Zod schema. Validated at:
- Startup of each tenant app (fail loud if invalid)
- Save in admin portal (prevent saving invalid config)

### Loading (`get-tenant.ts`)

1. Reads `TENANT_ID` from `process.env`
2. Queries Platform DB: `tenant_registry` JOIN `tenant_configs` WHERE `id = TENANT_ID`
3. Queries `tenant_locales` for tenant-specific labels
4. Loads base locale file from `src/config/locales/{locale}.json`
5. Merges: tenant labels override locale file strings
6. Validates with Zod
7. Converts hex colors to HSL channels for shadcn compatibility
8. Caches in module scope (singleton per process)
9. Exports `getTenant(): Promise<TenantConfig>` (async on first call, sync from cache after)

**Fallback:** If Platform DB query fails, loads `src/config/_default.json` and logs warning.

**Refresh:** Config is cached per process. To propagate changes without redeploying, the admin portal calls a `/api/admin/refresh-config` endpoint on the tenant app which clears the cache.

---

## 3. Theming Layer

### CSS custom properties

The root layout reads tenant colors and injects them as CSS custom properties on `<html>`:

```tsx
// src/app/layout.tsx
const tenant = await getTenant()

<html style={{
  '--primary': tenant.brand.colors.primary,    // Already HSL channels
  '--accent': tenant.brand.colors.accent,
  '--background': tenant.brand.colors.background,
  '--surface': tenant.brand.colors.surface,
  // ... all color tokens
}}>
```

shadcn/ui components consume CSS variables in `hsl()` format. The tenant config stores colors as hex strings for readability. `get-tenant.ts` converts hex to HSL channels (e.g., `#DC0032` -> `348 100% 43%`) before caching. The CSS vars are set as HSL channel values so shadcn's `hsl(var(--primary))` works without modification.

### What moves out of globals.css

The MG-specific color values currently hardcoded in `globals.css` move to Platform DB (tenant_configs for MG Motor). The `globals.css` file retains only structural CSS (resets, base styles, font imports) — no brand colors.

### Static assets (logos)

Logos are stored in the Platform DB as URLs. Two storage options:
- **For MVP:** Logo files in `public/tenants/{tenant-id}/` served from the app itself
- **Future:** Upload to Vercel Blob or R2, store URL in `tenant_configs.brand`

The admin portal includes a logo upload form that saves to the appropriate storage.

---

## 4. React Context Layer

### TenantProvider

Wraps the app in root layout. Provides tenant config to all client components.

```tsx
// src/providers/tenant-provider.tsx
const TenantContext = createContext<TenantConfig>(null!)

export function TenantProvider({ config, children }: {
  config: TenantConfig
  children: React.ReactNode
}) {
  return (
    <TenantContext.Provider value={config}>
      {children}
    </TenantContext.Provider>
  )
}
```

### Hooks

Three focused hooks:

**`useTenant()`** — full config access for components that need brand info (logo, name).

**`useFeature(key: keyof TenantConfig['features'])`** — returns boolean. Used to conditionally render tabs, sections, buttons.

```tsx
const has360 = useFeature('video360')
// In JSX: {has360 && <Tab value="player">360° Player</Tab>}
```

**`useLabel(key: string)`** — resolves a label string. Resolution order:
1. `tenant.labels[key]` (tenant-specific override from DB)
2. Locale file string
3. `key` itself (fallback, so missing translations are visible in dev)

### Server components

Server components call `await getTenant()` directly. Only client components use the hooks via TenantProvider.

---

## 5. Internationalization (i18n)

### Locale files

Base locale files ship with the app. Simple key-value JSON, ~100-150 UI strings.

```
src/config/locales/
├── es-CL.json    # Default
└── en-US.json
```

Keys use dot notation:
```jsonc
{
  "nav.dashboard": "Panel",
  "nav.sessions": "Sesiones",
  "session.status.processing": "Procesando",
  "export.pdf": "Exportar PDF"
}
```

### Resolution priority

```
tenant_locales DB rows  →  locale JSON file  →  key literal
```

Tenant-specific labels (from `tenant_locales` table, editable in admin portal) always win over base locale strings.

---

## 6. WAV Admin Portal

A separate Next.js app deployed at `admin.wavbtl.cl`. Same repo as tenant dashboards. Connected to the Platform Supabase instance.

### Pages

```
/login                        ← WAV-only auth (Platform Supabase)
/tenants                      ← List all tenants (cards with status, domain, last update)
/tenants/new                  ← Create new tenant (name, domain, provision checklist)
/tenants/[id]                 ← Tenant overview (status, domain, quick links)
/tenants/[id]/brand           ← Edit colors (color pickers), upload logo, select fonts
/tenants/[id]/labels          ← Edit label overrides (key-value table, searchable)
/tenants/[id]/features        ← Toggle features on/off (switch grid)
/tenants/[id]/pipeline        ← Transcription provider, video sources, AI model
/tenants/[id]/preview         ← Live preview of dashboard with current config
/tenants/[id]/open            ← Generate magic link → redirect to tenant dashboard
```

### Auth

Platform Supabase auth with magic link. Only emails in `wav_admin_users` table can log in. Two roles:
- `wav_super_admin`: full access (create/delete tenants, manage WAV users)
- `wav_admin`: edit tenant configs, access tenant dashboards

### Preview feature

`/tenants/[id]/preview` renders a simplified dashboard shell with the tenant's current config applied. Uses the same `TenantProvider` + CSS vars injection as the real dashboard, but with mock data. This lets WAV see the visual result before pushing changes.

### Config propagation

When an admin saves config changes:
1. Updates rows in Platform DB
2. Calls `POST /api/admin/refresh-config` on the tenant's Vercel deployment
3. Tenant app clears its cached config, next request loads fresh config
4. Admin sees a "Config pushed" confirmation

---

## 7. Cross-Tenant Access

WAV admin needs to access any client's dashboard to inspect data, debug issues, and make fine adjustments.

### Flow

1. WAV admin logs into `admin.wavbtl.cl` (Platform Supabase auth)
2. Navigates to `/tenants/mg-motor/open`
3. Portal generates a one-time magic link for MG Motor's Supabase auth:
   - Uses the tenant's `supabase_anon_key` from `tenant_registry`
   - Creates a magic link for the WAV admin's email via Supabase Admin API
   - The WAV admin's email is pre-registered in each tenant's Supabase with role `wav_admin`
4. Admin is redirected to `intelligence.mgmotor.cl` and authenticated
5. Inside the tenant dashboard, `wav_admin` role gates a "Tenant Settings" sidebar menu

### Tenant Settings (in-dashboard)

When a `wav_admin` is inside a tenant dashboard, they see an extra sidebar item: "Tenant Settings". This provides quick access to:
- Brand colors (color pickers, same as portal)
- Logo swap
- Feature toggles
- Label overrides

These write to the same Platform DB tables. The in-dashboard settings are a subset of what the full portal offers — convenience for quick adjustments without switching to the portal.

### Pre-registration

When a new tenant is created via the portal, it automatically:
1. Creates the tenant's Supabase auth user for each WAV admin email
2. Sets their `app_metadata.role = 'wav_admin'`
3. This is a one-time setup step in the tenant provisioning flow

---

## 8. Deploy Strategy

### Three Vercel projects per tenant + one portal

| App | Vercel Project | Domain | Supabase |
|-----|---------------|--------|----------|
| Admin Portal | wav-admin-portal | admin.wavbtl.cl | Platform instance |
| MG Motor | wav-mg-motor | intelligence.mgmotor.cl | MG instance |
| Client B | wav-cliente-b | insights.clienteb.com | B instance |

### Environment variables

**Admin Portal:**
- `APP_MODE=admin` — tells the app to render portal routes
- `PLATFORM_SUPABASE_URL` — Platform DB URL
- `PLATFORM_SUPABASE_SERVICE_ROLE_KEY` — for admin operations
- `PLATFORM_SUPABASE_ANON_KEY` — for auth

**Each Tenant Dashboard:**
- `APP_MODE=tenant`
- `TENANT_ID` — which tenant config to load
- `NEXT_PUBLIC_TENANT_ID` — client-side tenant identification
- `PLATFORM_SUPABASE_URL` — to read config from Platform DB
- `PLATFORM_SUPABASE_ANON_KEY` — read-only access to config
- `SUPABASE_URL` — tenant's own Supabase (business data)
- `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`
- `R2_ACCOUNT_ID`, `R2_ENDPOINT`
- `TRIGGER_API_KEY`

### App mode routing

The same codebase serves both admin and tenant modes. `APP_MODE` env var determines which routes are active:

- `APP_MODE=admin`: `/tenants/*` routes active, tenant dashboard routes disabled
- `APP_MODE=tenant`: `/dashboard/*`, `/sessions/*` etc. active, admin routes disabled

This is handled in `proxy.ts` — requests to admin routes on a tenant deploy return 404 and vice versa.

### Adding a new client

1. In Admin Portal: create tenant (fills `tenant_registry` + `tenant_configs`)
2. Provision Supabase instance for tenant, run business data migrations
3. Provision R2 bucket
4. Pre-register WAV admin emails in tenant's Supabase auth
5. Create Vercel project with env vars
6. Configure domain
7. Deploy

Estimated time: 30-60 minutes per new client.

---

## 9. Impact on Existing P1 Code

### Files modified

| File | Change |
|------|--------|
| `src/app/layout.tsx` | Add TenantProvider, async getTenant(), inject CSS vars, dynamic favicon |
| `src/app/globals.css` | Remove hardcoded MG colors, keep structural CSS only |
| `src/components/auth/login-form.tsx` | Logo and app name from `useTenant()` |
| `src/components/dashboard/wav-admin-dashboard.tsx` | Labels via `useLabel()`, add "Tenant Settings" link for wav_admin |
| `src/components/dashboard/mg-client-dashboard.tsx` | Labels via `useLabel()` |
| `src/components/dashboard/moderator-dashboard.tsx` | Labels via `useLabel()` |
| `src/proxy.ts` | Add APP_MODE routing logic |
| `.env.example` | Add `TENANT_ID`, `APP_MODE`, `PLATFORM_SUPABASE_*` vars |

### Files NOT modified

- `supabase/migrations/*` — business data schema unchanged (each tenant has own DB)
- `src/lib/supabase/*` — tenant Supabase clients read from env vars, already tenant-agnostic
- `src/lib/utils/auth.ts` — role logic unchanged
- `src/app/api/auth/callback/route.ts` — Supabase auth is per-instance

### New files

```
# Tenant config system
src/config/_default.json                  # Fallback config
src/config/locales/es-CL.json            # Base Spanish strings
src/config/locales/en-US.json            # Base English strings
src/config/tenant-schema.ts              # Zod schema + types
src/config/get-tenant.ts                 # Loads from Platform DB, caches, converts colors

# React layer
src/providers/tenant-provider.tsx
src/hooks/use-tenant.ts
src/hooks/use-feature.ts
src/hooks/use-label.ts

# Platform DB migrations
supabase/platform/migrations/001_tenant_registry.sql
supabase/platform/migrations/002_tenant_configs.sql
supabase/platform/migrations/003_tenant_locales.sql
supabase/platform/migrations/004_wav_admin_users.sql
supabase/platform/migrations/005_rls_policies.sql

# Admin portal pages
src/app/admin-portal/layout.tsx
src/app/admin-portal/login/page.tsx
src/app/admin-portal/tenants/page.tsx
src/app/admin-portal/tenants/new/page.tsx
src/app/admin-portal/tenants/[id]/page.tsx
src/app/admin-portal/tenants/[id]/brand/page.tsx
src/app/admin-portal/tenants/[id]/labels/page.tsx
src/app/admin-portal/tenants/[id]/features/page.tsx
src/app/admin-portal/tenants/[id]/pipeline/page.tsx
src/app/admin-portal/tenants/[id]/preview/page.tsx

# Admin components
src/components/admin/tenant-card.tsx
src/components/admin/color-picker.tsx
src/components/admin/feature-toggles.tsx
src/components/admin/label-editor.tsx
src/components/admin/pipeline-config.tsx
src/components/admin/preview-shell.tsx

# In-dashboard tenant settings (for wav_admin inside a tenant)
src/app/settings/tenant/page.tsx
src/components/settings/tenant-settings.tsx

# Config refresh endpoint
src/app/api/admin/refresh-config/route.ts

# Static assets
public/tenants/mg-motor/logo.svg
public/tenants/mg-motor/logo-small.svg
public/tenants/mg-motor/favicon.ico
public/tenants/_default/logo.svg
public/tenants/_default/logo-small.svg
public/tenants/_default/favicon.ico
```

---

## 10. Implementation Sequencing

This becomes **Phase 0** in the existing plan, split into sub-phases:

- **P0.1:** Platform DB schema + migrations + Supabase provisioning
- **P0.2:** `get-tenant.ts` (reads Platform DB, fallback to JSON, caching, hex→HSL)
- **P0.3:** TenantProvider + hooks (useTenant, useFeature, useLabel)
- **P0.4:** Refactor P1 code (remove hardcoded colors/labels, use tenant hooks)
- **P0.5:** WAV Admin Portal (tenant CRUD, brand editor, feature toggles, label editor)
- **P0.6:** Cross-tenant auth flow (magic link generation, pre-registration)
- **P0.7:** In-dashboard "Tenant Settings" for wav_admin
- **P0.8:** Config propagation (refresh endpoint, cache invalidation)

P1-P8 from the original plan remain unchanged but all UI code uses `useLabel()`, `useFeature()`, and `getTenant()`.

---

## 11. Testing Strategy

### Unit tests

- `get-tenant.ts`: loads from Platform DB, falls back to JSON, validates, caches, converts colors
- `tenant-schema.ts`: rejects invalid configs
- `use-label.ts`: resolution priority (DB labels > locale file > fallback)
- `use-feature.ts`: returns correct boolean per feature key
- `proxy.ts`: routes correctly based on APP_MODE

### Integration tests

- Render root layout with tenant config → verify CSS vars match
- Admin portal: create tenant → verify DB rows created
- Admin portal: edit colors → verify tenant app picks up new config after refresh
- Cross-tenant: generate magic link → verify redirect works

### E2E tests (admin portal)

- Login as wav_admin → see tenant list
- Create new tenant → fill form → verify appears in list
- Edit brand colors → preview shows changes → save → verify propagation

---

## 12. Migration Path to Monorepo

If client count exceeds 5 or clients need divergent features:

1. Init Turborepo at repo root
2. Move `src/config/` to `packages/config/`
3. Move shared components to `packages/ui/`
4. Move business logic to `packages/core/`
5. Admin portal becomes `apps/admin/`
6. Each tenant template becomes `apps/dashboard/`
7. Platform DB schema moves to `packages/platform-db/`

The clean separation (Platform DB for config, tenant DB for data, hooks for UI) makes this extraction mechanical.

---

*Spec v2.0 generated 2026-03-25. Supersedes v1.0.*
*Parent spec: `docs/superpowers/specs/2026-03-25-wav-intelligence-dashboard-design.md`*
