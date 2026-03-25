# White-Label Infrastructure — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add white-label infrastructure to WAV Intelligence so the same codebase serves multiple branded tenants, each with their own colors, logos, labels, features, pipeline config, and language — all managed from a central admin portal.

**Architecture:** Central Platform Supabase stores all tenant configs. Each tenant app reads its config from Platform DB at startup (with JSON fallback). A WAV Admin Portal at `admin.wavbtl.cl` provides CRUD for tenant configuration. WAV admins can cross-authenticate into any tenant dashboard. Same repo serves both admin portal and tenant dashboards via `APP_MODE` env var.

**Tech Stack:** Next.js 16, TypeScript, Supabase (Platform instance + per-tenant instances), Zod, shadcn/ui, Tailwind CSS (oklch), Vitest, React Testing Library

**Spec:** `docs/superpowers/specs/2026-03-25-white-label-architecture-design.md`

---

## Scope Note

This is **Phase 0** — it runs before P2 of the original dashboard plan. It modifies P1 code and creates the tenant infrastructure that all subsequent phases (P2–P8) build on.

The plan has 8 task groups. Tasks 1–4 build the tenant config system. Tasks 5–6 build the admin portal. Tasks 7–8 add cross-tenant auth and config propagation.

---

## File Structure

```
wav-intelligence/
├── supabase/
│   └── platform/                          ← NEW: Platform DB migrations
│       └── migrations/
│           ├── 001_tenant_registry.sql
│           ├── 002_tenant_configs.sql
│           ├── 003_tenant_locales.sql
│           ├── 004_wav_admin_users.sql
│           └── 005_rls_policies.sql
│
├── src/
│   ├── config/                            ← NEW: Tenant config system
│   │   ├── _default.json                  ← Fallback config (safety net)
│   │   ├── locales/
│   │   │   ├── es-CL.json
│   │   │   └── en-US.json
│   │   ├── tenant-schema.ts               ← Zod schema + TenantConfig type
│   │   ├── get-tenant.ts                  ← Loads from Platform DB, caches
│   │   └── platform-client.ts             ← Supabase client for Platform DB
│   │
│   ├── providers/
│   │   └── tenant-provider.tsx            ← NEW: React context
│   │
│   ├── hooks/                             ← NEW: Tenant hooks
│   │   ├── use-tenant.ts
│   │   ├── use-feature.ts
│   │   └── use-label.ts
│   │
│   ├── app/
│   │   ├── layout.tsx                     ← MODIFY: add TenantProvider + CSS vars
│   │   ├── globals.css                    ← MODIFY: remove MG-specific colors
│   │   ├── login/page.tsx                 ← MODIFY: use tenant branding
│   │   ├── dashboard/page.tsx             ← MODIFY: use tenant labels
│   │   │
│   │   ├── admin-portal/                  ← NEW: Admin portal routes
│   │   │   ├── layout.tsx
│   │   │   ├── login/page.tsx
│   │   │   ├── tenants/page.tsx
│   │   │   ├── tenants/new/page.tsx
│   │   │   ├── tenants/[id]/page.tsx
│   │   │   ├── tenants/[id]/brand/page.tsx
│   │   │   ├── tenants/[id]/labels/page.tsx
│   │   │   ├── tenants/[id]/features/page.tsx
│   │   │   └── tenants/[id]/pipeline/page.tsx
│   │   │
│   │   ├── settings/
│   │   │   └── tenant/page.tsx            ← NEW: In-dashboard tenant settings
│   │   │
│   │   └── api/
│   │       └── admin/
│   │           └── refresh-config/route.ts ← NEW: Cache invalidation endpoint
│   │
│   ├── components/
│   │   ├── auth/login-form.tsx            ← MODIFY: use tenant branding
│   │   ├── dashboard/
│   │   │   ├── wav-admin-dashboard.tsx    ← MODIFY: use labels + tenant settings link
│   │   │   ├── mg-client-dashboard.tsx    ← MODIFY: use labels
│   │   │   └── moderator-dashboard.tsx    ← MODIFY: use labels
│   │   └── admin/                         ← NEW: Admin portal components
│   │       ├── tenant-card.tsx
│   │       ├── color-picker.tsx
│   │       ├── feature-toggles.tsx
│   │       ├── label-editor.tsx
│   │       └── pipeline-config.tsx
│   │
│   └── proxy.ts                           ← MODIFY: add APP_MODE routing
│
├── tests/
│   └── unit/
│       ├── auth.test.ts                   ← EXISTS
│       ├── tenant-schema.test.ts          ← NEW
│       ├── get-tenant.test.ts             ← NEW
│       ├── use-label.test.ts              ← NEW
│       └── use-feature.test.ts            ← NEW
│
└── public/
    └── tenants/
        ├── mg-motor/
        │   ├── logo.svg
        │   ├── logo-small.svg
        │   └── favicon.ico
        └── _default/
            ├── logo.svg
            ├── logo-small.svg
            └── favicon.ico
```

---

## Task 1: Platform DB Schema

**Files:**
- Create: `supabase/platform/migrations/001_tenant_registry.sql`
- Create: `supabase/platform/migrations/002_tenant_configs.sql`
- Create: `supabase/platform/migrations/003_tenant_locales.sql`
- Create: `supabase/platform/migrations/004_wav_admin_users.sql`
- Create: `supabase/platform/migrations/005_rls_policies.sql`

- [ ] **Step 1: Create Platform DB migrations directory**

```bash
mkdir -p supabase/platform/migrations
```

- [ ] **Step 2: Write `001_tenant_registry.sql`**

```sql
-- Tenant registry: master list of tenants and their infrastructure
create table tenant_registry (
  id text primary key,
  name text not null,
  status text not null default 'active'
    check (status in ('active', 'suspended', 'provisioning')),
  domain text,
  supabase_url text,
  supabase_anon_key text,
  r2_bucket text,
  vercel_project_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Auto-update updated_at
create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger tenant_registry_updated_at
  before update on tenant_registry
  for each row execute function update_updated_at();
```

- [ ] **Step 3: Write `002_tenant_configs.sql`**

```sql
-- Tenant configuration: brand, features, pipeline settings
create table tenant_configs (
  tenant_id text primary key references tenant_registry(id) on delete cascade,
  brand jsonb not null,
  features jsonb not null,
  pipeline jsonb not null,
  locale text not null default 'es-CL',
  updated_at timestamptz not null default now()
);

create trigger tenant_configs_updated_at
  before update on tenant_configs
  for each row execute function update_updated_at();
```

- [ ] **Step 4: Write `003_tenant_locales.sql`**

```sql
-- Per-tenant label overrides for i18n
create table tenant_locales (
  tenant_id text not null references tenant_registry(id) on delete cascade,
  key text not null,
  value text not null,
  primary key (tenant_id, key)
);

-- Index for fast lookup by tenant
create index idx_tenant_locales_tenant on tenant_locales(tenant_id);
```

- [ ] **Step 5: Write `004_wav_admin_users.sql`**

```sql
-- WAV team members with portal access
create table wav_admin_users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  name text not null,
  role text not null default 'wav_admin'
    check (role in ('wav_super_admin', 'wav_admin')),
  created_at timestamptz not null default now()
);
```

- [ ] **Step 6: Write `005_rls_policies.sql`**

```sql
-- Enable RLS on all tables
alter table tenant_registry enable row level security;
alter table tenant_configs enable row level security;
alter table tenant_locales enable row level security;
alter table wav_admin_users enable row level security;

-- Service role bypasses RLS (used by admin portal backend and tenant app server)
-- Anon/authenticated users get restricted access

-- tenant_configs: readable by authenticated (tenant apps use service role anyway)
create policy "tenant_configs_read" on tenant_configs
  for select to authenticated using (true);

create policy "tenant_configs_write" on tenant_configs
  for all to authenticated using (
    exists (
      select 1 from wav_admin_users
      where email = auth.jwt()->>'email'
      and role in ('wav_super_admin', 'wav_admin')
    )
  );

-- tenant_locales: same pattern
create policy "tenant_locales_read" on tenant_locales
  for select to authenticated using (true);

create policy "tenant_locales_write" on tenant_locales
  for all to authenticated using (
    exists (
      select 1 from wav_admin_users
      where email = auth.jwt()->>'email'
      and role in ('wav_super_admin', 'wav_admin')
    )
  );

-- tenant_registry: readable by wav_admin+
create policy "tenant_registry_read" on tenant_registry
  for select to authenticated using (
    exists (
      select 1 from wav_admin_users
      where email = auth.jwt()->>'email'
    )
  );

create policy "tenant_registry_write" on tenant_registry
  for all to authenticated using (
    exists (
      select 1 from wav_admin_users
      where email = auth.jwt()->>'email'
      and role in ('wav_super_admin', 'wav_admin')
    )
  );

-- wav_admin_users: CRUD for super_admin only
create policy "wav_admin_users_read" on wav_admin_users
  for select to authenticated using (
    exists (
      select 1 from wav_admin_users
      where email = auth.jwt()->>'email'
    )
  );

create policy "wav_admin_users_write" on wav_admin_users
  for all to authenticated using (
    exists (
      select 1 from wav_admin_users
      where email = auth.jwt()->>'email'
      and role = 'wav_super_admin'
    )
  );
```

- [ ] **Step 7: Seed MG Motor tenant data**

Create `supabase/platform/seed.sql`:

