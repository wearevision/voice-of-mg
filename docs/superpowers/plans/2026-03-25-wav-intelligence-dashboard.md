# WAV Intelligence Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the WAV Intelligence Dashboard — a production SaaS that ingests focus group media (360° video, DSLR, 13 lavalier audio tracks), processes through an AI pipeline, and delivers searchable transcripts, insights, and action plans to MG Motor Chile.

**Architecture:** Next.js 16 (App Router) + Supabase (Auth/DB/RLS) + Cloudflare R2 (media storage) + Trigger.dev Cloud (processing pipeline) + Vercel AI Gateway (LLM). All roles enforced at the DB layer via RLS. Separate repo from the static proposal site.

**Tech Stack:** Next.js 16, TypeScript, Supabase, Cloudflare R2, Trigger.dev Cloud, shadcn/ui, Tailwind CSS, ElevenLabs Scribe, Vercel AI Gateway (OpenAI text-embedding-3-small), HLS.js, Video.js + videojs-vr, Peaks.js, React-pdf, Vitest, Playwright

**Spec:** `docs/superpowers/specs/2026-03-25-wav-intelligence-dashboard-design.md`

---

## Scope Note

This plan covers 8 sequential phases. Each phase ends with working, deployable software. Phases P1–P3 are detailed to bite-sized TDD steps. Phases P4–P8 are task-level (invoke `writing-plans` again per phase when ready to execute).

---

## File Structure

```
wav-intelligence/                        ← NEW REPO (separate from voice-of-mg)
├── package.json
├── next.config.ts
├── vercel.json                          ← cron config
├── tsconfig.json
├── vitest.config.ts
├── playwright.config.ts
├── tailwind.config.ts
├── .env.example
│
├── supabase/
│   ├── config.toml
│   └── migrations/
│       ├── 001_initial_schema.sql       ← all tables
│       ├── 002_rls_policies.sql         ← RLS per role
│       ├── 003_indexes.sql              ← all indexes incl. HNSW
│       └── 004_functions.sql            ← helper DB functions
│
├── src/
│   ├── app/
│   │   ├── layout.tsx                   ← root layout + providers
│   │   ├── page.tsx                     ← redirect → /dashboard
│   │   ├── globals.css                  ← MG dark theme tokens
│   │   ├── login/page.tsx
│   │   ├── dashboard/page.tsx           ← role-based landing
│   │   ├── sessions/
│   │   │   ├── page.tsx                 ← session list
│   │   │   └── [id]/
│   │   │       ├── page.tsx             ← session shell (tabs)
│   │   │       ├── player/page.tsx
│   │   │       ├── transcripts/page.tsx
│   │   │       ├── participants/page.tsx
│   │   │       ├── insights/page.tsx
│   │   │       ├── action-plan/page.tsx
│   │   │       └── export/page.tsx
│   │   ├── trends/page.tsx
│   │   ├── ask/page.tsx
│   │   ├── admin/
│   │   │   ├── sessions/new/page.tsx
│   │   │   ├── sessions/[id]/setup/page.tsx
│   │   │   ├── processing/page.tsx
│   │   │   └── users/page.tsx
│   │   └── api/
│   │       ├── auth/callback/route.ts
│   │       ├── sessions/route.ts
│   │       ├── sessions/[id]/route.ts
│   │       ├── sessions/[id]/upload-url/route.ts
│   │       ├── sessions/[id]/upload-complete/route.ts
│   │       ├── sessions/[id]/process/route.ts
│   │       ├── sessions/[id]/processing/route.ts
│   │       ├── sessions/[id]/processing/retry/route.ts
│   │       ├── sessions/[id]/media/[fileId]/stream/route.ts
│   │       ├── sessions/[id]/media/[fileId]/peaks/route.ts
│   │       ├── sessions/[id]/participants/route.ts
│   │       ├── sessions/[id]/seating/route.ts
│   │       ├── sessions/[id]/verbatims/route.ts
│   │       ├── sessions/[id]/keypoints/route.ts
│   │       ├── sessions/[id]/action-plans/route.ts
│   │       ├── sessions/[id]/export/pdf/route.ts
│   │       ├── sessions/[id]/export/csv/route.ts
│   │       ├── action-plans/[id]/route.ts
│   │       ├── search/route.ts
│   │       ├── ask/route.ts
│   │       ├── trends/route.ts
│   │       ├── cron/check-uploads/route.ts
│   │       ├── admin/users/route.ts
│   │       ├── admin/users/[id]/route.ts
│   │       └── admin/users/[id]/sessions/route.ts
│   │
│   ├── components/
│   │   ├── ui/                          ← shadcn/ui (generated)
│   │   ├── layout/
│   │   │   ├── nav.tsx
│   │   │   └── sidebar.tsx
│   │   ├── auth/login-form.tsx
│   │   ├── dashboard/
│   │   │   ├── wav-admin-dashboard.tsx
│   │   │   ├── mg-client-dashboard.tsx
│   │   │   └── moderator-dashboard.tsx
│   │   ├── sessions/
│   │   │   ├── session-card.tsx
│   │   │   ├── session-status-badge.tsx
│   │   │   └── sessions-table.tsx
│   │   ├── player/
│   │   │   ├── sync-player.tsx          ← orchestrator
│   │   │   ├── video-360.tsx            ← HLS + VR viewer
│   │   │   ├── video-dslr.tsx
│   │   │   ├── audio-track.tsx          ← single waveform
│   │   │   ├── audio-tracks.tsx         ← 13-track list
│   │   │   ├── master-timeline.tsx      ← scrubber + markers
│   │   │   ├── transcript-follow.tsx
│   │   │   ├── speaker-overlay.tsx
│   │   │   └── seating-map.tsx
│   │   ├── upload/
│   │   │   ├── file-upload-zone.tsx
│   │   │   └── upload-progress.tsx
│   │   ├── processing/
│   │   │   ├── processing-status.tsx
│   │   │   └── processing-queue.tsx
│   │   ├── insights/
│   │   │   ├── keypoints-list.tsx
│   │   │   ├── topic-chart.tsx
│   │   │   ├── sentiment-heatmap.tsx
│   │   │   └── action-plans-list.tsx
│   │   ├── search/
│   │   │   ├── search-bar.tsx
│   │   │   └── search-results.tsx
│   │   ├── ask/ask-interface.tsx
│   │   ├── trends/
│   │   │   ├── trend-chart.tsx
│   │   │   └── cross-session-table.tsx
│   │   └── export/
│   │       ├── export-panel.tsx
│   │       └── pdf-template.tsx
│   │
│   ├── lib/
│   │   ├── supabase/
│   │   │   ├── client.ts               ← browser client
│   │   │   ├── server.ts               ← server client (cookies)
│   │   │   └── middleware.ts           ← auth middleware
│   │   ├── r2/
│   │   │   ├── client.ts               ← S3-compatible client
│   │   │   ├── upload.ts               ← presigned multipart URLs
│   │   │   └── stream.ts               ← signed playback URLs
│   │   ├── transcription/
│   │   │   ├── types.ts                ← TranscriptionProvider interface
│   │   │   ├── elevenlabs-scribe.ts
│   │   │   ├── deepgram-nova3.ts
│   │   │   ├── whisper-local.ts       ← self-hosted (A/B test option)
│   │   │   └── index.ts               ← getProvider() factory
│   │   ├── ai/
│   │   │   ├── classify-topics.ts
│   │   │   ├── analyze-sentiment.ts
│   │   │   ├── extract-keypoints.ts
│   │   │   ├── generate-action-plans.ts
│   │   │   ├── embed-verbatims.ts
│   │   │   ├── rag-query.ts
│   │   │   └── translate.ts
│   │   ├── sync/
│   │   │   ├── sync-engine.ts          ← coordinator + state machine
│   │   │   └── amplitude-detector.ts   ← RMS active speaker
│   │   ├── export/
│   │   │   ├── pdf-report.tsx
│   │   │   └── csv-export.ts
│   │   └── utils/
│   │       ├── auth.ts                 ← role-checking helpers
│   │       └── format.ts               ← time/currency formatters
│   │
│   ├── trigger/
│   │   ├── client.ts                   ← Trigger.dev client
│   │   ├── process-session.ts          ← main job (7 steps)
│   │   └── steps/
│   │       ├── transcode-360.ts
│   │       ├── transcode-dslr.ts
│   │       ├── generate-peaks.ts
│   │       ├── transcribe-audio.ts
│   │       ├── ai-enrichment.ts
│   │       ├── generate-embeddings.ts
│   │       └── finalize.ts
│   │
│   └── types/
│       └── database.ts                 ← shared DB types
│
└── tests/
    ├── unit/
    │   ├── transcription/
    │   │   ├── elevenlabs-scribe.test.ts
    │   │   └── deepgram-nova3.test.ts
    │   ├── ai/
    │   │   ├── classify-topics.test.ts
    │   │   └── generate-action-plans.test.ts
    │   └── sync/
    │       ├── sync-engine.test.ts
    │       └── amplitude-detector.test.ts
    ├── integration/
    │   ├── upload-flow.test.ts
    │   └── rls-policies.test.ts
    └── e2e/
        ├── auth.spec.ts
        ├── upload.spec.ts
        └── session-view.spec.ts
```

---

## Phase 1 — Scaffold + Auth + DB Schema + MG Theme

**Deliverable:** Deployed Next.js app with Supabase auth (magic link), 3 roles enforced via RLS, dark MG theme, and role-based dashboard landing. No media yet. All tests green.

**Done when:** WAV Admin can log in, see admin dashboard. MG Client can log in, see client dashboard. Moderator can log in, see moderator dashboard. Login with unknown role → 403.

---

### Task 1.1: Create repo and install dependencies

**Files:**
- Create: `package.json`
- Create: `next.config.ts`
- Create: `tsconfig.json`
- Create: `vitest.config.ts`
- Create: `.env.example`

- [ ] **Step 1: Scaffold Next.js 16 app**

