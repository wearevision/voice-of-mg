# Action Plans Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the basic action plans card list in the session detail tab with a full-featured action plans management interface — sortable table, status updates, category/cost badges, inline editing, and a cross-session action plans overview page.

**Architecture:** Extract the existing inline action plans tab into dedicated components. Add CRUD API routes for action plans with status transitions. Build a cross-session `/action-plans` page showing all action plans across sessions with filtering. mg_client can update status; wav_admin has full CRUD.

**Tech Stack:** Next.js 16 (App Router), Supabase (RLS), shadcn/ui (Table, Badge, Select, Dialog), Vitest

---

## File Structure

```
src/
├── types/
│   └── action-plan.ts                        ← ActionPlan interface + enums
├── app/
│   ├── api/
│   │   ├── sessions/[id]/action-plans/
│   │   │   └── route.ts                      ← GET list + POST create
│   │   └── action-plans/[id]/
│   │       └── route.ts                      ← PATCH update + DELETE
│   └── action-plans/
│       └── page.tsx                          ← Cross-session overview (server)
├── components/
│   └── action-plans/
│       ├── action-plan-table.tsx             ← Sortable table with inline status select
│       ├── action-plan-card.tsx              ← Card view for single action plan detail
│       ├── action-plan-filters.tsx           ← Status + category filter bar
│       └── action-plans-overview.tsx         ← Client orchestrator for /action-plans page
├── hooks/
│   └── use-action-plans.ts                  ← Client hook: fetch, update status, delete
└── config/locales/
    ├── en-US.json                           ← +20 locale keys
    └── es-CL.json                           ← +20 locale keys
```

**Existing files modified:**
- `src/app/sessions/[id]/page.tsx` — replace inline action plans cards with `ActionPlanTable` component
- `src/components/layout/nav.tsx` — add Action Plans nav link
- `src/config/locales/en-US.json` — add `action_plans.*` locale keys
- `src/config/locales/es-CL.json` — add `action_plans.*` locale keys

---

### Task 1: ActionPlan Types

**Files:**
- Create: `src/types/action-plan.ts`
- Test: `tests/unit/action-plans/types.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/action-plans/types.test.ts
import { describe, it, expect } from 'vitest'
import type {
  ActionPlan,
  ActionCategory,
  ActionStatus,
  CostEstimate,
} from '@/types/action-plan'
import {
  CATEGORY_LABELS,
  STATUS_LABELS,
  COST_LABELS,
  CATEGORY_COLORS,
  STATUS_COLORS,
} from '@/types/action-plan'

describe('ActionPlan types', () => {
  it('ActionPlan has all required fields', () => {
    const plan: ActionPlan = {
      id: 'ap1',
      sessionId: 's1',
      sessionName: 'Sesión 1',
      category: 'quick_win',
      title: 'Mejorar postventa',
      description: 'Capacitar equipo de postventa',
      aiReasoning: 'Basado en análisis de verbatims...',
      impactScore: 8,
      costEstimate: 'low',
      cognitiveLoad: 'medium',
      timeEstimate: '2 semanas',
      status: 'pending',
      assignedTo: null,
      createdAt: '2026-01-15T00:00:00Z',
      updatedAt: '2026-01-15T00:00:00Z',
    }
    expect(plan.impactScore).toBe(8)
    expect(plan.status).toBe('pending')
  })

  it('CATEGORY_LABELS maps all categories', () => {
    expect(CATEGORY_LABELS.quick_win).toBeDefined()
    expect(CATEGORY_LABELS.strategic).toBeDefined()
    expect(CATEGORY_LABELS.monitor).toBeDefined()
  })

  it('STATUS_LABELS maps all statuses', () => {
    expect(STATUS_LABELS.pending).toBeDefined()
    expect(STATUS_LABELS.in_progress).toBeDefined()
    expect(STATUS_LABELS.done).toBeDefined()
  })

  it('CATEGORY_COLORS maps all categories', () => {
    expect(CATEGORY_COLORS.quick_win).toContain('emerald')
    expect(CATEGORY_COLORS.strategic).toContain('indigo')
    expect(CATEGORY_COLORS.monitor).toContain('zinc')
  })

  it('STATUS_COLORS maps all statuses', () => {
    expect(STATUS_COLORS.pending).toContain('amber')
    expect(STATUS_COLORS.in_progress).toContain('blue')
    expect(STATUS_COLORS.done).toContain('emerald')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/action-plans/types.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/types/action-plan.ts

export type ActionCategory = 'quick_win' | 'strategic' | 'monitor'
export type ActionStatus = 'pending' | 'in_progress' | 'done'
export type CostEstimate = 'low' | 'medium' | 'high'

export interface ActionPlan {
  id: string
  sessionId: string | null
  sessionName: string | null
  category: ActionCategory
  title: string
  description: string | null
  aiReasoning: string | null
  impactScore: number
  costEstimate: CostEstimate | null
  cognitiveLoad: CostEstimate | null
  timeEstimate: string | null
  status: ActionStatus
  assignedTo: string | null
  createdAt: string
  updatedAt: string
}

export const CATEGORY_LABELS: Record<ActionCategory, string> = {
  quick_win: 'Quick Win',
  strategic: 'Estratégico',
  monitor: 'Monitorear',
}

export const STATUS_LABELS: Record<ActionStatus, string> = {
  pending: 'Pendiente',
  in_progress: 'En Progreso',
  done: 'Completado',
}

export const COST_LABELS: Record<CostEstimate, string> = {
  low: 'Bajo',
  medium: 'Medio',
  high: 'Alto',
}

export const CATEGORY_COLORS: Record<ActionCategory, string> = {
  quick_win: 'bg-emerald-500/20 text-emerald-400',
  strategic: 'bg-indigo-500/20 text-indigo-400',
  monitor: 'bg-zinc-700 text-zinc-400',
}

export const STATUS_COLORS: Record<ActionStatus, string> = {
  pending: 'bg-amber-500/20 text-amber-400',
  in_progress: 'bg-blue-500/20 text-blue-400',
  done: 'bg-emerald-500/20 text-emerald-400',
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/action-plans/types.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/types/action-plan.ts tests/unit/action-plans/types.test.ts
git commit -m "feat: add action plan types and display constants"
```