```sql
-- Seed: MG Motor as first tenant
insert into tenant_registry (id, name, status, domain)
values ('mg-motor', 'MG Motor Chile', 'active', 'intelligence.mgmotor.cl');

insert into tenant_configs (tenant_id, brand, features, pipeline, locale)
values (
  'mg-motor',
  '{
    "name": "MG Motor Chile",
    "logo": "/tenants/mg-motor/logo.svg",
    "logoSmall": "/tenants/mg-motor/logo-small.svg",
    "favicon": "/tenants/mg-motor/favicon.ico",
    "colors": {
      "primary": "oklch(0.345 0.183 14.7)",
      "primaryForeground": "oklch(0.966 0.008 60)",
      "secondary": "oklch(0.127 0.088 348)",
      "secondaryForeground": "oklch(0.966 0.008 60)",
      "background": "oklch(0.097 0.015 270)",
      "foreground": "oklch(0.966 0.008 60)",
      "card": "oklch(0.13 0.015 270)",
      "cardForeground": "oklch(0.966 0.008 60)",
      "muted": "oklch(0.18 0.012 270)",
      "mutedForeground": "oklch(0.60 0.01 270)",
      "accent": "oklch(0.576 0.243 24.5)",
      "accentForeground": "oklch(1 0 0)",
      "destructive": "oklch(0.704 0.191 22.216)",
      "border": "oklch(1 0 0 / 12%)",
      "input": "oklch(1 0 0 / 15%)",
      "ring": "oklch(0.345 0.183 14.7)"
    },
    "fonts": {
      "sans": "Geist Sans",
      "mono": "Geist Mono"
    }
  }'::jsonb,
  '{
    "video360": true,
    "videoDslr": true,
    "audioTracks": true,
    "semanticSearch": true,
    "ragQA": true,
    "pdfExport": true,
    "csvExport": true,
    "trends": true
  }'::jsonb,
  '{
    "transcriptionProvider": "elevenlabs",
    "videoSources": ["360", "dslr"],
    "audioTrackCount": 13,
    "aiModel": "anthropic/claude-sonnet-4.6"
  }'::jsonb,
  'es-CL'
);

-- Seed: WAV super admin
insert into wav_admin_users (email, name, role)
values ('federico@wearevision.cl', 'Federico Elgueta', 'wav_super_admin');
```

- [ ] **Step 8: Commit**

```bash
git add supabase/platform/
git commit -m "feat: Platform DB schema for multi-tenant config"
```

---

## Task 2: Tenant Config System (TypeScript)

**Files:**
- Create: `src/config/tenant-schema.ts`
- Create: `src/config/platform-client.ts`
- Create: `src/config/get-tenant.ts`
- Create: `src/config/_default.json`
- Create: `src/config/locales/es-CL.json`
- Create: `src/config/locales/en-US.json`
- Create: `tests/unit/tenant-schema.test.ts`
- Create: `tests/unit/get-tenant.test.ts`

- [ ] **Step 1: Write failing test for tenant schema validation**

Create `tests/unit/tenant-schema.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { tenantConfigSchema, type TenantConfig } from '@/config/tenant-schema'

const validConfig: TenantConfig = {
  id: 'mg-motor',
  name: 'MG Motor Chile',
  status: 'active',
  domain: 'intelligence.mgmotor.cl',
  brand: {
    name: 'MG Motor Chile',
    logo: '/tenants/mg-motor/logo.svg',
    logoSmall: '/tenants/mg-motor/logo-small.svg',
    favicon: '/tenants/mg-motor/favicon.ico',
    colors: {
      primary: 'oklch(0.345 0.183 14.7)',
      primaryForeground: 'oklch(0.966 0.008 60)',
      secondary: 'oklch(0.127 0.088 348)',
      secondaryForeground: 'oklch(0.966 0.008 60)',
      background: 'oklch(0.097 0.015 270)',
      foreground: 'oklch(0.966 0.008 60)',
      card: 'oklch(0.13 0.015 270)',
      cardForeground: 'oklch(0.966 0.008 60)',
      muted: 'oklch(0.18 0.012 270)',
      mutedForeground: 'oklch(0.60 0.01 270)',
      accent: 'oklch(0.576 0.243 24.5)',
      accentForeground: 'oklch(1 0 0)',
      destructive: 'oklch(0.704 0.191 22.216)',
      border: 'oklch(1 0 0 / 12%)',
      input: 'oklch(1 0 0 / 15%)',
      ring: 'oklch(0.345 0.183 14.7)',
    },
    fonts: { sans: 'Geist Sans', mono: 'Geist Mono' },
  },
  labels: { 'nav.sessions': 'Sesiones' },
  features: {
    video360: true,
    videoDslr: true,
    audioTracks: true,
    semanticSearch: true,
    ragQA: true,
    pdfExport: true,
    csvExport: true,
    trends: true,
  },
  pipeline: {
    transcriptionProvider: 'elevenlabs',
    videoSources: ['360', 'dslr'],
    audioTrackCount: 13,
    aiModel: 'anthropic/claude-sonnet-4.6',
  },
  locale: 'es-CL',
}

describe('tenantConfigSchema', () => {
  it('accepts a valid config', () => {
    const result = tenantConfigSchema.safeParse(validConfig)
    expect(result.success).toBe(true)
  })

  it('rejects config missing brand.colors.primary', () => {
    const invalid = {
      ...validConfig,
      brand: {
        ...validConfig.brand,
        colors: { ...validConfig.brand.colors, primary: undefined },
      },
    }
    const result = tenantConfigSchema.safeParse(invalid)
    expect(result.success).toBe(false)
  })

  it('rejects invalid status', () => {
    const invalid = { ...validConfig, status: 'deleted' }
    const result = tenantConfigSchema.safeParse(invalid)
    expect(result.success).toBe(false)
  })

  it('rejects invalid transcription provider', () => {
    const invalid = {
      ...validConfig,
      pipeline: { ...validConfig.pipeline, transcriptionProvider: 'invalid' },
    }
    const result = tenantConfigSchema.safeParse(invalid)
    expect(result.success).toBe(false)
  })

  it('accepts empty labels', () => {
    const withEmpty = { ...validConfig, labels: {} }
    const result = tenantConfigSchema.safeParse(withEmpty)
    expect(result.success).toBe(true)
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd ~/projects/wav-intelligence && npx vitest run tests/unit/tenant-schema.test.ts
```

Expected: FAIL — `Cannot find module '@/config/tenant-schema'`

- [ ] **Step 3: Implement `src/config/tenant-schema.ts`**

```typescript
import { z } from 'zod'

const colorsSchema = z.object({
  primary: z.string(),
  primaryForeground: z.string(),
  secondary: z.string(),
  secondaryForeground: z.string(),
  background: z.string(),
  foreground: z.string(),
  card: z.string(),
  cardForeground: z.string(),
  muted: z.string(),
  mutedForeground: z.string(),
  accent: z.string(),
  accentForeground: z.string(),
  destructive: z.string(),
  border: z.string(),
  input: z.string(),
  ring: z.string(),
})

const brandSchema = z.object({
  name: z.string(),
  logo: z.string(),
  logoSmall: z.string(),
  favicon: z.string(),
  colors: colorsSchema,
  fonts: z.object({
    sans: z.string(),
    mono: z.string(),
  }),
})

const featuresSchema = z.object({
  video360: z.boolean(),
  videoDslr: z.boolean(),
  audioTracks: z.boolean(),
  semanticSearch: z.boolean(),
  ragQA: z.boolean(),
  pdfExport: z.boolean(),
  csvExport: z.boolean(),
  trends: z.boolean(),
})

const pipelineSchema = z.object({
  transcriptionProvider: z.enum(['elevenlabs', 'deepgram', 'whisper']),
  videoSources: z.array(z.enum(['360', 'dslr'])),
  audioTrackCount: z.number().int().min(1).max(30),
  aiModel: z.string(),
})

export const tenantConfigSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: z.enum(['active', 'suspended', 'provisioning']),
  domain: z.string().nullable(),
  brand: brandSchema,
  labels: z.record(z.string(), z.string()),
  features: featuresSchema,
  pipeline: pipelineSchema,
  locale: z.string(),
})

export type TenantConfig = z.infer<typeof tenantConfigSchema>
export type TenantFeatures = z.infer<typeof featuresSchema>
export type TenantBrand = z.infer<typeof brandSchema>
export type TenantColors = z.infer<typeof colorsSchema>
```

- [ ] **Step 4: Run test — expect PASS**

```bash
cd ~/projects/wav-intelligence && npx vitest run tests/unit/tenant-schema.test.ts
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Write failing test for `get-tenant.ts`**

Create `tests/unit/get-tenant.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock the platform client before importing get-tenant
vi.mock('@/config/platform-client', () => ({
  fetchTenantFromPlatform: vi.fn(),
}))

import { getTenant, clearTenantCache } from '@/config/get-tenant'
import { fetchTenantFromPlatform } from '@/config/platform-client'

const mockPlatformResponse = {
  registry: {
    id: 'mg-motor',
    name: 'MG Motor Chile',
    status: 'active',
    domain: 'intelligence.mgmotor.cl',
  },
  config: {
    brand: {
      name: 'MG Motor Chile',
      logo: '/tenants/mg-motor/logo.svg',
      logoSmall: '/tenants/mg-motor/logo-small.svg',
      favicon: '/tenants/mg-motor/favicon.ico',
      colors: {
        primary: 'oklch(0.345 0.183 14.7)',
        primaryForeground: 'oklch(0.966 0.008 60)',
        secondary: 'oklch(0.127 0.088 348)',
        secondaryForeground: 'oklch(0.966 0.008 60)',
        background: 'oklch(0.097 0.015 270)',
        foreground: 'oklch(0.966 0.008 60)',
        card: 'oklch(0.13 0.015 270)',
        cardForeground: 'oklch(0.966 0.008 60)',
        muted: 'oklch(0.18 0.012 270)',
        mutedForeground: 'oklch(0.60 0.01 270)',
        accent: 'oklch(0.576 0.243 24.5)',
        accentForeground: 'oklch(1 0 0)',
        destructive: 'oklch(0.704 0.191 22.216)',
        border: 'oklch(1 0 0 / 12%)',
        input: 'oklch(1 0 0 / 15%)',
        ring: 'oklch(0.345 0.183 14.7)',
      },
      fonts: { sans: 'Geist Sans', mono: 'Geist Mono' },
    },
    features: {
      video360: true, videoDslr: true, audioTracks: true,
      semanticSearch: true, ragQA: true, pdfExport: true,
      csvExport: true, trends: true,
    },
    pipeline: {
      transcriptionProvider: 'elevenlabs',
      videoSources: ['360', 'dslr'],
      audioTrackCount: 13,
      aiModel: 'anthropic/claude-sonnet-4.6',
    },
    locale: 'es-CL',
  },
  locales: [
    { key: 'nav.sessions', value: 'Sesiones' },
    { key: 'nav.dashboard', value: 'Panel' },
  ],
}