```bash
npx create-next-app@latest wav-intelligence \
  --typescript --tailwind --app --src-dir \
  --no-eslint --import-alias "@/*"
cd wav-intelligence
```

- [ ] **Step 2: Install core dependencies**

```bash
npm install @supabase/supabase-js @supabase/ssr \
  @aws-sdk/client-s3 @aws-sdk/s3-request-presigner \
  @trigger.dev/sdk @trigger.dev/react-hooks \
  ai @ai-sdk/react @ai-sdk/openai \
  @radix-ui/react-slot @radix-ui/react-tabs \
  @radix-ui/react-dialog @radix-ui/react-dropdown-menu \
  class-variance-authority clsx tailwind-merge lucide-react \
  recharts date-fns zod
```

- [ ] **Step 3: Install dev dependencies**

```bash
npm install -D vitest @vitejs/plugin-react \
  @testing-library/react @testing-library/user-event \
  @playwright/test @types/node jsdom
```

- [ ] **Step 4: Install shadcn/ui**

```bash
npx shadcn@latest init
# choose: Dark theme, CSS variables, src/components/ui
npx shadcn@latest add button card badge tabs dialog \
  dropdown-menu input label textarea toast separator \
  skeleton progress avatar table
```

- [ ] **Step 5: Create `.env.example`**

```bash
cat > .env.example << 'EOF'
# Supabase
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# Cloudflare R2
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
R2_ACCOUNT_ID=
R2_PUBLIC_URL=

# Transcription
ELEVENLABS_API_KEY=
DEEPGRAM_API_KEY=

# Processing pipeline
TRIGGER_SECRET_KEY=        # Trigger.dev Cloud API key

# Vercel Cron
CRON_SECRET=

# App
NEXT_PUBLIC_APP_URL=http://localhost:3000
EOF
cp .env.example .env.local
```

- [ ] **Step 6: Configure Vitest**

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/tests/setup.ts'],
  },
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
})
```

```typescript
// src/tests/setup.ts
import '@testing-library/jest-dom'
```

- [ ] **Step 7: Commit**

```bash
git init && git add -A
git commit -m "chore: scaffold Next.js 16 + install dependencies"
```

---

### Task 1.2: Supabase project + DB schema

**Files:**
- Create: `supabase/migrations/001_initial_schema.sql`
- Create: `supabase/migrations/002_rls_policies.sql`
- Create: `supabase/migrations/003_indexes.sql`

- [ ] **Step 1: Install Supabase CLI and init**

```bash
npm install -D supabase
npx supabase init
npx supabase start   # starts local Supabase (Docker required)
```

- [ ] **Step 2: Write failing test for schema existence**

```typescript
// tests/integration/schema.test.ts
import { createClient } from '@supabase/supabase-js'
import { describe, it, expect } from 'vitest'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

describe('database schema', () => {
  it('has sessions table', async () => {
    const { error } = await supabase.from('sessions').select('id').limit(1)
    expect(error).toBeNull()
  })

  it('has verbatims table with topic column', async () => {
    const { error } = await supabase.from('verbatims').select('id, topic').limit(1)
    expect(error).toBeNull()
  })

  it('has verbatim_embeddings table', async () => {
    const { error } = await supabase.from('verbatim_embeddings').select('id').limit(1)
    expect(error).toBeNull()
  })
})
```

- [ ] **Step 3: Run test — expect FAIL**

```bash
npx vitest run tests/integration/schema.test.ts
# Expected: relation "sessions" does not exist
```

- [ ] **Step 4: Write `001_initial_schema.sql`**

```sql
-- supabase/migrations/001_initial_schema.sql

-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Enums
CREATE TYPE session_status AS ENUM ('scheduled', 'uploaded', 'processing', 'ready', 'error');
CREATE TYPE topic_enum AS ENUM ('marca', 'diseno', 'precio', 'infotainment', 'postventa', 'seguridad', 'garantia', 'convocatoria', 'otro');
CREATE TYPE sentiment_enum AS ENUM ('positivo', 'neutro', 'negativo');
CREATE TYPE media_type AS ENUM ('video_360', 'video_dslr', 'audio');
CREATE TYPE job_status AS ENUM ('queued', 'running', 'completed', 'failed');
CREATE TYPE action_category AS ENUM ('quick_win', 'strategic', 'monitor');
CREATE TYPE action_status AS ENUM ('pending', 'in_progress', 'done');
CREATE TYPE cost_estimate AS ENUM ('low', 'medium', 'high');

-- Programs and focus groups
CREATE TABLE programs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  year INT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE focus_groups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  program_id UUID NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
  quarter TEXT NOT NULL CHECK (quarter IN ('Q1','Q2','Q3','Q4')),
  start_date DATE,
  end_date DATE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE days (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  focus_group_id UUID NOT NULL REFERENCES focus_groups(id) ON DELETE CASCADE,
  day_number INT NOT NULL CHECK (day_number BETWEEN 1 AND 3),
  date DATE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sessions
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  day_id UUID NOT NULL REFERENCES days(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  status session_status NOT NULL DEFAULT 'scheduled',
  moderator_id UUID REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User-session assignments (moderators)
CREATE TABLE user_sessions (
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, session_id)
);

-- Media files
CREATE TABLE media_files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  type media_type NOT NULL,
  r2_key TEXT NOT NULL,
  r2_bucket TEXT NOT NULL,
  original_filename TEXT NOT NULL,
  duration_seconds INT,
  file_size_bytes BIGINT,
  hls_manifest_key TEXT,
  waveform_peaks_key TEXT,
  sync_offset_ms INT DEFAULT 0,
  mic_number INT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Participants
CREATE TABLE participants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  mg_model TEXT,
  mic_number INT,
  media_file_id UUID REFERENCES media_files(id),
  seat_angle FLOAT,
  seat_distance FLOAT,
  talk_time_seconds INT DEFAULT 0,
  sentiment_avg FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Verbatims
CREATE TABLE verbatims (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  participant_id UUID REFERENCES participants(id),
  text TEXT NOT NULL,
  start_ts FLOAT NOT NULL,
  end_ts FLOAT NOT NULL,
  topic topic_enum,
  sentiment sentiment_enum,
  sentiment_score FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Verbatim embeddings (separate table for model-agnostic storage)
CREATE TABLE verbatim_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  verbatim_id UUID NOT NULL REFERENCES verbatims(id) ON DELETE CASCADE,
  model_name TEXT NOT NULL DEFAULT 'text-embedding-3-small',
  dimensions INT NOT NULL DEFAULT 1536,
  embedding vector(1536) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(verbatim_id, model_name)
);

-- Keypoints
CREATE TABLE keypoints (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  topic topic_enum,
  title TEXT NOT NULL,
  description TEXT,
  timestamp FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE keypoint_verbatims (
  keypoint_id UUID NOT NULL REFERENCES keypoints(id) ON DELETE CASCADE,
  verbatim_id UUID NOT NULL REFERENCES verbatims(id) ON DELETE CASCADE,
  PRIMARY KEY (keypoint_id, verbatim_id)
);

-- Action plans
CREATE TABLE action_plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  category action_category NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  ai_reasoning TEXT,
  impact_score INT CHECK (impact_score BETWEEN 1 AND 10),
  cost_estimate cost_estimate,
  cognitive_load cost_estimate,
  time_estimate TEXT,
  status action_status NOT NULL DEFAULT 'pending',
  assigned_to UUID REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE action_plan_verbatims (
  action_plan_id UUID NOT NULL REFERENCES action_plans(id) ON DELETE CASCADE,
  verbatim_id UUID NOT NULL REFERENCES verbatims(id) ON DELETE CASCADE,
  PRIMARY KEY (action_plan_id, verbatim_id)
);

-- Processing jobs
CREATE TABLE processing_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  status job_status NOT NULL DEFAULT 'queued',
  current_step INT DEFAULT 0,
  total_steps INT DEFAULT 7,
  progress INT DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
  error_message TEXT,
  trigger_run_id TEXT,
  failed_step INT,
  last_completed_step INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);
```

- [ ] **Step 5: Write `002_rls_policies.sql`**

```sql
-- supabase/migrations/002_rls_policies.sql

-- Helper function to get role from app_metadata (CRITICAL: NOT user_metadata)
CREATE OR REPLACE FUNCTION auth.user_role()
RETURNS TEXT AS $$
  SELECT COALESCE(
    auth.jwt() -> 'app_metadata' ->> 'role',
    'anon'
  );
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- Enable RLS on all tables
ALTER TABLE programs ENABLE ROW LEVEL SECURITY;
ALTER TABLE focus_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE days ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE media_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE verbatims ENABLE ROW LEVEL SECURITY;
ALTER TABLE verbatim_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE keypoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE keypoint_verbatims ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_plan_verbatims ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_jobs ENABLE ROW LEVEL SECURITY;

-- wav_admin: full access to everything
CREATE POLICY "wav_admin_all" ON sessions FOR ALL
  USING (auth.user_role() = 'wav_admin');
CREATE POLICY "wav_admin_all" ON media_files FOR ALL
  USING (auth.user_role() = 'wav_admin');
CREATE POLICY "wav_admin_all" ON participants FOR ALL
  USING (auth.user_role() = 'wav_admin');
CREATE POLICY "wav_admin_all" ON verbatims FOR ALL
  USING (auth.user_role() = 'wav_admin');
CREATE POLICY "wav_admin_all" ON verbatim_embeddings FOR ALL
  USING (auth.user_role() = 'wav_admin');
CREATE POLICY "wav_admin_all" ON keypoints FOR ALL
  USING (auth.user_role() = 'wav_admin');
CREATE POLICY "wav_admin_all" ON keypoint_verbatims FOR ALL
  USING (auth.user_role() = 'wav_admin');
CREATE POLICY "wav_admin_all" ON action_plans FOR ALL
  USING (auth.user_role() = 'wav_admin');
CREATE POLICY "wav_admin_all" ON action_plan_verbatims FOR ALL
  USING (auth.user_role() = 'wav_admin');
CREATE POLICY "wav_admin_all" ON processing_jobs FOR ALL
  USING (auth.user_role() = 'wav_admin');
CREATE POLICY "wav_admin_all" ON programs FOR ALL
  USING (auth.user_role() = 'wav_admin');
CREATE POLICY "wav_admin_all" ON focus_groups FOR ALL
  USING (auth.user_role() = 'wav_admin');
CREATE POLICY "wav_admin_all" ON days FOR ALL
  USING (auth.user_role() = 'wav_admin');
CREATE POLICY "wav_admin_all" ON user_sessions FOR ALL
  USING (auth.user_role() = 'wav_admin');

-- mg_client: read-only on ready sessions + related data
CREATE POLICY "mg_client_read_sessions" ON sessions FOR SELECT
  USING (auth.user_role() = 'mg_client' AND status = 'ready');
CREATE POLICY "mg_client_read_media" ON media_files FOR SELECT
  USING (auth.user_role() = 'mg_client' AND
    session_id IN (SELECT id FROM sessions WHERE status = 'ready'));
CREATE POLICY "mg_client_read_participants" ON participants FOR SELECT
  USING (auth.user_role() = 'mg_client' AND
    session_id IN (SELECT id FROM sessions WHERE status = 'ready'));
CREATE POLICY "mg_client_read_verbatims" ON verbatims FOR SELECT
  USING (auth.user_role() = 'mg_client' AND
    session_id IN (SELECT id FROM sessions WHERE status = 'ready'));
CREATE POLICY "mg_client_read_embeddings" ON verbatim_embeddings FOR SELECT
  USING (auth.user_role() = 'mg_client' AND
    verbatim_id IN (SELECT id FROM verbatims WHERE
      session_id IN (SELECT id FROM sessions WHERE status = 'ready')));
CREATE POLICY "mg_client_read_keypoints" ON keypoints FOR SELECT
  USING (auth.user_role() = 'mg_client' AND
    session_id IN (SELECT id FROM sessions WHERE status = 'ready'));
CREATE POLICY "mg_client_read_action_plans" ON action_plans FOR SELECT
  USING (auth.user_role() = 'mg_client' AND
    (session_id IS NULL OR
     session_id IN (SELECT id FROM sessions WHERE status = 'ready')));
CREATE POLICY "mg_client_update_action_plans" ON action_plans FOR UPDATE
  USING (auth.user_role() = 'mg_client')
  WITH CHECK (auth.user_role() = 'mg_client');

-- moderator: read-only on assigned sessions
CREATE POLICY "moderator_read_sessions" ON sessions FOR SELECT
  USING (auth.user_role() = 'moderator' AND
    id IN (SELECT session_id FROM user_sessions WHERE user_id = auth.uid()));
CREATE POLICY "moderator_read_media" ON media_files FOR SELECT
  USING (auth.user_role() = 'moderator' AND
    session_id IN (SELECT session_id FROM user_sessions WHERE user_id = auth.uid()));
CREATE POLICY "moderator_read_participants" ON participants FOR SELECT
  USING (auth.user_role() = 'moderator' AND
    session_id IN (SELECT session_id FROM user_sessions WHERE user_id = auth.uid()));
CREATE POLICY "moderator_read_verbatims" ON verbatims FOR SELECT
  USING (auth.user_role() = 'moderator' AND
    session_id IN (SELECT session_id FROM user_sessions WHERE user_id = auth.uid()));
CREATE POLICY "moderator_read_keypoints" ON keypoints FOR SELECT
  USING (auth.user_role() = 'moderator' AND
    session_id IN (SELECT session_id FROM user_sessions WHERE user_id = auth.uid()));
```

- [ ] **Step 6: Write `003_indexes.sql`**

```sql
-- supabase/migrations/003_indexes.sql

-- Verbatim queries
CREATE INDEX idx_verbatims_session ON verbatims(session_id);
CREATE INDEX idx_verbatims_participant ON verbatims(participant_id);
CREATE INDEX idx_verbatims_topic ON verbatims(topic);
CREATE INDEX idx_verbatims_sentiment ON verbatims(sentiment);
CREATE INDEX idx_verbatims_session_topic ON verbatims(session_id, topic);

-- HNSW index for fast cosine similarity search
CREATE INDEX idx_verbatim_embeddings_vector ON verbatim_embeddings
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_verbatim_embeddings_verbatim ON verbatim_embeddings(verbatim_id);

-- Processing jobs
CREATE INDEX idx_processing_jobs_session ON processing_jobs(session_id);
CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);

