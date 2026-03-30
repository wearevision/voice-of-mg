# Trends: Cross-Session Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dedicated `/trends` page showing topic frequency evolution across sessions, sentiment trajectory over time, action plan tracking (implemented vs persisting issues), and a cross-session comparison table.

**Architecture:** Dedicated `/trends` page with its own data-fetching hook (`useTrendsData`) and 3 new API endpoints. Reuses existing `DashboardFilters` infrastructure and Recharts charting. Role-gated to `wav_admin` and `mg_client` only. Feature-flagged via `crossSessionTrends`.

**Tech Stack:** Next.js 16 (App Router), Supabase, Recharts 3.8, shadcn/ui, Vitest

---

## File Structure

```
src/
├── app/
│   └── trends/
│       └── page.tsx                          ← Server component, auth + role guard
├── components/
│   └── trends/
│       ├── trends-dashboard.tsx              ← Client orchestrator (filters + charts)
│       ├── topic-frequency-chart.tsx         ← Bar chart: verbatim count per topic per session
│       ├── sentiment-trajectory.tsx          ← Line chart: sentiment score evolution per topic
│       ├── action-plan-tracker.tsx           ← Stacked bar: action plan status across sessions
│       └── cross-session-table.tsx           ← Table comparing key metrics per session
├── hooks/
│   └── use-trends-data.ts                   ← Fetches all 3 trends API endpoints in parallel
├── app/api/trends/
│   ├── topic-frequency/route.ts             ← Verbatim counts per topic per session
│   ├── action-tracker/route.ts              ← Action plan statuses across sessions
│   └── cross-session/route.ts               ← Per-session metrics comparison table
├── types/
│   └── trends.ts                            ← Types for trends feature
└── config/locales/
    ├── en-US.json                           ← +12 locale keys
    └── es-CL.json                           ← +12 locale keys
```

**Existing files modified:**
- `src/config/locales/en-US.json` — add `trends.*` locale keys
- `src/config/locales/es-CL.json` — add `trends.*` locale keys
- `src/components/layout/nav.tsx` — add Trends nav link (role-gated)

**Existing files reused (not modified):**
- `src/lib/dashboard/filters.ts` — `parseDashboardParams()` reused for query param parsing
- `src/types/dashboard.ts` — `DashboardFilters` type reused
- `src/hooks/use-label.ts` — `useLabel()` for i18n
- `src/hooks/use-feature.ts` — `useFeature('crossSessionTrends')` for feature flag
- `src/components/dashboard/dashboard-filters.tsx` — filter bar component reused
- `src/app/api/dashboard/trends/route.ts` — existing sentiment trends API (already works)
- `src/components/dashboard/sentiment-trends.tsx` — existing line chart (reused in trends page)

---

### Task 1: Trends Types

**Files:**
- Create: `src/types/trends.ts`
- Test: `tests/unit/trends/types.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/trends/types.test.ts
import { describe, it, expect } from 'vitest'
import type {
  TopicFrequencyPoint,
  ActionTrackerPoint,
  CrossSessionRow,
  TrendsData,
} from '@/types/trends'

describe('Trends types', () => {
  it('TopicFrequencyPoint has required fields', () => {
    const point: TopicFrequencyPoint = {
      sessionId: 's1',
      sessionName: 'Sesión 1',
      date: '2026-01-15',
      topic: 'marca',
      count: 42,
    }
    expect(point.topic).toBe('marca')
    expect(point.count).toBe(42)
  })

  it('ActionTrackerPoint has required fields', () => {
    const point: ActionTrackerPoint = {
      sessionId: 's1',
      sessionName: 'Sesión 1',
      date: '2026-01-15',
      pending: 3,
      inProgress: 2,
      done: 5,
      total: 10,
    }
    expect(point.total).toBe(10)
  })

  it('CrossSessionRow has required fields', () => {
    const row: CrossSessionRow = {
      sessionId: 's1',
      sessionName: 'Sesión 1',
      date: '2026-01-15',
      participantCount: 8,
      verbatimCount: 120,
      avgSentiment: 0.35,
      topTopic: 'diseno',
      barrierCount: 15,
      actionPlanCount: 7,
      actionsDone: 3,
    }
    expect(row.avgSentiment).toBe(0.35)
  })

  it('TrendsData has all data arrays and loading flag', () => {
    const data: TrendsData = {
      topicFrequency: [],
      actionTracker: [],
      crossSession: [],
      loading: false,
      error: null,
    }
    expect(data.loading).toBe(false)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/types.test.ts`
Expected: FAIL — module `@/types/trends` not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/types/trends.ts

export interface TopicFrequencyPoint {
  sessionId: string
  sessionName: string
  date: string
  topic: string
  count: number
}

export interface ActionTrackerPoint {
  sessionId: string
  sessionName: string
  date: string
  pending: number
  inProgress: number
  done: number
  total: number
}

export interface CrossSessionRow {
  sessionId: string
  sessionName: string
  date: string
  participantCount: number
  verbatimCount: number
  avgSentiment: number
  topTopic: string
  barrierCount: number
  actionPlanCount: number
  actionsDone: number
}

