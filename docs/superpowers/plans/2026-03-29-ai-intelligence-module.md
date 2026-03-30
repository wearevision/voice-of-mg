# AI Intelligence Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a RAG-powered conversational AI sidebar that lets users explore focus group data through natural language, with cited verbatims linking to Player timestamps, tool calling for DB queries, and streaming responses.

**Architecture:** AI Chat is an omnipresent sidebar (400px desktop, full-screen sheet mobile) that opens over any view. It uses AI SDK v6 `streamText` with tool calling to query pgvector embeddings, Supabase tables, and generate cited responses. Chat history persists in `ai_conversations` + `ai_messages` tables. The RAG pipeline embeds user queries via OpenAI text-embedding-3-small (1536d) and performs cosine similarity search against pre-computed `verbatim_embeddings`.

**Tech Stack:** AI SDK v6 (`ai`, `@ai-sdk/react`), AI Gateway (OIDC), pgvector (Supabase), AI Elements (`<MessageResponse>`), shadcn/ui Sheet component, Supabase RLS

---

## File Structure

| File | Responsibility |
|------|---------------|
| `supabase/migrations/002_ai_conversations.sql` | ai_conversations + ai_messages tables, RLS policies |
| `src/types/ai.ts` | TypeScript types for AI module (conversations, messages, tools, citations) |
| `src/lib/ai/semantic-search.ts` | pgvector cosine similarity search utility |
| `src/lib/ai/tools.ts` | AI SDK tool definitions (search-verbatims, query-sessions, cite-verbatim, get-barriers, get-competitors) |
| `src/lib/ai/system-prompt.ts` | System prompt builder with session context |
| `src/app/api/chat/route.ts` | POST streaming chat endpoint (RAG + tool calling) |
| `src/app/api/chat/history/route.ts` | GET/DELETE conversation history |
| `src/components/ai/chat-sidebar.tsx` | Sidebar shell (Sheet desktop, full-screen mobile) |
| `src/components/ai-elements/message.tsx` | AI Elements MessageResponse (installed via registry, renders AI markdown) |
| `src/components/ai/chat-messages.tsx` | Message list using MessageResponse + citation rendering |
| `src/components/ai/chat-input.tsx` | Input field with quick prompt suggestions |
| `src/components/ai/verbatim-citation.tsx` | Inline citation block with Player link |
| `src/components/ai/chat-toggle.tsx` | Floating toggle button |
| `src/hooks/use-chat-sidebar.ts` | Sidebar open/close state + session context |
| `src/config/locales/en-US.json` | English locale keys for AI module |
| `src/config/locales/es-CL.json` | Spanish locale keys for AI module |

---

### Task 1: Database Migration — AI Conversations & Messages

**Files:**
- Create: `supabase/migrations/002_ai_conversations.sql`
- Test: `tests/unit/ai/migration-types.test.ts`

This task creates the persistence layer for chat history. The tables follow the spec exactly.

- [ ] **Step 1: Write the migration SQL**

```sql
-- supabase/migrations/002_ai_conversations.sql

-- AI conversations (per-user, optionally scoped to a session)
CREATE TABLE ai_conversations (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id    uuid REFERENCES sessions(id) ON DELETE SET NULL,
  user_id       uuid NOT NULL,
  title         text,
  created_at    timestamptz DEFAULT now(),
  updated_at    timestamptz DEFAULT now()
);

-- AI messages within a conversation
CREATE TABLE ai_messages (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
  role            text NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content         text NOT NULL,
  metadata        jsonb DEFAULT '{}',
  created_at      timestamptz DEFAULT now()
);

-- Indexes
CREATE INDEX idx_ai_conversations_user ON ai_conversations(user_id);
CREATE INDEX idx_ai_conversations_session ON ai_conversations(session_id);
CREATE INDEX idx_ai_messages_conversation ON ai_messages(conversation_id);
CREATE INDEX idx_ai_messages_created ON ai_messages(created_at);

-- RLS: owner-only access
ALTER TABLE ai_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own conversations"
  ON ai_conversations FOR ALL
  USING (user_id = auth.uid());

CREATE POLICY "Users can manage messages in own conversations"
  ON ai_messages FOR ALL
  USING (
    conversation_id IN (
      SELECT id FROM ai_conversations WHERE user_id = auth.uid()
    )
  );
```

- [ ] **Step 2: Write type validation test**

```typescript
// tests/unit/ai/migration-types.test.ts
import { describe, it, expect } from 'vitest'

// Validate our TypeScript types match the DB schema contract
import type { AiConversation, AiMessage } from '@/types/ai'

describe('AI conversation types', () => {
  it('AiConversation has required fields', () => {
    const conv: AiConversation = {
      id: 'c1',
      userId: 'u1',
      sessionId: null,
      title: 'Test conversation',
      createdAt: '2026-03-29T00:00:00Z',
      updatedAt: '2026-03-29T00:00:00Z',
    }
    expect(conv.id).toBe('c1')
    expect(conv.sessionId).toBeNull()
  })

  it('AiMessage has required fields', () => {
    const msg: AiMessage = {
      id: 'm1',
      conversationId: 'c1',
      role: 'assistant',
      content: 'Hello',
      metadata: { citedVerbatimIds: ['v1'] },
      createdAt: '2026-03-29T00:00:00Z',
    }
    expect(msg.role).toBe('assistant')
    expect(msg.metadata.citedVerbatimIds).toContain('v1')
  })

  it('AiMessage role is constrained', () => {
    const validRoles: AiMessage['role'][] = ['user', 'assistant', 'system']
    expect(validRoles).toHaveLength(3)
  })
})
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/migration-types.test.ts`
Expected: FAIL — `Cannot find module '@/types/ai'`

- [ ] **Step 4: Create AI types (minimal — just conversation/message)**

```typescript
// src/types/ai.ts
export interface AiConversation {
  id: string
  userId: string
  sessionId: string | null
  title: string | null
  createdAt: string
  updatedAt: string
}

export type AiMessageRole = 'user' | 'assistant' | 'system'

export interface AiMessageMetadata {
  citedVerbatimIds?: string[]
  toolCalls?: Array<{ name: string; args: Record<string, unknown> }>
  [key: string]: unknown
}

export interface AiMessage {
  id: string
  conversationId: string
  role: AiMessageRole
  content: string
  metadata: AiMessageMetadata
  createdAt: string
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/migration-types.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add supabase/migrations/002_ai_conversations.sql src/types/ai.ts tests/unit/ai/migration-types.test.ts
git commit -m "feat: add ai_conversations and ai_messages tables with RLS + types"
```

---

### Task 2: Semantic Search Utility

**Files:**
- Create: `src/lib/ai/semantic-search.ts`
- Test: `tests/unit/ai/semantic-search.test.ts`

This utility performs pgvector cosine similarity search against pre-computed verbatim embeddings. It takes a query string, generates an embedding via OpenAI, then runs a Supabase RPC call to find the most similar verbatims.

**Important:** The `verbatim_embeddings` table already exists with 1536-dimension vectors from `text-embedding-3-small`. The processing pipeline (Trigger.dev `generate-embeddings` task) populates these during session processing.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/ai/semantic-search.test.ts
import { describe, it, expect, vi } from 'vitest'

// Mock AI SDK embed function
vi.mock('ai', () => ({
  embed: vi.fn().mockResolvedValue({
    embedding: Array(1536).fill(0.1),
  }),
}))

vi.mock('@ai-sdk/openai', () => ({
  openai: {
    embedding: vi.fn().mockReturnValue('mocked-model'),
  },
}))

// Mock Supabase
const mockRpc = vi.fn().mockResolvedValue({
  data: [
    {
      verbatim_id: 'v1',
      text: 'El precio es muy alto para lo que ofrece',
      topic: 'precio',
      sentiment: 'negativo',
      sentiment_score: -0.7,
      start_ts: 45.2,
      end_ts: 51.8,
      session_id: 's1',
      participant_name: 'Carlos Ruiz',
      similarity: 0.89,
    },
    {
      verbatim_id: 'v2',
      text: 'Me gusta el diseño interior',
      topic: 'diseno',
      sentiment: 'positivo',
      sentiment_score: 0.8,
      start_ts: 120.5,
      end_ts: 125.0,
      session_id: 's1',
      participant_name: 'Ana García',
      similarity: 0.72,
    },
  ],
  error: null,
})