-- Moderator assignments
CREATE INDEX idx_user_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_session ON user_sessions(session_id);

-- Media lookups
CREATE INDEX idx_media_files_session ON media_files(session_id);
CREATE INDEX idx_media_files_type ON media_files(session_id, type);

-- Action plans
CREATE INDEX idx_action_plans_session ON action_plans(session_id);
CREATE INDEX idx_action_plans_status ON action_plans(status);
```

- [ ] **Step 7: Apply migrations**

```bash
npx supabase db push
```

- [ ] **Step 8: Run test — expect PASS**

```bash
npx vitest run tests/integration/schema.test.ts
# Expected: 3 passing
```

- [ ] **Step 9: Commit**

```bash
git add supabase/ tests/integration/schema.test.ts
git commit -m "feat: database schema with RLS policies and indexes"
```

---

### Task 1.3: Supabase auth clients + middleware

**Files:**
- Create: `src/lib/supabase/client.ts`
- Create: `src/lib/supabase/server.ts`
- Create: `src/lib/supabase/middleware.ts`
- Create: `src/middleware.ts`
- Create: `src/lib/utils/auth.ts`

- [ ] **Step 1: Write failing test for role extraction**

```typescript
// tests/unit/auth.test.ts
import { describe, it, expect } from 'vitest'
import { getRoleFromToken } from '@/lib/utils/auth'

describe('getRoleFromToken', () => {
  it('extracts role from app_metadata', () => {
    const jwt = {
      app_metadata: { role: 'wav_admin' },
      user_metadata: { role: 'should_be_ignored' },
    }
    expect(getRoleFromToken(jwt)).toBe('wav_admin')
  })

  it('returns null when no role', () => {
    expect(getRoleFromToken({})).toBeNull()
  })

  it('ignores user_metadata role (security)', () => {
    const jwt = { user_metadata: { role: 'wav_admin' } }
    expect(getRoleFromToken(jwt)).toBeNull()
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
npx vitest run tests/unit/auth.test.ts
```

- [ ] **Step 3: Implement `src/lib/utils/auth.ts`**

```typescript
// src/lib/utils/auth.ts
export type UserRole = 'wav_admin' | 'mg_client' | 'moderator'

export function getRoleFromToken(jwt: Record<string, unknown>): UserRole | null {
  const appMetadata = jwt['app_metadata']
  if (appMetadata && typeof appMetadata === 'object') {
    const role = (appMetadata as Record<string, unknown>)['role']
    if (role === 'wav_admin' || role === 'mg_client' || role === 'moderator') {
      return role
    }
  }
  return null
}

export function requireRole(role: UserRole | null, required: UserRole | UserRole[]): boolean {
  if (!role) return false
  const roles = Array.isArray(required) ? required : [required]
  return roles.includes(role)
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
npx vitest run tests/unit/auth.test.ts
```

- [ ] **Step 5: Implement Supabase clients**

```typescript
// src/lib/supabase/client.ts
import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}
```

```typescript
// src/lib/supabase/server.ts
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function createClient() {
  const cookieStore = await cookies()
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return cookieStore.getAll() },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options))
          } catch { /* server component, ignore */ }
        },
      },
    }
  )
}

export async function createServiceClient() {
  const cookieStore = await cookies()
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    {
      cookies: {
        getAll() { return cookieStore.getAll() },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options))
          } catch {}
        },
      },
    }
  )
}
```

```typescript
// src/middleware.ts
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
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

  const { data: { user } } = await supabase.auth.getUser()

  const isPublicPath = request.nextUrl.pathname.startsWith('/login') ||
    request.nextUrl.pathname.startsWith('/api/auth')

  if (!user && !isPublicPath) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return supabaseResponse
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
```

- [ ] **Step 6: Commit**

```bash
git add src/lib/supabase/ src/middleware.ts src/lib/utils/auth.ts tests/unit/auth.test.ts
git commit -m "feat: Supabase auth clients, middleware, role extraction"
```

---

### Task 1.4: MG dark theme + global CSS

**Files:**
- Modify: `src/app/globals.css`
- Create: `tailwind.config.ts`

- [ ] **Step 1: Configure MG brand tokens in globals.css**

```css
/* src/app/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* MG Dark Theme (default) */
    --background: 240 10% 4%;       /* #080810 */
    --foreground: 30 33% 95%;       /* #F7F3EF MG White */

    --card: 240 10% 7%;
    --card-foreground: 30 33% 95%;

    --primary: 347 100% 31%;        /* #A00022 MG Red */
    --primary-foreground: 30 33% 95%;

    --secondary: 326 100% 9%;       /* #28001E MG Burgundy */
    --secondary-foreground: 30 33% 95%;

    --accent: 358 98% 59%;          /* #FD2F33 MG Smoke */
    --accent-foreground: 0 0% 100%;

    --muted: 240 5% 15%;
    --muted-foreground: 240 5% 55%;

    --border: 240 5% 18%;
    --input: 240 5% 18%;
    --ring: 347 100% 31%;

    --radius: 0.5rem;

    /* MG brand custom vars */
    --mg-red: #A00022;
    --mg-burgundy: #28001E;
    --mg-smoke: #FD2F33;
    --mg-white: #F7F3EF;
    --mg-bg: #080810;
  }
}