export interface TrendsData {
  topicFrequency: TopicFrequencyPoint[]
  actionTracker: ActionTrackerPoint[]
  crossSession: CrossSessionRow[]
  loading: boolean
  error: string | null
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/types.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/types/trends.ts tests/unit/trends/types.test.ts
git commit -m "feat: add trends types for cross-session analysis"
```

---

### Task 2: Topic Frequency API

**Files:**
- Create: `src/app/api/trends/topic-frequency/route.ts`
- Test: `tests/unit/trends/topic-frequency-route.test.ts`

**Context:** This endpoint groups verbatim counts by topic and session, allowing the frontend to chart how topic distribution evolves across sessions. Uses the `verbatims` table joined through `sessions → days` to get dates. Reuses `parseDashboardParams` for filter parsing.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/trends/topic-frequency-route.test.ts
import { describe, it, expect, vi } from 'vitest'

const mockVerbatimData = [
  { topic: 'marca', session_id: 's1', sessions: { name: 'Sesión 1', days: { date: '2026-01-15' } } },
  { topic: 'marca', session_id: 's1', sessions: { name: 'Sesión 1', days: { date: '2026-01-15' } } },
  { topic: 'diseno', session_id: 's1', sessions: { name: 'Sesión 1', days: { date: '2026-01-15' } } },
  { topic: 'marca', session_id: 's2', sessions: { name: 'Sesión 2', days: { date: '2026-02-10' } } },
  { topic: 'precio', session_id: 's2', sessions: { name: 'Sesión 2', days: { date: '2026-02-10' } } },
]

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: { getUser: vi.fn().mockResolvedValue({ data: { user: { id: 'u1' } }, error: null }) },
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockReturnValue({
        order: vi.fn().mockResolvedValue({ data: mockVerbatimData, error: null }),
        in: vi.fn().mockReturnValue({
          order: vi.fn().mockResolvedValue({ data: mockVerbatimData, error: null }),
        }),
      }),
    }),
  }),
}))

import { GET, aggregateTopicFrequency } from '@/app/api/trends/topic-frequency/route'

describe('GET /api/trends/topic-frequency', () => {
  it('returns topic frequency points grouped by session and topic', async () => {
    const req = new Request('http://localhost/api/trends/topic-frequency')
    const res = await GET(req as any)
    expect(res.status).toBe(200)
    const json = await res.json()
    expect(json.topicFrequency).toBeDefined()
    expect(json.topicFrequency.length).toBeGreaterThan(0)
  })
})

describe('aggregateTopicFrequency', () => {
  it('groups verbatim counts by session + topic', () => {
    const result = aggregateTopicFrequency(mockVerbatimData as any)
    const s1Marca = result.find((p) => p.sessionId === 's1' && p.topic === 'marca')
    expect(s1Marca?.count).toBe(2)
    const s1Diseno = result.find((p) => p.sessionId === 's1' && p.topic === 'diseno')
    expect(s1Diseno?.count).toBe(1)
    const s2Marca = result.find((p) => p.sessionId === 's2' && p.topic === 'marca')
    expect(s2Marca?.count).toBe(1)
  })

  it('sorts by date ascending', () => {
    const result = aggregateTopicFrequency(mockVerbatimData as any)
    const dates = result.map((p) => p.date)
    expect(dates[0]).toBe('2026-01-15')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/topic-frequency-route.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/app/api/trends/topic-frequency/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { parseDashboardParams } from '@/lib/dashboard/filters'
import type { TopicFrequencyPoint } from '@/types/trends'

interface VerbatimRow {
  topic: string
  session_id: string
  sessions: { name: string; days: { date: string } }
}

export function aggregateTopicFrequency(rows: VerbatimRow[]): TopicFrequencyPoint[] {
  const map = new Map<string, TopicFrequencyPoint>()
  for (const row of rows) {
    const date = row.sessions?.days?.date ?? ''
    const key = `${row.session_id}|${row.topic}`
    const existing = map.get(key)
    if (existing) {
      map.set(key, { ...existing, count: existing.count + 1 })
    } else {
      map.set(key, {
        sessionId: row.session_id,
        sessionName: row.sessions?.name ?? '',
        date,
        topic: row.topic,
        count: 1,
      })
    }
  }
  return Array.from(map.values()).sort((a, b) => a.date.localeCompare(b.date))
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
    .select('topic, session_id, sessions(name, days(date))')

  if (filters.topics.length > 0) {
    query = query.in('topic', filters.topics)
  }

  const { data, error } = await query.order('session_id')
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  const topicFrequency = aggregateTopicFrequency((data ?? []) as unknown as VerbatimRow[])
  return NextResponse.json({ topicFrequency })
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/topic-frequency-route.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/app/api/trends/topic-frequency/route.ts tests/unit/trends/topic-frequency-route.test.ts
git commit -m "feat: add topic frequency API for cross-session trends"
```

---

### Task 3: Action Plan Tracker API

**Files:**
- Create: `src/app/api/trends/action-tracker/route.ts`
- Test: `tests/unit/trends/action-tracker-route.test.ts`

**Context:** This endpoint aggregates action plan statuses (pending/in_progress/done) per session, enabling a stacked bar chart showing resolution progress over time. Queries `action_plans` joined through `sessions → days`.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/trends/action-tracker-route.test.ts
import { describe, it, expect, vi } from 'vitest'

const mockActionData = [
  { session_id: 's1', status: 'pending', sessions: { name: 'Sesión 1', days: { date: '2026-01-15' } } },
  { session_id: 's1', status: 'done', sessions: { name: 'Sesión 1', days: { date: '2026-01-15' } } },
  { session_id: 's1', status: 'done', sessions: { name: 'Sesión 1', days: { date: '2026-01-15' } } },
  { session_id: 's2', status: 'in_progress', sessions: { name: 'Sesión 2', days: { date: '2026-02-10' } } },
  { session_id: 's2', status: 'pending', sessions: { name: 'Sesión 2', days: { date: '2026-02-10' } } },
]

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: { getUser: vi.fn().mockResolvedValue({ data: { user: { id: 'u1' } }, error: null }) },
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockReturnValue({
        order: vi.fn().mockResolvedValue({ data: mockActionData, error: null }),
      }),
    }),
  }),
}))

import { GET, aggregateActionTracker } from '@/app/api/trends/action-tracker/route'

describe('GET /api/trends/action-tracker', () => {
  it('returns action tracker points', async () => {
    const req = new Request('http://localhost/api/trends/action-tracker')
    const res = await GET(req as any)
    expect(res.status).toBe(200)
    const json = await res.json()
    expect(json.actionTracker).toBeDefined()
  })
})