describe('getTenant', () => {
  beforeEach(() => {
    clearTenantCache()
    vi.stubEnv('TENANT_ID', 'mg-motor')
    vi.mocked(fetchTenantFromPlatform).mockResolvedValue(mockPlatformResponse)
  })

  it('loads tenant from Platform DB and returns validated config', async () => {
    const config = await getTenant()
    expect(config.id).toBe('mg-motor')
    expect(config.brand.colors.primary).toBe('oklch(0.345 0.183 14.7)')
    expect(config.features.video360).toBe(true)
  })

  it('merges locale labels into config.labels', async () => {
    const config = await getTenant()
    expect(config.labels['nav.sessions']).toBe('Sesiones')
    expect(config.labels['nav.dashboard']).toBe('Panel')
  })

  it('caches config after first call', async () => {
    await getTenant()
    await getTenant()
    expect(fetchTenantFromPlatform).toHaveBeenCalledTimes(1)
  })

  it('returns fresh config after cache clear', async () => {
    await getTenant()
    clearTenantCache()
    await getTenant()
    expect(fetchTenantFromPlatform).toHaveBeenCalledTimes(2)
  })

  it('falls back to _default.json when Platform DB fails', async () => {
    vi.mocked(fetchTenantFromPlatform).mockRejectedValue(new Error('DB down'))
    const config = await getTenant()
    expect(config.id).toBe('_default')
    expect(config.name).toBe('WAV Intelligence')
  })

  it('throws when TENANT_ID is not set', async () => {
    vi.stubEnv('TENANT_ID', '')
    await expect(getTenant()).rejects.toThrow('TENANT_ID environment variable is required')
  })
})
```

- [ ] **Step 6: Run test — expect FAIL**

```bash
cd ~/projects/wav-intelligence && npx vitest run tests/unit/get-tenant.test.ts
```

Expected: FAIL — `Cannot find module '@/config/get-tenant'`

- [ ] **Step 7: Create `src/config/platform-client.ts`**

```typescript
import { createClient } from '@supabase/supabase-js'

function getPlatformClient() {
  const url = process.env.PLATFORM_SUPABASE_URL
  const key = process.env.PLATFORM_SUPABASE_SERVICE_ROLE_KEY
    || process.env.PLATFORM_SUPABASE_ANON_KEY

  if (!url || !key) {
    throw new Error('PLATFORM_SUPABASE_URL and PLATFORM_SUPABASE_ANON_KEY are required')
  }

  return createClient(url, key)
}

export interface PlatformTenantData {
  registry: {
    id: string
    name: string
    status: string
    domain: string | null
  }
  config: {
    brand: Record<string, unknown>
    features: Record<string, unknown>
    pipeline: Record<string, unknown>
    locale: string
  }
  locales: Array<{ key: string; value: string }>
}

export async function fetchTenantFromPlatform(
  tenantId: string
): Promise<PlatformTenantData> {
  const supabase = getPlatformClient()

  const [registryResult, configResult, localesResult] = await Promise.all([
    supabase
      .from('tenant_registry')
      .select('id, name, status, domain')
      .eq('id', tenantId)
      .single(),
    supabase
      .from('tenant_configs')
      .select('brand, features, pipeline, locale')
      .eq('tenant_id', tenantId)
      .single(),
    supabase
      .from('tenant_locales')
      .select('key, value')
      .eq('tenant_id', tenantId),
  ])

  if (registryResult.error) {
    throw new Error(`Tenant '${tenantId}' not found in registry: ${registryResult.error.message}`)
  }
  if (configResult.error) {
    throw new Error(`Tenant config for '${tenantId}' not found: ${configResult.error.message}`)
  }

  return {
    registry: registryResult.data,
    config: configResult.data,
    locales: localesResult.data ?? [],
  }
}
```

- [ ] **Step 8: Create `src/config/_default.json`**

```json
{
  "id": "_default",
  "name": "WAV Intelligence",
  "status": "active",
  "domain": null,
  "brand": {
    "name": "WAV Intelligence",
    "logo": "/tenants/_default/logo.svg",
    "logoSmall": "/tenants/_default/logo-small.svg",
    "favicon": "/tenants/_default/favicon.ico",
    "colors": {
      "primary": "oklch(0.345 0.183 14.7)",
      "primaryForeground": "oklch(0.966 0.008 60)",
      "secondary": "oklch(0.127 0.088 348)",
      "secondaryForeground": "oklch(0.966 0.008 60)",
      "background": "oklch(0.097 0.015 270)",
      "foreground": "oklch(0.966 0.008 60)",
      "card": "oklch(0.13 0.015 270)",
      "cardForeground": "oklch(0.966 0.008 60)",
      "muted": "oklch(0.18 0.012 270)",
      "mutedForeground": "oklch(0.60 0.01 270)",
      "accent": "oklch(0.576 0.243 24.5)",
      "accentForeground": "oklch(1 0 0)",
      "destructive": "oklch(0.704 0.191 22.216)",
      "border": "oklch(1 0 0 / 12%)",
      "input": "oklch(1 0 0 / 15%)",
      "ring": "oklch(0.345 0.183 14.7)"
    },
    "fonts": {
      "sans": "Geist Sans",
      "mono": "Geist Mono"
    }
  },
  "labels": {},
  "features": {
    "video360": true,
    "videoDslr": true,
    "audioTracks": true,
    "semanticSearch": true,
    "ragQA": true,
    "pdfExport": true,
    "csvExport": true,
    "trends": true
  },
  "pipeline": {
    "transcriptionProvider": "elevenlabs",
    "videoSources": ["360", "dslr"],
    "audioTrackCount": 13,
    "aiModel": "anthropic/claude-sonnet-4.6"
  },
  "locale": "es-CL"
}
```

- [ ] **Step 9: Create locale files**

Create `src/config/locales/es-CL.json`:

```json
{
  "nav.dashboard": "Panel",
  "nav.sessions": "Sesiones",
  "nav.search": "Buscar",
  "nav.trends": "Tendencias",
  "nav.settings": "Configuración",
  "session.status.scheduled": "Programada",
  "session.status.uploaded": "Archivos subidos",
  "session.status.processing": "Procesando",
  "session.status.ready": "Lista",
  "session.status.error": "Error",
  "dashboard.title.admin": "Panel de administración",
  "dashboard.title.client": "Resultados de investigación",
  "dashboard.title.moderator": "Mis sesiones asignadas",
  "dashboard.sessions": "Sesiones",
  "dashboard.processing": "Procesamiento",
  "dashboard.users": "Usuarios",
  "dashboard.available_sessions": "Sesiones disponibles",
  "dashboard.generated_insights": "Insights generados",
  "dashboard.assigned_sessions": "Sesiones asignadas",
  "auth.check_email": "Revisa tu correo",
  "auth.magic_link_sent": "Enviamos un enlace de acceso a",
  "auth.use_other_email": "Usar otro correo",
  "auth.email_label": "Correo electrónico",
  "auth.email_placeholder": "tu@empresa.com",
  "auth.send_link": "Enviar enlace de acceso",
  "auth.sending": "Enviando…",
  "auth.access_dashboard": "Accede a tu dashboard",
  "auth.magic_link_description": "Te enviaremos un enlace de acceso a tu correo",
  "auth.trouble": "¿Problemas para acceder?",
  "auth.contact_support": "Contacta soporte",
  "auth.pending_activation": "Cuenta pendiente de activación",
  "auth.no_role": "Tu cuenta aún no tiene un rol asignado. Contacta al administrador de WAV.",
  "export.pdf": "Exportar PDF",
  "export.csv": "Exportar CSV",
  "common.welcome": "Bienvenido",
  "common.full_access": "acceso completo",
  "common.under_construction": "Dashboard completo en construcción",
  "common.sessions_will_appear": "Tus sesiones de investigación aparecerán aquí cuando estén listas",
  "common.assigned_sessions_will_appear": "Las sesiones asignadas a tu perfil aparecerán aquí"
}
```

Create `src/config/locales/en-US.json`:

```json
{
  "nav.dashboard": "Dashboard",
  "nav.sessions": "Sessions",
  "nav.search": "Search",
  "nav.trends": "Trends",
  "nav.settings": "Settings",
  "session.status.scheduled": "Scheduled",
  "session.status.uploaded": "Uploaded",
  "session.status.processing": "Processing",
  "session.status.ready": "Ready",
  "session.status.error": "Error",
  "dashboard.title.admin": "Administration Panel",
  "dashboard.title.client": "Research Results",
  "dashboard.title.moderator": "My Assigned Sessions",
  "dashboard.sessions": "Sessions",
  "dashboard.processing": "Processing",
  "dashboard.users": "Users",
  "dashboard.available_sessions": "Available Sessions",
  "dashboard.generated_insights": "Generated Insights",
  "dashboard.assigned_sessions": "Assigned Sessions",
  "auth.check_email": "Check your email",
  "auth.magic_link_sent": "We sent an access link to",
  "auth.use_other_email": "Use a different email",
  "auth.email_label": "Email address",
  "auth.email_placeholder": "you@company.com",
  "auth.send_link": "Send access link",
  "auth.sending": "Sending…",
  "auth.access_dashboard": "Access your dashboard",
  "auth.magic_link_description": "We'll send an access link to your email",
  "auth.trouble": "Having trouble?",
  "auth.contact_support": "Contact support",
  "auth.pending_activation": "Account pending activation",
  "auth.no_role": "Your account does not have a role assigned yet. Contact the WAV administrator.",
  "export.pdf": "Export PDF",
  "export.csv": "Export CSV",
  "common.welcome": "Welcome",
  "common.full_access": "full access",
  "common.under_construction": "Full dashboard under construction",
  "common.sessions_will_appear": "Your research sessions will appear here when ready",
  "common.assigned_sessions_will_appear": "Sessions assigned to your profile will appear here"
}
```

- [ ] **Step 10: Implement `src/config/get-tenant.ts`**

```typescript
import { tenantConfigSchema, type TenantConfig } from './tenant-schema'
import { fetchTenantFromPlatform } from './platform-client'
import defaultConfig from './_default.json'
import esLocale from './locales/es-CL.json'
import enLocale from './locales/en-US.json'