@layer base {
  * { @apply border-border; }
  body {
    @apply bg-background text-foreground;
    font-family: 'Favorit', system-ui, sans-serif;
  }
  /* Favorit Mono for labels, data, timestamps */
  .font-mono { font-family: 'Favorit Mono', 'Courier New', monospace; }
}
```

- [ ] **Step 2: Update tailwind.config.ts to extend with MG colors**

```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ['class'],
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'mg-red': '#A00022',
        'mg-burgundy': '#28001E',
        'mg-smoke': '#FD2F33',
        'mg-white': '#F7F3EF',
        'mg-bg': '#080810',
      },
      fontFamily: {
        sans: ['Favorit', 'system-ui', 'sans-serif'],
        mono: ['Favorit Mono', 'Courier New', 'monospace'],
      },
    },
  },
  plugins: [],
}
export default config
```

- [ ] **Step 3: Commit**

```bash
git add src/app/globals.css tailwind.config.ts
git commit -m "feat: MG dark brand theme tokens"
```

---

### Task 1.5: Login page + magic link auth

**Files:**
- Create: `src/app/login/page.tsx`
- Create: `src/components/auth/login-form.tsx`
- Create: `src/app/api/auth/callback/route.ts`

- [ ] **Step 1: Implement auth callback route**

```typescript
// src/app/api/auth/callback/route.ts
import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')
  const next = searchParams.get('next') ?? '/dashboard'

  if (code) {
    const supabase = await createClient()
    const { error } = await supabase.auth.exchangeCodeForSession(code)
    if (!error) {
      return NextResponse.redirect(`${origin}${next}`)
    }
  }
  return NextResponse.redirect(`${origin}/login?error=auth_callback_error`)
}
```

- [ ] **Step 2: Implement login form component**

```typescript
// src/components/auth/login-form.tsx
'use client'
import { useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

export function LoginForm() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    const supabase = createClient()
    await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/api/auth/callback`,
      },
    })
    setSent(true)
    setLoading(false)
  }

  return (
    <Card className="w-full max-w-md border-border bg-card">
      <CardHeader>
        <CardTitle className="text-mg-white">WAV Intelligence</CardTitle>
        <CardDescription>Enter your email to receive a magic link</CardDescription>
      </CardHeader>
      <CardContent>
        {sent ? (
          <p className="text-sm text-muted-foreground">
            Check your inbox — a login link has been sent to <strong>{email}</strong>.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
              />
            </div>
            <Button type="submit" className="w-full bg-mg-red hover:bg-mg-red/90" disabled={loading}>
              {loading ? 'Sending…' : 'Send magic link'}
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 3: Implement login page**

```typescript
// src/app/login/page.tsx
import { LoginForm } from '@/components/auth/login-form'

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-mg-bg flex items-center justify-center p-4">
      <LoginForm />
    </main>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add src/app/login/ src/components/auth/ src/app/api/auth/
git commit -m "feat: magic link login page and auth callback"
```

---

### Task 1.6: Role-based dashboard landing

**Files:**
- Create: `src/app/dashboard/page.tsx`
- Create: `src/app/page.tsx`
- Create: `src/components/dashboard/wav-admin-dashboard.tsx`
- Create: `src/components/dashboard/mg-client-dashboard.tsx`
- Create: `src/components/dashboard/moderator-dashboard.tsx`
- Create: `src/app/layout.tsx`

- [ ] **Step 1: Write failing test for role-based routing**

```typescript
// tests/unit/dashboard-routing.test.ts
import { describe, it, expect } from 'vitest'
import { getDashboardComponent } from '@/lib/utils/auth'

describe('getDashboardComponent', () => {
  it('returns wav_admin component for wav_admin role', () => {
    expect(getDashboardComponent('wav_admin')).toBe('WavAdminDashboard')
  })
  it('returns mg_client component for mg_client role', () => {
    expect(getDashboardComponent('mg_client')).toBe('MgClientDashboard')
  })
  it('returns moderator component for moderator role', () => {
    expect(getDashboardComponent('moderator')).toBe('ModeratorDashboard')
  })
})
```

- [ ] **Step 2: Extend auth.ts with getDashboardComponent**

```typescript
// Add to src/lib/utils/auth.ts
export function getDashboardComponent(role: UserRole): string {
  const map: Record<UserRole, string> = {
    wav_admin: 'WavAdminDashboard',
    mg_client: 'MgClientDashboard',
    moderator: 'ModeratorDashboard',
  }
  return map[role]
}
```

- [ ] **Step 3: Run test — expect PASS**

```bash
npx vitest run tests/unit/dashboard-routing.test.ts
```

- [ ] **Step 4: Implement root layout**

```typescript
// src/app/layout.tsx
import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'WAV Intelligence',
  description: 'Focus group insights dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="dark">
      <body className="min-h-screen bg-mg-bg antialiased">{children}</body>
    </html>
  )
}
```

- [ ] **Step 5: Implement redirect from root**

```typescript
// src/app/page.tsx
import { redirect } from 'next/navigation'
export default function RootPage() {
  redirect('/dashboard')
}
```

- [ ] **Step 6: Implement role-based dashboard**

```typescript
// src/app/dashboard/page.tsx
import { createClient } from '@/lib/supabase/server'
import { getRoleFromToken } from '@/lib/utils/auth'
import { redirect } from 'next/navigation'
import { WavAdminDashboard } from '@/components/dashboard/wav-admin-dashboard'
import { MgClientDashboard } from '@/components/dashboard/mg-client-dashboard'
import { ModeratorDashboard } from '@/components/dashboard/moderator-dashboard'

export default async function DashboardPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const { data: { session } } = await supabase.auth.getSession()
  const jwt = session ? JSON.parse(atob(session.access_token.split('.')[1])) : {}
  const role = getRoleFromToken(jwt)

  if (role === 'wav_admin') return <WavAdminDashboard />
  if (role === 'mg_client') return <MgClientDashboard />
  if (role === 'moderator') return <ModeratorDashboard />

  return (
    <main className="p-8">
      <p className="text-muted-foreground">
        Your account has not been assigned a role. Contact your WAV administrator.
      </p>
    </main>
  )
}
```

- [ ] **Step 7: Implement stub dashboard components**

```typescript
// src/components/dashboard/wav-admin-dashboard.tsx
export function WavAdminDashboard() {
  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold text-mg-white mb-2">WAV Admin Dashboard</h1>
      <p className="text-muted-foreground">Processing queue and session management coming in P2.</p>
    </main>
  )
}
```

```typescript
// src/components/dashboard/mg-client-dashboard.tsx
export function MgClientDashboard() {
  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold text-mg-white mb-2">MG Intelligence Dashboard</h1>
      <p className="text-muted-foreground">Latest session insights coming in P3.</p>
    </main>
  )
}
```

```typescript
// src/components/dashboard/moderator-dashboard.tsx
export function ModeratorDashboard() {
  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold text-mg-white mb-2">Moderator View</h1>
      <p className="text-muted-foreground">Assigned sessions coming in P2.</p>
    </main>
  )
}
```

- [ ] **Step 8: Commit**

```bash
git add src/app/ src/components/dashboard/ tests/unit/dashboard-routing.test.ts
git commit -m "feat: role-based dashboard landing (P1 complete)"
```

---

### Task 1.7: Deploy P1 to Vercel

- [ ] **Step 1: Create new GitHub repo `wav-intelligence`**

```bash
gh repo create wav-intelligence --private --source=. --push
```

- [ ] **Step 2: Connect to Vercel and add env vars**

```bash
vercel link
vercel env add NEXT_PUBLIC_SUPABASE_URL
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY
vercel env add SUPABASE_SERVICE_ROLE_KEY
# ... add all env vars from .env.example
vercel deploy --prod
```

- [ ] **Step 3: Verify deployment — smoke test**

  - Navigate to deployed URL → should redirect to `/login`
  - Send magic link → check email → click link → land on `/dashboard`
  - Verify role-based component renders (requires setting role in Supabase app_metadata via service role)

- [ ] **Step 4: Commit**

```bash
git add vercel.json
git commit -m "chore: Vercel deployment config"
```

**P1 DONE ✅ — Auth working, 3 roles enforced at DB layer, MG dark theme deployed**

---

## Phase 2 — Admin: Session Creation + Upload + Participant Setup

**Deliverable:** WAV Admin can create a session (program → focus group → day → session), upload files (360 video, DSLR, 13 audio) directly to R2 via presigned URLs, assign mics to participants, and tag seat positions on the 360 frame.

**Done when:** Files appear in R2. MediaFile records in DB. Session status = 'uploaded'. Ready to trigger processing.

---

### Task 2.1: Cloudflare R2 client + presigned upload

**Files:**
- Create: `src/lib/r2/client.ts`
- Create: `src/lib/r2/upload.ts`
- Create: `src/lib/r2/stream.ts`
- Create: `tests/unit/r2-upload.test.ts`

- [ ] **Step 1: Write failing test**

```typescript
// tests/unit/r2-upload.test.ts
import { describe, it, expect, vi } from 'vitest'
import { buildR2Key } from '@/lib/r2/upload'