describe('aggregateActionTracker', () => {
  it('groups action plan statuses by session', () => {
    const result = aggregateActionTracker(mockActionData as any)
    const s1 = result.find((p) => p.sessionId === 's1')
    expect(s1?.pending).toBe(1)
    expect(s1?.done).toBe(2)
    expect(s1?.total).toBe(3)
    const s2 = result.find((p) => p.sessionId === 's2')
    expect(s2?.inProgress).toBe(1)
    expect(s2?.pending).toBe(1)
    expect(s2?.total).toBe(2)
  })

  it('sorts by date ascending', () => {
    const result = aggregateActionTracker(mockActionData as any)
    expect(result[0].date).toBe('2026-01-15')
    expect(result[1].date).toBe('2026-02-10')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/action-tracker-route.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/app/api/trends/action-tracker/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import type { ActionTrackerPoint } from '@/types/trends'

interface ActionRow {
  session_id: string
  status: 'pending' | 'in_progress' | 'done'
  sessions: { name: string; days: { date: string } }
}

export function aggregateActionTracker(rows: ActionRow[]): ActionTrackerPoint[] {
  const map = new Map<string, ActionTrackerPoint>()
  for (const row of rows) {
    const date = row.sessions?.days?.date ?? ''
    const existing = map.get(row.session_id)
    if (existing) {
      const updated = { ...existing }
      if (row.status === 'pending') updated.pending++
      else if (row.status === 'in_progress') updated.inProgress++
      else if (row.status === 'done') updated.done++
      updated.total++
      map.set(row.session_id, updated)
    } else {
      map.set(row.session_id, {
        sessionId: row.session_id,
        sessionName: row.sessions?.name ?? '',
        date,
        pending: row.status === 'pending' ? 1 : 0,
        inProgress: row.status === 'in_progress' ? 1 : 0,
        done: row.status === 'done' ? 1 : 0,
        total: 1,
      })
    }
  }
  return Array.from(map.values()).sort((a, b) => a.date.localeCompare(b.date))
}

export async function GET(req: NextRequest) {
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const { data, error } = await supabase
    .from('action_plans')
    .select('session_id, status, sessions(name, days(date))')
    .order('session_id')

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  const actionTracker = aggregateActionTracker((data ?? []) as unknown as ActionRow[])
  return NextResponse.json({ actionTracker })
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/action-tracker-route.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/app/api/trends/action-tracker/route.ts tests/unit/trends/action-tracker-route.test.ts
git commit -m "feat: add action plan tracker API for cross-session trends"
```

---

### Task 4: Cross-Session Comparison API

**Files:**
- Create: `src/app/api/trends/cross-session/route.ts`
- Test: `tests/unit/trends/cross-session-route.test.ts`

**Context:** This endpoint returns per-session summary metrics for a comparison table: participant count, verbatim count, average sentiment, top topic, barrier count, action plan stats. Joins across `sessions`, `days`, `verbatims`, `participants`, `purchase_barriers`, and `action_plans`.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/trends/cross-session-route.test.ts
import { describe, it, expect, vi } from 'vitest'

const mockSessions = [
  { id: 's1', name: 'Sesión 1', days: { date: '2026-01-15' } },
  { id: 's2', name: 'Sesión 2', days: { date: '2026-02-10' } },
]

const mockVerbatims = [
  { session_id: 's1', topic: 'marca', sentiment_score: 0.5 },
  { session_id: 's1', topic: 'marca', sentiment_score: 0.3 },
  { session_id: 's1', topic: 'diseno', sentiment_score: -0.2 },
  { session_id: 's2', topic: 'precio', sentiment_score: -0.8 },
]

const mockParticipants = [
  { session_id: 's1' },
  { session_id: 's1' },
  { session_id: 's2' },
]

const mockBarriers = [
  { session_id: 's1', mention_count: 5 },
  { session_id: 's1', mention_count: 3 },
  { session_id: 's2', mention_count: 10 },
]

const mockActions = [
  { session_id: 's1', status: 'done' },
  { session_id: 's1', status: 'pending' },
  { session_id: 's2', status: 'in_progress' },
]

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: { getUser: vi.fn().mockResolvedValue({ data: { user: { id: 'u1' } }, error: null }) },
    from: vi.fn().mockImplementation((table: string) => {
      const mockData: Record<string, unknown[]> = {
        sessions: mockSessions,
        verbatims: mockVerbatims,
        participants: mockParticipants,
        purchase_barriers: mockBarriers,
        action_plans: mockActions,
      }
      return {
        select: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            order: vi.fn().mockResolvedValue({ data: mockData[table], error: null }),
          }),
          order: vi.fn().mockResolvedValue({ data: mockData[table], error: null }),
        }),
      }
    }),
  }),
}))

import { GET, buildCrossSession } from '@/app/api/trends/cross-session/route'

describe('buildCrossSession', () => {
  it('builds per-session summary rows', () => {
    const result = buildCrossSession(
      mockSessions as any,
      mockVerbatims as any,
      mockParticipants as any,
      mockBarriers as any,
      mockActions as any,
    )
    expect(result).toHaveLength(2)

    const s1 = result.find((r) => r.sessionId === 's1')!
    expect(s1.participantCount).toBe(2)
    expect(s1.verbatimCount).toBe(3)
    expect(s1.avgSentiment).toBeCloseTo(0.2, 1)
    expect(s1.topTopic).toBe('marca')
    expect(s1.barrierCount).toBe(8)
    expect(s1.actionPlanCount).toBe(2)
    expect(s1.actionsDone).toBe(1)

    const s2 = result.find((r) => r.sessionId === 's2')!
    expect(s2.participantCount).toBe(1)
    expect(s2.verbatimCount).toBe(1)
    expect(s2.topTopic).toBe('precio')
  })
})

describe('GET /api/trends/cross-session', () => {
  it('returns cross-session rows', async () => {
    const req = new Request('http://localhost/api/trends/cross-session')
    const res = await GET(req as any)
    expect(res.status).toBe(200)
    const json = await res.json()
    expect(json.crossSession).toBeDefined()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/cross-session-route.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/app/api/trends/cross-session/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import type { CrossSessionRow } from '@/types/trends'

interface SessionRow { id: string; name: string; days: { date: string } }
interface VerbatimRow { session_id: string; topic: string; sentiment_score: number }
interface ParticipantRow { session_id: string }
interface BarrierRow { session_id: string; mention_count: number }
interface ActionRow { session_id: string; status: string }

export function buildCrossSession(
  sessions: SessionRow[],
  verbatims: VerbatimRow[],
  participants: ParticipantRow[],
  barriers: BarrierRow[],
  actions: ActionRow[],
): CrossSessionRow[] {
  return sessions.map((session) => {
    const sVerbatims = verbatims.filter((v) => v.session_id === session.id)
    const sParticipants = participants.filter((p) => p.session_id === session.id)
    const sBarriers = barriers.filter((b) => b.session_id === session.id)
    const sActions = actions.filter((a) => a.session_id === session.id)

    const avgSentiment = sVerbatims.length > 0
      ? sVerbatims.reduce((sum, v) => sum + v.sentiment_score, 0) / sVerbatims.length
      : 0

    const topicCounts = new Map<string, number>()
    for (const v of sVerbatims) {
      topicCounts.set(v.topic, (topicCounts.get(v.topic) ?? 0) + 1)
    }
    let topTopic = ''
    let topCount = 0
    for (const [topic, count] of topicCounts) {
      if (count > topCount) {
        topTopic = topic
        topCount = count
      }
    }

    const barrierCount = sBarriers.reduce((sum, b) => sum + b.mention_count, 0)

    return {
      sessionId: session.id,
      sessionName: session.name,
      date: session.days?.date ?? '',
      participantCount: sParticipants.length,
      verbatimCount: sVerbatims.length,
      avgSentiment,
      topTopic,
      barrierCount,
      actionPlanCount: sActions.length,
      actionsDone: sActions.filter((a) => a.status === 'done').length,
    }
  }).sort((a, b) => a.date.localeCompare(b.date))
}

export async function GET(req: NextRequest) {
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const [sessionsRes, verbatimsRes, participantsRes, barriersRes, actionsRes] = await Promise.all([
    supabase.from('sessions').select('id, name, days(date)').order('name'),
    supabase.from('verbatims').select('session_id, topic, sentiment_score'),
    supabase.from('participants').select('session_id'),
    supabase.from('purchase_barriers').select('session_id, mention_count'),
    supabase.from('action_plans').select('session_id, status'),
  ])

  if (sessionsRes.error) {
    return NextResponse.json({ error: sessionsRes.error.message }, { status: 500 })
  }

  const crossSession = buildCrossSession(
    (sessionsRes.data ?? []) as unknown as SessionRow[],
    (verbatimsRes.data ?? []) as unknown as VerbatimRow[],
    (participantsRes.data ?? []) as unknown as ParticipantRow[],
    (barriersRes.data ?? []) as unknown as BarrierRow[],
    (actionsRes.data ?? []) as unknown as ActionRow[],
  )

  return NextResponse.json({ crossSession })
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/cross-session-route.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/app/api/trends/cross-session/route.ts tests/unit/trends/cross-session-route.test.ts
git commit -m "feat: add cross-session comparison API for trends"
```

---

### Task 5: useTrendsData Hook

**Files:**
- Create: `src/hooks/use-trends-data.ts`
- Test: `tests/unit/trends/use-trends-data.test.tsx`

**Context:** Client-side hook that fetches all 3 trends endpoints (`topic-frequency`, `action-tracker`, `cross-session`) plus the existing `/api/dashboard/trends` (for sentiment trajectory) in parallel. Reuses `DashboardFilters` and `buildQuery` pattern from `useDashboardData`.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/trends/use-trends-data.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useTrendsData } from '@/hooks/use-trends-data'
import type { DashboardFilters } from '@/types/dashboard'

const mockFetch = vi.fn()
global.fetch = mockFetch

const defaultFilters: DashboardFilters = {
  studyId: null, dayId: null, topics: [], dateFrom: null, dateTo: null,
}

describe('useTrendsData', () => {
  beforeEach(() => {
    mockFetch.mockReset()
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        topicFrequency: [],
        actionTracker: [],
        crossSession: [],
        trends: [],
      }),
    })
  })

  it('fetches all 4 endpoints in parallel', async () => {
    renderHook(() => useTrendsData(defaultFilters))
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(4)
    })
    const urls = mockFetch.mock.calls.map((c: unknown[]) => (c[0] as string))
    expect(urls.some((u: string) => u.includes('/api/trends/topic-frequency'))).toBe(true)
    expect(urls.some((u: string) => u.includes('/api/trends/action-tracker'))).toBe(true)
    expect(urls.some((u: string) => u.includes('/api/trends/cross-session'))).toBe(true)
    expect(urls.some((u: string) => u.includes('/api/dashboard/trends'))).toBe(true)
  })

  it('starts with loading true', () => {
    const { result } = renderHook(() => useTrendsData(defaultFilters))
    expect(result.current.loading).toBe(true)
  })

  it('passes filter query params', async () => {
    const filters: DashboardFilters = {
      studyId: null, dayId: null, topics: ['marca', 'diseno'], dateFrom: null, dateTo: null,
    }
    renderHook(() => useTrendsData(filters))
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })
    const urls = mockFetch.mock.calls.map((c: unknown[]) => (c[0] as string))
    expect(urls.every((u: string) => u.includes('topics=marca%2Cdiseno') || u.includes('topics=marca,diseno'))).toBe(true)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/use-trends-data.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/hooks/use-trends-data.ts