const localeFiles: Record<string, Record<string, string>> = {
  'es-CL': esLocale,
  'en-US': enLocale,
}

let cachedConfig: TenantConfig | null = null

export function clearTenantCache(): void {
  cachedConfig = null
}

export async function getTenant(): Promise<TenantConfig> {
  if (cachedConfig) return cachedConfig

  const tenantId = process.env.TENANT_ID
  if (!tenantId) {
    throw new Error('TENANT_ID environment variable is required')
  }

  try {
    const data = await fetchTenantFromPlatform(tenantId)

    // Merge locale labels: base locale file + tenant-specific overrides
    const baseLocale = localeFiles[data.config.locale] ?? localeFiles['es-CL']
    const tenantLabels: Record<string, string> = {}
    for (const { key, value } of data.locales) {
      tenantLabels[key] = value
    }

    const raw = {
      id: data.registry.id,
      name: data.registry.name,
      status: data.registry.status,
      domain: data.registry.domain,
      brand: data.config.brand,
      labels: { ...baseLocale, ...tenantLabels },
      features: data.config.features,
      pipeline: data.config.pipeline,
      locale: data.config.locale,
    }

    const config = tenantConfigSchema.parse(raw)
    cachedConfig = config
    return config
  } catch (error) {
    console.warn(
      `[get-tenant] Failed to load tenant '${tenantId}' from Platform DB, using fallback:`,
      error instanceof Error ? error.message : error
    )

    const baseLocale = localeFiles[defaultConfig.locale] ?? localeFiles['es-CL']
    const fallback = {
      ...defaultConfig,
      labels: { ...baseLocale },
    }

    const config = tenantConfigSchema.parse(fallback)
    cachedConfig = config
    return config
  }
}
```

- [ ] **Step 11: Run tests — expect PASS**

```bash
cd ~/projects/wav-intelligence && npx vitest run tests/unit/get-tenant.test.ts tests/unit/tenant-schema.test.ts
```

Expected: All tests PASS.

- [ ] **Step 12: Commit**

```bash
git add src/config/ tests/unit/tenant-schema.test.ts tests/unit/get-tenant.test.ts
git commit -m "feat: tenant config system — schema, loader, locales, fallback"
```

---

## Task 3: React Context + Hooks

**Files:**
- Create: `src/providers/tenant-provider.tsx`
- Create: `src/hooks/use-tenant.ts`
- Create: `src/hooks/use-feature.ts`
- Create: `src/hooks/use-label.ts`
- Create: `tests/unit/use-label.test.ts`
- Create: `tests/unit/use-feature.test.ts`

- [ ] **Step 1: Write failing test for `useLabel`**

Create `tests/unit/use-label.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { renderHook } from '@testing-library/react'
import { type ReactNode } from 'react'
import { TenantProvider } from '@/providers/tenant-provider'
import { useLabel } from '@/hooks/use-label'
import { type TenantConfig } from '@/config/tenant-schema'

const mockConfig: TenantConfig = {
  id: 'test',
  name: 'Test Tenant',
  status: 'active',
  domain: null,
  brand: {
    name: 'Test',
    logo: '/logo.svg',
    logoSmall: '/logo-small.svg',
    favicon: '/favicon.ico',
    colors: {
      primary: 'oklch(0.5 0.1 0)',
      primaryForeground: 'oklch(1 0 0)',
      secondary: 'oklch(0.3 0.1 0)',
      secondaryForeground: 'oklch(1 0 0)',
      background: 'oklch(0.1 0 0)',
      foreground: 'oklch(0.9 0 0)',
      card: 'oklch(0.15 0 0)',
      cardForeground: 'oklch(0.9 0 0)',
      muted: 'oklch(0.2 0 0)',
      mutedForeground: 'oklch(0.6 0 0)',
      accent: 'oklch(0.5 0.2 30)',
      accentForeground: 'oklch(1 0 0)',
      destructive: 'oklch(0.5 0.2 20)',
      border: 'oklch(1 0 0 / 12%)',
      input: 'oklch(1 0 0 / 15%)',
      ring: 'oklch(0.5 0.1 0)',
    },
    fonts: { sans: 'Geist Sans', mono: 'Geist Mono' },
  },
  labels: {
    'nav.sessions': 'Sesiones',
    'custom.label': 'Custom Value',
  },
  features: {
    video360: true, videoDslr: false, audioTracks: true,
    semanticSearch: true, ragQA: true, pdfExport: true,
    csvExport: true, trends: true,
  },
  pipeline: {
    transcriptionProvider: 'elevenlabs',
    videoSources: ['360'],
    audioTrackCount: 6,
    aiModel: 'anthropic/claude-sonnet-4.6',
  },
  locale: 'es-CL',
}

function wrapper({ children }: { children: ReactNode }) {
  return <TenantProvider config={mockConfig}>{children}</TenantProvider>
}

describe('useLabel', () => {
  it('returns label from tenant config', () => {
    const { result } = renderHook(() => useLabel('nav.sessions'), { wrapper })
    expect(result.current).toBe('Sesiones')
  })

  it('returns key as fallback for missing label', () => {
    const { result } = renderHook(() => useLabel('nonexistent.key'), { wrapper })
    expect(result.current).toBe('nonexistent.key')
  })

  it('returns tenant-specific custom labels', () => {
    const { result } = renderHook(() => useLabel('custom.label'), { wrapper })
    expect(result.current).toBe('Custom Value')
  })
})
```

- [ ] **Step 2: Write failing test for `useFeature`**

Create `tests/unit/use-feature.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { renderHook } from '@testing-library/react'
import { type ReactNode } from 'react'
import { TenantProvider } from '@/providers/tenant-provider'
import { useFeature } from '@/hooks/use-feature'
import { type TenantConfig } from '@/config/tenant-schema'

// Reuse the same mockConfig from use-label.test.ts inline
const mockConfig: TenantConfig = {
  id: 'test',
  name: 'Test Tenant',
  status: 'active',
  domain: null,
  brand: {
    name: 'Test',
    logo: '/logo.svg',
    logoSmall: '/logo-small.svg',
    favicon: '/favicon.ico',
    colors: {
      primary: 'oklch(0.5 0.1 0)',
      primaryForeground: 'oklch(1 0 0)',
      secondary: 'oklch(0.3 0.1 0)',
      secondaryForeground: 'oklch(1 0 0)',
      background: 'oklch(0.1 0 0)',
      foreground: 'oklch(0.9 0 0)',
      card: 'oklch(0.15 0 0)',
      cardForeground: 'oklch(0.9 0 0)',
      muted: 'oklch(0.2 0 0)',
      mutedForeground: 'oklch(0.6 0 0)',
      accent: 'oklch(0.5 0.2 30)',
      accentForeground: 'oklch(1 0 0)',
      destructive: 'oklch(0.5 0.2 20)',
      border: 'oklch(1 0 0 / 12%)',
      input: 'oklch(1 0 0 / 15%)',
      ring: 'oklch(0.5 0.1 0)',
    },
    fonts: { sans: 'Geist Sans', mono: 'Geist Mono' },
  },
  labels: {},
  features: {
    video360: true, videoDslr: false, audioTracks: true,
    semanticSearch: true, ragQA: true, pdfExport: true,
    csvExport: true, trends: true,
  },
  pipeline: {
    transcriptionProvider: 'elevenlabs',
    videoSources: ['360'],
    audioTrackCount: 6,
    aiModel: 'anthropic/claude-sonnet-4.6',
  },
  locale: 'es-CL',
}

function wrapper({ children }: { children: ReactNode }) {
  return <TenantProvider config={mockConfig}>{children}</TenantProvider>
}

describe('useFeature', () => {
  it('returns true for enabled feature', () => {
    const { result } = renderHook(() => useFeature('video360'), { wrapper })
    expect(result.current).toBe(true)
  })

  it('returns false for disabled feature', () => {
    const { result } = renderHook(() => useFeature('videoDslr'), { wrapper })
    expect(result.current).toBe(false)
  })
})
```

- [ ] **Step 3: Run tests — expect FAIL**

```bash
cd ~/projects/wav-intelligence && npx vitest run tests/unit/use-label.test.ts tests/unit/use-feature.test.ts
```

Expected: FAIL — modules not found.

- [ ] **Step 4: Implement TenantProvider and hooks**

Create `src/providers/tenant-provider.tsx`:

```tsx
'use client'

import { createContext, useContext } from 'react'
import { type TenantConfig } from '@/config/tenant-schema'

const TenantContext = createContext<TenantConfig | null>(null)

export function TenantProvider({
  config,
  children,
}: {
  config: TenantConfig
  children: React.ReactNode
}) {
  return (
    <TenantContext.Provider value={config}>
      {children}
    </TenantContext.Provider>
  )
}

export function useTenantContext(): TenantConfig {
  const ctx = useContext(TenantContext)
  if (!ctx) {
    throw new Error('useTenantContext must be used within TenantProvider')
  }
  return ctx
}
```

Create `src/hooks/use-tenant.ts`:

```typescript
'use client'

import { useTenantContext } from '@/providers/tenant-provider'
import { type TenantConfig } from '@/config/tenant-schema'