vi.mock('@/lib/supabase/server', () => ({
  createServiceClient: vi.fn().mockResolvedValue({ rpc: mockRpc }),
}))

import { searchVerbatims } from '@/lib/ai/semantic-search'

describe('searchVerbatims', () => {
  it('returns ranked verbatims by semantic similarity', async () => {
    const results = await searchVerbatims('problemas con el precio', { topK: 5 })

    expect(results).toHaveLength(2)
    expect(results[0].verbatimId).toBe('v1')
    expect(results[0].similarity).toBe(0.89)
    expect(results[0].text).toContain('precio')
    expect(results[0].participantName).toBe('Carlos Ruiz')
    expect(results[0].startTs).toBe(45.2)
  })

  it('passes session filter to RPC when provided', async () => {
    await searchVerbatims('diseño', { topK: 3, sessionId: 's1' })

    expect(mockRpc).toHaveBeenCalledWith('match_verbatims', expect.objectContaining({
      p_session_id: 's1',
      p_match_count: 3,
    }))
  })

  it('passes null session_id for cross-session search', async () => {
    await searchVerbatims('diseño', { topK: 5 })

    expect(mockRpc).toHaveBeenCalledWith('match_verbatims', expect.objectContaining({
      p_session_id: null,
    }))
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/semantic-search.test.ts`
Expected: FAIL — `Cannot find module '@/lib/ai/semantic-search'`

- [ ] **Step 3: Add the Supabase RPC function to migration**

Append to `supabase/migrations/002_ai_conversations.sql`:

```sql
-- Semantic search function for RAG
CREATE OR REPLACE FUNCTION match_verbatims(
  p_query_embedding vector(1536),
  p_match_count int DEFAULT 10,
  p_session_id uuid DEFAULT NULL
)
RETURNS TABLE (
  verbatim_id uuid,
  text text,
  topic topic_enum,
  sentiment sentiment_enum,
  sentiment_score float,
  start_ts float,
  end_ts float,
  session_id uuid,
  participant_name text,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    v.id AS verbatim_id,
    v.text,
    v.topic,
    v.sentiment,
    v.sentiment_score,
    v.start_ts,
    v.end_ts,
    v.session_id,
    p.name AS participant_name,
    1 - (ve.embedding <=> p_query_embedding) AS similarity
  FROM verbatim_embeddings ve
  JOIN verbatims v ON ve.verbatim_id = v.id
  LEFT JOIN participants p ON v.participant_id = p.id
  WHERE (p_session_id IS NULL OR v.session_id = p_session_id)
  ORDER BY ve.embedding <=> p_query_embedding
  LIMIT p_match_count;
$$;
```

- [ ] **Step 4: Write the semantic search implementation**

```typescript
// src/lib/ai/semantic-search.ts
import { embed } from 'ai'
import { openai } from '@ai-sdk/openai'
import { createServiceClient } from '@/lib/supabase/server'

export interface SemanticSearchOptions {
  topK?: number
  sessionId?: string | null
}

export interface VerbatimMatch {
  verbatimId: string
  text: string
  topic: string
  sentiment: string
  sentimentScore: number
  startTs: number
  endTs: number
  sessionId: string
  participantName: string | null
  similarity: number
}

export async function searchVerbatims(
  query: string,
  options: SemanticSearchOptions = {}
): Promise<VerbatimMatch[]> {
  const { topK = 10, sessionId = null } = options

  // Generate query embedding
  const { embedding } = await embed({
    model: openai.embedding('text-embedding-3-small'),
    value: query,
  })

  // Run pgvector similarity search via Supabase RPC
  const supabase = await createServiceClient()
  const { data, error } = await supabase.rpc('match_verbatims', {
    p_query_embedding: JSON.stringify(embedding),
    p_match_count: topK,
    p_session_id: sessionId,
  })

  if (error) throw new Error(`Semantic search failed: ${error.message}`)

  return (data ?? []).map((row: Record<string, unknown>) => ({
    verbatimId: row.verbatim_id as string,
    text: row.text as string,
    topic: row.topic as string,
    sentiment: row.sentiment as string,
    sentimentScore: row.sentiment_score as number,
    startTs: row.start_ts as number,
    endTs: row.end_ts as number,
    sessionId: row.session_id as string,
    participantName: row.participant_name as string | null,
    similarity: row.similarity as number,
  }))
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/semantic-search.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/lib/ai/semantic-search.ts tests/unit/ai/semantic-search.test.ts supabase/migrations/002_ai_conversations.sql
git commit -m "feat: add semantic search utility with pgvector cosine similarity"
```

---

### Task 3: AI Tool Definitions

**Files:**
- Create: `src/lib/ai/tools.ts`
- Test: `tests/unit/ai/tools.test.ts`

Defines the tools the AI can call during conversation. Each tool has an `inputSchema` (Zod) and an `execute` function. The AI SDK v6 tool calling protocol handles orchestration.

**Tools:**
1. `search_verbatims` — semantic search via pgvector
2. `get_session_stats` — aggregate stats for a session
3. `get_barriers` — purchase barriers ranking
4. `get_competitors` — competitor mentions with sentiment
5. `cite_verbatim` — create a citation block with Player link

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/ai/tools.test.ts
import { describe, it, expect, vi } from 'vitest'

vi.mock('@/lib/ai/semantic-search', () => ({
  searchVerbatims: vi.fn().mockResolvedValue([
    {
      verbatimId: 'v1',
      text: 'El precio es alto',
      topic: 'precio',
      sentiment: 'negativo',
      sentimentScore: -0.6,
      startTs: 10.5,
      endTs: 15.0,
      sessionId: 's1',
      participantName: 'Carlos',
      similarity: 0.91,
    },
  ]),
}))

vi.mock('@/lib/supabase/server', () => ({
  createServiceClient: vi.fn().mockResolvedValue({
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({
            data: { id: 's1', name: 'Sesión 1', status: 'ready' },
            error: null,
          }),
        }),
        order: vi.fn().mockResolvedValue({
          data: [{ barrier_name: 'Precio alto', category: 'price', mention_count: 12 }],
          error: null,
        }),
      }),
    }),
    rpc: vi.fn().mockResolvedValue({ data: [], error: null }),
  }),
}))

import { createAiTools } from '@/lib/ai/tools'

describe('createAiTools', () => {
  it('returns all 5 tool definitions', () => {
    const tools = createAiTools({ sessionId: null })
    const names = Object.keys(tools)
    expect(names).toContain('search_verbatims')
    expect(names).toContain('get_session_stats')
    expect(names).toContain('get_barriers')
    expect(names).toContain('get_competitors')
    expect(names).toContain('cite_verbatim')
    expect(names).toHaveLength(5)
  })

  it('each tool has inputSchema and execute', () => {
    const tools = createAiTools({ sessionId: null })
    for (const [, tool] of Object.entries(tools)) {
      expect(tool).toHaveProperty('inputSchema')
      expect(tool).toHaveProperty('execute')
    }
  })

  it('search_verbatims tool executes semantic search', async () => {
    const tools = createAiTools({ sessionId: 's1' })
    const result = await tools.search_verbatims.execute(
      { query: 'precio', topK: 5 },
      { toolCallId: 'tc1', messages: [], abortSignal: new AbortController().signal }
    )
    expect(result.verbatims).toHaveLength(1)
    expect(result.verbatims[0].text).toContain('precio')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/tools.test.ts`
Expected: FAIL — `Cannot find module '@/lib/ai/tools'`

- [ ] **Step 3: Write the tools implementation**

```typescript
// src/lib/ai/tools.ts
import { tool } from 'ai'
import { z } from 'zod'
import { searchVerbatims } from '@/lib/ai/semantic-search'
import { createServiceClient } from '@/lib/supabase/server'

export interface ToolContext {
  sessionId: string | null
}

export function createAiTools(ctx: ToolContext) {
  return {
    search_verbatims: tool({
      description:
        'Search focus group verbatims using semantic similarity. Use when the user asks about specific topics, sentiments, or participant opinions. Returns ranked verbatims with timestamps for player citations.',
      inputSchema: z.object({
        query: z.string().describe('Natural language search query'),
        topK: z.number().min(1).max(20).default(8).describe('Number of results'),
        sessionId: z.string().uuid().nullable().optional().describe('Filter to specific session, or null for cross-session'),
      }),
      execute: async ({ query, topK, sessionId }) => {
        const effectiveSessionId = sessionId ?? ctx.sessionId
        const verbatims = await searchVerbatims(query, { topK, sessionId: effectiveSessionId })
        return { verbatims }
      },
    }),

    get_session_stats: tool({
      description:
        'Get aggregate statistics for a session: total verbatims, sentiment breakdown, top topics, participant count. Use when asked about session overview or summary.',
      inputSchema: z.object({
        sessionId: z.string().uuid().describe('Session ID to query'),
      }),
      execute: async ({ sessionId }) => {
        const supabase = await createServiceClient()

        const { data: verbatims } = await supabase
          .from('verbatims')
          .select('sentiment, topic')
          .eq('session_id', sessionId)

        const { data: participants } = await supabase
          .from('participants')
          .select('id')
          .eq('session_id', sessionId)

        const sentimentCounts = { positivo: 0, neutro: 0, negativo: 0 }
        const topicCounts: Record<string, number> = {}

        for (const v of verbatims ?? []) {
          if (v.sentiment) sentimentCounts[v.sentiment as keyof typeof sentimentCounts]++
          if (v.topic) topicCounts[v.topic] = (topicCounts[v.topic] ?? 0) + 1
        }

        return {
          totalVerbatims: verbatims?.length ?? 0,
          participantCount: participants?.length ?? 0,
          sentimentCounts,
          topTopics: Object.entries(topicCounts)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 5)
            .map(([topic, count]) => ({ topic, count })),
        }
      },
    }),

    get_barriers: tool({
      description:
        'Get purchase barriers ranked by mention count. Use when asked about what prevents customers from buying, objections, or sales blockers.',
      inputSchema: z.object({
        sessionId: z.string().uuid().nullable().optional().describe('Filter to session, null for all'),
        limit: z.number().min(1).max(20).default(10),
      }),
      execute: async ({ sessionId, limit }) => {
        const supabase = await createServiceClient()
        let query = supabase
          .from('purchase_barriers')
          .select('barrier_name, category, mention_count')
          .order('mention_count', { ascending: false })
          .limit(limit)

        if (sessionId) query = query.eq('session_id', sessionId)

        const { data, error } = await query
        if (error) throw new Error(`Failed to fetch barriers: ${error.message}`)

        return { barriers: data ?? [] }
      },
    }),

    get_competitors: tool({
      description:
        'Get competitor brand mentions with sentiment breakdown. Use when asked about competitor perception, brand comparison, or market positioning.',
      inputSchema: z.object({
        sessionId: z.string().uuid().nullable().optional().describe('Filter to session, null for all'),
      }),
      execute: async ({ sessionId }) => {
        const supabase = await createServiceClient()
        let query = supabase
          .from('competitor_mentions')
          .select('brand_name, sentiment, context')

        if (sessionId) query = query.eq('session_id', sessionId)

        const { data, error } = await query
        if (error) throw new Error(`Failed to fetch competitors: ${error.message}`)

        // Aggregate by brand
        const brands: Record<string, { positivo: number; neutro: number; negativo: number; total: number }> = {}
        for (const row of data ?? []) {
          if (!brands[row.brand_name]) {
            brands[row.brand_name] = { positivo: 0, neutro: 0, negativo: 0, total: 0 }
          }
          if (row.sentiment) brands[row.brand_name][row.sentiment as 'positivo' | 'neutro' | 'negativo']++
          brands[row.brand_name].total++
        }

        return {
          competitors: Object.entries(brands)
            .map(([brand, counts]) => ({ brand, ...counts }))
            .sort((a, b) => b.total - a.total),
        }
      },
    }),

    cite_verbatim: tool({
      description:
        'Create a citation for a specific verbatim with a link to the Player at its exact timestamp. Use after search_verbatims to reference specific quotes in your response.',
      inputSchema: z.object({
        verbatimId: z.string().uuid().describe('Verbatim ID from search results'),
        sessionId: z.string().uuid().describe('Session ID for the Player link'),
        text: z.string().describe('The verbatim text to cite'),
        participantName: z.string().describe('Speaker name'),
        startTs: z.number().describe('Start timestamp in seconds'),
        topic: z.string().describe('Topic classification'),
        sentiment: z.string().describe('Sentiment classification'),
      }),
      execute: async ({ verbatimId, sessionId, text, participantName, startTs, topic, sentiment }) => {
        return {
          citation: {
            verbatimId,
            text,
            participantName,
            startTs,
            topic,
            sentiment,
            playerUrl: `/sessions/${sessionId}?t=${Math.floor(startTs)}`,
          },
        }
      },
    }),
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/tools.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/lib/ai/tools.ts tests/unit/ai/tools.test.ts
git commit -m "feat: add AI tool definitions for RAG chat (search, stats, barriers, competitors, cite)"
```

---

### Task 4: System Prompt Builder

**Files:**
- Create: `src/lib/ai/system-prompt.ts`
- Test: `tests/unit/ai/system-prompt.test.ts`

Builds the system prompt that instructs the AI how to behave. Includes domain context (focus group research for MG Motor Chile), available capabilities, citation format, and session-specific context when opened from the Player.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/ai/system-prompt.test.ts
import { describe, it, expect } from 'vitest'
import { buildSystemPrompt } from '@/lib/ai/system-prompt'

describe('buildSystemPrompt', () => {
  it('includes base domain context', () => {
    const prompt = buildSystemPrompt({})
    expect(prompt).toContain('focus group')
    expect(prompt).toContain('MG Motor Chile')
    expect(prompt).toContain('search_verbatims')
    expect(prompt).toContain('cite_verbatim')
  })

  it('includes session context when sessionId provided', () => {
    const prompt = buildSystemPrompt({
      sessionId: 's1',
      sessionName: 'Sesión 3 - Q1 2026',
    })
    expect(prompt).toContain('Sesión 3 - Q1 2026')
    expect(prompt).toContain('s1')
  })

  it('instructs cross-session mode when no sessionId', () => {
    const prompt = buildSystemPrompt({})
    expect(prompt).toContain('cross-session')
  })

  it('always instructs citation format', () => {
    const prompt = buildSystemPrompt({})
    expect(prompt).toContain('cite_verbatim')
    expect(prompt).toContain('Player')
  })

  it('responds in Spanish by default', () => {
    const prompt = buildSystemPrompt({ locale: 'es-CL' })
    expect(prompt).toContain('español')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/system-prompt.test.ts`
Expected: FAIL — `Cannot find module '@/lib/ai/system-prompt'`

- [ ] **Step 3: Write the system prompt builder**

```typescript
// src/lib/ai/system-prompt.ts

export interface SystemPromptContext {
  sessionId?: string
  sessionName?: string
  locale?: string
}

export function buildSystemPrompt(ctx: SystemPromptContext): string {
  const { sessionId, sessionName, locale = 'es-CL' } = ctx

  const languageInstruction = locale.startsWith('es')
    ? 'Responde siempre en español chileno profesional.'
    : 'Respond in English.'

  const sessionContext = sessionId
    ? `You are currently viewing session "${sessionName}" (ID: ${sessionId}). When the user asks about "this session" or "esta sesión", scope queries to this session ID. Use search_verbatims with sessionId="${sessionId}" by default unless the user explicitly asks about other sessions or cross-session analysis.`
    : 'You are in cross-session mode. Search across ALL sessions unless the user specifies a particular session.'

  return `You are an AI research analyst for WAV Intelligence, a focus group research platform for MG Motor Chile. You help users explore consumer insights from focus group sessions where participants discuss their perceptions of MG vehicles.

## Domain Context
- Each focus group session has 10-15 participants with individual microphones
- Participants discuss topics: marca (brand), diseño (design), precio (price), infotainment (tech), postventa (after-sales), seguridad (safety), garantía (warranty), convocatoria (recruitment)
- Each verbatim (quote) has: speaker name, timestamp, topic, sentiment (positivo/neutro/negativo), and sentiment_score (-1 to +1)
- Embeddings are pre-computed for semantic search via pgvector

## Current Context
${sessionContext}

## Available Tools
- **search_verbatims**: Semantic search across verbatims. Use this to find relevant quotes before answering questions. ALWAYS search before making claims about the data.
- **get_session_stats**: Get aggregate statistics for a specific session.
- **get_barriers**: Get purchase barriers ranked by frequency.
- **get_competitors**: Get competitor brand mentions with sentiment.
- **cite_verbatim**: Create a citation with a link to the Player at the exact timestamp. Use this to cite specific verbatims in your response.

## Citation Rules
- When referencing specific participant quotes, ALWAYS use cite_verbatim to create a clickable link to the Player at that timestamp.
- After calling search_verbatims, call cite_verbatim for each relevant result you want to reference.
- Format citations naturally within your response.

## Response Guidelines
- ${languageInstruction}
- Be concise but thorough. Use bullet points for lists.
- When presenting sentiment analysis, use specific numbers and percentages.
- When asked for action plans, categorize as: quick_win (bajo costo, alto impacto), strategic (inversión mayor, impacto a largo plazo), or monitor (seguimiento).
- Always ground your responses in actual data — never fabricate quotes or statistics.
- If the data doesn't have enough information to answer, say so clearly.`
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/system-prompt.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/lib/ai/system-prompt.ts tests/unit/ai/system-prompt.test.ts
git commit -m "feat: add system prompt builder with session context and citation rules"
```

---

### Task 5: Chat API Route (Streaming + Tool Calling)

**Files:**
- Create: `src/app/api/chat/route.ts`
- Test: `tests/unit/ai/chat-route.test.ts`

The core streaming endpoint. Accepts messages + optional sessionId/conversationId, performs RAG + tool calling via AI SDK v6 `streamText`, returns a streaming response.

**Pattern:** Uses AI SDK v6 conventions — `convertToModelMessages()`, `streamText()`, `toUIMessageStreamResponse()`. Tool calling is automatic via the AI SDK agent loop with `stopWhen: stepCountIs(5)`.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/ai/chat-route.test.ts
import { describe, it, expect, vi } from 'vitest'
import { NextRequest } from 'next/server'

// Mock auth
vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: {
      getUser: vi.fn().mockResolvedValue({
        data: { user: { id: 'u1' } },
        error: null,
      }),
    },
  }),
  createServiceClient: vi.fn().mockResolvedValue({
    rpc: vi.fn().mockResolvedValue({ data: [], error: null }),
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({ data: null, error: null }),
          order: vi.fn().mockResolvedValue({ data: [], error: null }),
        }),
        order: vi.fn().mockResolvedValue({ data: [], error: null }),
      }),
    }),
  }),
}))

// Mock AI SDK
vi.mock('ai', async () => {
  const actual = await vi.importActual('ai')
  return {
    ...actual,
    streamText: vi.fn().mockReturnValue({
      toUIMessageStreamResponse: vi.fn().mockReturnValue(
        new Response('streamed', { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
      ),
    }),
    convertToModelMessages: vi.fn().mockReturnValue([]),
    embed: vi.fn().mockResolvedValue({ embedding: Array(1536).fill(0) }),
    tool: vi.fn().mockImplementation((def) => def),
    stepCountIs: vi.fn().mockReturnValue(() => false),
  }
})

vi.mock('@ai-sdk/openai', () => ({
  openai: { embedding: vi.fn().mockReturnValue('mock-model') },
}))

vi.mock('@/lib/ai/system-prompt', () => ({
  buildSystemPrompt: vi.fn().mockReturnValue('You are an AI analyst.'),
}))

import { POST } from '@/app/api/chat/route'

describe('POST /api/chat', () => {
  it('returns 401 when not authenticated', async () => {
    const { createClient } = await import('@/lib/supabase/server')
    vi.mocked(createClient).mockResolvedValueOnce({
      auth: { getUser: vi.fn().mockResolvedValue({ data: { user: null }, error: { message: 'no auth' } }) },
    } as never)

    const req = new NextRequest('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({ messages: [{ role: 'user', content: 'hello' }] }),
    })
    const res = await POST(req)
    expect(res.status).toBe(401)
  })

  it('returns streaming response for valid request', async () => {
    const req = new NextRequest('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', parts: [{ type: 'text', text: 'Top barreras de compra' }] }],
      }),
    })
    const res = await POST(req)
    expect(res.status).toBe(200)
    expect(res.headers.get('Content-Type')).toBe('text/event-stream')
  })

  it('returns 400 for missing messages', async () => {
    const req = new NextRequest('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({}),
    })
    const res = await POST(req)
    expect(res.status).toBe(400)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/chat-route.test.ts`
Expected: FAIL — `Cannot find module '@/app/api/chat/route'`

- [ ] **Step 3: Write the chat route implementation**

```typescript
// src/app/api/chat/route.ts
import { streamText, convertToModelMessages, UIMessage, stepCountIs } from 'ai'
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { createAiTools } from '@/lib/ai/tools'
import { buildSystemPrompt } from '@/lib/ai/system-prompt'

export async function POST(req: NextRequest) {
  // Auth guard
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  // Parse body
  const body = await req.json()
  const { messages, sessionId, sessionName } = body as {
    messages?: UIMessage[]
    sessionId?: string
    sessionName?: string
  }

  if (!messages || !Array.isArray(messages) || messages.length === 0) {
    return NextResponse.json({ error: 'messages required' }, { status: 400 })
  }

  // Build context
  const systemPrompt = buildSystemPrompt({
    sessionId: sessionId ?? undefined,
    sessionName: sessionName ?? undefined,
    locale: 'es-CL',
  })

  const tools = createAiTools({ sessionId: sessionId ?? null })

  // Stream response with tool calling
  const result = streamText({
    model: 'openai/gpt-5.4',
    system: systemPrompt,
    messages: convertToModelMessages(messages),
    tools,
    stopWhen: stepCountIs(5),
  })

  return result.toUIMessageStreamResponse()
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/chat-route.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/app/api/chat/route.ts tests/unit/ai/chat-route.test.ts
git commit -m "feat: add streaming chat API route with RAG tool calling"
```

---

### Task 6: Install Frontend Dependencies

**Files:**
- Modify: `package.json`

Install `@ai-sdk/react` (for `useChat` hook), AI Elements (for `<MessageResponse>` markdown rendering), and shadcn Sheet component (for sidebar).

- [ ] **Step 1: Install @ai-sdk/react**

```bash
cd /Users/fede/projects/wav-intelligence && npm install @ai-sdk/react
```

- [ ] **Step 2: Install AI Elements MessageResponse component**

```bash
cd /Users/fede/projects/wav-intelligence && npx shadcn@latest add https://elements.ai-sdk.dev/api/registry/message.json
```

This installs `<MessageResponse>` at `src/components/ai-elements/message.tsx` — a streaming-aware markdown renderer that handles code blocks, math, mermaid diagrams, and CJK text.

- [ ] **Step 3: Install shadcn sheet component**

```bash
cd /Users/fede/projects/wav-intelligence && npx shadcn@latest add sheet
```

- [ ] **Step 4: Install shadcn scroll-area component**

```bash
cd /Users/fede/projects/wav-intelligence && npx shadcn@latest add scroll-area
```

- [ ] **Step 5: Verify imports work**

```bash
cd /Users/fede/projects/wav-intelligence && node -e "require('@ai-sdk/react')" && echo "OK"
```

- [ ] **Step 6: Commit**

```bash
git add package.json package-lock.json src/components/ai-elements/ src/components/ui/sheet.tsx src/components/ui/scroll-area.tsx
git commit -m "feat: install @ai-sdk/react, AI Elements, shadcn sheet and scroll-area"
```

---

### Task 7: Chat Sidebar State Hook

**Files:**
- Create: `src/hooks/use-chat-sidebar.ts`
- Test: `tests/unit/ai/use-chat-sidebar.test.tsx`

Manages the sidebar open/close state and session context. When opened from the Player, it passes the current session ID so the AI scopes queries to that session.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/ai/use-chat-sidebar.test.tsx
import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useChatSidebar } from '@/hooks/use-chat-sidebar'

describe('useChatSidebar', () => {
  it('starts closed', () => {
    const { result } = renderHook(() => useChatSidebar())
    expect(result.current.isOpen).toBe(false)
    expect(result.current.sessionId).toBeNull()
  })

  it('opens without session context', () => {
    const { result } = renderHook(() => useChatSidebar())
    act(() => result.current.open())
    expect(result.current.isOpen).toBe(true)
    expect(result.current.sessionId).toBeNull()
  })

  it('opens with session context', () => {
    const { result } = renderHook(() => useChatSidebar())
    act(() => result.current.open({ sessionId: 's1', sessionName: 'Session 1' }))
    expect(result.current.isOpen).toBe(true)
    expect(result.current.sessionId).toBe('s1')
    expect(result.current.sessionName).toBe('Session 1')
  })

  it('closes and preserves session context', () => {
    const { result } = renderHook(() => useChatSidebar())
    act(() => result.current.open({ sessionId: 's1', sessionName: 'S1' }))
    act(() => result.current.close())
    expect(result.current.isOpen).toBe(false)
    expect(result.current.sessionId).toBe('s1')
  })

  it('clears context on reset', () => {
    const { result } = renderHook(() => useChatSidebar())
    act(() => result.current.open({ sessionId: 's1', sessionName: 'S1' }))
    act(() => result.current.reset())
    expect(result.current.isOpen).toBe(false)
    expect(result.current.sessionId).toBeNull()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/use-chat-sidebar.test.tsx`
Expected: FAIL — `Cannot find module '@/hooks/use-chat-sidebar'`

- [ ] **Step 3: Write the hook implementation**

```typescript
// src/hooks/use-chat-sidebar.ts
'use client'

import { useCallback, useState } from 'react'

interface SessionContext {
  sessionId: string
  sessionName: string
}

interface ChatSidebarState {
  isOpen: boolean
  sessionId: string | null
  sessionName: string | null
  open: (ctx?: SessionContext) => void
  close: () => void
  reset: () => void
  toggle: (ctx?: SessionContext) => void
}

export function useChatSidebar(): ChatSidebarState {
  const [isOpen, setIsOpen] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [sessionName, setSessionName] = useState<string | null>(null)

  const open = useCallback((ctx?: SessionContext) => {
    if (ctx) {
      setSessionId(ctx.sessionId)
      setSessionName(ctx.sessionName)
    }
    setIsOpen(true)
  }, [])

  const close = useCallback(() => {
    setIsOpen(false)
  }, [])

  const reset = useCallback(() => {
    setIsOpen(false)
    setSessionId(null)
    setSessionName(null)
  }, [])

  const toggle = useCallback((ctx?: SessionContext) => {
    setIsOpen((prev) => {
      if (!prev && ctx) {
        setSessionId(ctx.sessionId)
        setSessionName(ctx.sessionName)
      }
      return !prev
    })
  }, [])

  return { isOpen, sessionId, sessionName, open, close, reset, toggle }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/use-chat-sidebar.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/hooks/use-chat-sidebar.ts tests/unit/ai/use-chat-sidebar.test.tsx
git commit -m "feat: add useChatSidebar hook for sidebar state and session context"
```

---

### Task 8: Verbatim Citation Component

**Files:**
- Create: `src/components/ai/verbatim-citation.tsx`
- Test: `tests/unit/ai/verbatim-citation.test.tsx`

A small component that renders an inline citation block: participant name, verbatim text (truncated), sentiment badge, and a link to the Player at the exact timestamp.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/ai/verbatim-citation.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { VerbatimCitation } from '@/components/ai/verbatim-citation'

describe('VerbatimCitation', () => {
  const defaultProps = {
    text: 'El precio es muy alto para lo que ofrece el vehículo',
    participantName: 'Carlos Ruiz',
    startTs: 45.2,
    topic: 'precio',
    sentiment: 'negativo' as const,
    playerUrl: '/sessions/s1?t=45',
  }

  it('renders participant name', () => {
    render(<VerbatimCitation {...defaultProps} />)
    expect(screen.getByText('Carlos Ruiz')).toBeDefined()
  })

  it('renders verbatim text', () => {
    render(<VerbatimCitation {...defaultProps} />)
    expect(screen.getByText(/precio es muy alto/)).toBeDefined()
  })

  it('renders topic badge', () => {
    render(<VerbatimCitation {...defaultProps} />)
    expect(screen.getByText('precio')).toBeDefined()
  })

  it('renders timestamp as link', () => {
    render(<VerbatimCitation {...defaultProps} />)
    const link = screen.getByRole('link')
    expect(link.getAttribute('href')).toBe('/sessions/s1?t=45')
  })

  it('formats timestamp as mm:ss', () => {
    render(<VerbatimCitation {...defaultProps} />)
    expect(screen.getByText('0:45')).toBeDefined()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/verbatim-citation.test.tsx`
Expected: FAIL — `Cannot find module '@/components/ai/verbatim-citation'`

- [ ] **Step 3: Write the citation component**

```typescript
// src/components/ai/verbatim-citation.tsx
import Link from 'next/link'
import { Badge } from '@/components/ui/badge'

interface VerbatimCitationProps {
  text: string
  participantName: string
  startTs: number
  topic: string
  sentiment: 'positivo' | 'neutro' | 'negativo'
  playerUrl: string
}

const SENTIMENT_COLORS = {
  positivo: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  neutro: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  negativo: 'bg-red-500/20 text-red-400 border-red-500/30',
} as const

function formatTimestamp(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

export function VerbatimCitation({
  text,
  participantName,
  startTs,
  topic,
  sentiment,
  playerUrl,
}: VerbatimCitationProps) {
  return (
    <div className="my-2 rounded-lg border border-zinc-700 bg-zinc-800/50 p-3">
      <div className="mb-1 flex items-center gap-2">
        <span className="text-sm font-medium text-zinc-200">{participantName}</span>
        <Badge variant="outline" className="text-xs">
          {topic}
        </Badge>
        <span className={`rounded-full px-2 py-0.5 text-xs ${SENTIMENT_COLORS[sentiment]}`}>
          {sentiment}
        </span>
      </div>
      <p className="mb-1 text-sm text-zinc-300 italic">&ldquo;{text}&rdquo;</p>
      <Link
        href={playerUrl}
        className="text-xs text-blue-400 hover:text-blue-300 hover:underline"
      >
        {formatTimestamp(startTs)}
      </Link>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/verbatim-citation.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/components/ai/verbatim-citation.tsx tests/unit/ai/verbatim-citation.test.tsx
git commit -m "feat: add VerbatimCitation component with Player timestamp link"
```

---

### Task 9: Chat Messages Component

**Files:**
- Create: `src/components/ai/chat-messages.tsx`
- Test: `tests/unit/ai/chat-messages.test.tsx`

Renders the message list. User messages are plain text bubbles. Assistant messages use `<MessageResponse>` from AI Elements for streaming-aware markdown rendering. Tool call results with citations render `<VerbatimCitation>` blocks inline.

**Important AI SDK v6 note:** In v6, tool result parts use the `tool-<toolName>` pattern (e.g., `part.type === 'tool-cite_verbatim'`), NOT the removed `tool-invocation` type. Install AI Elements for markdown rendering: `npx shadcn@latest add https://elements.ai-sdk.dev/api/registry/message.json`

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/ai/chat-messages.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

// Mock AI Elements MessageResponse — renders content as plain text for testing
vi.mock('@/components/ai-elements/message', () => ({
  MessageResponse: ({ content }: { content: string }) => <div>{content}</div>,
}))

import { ChatMessages } from '@/components/ai/chat-messages'
import type { UIMessage } from 'ai'

describe('ChatMessages', () => {
  it('renders user message', () => {
    const messages: UIMessage[] = [
      { id: 'm1', role: 'user', parts: [{ type: 'text', text: 'Hola' }] },
    ]
    render(<ChatMessages messages={messages} />)
    expect(screen.getByText('Hola')).toBeDefined()
  })

  it('renders assistant text message', () => {
    const messages: UIMessage[] = [
      { id: 'm2', role: 'assistant', parts: [{ type: 'text', text: 'Las barreras principales son precio y confianza.' }] },
    ]
    render(<ChatMessages messages={messages} />)
    expect(screen.getByText(/barreras principales/)).toBeDefined()
  })

  it('renders multiple messages in order', () => {
    const messages: UIMessage[] = [
      { id: 'm1', role: 'user', parts: [{ type: 'text', text: 'Pregunta 1' }] },
      { id: 'm2', role: 'assistant', parts: [{ type: 'text', text: 'Respuesta 1' }] },
      { id: 'm3', role: 'user', parts: [{ type: 'text', text: 'Pregunta 2' }] },
    ]
    render(<ChatMessages messages={messages} />)
    expect(screen.getByText('Pregunta 1')).toBeDefined()
    expect(screen.getByText('Respuesta 1')).toBeDefined()
    expect(screen.getByText('Pregunta 2')).toBeDefined()
  })

  it('renders empty state when no messages', () => {
    render(<ChatMessages messages={[]} />)
    expect(screen.getByText(/comienza una conversación/i)).toBeDefined()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/chat-messages.test.tsx`
Expected: FAIL — `Cannot find module '@/components/ai/chat-messages'`

- [ ] **Step 3: Write the chat messages component**

```typescript
// src/components/ai/chat-messages.tsx
'use client'

import type { UIMessage } from 'ai'
import { MessageResponse } from '@/components/ai-elements/message'
import { VerbatimCitation } from '@/components/ai/verbatim-citation'

interface ChatMessagesProps {
  messages: UIMessage[]
}

function renderCitation(result: unknown) {
  if (!result || typeof result !== 'object') return null
  const data = result as Record<string, unknown>

  if (data.citation && typeof data.citation === 'object') {
    const c = data.citation as Record<string, unknown>
    return (
      <VerbatimCitation
        text={c.text as string}
        participantName={c.participantName as string}
        startTs={c.startTs as number}
        topic={c.topic as string}
        sentiment={c.sentiment as 'positivo' | 'neutro' | 'negativo'}
        playerUrl={c.playerUrl as string}
      />
    )
  }

  return null
}

export function ChatMessages({ messages }: ChatMessagesProps) {
  if (messages.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-8 text-center">
        <p className="text-sm text-zinc-500">
          Comienza una conversación preguntando sobre los datos de las sesiones de focus group.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 p-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[85%] rounded-lg px-4 py-2 ${
              message.role === 'user'
                ? 'bg-blue-600 text-white'
                : 'bg-zinc-800 text-zinc-200'
            }`}
          >
            {message.parts.map((part, i) => {
              if (part.type === 'text') {
                return (
                  <MessageResponse key={i} content={part.text} />
                )
              }
              // AI SDK v6: tool results use tool-<toolName> pattern
              if (part.type === 'tool-cite_verbatim' && 'result' in part) {
                return <div key={i}>{renderCitation(part.result)}</div>
              }
              return null
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/chat-messages.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/components/ai/chat-messages.tsx tests/unit/ai/chat-messages.test.tsx
git commit -m "feat: add ChatMessages component with citation rendering"
```

---

### Task 10: Chat Input with Quick Prompts

**Files:**
- Create: `src/components/ai/chat-input.tsx`
- Test: `tests/unit/ai/chat-input.test.tsx`

Input field with send button and quick prompt suggestion chips. Quick prompts: "Resumen última sesión", "Top barreras de compra", "Plan de acción para postventa".

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/ai/chat-input.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatInput } from '@/components/ai/chat-input'

describe('ChatInput', () => {
  it('renders textarea', () => {
    render(<ChatInput onSend={vi.fn()} isLoading={false} showQuickPrompts />)
    expect(screen.getByPlaceholderText(/pregunta/i)).toBeDefined()
  })

  it('renders quick prompt chips when showQuickPrompts is true', () => {
    render(<ChatInput onSend={vi.fn()} isLoading={false} showQuickPrompts />)
    expect(screen.getByText(/Resumen última sesión/)).toBeDefined()
    expect(screen.getByText(/Top barreras de compra/)).toBeDefined()
    expect(screen.getByText(/Plan de acción/)).toBeDefined()
  })

  it('hides quick prompts when showQuickPrompts is false', () => {
    render(<ChatInput onSend={vi.fn()} isLoading={false} showQuickPrompts={false} />)
    expect(screen.queryByText(/Resumen última sesión/)).toBeNull()
  })

  it('calls onSend when quick prompt clicked', async () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} isLoading={false} showQuickPrompts />)
    await userEvent.click(screen.getByText(/Top barreras de compra/))
    expect(onSend).toHaveBeenCalledWith('Top barreras de compra')
  })

  it('disables input when loading', () => {
    render(<ChatInput onSend={vi.fn()} isLoading showQuickPrompts={false} />)
    const textarea = screen.getByPlaceholderText(/pregunta/i) as HTMLTextAreaElement
    expect(textarea.disabled).toBe(true)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/chat-input.test.tsx`
Expected: FAIL — `Cannot find module '@/components/ai/chat-input'`

- [ ] **Step 3: Write the chat input component**

```typescript
// src/components/ai/chat-input.tsx
'use client'

import { useState, useCallback, KeyboardEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Send } from 'lucide-react'

const QUICK_PROMPTS = [
  'Resumen última sesión',
  'Top barreras de compra',
  'Plan de acción para postventa',
]

interface ChatInputProps {
  onSend: (text: string) => void
  isLoading: boolean
  showQuickPrompts: boolean
}

export function ChatInput({ onSend, isLoading, showQuickPrompts }: ChatInputProps) {
  const [value, setValue] = useState('')

  const handleSend = useCallback(() => {
    const trimmed = value.trim()
    if (!trimmed) return
    onSend(trimmed)
    setValue('')
  }, [value, onSend])

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend]
  )

  return (
    <div className="border-t border-zinc-700 p-4">
      {showQuickPrompts && (
        <div className="mb-3 flex flex-wrap gap-2">
          {QUICK_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => onSend(prompt)}
              className="rounded-full border border-zinc-600 px-3 py-1 text-xs text-zinc-300 transition-colors hover:border-blue-500 hover:text-blue-400"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <Textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Haz una pregunta sobre los datos..."
          disabled={isLoading}
          rows={1}
          className="min-h-[40px] resize-none bg-zinc-800 text-zinc-200"
        />
        <Button
          size="icon"
          onClick={handleSend}
          disabled={isLoading || !value.trim()}
          className="shrink-0"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/chat-input.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/components/ai/chat-input.tsx tests/unit/ai/chat-input.test.tsx
git commit -m "feat: add ChatInput component with quick prompt chips"
```

---

### Task 11: Chat Sidebar Component

**Files:**
- Create: `src/components/ai/chat-sidebar.tsx`
- Test: `tests/unit/ai/chat-sidebar.test.tsx`

The main sidebar shell. Uses shadcn Sheet on desktop (right side, 400px) and full-screen on mobile. Integrates `useChat` from `@ai-sdk/react` with `DefaultChatTransport`. Contains ChatMessages and ChatInput.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/ai/chat-sidebar.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

// Mock useChat
vi.mock('@ai-sdk/react', () => ({
  useChat: vi.fn().mockReturnValue({
    messages: [],
    sendMessage: vi.fn(),
    status: 'ready',
  }),
  DefaultChatTransport: vi.fn(),
}))

import { ChatSidebar } from '@/components/ai/chat-sidebar'

describe('ChatSidebar', () => {
  it('renders when open', () => {
    render(
      <ChatSidebar
        isOpen
        onClose={vi.fn()}
        sessionId={null}
        sessionName={null}
      />
    )
    expect(screen.getByText(/AI Assistant/i)).toBeDefined()
  })

  it('shows empty state when no messages', () => {
    render(
      <ChatSidebar
        isOpen
        onClose={vi.fn()}
        sessionId={null}
        sessionName={null}
      />
    )
    expect(screen.getByText(/comienza una conversación/i)).toBeDefined()
  })

  it('shows session context badge when sessionId provided', () => {
    render(
      <ChatSidebar
        isOpen
        onClose={vi.fn()}
        sessionId="s1"
        sessionName="Sesión 3"
      />
    )
    expect(screen.getByText('Sesión 3')).toBeDefined()
  })

  it('shows quick prompts when no messages', () => {
    render(
      <ChatSidebar
        isOpen
        onClose={vi.fn()}
        sessionId={null}
        sessionName={null}
      />
    )
    expect(screen.getByText(/Resumen última sesión/)).toBeDefined()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/chat-sidebar.test.tsx`
Expected: FAIL — `Cannot find module '@/components/ai/chat-sidebar'`

- [ ] **Step 3: Write the chat sidebar component**

```typescript
// src/components/ai/chat-sidebar.tsx
'use client'

import { useCallback, useEffect, useRef } from 'react'
import { useChat, DefaultChatTransport } from '@ai-sdk/react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { X } from 'lucide-react'
import { ChatMessages } from '@/components/ai/chat-messages'
import { ChatInput } from '@/components/ai/chat-input'

interface ChatSidebarProps {
  isOpen: boolean
  onClose: () => void
  sessionId: string | null
  sessionName: string | null
}

export function ChatSidebar({ isOpen, onClose, sessionId, sessionName }: ChatSidebarProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  const { messages, sendMessage, status } = useChat({
    transport: new DefaultChatTransport({
      api: '/api/chat',
      body: { sessionId, sessionName },
    }),
  })

  const isLoading = status === 'streaming' || status === 'submitted'

  const handleSend = useCallback(
    (text: string) => {
      sendMessage({ text })
    },
    [sendMessage]
  )

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <SheetContent
        side="right"
        className="flex w-full flex-col border-zinc-700 bg-zinc-900 p-0 sm:w-[400px]"
      >
        <SheetHeader className="border-b border-zinc-700 px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <SheetTitle className="text-zinc-100">AI Assistant</SheetTitle>
              {sessionName && (
                <Badge variant="outline" className="text-xs">
                  {sessionName}
                </Badge>
              )}
            </div>
            <button
              onClick={onClose}
              className="rounded-md p-1 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </SheetHeader>

        <ScrollArea ref={scrollRef} className="flex-1">
          <ChatMessages messages={messages} />
        </ScrollArea>

        <ChatInput
          onSend={handleSend}
          isLoading={isLoading}
          showQuickPrompts={messages.length === 0}
        />
      </SheetContent>
    </Sheet>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/chat-sidebar.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/components/ai/chat-sidebar.tsx tests/unit/ai/chat-sidebar.test.tsx
git commit -m "feat: add ChatSidebar with useChat, streaming, and session context"
```

---

### Task 12: Chat Toggle Button

**Files:**
- Create: `src/components/ai/chat-toggle.tsx`
- Test: `tests/unit/ai/chat-toggle.test.tsx`

Floating action button (FAB) in bottom-right corner that opens the AI chat sidebar. Uses the ◉ sparkle/brain icon. Gated by `useFeature('ragQA')`.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/ai/chat-toggle.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatToggle } from '@/components/ai/chat-toggle'

describe('ChatToggle', () => {
  it('renders the toggle button', () => {
    render(<ChatToggle onClick={vi.fn()} />)
    const button = screen.getByRole('button', { name: /ai chat/i })
    expect(button).toBeDefined()
  })

  it('calls onClick when pressed', async () => {
    const onClick = vi.fn()
    render(<ChatToggle onClick={onClick} />)
    await userEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledOnce()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/chat-toggle.test.tsx`
Expected: FAIL — `Cannot find module '@/components/ai/chat-toggle'`

- [ ] **Step 3: Write the toggle button**

```typescript
// src/components/ai/chat-toggle.tsx
'use client'

import { Button } from '@/components/ui/button'
import { Sparkles } from 'lucide-react'

interface ChatToggleProps {
  onClick: () => void
}

export function ChatToggle({ onClick }: ChatToggleProps) {
  return (
    <Button
      onClick={onClick}
      size="icon"
      aria-label="AI Chat"
      className="fixed bottom-6 right-6 z-50 h-14 w-14 rounded-full bg-blue-600 shadow-lg shadow-blue-600/25 hover:bg-blue-500"
    >
      <Sparkles className="h-6 w-6" />
    </Button>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/chat-toggle.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/components/ai/chat-toggle.tsx tests/unit/ai/chat-toggle.test.tsx
git commit -m "feat: add ChatToggle FAB button for AI sidebar"
```

---

### Task 13: Layout Integration — Wire Chat Sidebar into App

**Files:**
- Modify: `src/app/layout.tsx` (or the dashboard layout)
- Create: `src/components/ai/chat-provider.tsx`

Wire the ChatSidebar + ChatToggle into the app layout. The toggle is gated by `useFeature('ragQA')`. The sidebar state is managed by `useChatSidebar` hook exposed via a context provider, so any page can open the chat (e.g., the Player can pass session context).

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/ai/chat-provider.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('@ai-sdk/react', () => ({
  useChat: vi.fn().mockReturnValue({
    messages: [],
    sendMessage: vi.fn(),
    status: 'ready',
  }),
  DefaultChatTransport: vi.fn(),
}))

vi.mock('@/hooks/use-feature', () => ({
  useFeature: vi.fn().mockReturnValue(true),
}))

import { ChatProvider, useChatContext } from '@/components/ai/chat-provider'

function TestConsumer() {
  const { open } = useChatContext()
  return <button onClick={() => open()}>Open Chat</button>
}

describe('ChatProvider', () => {
  it('renders children and toggle button', () => {
    render(
      <ChatProvider>
        <div>App Content</div>
      </ChatProvider>
    )
    expect(screen.getByText('App Content')).toBeDefined()
    expect(screen.getByRole('button', { name: /ai chat/i })).toBeDefined()
  })

  it('opens sidebar via context', async () => {
    render(
      <ChatProvider>
        <TestConsumer />
      </ChatProvider>
    )
    await userEvent.click(screen.getByText('Open Chat'))
    expect(screen.getByText(/AI Assistant/i)).toBeDefined()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/chat-provider.test.tsx`
Expected: FAIL — `Cannot find module '@/components/ai/chat-provider'`

- [ ] **Step 3: Write the chat provider**

```typescript
// src/components/ai/chat-provider.tsx
'use client'

import { createContext, useContext, ReactNode } from 'react'
import { useChatSidebar } from '@/hooks/use-chat-sidebar'
import { useFeature } from '@/hooks/use-feature'
import { ChatSidebar } from '@/components/ai/chat-sidebar'
import { ChatToggle } from '@/components/ai/chat-toggle'

interface ChatContextValue {
  open: (ctx?: { sessionId: string; sessionName: string }) => void
  close: () => void
  isOpen: boolean
}

const ChatContext = createContext<ChatContextValue>({
  open: () => {},
  close: () => {},
  isOpen: false,
})

export function useChatContext() {
  return useContext(ChatContext)
}

interface ChatProviderProps {
  children: ReactNode
}

export function ChatProvider({ children }: ChatProviderProps) {
  const sidebar = useChatSidebar()
  const ragEnabled = useFeature('ragQA')

  return (
    <ChatContext.Provider
      value={{ open: sidebar.open, close: sidebar.close, isOpen: sidebar.isOpen }}
    >
      {children}
      {ragEnabled && (
        <>
          {!sidebar.isOpen && <ChatToggle onClick={() => sidebar.toggle()} />}
          <ChatSidebar
            isOpen={sidebar.isOpen}
            onClose={sidebar.close}
            sessionId={sidebar.sessionId}
            sessionName={sidebar.sessionName}
          />
        </>
      )}
    </ChatContext.Provider>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/chat-provider.test.tsx`
Expected: PASS

- [ ] **Step 5: Integrate into the dashboard layout**

Find the layout file that wraps the dashboard pages (likely `src/app/(dashboard)/layout.tsx` or `src/app/layout.tsx`). Wrap children with `<ChatProvider>`:

```tsx
// In the existing layout, add:
import { ChatProvider } from '@/components/ai/chat-provider'

// Wrap the children:
<ChatProvider>
  {children}
</ChatProvider>
```

- [ ] **Step 6: Commit**

```bash
git add src/components/ai/chat-provider.tsx tests/unit/ai/chat-provider.test.tsx src/app/**/layout.tsx
git commit -m "feat: add ChatProvider with context and integrate into app layout"
```

---

### Task 14: Chat History API

**Files:**
- Create: `src/app/api/chat/history/route.ts`
- Test: `tests/unit/ai/chat-history-route.test.ts`

GET endpoint returns user's conversation list. DELETE endpoint removes a conversation and its messages. Both are owner-only (RLS enforced).

- [ ] **Step 1: Write the failing test**

```typescript
// tests/unit/ai/chat-history-route.test.ts
import { describe, it, expect, vi } from 'vitest'
import { NextRequest } from 'next/server'

const mockSelect = vi.fn().mockReturnValue({
  eq: vi.fn().mockReturnValue({
    order: vi.fn().mockResolvedValue({
      data: [
        { id: 'c1', title: 'Análisis de precios', session_id: null, created_at: '2026-03-29T00:00:00Z', updated_at: '2026-03-29T00:00:00Z' },
      ],
      error: null,
    }),
  }),
})

const mockDelete = vi.fn().mockReturnValue({
  eq: vi.fn().mockResolvedValue({ error: null }),
})

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: { getUser: vi.fn().mockResolvedValue({ data: { user: { id: 'u1' } }, error: null }) },
    from: vi.fn().mockImplementation((table: string) => {
      if (table === 'ai_conversations') {
        return { select: mockSelect, delete: mockDelete }
      }
      return {}
    }),
  }),
}))

import { GET, DELETE } from '@/app/api/chat/history/route'

describe('GET /api/chat/history', () => {
  it('returns conversations for authenticated user', async () => {
    const req = new NextRequest('http://localhost/api/chat/history')
    const res = await GET(req)
    expect(res.status).toBe(200)
    const json = await res.json()
    expect(json.conversations).toHaveLength(1)
    expect(json.conversations[0].title).toBe('Análisis de precios')
  })
})

describe('DELETE /api/chat/history', () => {
  it('deletes a conversation', async () => {
    const req = new NextRequest('http://localhost/api/chat/history?id=c1', { method: 'DELETE' })
    const res = await DELETE(req)
    expect(res.status).toBe(200)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/chat-history-route.test.ts`
Expected: FAIL — `Cannot find module '@/app/api/chat/history/route'`

- [ ] **Step 3: Write the history route**

```typescript
// src/app/api/chat/history/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export async function GET(req: NextRequest) {
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const { data, error } = await supabase
    .from('ai_conversations')
    .select('id, title, session_id, created_at, updated_at')
    .eq('user_id', user.id)
    .order('updated_at', { ascending: false })

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({
    conversations: (data ?? []).map((c) => ({
      id: c.id,
      title: c.title,
      sessionId: c.session_id,
      createdAt: c.created_at,
      updatedAt: c.updated_at,
    })),
  })
}

export async function DELETE(req: NextRequest) {
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const id = req.nextUrl.searchParams.get('id')
  if (!id) {
    return NextResponse.json({ error: 'id required' }, { status: 400 })
  }

  const { error } = await supabase
    .from('ai_conversations')
    .delete()
    .eq('id', id)

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ success: true })
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/chat-history-route.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/app/api/chat/history/route.ts tests/unit/ai/chat-history-route.test.ts
git commit -m "feat: add chat history API (GET list, DELETE conversation)"
```

---

### Task 15: Locale Keys for AI Module

**Files:**
- Modify: `src/config/locales/en-US.json`
- Modify: `src/config/locales/es-CL.json`

Add locale keys for all AI chat UI strings.

- [ ] **Step 1: Add English locale keys**

Add to `en-US.json`:
```json
"ai.title": "AI Assistant",
"ai.placeholder": "Ask a question about the data...",
"ai.empty_state": "Start a conversation by asking about focus group session data.",
"ai.quick_prompt.summary": "Summary of last session",
"ai.quick_prompt.barriers": "Top purchase barriers",
"ai.quick_prompt.action_plan": "Action plan for after-sales",
"ai.session_context": "Analyzing",
"ai.cross_session": "Cross-session mode",
"ai.history": "History",
"ai.new_chat": "New conversation",
"ai.thinking": "Thinking..."
```

- [ ] **Step 2: Add Spanish locale keys**

Add to `es-CL.json`:
```json
"ai.title": "Asistente IA",
"ai.placeholder": "Haz una pregunta sobre los datos...",
"ai.empty_state": "Comienza una conversación preguntando sobre los datos de las sesiones de focus group.",
"ai.quick_prompt.summary": "Resumen última sesión",
"ai.quick_prompt.barriers": "Top barreras de compra",
"ai.quick_prompt.action_plan": "Plan de acción para postventa",
"ai.session_context": "Analizando",
"ai.cross_session": "Modo cross-session",
"ai.history": "Historial",
"ai.new_chat": "Nueva conversación",
"ai.thinking": "Pensando..."
```

- [ ] **Step 3: Commit**

```bash
git add src/config/locales/en-US.json src/config/locales/es-CL.json
git commit -m "feat: add AI module locale keys (en-US, es-CL)"
```

---

### Task 16: Run All Tests and Fix Issues

**Files:**
- All test files in `tests/unit/ai/`
- Any files needing fixes

Run the full test suite to ensure nothing is broken. Fix any issues that arise.

- [ ] **Step 1: Run all AI module tests**

```bash
cd /Users/fede/projects/wav-intelligence && npx vitest run tests/unit/ai/
```
Expected: ALL PASS

- [ ] **Step 2: Run full test suite**

```bash
cd /Users/fede/projects/wav-intelligence && npx vitest run
```
Expected: ALL PASS (167 existing + ~50 new = ~217 tests)

- [ ] **Step 3: Run TypeScript check**

```bash
cd /Users/fede/projects/wav-intelligence && npx tsc --noEmit
```
Expected: No new errors (pre-existing errors in peaks-route.test.ts and verbatims-route.test.ts are known and out of scope)

- [ ] **Step 4: Fix any failures discovered**

Address test failures, type errors, or import issues.

- [ ] **Step 5: Commit fixes if any**

```bash
git add -A && git commit -m "fix: resolve test and type issues in AI module"
```

---

## Summary

| Task | Description | Files | Complexity |
|------|------------|-------|------------|
| 1 | DB migration + types | migration SQL, `types/ai.ts` | Mechanical |
| 2 | Semantic search utility | `lib/ai/semantic-search.ts` | Mechanical |
| 3 | AI tool definitions | `lib/ai/tools.ts` | Integration |
| 4 | System prompt builder | `lib/ai/system-prompt.ts` | Mechanical |
| 5 | Chat API route (streaming) | `app/api/chat/route.ts` | Integration |
| 6 | Install frontend deps | `package.json` | Mechanical |
| 7 | Chat sidebar state hook | `hooks/use-chat-sidebar.ts` | Mechanical |
| 8 | Verbatim citation component | `components/ai/verbatim-citation.tsx` | Mechanical |
| 9 | Chat messages component | `components/ai/chat-messages.tsx` | Mechanical |
| 10 | Chat input + quick prompts | `components/ai/chat-input.tsx` | Mechanical |
| 11 | Chat sidebar shell | `components/ai/chat-sidebar.tsx` | Integration |
| 12 | Chat toggle FAB | `components/ai/chat-toggle.tsx` | Mechanical |
| 13 | Layout integration + provider | `components/ai/chat-provider.tsx` | Integration |
| 14 | Chat history API | `app/api/chat/history/route.ts` | Mechanical |
| 15 | Locale keys | locale JSON files | Mechanical |
| 16 | Full test run + fixes | All files | Integration |

**Total: 16 tasks, ~14 commits, ~16 new files, ~50 new tests**