'use client'

import { useState, useEffect, useCallback } from 'react'
import type { DashboardFilters } from '@/types/dashboard'
import type { TrendPoint } from '@/types/dashboard'
import type { TopicFrequencyPoint, ActionTrackerPoint, CrossSessionRow } from '@/types/trends'

interface TrendsDataState {
  topicFrequency: TopicFrequencyPoint[]
  sentimentTrends: TrendPoint[]
  actionTracker: ActionTrackerPoint[]
  crossSession: CrossSessionRow[]
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

export function useTrendsData(filters: DashboardFilters): TrendsDataState {
  const [data, setData] = useState<TrendsDataState>({
    topicFrequency: [],
    sentimentTrends: [],
    actionTracker: [],
    crossSession: [],
    loading: true,
    error: null,
  })

  const fetchAll = useCallback(async () => {
    setData((prev) => ({ ...prev, loading: true, error: null }))
    const qs = buildQuery(filters)

    try {
      const [freqRes, sentimentRes, actionRes, crossRes] = await Promise.all([
        fetch(`/api/trends/topic-frequency${qs}`),
        fetch(`/api/dashboard/trends${qs}`),
        fetch(`/api/trends/action-tracker${qs}`),
        fetch(`/api/trends/cross-session${qs}`),
      ])

      const [freqJson, sentimentJson, actionJson, crossJson] = await Promise.all([
        freqRes.json(),
        sentimentRes.json(),
        actionRes.json(),
        crossRes.json(),
      ])

      setData({
        topicFrequency: freqJson.topicFrequency ?? [],
        sentimentTrends: sentimentJson.trends ?? [],
        actionTracker: actionJson.actionTracker ?? [],
        crossSession: crossJson.crossSession ?? [],
        loading: false,
        error: null,
      })
    } catch (err) {
      setData((prev) => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : 'Failed to load trends',
      }))
    }
  }, [filters])

  useEffect(() => { fetchAll() }, [fetchAll])

  return data
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/use-trends-data.test.tsx`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/hooks/use-trends-data.ts tests/unit/trends/use-trends-data.test.tsx
git commit -m "feat: add useTrendsData hook for parallel trends fetching"
```

---

### Task 6: TopicFrequencyChart Component

**Files:**
- Create: `src/components/trends/topic-frequency-chart.tsx`
- Test: `tests/unit/trends/topic-frequency-chart.test.tsx`