---

### Task 2: Session Action Plans API (GET + POST)

**Files:**
- Create: `src/app/api/sessions/[id]/action-plans/route.ts`
- Test: `tests/unit/action-plans/session-route.test.ts`

**Context:** GET returns action plans for a session with session name from join. POST creates a new action plan (wav_admin only). Both use auth guard. Response maps snake_case DB columns to camelCase.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/action-plans/session-route.test.ts
import { describe, it, expect, vi } from 'vitest'

const mockActionPlans = [
  {
    id: 'ap1',
    session_id: 's1',
    category: 'quick_win',
    title: 'Mejorar postventa',
    description: 'Capacitar equipo',
    ai_reasoning: 'Basado en verbatims...',
    impact_score: 8,
    cost_estimate: 'low',
    cognitive_load: 'medium',
    time_estimate: '2 semanas',
    status: 'pending',
    assigned_to: null,
    created_at: '2026-01-15T00:00:00Z',
    updated_at: '2026-01-15T00:00:00Z',
    sessions: { name: 'Sesión 1' },
  },
]

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: { getUser: vi.fn().mockResolvedValue({ data: { user: { id: 'u1', app_metadata: { role: 'wav_admin' } } }, error: null }) },
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          order: vi.fn().mockResolvedValue({ data: mockActionPlans, error: null }),
        }),
      }),
      insert: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({ data: mockActionPlans[0], error: null }),
        }),
      }),
    }),
  }),
}))

import { GET, POST } from '@/app/api/sessions/[id]/action-plans/route'

describe('GET /api/sessions/[id]/action-plans', () => {
  it('returns action plans with camelCase fields', async () => {
    const req = new Request('http://localhost/api/sessions/s1/action-plans')
    const res = await GET(req as any, { params: Promise.resolve({ id: 's1' }) })
    expect(res.status).toBe(200)
    const json = await res.json()
    expect(json.actionPlans).toHaveLength(1)
    expect(json.actionPlans[0].impactScore).toBe(8)
    expect(json.actionPlans[0].costEstimate).toBe('low')
    expect(json.actionPlans[0].sessionName).toBe('Sesión 1')
  })
})

describe('POST /api/sessions/[id]/action-plans', () => {
  it('creates a new action plan', async () => {
    const body = { category: 'quick_win', title: 'Test', impactScore: 5 }
    const req = new Request('http://localhost/api/sessions/s1/action-plans', {
      method: 'POST',
      body: JSON.stringify(body),
    })
    const res = await POST(req as any, { params: Promise.resolve({ id: 's1' }) })
    expect(res.status).toBe(201)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/action-plans/session-route.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/app/api/sessions/[id]/action-plans/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import type { ActionPlan } from '@/types/action-plan'

interface RouteContext {
  params: Promise<{ id: string }>
}

interface ActionPlanRow {
  id: string
  session_id: string
  category: string
  title: string
  description: string | null
  ai_reasoning: string | null
  impact_score: number
  cost_estimate: string | null
  cognitive_load: string | null
  time_estimate: string | null
  status: string
  assigned_to: string | null
  created_at: string
  updated_at: string
  sessions: { name: string } | null
}

function mapRow(row: ActionPlanRow): ActionPlan {
  return {
    id: row.id,
    sessionId: row.session_id,
    sessionName: row.sessions?.name ?? null,
    category: row.category as ActionPlan['category'],
    title: row.title,
    description: row.description,
    aiReasoning: row.ai_reasoning,
    impactScore: row.impact_score,
    costEstimate: row.cost_estimate as ActionPlan['costEstimate'],
    cognitiveLoad: row.cognitive_load as ActionPlan['cognitiveLoad'],
    timeEstimate: row.time_estimate,
    status: row.status as ActionPlan['status'],
    assignedTo: row.assigned_to,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  }
}

export async function GET(req: NextRequest, ctx: RouteContext) {
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const { id: sessionId } = await ctx.params

  const { data, error } = await supabase
    .from('action_plans')
    .select('*, sessions(name)')
    .eq('session_id', sessionId)
    .order('impact_score', { ascending: false })

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  const actionPlans = (data ?? []).map((row) => mapRow(row as unknown as ActionPlanRow))
  return NextResponse.json({ actionPlans })
}

export async function POST(req: NextRequest, ctx: RouteContext) {
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const role = user.app_metadata?.role
  if (role !== 'wav_admin') {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 })
  }

  const { id: sessionId } = await ctx.params
  const body = await req.json()

  const { data, error } = await supabase
    .from('action_plans')
    .insert({
      session_id: sessionId,
      category: body.category,
      title: body.title,
      description: body.description ?? null,
      ai_reasoning: body.aiReasoning ?? null,
      impact_score: body.impactScore ?? 5,
      cost_estimate: body.costEstimate ?? null,
      cognitive_load: body.cognitiveLoad ?? null,
      time_estimate: body.timeEstimate ?? null,
      status: 'pending',
    })
    .select()
    .single()

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ actionPlan: data }, { status: 201 })
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/action-plans/session-route.test.ts`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/app/api/sessions/[id]/action-plans/route.ts tests/unit/action-plans/session-route.test.ts
git commit -m "feat: add session action plans API (GET + POST)"
```

---

### Task 3: Action Plan CRUD API (PATCH + DELETE)

**Files:**
- Create: `src/app/api/action-plans/[id]/route.ts`
- Test: `tests/unit/action-plans/crud-route.test.ts`

**Context:** PATCH updates an action plan (status, assigned_to, etc). DELETE removes it. Both check auth. mg_client can only update status; wav_admin can update any field or delete.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/action-plans/crud-route.test.ts
import { describe, it, expect, vi } from 'vitest'

const mockUpdate = vi.fn().mockReturnValue({
  eq: vi.fn().mockReturnValue({
    select: vi.fn().mockReturnValue({
      single: vi.fn().mockResolvedValue({ data: { id: 'ap1', status: 'in_progress' }, error: null }),
    }),
  }),
})

const mockDelete = vi.fn().mockReturnValue({
  eq: vi.fn().mockResolvedValue({ error: null }),
})

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: {
      getUser: vi.fn().mockResolvedValue({
        data: { user: { id: 'u1', app_metadata: { role: 'wav_admin' } } },
        error: null,
      }),
    },
    from: vi.fn().mockReturnValue({
      update: mockUpdate,
      delete: mockDelete,
    }),
  }),
}))