export function useTenant(): TenantConfig {
  return useTenantContext()
}
```

Create `src/hooks/use-feature.ts`:

```typescript
'use client'

import { useTenantContext } from '@/providers/tenant-provider'
import { type TenantFeatures } from '@/config/tenant-schema'

export function useFeature(key: keyof TenantFeatures): boolean {
  const config = useTenantContext()
  return config.features[key]
}
```

Create `src/hooks/use-label.ts`:

```typescript
'use client'

import { useTenantContext } from '@/providers/tenant-provider'

export function useLabel(key: string): string {
  const config = useTenantContext()
  return config.labels[key] ?? key
}
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
cd ~/projects/wav-intelligence && npx vitest run tests/unit/use-label.test.ts tests/unit/use-feature.test.ts
```

Expected: All 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/providers/ src/hooks/ tests/unit/use-label.test.ts tests/unit/use-feature.test.ts
git commit -m "feat: TenantProvider + useLabel, useFeature, useTenant hooks"
```

---

## Task 4: Refactor P1 Code to Use Tenant System

**Files:**
- Modify: `src/app/layout.tsx`
- Modify: `src/app/globals.css`
- Modify: `src/app/login/page.tsx`
- Modify: `src/app/dashboard/page.tsx`
- Modify: `src/components/auth/login-form.tsx`
- Modify: `src/components/dashboard/wav-admin-dashboard.tsx`
- Modify: `src/components/dashboard/mg-client-dashboard.tsx`
- Modify: `src/components/dashboard/moderator-dashboard.tsx`
- Modify: `src/proxy.ts`
- Modify: `.env.example`

- [ ] **Step 1: Update `.env.example`**

Add to `.env.example`:

```bash
# Multi-tenant
APP_MODE=tenant                    # "tenant" or "admin"
TENANT_ID=mg-motor                 # Which tenant config to load
NEXT_PUBLIC_TENANT_ID=mg-motor     # Client-side tenant ID

# Platform DB (shared config)
PLATFORM_SUPABASE_URL=
PLATFORM_SUPABASE_ANON_KEY=
PLATFORM_SUPABASE_SERVICE_ROLE_KEY=
```

- [ ] **Step 2: Update `src/app/globals.css` — remove hardcoded MG colors from `.dark`**

Replace the entire `.dark { ... }` block with:

```css
.dark {
  /* Tenant colors injected via CSS vars from TenantProvider — see layout.tsx */
  /* Only structural defaults here as safety net */
  --radius: 0.625rem;
}
```

Keep the `:root { ... }` block (light mode defaults) and all `@theme inline`, `@layer base` sections unchanged. The MG brand tokens (`--color-mg-red` etc. in `@theme inline`) stay as utility aliases — they'll be overridden by the tenant CSS vars.

- [ ] **Step 3: Update `src/app/layout.tsx`**

Replace the entire file:

```tsx
import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { getTenant } from '@/config/get-tenant'
import { TenantProvider } from '@/providers/tenant-provider'
import './globals.css'

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
})

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
})

export async function generateMetadata(): Promise<Metadata> {
  const tenant = await getTenant()
  return {
    title: tenant.brand.name,
    description: `Dashboard de investigación — ${tenant.brand.name}`,
    icons: { icon: tenant.brand.favicon },
  }
}

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const tenant = await getTenant()
  const { colors } = tenant.brand

  const tenantCssVars: Record<string, string> = {
    '--background': colors.background,
    '--foreground': colors.foreground,
    '--card': colors.card,
    '--card-foreground': colors.cardForeground,
    '--popover': colors.card,
    '--popover-foreground': colors.cardForeground,
    '--primary': colors.primary,
    '--primary-foreground': colors.primaryForeground,
    '--secondary': colors.secondary,
    '--secondary-foreground': colors.secondaryForeground,
    '--muted': colors.muted,
    '--muted-foreground': colors.mutedForeground,
    '--accent': colors.accent,
    '--accent-foreground': colors.accentForeground,
    '--destructive': colors.destructive,
    '--border': colors.border,
    '--input': colors.input,
    '--ring': colors.ring,
  }

  return (
    <html
      lang={tenant.locale.split('-')[0]}
      className={`${geistSans.variable} ${geistMono.variable} dark h-full antialiased`}
      style={tenantCssVars as React.CSSProperties}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <TenantProvider config={tenant}>
          {children}
        </TenantProvider>
      </body>
    </html>
  )
}
```

- [ ] **Step 4: Update `src/app/login/page.tsx`**

Replace the entire file:

```tsx
import { getTenant } from '@/config/get-tenant'
import { LoginForm } from '@/components/auth/login-form'

export default async function LoginPage() {
  const tenant = await getTenant()

  return (
    <main className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-8">
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center gap-3 mb-4">
            <img
              src={tenant.brand.logoSmall}
              alt={tenant.brand.name}
              className="h-8"
            />
            <span className="text-border">|</span>
            <span className="text-foreground font-medium text-lg">Intelligence</span>
          </div>
          <h1 className="text-xl font-semibold text-foreground">
            {tenant.labels['auth.access_dashboard'] ?? 'Accede a tu dashboard'}
          </h1>
          <p className="text-muted-foreground text-sm">
            {tenant.labels['auth.magic_link_description'] ?? 'Te enviaremos un enlace de acceso a tu correo'}
          </p>
        </div>

        <div className="bg-card border border-border rounded-lg p-6 shadow-sm">
          <LoginForm />
        </div>

        <p className="text-center text-xs text-muted-foreground">
          {tenant.labels['auth.trouble'] ?? '¿Problemas para acceder?'}{' '}
          <a
            href="mailto:soporte@wav.cl"
            className="text-accent hover:text-primary underline underline-offset-4 transition-colors"
          >
            {tenant.labels['auth.contact_support'] ?? 'Contacta soporte'}
          </a>
        </p>
      </div>
    </main>
  )
}
```

- [ ] **Step 5: Update `src/components/auth/login-form.tsx`**

Replace the entire file:

```tsx
'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import { useLabel } from '@/hooks/use-label'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

type LoginState = 'idle' | 'loading' | 'sent' | 'error'

export function LoginForm() {
  const [email, setEmail] = useState('')
  const [state, setState] = useState<LoginState>('idle')
  const [errorMessage, setErrorMessage] = useState('')
  const label = useLabel

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!email.trim()) return

    setState('loading')
    setErrorMessage('')

    const supabase = createClient()
    const { error } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: {
        emailRedirectTo: `${window.location.origin}/api/auth/callback`,
      },
    })

    if (error) {
      setState('error')
      setErrorMessage(error.message)
    } else {
      setState('sent')
    }
  }

  if (state === 'sent') {
    return (
      <div className="text-center space-y-2">
        <p className="text-foreground font-medium">{label('auth.check_email')}</p>
        <p className="text-muted-foreground text-sm">
          {label('auth.magic_link_sent')} <span className="text-foreground">{email}</span>
        </p>
        <Button
          variant="ghost"
          size="sm"
          className="mt-4 text-muted-foreground"
          onClick={() => { setState('idle'); setEmail('') }}
        >
          {label('auth.use_other_email')}
        </Button>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="email">{label('auth.email_label')}</Label>
        <Input
          id="email"
          type="email"
          placeholder={label('auth.email_placeholder')}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={state === 'loading'}
          required
          autoFocus
        />
      </div>

      {state === 'error' && (
        <p className="text-destructive text-sm">{errorMessage}</p>
      )}

      <Button
        type="submit"
        className="w-full bg-primary hover:bg-primary/90 text-primary-foreground"
        disabled={state === 'loading' || !email.trim()}
      >
        {state === 'loading' ? label('auth.sending') : label('auth.send_link')}
      </Button>
    </form>
  )
}
```

- [ ] **Step 6: Update dashboard components**

Replace `src/components/dashboard/wav-admin-dashboard.tsx`:

```tsx
'use client'

import type { User } from '@supabase/supabase-js'
import { useLabel } from '@/hooks/use-label'

interface WavAdminDashboardProps {
  user: User
}

export function WavAdminDashboard({ user }: WavAdminDashboardProps) {
  const label = useLabel

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">{label('dashboard.title.admin')}</h1>
        <p className="text-muted-foreground text-sm mt-1">
          {label('common.welcome')}, {user.email} — {label('common.full_access')}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-card border border-border rounded-lg p-5 space-y-2">
          <p className="text-xs text-muted-foreground uppercase tracking-wide">{label('dashboard.sessions')}</p>
          <p className="text-3xl font-bold text-foreground">—</p>
        </div>
        <div className="bg-card border border-border rounded-lg p-5 space-y-2">
          <p className="text-xs text-muted-foreground uppercase tracking-wide">{label('dashboard.processing')}</p>
          <p className="text-3xl font-bold text-foreground">—</p>
        </div>
        <div className="bg-card border border-border rounded-lg p-5 space-y-2">
          <p className="text-xs text-muted-foreground uppercase tracking-wide">{label('dashboard.users')}</p>
          <p className="text-3xl font-bold text-foreground">—</p>
        </div>
      </div>

      <div className="bg-card border border-border rounded-lg p-5">
        <p className="text-sm text-muted-foreground">{label('common.under_construction')}</p>
      </div>
    </div>
  )
}
```

Replace `src/components/dashboard/mg-client-dashboard.tsx`:

```tsx
'use client'

import type { User } from '@supabase/supabase-js'
import { useTenant } from '@/hooks/use-tenant'
import { useLabel } from '@/hooks/use-label'

interface MgClientDashboardProps {
  user: User
}

export function MgClientDashboard({ user }: MgClientDashboardProps) {
  const tenant = useTenant()
  const label = useLabel

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">{label('dashboard.title.client')}</h1>
        <p className="text-muted-foreground text-sm mt-1">
          {label('common.welcome')}, {user.email} — {tenant.brand.name}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-card border border-border rounded-lg p-5 space-y-2">
          <p className="text-xs text-muted-foreground uppercase tracking-wide">{label('dashboard.available_sessions')}</p>
          <p className="text-3xl font-bold text-primary">—</p>
        </div>
        <div className="bg-card border border-border rounded-lg p-5 space-y-2">
          <p className="text-xs text-muted-foreground uppercase tracking-wide">{label('dashboard.generated_insights')}</p>
          <p className="text-3xl font-bold text-primary">—</p>
        </div>
      </div>

      <div className="bg-card border border-border rounded-lg p-5">
        <p className="text-sm text-muted-foreground">{label('common.sessions_will_appear')}</p>
      </div>
    </div>
  )
}
```

