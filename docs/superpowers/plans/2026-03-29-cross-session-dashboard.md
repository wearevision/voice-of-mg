# Cross-Session Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cross-session analytics dashboard with sentiment analysis, purchase barrier aggregation, competitor mention tracking, and trend visualization — role-gated per tenant feature flags.

**Architecture:** Server component prefetches studies/days for filters, renders role-specific client dashboard. Each dashboard uses `useDashboardData` hook to fetch 6 API routes in parallel with filter params. Widgets are recharts-based client components receiving typed data as props.

**Tech Stack:** Next.js 16 App Router, Supabase (server client), recharts 3.8.1, shadcn/ui, Tailwind CSS (dark theme), Vitest

---

## File Structure

```
src/types/dashboard.ts                              — Dashboard type interfaces
src/lib/dashboard/filters.ts                        — Shared filter parsing + query builder
src/hooks/use-dashboard-data.ts                     — Client-side data fetching hook

src/app/api/dashboard/
  sessions/route.ts                                 — Session list with summary stats
  sentiment-summary/route.ts                        — Aggregated sentiment counts
  sentiment-heatmap/route.ts                        — Topic × sentiment matrix
  barriers/route.ts                                 — Purchase barrier aggregation
  competitors/route.ts                              — Competitor mention aggregation
  trends/route.ts                                   — Sentiment over time by topic

src/components/dashboard/
  dashboard-filters.tsx                             — Study/day/topic/date filter bar
  sentiment-hero.tsx                                — KPI cards (positive/neutral/negative %)
  sentiment-heatmap.tsx                             — Topic × sentiment colored grid
  purchase-barriers.tsx                             — Horizontal bar chart by category
  competitor-mentions.tsx                           — Stacked bar chart by brand
  sentiment-trends.tsx                              — Multi-line chart over time
  session-cards.tsx                                 — Clickable session summary cards
  mg-client-dashboard.tsx                           — MODIFY: full MG client layout
  wav-admin-dashboard.tsx                           — MODIFY: admin layout with extras
  moderator-dashboard.tsx                           — MODIFY: simplified moderator view

tests/unit/dashboard/
  dashboard-types.test.ts                           — Type compilation smoke test
  filters-helper.test.ts                            — parseDashboardParams + applyVerbatimFilters
  sessions-route.test.ts
  sentiment-summary-route.test.ts
  sentiment-heatmap-route.test.ts
  barriers-route.test.ts
  competitors-route.test.ts
  trends-route.test.ts
  sentiment-hero.test.tsx
  session-cards.test.tsx
```

---

## Database Schema Reference

```sql
-- purchase_barriers (from migration 007)
purchase_barriers(id, session_id, barrier_name, category, mention_count, participant_ids, verbatim_ids, created_at)
-- category CHECK: 'trust','price','service','financing','resale','other'

-- competitor_mentions (from migration 007)
competitor_mentions(id, session_id, brand_name, sentiment, context, verbatim_id, participant_id, created_at)
-- sentiment uses sentiment_enum: 'positive','neutral','negative'

-- verbatims: id, session_id, participant_id, text, start_ts, end_ts, topic, sentiment, sentiment_score
-- sessions: id, day_id, study_id, name, status, mg_model, created_at
-- days: id, study_id, name, date
-- studies: id, name, tenant_id, created_at
```

---

### Task 1: Dashboard Types and Feature Flag Extension

**Files:**
- Create: `src/types/dashboard.ts`
- Modify: `src/config/tenant-schema.ts` (add `compareSessions`, `rawVerbatims` to featuresSchema)
- Modify: `src/config/_default.json` (add the two new feature flags)
- Test: `tests/unit/dashboard/dashboard-types.test.ts`

- [ ] **Step 1: Write type compilation test**

```typescript
// tests/unit/dashboard/dashboard-types.test.ts
import { describe, it, expect } from 'vitest'
import type {
  SentimentSummary,
  HeatmapCell,
  BarrierAggregate,
  CompetitorAggregate,
  TrendPoint,
  SessionSummary,
  DashboardFilters,
} from '@/types/dashboard'

describe('dashboard types', () => {
  it('SentimentSummary is constructable', () => {
    const s: SentimentSummary = { positive: 10, neutral: 5, negative: 3, total: 18 }
    expect(s.total).toBe(18)
  })

  it('HeatmapCell is constructable', () => {
    const c: HeatmapCell = { topic: 'safety', positive: 4, neutral: 2, negative: 1, total: 7 }
    expect(c.topic).toBe('safety')
  })

  it('BarrierAggregate is constructable', () => {
    const b: BarrierAggregate = { barrierName: 'price', category: 'price', mentionCount: 5 }
    expect(b.mentionCount).toBe(5)
  })

  it('CompetitorAggregate is constructable', () => {
    const c: CompetitorAggregate = { brandName: 'Toyota', positive: 2, neutral: 1, negative: 3, total: 6 }
    expect(c.total).toBe(6)
  })

  it('TrendPoint is constructable', () => {
    const t: TrendPoint = { date: '2026-03-01', sessionName: 'S1', topic: 'safety', avgSentiment: 0.7, count: 10 }
    expect(t.avgSentiment).toBe(0.7)
  })

  it('SessionSummary is constructable', () => {
    const s: SessionSummary = {
      id: '1', name: 'Session 1', mgModel: 'MG4', date: '2026-03-01',
      status: 'ready', participantCount: 8, verbatimCount: 50, sentimentAvg: 0.65,
    }
    expect(s.participantCount).toBe(8)
  })

  it('DashboardFilters is constructable', () => {
    const f: DashboardFilters = { studyId: null, dayId: null, topics: [], dateFrom: null, dateTo: null }
    expect(f.topics).toHaveLength(0)
  })
})
```