import { PATCH, DELETE } from '@/app/api/action-plans/[id]/route'

describe('PATCH /api/action-plans/[id]', () => {
  it('updates action plan status', async () => {
    const req = new Request('http://localhost/api/action-plans/ap1', {
      method: 'PATCH',
      body: JSON.stringify({ status: 'in_progress' }),
    })
    const res = await PATCH(req as any, { params: Promise.resolve({ id: 'ap1' }) })
    expect(res.status).toBe(200)
  })
})

describe('DELETE /api/action-plans/[id]', () => {
  it('deletes action plan for wav_admin', async () => {
    const req = new Request('http://localhost/api/action-plans/ap1', { method: 'DELETE' })
    const res = await DELETE(req as any, { params: Promise.resolve({ id: 'ap1' }) })
    expect(res.status).toBe(200)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/action-plans/crud-route.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/app/api/action-plans/[id]/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

interface RouteContext {
  params: Promise<{ id: string }>
}

export async function PATCH(req: NextRequest, ctx: RouteContext) {
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const { id } = await ctx.params
  const body = await req.json()
  const role = user.app_metadata?.role

  const updateFields: Record<string, unknown> = { updated_at: new Date().toISOString() }

  if (body.status) updateFields.status = body.status
  if (role === 'wav_admin') {
    if (body.title !== undefined) updateFields.title = body.title
    if (body.description !== undefined) updateFields.description = body.description
    if (body.category !== undefined) updateFields.category = body.category
    if (body.impactScore !== undefined) updateFields.impact_score = body.impactScore
    if (body.costEstimate !== undefined) updateFields.cost_estimate = body.costEstimate
    if (body.assignedTo !== undefined) updateFields.assigned_to = body.assignedTo
    if (body.timeEstimate !== undefined) updateFields.time_estimate = body.timeEstimate
  }

  const { data, error } = await supabase
    .from('action_plans')
    .update(updateFields)
    .eq('id', id)
    .select()
    .single()

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ actionPlan: data })
}

export async function DELETE(req: NextRequest, ctx: RouteContext) {
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const role = user.app_metadata?.role
  if (role !== 'wav_admin') {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 })
  }

  const { id } = await ctx.params

  const { error } = await supabase
    .from('action_plans')
    .delete()
    .eq('id', id)

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ success: true })
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/action-plans/crud-route.test.ts`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/app/api/action-plans/[id]/route.ts tests/unit/action-plans/crud-route.test.ts
git commit -m "feat: add action plan CRUD API (PATCH + DELETE)"
```

---

### Task 4: useActionPlans Hook

**Files:**
- Create: `src/hooks/use-action-plans.ts`
- Test: `tests/unit/action-plans/use-action-plans.test.tsx`

**Context:** Client hook that fetches action plans for a session (or all sessions), provides `updateStatus` and `deleteActionPlan` mutations that optimistically update the local state and call the API.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/action-plans/use-action-plans.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useActionPlans } from '@/hooks/use-action-plans'

const mockFetch = vi.fn()
global.fetch = mockFetch

describe('useActionPlans', () => {
  beforeEach(() => {
    mockFetch.mockReset()
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        actionPlans: [
          { id: 'ap1', title: 'Test', status: 'pending', category: 'quick_win', impactScore: 8 },
        ],
      }),
    })
  })

  it('fetches action plans for a session', async () => {
    renderHook(() => useActionPlans('s1'))
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/sessions/s1/action-plans')
    })
  })

  it('fetches all action plans when no sessionId', async () => {
    renderHook(() => useActionPlans(null))
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/action-plans')
    })
  })

  it('starts with loading true', () => {
    const { result } = renderHook(() => useActionPlans('s1'))
    expect(result.current.loading).toBe(true)
  })

  it('updateStatus calls PATCH endpoint', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ actionPlans: [{ id: 'ap1', status: 'pending' }] }),
    })
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ actionPlan: { id: 'ap1', status: 'done' } }),
    })

    const { result } = renderHook(() => useActionPlans('s1'))
    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.updateStatus('ap1', 'done')
    })

    expect(mockFetch).toHaveBeenCalledWith('/api/action-plans/ap1', expect.objectContaining({
      method: 'PATCH',
    }))
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/action-plans/use-action-plans.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/hooks/use-action-plans.ts
'use client'

import { useState, useEffect, useCallback } from 'react'
import type { ActionPlan } from '@/types/action-plan'