**Context:** A grouped bar chart showing how many verbatims each topic received across sessions. X-axis = sessions (by date), Y-axis = count, color-coded bars per topic. Uses Recharts `BarChart` with grouped bars. Follows the same Card + CardHeader + CardContent pattern as existing dashboard widgets.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/trends/topic-frequency-chart.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TopicFrequencyChart, transformForChart } from '@/components/trends/topic-frequency-chart'
import type { TopicFrequencyPoint } from '@/types/trends'

// Mock Recharts to avoid SVG rendering issues in JSDOM
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="responsive-container">{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => <div data-testid="bar" />,
  XAxis: () => <div />,
  YAxis: () => <div />,
  CartesianGrid: () => <div />,
  Tooltip: () => <div />,
  Legend: () => <div />,
}))

const mockData: TopicFrequencyPoint[] = [
  { sessionId: 's1', sessionName: 'Sesión 1', date: '2026-01-15', topic: 'marca', count: 10 },
  { sessionId: 's1', sessionName: 'Sesión 1', date: '2026-01-15', topic: 'diseno', count: 8 },
  { sessionId: 's2', sessionName: 'Sesión 2', date: '2026-02-10', topic: 'marca', count: 15 },
  { sessionId: 's2', sessionName: 'Sesión 2', date: '2026-02-10', topic: 'precio', count: 5 },
]

const mockLabel = (key: string) => key

describe('transformForChart', () => {
  it('pivots flat data to session rows with topic columns', () => {
    const { data, topics } = transformForChart(mockData)
    expect(data).toHaveLength(2) // 2 sessions
    expect(topics).toContain('marca')
    expect(topics).toContain('diseno')
    expect(topics).toContain('precio')
    expect(data[0]).toMatchObject({ sessionName: 'Sesión 1', marca: 10, diseno: 8 })
    expect(data[1]).toMatchObject({ sessionName: 'Sesión 2', marca: 15, precio: 5 })
  })
})