describe('buildR2Key', () => {
  it('builds raw 360 key', () => {
    expect(buildR2Key('sess-123', 'video_360', 'raw'))
      .toBe('sessions/sess-123/raw/360.mp4')
  })
  it('builds raw audio key with mic number', () => {
    expect(buildR2Key('sess-123', 'audio', 'raw', { micNumber: 3 }))
      .toBe('sessions/sess-123/raw/audio/mic-03.wav')
  })
  it('builds processed HLS key', () => {
    expect(buildR2Key('sess-123', 'video_360', 'processed'))
      .toBe('sessions/sess-123/processed/360/master.m3u8')
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
npx vitest run tests/unit/r2-upload.test.ts
```

- [ ] **Step 3: Implement `src/lib/r2/upload.ts`**

```typescript
// src/lib/r2/upload.ts
import { S3Client, CreateMultipartUploadCommand,
  UploadPartCommand, CompleteMultipartUploadCommand,
  PutObjectCommand } from '@aws-sdk/client-s3'
import { getSignedUrl } from '@aws-sdk/s3-request-presigner'
import { getR2Client } from './client'

type MediaType = 'video_360' | 'video_dslr' | 'audio'
type StorageStage = 'raw' | 'processed'

interface R2KeyOptions { micNumber?: number }

export function buildR2Key(
  sessionId: string,
  type: MediaType,
  stage: StorageStage,
  opts: R2KeyOptions = {}
): string {
  const base = `sessions/${sessionId}`
  if (stage === 'raw') {
    if (type === 'video_360') return `${base}/raw/360.mp4`
    if (type === 'video_dslr') return `${base}/raw/dslr.mp4`
    if (type === 'audio' && opts.micNumber !== undefined) {
      const n = String(opts.micNumber).padStart(2, '0')
      return `${base}/raw/audio/mic-${n}.wav`
    }
  }
  if (stage === 'processed') {
    if (type === 'video_360') return `${base}/processed/360/master.m3u8`
    if (type === 'video_dslr') return `${base}/processed/dslr/master.m3u8`
  }
  throw new Error(`Cannot build R2 key for type=${type} stage=${stage}`)
}

export async function getPresignedUploadUrl(key: string): Promise<string> {
  const client = getR2Client()
  const command = new PutObjectCommand({
    Bucket: process.env.R2_BUCKET_NAME!,
    Key: key,
  })
  return getSignedUrl(client, command, { expiresIn: 3600 })
}
```

```typescript
// src/lib/r2/client.ts
import { S3Client } from '@aws-sdk/client-s3'

let client: S3Client | null = null

export function getR2Client(): S3Client {
  if (!client) {
    client = new S3Client({
      region: 'auto',
      endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
      credentials: {
        accessKeyId: process.env.R2_ACCESS_KEY_ID!,
        secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!,
      },
    })
  }
  return client
}
```

```typescript
// src/lib/r2/stream.ts
import { GetObjectCommand } from '@aws-sdk/client-s3'
import { getSignedUrl } from '@aws-sdk/s3-request-presigner'
import { getR2Client } from './client'

export async function getSignedStreamUrl(key: string, expiresIn = 3600): Promise<string> {
  const client = getR2Client()
  const command = new GetObjectCommand({
    Bucket: process.env.R2_BUCKET_NAME!,
    Key: key,
  })
  return getSignedUrl(client, command, { expiresIn })
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
npx vitest run tests/unit/r2-upload.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add src/lib/r2/ tests/unit/r2-upload.test.ts
git commit -m "feat: Cloudflare R2 client with presigned URL generation"
```

---

### Task 2.2: Upload API route + upload UI

**Files:**
- Create: `src/app/api/sessions/[id]/upload-url/route.ts`
- Create: `src/app/api/sessions/[id]/upload-complete/route.ts`
- Create: `src/components/upload/file-upload-zone.tsx`
- Create: `src/components/upload/upload-progress.tsx`

- [ ] **Step 1: Write failing test for upload-url endpoint**

```typescript
// tests/unit/upload-url-validation.test.ts
import { describe, it, expect } from 'vitest'
import { validateUploadRequest } from '@/lib/r2/upload'

describe('validateUploadRequest', () => {
  it('accepts valid video_360 upload', () => {
    expect(() => validateUploadRequest({ type: 'video_360', filename: 'session.mp4' }))
      .not.toThrow()
  })
  it('rejects unknown file type', () => {
    expect(() => validateUploadRequest({ type: 'invalid', filename: 'file.mp4' }))
      .toThrow('Invalid media type')
  })
  it('rejects disallowed MIME extension', () => {
    expect(() => validateUploadRequest({ type: 'video_360', filename: 'file.exe' }))
      .toThrow('Disallowed file extension')
  })
})
```

- [ ] **Step 2: Add validation to upload.ts**

```typescript
// Add to src/lib/r2/upload.ts
const ALLOWED_EXTENSIONS: Record<string, string[]> = {
  video_360: ['.mp4', '.mov'],
  video_dslr: ['.mp4', '.mov'],
  audio: ['.wav', '.aif', '.aiff'],
}

export function validateUploadRequest(req: { type: string; filename: string }): void {
  const validTypes = ['video_360', 'video_dslr', 'audio']
  if (!validTypes.includes(req.type)) throw new Error('Invalid media type')
  const ext = '.' + req.filename.split('.').pop()?.toLowerCase()
  const allowed = ALLOWED_EXTENSIONS[req.type] ?? []
  if (!allowed.includes(ext)) throw new Error('Disallowed file extension')
}
```

- [ ] **Step 3: Run test — expect PASS**

```bash
npx vitest run tests/unit/upload-url-validation.test.ts
```

- [ ] **Step 4: Implement upload-url API route**

```typescript
// src/app/api/sessions/[id]/upload-url/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createServiceClient } from '@/lib/supabase/server'
import { getRoleFromToken } from '@/lib/utils/auth'
import { getPresignedUploadUrl, buildR2Key, validateUploadRequest } from '@/lib/r2/upload'

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const supabase = await createServiceClient()
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const jwt = JSON.parse(atob(session.access_token.split('.')[1]))
  const role = getRoleFromToken(jwt)
  if (role !== 'wav_admin') return NextResponse.json({ error: 'Forbidden' }, { status: 403 })

  const { id } = await params
  const body = await request.json()

  try {
    validateUploadRequest(body)
  } catch (err) {
    return NextResponse.json({ error: (err as Error).message }, { status: 400 })
  }

  const key = buildR2Key(id, body.type, 'raw', { micNumber: body.micNumber })
  const url = await getPresignedUploadUrl(key)
  return NextResponse.json({ url, key })
}
```

- [ ] **Step 5: Implement upload-complete route**

```typescript
// src/app/api/sessions/[id]/upload-complete/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createServiceClient } from '@/lib/supabase/server'
import { getRoleFromToken } from '@/lib/utils/auth'

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const supabase = await createServiceClient()
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const jwt = JSON.parse(atob(session.access_token.split('.')[1]))
  const role = getRoleFromToken(jwt)
  if (role !== 'wav_admin') return NextResponse.json({ error: 'Forbidden' }, { status: 403 })

  const { id: sessionId } = await params
  const { files } = await request.json() as {
    files: Array<{ type: string; r2_key: string; original_filename: string;
      file_size_bytes: number; mic_number?: number }>
  }

  const { error } = await supabase.from('media_files').insert(
    files.map(f => ({
      session_id: sessionId,
      type: f.type,
      r2_key: f.r2_key,
      r2_bucket: process.env.R2_BUCKET_NAME!,
      original_filename: f.original_filename,
      file_size_bytes: f.file_size_bytes,
      mic_number: f.mic_number ?? null,
    }))
  )
  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  await supabase.from('sessions').update({ status: 'uploaded' }).eq('id', sessionId)
  return NextResponse.json({ ok: true })
}
```

- [ ] **Step 6: Commit**

```bash
git add src/app/api/sessions/ src/lib/r2/ tests/unit/upload-url-validation.test.ts
git commit -m "feat: R2 presigned upload URLs + upload-complete endpoint"
```

---

### Task 2.3: Session creation UI + participant setup

**Files:**
- Create: `src/app/admin/sessions/new/page.tsx`
- Create: `src/app/admin/sessions/[id]/setup/page.tsx`
- Create: `src/app/api/sessions/route.ts`
- Create: `src/app/api/sessions/[id]/participants/route.ts`

- [ ] **Step 1: Session creation API route**

```typescript
// src/app/api/sessions/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createServiceClient } from '@/lib/supabase/server'
import { getRoleFromToken } from '@/lib/utils/auth'
import { z } from 'zod'

const CreateSessionSchema = z.object({
  program_id: z.string().uuid(),
  quarter: z.enum(['Q1', 'Q2', 'Q3', 'Q4']),
  day_number: z.number().int().min(1).max(3),
  name: z.string().min(1).max(100),
  date: z.string().optional(),
})

export async function POST(request: NextRequest) {
  const supabase = await createServiceClient()
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const jwt = JSON.parse(atob(session.access_token.split('.')[1]))
  if (getRoleFromToken(jwt) !== 'wav_admin') {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 })
  }

  const parsed = CreateSessionSchema.safeParse(await request.json())
  if (!parsed.success) return NextResponse.json({ error: parsed.error }, { status: 400 })

  const { program_id, quarter, day_number, name, date } = parsed.data

  // Upsert focus_group and day
  const { data: fg } = await supabase.from('focus_groups')
    .upsert({ program_id, quarter }, { onConflict: 'program_id,quarter' })
    .select('id').single()

  const { data: day } = await supabase.from('days')
    .upsert({ focus_group_id: fg!.id, day_number, date }, { onConflict: 'focus_group_id,day_number' })
    .select('id').single()

  const { data: sess, error } = await supabase.from('sessions')
    .insert({ day_id: day!.id, name }).select().single()

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  return NextResponse.json(sess, { status: 201 })
}

export async function GET(request: NextRequest) {
  const supabase = await createServiceClient()
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { data, error } = await supabase
    .from('sessions')
    .select('*, days(day_number, date, focus_groups(quarter, programs(name, year)))')
    .order('created_at', { ascending: false })

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  return NextResponse.json(data)
}
```

- [ ] **Step 2: Participant assignment API route**

```typescript
// src/app/api/sessions/[id]/participants/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createServiceClient } from '@/lib/supabase/server'
import { getRoleFromToken } from '@/lib/utils/auth'
import { z } from 'zod'

const ParticipantSchema = z.object({
  name: z.string().min(1),
  mg_model: z.string().optional(),
  mic_number: z.number().int().min(1).max(13),
})

const BulkParticipantsSchema = z.object({
  participants: z.array(ParticipantSchema),
})

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const supabase = await createServiceClient()
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const jwt = JSON.parse(atob(session.access_token.split('.')[1]))
  if (getRoleFromToken(jwt) !== 'wav_admin') {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 })
  }

  const { id: sessionId } = await params
  const parsed = BulkParticipantsSchema.safeParse(await request.json())
  if (!parsed.success) return NextResponse.json({ error: parsed.error }, { status: 400 })

  // Delete existing and re-insert (bulk upsert)
  await supabase.from('participants').delete().eq('session_id', sessionId)

  const { data, error } = await supabase.from('participants').insert(
    parsed.data.participants.map(p => ({ ...p, session_id: sessionId }))
  ).select()

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  return NextResponse.json(data, { status: 201 })
}
```

- [ ] **Step 3: Commit**

```bash
git add src/app/api/sessions/ src/app/admin/
git commit -m "feat: session creation + participant mic assignment API"
```

**P2 DONE ✅ — Admin can create sessions, upload files to R2, assign participants to mics**

---

## Phase 3 — Processing Pipeline (Trigger.dev + ffmpeg + ElevenLabs + AI)

**Deliverable:** Clicking "Process Session" dispatches a Trigger.dev job that (1) transcodes video to HLS, (2) generates audio waveform peaks, (3) transcribes with ElevenLabs Scribe, (4) runs AI enrichment (topics + sentiment + keypoints + action plans), (5) generates embeddings. Session status → 'ready'. Dashboard shows progress bar.

**Done when:** A test session with real (or mock) audio files can be processed end-to-end. Verbatims appear in DB with topics and sentiment. Action plans generated.

---

### Task 3.1: Transcription adapter layer

**Files:**
- Create: `src/lib/transcription/types.ts`
- Create: `src/lib/transcription/elevenlabs-scribe.ts`
- Create: `src/lib/transcription/deepgram-nova3.ts`
- Create: `src/lib/transcription/whisper-local.ts`
- Create: `src/lib/transcription/index.ts`
- Create: `tests/unit/transcription/elevenlabs-scribe.test.ts`

- [ ] **Step 1: Write failing test for adapter interface**

```typescript
// tests/unit/transcription/elevenlabs-scribe.test.ts
import { describe, it, expect, vi } from 'vitest'
import { ElevenLabsScribeProvider } from '@/lib/transcription/elevenlabs-scribe'