Replace `src/components/dashboard/moderator-dashboard.tsx`:

```tsx
'use client'

import type { User } from '@supabase/supabase-js'
import { useLabel } from '@/hooks/use-label'

interface ModeratorDashboardProps {
  user: User
}

export function ModeratorDashboard({ user }: ModeratorDashboardProps) {
  const label = useLabel

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">{label('dashboard.title.moderator')}</h1>
        <p className="text-muted-foreground text-sm mt-1">
          {label('common.welcome')}, {user.email}
        </p>
      </div>

      <div className="bg-card border border-border rounded-lg p-5 space-y-2">
        <p className="text-xs text-muted-foreground uppercase tracking-wide">{label('dashboard.assigned_sessions')}</p>
        <p className="text-3xl font-bold text-foreground">—</p>
      </div>

      <div className="bg-card border border-border rounded-lg p-5">
        <p className="text-sm text-muted-foreground">{label('common.assigned_sessions_will_appear')}</p>
      </div>
    </div>
  )
}
```

- [ ] **Step 7: Update `src/app/dashboard/page.tsx`**

Replace the no-role holding page strings:

```tsx
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { getRoleFromToken } from '@/lib/utils/auth'
import { getTenant } from '@/config/get-tenant'
import { WavAdminDashboard } from '@/components/dashboard/wav-admin-dashboard'
import { MgClientDashboard } from '@/components/dashboard/mg-client-dashboard'
import { ModeratorDashboard } from '@/components/dashboard/moderator-dashboard'

export default async function DashboardPage() {
  const supabase = await createClient()
  const tenant = await getTenant()

  const { data: { user }, error } = await supabase.auth.getUser()

  if (error || !user) {
    redirect('/login')
  }

  const { data: { session } } = await supabase.auth.getSession()
  const jwt = session?.access_token
    ? JSON.parse(atob(session.access_token.split('.')[1]))
    : {}

  const role = getRoleFromToken(jwt)

  if (!role) {
    return (
      <main className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="text-center space-y-3 max-w-sm">
          <p className="text-foreground font-medium">
            {tenant.labels['auth.pending_activation'] ?? 'Cuenta pendiente de activación'}
          </p>
          <p className="text-muted-foreground text-sm">
            {tenant.labels['auth.no_role'] ?? 'Tu cuenta aún no tiene un rol asignado.'}
          </p>
          <a
            href="mailto:soporte@wav.cl"
            className="text-accent hover:text-primary text-sm underline underline-offset-4 transition-colors"
          >
            soporte@wav.cl
          </a>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {role === 'wav_admin' && <WavAdminDashboard user={user} />}
        {role === 'mg_client' && <MgClientDashboard user={user} />}
        {role === 'moderator' && <ModeratorDashboard user={user} />}
      </div>
    </main>
  )
}
```

- [ ] **Step 8: Update `src/proxy.ts` — add APP_MODE routing**

Replace the entire file:

```typescript
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  const appMode = process.env.APP_MODE || 'tenant'
  const pathname = request.nextUrl.pathname

  // APP_MODE routing: block cross-mode routes
  if (appMode === 'tenant' && pathname.startsWith('/admin-portal')) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 })
  }
  if (appMode === 'admin' && !pathname.startsWith('/admin-portal') && !pathname.startsWith('/api') && pathname !== '/favicon.ico') {
    // Admin mode: redirect non-portal routes to portal
    return NextResponse.redirect(new URL('/admin-portal/tenants', request.url))
  }

  let supabaseResponse = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return request.cookies.getAll() },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value))
          supabaseResponse = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options))
        },
      },
    }
  )

  // Refresh session
  const { data: { user } } = await supabase.auth.getUser()

  const isPublicPath =
    pathname.startsWith('/login') ||
    pathname.startsWith('/admin-portal/login') ||
    pathname.startsWith('/api/auth') ||
    pathname === '/favicon.ico'

  if (!user && !isPublicPath) {
    const loginPath = appMode === 'admin' ? '/admin-portal/login' : '/login'
    return NextResponse.redirect(new URL(loginPath, request.url))
  }

  return supabaseResponse
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|tenants/).*)'],
}
```

- [ ] **Step 9: Run all tests**

```bash
cd ~/projects/wav-intelligence && npx vitest run
```

Expected: All tests PASS (auth tests + new tenant tests).

- [ ] **Step 10: Commit**

```bash
git add src/app/ src/components/ src/proxy.ts .env.example
git commit -m "refactor: P1 code now uses tenant config system — dynamic branding, labels, APP_MODE routing"
```

---

## Task 5: Static Assets + Logo Placeholders

**Files:**
- Create: `public/tenants/mg-motor/logo.svg`
- Create: `public/tenants/mg-motor/logo-small.svg`
- Create: `public/tenants/mg-motor/favicon.ico`
- Create: `public/tenants/_default/logo.svg`
- Create: `public/tenants/_default/logo-small.svg`
- Create: `public/tenants/_default/favicon.ico`

- [ ] **Step 1: Create placeholder SVG logos**

Create `public/tenants/mg-motor/logo.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 40" fill="none">
  <text x="0" y="30" font-family="system-ui" font-size="28" font-weight="700" fill="#DC0032">MG</text>
  <text x="50" y="30" font-family="system-ui" font-size="20" fill="#F7F3EF">Motor</text>
</svg>
```

Create `public/tenants/mg-motor/logo-small.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40" fill="none">
  <text x="2" y="30" font-family="system-ui" font-size="28" font-weight="700" fill="#DC0032">MG</text>
</svg>
```

Copy `public/favicon.ico` to `public/tenants/mg-motor/favicon.ico`.

Create `public/tenants/_default/logo.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 40" fill="none">
  <text x="0" y="30" font-family="system-ui" font-size="24" font-weight="700" fill="#A0A0B0">WAV</text>
  <text x="60" y="30" font-family="system-ui" font-size="18" fill="#F5F5F5">Intelligence</text>
</svg>
```

Create `public/tenants/_default/logo-small.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40" fill="none">
  <text x="0" y="30" font-family="system-ui" font-size="22" font-weight="700" fill="#A0A0B0">WAV</text>
</svg>
```

Copy `public/favicon.ico` to `public/tenants/_default/favicon.ico`.

- [ ] **Step 2: Commit**

```bash
git add public/tenants/
git commit -m "feat: tenant logo placeholders for MG Motor and default"
```

---

## Task 6: Config Refresh Endpoint

**Files:**
- Create: `src/app/api/admin/refresh-config/route.ts`

- [ ] **Step 1: Implement refresh endpoint**

Create `src/app/api/admin/refresh-config/route.ts`:

```typescript
import { NextResponse } from 'next/server'
import { clearTenantCache } from '@/config/get-tenant'

export async function POST(request: Request) {
  const authHeader = request.headers.get('authorization')
  const expectedToken = process.env.ADMIN_REFRESH_SECRET

  if (!expectedToken || authHeader !== `Bearer ${expectedToken}`) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  clearTenantCache()

  return NextResponse.json({ ok: true, message: 'Tenant config cache cleared' })
}
```

- [ ] **Step 2: Add `ADMIN_REFRESH_SECRET` to `.env.example`**

Add to `.env.example`:

```bash
# Admin config refresh
ADMIN_REFRESH_SECRET=             # Secret for /api/admin/refresh-config
```

- [ ] **Step 3: Commit**

```bash
git add src/app/api/admin/ .env.example
git commit -m "feat: config refresh endpoint for cache invalidation"
```

---

## Task 7: WAV Admin Portal — Layout + Auth + Tenant List

**Files:**
- Create: `src/app/admin-portal/layout.tsx`
- Create: `src/app/admin-portal/login/page.tsx`
- Create: `src/app/admin-portal/tenants/page.tsx`
- Create: `src/components/admin/tenant-card.tsx`

- [ ] **Step 1: Create admin portal layout**

Create `src/app/admin-portal/layout.tsx`:

```tsx
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'WAV Admin Portal',
  description: 'Multi-tenant administration for WAV Intelligence',
}

export default function AdminPortalLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border px-6 py-3 flex items-center gap-4">
        <span className="font-bold text-lg text-foreground">WAV Admin</span>
        <span className="text-muted-foreground text-sm">Multi-Tenant Portal</span>
      </header>
      <main className="max-w-6xl mx-auto px-6 py-8">
        {children}
      </main>
    </div>
  )
}
```

- [ ] **Step 2: Create admin login page**

Create `src/app/admin-portal/login/page.tsx`:

```tsx
'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function AdminLoginPage() {
  const [email, setEmail] = useState('')
  const [state, setState] = useState<'idle' | 'loading' | 'sent' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!email.trim()) return

    setState('loading')
    setErrorMessage('')

    const supabase = createClient()
    const { error } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: {
        emailRedirectTo: `${window.location.origin}/api/auth/callback`,
      },
    })

    if (error) {
      setState('error')
      setErrorMessage(error.message)
    } else {
      setState('sent')
    }
  }

  if (state === 'sent') {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-2">
          <p className="text-foreground font-medium">Check your email</p>
          <p className="text-muted-foreground text-sm">
            Access link sent to <span className="text-foreground">{email}</span>
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <h1 className="text-xl font-semibold text-foreground">WAV Admin Portal</h1>
          <p className="text-muted-foreground text-sm mt-1">WAV team access only</p>
        </div>

        <div className="bg-card border border-border rounded-lg p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@wearevision.cl"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={state === 'loading'}
                required
                autoFocus
              />
            </div>

            {state === 'error' && (
              <p className="text-destructive text-sm">{errorMessage}</p>
            )}

            <Button
              type="submit"
              className="w-full"
              disabled={state === 'loading' || !email.trim()}
            >
              {state === 'loading' ? 'Sending…' : 'Send access link'}
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create tenant card component**

Create `src/components/admin/tenant-card.tsx`:

```tsx
import { Badge } from '@/components/ui/badge'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'