describe('TopicFrequencyChart', () => {
  it('renders card with title', () => {
    render(<TopicFrequencyChart data={mockData} label={mockLabel} />)
    expect(screen.getByText('trends.topic_frequency')).toBeDefined()
  })

  it('renders bar chart', () => {
    render(<TopicFrequencyChart data={mockData} label={mockLabel} />)
    expect(screen.getByTestId('bar-chart')).toBeDefined()
  })

  it('renders no-data message when empty', () => {
    render(<TopicFrequencyChart data={[]} label={mockLabel} />)
    expect(screen.getByText('dashboard.no_data')).toBeDefined()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/topic-frequency-chart.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/components/trends/topic-frequency-chart.tsx
'use client'

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { TOPIC_COLORS } from '@/types/player'
import type { TopicFrequencyPoint } from '@/types/trends'

interface TopicFrequencyChartProps {
  data: TopicFrequencyPoint[]
  label: (key: string) => string
}

export function transformForChart(data: TopicFrequencyPoint[]): {
  data: Array<Record<string, unknown>>
  topics: string[]
} {
  const sessionMap = new Map<string, Record<string, unknown>>()
  const topicSet = new Set<string>()

  for (const point of data) {
    topicSet.add(point.topic)
    const entry = sessionMap.get(point.sessionId) ?? {
      sessionName: point.sessionName,
      date: point.date,
    }
    entry[point.topic] = point.count
    sessionMap.set(point.sessionId, entry)
  }

  return {
    data: Array.from(sessionMap.values()).sort((a, b) =>
      (a.date as string).localeCompare(b.date as string),
    ),
    topics: Array.from(topicSet),
  }
}

export function TopicFrequencyChart({ data, label }: TopicFrequencyChartProps) {
  const { data: chartData, topics } = transformForChart(data)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{label('trends.topic_frequency')}</CardTitle>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <p className="text-sm text-muted-foreground">{label('dashboard.no_data')}</p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
              <XAxis dataKey="sessionName" tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }} />
              <YAxis tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }} />
              <Tooltip contentStyle={{ backgroundColor: 'var(--card)', border: '1px solid var(--border)' }} />
              <Legend />
              {topics.map((topic) => (
                <Bar key={topic} dataKey={topic} fill={TOPIC_COLORS[topic] ?? '#6b7280'} name={topic.replace(/_/g, ' ')} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/topic-frequency-chart.test.tsx`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/components/trends/topic-frequency-chart.tsx tests/unit/trends/topic-frequency-chart.test.tsx
git commit -m "feat: add topic frequency grouped bar chart component"
```

---

### Task 7: ActionPlanTracker Component

**Files:**
- Create: `src/components/trends/action-plan-tracker.tsx`
- Test: `tests/unit/trends/action-plan-tracker.test.tsx`

**Context:** A stacked bar chart showing action plan resolution across sessions. Each bar = one session, segments = pending (amber), in_progress (blue), done (emerald). Lets MG Motor see if issues are being resolved over time.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/trends/action-plan-tracker.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ActionPlanTracker } from '@/components/trends/action-plan-tracker'
import type { ActionTrackerPoint } from '@/types/trends'

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="responsive-container">{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => <div data-testid="bar" />,
  XAxis: () => <div />,
  YAxis: () => <div />,
  CartesianGrid: () => <div />,
  Tooltip: () => <div />,
  Legend: () => <div />,
}))

const mockData: ActionTrackerPoint[] = [
  { sessionId: 's1', sessionName: 'Sesión 1', date: '2026-01-15', pending: 3, inProgress: 2, done: 5, total: 10 },
  { sessionId: 's2', sessionName: 'Sesión 2', date: '2026-02-10', pending: 1, inProgress: 4, done: 8, total: 13 },
]

const mockLabel = (key: string) => key

describe('ActionPlanTracker', () => {
  it('renders card with title', () => {
    render(<ActionPlanTracker data={mockData} label={mockLabel} />)
    expect(screen.getByText('trends.action_tracker')).toBeDefined()
  })

  it('renders stacked bar chart', () => {
    render(<ActionPlanTracker data={mockData} label={mockLabel} />)
    expect(screen.getByTestId('bar-chart')).toBeDefined()
  })

  it('renders 3 bar segments (pending, inProgress, done)', () => {
    render(<ActionPlanTracker data={mockData} label={mockLabel} />)
    const bars = screen.getAllByTestId('bar')
    expect(bars).toHaveLength(3)
  })

  it('renders no-data message when empty', () => {
    render(<ActionPlanTracker data={[]} label={mockLabel} />)
    expect(screen.getByText('dashboard.no_data')).toBeDefined()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/action-plan-tracker.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/components/trends/action-plan-tracker.tsx
'use client'

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import type { ActionTrackerPoint } from '@/types/trends'

interface ActionPlanTrackerProps {
  data: ActionTrackerPoint[]
  label: (key: string) => string
}

const STATUS_COLORS = {
  done: '#10b981',
  inProgress: '#3b82f6',
  pending: '#f59e0b',
} as const

export function ActionPlanTracker({ data, label }: ActionPlanTrackerProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{label('trends.action_tracker')}</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="text-sm text-muted-foreground">{label('dashboard.no_data')}</p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
              <XAxis dataKey="sessionName" tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }} />
              <YAxis tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }} />
              <Tooltip contentStyle={{ backgroundColor: 'var(--card)', border: '1px solid var(--border)' }} />
              <Legend />
              <Bar dataKey="done" stackId="status" fill={STATUS_COLORS.done} name={label('trends.status_done')} />
              <Bar dataKey="inProgress" stackId="status" fill={STATUS_COLORS.inProgress} name={label('trends.status_in_progress')} />
              <Bar dataKey="pending" stackId="status" fill={STATUS_COLORS.pending} name={label('trends.status_pending')} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/action-plan-tracker.test.tsx`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/components/trends/action-plan-tracker.tsx tests/unit/trends/action-plan-tracker.test.tsx
git commit -m "feat: add action plan tracker stacked bar chart"
```

---

### Task 8: CrossSessionTable Component

**Files:**
- Create: `src/components/trends/cross-session-table.tsx`
- Test: `tests/unit/trends/cross-session-table.test.tsx`

**Context:** A comparison table where each row = one session, columns show date, participant count, verbatim count, avg sentiment (color-coded), top topic (Badge), barrier count, action plan progress (done/total). Uses shadcn/ui `Table`. Sortable by clicking column headers.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/trends/cross-session-table.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CrossSessionTable } from '@/components/trends/cross-session-table'
import type { CrossSessionRow } from '@/types/trends'

const mockData: CrossSessionRow[] = [
  {
    sessionId: 's1', sessionName: 'Sesión 1', date: '2026-01-15',
    participantCount: 8, verbatimCount: 120, avgSentiment: 0.35,
    topTopic: 'diseno', barrierCount: 15, actionPlanCount: 7, actionsDone: 3,
  },
  {
    sessionId: 's2', sessionName: 'Sesión 2', date: '2026-02-10',
    participantCount: 10, verbatimCount: 95, avgSentiment: -0.1,
    topTopic: 'precio', barrierCount: 22, actionPlanCount: 10, actionsDone: 8,
  },
]

const mockLabel = (key: string) => key

describe('CrossSessionTable', () => {
  it('renders all session rows', () => {
    render(<CrossSessionTable data={mockData} label={mockLabel} />)
    expect(screen.getByText('Sesión 1')).toBeDefined()
    expect(screen.getByText('Sesión 2')).toBeDefined()
  })

  it('displays participant counts', () => {
    render(<CrossSessionTable data={mockData} label={mockLabel} />)
    expect(screen.getByText('8')).toBeDefined()
    expect(screen.getByText('10')).toBeDefined()
  })

  it('displays action plan progress', () => {
    render(<CrossSessionTable data={mockData} label={mockLabel} />)
    expect(screen.getByText('3/7')).toBeDefined()
    expect(screen.getByText('8/10')).toBeDefined()
  })

  it('renders no-data message when empty', () => {
    render(<CrossSessionTable data={[]} label={mockLabel} />)
    expect(screen.getByText('dashboard.no_data')).toBeDefined()
  })

  it('sorts by column when header clicked', async () => {
    const user = userEvent.setup()
    render(<CrossSessionTable data={mockData} label={mockLabel} />)
    const verbatimHeader = screen.getByText('trends.col_verbatims')
    await user.click(verbatimHeader)
    const rows = screen.getAllByRole('row')
    // Header + 2 data rows
    expect(rows).toHaveLength(3)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/cross-session-table.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/components/trends/cross-session-table.tsx
'use client'

import { useState, useMemo } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import type { CrossSessionRow } from '@/types/trends'

interface CrossSessionTableProps {
  data: CrossSessionRow[]
  label: (key: string) => string
}

type SortField = 'date' | 'participantCount' | 'verbatimCount' | 'avgSentiment' | 'barrierCount' | 'actionsDone'

function sentimentColor(value: number): string {
  if (value > 0.15) return 'text-emerald-400'
  if (value < -0.15) return 'text-red-400'
  return 'text-amber-400'
}

export function CrossSessionTable({ data, label }: CrossSessionTableProps) {
  const [sortField, setSortField] = useState<SortField>('date')
  const [sortAsc, setSortAsc] = useState(true)

  const sorted = useMemo(() => {
    const copy = [...data]
    copy.sort((a, b) => {
      const aVal = a[sortField]
      const bVal = b[sortField]
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal)
      }
      return sortAsc ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number)
    })
    return copy
  }, [data, sortField, sortAsc])

  function handleSort(field: SortField) {
    if (field === sortField) {
      setSortAsc((prev) => !prev)
    } else {
      setSortField(field)
      setSortAsc(true)
    }
  }

  const headerClass = 'cursor-pointer hover:text-foreground transition-colors select-none'

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{label('trends.cross_session_table')}</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="text-sm text-muted-foreground">{label('dashboard.no_data')}</p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className={headerClass} onClick={() => handleSort('date')}>{label('trends.col_session')}</TableHead>
                  <TableHead className={headerClass} onClick={() => handleSort('date')}>{label('trends.col_date')}</TableHead>
                  <TableHead className={`${headerClass} text-right`} onClick={() => handleSort('participantCount')}>{label('trends.col_participants')}</TableHead>
                  <TableHead className={`${headerClass} text-right`} onClick={() => handleSort('verbatimCount')}>{label('trends.col_verbatims')}</TableHead>
                  <TableHead className={`${headerClass} text-right`} onClick={() => handleSort('avgSentiment')}>{label('trends.col_sentiment')}</TableHead>
                  <TableHead>{label('trends.col_top_topic')}</TableHead>
                  <TableHead className={`${headerClass} text-right`} onClick={() => handleSort('barrierCount')}>{label('trends.col_barriers')}</TableHead>
                  <TableHead className={`${headerClass} text-right`} onClick={() => handleSort('actionsDone')}>{label('trends.col_actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sorted.map((row) => (
                  <TableRow key={row.sessionId}>
                    <TableCell className="font-medium">{row.sessionName}</TableCell>
                    <TableCell className="text-muted-foreground">{row.date}</TableCell>
                    <TableCell className="text-right">{row.participantCount}</TableCell>
                    <TableCell className="text-right">{row.verbatimCount}</TableCell>
                    <TableCell className={`text-right font-mono ${sentimentColor(row.avgSentiment)}`}>
                      {row.avgSentiment.toFixed(2)}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">{row.topTopic.replace(/_/g, ' ')}</Badge>
                    </TableCell>
                    <TableCell className="text-right">{row.barrierCount}</TableCell>
                    <TableCell className="text-right">{row.actionsDone}/{row.actionPlanCount}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/cross-session-table.test.tsx`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/components/trends/cross-session-table.tsx tests/unit/trends/cross-session-table.test.tsx
git commit -m "feat: add sortable cross-session comparison table"
```

---

### Task 9: TrendsDashboard Orchestrator Component

**Files:**
- Create: `src/components/trends/trends-dashboard.tsx`
- Test: `tests/unit/trends/trends-dashboard.test.tsx`

**Context:** Client component that orchestrates the entire `/trends` page. Contains a `DashboardFiltersBar` (reused from dashboard) and renders all 4 chart/table widgets in a responsive grid. Uses `useTrendsData` hook. Reuses `SentimentTrends` from dashboard for the sentiment trajectory line chart.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/trends/trends-dashboard.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TrendsDashboard } from '@/components/trends/trends-dashboard'

vi.mock('@/hooks/use-trends-data', () => ({
  useTrendsData: vi.fn().mockReturnValue({
    topicFrequency: [],
    sentimentTrends: [],
    actionTracker: [],
    crossSession: [],
    loading: false,
    error: null,
  }),
}))

vi.mock('@/hooks/use-label', () => ({
  useLabel: vi.fn().mockReturnValue((key: string) => key),
}))

vi.mock('@/hooks/use-feature', () => ({
  useFeature: vi.fn().mockReturnValue(true),
}))

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LineChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Bar: () => <div />,
  Line: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
  CartesianGrid: () => <div />,
  Tooltip: () => <div />,
  Legend: () => <div />,
}))

const mockStudies = [{ id: 'fg1', name: 'Q1 2026' }]
const mockDays = [{ id: 'd1', studyId: 'fg1', name: 'Día 1', date: '2026-01-15' }]

describe('TrendsDashboard', () => {
  it('renders page title', () => {
    render(<TrendsDashboard studies={mockStudies} days={mockDays} />)
    expect(screen.getByText('trends.title')).toBeDefined()
  })

  it('renders all 4 widget sections', () => {
    render(<TrendsDashboard studies={mockStudies} days={mockDays} />)
    expect(screen.getByText('trends.topic_frequency')).toBeDefined()
    expect(screen.getByText('dashboard.widget.sentiment_trends')).toBeDefined()
    expect(screen.getByText('trends.action_tracker')).toBeDefined()
    expect(screen.getByText('trends.cross_session_table')).toBeDefined()
  })

  it('shows loading state', () => {
    const { useTrendsData } = vi.mocked(await import('@/hooks/use-trends-data'))
    useTrendsData.mockReturnValueOnce({
      topicFrequency: [], sentimentTrends: [], actionTracker: [], crossSession: [],
      loading: true, error: null,
    })
    render(<TrendsDashboard studies={mockStudies} days={mockDays} />)
    expect(screen.getByText('dashboard.loading')).toBeDefined()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/trends-dashboard.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/components/trends/trends-dashboard.tsx
'use client'

import { useState } from 'react'
import { useLabel } from '@/hooks/use-label'
import { useTrendsData } from '@/hooks/use-trends-data'
import type { DashboardFilters } from '@/types/dashboard'
import { DashboardFiltersBar } from '@/components/dashboard/dashboard-filters'
import { TopicFrequencyChart } from './topic-frequency-chart'
import { SentimentTrends } from '@/components/dashboard/sentiment-trends'
import { ActionPlanTracker } from './action-plan-tracker'
import { CrossSessionTable } from './cross-session-table'

interface TrendsDashboardProps {
  studies: Array<{ id: string; name: string }>
  days: Array<{ id: string; studyId: string; name: string; date: string }>
}

export function TrendsDashboard({ studies, days }: TrendsDashboardProps) {
  const label = useLabel()
  const [filters, setFilters] = useState<DashboardFilters>({
    studyId: null, dayId: null, topics: [], dateFrom: null, dateTo: null,
  })

  const { topicFrequency, sentimentTrends, actionTracker, crossSession, loading } = useTrendsData(filters)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-foreground">{label('trends.title')}</h1>

      <DashboardFiltersBar studies={studies} days={days} filters={filters} onFiltersChange={setFilters} label={label} />

      {loading ? (
        <p className="text-sm text-muted-foreground">{label('dashboard.loading')}</p>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <TopicFrequencyChart data={topicFrequency} label={label} />
            <SentimentTrends trends={sentimentTrends} label={label} />
          </div>

          <ActionPlanTracker data={actionTracker} label={label} />

          <CrossSessionTable data={crossSession} label={label} />
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/trends-dashboard.test.tsx`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/components/trends/trends-dashboard.tsx tests/unit/trends/trends-dashboard.test.tsx
git commit -m "feat: add TrendsDashboard orchestrator component"
```

---

### Task 10: Trends Page (Server Component + Routing)

**Files:**
- Create: `src/app/trends/page.tsx`
- Test: `tests/unit/trends/trends-page.test.tsx`

**Context:** Server component that handles auth, role checking (only `wav_admin` and `mg_client`), prefetches studies/days (same pattern as dashboard/page.tsx), and renders `TrendsDashboard`. Redirects unauthorized users to `/dashboard`.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/trends/trends-page.test.tsx
import { describe, it, expect, vi } from 'vitest'

const mockRedirect = vi.fn()

vi.mock('next/navigation', () => ({
  redirect: (...args: unknown[]) => {
    mockRedirect(...args)
    throw new Error('NEXT_REDIRECT')
  },
}))

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
        order: vi.fn().mockResolvedValue({ data: [], error: null }),
      }),
    }),
  }),
}))