describe('ElevenLabsScribeProvider', () => {
  it('implements TranscriptionProvider interface', () => {
    const provider = new ElevenLabsScribeProvider('fake-key')
    expect(typeof provider.transcribe).toBe('function')
  })

  it('maps response to standard Transcript format', async () => {
    const mockResponse = {
      words: [
        { text: 'Hola', start: 0.1, end: 0.5, speaker_id: 'speaker_0' },
        { text: 'mundo', start: 0.6, end: 1.0, speaker_id: 'speaker_0' },
      ]
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    }))

    const provider = new ElevenLabsScribeProvider('fake-key')
    const result = await provider.transcribe('https://example.com/audio.wav', 'es')

    expect(result.segments).toHaveLength(1)
    expect(result.segments[0].text).toBe('Hola mundo')
    expect(result.segments[0].start).toBe(0.1)
    expect(result.segments[0].speakerId).toBe('speaker_0')
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
npx vitest run tests/unit/transcription/
```

- [ ] **Step 3: Implement types + adapters**

```typescript
// src/lib/transcription/types.ts
export interface TranscriptSegment {
  text: string
  start: number
  end: number
  speakerId: string
  confidence?: number
}

export interface Transcript {
  language: string
  duration: number
  segments: TranscriptSegment[]
  rawResponse?: unknown
}

export interface TranscriptionProvider {
  transcribe(audioUrl: string, language: string): Promise<Transcript>
}
```

```typescript
// src/lib/transcription/elevenlabs-scribe.ts
import type { Transcript, TranscriptSegment, TranscriptionProvider } from './types'

export class ElevenLabsScribeProvider implements TranscriptionProvider {
  constructor(private apiKey: string) {}

  async transcribe(audioUrl: string, language: string): Promise<Transcript> {
    const response = await fetch('https://api.elevenlabs.io/v1/speech-to-text', {
      method: 'POST',
      headers: {
        'xi-api-key': this.apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        audio_url: audioUrl,
        language_code: language,
        diarize: true,
        timestamps_granularity: 'word',
      }),
    })

    if (!response.ok) {
      throw new Error(`ElevenLabs error: ${response.status} ${await response.text()}`)
    }

    const data = await response.json()
    return this.mapResponse(data, language)
  }

  private mapResponse(data: { words: Array<{ text: string; start: number; end: number; speaker_id: string }> }, language: string): Transcript {
    // Group consecutive words by speaker into segments
    const segments: TranscriptSegment[] = []
    let current: TranscriptSegment | null = null

    for (const word of data.words) {
      if (!current || current.speakerId !== word.speaker_id) {
        if (current) segments.push(current)
        current = { text: word.text, start: word.start, end: word.end, speakerId: word.speaker_id }
      } else {
        current.text += ' ' + word.text
        current.end = word.end
      }
    }
    if (current) segments.push(current)

    const duration = segments.length > 0 ? segments[segments.length - 1].end : 0
    return { language, duration, segments, rawResponse: data }
  }
}
```

```typescript
// src/lib/transcription/deepgram-nova3.ts
import type { Transcript, TranscriptSegment, TranscriptionProvider } from './types'

export class DeepgramNova3Provider implements TranscriptionProvider {
  constructor(private apiKey: string) {}

  async transcribe(audioUrl: string, language: string): Promise<Transcript> {
    const response = await fetch(
      `https://api.deepgram.com/v1/listen?model=nova-3&language=${language}&diarize=true&punctuate=true&utterances=true`,
      {
        method: 'POST',
        headers: {
          Authorization: `Token ${this.apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: audioUrl }),
      }
    )

    if (!response.ok) {
      throw new Error(`Deepgram error: ${response.status}`)
    }

    const data = await response.json()
    const utterances = data?.results?.utterances ?? []

    const segments: TranscriptSegment[] = utterances.map((u: { transcript: string; start: number; end: number; speaker: number }) => ({
      text: u.transcript,
      start: u.start,
      end: u.end,
      speakerId: `speaker_${u.speaker}`,
    }))

    const duration = segments.length > 0 ? segments[segments.length - 1].end : 0
    return { language, duration, segments, rawResponse: data }
  }
}
```

```typescript
// src/lib/transcription/whisper-local.ts
// Stub for A/B test against local/self-hosted Whisper.
// Implement when running the pre-production benchmark.
import type { Transcript, TranscriptionProvider } from './types'

export class WhisperLocalProvider implements TranscriptionProvider {
  constructor(private endpoint: string) {}

  async transcribe(audioUrl: string, language: string): Promise<Transcript> {
    const response = await fetch(`${this.endpoint}/transcribe`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ audio_url: audioUrl, language }),
    })
    if (!response.ok) throw new Error(`Whisper error: ${response.status}`)
    const data = await response.json()
    // Map Whisper response format to shared Transcript type
    return {
      language,
      duration: data.duration ?? 0,
      segments: (data.segments ?? []).map((s: { text: string; start: number; end: number; speaker?: string }) => ({
        text: s.text,
        start: s.start,
        end: s.end,
        speakerId: s.speaker ?? 'speaker_0',
      })),
      rawResponse: data,
    }
  }
}
```

```typescript
// src/lib/transcription/index.ts
import { ElevenLabsScribeProvider } from './elevenlabs-scribe'
import { DeepgramNova3Provider } from './deepgram-nova3'
import { WhisperLocalProvider } from './whisper-local'
import type { TranscriptionProvider } from './types'

export type ProviderName = 'elevenlabs' | 'deepgram' | 'whisper'

export function getTranscriptionProvider(name: ProviderName = 'elevenlabs'): TranscriptionProvider {
  if (name === 'elevenlabs') {
    if (!process.env.ELEVENLABS_API_KEY) throw new Error('ELEVENLABS_API_KEY not set')
    return new ElevenLabsScribeProvider(process.env.ELEVENLABS_API_KEY)
  }
  if (name === 'deepgram') {
    if (!process.env.DEEPGRAM_API_KEY) throw new Error('DEEPGRAM_API_KEY not set')
    return new DeepgramNova3Provider(process.env.DEEPGRAM_API_KEY)
  }
  if (name === 'whisper') {
    const endpoint = process.env.WHISPER_ENDPOINT ?? 'http://localhost:9000'
    return new WhisperLocalProvider(endpoint)
  }
  throw new Error(`Unknown transcription provider: ${name}`)
}

export type { TranscriptionProvider, Transcript, TranscriptSegment } from './types'
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
npx vitest run tests/unit/transcription/
```

- [ ] **Step 5: Commit**

```bash
git add src/lib/transcription/ tests/unit/transcription/
git commit -m "feat: transcription adapter layer (ElevenLabs + Deepgram)"
```

---

### Task 3.2: AI enrichment functions

**Files:**
- Create: `src/lib/ai/classify-topics.ts`
- Create: `src/lib/ai/analyze-sentiment.ts`
- Create: `src/lib/ai/extract-keypoints.ts`
- Create: `src/lib/ai/generate-action-plans.ts`
- Create: `src/lib/ai/embed-verbatims.ts`
- Create: `tests/unit/ai/classify-topics.test.ts`
- Create: `tests/unit/ai/generate-action-plans.test.ts`

- [ ] **Step 1: Write failing test for topic classification**

```typescript
// tests/unit/ai/classify-topics.test.ts
import { describe, it, expect } from 'vitest'
import { VALID_TOPICS, mapTextToTopic } from '@/lib/ai/classify-topics'

describe('topic classification', () => {
  it('maps infotainment to correct topic', () => {
    expect(VALID_TOPICS).toContain('infotainment')
  })

  it('mapTextToTopic returns fallback for unknown', () => {
    expect(mapTextToTopic('xyz-unknown')).toBe('otro')
  })

  it('mapTextToTopic handles case-insensitive match', () => {
    expect(mapTextToTopic('Infotainment')).toBe('infotainment')
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
npx vitest run tests/unit/ai/classify-topics.test.ts
```

- [ ] **Step 3: Implement classify-topics.ts**

```typescript
// src/lib/ai/classify-topics.ts
import { generateText } from 'ai'

export const VALID_TOPICS = [
  'marca', 'diseno', 'precio', 'infotainment',
  'postventa', 'seguridad', 'garantia', 'convocatoria', 'otro'
] as const

export type Topic = typeof VALID_TOPICS[number]

export function mapTextToTopic(text: string): Topic {
  const normalized = text.toLowerCase().trim()
  const match = VALID_TOPICS.find(t => t === normalized)
  return match ?? 'otro'
}

export interface VerbatimForClassification {
  id: string
  text: string
}

export async function classifyTopicsBatch(
  verbatims: VerbatimForClassification[]
): Promise<Map<string, Topic>> {
  const chunks: VerbatimForClassification[][] = []
  for (let i = 0; i < verbatims.length; i += 20) {
    chunks.push(verbatims.slice(i, i + 20))
  }

  const results = new Map<string, Topic>()

  for (const chunk of chunks) {
    const formatted = chunk.map((v, i) => `${i + 1}. [${v.id}] "${v.text}"`).join('\n')

    const { text } = await generateText({
      model: 'openai/gpt-5.4',
      system: `You classify focus group verbatims about MG Motor vehicles into topics.
Valid topics: ${VALID_TOPICS.join(', ')}.
Respond ONLY with JSON: {"classifications": [{"id": "...", "topic": "..."}]}`,
      prompt: `Classify these verbatims:\n${formatted}`,
    })

    const parsed = JSON.parse(text)
    for (const item of parsed.classifications) {
      results.set(item.id, mapTextToTopic(item.topic))
    }
  }

  return results
}
```

- [ ] **Step 4: Implement remaining AI functions**

```typescript
// src/lib/ai/analyze-sentiment.ts
import { generateText } from 'ai'

export type Sentiment = 'positivo' | 'neutro' | 'negativo'

export interface SentimentResult {
  verbatimId: string
  sentiment: Sentiment
  score: number
}

export async function analyzeSentimentBatch(
  verbatims: Array<{ id: string; text: string }>
): Promise<SentimentResult[]> {
  const formatted = verbatims.map((v, i) => `${i + 1}. [${v.id}] "${v.text}"`).join('\n')

  const { text } = await generateText({
    model: 'openai/gpt-5.4',
    system: `Analyze sentiment of MG Motor focus group verbatims.
Respond ONLY with JSON: {"results": [{"id": "...", "sentiment": "positivo|neutro|negativo", "score": 0.0-1.0}]}`,
    prompt: formatted,
  })

  const parsed = JSON.parse(text)
  return parsed.results.map((r: { id: string; sentiment: string; score: number }) => ({
    verbatimId: r.id,
    sentiment: r.sentiment as Sentiment,
    score: r.score,
  }))
}
```

```typescript
// src/lib/ai/generate-action-plans.ts
import { generateText } from 'ai'

export interface ActionPlanInput {
  sessionId: string
  keypoints: Array<{ id: string; title: string; description: string; topic: string }>
  verbatims: Array<{ id: string; text: string; topic: string; sentiment: string; sentiment_score: number }>
}

export interface GeneratedActionPlan {
  category: 'quick_win' | 'strategic' | 'monitor'
  title: string
  description: string
  ai_reasoning: string
  impact_score: number
  cost_estimate: 'low' | 'medium' | 'high'
  cognitive_load: 'low' | 'medium' | 'high'
  time_estimate: string
  supporting_verbatim_ids: string[]
}

export async function generateActionPlans(
  input: ActionPlanInput
): Promise<GeneratedActionPlan[]> {
  const keypointSummary = input.keypoints
    .map(k => `[${k.topic}] ${k.title}: ${k.description}`)
    .join('\n')

  const verbatimSummary = input.verbatims
    .filter(v => v.sentiment === 'negativo' || v.sentiment_score > 0.6)
    .slice(0, 50)
    .map(v => `[${v.id}][${v.topic}][${v.sentiment}] "${v.text}"`)
    .join('\n')

  const { text } = await generateText({
    model: 'openai/gpt-5.4',
    system: `You are WAV Strategist — an expert consultant generating action plans for MG Motor Chile. Generate prioritized action plans from focus group insights. Categories: quick_win (high impact, low cost), strategic (high impact, needs investment), monitor (low frequency or unclear). Respond ONLY with JSON: {"action_plans": [{category, title, description, ai_reasoning, impact_score (1 to 10), cost_estimate, cognitive_load, time_estimate, supporting_verbatim_ids}]}`,
    prompt: `Key insights:\n${keypointSummary}\n\nSupporting verbatims:\n${verbatimSummary}`,
  })

  const parsed = JSON.parse(text)
  return parsed.action_plans
}
```

```typescript
// src/lib/ai/embed-verbatims.ts
import { embed } from 'ai'
import { openai } from '@ai-sdk/openai'

export async function embedVerbatims(
  verbatims: Array<{ id: string; text: string }>
): Promise<Array<{ verbatimId: string; embedding: number[] }>> {
  const results: Array<{ verbatimId: string; embedding: number[] }> = []

  // Process in batches of 100
  for (let i = 0; i < verbatims.length; i += 100) {
    const batch = verbatims.slice(i, i + 100)
    await Promise.all(
      batch.map(async v => {
        const { embedding } = await embed({
          model: openai.embedding('text-embedding-3-small'),
          value: v.text,
        })
        results.push({ verbatimId: v.id, embedding: Array.from(embedding) })
      })
    )
  }

  return results
}
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
npx vitest run tests/unit/ai/
```

- [ ] **Step 6: Commit**

```bash
git add src/lib/ai/ tests/unit/ai/
git commit -m "feat: AI enrichment functions (topics, sentiment, action plans, embeddings)"
```

---

### Task 3.3: Trigger.dev pipeline job

**Files:**
- Create: `src/trigger/client.ts`
- Create: `src/trigger/process-session.ts`
- Create: `src/trigger/steps/transcode-360.ts`
- Create: `src/trigger/steps/transcode-dslr.ts`
- Create: `src/trigger/steps/generate-peaks.ts`
- Create: `src/trigger/steps/transcribe-audio.ts`
- Create: `src/trigger/steps/ai-enrichment.ts`
- Create: `src/trigger/steps/generate-embeddings.ts`
- Create: `src/trigger/steps/finalize.ts`
- Create: `src/app/api/sessions/[id]/process/route.ts`
- Create: `src/app/api/cron/check-uploads/route.ts`

- [ ] **Step 1: Install Trigger.dev SDK**

```bash
npm install @trigger.dev/sdk@3
npx trigger.dev@latest init   # follow prompts: Cloud, your project ref
```

- [ ] **Step 2: Implement Trigger client**

```typescript
// src/trigger/client.ts  (v3 — no TriggerClient needed, configure via env)
// Trigger.dev v3 uses TRIGGER_SECRET_KEY env var automatically.
// This file is a placeholder for any shared Trigger.dev utilities.
export const TRIGGER_PROJECT_REF = process.env.TRIGGER_PROJECT_REF ?? 'wav-intelligence'
```

- [ ] **Step 3: Implement process-session job**

```typescript
// src/trigger/process-session.ts
import { task, retry } from '@trigger.dev/sdk/v3'
import { createClient } from '@supabase/supabase-js'
import { transcodeVideo } from './steps/transcode-360'
import { transcodeDslr } from './steps/transcode-dslr'
import { generatePeaks } from './steps/generate-peaks'
import { transcribeAudio } from './steps/transcribe-audio'
import { runAiEnrichment } from './steps/ai-enrichment'
import { generateEmbeddings } from './steps/generate-embeddings'
import { finalizeSession } from './steps/finalize'

export const processSessionTask = task({
  id: 'process-session',
  maxDuration: 7200, // 2 hours
  retry: { maxAttempts: 3, minTimeoutInMs: 1000, factor: 5 },

  run: async (payload: { sessionId: string; jobId: string }) => {
    const { sessionId, jobId } = payload

    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!
    )

    const updateProgress = async (step: number, total: number, status = 'running') => {
      await supabase.from('processing_jobs').update({
        status,
        current_step: step,
        progress: Math.round((step / total) * 100),
        last_completed_step: step - 1,
      }).eq('id', jobId)
    }

    const TOTAL = 7
    const steps = [
      { n: 1, fn: () => transcodeVideo(sessionId, supabase) },
      { n: 2, fn: () => transcodeDslr(sessionId, supabase) },
      { n: 3, fn: () => generatePeaks(sessionId, supabase) },
      { n: 4, fn: () => transcribeAudio(sessionId, supabase) },
      { n: 5, fn: () => runAiEnrichment(sessionId, supabase) },
      { n: 6, fn: () => generateEmbeddings(sessionId, supabase) },
      { n: 7, fn: () => finalizeSession(sessionId, supabase) },
    ]

    for (const step of steps) {
      await updateProgress(step.n, TOTAL)
      try {
        await step.fn()
      } catch (err) {
        // Record which step failed for targeted retry (spec §12)
        await supabase.from('processing_jobs').update({
          status: 'failed',
          failed_step: step.n,
          error_message: (err as Error).message,
        }).eq('id', jobId)
        await supabase.from('sessions').update({ status: 'error' }).eq('id', sessionId)
        throw err  // re-throw so Trigger.dev handles retries
      }
    }

    await supabase.from('processing_jobs').update({
      status: 'completed',
      current_step: 7,
      progress: 100,
      completed_at: new Date().toISOString(),
    }).eq('id', jobId)

    return { success: true, sessionId }
  },
})
```

- [ ] **Step 4: Implement process API route + cron**

```typescript
// src/app/api/sessions/[id]/process/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createServiceClient } from '@/lib/supabase/server'
import { getRoleFromToken } from '@/lib/utils/auth'
import { tasks } from '@trigger.dev/sdk/v3'
import { processSessionTask } from '@/trigger/process-session'

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const supabase = await createServiceClient()
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const jwt = JSON.parse(atob(session.access_token.split('.')[1]))
  if (getRoleFromToken(jwt) !== 'wav_admin') {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 })
  }

  const { id: sessionId } = await params

  // Create processing job record
  const { data: job, error } = await supabase.from('processing_jobs')
    .insert({ session_id: sessionId, status: 'queued', total_steps: 7 })
    .select().single()

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  // Dispatch to Trigger.dev Cloud
  const handle = await tasks.trigger<typeof processSessionTask>(
    'process-session',
    { sessionId, jobId: job.id }
  )

  await supabase.from('processing_jobs')
    .update({ trigger_run_id: handle.id, status: 'running' })
    .eq('id', job.id)

  await supabase.from('sessions').update({ status: 'processing' }).eq('id', sessionId)

  return NextResponse.json({ jobId: job.id, triggerId: handle.id })
}
```

```typescript
// src/app/api/cron/check-uploads/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createServiceClient } from '@/lib/supabase/server'
import { tasks } from '@trigger.dev/sdk/v3'
import { processSessionTask } from '@/trigger/process-session'

export async function GET(request: NextRequest) {
  // Vercel Cron sends the secret as Authorization: Bearer <CRON_SECRET>
  const authHeader = request.headers.get('authorization')
  const secret = authHeader?.replace('Bearer ', '')
  if (secret !== process.env.CRON_SECRET) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const supabase = await createServiceClient()

  // Find uploaded sessions with no processing job
  const { data: sessions } = await supabase
    .from('sessions')
    .select('id')
    .eq('status', 'uploaded')
    .not('id', 'in',
      supabase.from('processing_jobs').select('session_id')
    )

  if (!sessions?.length) return NextResponse.json({ dispatched: 0 })

  let dispatched = 0
  for (const session of sessions) {
    const { data: job } = await supabase.from('processing_jobs')
      .insert({ session_id: session.id, status: 'queued', total_steps: 7 })
      .select().single()

    if (job) {
      const handle = await tasks.trigger<typeof processSessionTask>(
        'process-session',
        { sessionId: session.id, jobId: job.id }
      )
      await supabase.from('processing_jobs')
        .update({ trigger_run_id: handle.id, status: 'running' })
        .eq('id', job.id)
      dispatched++
    }
  }

  return NextResponse.json({ dispatched })
}
```

- [ ] **Step 5: Add cron to vercel.json**

```json
// vercel.json
{
  "crons": [
    {
      "path": "/api/cron/check-uploads",
      "schedule": "*/5 * * * *"
    }
  ]
}
```

- [ ] **Step 6: Commit**

```bash
git add src/trigger/ src/app/api/sessions/ src/app/api/cron/ vercel.json
git commit -m "feat: Trigger.dev processing pipeline + cron fallback"
```

**P3 DONE ✅ — Full pipeline: upload → transcode → transcribe → AI enrich → embed → ready**

---

## Phase 4 — Multi-Track Synchronized Player

**Deliverable:** Session view with 6 tabs. Player tab: 360° video (videojs-vr), DSLR video, 13 audio waveforms (Peaks.js), master timeline scrubber, topic markers, auto-scrolling transcript. All tracks in sync (±100ms). Active speaker detected and highlighted.

**Task-level outline** (invoke `writing-plans` for full detail):

1. **Task 4.1:** Install HLS.js, Video.js, videojs-vr, Peaks.js. Create `src/lib/sync/sync-engine.ts` with state machine + coordinator. Unit tests for sync coordinator and amplitude detector.
2. **Task 4.2:** `video-360.tsx` — Video.js + videojs-vr player with HLS. Lazy-load WebGL/three.js. Speaker position overlay from seat data.
3. **Task 4.3:** `video-dslr.tsx` — Standard HLS player.
4. **Task 4.4:** `audio-track.tsx` + `audio-tracks.tsx` — Peaks.js waveform per mic. Virtualized list. RMS amplitude monitoring via Web Audio API.
5. **Task 4.5:** `master-timeline.tsx` — Scrubber + topic color markers. Connects to sync engine.
6. **Task 4.6:** `transcript-follow.tsx` — Auto-scrolling verbatim list synced to currentTime. Click to seek.
7. **Task 4.7:** `sync-player.tsx` — Orchestrator: React context for shared time state, coordinates all tracks.
8. **Task 4.8:** `seating-map.tsx` — 2D diagram for seat position overview.
9. **Task 4.9:** `src/app/api/sessions/[id]/media/[fileId]/stream/route.ts` — Signed HLS URL. `peaks/route.ts` — Serve peaks JSON.
10. **Task 4.10:** Wire player tab in session view. E2E test: navigate to player, press play, verify all tracks start.

---

## Phase 5 — Semantic Search + RAG Q&A

**Deliverable:** `/search` page with real-time semantic search across verbatims. `/ask` page with free-form Q&A returning AI answers with cited verbatims.

**Task-level outline:**

1. **Task 5.1:** `src/lib/ai/rag-query.ts` — embed query, cosine search via pgvector, return top-K. Unit tests with mock DB.
2. **Task 5.2:** `/api/search` route — accepts q param, calls rag-query, returns ranked verbatims with session/participant context.
3. **Task 5.3:** `/api/ask` route — RAG + LLM synthesis. Rate limiting (20 req/min per user). Prompt injection mitigation.
4. **Task 5.4:** `search-bar.tsx` + `search-results.tsx` — debounced input, result cards with topic badge, timestamp, participant name, sentiment indicator.
5. **Task 5.5:** `ask-interface.tsx` — Chat-like UI using AI Elements `<MessageResponse>` for rendered markdown. Shows cited verbatims below answer.
6. **Task 5.6:** E2E test: search "infotainment" → results appear. Ask "¿qué piensan del sistema de navegación?" → AI answer with citations.

---

## Phase 6 — Trends: Cross-Session Analysis

**Deliverable:** `/trends` page showing topic frequency evolution across sessions, sentiment trends, action plan tracking (implemented actions vs persisting issues).

**Task-level outline:**

1. **Task 6.1:** `/api/trends` route — aggregate verbatim counts, sentiment averages by session + topic. SQL window functions.
2. **Task 6.2:** `trend-chart.tsx` — Recharts line/bar chart for topic frequency over time. Color-coded by topic enum.
3. **Task 6.3:** `cross-session-table.tsx` — Table comparing key metrics across all sessions.
4. **Task 6.4:** Action plan tracking — cross-session resolution rate: did issues from Q1 reduce in Q2?
5. **Task 6.5:** Wire `/trends` page. Role check: mg_client + wav_admin only.

---

## Phase 7 — Export: PDF Reports + CSV

**Deliverable:** "Export" tab on session view. Generate bilingual (ESP+ENG) PDF with executive summary, topic breakdown, keypoints, selected verbatims, action plans, charts. Download CSV of all verbatims.

**Task-level outline:**

1. **Task 7.1:** Install `@react-pdf/renderer`. Create `src/lib/export/pdf-report.tsx` — branded React-pdf template with MG colors.
2. **Task 7.2:** `src/lib/ai/translate.ts` — AI Gateway translation for bilingual content. Cache translated strings in DB.
3. **Task 7.3:** `/api/sessions/[id]/export/pdf` route — renders PDF, stores in Supabase Storage, returns signed URL.
4. **Task 7.4:** `/api/sessions/[id]/export/csv` route — streams CSV with headers: timestamp, speaker, text, topic, sentiment, score.
5. **Task 7.5:** `export-panel.tsx` — download buttons with status (generating / ready / download).
6. **Task 7.6:** E2E test: click "Export PDF" → wait → download dialog appears.

---

## Phase 8 — Polish: Notifications + Onboarding + Mobile + Error States

**Deliverable:** Production-ready. Email notifications when session is ready. Admin onboarding flow for new users. All error states handled. Mobile-responsive layout.

**Task-level outline:**

1. **Task 8.1:** Processing complete notification — email via Supabase Edge Functions or Resend API.
2. **Task 8.2:** Processing failure alert — email WAV Admin with step name + error message.
3. **Task 8.3:** Onboarding flow for new MG Client users — "Welcome" modal with quick tour.
4. **Task 8.4:** All empty states — no sessions, no results, no action plans.
5. **Task 8.5:** Mobile responsive — sidebar collapse, player layout for mobile, waveforms simplified.
6. **Task 8.6:** Error boundaries — per-section error boundary with retry CTA.
7. **Task 8.7:** Health check cron — `GET /api/health` pinged every 5 min, alerts on failure.
8. **Task 8.8:** Final E2E sweep — auth, upload, process (mock), view, search, ask, export.

---

## Pre-Production Checklist

Before releasing to MG Motor Chile:

- [ ] Run transcription A/B test with 10 min of real January 2026 Chilean audio (ElevenLabs vs Deepgram vs Whisper). Pick winner, update `getTranscriptionProvider()` default.
- [ ] Confirm 360° camera model with Federico — verify video format matches ffmpeg transcode config.
- [ ] Confirm sync method: clap marker or timecode? Update `offset-calculator.ts` accordingly.
- [ ] Confirm Favorit/Heatwood font licensing for dashboard use.
- [ ] Supabase PITR enabled on Pro plan.
- [ ] Weekly pg_dump cron to R2 backups bucket configured.
- [ ] CORS restricted to production domain in all API routes.
- [ ] Rate limiting on `/api/ask` verified: 21st request within 1 minute returns 429.
- [ ] Role escalation test: attempt to set role via `updateUser()` → verify RLS blocks access.

---

*Plan generated 2026-03-25. Spec: `docs/superpowers/specs/2026-03-25-wav-intelligence-dashboard-design.md`*