- [ ] **Step 2: Run test — expect FAIL (types don't exist)**

```bash
npx vitest run tests/unit/dashboard/dashboard-types.test.ts
```

Expected: FAIL — `Cannot find module '@/types/dashboard'`

- [ ] **Step 3: Create dashboard types**

```typescript
// src/types/dashboard.ts

export interface SentimentSummary {
  positive: number
  neutral: number
  negative: number
  total: number
}

export interface HeatmapCell {
  topic: string
  positive: number
  neutral: number
  negative: number
  total: number
}

export interface BarrierAggregate {
  barrierName: string
  category: string
  mentionCount: number
}

export interface CompetitorAggregate {
  brandName: string
  positive: number
  neutral: number
  negative: number
  total: number
}

export interface TrendPoint {
  date: string
  sessionName: string
  topic: string
  avgSentiment: number
  count: number
}

export interface SessionSummary {
  id: string
  name: string
  mgModel: string | null
  date: string
  status: string
  participantCount: number
  verbatimCount: number
  sentimentAvg: number | null
}

export interface DashboardFilters {
  studyId: string | null
  dayId: string | null
  topics: string[]
  dateFrom: string | null
  dateTo: string | null
}
```

- [ ] **Step 4: Extend feature flags in tenant schema**

In `src/config/tenant-schema.ts`, add to `featuresSchema`:
```typescript
compareSessions: z.boolean().default(true),
rawVerbatims: z.boolean().default(true),
```

In `src/config/_default.json`, add to `features`:
```json
"compareSessions": true,
"rawVerbatims": true
```

- [ ] **Step 5: Run test — expect PASS**

```bash
npx vitest run tests/unit/dashboard/dashboard-types.test.ts
```

- [ ] **Step 6: Commit**

```bash
git add src/types/dashboard.ts src/config/tenant-schema.ts src/config/_default.json tests/unit/dashboard/dashboard-types.test.ts
git commit -m "feat: add dashboard types and extend tenant feature flags"
```

---

### Task 2: Shared Filter Helper

**Files:**
- Create: `src/lib/dashboard/filters.ts`
- Test: `tests/unit/dashboard/filters-helper.test.ts`

- [ ] **Step 1: Write tests for parseDashboardParams**

```typescript
// tests/unit/dashboard/filters-helper.test.ts
import { describe, it, expect } from 'vitest'
import { parseDashboardParams } from '@/lib/dashboard/filters'

describe('parseDashboardParams', () => {
  it('parses all params from URL', () => {
    const url = new URL('http://localhost/api/dashboard/x?study_id=s1&day_id=d1&topics=safety,pricing&date_from=2026-01-01&date_to=2026-03-01')
    const filters = parseDashboardParams(url)
    expect(filters.studyId).toBe('s1')
    expect(filters.dayId).toBe('d1')
    expect(filters.topics).toEqual(['safety', 'pricing'])
    expect(filters.dateFrom).toBe('2026-01-01')
    expect(filters.dateTo).toBe('2026-03-01')
  })

  it('returns nulls and empty array for missing params', () => {
    const url = new URL('http://localhost/api/dashboard/x')
    const filters = parseDashboardParams(url)
    expect(filters.studyId).toBeNull()
    expect(filters.dayId).toBeNull()
    expect(filters.topics).toEqual([])
    expect(filters.dateFrom).toBeNull()
    expect(filters.dateTo).toBeNull()
  })

  it('handles single topic without comma', () => {
    const url = new URL('http://localhost/api/dashboard/x?topics=safety')
    const filters = parseDashboardParams(url)
    expect(filters.topics).toEqual(['safety'])
  })

  it('ignores empty topics string', () => {
    const url = new URL('http://localhost/api/dashboard/x?topics=')
    const filters = parseDashboardParams(url)
    expect(filters.topics).toEqual([])
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
npx vitest run tests/unit/dashboard/filters-helper.test.ts
```

- [ ] **Step 3: Implement parseDashboardParams**

```typescript
// src/lib/dashboard/filters.ts
import type { DashboardFilters } from '@/types/dashboard'

export function parseDashboardParams(url: URL): DashboardFilters {
  const studyId = url.searchParams.get('study_id') || null
  const dayId = url.searchParams.get('day_id') || null
  const topicsRaw = url.searchParams.get('topics') || ''
  const topics = topicsRaw ? topicsRaw.split(',').filter(Boolean) : []
  const dateFrom = url.searchParams.get('date_from') || null
  const dateTo = url.searchParams.get('date_to') || null

  return { studyId, dayId, topics, dateFrom, dateTo }
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
npx vitest run tests/unit/dashboard/filters-helper.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add src/lib/dashboard/filters.ts tests/unit/dashboard/filters-helper.test.ts
git commit -m "feat: add shared dashboard filter parser"
```

---

### Task 3: Sessions API Route

**Files:**
- Create: `src/app/api/dashboard/sessions/route.ts`
- Test: `tests/unit/dashboard/sessions-route.test.ts`

- [ ] **Step 1: Write test**

```typescript
// tests/unit/dashboard/sessions-route.test.ts
import { describe, it, expect, vi } from 'vitest'

const mockData = [
  {
    id: 's1',
    name: 'Session 1',
    mg_model: 'MG4',
    status: 'ready',
    days: { date: '2026-03-15' },
    participants: [{ count: 8 }],
    verbatims: [{ count: 45 }],
  },
]

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: {
      getUser: vi.fn().mockResolvedValue({
        data: { user: { id: 'u1', app_metadata: { role: 'mg_client' } } },
        error: null,
      }),
    },
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          eq: vi.fn().mockResolvedValue({ data: mockData, error: null }),
        }),
      }),
    }),
  }),
}))

import { GET } from '@/app/api/dashboard/sessions/route'

describe('GET /api/dashboard/sessions', () => {
  it('returns session summaries', async () => {
    const req = new Request('http://localhost/api/dashboard/sessions?study_id=st1')
    const res = await GET(req)
    expect(res.status).toBe(200)
    const json = await res.json()
    expect(json.sessions).toBeDefined()
    expect(Array.isArray(json.sessions)).toBe(true)
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
npx vitest run tests/unit/dashboard/sessions-route.test.ts
```

- [ ] **Step 3: Implement sessions route**

```typescript
// src/app/api/dashboard/sessions/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { parseDashboardParams } from '@/lib/dashboard/filters'
import type { SessionSummary } from '@/types/dashboard'

export async function GET(req: NextRequest) {
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const filters = parseDashboardParams(new URL(req.url))

  let query = supabase
    .from('sessions')
    .select('id, name, mg_model, status, days(date), participants(count), verbatims(count)')

  if (filters.studyId) {
    query = query.eq('study_id', filters.studyId)
  }
  if (filters.dayId) {
    query = query.eq('day_id', filters.dayId)
  }

  // mg_client defense-in-depth: only show ready sessions
  const role = user.app_metadata?.role
  if (role === 'mg_client') {
    query = query.eq('status', 'ready')
  }

  const { data, error } = await query

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  const sessions: SessionSummary[] = (data ?? []).map((row: Record<string, unknown>) => ({
    id: row.id as string,
    name: row.name as string,
    mgModel: (row.mg_model as string) ?? null,
    date: (row.days as unknown as { date: string } | null)?.date ?? '',
    status: row.status as string,
    participantCount: ((row.participants as unknown as Array<{ count: number }>) ?? [])[0]?.count ?? 0,
    verbatimCount: ((row.verbatims as unknown as Array<{ count: number }>) ?? [])[0]?.count ?? 0,
    sentimentAvg: null, // computed client-side or via separate query
  }))

  return NextResponse.json({ sessions })
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
npx vitest run tests/unit/dashboard/sessions-route.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add src/app/api/dashboard/sessions/route.ts tests/unit/dashboard/sessions-route.test.ts
git commit -m "feat: add dashboard sessions API route"
```

---

### Task 4: Sentiment Summary API Route

**Files:**
- Create: `src/app/api/dashboard/sentiment-summary/route.ts`
- Test: `tests/unit/dashboard/sentiment-summary-route.test.ts`

- [ ] **Step 1: Write test**

```typescript
// tests/unit/dashboard/sentiment-summary-route.test.ts
import { describe, it, expect, vi } from 'vitest'

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: {
      getUser: vi.fn().mockResolvedValue({
        data: { user: { id: 'u1', app_metadata: { role: 'mg_client' } } },
        error: null,
      }),
    },
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          in: vi.fn().mockResolvedValue({
            data: [
              { sentiment: 'positive' },
              { sentiment: 'positive' },
              { sentiment: 'neutral' },
              { sentiment: 'negative' },
            ],
            error: null,
          }),
        }),
      }),
    }),
  }),
}))

import { GET } from '@/app/api/dashboard/sentiment-summary/route'

describe('GET /api/dashboard/sentiment-summary', () => {
  it('returns aggregated sentiment counts', async () => {
    const req = new Request('http://localhost/api/dashboard/sentiment-summary?study_id=st1')
    const res = await GET(req)
    expect(res.status).toBe(200)
    const json = await res.json()
    expect(json.summary.positive).toBe(2)
    expect(json.summary.neutral).toBe(1)
    expect(json.summary.negative).toBe(1)
    expect(json.summary.total).toBe(4)
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

- [ ] **Step 3: Implement sentiment-summary route**

The route fetches verbatims with `sentiment` column only, applies filters, and aggregates in JS:

```typescript
// src/app/api/dashboard/sentiment-summary/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { parseDashboardParams } from '@/lib/dashboard/filters'
import type { SentimentSummary } from '@/types/dashboard'

export function aggregateSentiment(rows: Array<{ sentiment: string }>): SentimentSummary {
  const summary: SentimentSummary = { positive: 0, neutral: 0, negative: 0, total: 0 }
  for (const row of rows) {
    if (row.sentiment === 'positive') summary.positive++
    else if (row.sentiment === 'neutral') summary.neutral++
    else if (row.sentiment === 'negative') summary.negative++
    summary.total++
  }
  return summary
}

export async function GET(req: NextRequest) {
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const filters = parseDashboardParams(new URL(req.url))

  let query = supabase.from('verbatims').select('sentiment')

  if (filters.studyId) {
    query = query.eq('session_id', filters.studyId) // will need join logic
  }
  if (filters.topics.length > 0) {
    query = query.in('topic', filters.topics)
  }

  const { data, error } = await query

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  const summary = aggregateSentiment(data ?? [])
  return NextResponse.json({ summary })
}
```

**Note:** The `aggregateSentiment` function is exported as a pure function for direct unit testing. The study_id filter needs to join through sessions — the implementer should use a subquery or filter sessions first, then use `.in('session_id', sessionIds)`.

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/app/api/dashboard/sentiment-summary/route.ts tests/unit/dashboard/sentiment-summary-route.test.ts
git commit -m "feat: add sentiment summary API route with aggregation"
```

---

### Task 5: Sentiment Heatmap API Route

**Files:**
- Create: `src/app/api/dashboard/sentiment-heatmap/route.ts`
- Test: `tests/unit/dashboard/sentiment-heatmap-route.test.ts`

- [ ] **Step 1: Write test**

```typescript
// tests/unit/dashboard/sentiment-heatmap-route.test.ts
import { describe, it, expect, vi } from 'vitest'

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: {
      getUser: vi.fn().mockResolvedValue({
        data: { user: { id: 'u1', app_metadata: { role: 'wav_admin' } } },
        error: null,
      }),
    },
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockResolvedValue({
        data: [
          { topic: 'safety', sentiment: 'positive' },
          { topic: 'safety', sentiment: 'positive' },
          { topic: 'safety', sentiment: 'negative' },
          { topic: 'pricing', sentiment: 'neutral' },
          { topic: 'pricing', sentiment: 'negative' },
        ],
        error: null,
      }),
    }),
  }),
}))

import { GET } from '@/app/api/dashboard/sentiment-heatmap/route'

describe('GET /api/dashboard/sentiment-heatmap', () => {
  it('returns heatmap cells grouped by topic', async () => {
    const req = new Request('http://localhost/api/dashboard/sentiment-heatmap')
    const res = await GET(req)
    expect(res.status).toBe(200)
    const json = await res.json()
    expect(json.heatmap).toHaveLength(2)
    const safety = json.heatmap.find((c: { topic: string }) => c.topic === 'safety')
    expect(safety.positive).toBe(2)
    expect(safety.negative).toBe(1)
    const pricing = json.heatmap.find((c: { topic: string }) => c.topic === 'pricing')
    expect(pricing.neutral).toBe(1)
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

- [ ] **Step 3: Implement heatmap route**

Export a pure `buildHeatmap(rows)` function that groups `{ topic, sentiment }[]` into `HeatmapCell[]`. Route handler fetches `topic, sentiment` from verbatims, applies filters, calls `buildHeatmap`.

```typescript
// src/app/api/dashboard/sentiment-heatmap/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { parseDashboardParams } from '@/lib/dashboard/filters'
import type { HeatmapCell } from '@/types/dashboard'

export function buildHeatmap(rows: Array<{ topic: string; sentiment: string }>): HeatmapCell[] {
  const map = new Map<string, HeatmapCell>()
  for (const row of rows) {
    const cell = map.get(row.topic) ?? { topic: row.topic, positive: 0, neutral: 0, negative: 0, total: 0 }
    if (row.sentiment === 'positive') cell.positive++
    else if (row.sentiment === 'neutral') cell.neutral++
    else if (row.sentiment === 'negative') cell.negative++
    cell.total++
    map.set(row.topic, cell)
  }
  return Array.from(map.values())
}

export async function GET(req: NextRequest) {
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const filters = parseDashboardParams(new URL(req.url))
  let query = supabase.from('verbatims').select('topic, sentiment')

  if (filters.topics.length > 0) {
    query = query.in('topic', filters.topics)
  }
  // Add study/day filters via session join as needed

  const { data, error } = await query
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  const heatmap = buildHeatmap(data ?? [])
  return NextResponse.json({ heatmap })
}
```

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/app/api/dashboard/sentiment-heatmap/route.ts tests/unit/dashboard/sentiment-heatmap-route.test.ts
git commit -m "feat: add sentiment heatmap API route"
```

---

### Task 6: Barriers API Route

**Files:**
- Create: `src/app/api/dashboard/barriers/route.ts`
- Test: `tests/unit/dashboard/barriers-route.test.ts`

- [ ] **Step 1: Write test**

```typescript
// tests/unit/dashboard/barriers-route.test.ts
import { describe, it, expect, vi } from 'vitest'

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: {
      getUser: vi.fn().mockResolvedValue({
        data: { user: { id: 'u1', app_metadata: { role: 'mg_client' } } },
        error: null,
      }),
    },
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockResolvedValue({
        data: [
          { barrier_name: 'Alto precio base', category: 'price', mention_count: 5, session_id: 's1' },
          { barrier_name: 'Red de servicio limitada', category: 'service', mention_count: 3, session_id: 's1' },
          { barrier_name: 'Precio de repuestos', category: 'price', mention_count: 2, session_id: 's2' },
        ],
        error: null,
      }),
    }),
  }),
}))

import { GET } from '@/app/api/dashboard/barriers/route'

describe('GET /api/dashboard/barriers', () => {
  it('aggregates barriers by category', async () => {
    const req = new Request('http://localhost/api/dashboard/barriers')
    const res = await GET(req)
    expect(res.status).toBe(200)
    const json = await res.json()
    expect(json.barriers).toBeDefined()
    // price category: 2 entries, total mentions = 7
    const price = json.barriers.find((b: { category: string }) => b.category === 'price')
    expect(price.totalMentions).toBe(7)
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

- [ ] **Step 3: Implement barriers route**

Export a pure `aggregateBarriers(rows)` function that groups by `category`, sums `mention_count`.

```typescript
// src/app/api/dashboard/barriers/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { parseDashboardParams } from '@/lib/dashboard/filters'

interface BarrierRow {
  barrier_name: string
  category: string
  mention_count: number
  session_id: string
}

export interface BarrierCategoryAggregate {
  category: string
  barriers: Array<{ barrierName: string; mentionCount: number }>
  totalMentions: number
}

export function aggregateBarriers(rows: BarrierRow[]): BarrierCategoryAggregate[] {
  const map = new Map<string, BarrierCategoryAggregate>()
  for (const row of rows) {
    const agg = map.get(row.category) ?? { category: row.category, barriers: [], totalMentions: 0 }
    agg.barriers.push({ barrierName: row.barrier_name, mentionCount: row.mention_count })
    agg.totalMentions += row.mention_count
    map.set(row.category, agg)
  }
  return Array.from(map.values()).sort((a, b) => b.totalMentions - a.totalMentions)
}

export async function GET(req: NextRequest) {
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const filters = parseDashboardParams(new URL(req.url))
  let query = supabase.from('purchase_barriers').select('barrier_name, category, mention_count, session_id')

  // Filter by study via session join if needed

  const { data, error } = await query
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  const barriers = aggregateBarriers(data ?? [])
  return NextResponse.json({ barriers })
}
```

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/app/api/dashboard/barriers/route.ts tests/unit/dashboard/barriers-route.test.ts
git commit -m "feat: add purchase barriers API route"
```

---

### Task 7: Competitors API Route

**Files:**
- Create: `src/app/api/dashboard/competitors/route.ts`
- Test: `tests/unit/dashboard/competitors-route.test.ts`

- [ ] **Step 1: Write test**

```typescript
// tests/unit/dashboard/competitors-route.test.ts
import { describe, it, expect, vi } from 'vitest'

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: {
      getUser: vi.fn().mockResolvedValue({
        data: { user: { id: 'u1', app_metadata: { role: 'mg_client' } } },
        error: null,
      }),
    },
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockResolvedValue({
        data: [
          { brand_name: 'Toyota', sentiment: 'positive' },
          { brand_name: 'Toyota', sentiment: 'negative' },
          { brand_name: 'BYD', sentiment: 'neutral' },
          { brand_name: 'BYD', sentiment: 'positive' },
          { brand_name: 'Toyota', sentiment: 'neutral' },
        ],
        error: null,
      }),
    }),
  }),
}))

import { GET } from '@/app/api/dashboard/competitors/route'

describe('GET /api/dashboard/competitors', () => {
  it('aggregates competitor mentions with sentiment breakdown', async () => {
    const req = new Request('http://localhost/api/dashboard/competitors')
    const res = await GET(req)
    expect(res.status).toBe(200)
    const json = await res.json()
    expect(json.competitors).toHaveLength(2)
    const toyota = json.competitors.find((c: { brandName: string }) => c.brandName === 'Toyota')
    expect(toyota.positive).toBe(1)
    expect(toyota.negative).toBe(1)
    expect(toyota.neutral).toBe(1)
    expect(toyota.total).toBe(3)
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

- [ ] **Step 3: Implement competitors route**

Export a pure `aggregateCompetitors(rows)` function. Pattern identical to heatmap but grouping by `brand_name`.

```typescript
// src/app/api/dashboard/competitors/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { parseDashboardParams } from '@/lib/dashboard/filters'
import type { CompetitorAggregate } from '@/types/dashboard'

export function aggregateCompetitors(rows: Array<{ brand_name: string; sentiment: string }>): CompetitorAggregate[] {
  const map = new Map<string, CompetitorAggregate>()
  for (const row of rows) {
    const agg = map.get(row.brand_name) ?? { brandName: row.brand_name, positive: 0, neutral: 0, negative: 0, total: 0 }
    if (row.sentiment === 'positive') agg.positive++
    else if (row.sentiment === 'neutral') agg.neutral++
    else if (row.sentiment === 'negative') agg.negative++
    agg.total++
    map.set(row.brand_name, agg)
  }
  return Array.from(map.values()).sort((a, b) => b.total - a.total)
}

export async function GET(req: NextRequest) {
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const filters = parseDashboardParams(new URL(req.url))
  const query = supabase.from('competitor_mentions').select('brand_name, sentiment')

  const { data, error } = await query
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  const competitors = aggregateCompetitors(data ?? [])
  return NextResponse.json({ competitors })
}
```

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/app/api/dashboard/competitors/route.ts tests/unit/dashboard/competitors-route.test.ts
git commit -m "feat: add competitor mentions API route"
```

---

### Task 8: Trends API Route

**Files:**
- Create: `src/app/api/dashboard/trends/route.ts`
- Test: `tests/unit/dashboard/trends-route.test.ts`

- [ ] **Step 1: Write test**

```typescript
// tests/unit/dashboard/trends-route.test.ts
import { describe, it, expect, vi } from 'vitest'

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: {
      getUser: vi.fn().mockResolvedValue({
        data: { user: { id: 'u1', app_metadata: { role: 'wav_admin' } } },
        error: null,
      }),
    },
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockReturnValue({
        order: vi.fn().mockResolvedValue({
          data: [
            { topic: 'safety', sentiment_score: 0.8, sessions: { name: 'S1', days: { date: '2026-03-01' } } },
            { topic: 'safety', sentiment_score: 0.6, sessions: { name: 'S1', days: { date: '2026-03-01' } } },
            { topic: 'pricing', sentiment_score: -0.3, sessions: { name: 'S2', days: { date: '2026-03-08' } } },
          ],
          error: null,
        }),
      }),
    }),
  }),
}))

import { GET } from '@/app/api/dashboard/trends/route'

describe('GET /api/dashboard/trends', () => {
  it('returns trend points grouped by date and topic', async () => {
    const req = new Request('http://localhost/api/dashboard/trends')
    const res = await GET(req)
    expect(res.status).toBe(200)
    const json = await res.json()
    expect(json.trends.length).toBeGreaterThanOrEqual(2)
    const safetyPoint = json.trends.find((t: { topic: string; date: string }) => t.topic === 'safety' && t.date === '2026-03-01')
    expect(safetyPoint.avgSentiment).toBeCloseTo(0.7)
    expect(safetyPoint.count).toBe(2)
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

- [ ] **Step 3: Implement trends route**

Export a pure `buildTrends(rows)` function that groups by `(date, topic)`, computes average `sentiment_score`.

```typescript
// src/app/api/dashboard/trends/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { parseDashboardParams } from '@/lib/dashboard/filters'
import type { TrendPoint } from '@/types/dashboard'

interface TrendRow {
  topic: string
  sentiment_score: number
  sessions: { name: string; days: { date: string } }
}

export function buildTrends(rows: TrendRow[]): TrendPoint[] {
  const map = new Map<string, { total: number; count: number; sessionName: string }>()
  for (const row of rows) {
    const date = (row.sessions as unknown as { days: { date: string } })?.days?.date ?? ''
    const key = `${date}|${row.topic}`
    const entry = map.get(key) ?? { total: 0, count: 0, sessionName: (row.sessions as unknown as { name: string })?.name ?? '' }
    entry.total += row.sentiment_score
    entry.count++
    map.set(key, entry)
  }

  const trends: TrendPoint[] = []
  for (const [key, entry] of map) {
    const [date, topic] = key.split('|')
    trends.push({
      date,
      sessionName: entry.sessionName,
      topic,
      avgSentiment: entry.total / entry.count,
      count: entry.count,
    })
  }
  return trends.sort((a, b) => a.date.localeCompare(b.date))
}

export async function GET(req: NextRequest) {
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const filters = parseDashboardParams(new URL(req.url))
  let query = supabase
    .from('verbatims')
    .select('topic, sentiment_score, sessions(name, days(date))')

  if (filters.topics.length > 0) {
    query = query.in('topic', filters.topics)
  }

  const { data, error } = await query.order('start_ts')
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  const trends = buildTrends((data ?? []) as unknown as TrendRow[])
  return NextResponse.json({ trends })
}
```

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/app/api/dashboard/trends/route.ts tests/unit/dashboard/trends-route.test.ts
git commit -m "feat: add sentiment trends API route"
```

---

### Task 9: Dashboard Locale Labels

**Files:**
- Modify: `src/config/locales/es-CL.json`
- Modify: `src/config/locales/en-US.json`

- [ ] **Step 1: Add Spanish labels**

Add the following keys to `src/config/locales/es-CL.json`:

```json
"dashboard.widget.sentiment_summary": "Resumen de Sentimiento",
"dashboard.widget.sentiment_heatmap": "Mapa de Calor por Tema",
"dashboard.widget.purchase_barriers": "Barreras de Compra",
"dashboard.widget.competitor_mentions": "Menciones de Competidores",
"dashboard.widget.sentiment_trends": "Tendencias de Sentimiento",
"dashboard.widget.sessions_overview": "Sesiones",
"dashboard.sentiment.positive": "Positivo",
"dashboard.sentiment.neutral": "Neutro",
"dashboard.sentiment.negative": "Negativo",
"dashboard.filter.study": "Estudio",
"dashboard.filter.day": "Día",
"dashboard.filter.topics": "Temas",
"dashboard.filter.date_from": "Desde",
"dashboard.filter.date_to": "Hasta",
"dashboard.filter.all_studies": "Todos los estudios",
"dashboard.filter.all_days": "Todos los días",
"dashboard.participants_count": "participantes",
"dashboard.verbatims_count": "verbatims",
"dashboard.no_data": "Sin datos disponibles",
"dashboard.loading": "Cargando datos…"
```

- [ ] **Step 2: Add English labels**

Add equivalent keys to `src/config/locales/en-US.json`.

- [ ] **Step 3: Commit**

```bash
git add src/config/locales/es-CL.json src/config/locales/en-US.json
git commit -m "feat: add dashboard locale labels (es-CL, en-US)"
```

---

### Task 10: SentimentHero Widget

**Files:**
- Create: `src/components/dashboard/sentiment-hero.tsx`
- Test: `tests/unit/dashboard/sentiment-hero.test.tsx`

- [ ] **Step 1: Write test**

```typescript
// tests/unit/dashboard/sentiment-hero.test.tsx
import { describe, it, expect } from 'vitest'
import { computePercentage } from '@/components/dashboard/sentiment-hero'

describe('computePercentage', () => {
  it('returns correct percentage', () => {
    expect(computePercentage(7, 10)).toBe(70)
  })

  it('returns 0 when total is 0', () => {
    expect(computePercentage(5, 0)).toBe(0)
  })

  it('rounds to nearest integer', () => {
    expect(computePercentage(1, 3)).toBe(33)
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

- [ ] **Step 3: Implement SentimentHero**

```typescript
// src/components/dashboard/sentiment-hero.tsx
'use client'

import { Card, CardContent } from '@/components/ui/card'
import type { SentimentSummary } from '@/types/dashboard'

export function computePercentage(count: number, total: number): number {
  if (total === 0) return 0
  return Math.round((count / total) * 100)
}

interface SentimentHeroProps {
  summary: SentimentSummary
  label: (key: string) => string
}

const sentimentConfig = [
  { key: 'positive' as const, labelKey: 'dashboard.sentiment.positive', color: 'text-emerald-400', bg: 'bg-emerald-400/10' },
  { key: 'neutral' as const, labelKey: 'dashboard.sentiment.neutral', color: 'text-amber-400', bg: 'bg-amber-400/10' },
  { key: 'negative' as const, labelKey: 'dashboard.sentiment.negative', color: 'text-red-400', bg: 'bg-red-400/10' },
]

export function SentimentHero({ summary, label }: SentimentHeroProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {sentimentConfig.map(({ key, labelKey, color, bg }) => (
        <Card key={key} className={bg}>
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">{label(labelKey)}</p>
            <p className={`text-4xl font-bold mt-1 ${color}`}>
              {computePercentage(summary[key], summary.total)}%
            </p>
            <p className="text-sm text-muted-foreground mt-1">{summary[key]} / {summary.total}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/components/dashboard/sentiment-hero.tsx tests/unit/dashboard/sentiment-hero.test.tsx
git commit -m "feat: add SentimentHero KPI widget"
```

---

### Task 11: SentimentHeatmap Widget

**Files:**
- Create: `src/components/dashboard/sentiment-heatmap.tsx`

- [ ] **Step 1: Implement heatmap widget**

A CSS grid with rows = topics, columns = positive/neutral/negative. Cell opacity proportional to count. Uses `TOPIC_COLORS` for row label accent.

```typescript
// src/components/dashboard/sentiment-heatmap.tsx
'use client'

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { TOPIC_COLORS } from '@/types/player'
import type { HeatmapCell } from '@/types/dashboard'

interface SentimentHeatmapProps {
  heatmap: HeatmapCell[]
  label: (key: string) => string
}

function cellOpacity(count: number, max: number): number {
  if (max === 0) return 0.1
  return Math.max(0.1, count / max)
}

export function SentimentHeatmap({ heatmap, label }: SentimentHeatmapProps) {
  const maxCount = Math.max(...heatmap.flatMap(c => [c.positive, c.neutral, c.negative]), 1)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{label('dashboard.widget.sentiment_heatmap')}</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Header row */}
        <div className="grid grid-cols-[1fr_80px_80px_80px] gap-1 mb-2">
          <div />
          <div className="text-xs text-center text-muted-foreground">{label('dashboard.sentiment.positive')}</div>
          <div className="text-xs text-center text-muted-foreground">{label('dashboard.sentiment.neutral')}</div>
          <div className="text-xs text-center text-muted-foreground">{label('dashboard.sentiment.negative')}</div>
        </div>
        {/* Data rows */}
        {heatmap.map((cell) => (
          <div key={cell.topic} className="grid grid-cols-[1fr_80px_80px_80px] gap-1 mb-1">
            <div className="flex items-center gap-2 text-xs text-foreground">
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: TOPIC_COLORS[cell.topic] ?? '#6b7280' }}
              />
              {cell.topic.replace(/_/g, ' ')}
            </div>
            <div
              className="rounded text-center text-xs py-1"
              style={{ backgroundColor: `rgba(52, 211, 153, ${cellOpacity(cell.positive, maxCount)})` }}
            >
              {cell.positive}
            </div>
            <div
              className="rounded text-center text-xs py-1"
              style={{ backgroundColor: `rgba(251, 191, 36, ${cellOpacity(cell.neutral, maxCount)})` }}
            >
              {cell.neutral}
            </div>
            <div
              className="rounded text-center text-xs py-1"
              style={{ backgroundColor: `rgba(248, 113, 113, ${cellOpacity(cell.negative, maxCount)})` }}
            >
              {cell.negative}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/dashboard/sentiment-heatmap.tsx
git commit -m "feat: add SentimentHeatmap grid widget"
```

---

### Task 12: PurchaseBarriers Widget

**Files:**
- Create: `src/components/dashboard/purchase-barriers.tsx`

- [ ] **Step 1: Implement barriers widget**

Horizontal bar chart using recharts `BarChart` with `layout="vertical"`. Bars colored by category.

```typescript
// src/components/dashboard/purchase-barriers.tsx
'use client'

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface BarrierCategoryAggregate {
  category: string
  totalMentions: number
}

interface PurchaseBarriersProps {
  barriers: BarrierCategoryAggregate[]
  label: (key: string) => string
}

const CATEGORY_COLORS: Record<string, string> = {
  trust: '#8b5cf6',
  price: '#ef4444',
  service: '#f59e0b',
  financing: '#3b82f6',
  resale: '#10b981',
  other: '#6b7280',
}

export function PurchaseBarriers({ barriers, label }: PurchaseBarriersProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{label('dashboard.widget.purchase_barriers')}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={Math.max(200, barriers.length * 40)}>
          <BarChart data={barriers} layout="vertical" margin={{ left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis type="number" tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }} />
            <YAxis
              type="category"
              dataKey="category"
              tick={{ fill: 'var(--foreground)', fontSize: 12 }}
              width={80}
            />
            <Tooltip
              contentStyle={{ backgroundColor: 'var(--card)', border: '1px solid var(--border)' }}
              labelStyle={{ color: 'var(--foreground)' }}
            />
            <Bar
              dataKey="totalMentions"
              fill="#6366f1"
              radius={[0, 4, 4, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/dashboard/purchase-barriers.tsx
git commit -m "feat: add PurchaseBarriers chart widget"
```

---

### Task 13: CompetitorMentions Widget

**Files:**
- Create: `src/components/dashboard/competitor-mentions.tsx`

- [ ] **Step 1: Implement competitor widget**

Stacked bar chart using recharts. Each bar = a brand, stacked by sentiment.

```typescript
// src/components/dashboard/competitor-mentions.tsx
'use client'

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import type { CompetitorAggregate } from '@/types/dashboard'

interface CompetitorMentionsProps {
  competitors: CompetitorAggregate[]
  label: (key: string) => string
}

export function CompetitorMentions({ competitors, label }: CompetitorMentionsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{label('dashboard.widget.competitor_mentions')}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={competitors}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis dataKey="brandName" tick={{ fill: 'var(--foreground)', fontSize: 12 }} />
            <YAxis tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }} />
            <Tooltip contentStyle={{ backgroundColor: 'var(--card)', border: '1px solid var(--border)' }} />
            <Legend />
            <Bar dataKey="positive" stackId="sentiment" fill="#34d399" name={label('dashboard.sentiment.positive')} />
            <Bar dataKey="neutral" stackId="sentiment" fill="#fbbf24" name={label('dashboard.sentiment.neutral')} />
            <Bar dataKey="negative" stackId="sentiment" fill="#f87171" name={label('dashboard.sentiment.negative')} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/dashboard/competitor-mentions.tsx
git commit -m "feat: add CompetitorMentions stacked bar widget"
```

---

### Task 14: SentimentTrends Widget

**Files:**
- Create: `src/components/dashboard/sentiment-trends.tsx`

- [ ] **Step 1: Implement trends widget**

Multi-line chart: X = date, Y = avg sentiment score, one line per topic colored by `TOPIC_COLORS`.

```typescript
// src/components/dashboard/sentiment-trends.tsx
'use client'

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { TOPIC_COLORS } from '@/types/player'
import type { TrendPoint } from '@/types/dashboard'

interface SentimentTrendsProps {
  trends: TrendPoint[]
  label: (key: string) => string
}

/** Transform TrendPoint[] to recharts-friendly: [{ date, safety: 0.7, pricing: -0.3 }, ...] */
export function transformTrendsForChart(trends: TrendPoint[]): { data: Array<Record<string, unknown>>; topics: string[] } {
  const dateMap = new Map<string, Record<string, unknown>>()
  const topicSet = new Set<string>()

  for (const t of trends) {
    topicSet.add(t.topic)
    const entry = dateMap.get(t.date) ?? { date: t.date }
    entry[t.topic] = t.avgSentiment
    dateMap.set(t.date, entry)
  }

  return {
    data: Array.from(dateMap.values()).sort((a, b) => (a.date as string).localeCompare(b.date as string)),
    topics: Array.from(topicSet),
  }
}

export function SentimentTrends({ trends, label }: SentimentTrendsProps) {
  const { data, topics } = transformTrendsForChart(trends)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{label('dashboard.widget.sentiment_trends')}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis dataKey="date" tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }} />
            <YAxis domain={[-1, 1]} tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }} />
            <Tooltip contentStyle={{ backgroundColor: 'var(--card)', border: '1px solid var(--border)' }} />
            <Legend />
            {topics.map((topic) => (
              <Line
                key={topic}
                type="monotone"
                dataKey={topic}
                stroke={TOPIC_COLORS[topic] ?? '#6b7280'}
                strokeWidth={2}
                dot={{ r: 3 }}
                name={topic.replace(/_/g, ' ')}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/dashboard/sentiment-trends.tsx
git commit -m "feat: add SentimentTrends line chart widget"
```

---

### Task 15: SessionCards Widget

**Files:**
- Create: `src/components/dashboard/session-cards.tsx`
- Test: `tests/unit/dashboard/session-cards.test.tsx`

- [ ] **Step 1: Write test**

```typescript
// tests/unit/dashboard/session-cards.test.tsx
import { describe, it, expect } from 'vitest'
import { sentimentColor } from '@/components/dashboard/session-cards'

describe('sentimentColor', () => {
  it('returns emerald for positive sentiment', () => {
    expect(sentimentColor(0.6)).toBe('bg-emerald-400')
  })

  it('returns amber for neutral sentiment', () => {
    expect(sentimentColor(0.1)).toBe('bg-amber-400')
  })

  it('returns red for negative sentiment', () => {
    expect(sentimentColor(-0.3)).toBe('bg-red-400')
  })

  it('returns zinc for null sentiment', () => {
    expect(sentimentColor(null)).toBe('bg-zinc-500')
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

- [ ] **Step 3: Implement SessionCards**

```typescript
// src/components/dashboard/session-cards.tsx
'use client'

import Link from 'next/link'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { SessionSummary } from '@/types/dashboard'

export function sentimentColor(avg: number | null): string {
  if (avg == null) return 'bg-zinc-500'
  if (avg >= 0.3) return 'bg-emerald-400'
  if (avg >= -0.3) return 'bg-amber-400'
  return 'bg-red-400'
}

interface SessionCardsProps {
  sessions: SessionSummary[]
  label: (key: string) => string
}

export function SessionCards({ sessions, label }: SessionCardsProps) {
  if (sessions.length === 0) {
    return <p className="text-sm text-muted-foreground">{label('dashboard.no_data')}</p>
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
      {sessions.map((s) => (
        <Link key={s.id} href={`/sessions/${s.id}`}>
          <Card className="hover:border-primary/40 transition-colors cursor-pointer">
            <CardContent className="pt-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-medium text-sm text-foreground">{s.name}</p>
                  {s.mgModel && <Badge variant="secondary" className="mt-1 text-xs">{s.mgModel}</Badge>}
                </div>
                <span className={`w-2.5 h-2.5 rounded-full shrink-0 mt-1 ${sentimentColor(s.sentimentAvg)}`} />
              </div>
              <div className="flex gap-4 mt-3 text-xs text-muted-foreground">
                <span>{s.participantCount} {label('dashboard.participants_count')}</span>
                <span>{s.verbatimCount} {label('dashboard.verbatims_count')}</span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">{s.date}</p>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/components/dashboard/session-cards.tsx tests/unit/dashboard/session-cards.test.tsx
git commit -m "feat: add SessionCards clickable grid widget"
```

---

### Task 16: DashboardFilters Component

**Files:**
- Create: `src/components/dashboard/dashboard-filters.tsx`

- [ ] **Step 1: Install missing shadcn components if needed**

```bash
cd /Users/fede/projects/wav-intelligence && npx shadcn@latest add select
```

- [ ] **Step 2: Implement DashboardFilters**

```typescript
// src/components/dashboard/dashboard-filters.tsx
'use client'

import { useCallback } from 'react'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { DashboardFilters } from '@/types/dashboard'

const ALL_TOPICS = [
  'design_exterior', 'design_interior', 'infotainment', 'powertrain',
  'safety', 'pricing', 'brand_image', 'comparison', 'purchase_intent', 'general',
]

interface DashboardFiltersBarProps {
  studies: Array<{ id: string; name: string }>
  days: Array<{ id: string; studyId: string; name: string; date: string }>
  filters: DashboardFilters
  onFiltersChange: (filters: DashboardFilters) => void
  label: (key: string) => string
}

export function DashboardFiltersBar({ studies, days, filters, onFiltersChange, label }: DashboardFiltersBarProps) {
  const filteredDays = filters.studyId
    ? days.filter((d) => d.studyId === filters.studyId)
    : days

  const setField = useCallback(
    <K extends keyof DashboardFilters>(key: K, value: DashboardFilters[K]) => {
      onFiltersChange({ ...filters, [key]: value })
    },
    [filters, onFiltersChange],
  )

  return (
    <div className="flex flex-wrap items-end gap-3 p-4 bg-card border border-border rounded-lg">
      {/* Study */}
      <div className="space-y-1">
        <Label className="text-xs">{label('dashboard.filter.study')}</Label>
        <Select
          value={filters.studyId ?? '_all'}
          onValueChange={(v) => setField('studyId', v === '_all' ? null : v)}
        >
          <SelectTrigger className="w-[180px] h-8 text-xs">
            <SelectValue placeholder={label('dashboard.filter.all_studies')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="_all">{label('dashboard.filter.all_studies')}</SelectItem>
            {studies.map((s) => (
              <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Day */}
      <div className="space-y-1">
        <Label className="text-xs">{label('dashboard.filter.day')}</Label>
        <Select
          value={filters.dayId ?? '_all'}
          onValueChange={(v) => setField('dayId', v === '_all' ? null : v)}
        >
          <SelectTrigger className="w-[180px] h-8 text-xs">
            <SelectValue placeholder={label('dashboard.filter.all_days')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="_all">{label('dashboard.filter.all_days')}</SelectItem>
            {filteredDays.map((d) => (
              <SelectItem key={d.id} value={d.id}>{d.name} ({d.date})</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Date range */}
      <div className="space-y-1">
        <Label className="text-xs">{label('dashboard.filter.date_from')}</Label>
        <Input
          type="date"
          className="w-[140px] h-8 text-xs"
          value={filters.dateFrom ?? ''}
          onChange={(e) => setField('dateFrom', e.target.value || null)}
        />
      </div>
      <div className="space-y-1">
        <Label className="text-xs">{label('dashboard.filter.date_to')}</Label>
        <Input
          type="date"
          className="w-[140px] h-8 text-xs"
          value={filters.dateTo ?? ''}
          onChange={(e) => setField('dateTo', e.target.value || null)}
        />
      </div>
    </div>
  )
}
```

**Note:** Topic multi-select omitted from v1 for simplicity — add in a follow-up task if needed.

- [ ] **Step 3: Commit**

```bash
git add src/components/dashboard/dashboard-filters.tsx
git commit -m "feat: add DashboardFiltersBar component"
```

---

### Task 17: useDashboardData Hook

**Files:**
- Create: `src/hooks/use-dashboard-data.ts`

- [ ] **Step 1: Implement the hook**

```typescript
// src/hooks/use-dashboard-data.ts
'use client'

import { useState, useEffect, useCallback } from 'react'
import type {
  SentimentSummary, HeatmapCell, CompetitorAggregate, TrendPoint, SessionSummary, DashboardFilters,
} from '@/types/dashboard'

interface BarrierCategoryAggregate {
  category: string
  barriers: Array<{ barrierName: string; mentionCount: number }>
  totalMentions: number
}

interface DashboardData {
  summary: SentimentSummary | null
  heatmap: HeatmapCell[]
  barriers: BarrierCategoryAggregate[]
  competitors: CompetitorAggregate[]
  trends: TrendPoint[]
  sessions: SessionSummary[]
  loading: boolean
  error: string | null
}

function buildQuery(filters: DashboardFilters): string {
  const params = new URLSearchParams()
  if (filters.studyId) params.set('study_id', filters.studyId)
  if (filters.dayId) params.set('day_id', filters.dayId)
  if (filters.topics.length > 0) params.set('topics', filters.topics.join(','))
  if (filters.dateFrom) params.set('date_from', filters.dateFrom)
  if (filters.dateTo) params.set('date_to', filters.dateTo)
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

export function useDashboardData(filters: DashboardFilters): DashboardData {
  const [data, setData] = useState<DashboardData>({
    summary: null, heatmap: [], barriers: [], competitors: [], trends: [], sessions: [],
    loading: true, error: null,
  })

  const fetchAll = useCallback(async () => {
    setData((prev) => ({ ...prev, loading: true, error: null }))
    const qs = buildQuery(filters)

    try {
      const [summaryRes, heatmapRes, barriersRes, competitorsRes, trendsRes, sessionsRes] = await Promise.all([
        fetch(`/api/dashboard/sentiment-summary${qs}`),
        fetch(`/api/dashboard/sentiment-heatmap${qs}`),
        fetch(`/api/dashboard/barriers${qs}`),
        fetch(`/api/dashboard/competitors${qs}`),
        fetch(`/api/dashboard/trends${qs}`),
        fetch(`/api/dashboard/sessions${qs}`),
      ])

      const [summaryJson, heatmapJson, barriersJson, competitorsJson, trendsJson, sessionsJson] = await Promise.all([
        summaryRes.json(),
        heatmapRes.json(),
        barriersRes.json(),
        competitorsRes.json(),
        trendsRes.json(),
        sessionsRes.json(),
      ])

      setData({
        summary: summaryJson.summary ?? null,
        heatmap: heatmapJson.heatmap ?? [],
        barriers: barriersJson.barriers ?? [],
        competitors: competitorsJson.competitors ?? [],
        trends: trendsJson.trends ?? [],
        sessions: sessionsJson.sessions ?? [],
        loading: false,
        error: null,
      })
    } catch (err) {
      setData((prev) => ({ ...prev, loading: false, error: (err as Error).message }))
    }
  }, [filters])

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  return data
}
```

- [ ] **Step 2: Commit**

```bash
git add src/hooks/use-dashboard-data.ts
git commit -m "feat: add useDashboardData hook for parallel API fetching"
```

---

### Task 18: MgClientDashboard Integration

**Files:**
- Modify: `src/components/dashboard/mg-client-dashboard.tsx`
- Modify: `src/app/dashboard/page.tsx` (prefetch studies/days)

- [ ] **Step 1: Update dashboard page to prefetch studies and days**

Add to `src/app/dashboard/page.tsx`:

```typescript
// After auth check, before rendering:
const { data: studies } = await supabase
  .from('studies')
  .select('id, name')
  .order('created_at', { ascending: false })

const { data: rawDays } = await supabase
  .from('days')
  .select('id, study_id, name, date')
  .order('date')

const days = (rawDays ?? []).map((d) => ({
  id: d.id,
  studyId: d.study_id,
  name: d.name,
  date: d.date,
}))
```

Pass `studies` and `days` as props to all three dashboard components.

- [ ] **Step 2: Rewrite MgClientDashboard**

Replace entire stub with full dashboard layout using all widgets, the filter bar, and `useDashboardData`:

```typescript
// src/components/dashboard/mg-client-dashboard.tsx
'use client'

import { useState } from 'react'
import type { User } from '@supabase/supabase-js'
import { useTenant } from '@/hooks/use-tenant'
import { useLabel } from '@/hooks/use-label'
import { useFeature } from '@/hooks/use-feature'
import { useDashboardData } from '@/hooks/use-dashboard-data'
import type { DashboardFilters } from '@/types/dashboard'
import { DashboardFiltersBar } from './dashboard-filters'
import { SentimentHero } from './sentiment-hero'
import { SentimentHeatmap } from './sentiment-heatmap'
import { PurchaseBarriers } from './purchase-barriers'
import { CompetitorMentions } from './competitor-mentions'
import { SentimentTrends } from './sentiment-trends'
import { SessionCards } from './session-cards'

interface MgClientDashboardProps {
  user: User
  studies: Array<{ id: string; name: string }>
  days: Array<{ id: string; studyId: string; name: string; date: string }>
}

export function MgClientDashboard({ user, studies, days }: MgClientDashboardProps) {
  const tenant = useTenant()
  const label = useLabel()
  const showTrends = useFeature('trends')

  const [filters, setFilters] = useState<DashboardFilters>({
    studyId: null, dayId: null, topics: [], dateFrom: null, dateTo: null,
  })

  const { summary, heatmap, barriers, competitors, trends, sessions, loading } = useDashboardData(filters)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-foreground">{label('dashboard.title.client')}</h1>
        <p className="text-muted-foreground text-sm mt-1">
          {label('common.welcome')}, {user.email} — {tenant.brand.name}
        </p>
      </div>

      {/* Filters */}
      <DashboardFiltersBar
        studies={studies}
        days={days}
        filters={filters}
        onFiltersChange={setFilters}
        label={label}
      />

      {loading ? (
        <p className="text-sm text-muted-foreground">{label('dashboard.loading')}</p>
      ) : (
        <>
          {/* Sentiment KPIs */}
          {summary && <SentimentHero summary={summary} label={label} />}

          {/* Middle row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
              <SentimentHeatmap heatmap={heatmap} label={label} />
            </div>
            <div>
              <PurchaseBarriers barriers={barriers} label={label} />
            </div>
          </div>

          {/* Charts row */}
          <div className={`grid grid-cols-1 ${showTrends ? 'lg:grid-cols-2' : ''} gap-4`}>
            <CompetitorMentions competitors={competitors} label={label} />
            {showTrends && <SentimentTrends trends={trends} label={label} />}
          </div>

          {/* Sessions */}
          <div>
            <h2 className="text-sm font-medium text-foreground mb-3">{label('dashboard.widget.sessions_overview')}</h2>
            <SessionCards sessions={sessions} label={label} />
          </div>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Verify build compiles**

```bash
cd /Users/fede/projects/wav-intelligence && npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add src/components/dashboard/mg-client-dashboard.tsx src/app/dashboard/page.tsx
git commit -m "feat: integrate MgClientDashboard with all widgets and filters"
```

---

### Task 19: WavAdminDashboard and ModeratorDashboard

**Files:**
- Modify: `src/components/dashboard/wav-admin-dashboard.tsx`
- Modify: `src/components/dashboard/moderator-dashboard.tsx`

- [ ] **Step 1: Rewrite WavAdminDashboard**

Same as MgClientDashboard but with all features enabled and an extra admin KPI row (total sessions, processing count). Accept same `studies`/`days` props.

- [ ] **Step 2: Rewrite ModeratorDashboard**

Simplified: only `SentimentHero` and `SessionCards`. No barriers/competitors/trends. Accept same `studies`/`days` props.

- [ ] **Step 3: Update dashboard page props**

Ensure `WavAdminDashboard` and `ModeratorDashboard` receive `studies` and `days` props (same change from Task 18).

- [ ] **Step 4: Verify build compiles**

```bash
cd /Users/fede/projects/wav-intelligence && npx tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
git add src/components/dashboard/wav-admin-dashboard.tsx src/components/dashboard/moderator-dashboard.tsx
git commit -m "feat: integrate WavAdmin and Moderator dashboards"
```

---

### Task 20: Final Build Verification and Test Run

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/fede/projects/wav-intelligence && npx vitest run
```

All tests should pass (existing 130 + new ~15 dashboard tests).

- [ ] **Step 2: Run TypeScript build**

```bash
npx tsc --noEmit
```

- [ ] **Step 3: Fix any issues found**

- [ ] **Step 4: Commit any fixes**

```bash
git commit -m "fix: resolve dashboard build/test issues"
```