vi.mock('@/components/trends/trends-dashboard', () => ({
  TrendsDashboard: ({ studies, days }: { studies: unknown[]; days: unknown[] }) => (
    <div data-testid="trends-dashboard" data-studies={JSON.stringify(studies)} data-days={JSON.stringify(days)} />
  ),
}))

import TrendsPage from '@/app/trends/page'

describe('TrendsPage', () => {
  it('renders TrendsDashboard for mg_client role', async () => {
    const { render, screen } = await import('@testing-library/react')
    const page = await TrendsPage()
    render(page)
    expect(screen.getByTestId('trends-dashboard')).toBeDefined()
  })

  it('redirects moderator to dashboard', async () => {
    const { createClient } = vi.mocked(await import('@/lib/supabase/server'))
    ;(createClient as any).mockResolvedValueOnce({
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: { id: 'u1', app_metadata: { role: 'moderator' } } },
          error: null,
        }),
      },
      from: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          order: vi.fn().mockResolvedValue({ data: [], error: null }),
        }),
      }),
    })
    try {
      await TrendsPage()
    } catch {
      // redirect throws
    }
    expect(mockRedirect).toHaveBeenCalledWith('/dashboard')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/trends-page.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/app/trends/page.tsx
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { TrendsDashboard } from '@/components/trends/trends-dashboard'