interface TenantCardProps {
  id: string
  name: string
  status: string
  domain: string | null
}

export function TenantCard({ id, name, status, domain }: TenantCardProps) {
  const statusColor = {
    active: 'bg-green-500/20 text-green-400',
    suspended: 'bg-yellow-500/20 text-yellow-400',
    provisioning: 'bg-blue-500/20 text-blue-400',
  }[status] ?? 'bg-muted text-muted-foreground'

  return (
    <a href={`/admin-portal/tenants/${id}`}>
      <Card className="hover:border-primary/40 transition-colors cursor-pointer">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">{name}</CardTitle>
            <Badge className={statusColor} variant="secondary">{status}</Badge>
          </div>
          <CardDescription>{domain ?? 'No domain configured'}</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground font-mono">{id}</p>
        </CardContent>
      </Card>
    </a>
  )
}
```

- [ ] **Step 4: Create tenant list page**

Create `src/app/admin-portal/tenants/page.tsx`:

```tsx
import { createClient } from '@supabase/supabase-js'
import { TenantCard } from '@/components/admin/tenant-card'
import { Button } from '@/components/ui/button'

async function getTenants() {
  const supabase = createClient(
    process.env.PLATFORM_SUPABASE_URL!,
    process.env.PLATFORM_SUPABASE_SERVICE_ROLE_KEY!
  )

  const { data, error } = await supabase
    .from('tenant_registry')
    .select('id, name, status, domain')
    .order('created_at', { ascending: true })

  if (error) throw new Error(`Failed to load tenants: ${error.message}`)
  return data
}