interface UseActionPlansResult {
  actionPlans: ActionPlan[]
  loading: boolean
  error: string | null
  updateStatus: (id: string, status: string) => Promise<void>
  deleteActionPlan: (id: string) => Promise<void>
  refresh: () => Promise<void>
}

export function useActionPlans(sessionId: string | null): UseActionPlansResult {
  const [actionPlans, setActionPlans] = useState<ActionPlan[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchPlans = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const url = sessionId
        ? `/api/sessions/${sessionId}/action-plans`
        : '/api/action-plans'
      const res = await fetch(url)
      const json = await res.json()
      setActionPlans(json.actionPlans ?? [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load action plans')
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  useEffect(() => { fetchPlans() }, [fetchPlans])

  const updateStatus = useCallback(async (id: string, status: string) => {
    setActionPlans((prev) =>
      prev.map((ap) => (ap.id === id ? { ...ap, status: status as ActionPlan['status'] } : ap))
    )
    await fetch(`/api/action-plans/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
  }, [])

  const deleteActionPlan = useCallback(async (id: string) => {
    setActionPlans((prev) => prev.filter((ap) => ap.id !== id))
    await fetch(`/api/action-plans/${id}`, { method: 'DELETE' })
  }, [])

  return { actionPlans, loading, error, updateStatus, deleteActionPlan, refresh: fetchPlans }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/action-plans/use-action-plans.test.tsx`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/hooks/use-action-plans.ts tests/unit/action-plans/use-action-plans.test.tsx
git commit -m "feat: add useActionPlans hook with optimistic updates"
```

---

### Task 5: ActionPlanTable Component

**Files:**
- Create: `src/components/action-plans/action-plan-table.tsx`
- Test: `tests/unit/action-plans/action-plan-table.test.tsx`

**Context:** Sortable table displaying action plans. Each row shows: category badge, title, impact score bar, cost estimate badge, status Select dropdown (for inline status update), time estimate. Clicking a row expands description + AI reasoning.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/action-plans/action-plan-table.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ActionPlanTable } from '@/components/action-plans/action-plan-table'
import type { ActionPlan } from '@/types/action-plan'

const mockPlans: ActionPlan[] = [
  {
    id: 'ap1', sessionId: 's1', sessionName: 'Sesión 1', category: 'quick_win',
    title: 'Mejorar postventa', description: 'Capacitar equipo', aiReasoning: 'Análisis...',
    impactScore: 8, costEstimate: 'low', cognitiveLoad: 'medium', timeEstimate: '2 semanas',
    status: 'pending', assignedTo: null, createdAt: '2026-01-15T00:00:00Z', updatedAt: '2026-01-15T00:00:00Z',
  },
  {
    id: 'ap2', sessionId: 's1', sessionName: 'Sesión 1', category: 'strategic',
    title: 'Rediseñar infotainment', description: null, aiReasoning: null,
    impactScore: 6, costEstimate: 'high', cognitiveLoad: 'high', timeEstimate: '3 meses',
    status: 'in_progress', assignedTo: null, createdAt: '2026-01-15T00:00:00Z', updatedAt: '2026-01-15T00:00:00Z',
  },
]

const mockLabel = (key: string) => key
const mockOnStatusChange = vi.fn()

describe('ActionPlanTable', () => {
  it('renders all action plans', () => {
    render(<ActionPlanTable plans={mockPlans} label={mockLabel} onStatusChange={mockOnStatusChange} />)
    expect(screen.getByText('Mejorar postventa')).toBeDefined()
    expect(screen.getByText('Rediseñar infotainment')).toBeDefined()
  })

  it('displays category badges', () => {
    render(<ActionPlanTable plans={mockPlans} label={mockLabel} onStatusChange={mockOnStatusChange} />)
    expect(screen.getByText('Quick Win')).toBeDefined()
    expect(screen.getByText('Estratégico')).toBeDefined()
  })

  it('displays impact scores', () => {
    render(<ActionPlanTable plans={mockPlans} label={mockLabel} onStatusChange={mockOnStatusChange} />)
    expect(screen.getByText('8/10')).toBeDefined()
    expect(screen.getByText('6/10')).toBeDefined()
  })

  it('shows description on row expand', async () => {
    const user = userEvent.setup()
    render(<ActionPlanTable plans={mockPlans} label={mockLabel} onStatusChange={mockOnStatusChange} />)
    await user.click(screen.getByText('Mejorar postventa'))
    expect(screen.getByText('Capacitar equipo')).toBeDefined()
  })

  it('renders empty state when no plans', () => {
    render(<ActionPlanTable plans={[]} label={mockLabel} onStatusChange={mockOnStatusChange} />)
    expect(screen.getByText('action_plans.empty')).toBeDefined()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/action-plans/action-plan-table.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/components/action-plans/action-plan-table.tsx
'use client'

import { useState } from 'react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import type { ActionPlan } from '@/types/action-plan'
import { CATEGORY_LABELS, CATEGORY_COLORS, STATUS_COLORS, STATUS_LABELS, COST_LABELS } from '@/types/action-plan'

interface ActionPlanTableProps {
  plans: ActionPlan[]
  label: (key: string) => string
  onStatusChange: (id: string, status: string) => void
  showSession?: boolean
}

export function ActionPlanTable({ plans, label, onStatusChange, showSession = false }: ActionPlanTableProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  if (plans.length === 0) {
    return <p className="text-sm text-muted-foreground">{label('action_plans.empty')}</p>
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{label('action_plans.col_category')}</TableHead>
            <TableHead>{label('action_plans.col_title')}</TableHead>
            {showSession && <TableHead>{label('action_plans.col_session')}</TableHead>}
            <TableHead className="text-right">{label('action_plans.col_impact')}</TableHead>
            <TableHead>{label('action_plans.col_cost')}</TableHead>
            <TableHead>{label('action_plans.col_time')}</TableHead>
            <TableHead>{label('action_plans.col_status')}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {plans.map((plan) => (
            <>
              <TableRow
                key={plan.id}
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => setExpandedId(expandedId === plan.id ? null : plan.id)}
              >
                <TableCell>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${CATEGORY_COLORS[plan.category]}`}>
                    {CATEGORY_LABELS[plan.category]}
                  </span>
                </TableCell>
                <TableCell className="font-medium">{plan.title}</TableCell>
                {showSession && <TableCell className="text-muted-foreground text-sm">{plan.sessionName}</TableCell>}
                <TableCell className="text-right font-mono">{plan.impactScore}/10</TableCell>
                <TableCell>
                  {plan.costEstimate && (
                    <Badge variant="outline" className="text-xs">{COST_LABELS[plan.costEstimate]}</Badge>
                  )}
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">{plan.timeEstimate ?? '—'}</TableCell>
                <TableCell>
                  <select
                    className="bg-transparent text-xs border border-zinc-700 rounded px-2 py-1"
                    value={plan.status}
                    onChange={(e) => {
                      e.stopPropagation()
                      onStatusChange(plan.id, e.target.value)
                    }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <option value="pending">{STATUS_LABELS.pending}</option>
                    <option value="in_progress">{STATUS_LABELS.in_progress}</option>
                    <option value="done">{STATUS_LABELS.done}</option>
                  </select>
                </TableCell>
              </TableRow>
              {expandedId === plan.id && (
                <TableRow key={`${plan.id}-detail`}>
                  <TableCell colSpan={showSession ? 7 : 6} className="bg-muted/30">
                    <div className="py-2 space-y-2">
                      {plan.description && (
                        <p className="text-sm text-muted-foreground">{plan.description}</p>
                      )}
                      {plan.aiReasoning && (
                        <div className="text-xs text-muted-foreground/70 border-l-2 border-zinc-700 pl-3">
                          <span className="font-medium text-muted-foreground">{label('action_plans.ai_reasoning')}:</span> {plan.aiReasoning}
                        </div>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              )}
            </>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/action-plans/action-plan-table.test.tsx`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/components/action-plans/action-plan-table.tsx tests/unit/action-plans/action-plan-table.test.tsx
git commit -m "feat: add ActionPlanTable with inline status update and expand"
```

---

### Task 6: ActionPlanFilters Component

**Files:**
- Create: `src/components/action-plans/action-plan-filters.tsx`
- Test: `tests/unit/action-plans/action-plan-filters.test.tsx`

**Context:** Filter bar for the cross-session action plans page. Filters by status (all/pending/in_progress/done) and category (all/quick_win/strategic/monitor). Uses native HTML select elements matching the table's inline select pattern.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/action-plans/action-plan-filters.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ActionPlanFilters, filterActionPlans } from '@/components/action-plans/action-plan-filters'
import type { ActionPlan } from '@/types/action-plan'

const mockLabel = (key: string) => key

describe('filterActionPlans', () => {
  const plans: ActionPlan[] = [
    { id: '1', status: 'pending', category: 'quick_win', title: 'A' } as ActionPlan,
    { id: '2', status: 'done', category: 'strategic', title: 'B' } as ActionPlan,
    { id: '3', status: 'in_progress', category: 'quick_win', title: 'C' } as ActionPlan,
  ]

  it('returns all when no filters', () => {
    expect(filterActionPlans(plans, null, null)).toHaveLength(3)
  })

  it('filters by status', () => {
    expect(filterActionPlans(plans, 'pending', null)).toHaveLength(1)
  })

  it('filters by category', () => {
    expect(filterActionPlans(plans, null, 'quick_win')).toHaveLength(2)
  })

  it('combines status and category filters', () => {
    expect(filterActionPlans(plans, 'pending', 'quick_win')).toHaveLength(1)
  })
})

describe('ActionPlanFilters', () => {
  it('renders status and category selects', () => {
    const onChange = vi.fn()
    render(<ActionPlanFilters statusFilter={null} categoryFilter={null} onStatusChange={onChange} onCategoryChange={onChange} label={mockLabel} />)
    expect(screen.getAllByRole('combobox')).toHaveLength(2)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/action-plans/action-plan-filters.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/components/action-plans/action-plan-filters.tsx
'use client'

import type { ActionPlan, ActionStatus, ActionCategory } from '@/types/action-plan'
import { STATUS_LABELS, CATEGORY_LABELS } from '@/types/action-plan'

interface ActionPlanFiltersProps {
  statusFilter: ActionStatus | null
  categoryFilter: ActionCategory | null
  onStatusChange: (status: ActionStatus | null) => void
  onCategoryChange: (category: ActionCategory | null) => void
  label: (key: string) => string
}

export function filterActionPlans(
  plans: ActionPlan[],
  statusFilter: ActionStatus | null,
  categoryFilter: ActionCategory | null,
): ActionPlan[] {
  return plans.filter((plan) => {
    if (statusFilter && plan.status !== statusFilter) return false
    if (categoryFilter && plan.category !== categoryFilter) return false
    return true
  })
}

export function ActionPlanFilters({
  statusFilter,
  categoryFilter,
  onStatusChange,
  onCategoryChange,
  label,
}: ActionPlanFiltersProps) {
  return (
    <div className="flex items-center gap-3">
      <select
        className="bg-transparent text-sm border border-zinc-700 rounded px-3 py-1.5"
        value={statusFilter ?? ''}
        onChange={(e) => onStatusChange((e.target.value || null) as ActionStatus | null)}
      >
        <option value="">{label('action_plans.filter_all_statuses')}</option>
        {(Object.entries(STATUS_LABELS) as [ActionStatus, string][]).map(([value, text]) => (
          <option key={value} value={value}>{text}</option>
        ))}
      </select>

      <select
        className="bg-transparent text-sm border border-zinc-700 rounded px-3 py-1.5"
        value={categoryFilter ?? ''}
        onChange={(e) => onCategoryChange((e.target.value || null) as ActionCategory | null)}
      >
        <option value="">{label('action_plans.filter_all_categories')}</option>
        {(Object.entries(CATEGORY_LABELS) as [ActionCategory, string][]).map(([value, text]) => (
          <option key={value} value={value}>{text}</option>
        ))}
      </select>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/action-plans/action-plan-filters.test.tsx`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/components/action-plans/action-plan-filters.tsx tests/unit/action-plans/action-plan-filters.test.tsx
git commit -m "feat: add action plan filters with status and category"
```

---

### Task 7: ActionPlansOverview Client Component

**Files:**
- Create: `src/components/action-plans/action-plans-overview.tsx`
- Test: `tests/unit/action-plans/action-plans-overview.test.tsx`

**Context:** Client orchestrator for the cross-session `/action-plans` page. Uses `useActionPlans(null)` to load all plans, renders `ActionPlanFilters` + `ActionPlanTable` with `showSession={true}`. Summary stats at top: total plans, done count, completion percentage.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/action-plans/action-plans-overview.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ActionPlansOverview } from '@/components/action-plans/action-plans-overview'

vi.mock('@/hooks/use-action-plans', () => ({
  useActionPlans: vi.fn().mockReturnValue({
    actionPlans: [
      { id: 'ap1', title: 'Test', status: 'done', category: 'quick_win', impactScore: 8, sessionName: 'Sesión 1' },
      { id: 'ap2', title: 'Test2', status: 'pending', category: 'strategic', impactScore: 6, sessionName: 'Sesión 2' },
    ],
    loading: false,
    error: null,
    updateStatus: vi.fn(),
    deleteActionPlan: vi.fn(),
    refresh: vi.fn(),
  }),
}))

vi.mock('@/hooks/use-label', () => ({
  useLabel: vi.fn().mockReturnValue((key: string) => key),
}))

describe('ActionPlansOverview', () => {
  it('renders page title', () => {
    render(<ActionPlansOverview />)
    expect(screen.getByText('action_plans.title')).toBeDefined()
  })

  it('shows summary stats', () => {
    render(<ActionPlansOverview />)
    expect(screen.getByText('2')).toBeDefined() // total
    expect(screen.getByText('1')).toBeDefined() // done
    expect(screen.getByText('50%')).toBeDefined() // completion rate
  })

  it('renders action plan table with session column', () => {
    render(<ActionPlansOverview />)
    expect(screen.getByText('Test')).toBeDefined()
    expect(screen.getByText('Test2')).toBeDefined()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/action-plans/action-plans-overview.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/components/action-plans/action-plans-overview.tsx
'use client'

import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { useLabel } from '@/hooks/use-label'
import { useActionPlans } from '@/hooks/use-action-plans'
import { ActionPlanTable } from './action-plan-table'
import { ActionPlanFilters, filterActionPlans } from './action-plan-filters'
import type { ActionStatus, ActionCategory } from '@/types/action-plan'

export function ActionPlansOverview() {
  const label = useLabel()
  const { actionPlans, loading, updateStatus } = useActionPlans(null)
  const [statusFilter, setStatusFilter] = useState<ActionStatus | null>(null)
  const [categoryFilter, setCategoryFilter] = useState<ActionCategory | null>(null)

  const filtered = filterActionPlans(actionPlans, statusFilter, categoryFilter)
  const doneCount = actionPlans.filter((p) => p.status === 'done').length
  const completionRate = actionPlans.length > 0
    ? Math.round((doneCount / actionPlans.length) * 100)
    : 0

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-foreground">{label('action_plans.title')}</h1>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">{actionPlans.length}</p>
            <p className="text-xs text-muted-foreground">{label('action_plans.stat_total')}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold text-emerald-400">{doneCount}</p>
            <p className="text-xs text-muted-foreground">{label('action_plans.stat_done')}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">{completionRate}%</p>
            <p className="text-xs text-muted-foreground">{label('action_plans.stat_completion')}</p>
          </CardContent>
        </Card>
      </div>

      <ActionPlanFilters
        statusFilter={statusFilter}
        categoryFilter={categoryFilter}
        onStatusChange={setStatusFilter}
        onCategoryChange={setCategoryFilter}
        label={label}
      />

      {loading ? (
        <p className="text-sm text-muted-foreground">{label('dashboard.loading')}</p>
      ) : (
        <ActionPlanTable
          plans={filtered}
          label={label}
          onStatusChange={updateStatus}
          showSession
        />
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/action-plans/action-plans-overview.test.tsx`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/components/action-plans/action-plans-overview.tsx tests/unit/action-plans/action-plans-overview.test.tsx
git commit -m "feat: add ActionPlansOverview with stats and filters"
```

---

### Task 8: Cross-Session Action Plans Page + All Plans API

**Files:**
- Create: `src/app/action-plans/page.tsx`
- Create: `src/app/api/action-plans/route.ts`
- Test: `tests/unit/action-plans/page.test.tsx`
- Test: `tests/unit/action-plans/all-route.test.ts`

**Context:** Server component page (auth + role guard, wav_admin and mg_client only). Also need a GET /api/action-plans endpoint that returns all action plans across sessions (used by useActionPlans(null)).

- [ ] **Step 1: Write the API test**

```typescript
// tests/unit/action-plans/all-route.test.ts
import { describe, it, expect, vi } from 'vitest'

const mockAllPlans = [
  { id: 'ap1', session_id: 's1', category: 'quick_win', title: 'Test', status: 'pending',
    impact_score: 8, cost_estimate: 'low', cognitive_load: null, time_estimate: '2w',
    description: null, ai_reasoning: null, assigned_to: null,
    created_at: '2026-01-15', updated_at: '2026-01-15',
    sessions: { name: 'Sesión 1' } },
]

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: { getUser: vi.fn().mockResolvedValue({ data: { user: { id: 'u1' } }, error: null }) },
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockReturnValue({
        order: vi.fn().mockResolvedValue({ data: mockAllPlans, error: null }),
      }),
    }),
  }),
}))

import { GET } from '@/app/api/action-plans/route'

describe('GET /api/action-plans', () => {
  it('returns all action plans with session names', async () => {
    const req = new Request('http://localhost/api/action-plans')
    const res = await GET(req as any)
    expect(res.status).toBe(200)
    const json = await res.json()
    expect(json.actionPlans).toHaveLength(1)
    expect(json.actionPlans[0].sessionName).toBe('Sesión 1')
  })
})
```

- [ ] **Step 2: Write the page test**

```typescript
// tests/unit/action-plans/page.test.tsx
import { describe, it, expect, vi } from 'vitest'

const mockRedirect = vi.fn()
vi.mock('next/navigation', () => ({
  redirect: (...args: unknown[]) => { mockRedirect(...args); throw new Error('NEXT_REDIRECT') },
}))

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: { getUser: vi.fn().mockResolvedValue({ data: { user: { id: 'u1', app_metadata: { role: 'mg_client' } } }, error: null }) },
  }),
}))

vi.mock('@/components/action-plans/action-plans-overview', () => ({
  ActionPlansOverview: () => <div data-testid="overview" />,
}))

import ActionPlansPage from '@/app/action-plans/page'

describe('ActionPlansPage', () => {
  it('renders overview for mg_client', async () => {
    const { render, screen } = await import('@testing-library/react')
    const page = await ActionPlansPage()
    render(page)
    expect(screen.getByTestId('overview')).toBeDefined()
  })

  it('redirects moderator', async () => {
    const { createClient } = vi.mocked(await import('@/lib/supabase/server'))
    ;(createClient as any).mockResolvedValueOnce({
      auth: { getUser: vi.fn().mockResolvedValue({ data: { user: { id: 'u1', app_metadata: { role: 'moderator' } } }, error: null }) },
    })
    try { await ActionPlansPage() } catch { /* redirect throws */ }
    expect(mockRedirect).toHaveBeenCalledWith('/dashboard')
  })
})
```

- [ ] **Step 3: Write both implementations**

```typescript
// src/app/api/action-plans/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import type { ActionPlan } from '@/types/action-plan'

export async function GET(req: NextRequest) {
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const { data, error } = await supabase
    .from('action_plans')
    .select('*, sessions(name)')
    .order('impact_score', { ascending: false })

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  const actionPlans: ActionPlan[] = (data ?? []).map((row: any) => ({
    id: row.id,
    sessionId: row.session_id,
    sessionName: row.sessions?.name ?? null,
    category: row.category,
    title: row.title,
    description: row.description,
    aiReasoning: row.ai_reasoning,
    impactScore: row.impact_score,
    costEstimate: row.cost_estimate,
    cognitiveLoad: row.cognitive_load,
    timeEstimate: row.time_estimate,
    status: row.status,
    assignedTo: row.assigned_to,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  }))

  return NextResponse.json({ actionPlans })
}
```

```typescript
// src/app/action-plans/page.tsx
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { ActionPlansOverview } from '@/components/action-plans/action-plans-overview'

export default async function ActionPlansPage() {
  const supabase = await createClient()
  const { data: { user }, error } = await supabase.auth.getUser()

  if (error || !user) redirect('/login')

  const role = user.app_metadata?.role
  if (role !== 'wav_admin' && role !== 'mg_client') redirect('/dashboard')

  return <ActionPlansOverview />
}
```

- [ ] **Step 4: Run tests to verify**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/action-plans/all-route.test.ts tests/unit/action-plans/page.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/app/api/action-plans/route.ts src/app/action-plans/page.tsx tests/unit/action-plans/all-route.test.ts tests/unit/action-plans/page.test.tsx
git commit -m "feat: add cross-session action plans page and API"
```

---

### Task 9: Update Session Detail Tab

**Files:**
- Modify: `src/app/sessions/[id]/page.tsx`
- Test: `tests/unit/action-plans/session-tab.test.tsx`

**Context:** Replace the inline action plans card list (lines 172-208 of `src/app/sessions/[id]/page.tsx`) with the new `ActionPlanTable` component. The session detail page is a server component, so we need to wrap the table in a thin client component that passes server-fetched data.

- [ ] **Step 1: Write the test**

```typescript
// tests/unit/action-plans/session-tab.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SessionActionPlans } from '@/components/action-plans/session-action-plans'
import type { ActionPlan } from '@/types/action-plan'

vi.mock('@/hooks/use-label', () => ({
  useLabel: vi.fn().mockReturnValue((key: string) => key),
}))

const mockPlans: ActionPlan[] = [
  {
    id: 'ap1', sessionId: 's1', sessionName: 'Sesión 1', category: 'quick_win',
    title: 'Mejorar postventa', description: null, aiReasoning: null,
    impactScore: 8, costEstimate: 'low', cognitiveLoad: null, timeEstimate: '2w',
    status: 'pending', assignedTo: null, createdAt: '2026-01-15', updatedAt: '2026-01-15',
  },
]

describe('SessionActionPlans', () => {
  it('renders action plan table with plans', () => {
    render(<SessionActionPlans initialPlans={mockPlans} sessionId="s1" />)
    expect(screen.getByText('Mejorar postventa')).toBeDefined()
  })

  it('renders empty state when no plans', () => {
    render(<SessionActionPlans initialPlans={[]} sessionId="s1" />)
    expect(screen.getByText('action_plans.empty')).toBeDefined()
  })
})
```

- [ ] **Step 2: Create SessionActionPlans wrapper**

```typescript
// src/components/action-plans/session-action-plans.tsx
'use client'

import { useState } from 'react'
import { useLabel } from '@/hooks/use-label'
import { ActionPlanTable } from './action-plan-table'
import type { ActionPlan } from '@/types/action-plan'

interface SessionActionPlansProps {
  initialPlans: ActionPlan[]
  sessionId: string
}

export function SessionActionPlans({ initialPlans, sessionId }: SessionActionPlansProps) {
  const label = useLabel()
  const [plans, setPlans] = useState<ActionPlan[]>(initialPlans)

  const handleStatusChange = async (id: string, status: string) => {
    setPlans((prev) =>
      prev.map((p) => (p.id === id ? { ...p, status: status as ActionPlan['status'] } : p))
    )
    await fetch(`/api/action-plans/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
  }

  return <ActionPlanTable plans={plans} label={label} onStatusChange={handleStatusChange} />
}
```

- [ ] **Step 3: Update session detail page** — replace the inline action plans cards (lines 172-208) in `src/app/sessions/[id]/page.tsx` with:

```tsx
import { SessionActionPlans } from '@/components/action-plans/session-action-plans'
import type { ActionPlan } from '@/types/action-plan'

// ... in the data fetching section, map actionPlans to ActionPlan type:
const mappedActionPlans: ActionPlan[] = (actionPlans ?? []).map((ap) => ({
  id: ap.id,
  sessionId: sessionId,
  sessionName: session.name,
  category: ap.category as ActionPlan['category'],
  title: ap.title,
  description: ap.description ?? null,
  aiReasoning: null,
  impactScore: ap.impact_score,
  costEstimate: ap.cost_estimate as ActionPlan['costEstimate'],
  cognitiveLoad: null,
  timeEstimate: null,
  status: ap.status as ActionPlan['status'],
  assignedTo: null,
  createdAt: '',
  updatedAt: '',
}))

// ... in the TabsContent for "actions":
<TabsContent value="actions" className="flex-1 overflow-y-auto m-0 p-6">
  <SessionActionPlans initialPlans={mappedActionPlans} sessionId={sessionId} />
</TabsContent>
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/action-plans/session-tab.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/components/action-plans/session-action-plans.tsx src/app/sessions/[id]/page.tsx tests/unit/action-plans/session-tab.test.tsx
git commit -m "feat: replace inline action plans with ActionPlanTable in session detail"
```

---

### Task 10: Nav Link + Locale Keys

**Files:**
- Modify: `src/components/layout/nav.tsx`
- Modify: `src/config/locales/en-US.json`
- Modify: `src/config/locales/es-CL.json`

- [ ] **Step 1: Add locale keys to en-US.json**

```json
"action_plans.title": "Action Plans",
"action_plans.empty": "No action plans generated",
"action_plans.col_category": "Category",
"action_plans.col_title": "Title",
"action_plans.col_session": "Session",
"action_plans.col_impact": "Impact",
"action_plans.col_cost": "Cost",
"action_plans.col_time": "Time",
"action_plans.col_status": "Status",
"action_plans.ai_reasoning": "AI Reasoning",
"action_plans.filter_all_statuses": "All statuses",
"action_plans.filter_all_categories": "All categories",
"action_plans.stat_total": "Total Plans",
"action_plans.stat_done": "Completed",
"action_plans.stat_completion": "Completion Rate",
"nav.action_plans": "Action Plans"
```

- [ ] **Step 2: Add locale keys to es-CL.json**

```json
"action_plans.title": "Planes de Acción",
"action_plans.empty": "Sin planes de acción generados",
"action_plans.col_category": "Categoría",
"action_plans.col_title": "Título",
"action_plans.col_session": "Sesión",
"action_plans.col_impact": "Impacto",
"action_plans.col_cost": "Costo",
"action_plans.col_time": "Tiempo",
"action_plans.col_status": "Estado",
"action_plans.ai_reasoning": "Razonamiento IA",
"action_plans.filter_all_statuses": "Todos los estados",
"action_plans.filter_all_categories": "Todas las categorías",
"action_plans.stat_total": "Total Planes",
"action_plans.stat_done": "Completados",
"action_plans.stat_completion": "Tasa de Completitud",
"nav.action_plans": "Planes de Acción"
```

- [ ] **Step 3: Add Action Plans nav link** — read `src/components/layout/nav.tsx`, add a ClipboardList icon link to `/action-plans` visible for `wav_admin` and `mg_client` roles.

- [ ] **Step 4: Commit**

```bash
cd /Users/fede/projects/wav-intelligence
git add src/components/layout/nav.tsx src/config/locales/en-US.json src/config/locales/es-CL.json
git commit -m "feat: add action plans nav link and locale keys"
```

---

### Task 11: Full Test Run + Fixes

**Files:** All test files + any files needing fixes

- [ ] **Step 1: Run all action plan tests**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/action-plans/`
Expected: All pass

- [ ] **Step 2: Run full test suite**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run`
Expected: All pass (260+)

- [ ] **Step 3: Run TypeScript check**

Run: `cd /Users/fede/projects/wav-intelligence && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 4: Fix any failures**

- [ ] **Step 5: Commit fixes if any**

```bash
cd /Users/fede/projects/wav-intelligence
git add -A
git commit -m "fix: resolve test and type errors in action plans module"
```