export default async function TrendsPage() {
  const supabase = await createClient()
  const { data: { user }, error } = await supabase.auth.getUser()

  if (error || !user) {
    redirect('/login')
  }

  const role = user.app_metadata?.role
  if (role !== 'wav_admin' && role !== 'mg_client') {
    redirect('/dashboard')
  }

  const [studiesRes, daysRes] = await Promise.all([
    supabase.from('focus_groups').select('id, quarter').order('quarter'),
    supabase.from('days').select('id, focus_group_id, day_number, date').order('date'),
  ])

  const studies = (studiesRes.data ?? []).map((fg) => ({
    id: fg.id,
    name: fg.quarter,
  }))

  const days = (daysRes.data ?? []).map((d) => ({
    id: d.id,
    studyId: d.focus_group_id,
    name: `Día ${d.day_number}`,
    date: d.date,
  }))

  return <TrendsDashboard studies={studies} days={days} />
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/trends-page.test.tsx`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/app/trends/page.tsx tests/unit/trends/trends-page.test.tsx
git commit -m "feat: add /trends page with auth and role guard"
```

---

### Task 11: Nav Link + Locale Keys

**Files:**
- Modify: `src/components/layout/nav.tsx`
- Modify: `src/config/locales/en-US.json`
- Modify: `src/config/locales/es-CL.json`
- Test: `tests/unit/trends/nav-trends-link.test.tsx`

**Context:** Add a "Trends" link to the navigation sidebar, visible only to `wav_admin` and `mg_client` roles. Add all locale keys for the trends feature.

- [ ] **Step 1: Read the nav component to understand structure**

Run: `cat src/components/layout/nav.tsx` — understand how nav links are defined, how role-based visibility works, and where to add the Trends link.

- [ ] **Step 2: Write the failing test**

```typescript
// tests/unit/trends/nav-trends-link.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

vi.mock('@/hooks/use-label', () => ({
  useLabel: vi.fn().mockReturnValue((key: string) => {
    const labels: Record<string, string> = {
      'nav.trends': 'Tendencias',
      'nav.dashboard': 'Panel',
      'nav.sessions': 'Sesiones',
    }
    return labels[key] ?? key
  }),
}))

// NOTE: This test will need the actual nav import and props pattern after reading the file.
// The subagent should read nav.tsx first, then write this test to match the actual component API.

describe('Nav trends link', () => {
  it('shows Trends link for mg_client', () => {
    // Test that the nav renders a link with text "Tendencias" when role is mg_client
    // Implementation depends on actual nav component structure — subagent reads nav.tsx first
    expect(true).toBe(true) // placeholder — subagent replaces with real test
  })
})
```

- [ ] **Step 3: Add locale keys to both locale files**

Add to `src/config/locales/en-US.json`:
```json
"trends.title": "Cross-Session Trends",
"trends.topic_frequency": "Topic Frequency",
"trends.action_tracker": "Action Plan Progress",
"trends.cross_session_table": "Session Comparison",
"trends.col_session": "Session",
"trends.col_date": "Date",
"trends.col_participants": "Participants",
"trends.col_verbatims": "Verbatims",
"trends.col_sentiment": "Sentiment",
"trends.col_top_topic": "Top Topic",
"trends.col_barriers": "Barriers",
"trends.col_actions": "Actions",
"trends.status_done": "Done",
"trends.status_in_progress": "In Progress",
"trends.status_pending": "Pending"
```

Add to `src/config/locales/es-CL.json`:
```json
"trends.title": "Tendencias entre Sesiones",
"trends.topic_frequency": "Frecuencia por Tema",
"trends.action_tracker": "Progreso Planes de Acción",
"trends.cross_session_table": "Comparación de Sesiones",
"trends.col_session": "Sesión",
"trends.col_date": "Fecha",
"trends.col_participants": "Participantes",
"trends.col_verbatims": "Verbatims",
"trends.col_sentiment": "Sentimiento",
"trends.col_top_topic": "Tema Principal",
"trends.col_barriers": "Barreras",
"trends.col_actions": "Acciones",
"trends.status_done": "Completado",
"trends.status_in_progress": "En Progreso",
"trends.status_pending": "Pendiente"
```

- [ ] **Step 4: Add Trends link to nav** — read `nav.tsx`, add a TrendingUp icon link to `/trends` visible for `wav_admin` and `mg_client` roles.

- [ ] **Step 5: Run tests to verify**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/nav-trends-link.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/components/layout/nav.tsx src/config/locales/en-US.json src/config/locales/es-CL.json tests/unit/trends/nav-trends-link.test.tsx
git commit -m "feat: add trends nav link and locale keys"
```

---

### Task 12: Full Test Run + Fixes

**Files:**
- All test files
- Any files needing fixes

- [ ] **Step 1: Run all trends tests**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/trends/`
Expected: All trends tests pass

- [ ] **Step 2: Run full test suite**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run`
Expected: All tests pass (220+)

- [ ] **Step 3: Run TypeScript check**

Run: `cd /Users/fede/projects/wav-intelligence && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 4: Fix any failures** — read error output, fix issues, re-run until green.

- [ ] **Step 5: Commit fixes if any**

```bash
cd /Users/fede/projects/wav-intelligence
git add -A
git commit -m "fix: resolve test and type errors in trends module"
```