export default async function TenantsPage() {
  const tenants = await getTenants()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Tenants</h1>
          <p className="text-muted-foreground text-sm mt-1">{tenants.length} tenant(s)</p>
        </div>
        <a href="/admin-portal/tenants/new">
          <Button>New Tenant</Button>
        </a>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {tenants.map((t) => (
          <TenantCard key={t.id} {...t} />
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Commit**

```bash
git add src/app/admin-portal/ src/components/admin/
git commit -m "feat: admin portal — layout, login, tenant list"
```

---

## Task 8: Admin Portal — Tenant Detail + Brand Editor + Feature Toggles

**Files:**
- Create: `src/app/admin-portal/tenants/[id]/page.tsx`
- Create: `src/app/admin-portal/tenants/[id]/brand/page.tsx`
- Create: `src/app/admin-portal/tenants/[id]/features/page.tsx`
- Create: `src/app/admin-portal/tenants/[id]/labels/page.tsx`
- Create: `src/app/admin-portal/tenants/[id]/pipeline/page.tsx`
- Create: `src/components/admin/color-picker.tsx`
- Create: `src/components/admin/feature-toggles.tsx`
- Create: `src/components/admin/label-editor.tsx`
- Create: `src/components/admin/pipeline-config.tsx`

- [ ] **Step 1: Create tenant detail page**

Create `src/app/admin-portal/tenants/[id]/page.tsx`:

```tsx
import { createClient } from '@supabase/supabase-js'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { notFound } from 'next/navigation'

async function getTenantDetail(id: string) {
  const supabase = createClient(
    process.env.PLATFORM_SUPABASE_URL!,
    process.env.PLATFORM_SUPABASE_SERVICE_ROLE_KEY!
  )

  const [registryResult, configResult] = await Promise.all([
    supabase.from('tenant_registry').select('*').eq('id', id).single(),
    supabase.from('tenant_configs').select('*').eq('tenant_id', id).single(),
  ])

  if (registryResult.error) return null
  return { registry: registryResult.data, config: configResult.data }
}

export default async function TenantDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const tenant = await getTenantDetail(id)

  if (!tenant) notFound()

  const links = [
    { href: `/admin-portal/tenants/${id}/brand`, label: 'Brand & Colors', description: 'Logo, colors, fonts' },
    { href: `/admin-portal/tenants/${id}/features`, label: 'Features', description: 'Toggle features on/off' },
    { href: `/admin-portal/tenants/${id}/labels`, label: 'Labels & i18n', description: 'Custom labels and translations' },
    { href: `/admin-portal/tenants/${id}/pipeline`, label: 'Pipeline', description: 'Transcription, AI model, video sources' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">{tenant.registry.name}</h1>
        <p className="text-muted-foreground text-sm mt-1">
          {tenant.registry.domain ?? 'No domain'} · {tenant.registry.status}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {links.map((link) => (
          <a key={link.href} href={link.href}>
            <Card className="hover:border-primary/40 transition-colors cursor-pointer h-full">
              <CardHeader>
                <CardTitle className="text-base">{link.label}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{link.description}</p>
              </CardContent>
            </Card>
          </a>
        ))}
      </div>

      {tenant.registry.domain && (
        <div className="pt-4">
          <a href={`https://${tenant.registry.domain}`} target="_blank" rel="noopener">
            <Button variant="outline">Open Dashboard →</Button>
          </a>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Create brand editor page**

Create `src/components/admin/color-picker.tsx`:

```tsx
'use client'

import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface ColorPickerProps {
  label: string
  name: string
  value: string
  onChange: (name: string, value: string) => void
}

export function ColorPicker({ label, name, value, onChange }: ColorPickerProps) {
  return (
    <div className="flex items-center gap-3">
      <div
        className="w-8 h-8 rounded border border-border shrink-0"
        style={{ backgroundColor: value }}
      />
      <div className="flex-1 space-y-1">
        <Label className="text-xs">{label}</Label>
        <Input
          value={value}
          onChange={(e) => onChange(name, e.target.value)}
          className="font-mono text-xs h-8"
        />
      </div>
    </div>
  )
}
```

Create `src/app/admin-portal/tenants/[id]/brand/page.tsx`:

```tsx
'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { ColorPicker } from '@/components/admin/color-picker'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface BrandConfig {
  name: string
  logo: string
  logoSmall: string
  favicon: string
  colors: Record<string, string>
  fonts: { sans: string; mono: string }
}

export default function BrandEditorPage() {
  const { id } = useParams<{ id: string }>()
  const [brand, setBrand] = useState<BrandConfig | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    async function load() {
      const supabase = createClient()
      const { data } = await supabase
        .from('tenant_configs')
        .select('brand')
        .eq('tenant_id', id)
        .single()
      if (data) setBrand(data.brand as BrandConfig)
    }
    load()
  }, [id])

  function handleColorChange(name: string, value: string) {
    if (!brand) return
    setBrand({
      ...brand,
      colors: { ...brand.colors, [name]: value },
    })
  }

  async function handleSave() {
    if (!brand) return
    setSaving(true)
    setMessage('')

    const supabase = createClient()
    const { error } = await supabase
      .from('tenant_configs')
      .update({ brand })
      .eq('tenant_id', id)

    if (error) {
      setMessage(`Error: ${error.message}`)
    } else {
      setMessage('Saved! Refresh tenant dashboard to see changes.')
    }
    setSaving(false)
  }

  if (!brand) return <p className="text-muted-foreground">Loading...</p>

  const colorEntries = Object.entries(brand.colors)

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Brand & Colors</h1>
        <p className="text-muted-foreground text-sm mt-1">Tenant: {id}</p>
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
          <Label>Brand Name</Label>
          <Input
            value={brand.name}
            onChange={(e) => setBrand({ ...brand, name: e.target.value })}
          />
        </div>
        <div className="space-y-2">
          <Label>Logo URL</Label>
          <Input
            value={brand.logo}
            onChange={(e) => setBrand({ ...brand, logo: e.target.value })}
            className="font-mono text-sm"
          />
        </div>
      </div>

      <div>
        <h2 className="text-lg font-medium text-foreground mb-4">Colors</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {colorEntries.map(([name, value]) => (
            <ColorPicker
              key={name}
              label={name}
              name={name}
              value={value}
              onChange={handleColorChange}
            />
          ))}
        </div>
      </div>

      <div className="flex items-center gap-4">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Brand'}
        </Button>
        {message && (
          <p className={`text-sm ${message.startsWith('Error') ? 'text-destructive' : 'text-green-400'}`}>
            {message}
          </p>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create feature toggles page**

Create `src/components/admin/feature-toggles.tsx`:

```tsx
'use client'

import { Label } from '@/components/ui/label'

interface FeatureToggleProps {
  name: string
  label: string
  enabled: boolean
  onChange: (name: string, enabled: boolean) => void
}

export function FeatureToggle({ name, label, enabled, onChange }: FeatureToggleProps) {
  return (
    <div className="flex items-center justify-between py-2">
      <Label>{label}</Label>
      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        onClick={() => onChange(name, !enabled)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          enabled ? 'bg-primary' : 'bg-muted'
        }`}
      >
        <span
          className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
            enabled ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
    </div>
  )
}
```

Create `src/app/admin-portal/tenants/[id]/features/page.tsx`:

```tsx
'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { FeatureToggle } from '@/components/admin/feature-toggles'
import { Button } from '@/components/ui/button'

const featureLabels: Record<string, string> = {
  video360: '360° Video Player',
  videoDslr: 'DSLR Video Player',
  audioTracks: 'Audio Track Waveforms',
  semanticSearch: 'Semantic Search',
  ragQA: 'AI Q&A (RAG)',
  pdfExport: 'PDF Export',
  csvExport: 'CSV Export',
  trends: 'Cross-Session Trends',
}

export default function FeaturesPage() {
  const { id } = useParams<{ id: string }>()
  const [features, setFeatures] = useState<Record<string, boolean> | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    async function load() {
      const supabase = createClient()
      const { data } = await supabase
        .from('tenant_configs')
        .select('features')
        .eq('tenant_id', id)
        .single()
      if (data) setFeatures(data.features as Record<string, boolean>)
    }
    load()
  }, [id])

  function handleToggle(name: string, enabled: boolean) {
    if (!features) return
    setFeatures({ ...features, [name]: enabled })
  }

  async function handleSave() {
    if (!features) return
    setSaving(true)
    setMessage('')

    const supabase = createClient()
    const { error } = await supabase
      .from('tenant_configs')
      .update({ features })
      .eq('tenant_id', id)

    if (error) {
      setMessage(`Error: ${error.message}`)
    } else {
      setMessage('Saved!')
    }
    setSaving(false)
  }

  if (!features) return <p className="text-muted-foreground">Loading...</p>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Feature Toggles</h1>
        <p className="text-muted-foreground text-sm mt-1">Tenant: {id}</p>
      </div>

      <div className="bg-card border border-border rounded-lg p-6 divide-y divide-border">
        {Object.entries(featureLabels).map(([key, label]) => (
          <FeatureToggle
            key={key}
            name={key}
            label={label}
            enabled={features[key] ?? false}
            onChange={handleToggle}
          />
        ))}
      </div>

      <div className="flex items-center gap-4">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Features'}
        </Button>
        {message && <p className="text-sm text-green-400">{message}</p>}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Create labels editor page**

Create `src/components/admin/label-editor.tsx`:

```tsx
'use client'

import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

interface LabelRow {
  key: string
  value: string
}

interface LabelEditorProps {
  labels: LabelRow[]
  onChange: (index: number, field: 'key' | 'value', val: string) => void
  onAdd: () => void
  onRemove: (index: number) => void
}

export function LabelEditor({ labels, onChange, onAdd, onRemove }: LabelEditorProps) {
  return (
    <div className="space-y-2">
      {labels.map((row, i) => (
        <div key={i} className="flex items-center gap-2">
          <Input
            value={row.key}
            onChange={(e) => onChange(i, 'key', e.target.value)}
            placeholder="key (e.g. nav.sessions)"
            className="font-mono text-xs flex-1"
          />
          <Input
            value={row.value}
            onChange={(e) => onChange(i, 'value', e.target.value)}
            placeholder="value"
            className="flex-1"
          />
          <Button variant="ghost" size="sm" onClick={() => onRemove(i)}>×</Button>
        </div>
      ))}
      <Button variant="outline" size="sm" onClick={onAdd}>+ Add label</Button>
    </div>
  )
}
```

Create `src/app/admin-portal/tenants/[id]/labels/page.tsx`:

```tsx
'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { LabelEditor } from '@/components/admin/label-editor'
import { Button } from '@/components/ui/button'

interface LabelRow {
  key: string
  value: string
}

export default function LabelsPage() {
  const { id } = useParams<{ id: string }>()
  const [labels, setLabels] = useState<LabelRow[]>([])
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    async function load() {
      const supabase = createClient()
      const { data } = await supabase
        .from('tenant_locales')
        .select('key, value')
        .eq('tenant_id', id)
        .order('key')
      if (data) setLabels(data)
    }
    load()
  }, [id])

  function handleChange(index: number, field: 'key' | 'value', val: string) {
    const updated = labels.map((row, i) =>
      i === index ? { ...row, [field]: val } : row
    )
    setLabels(updated)
  }

  function handleAdd() {
    setLabels([...labels, { key: '', value: '' }])
  }

  function handleRemove(index: number) {
    setLabels(labels.filter((_, i) => i !== index))
  }

  async function handleSave() {
    setSaving(true)
    setMessage('')

    const supabase = createClient()

    // Delete existing and re-insert (simple upsert pattern)
    await supabase.from('tenant_locales').delete().eq('tenant_id', id)

    const validLabels = labels.filter((l) => l.key.trim() && l.value.trim())
    if (validLabels.length > 0) {
      const { error } = await supabase
        .from('tenant_locales')
        .insert(validLabels.map((l) => ({ tenant_id: id, key: l.key, value: l.value })))

      if (error) {
        setMessage(`Error: ${error.message}`)
        setSaving(false)
        return
      }
    }

    setMessage('Saved!')
    setSaving(false)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Labels & i18n</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Tenant: {id} · {labels.length} override(s)
        </p>
      </div>

      <div className="bg-card border border-border rounded-lg p-6">
        <LabelEditor
          labels={labels}
          onChange={handleChange}
          onAdd={handleAdd}
          onRemove={handleRemove}
        />
      </div>

      <div className="flex items-center gap-4">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Labels'}
        </Button>
        {message && <p className="text-sm text-green-400">{message}</p>}
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Create pipeline config page**

Create `src/components/admin/pipeline-config.tsx`:

```tsx
'use client'

import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'

interface PipelineConfigProps {
  pipeline: {
    transcriptionProvider: string
    videoSources: string[]
    audioTrackCount: number
    aiModel: string
  }
  onChange: (pipeline: PipelineConfigProps['pipeline']) => void
}

export function PipelineConfigForm({ pipeline, onChange }: PipelineConfigProps) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Transcription Provider</Label>
        <select
          value={pipeline.transcriptionProvider}
          onChange={(e) => onChange({ ...pipeline, transcriptionProvider: e.target.value })}
          className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm"
        >
          <option value="elevenlabs">ElevenLabs Scribe</option>
          <option value="deepgram">Deepgram</option>
          <option value="whisper">Whisper</option>
        </select>
      </div>

      <div className="space-y-2">
        <Label>Audio Track Count</Label>
        <Input
          type="number"
          min={1}
          max={30}
          value={pipeline.audioTrackCount}
          onChange={(e) => onChange({ ...pipeline, audioTrackCount: parseInt(e.target.value) || 1 })}
        />
      </div>

      <div className="space-y-2">
        <Label>AI Model</Label>
        <Input
          value={pipeline.aiModel}
          onChange={(e) => onChange({ ...pipeline, aiModel: e.target.value })}
          className="font-mono text-sm"
        />
      </div>

      <div className="space-y-2">
        <Label>Video Sources</Label>
        <div className="flex gap-4">
          {(['360', 'dslr'] as const).map((source) => (
            <label key={source} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={pipeline.videoSources.includes(source)}
                onChange={(e) => {
                  const sources = e.target.checked
                    ? [...pipeline.videoSources, source]
                    : pipeline.videoSources.filter((s) => s !== source)
                  onChange({ ...pipeline, videoSources: sources })
                }}
                className="rounded"
              />
              {source === '360' ? '360° Camera' : 'DSLR Camera'}
            </label>
          ))}
        </div>
      </div>
    </div>
  )
}
```

Create `src/app/admin-portal/tenants/[id]/pipeline/page.tsx`:

```tsx
'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { PipelineConfigForm } from '@/components/admin/pipeline-config'
import { Button } from '@/components/ui/button'

export default function PipelinePage() {
  const { id } = useParams<{ id: string }>()
  const [pipeline, setPipeline] = useState<{
    transcriptionProvider: string
    videoSources: string[]
    audioTrackCount: number
    aiModel: string
  } | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    async function load() {
      const supabase = createClient()
      const { data } = await supabase
        .from('tenant_configs')
        .select('pipeline')
        .eq('tenant_id', id)
        .single()
      if (data) setPipeline(data.pipeline as typeof pipeline)
    }
    load()
  }, [id])

  async function handleSave() {
    if (!pipeline) return
    setSaving(true)
    setMessage('')

    const supabase = createClient()
    const { error } = await supabase
      .from('tenant_configs')
      .update({ pipeline })
      .eq('tenant_id', id)

    if (error) {
      setMessage(`Error: ${error.message}`)
    } else {
      setMessage('Saved!')
    }
    setSaving(false)
  }

  if (!pipeline) return <p className="text-muted-foreground">Loading...</p>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Pipeline Config</h1>
        <p className="text-muted-foreground text-sm mt-1">Tenant: {id}</p>
      </div>

      <div className="bg-card border border-border rounded-lg p-6">
        <PipelineConfigForm pipeline={pipeline} onChange={setPipeline} />
      </div>

      <div className="flex items-center gap-4">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Pipeline'}
        </Button>
        {message && <p className="text-sm text-green-400">{message}</p>}
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Run all tests**

```bash
cd ~/projects/wav-intelligence && npx vitest run
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/app/admin-portal/ src/components/admin/
git commit -m "feat: admin portal — tenant detail, brand editor, feature toggles, labels, pipeline config"
```

---

## Done Criteria

**P0 DONE ✅ when:**
- Platform DB schema exists with 4 tables + RLS + MG Motor seed data
- Tenant config loads from Platform DB with JSON fallback
- TenantProvider + hooks work (useLabel, useFeature, useTenant)
- All P1 code uses tenant system (no hardcoded MG branding)
- Admin portal at `/admin-portal/` has: login, tenant list, brand editor, feature toggles, label editor, pipeline config
- APP_MODE routing blocks cross-mode access
- Config refresh endpoint clears cache
- All tests pass

---

## Pre-Production Checklist (deferred)

These items from the spec are intentionally deferred to a later task:

- [ ] Cross-tenant auth via magic link (Task 7 in spec — implement when first real cross-tenant access needed)
- [ ] In-dashboard "Tenant Settings" (Task 8 in spec — implement when WAV admin workflow is validated)
- [ ] Admin portal: new tenant creation form + provisioning automation
- [ ] Admin portal: preview page

Rationale: The core infrastructure (config system + admin CRUD) must ship first. Cross-tenant auth and in-dashboard settings are additive — they don't block P2–P8 work.

---

*Plan generated 2026-03-25. Spec: `docs/superpowers/specs/2026-03-25-white-label-architecture-design.md`*
