# WAV Intelligence Dashboard — System Design

**Date:** 2026-03-25
**Author:** Federico Elgueta (WAV BTL) + Claude
**Status:** Draft v2 — post architecture review

---

## 1. Purpose

Transform the static WAV Intelligence mockup into a production dashboard that processes focus group audio/video, generates transcripts with speaker attribution, and delivers AI-powered insights and action plans to MG Motor Chile.

### What this product does

WAV Intelligence is a SaaS-like dashboard for the "Voice of MG" program. It ingests raw media from quarterly focus group sessions (360 video, DSLR video, individual lavalier audio), processes them through an automated pipeline (transcription, topic classification, sentiment analysis, embedding generation), and presents the results as an interactive, searchable, AI-queryable dashboard with prioritized action plans.

### Who uses it

| Role | Person(s) | Access level |
|------|-----------|-------------|
| WAV Admin | Federico Elgueta | Full CRUD: upload, manage sessions, edit transcripts, manage users |
| MG Client | Kyle (GM), Alfredo Guzman (PM) | Read-only: explore sessions, search, export, ask AI questions |
| Moderator | Assigned per session | Read-only on assigned sessions only |

---

## 2. Architecture Overview

### Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | Next.js 16 (App Router, Server Components) | Vercel-native, streaming, RSC for performance |
| UI | shadcn/ui + custom MG brand theme (dark mode) | Professional, customizable, accessible |
| Auth | Supabase Auth + Row-Level Security | 3 roles enforced at DB layer, no extra service |
| Database | Supabase Postgres + pgvector | Relational data + vector embeddings, single platform |
| File storage (small) | Supabase Storage | Thumbnails, PDFs, profile photos (<10 GB) |
| Media storage (large) | Cloudflare R2 | 1.7 TB/yr video+audio, zero egress fees, ~$25/mo |
| Transcription | ElevenLabs Scribe (primary) | Best Chilean Spanish support (3.1% WER), $0.40/hr |
| AI/LLM | Vercel AI Gateway | Topic classification, sentiment, RAG, translations, action plans |
| Embeddings | OpenAI text-embedding-3-small | 1536-dim vectors stored in pgvector |
| Processing pipeline | Trigger.dev Cloud | Multi-step durable jobs, ffmpeg support, managed infra, ~$30/mo |
| Video streaming | HLS.js + Video.js + videojs-vr | Adaptive bitrate, 360 panoramic viewer |
| Audio waveforms | Peaks.js | Multi-track waveform visualization (BBC open-source) |
| PDF generation | React-pdf | Branded bilingual reports |
| Hosting | Vercel | Next.js optimized, preview deploys, cron jobs |

### System diagram

```
VERCEL (Next.js 16)
  ├── Dashboard (React, Server + Client Components)
  ├── API Routes (/api/*)
  └── Cron Jobs (check for new uploads every 5 min)
         │
    ┌────┴────────────────────────────┐
    │                                 │
    ▼                                 ▼
Supabase                    Trigger.dev Cloud (managed)
  ├── Auth (3 roles + RLS)      └── process-session job
  ├── Postgres + pgvector            ├── transcode (ffmpeg)
  │   └── verbatim_embeddings        ├── transcribe (ElevenLabs)
  └── Storage (small files)          ├── analyze (AI Gateway)
                                     ├── embed (OpenAI)
Cloudflare R2                        └── finalize
  └── /sessions/{id}/
       ├── raw/ (uploads)
       └── processed/ (HLS + peaks)

Pipeline trigger: event-driven (upload-complete API dispatches job directly)
                  + cron fallback every 5 min for missed dispatches
```

### Relationship to existing proposal site

Separate product in its own repository. The proposal site (static HTML at voice-of-mg) remains as-is. Both share MG branding but are independent.

---

## 3. Data Model

### Core entities

```
Program
  └── id, name, year

FocusGroup
  └── id, program_id (FK), quarter (Q1-Q4), start_date, end_date

Day
  └── id, focus_group_id (FK), day_number (1-3), date

Session
  └── id, day_id (FK), name, status (scheduled|uploaded|processing|ready|error)
  └── moderator_id (FK → User)
  └── created_at, updated_at

MediaFile
  └── id, session_id (FK), type (video_360|video_dslr|audio)
  └── r2_key, r2_bucket, original_filename
  └── duration_seconds, file_size_bytes
  └── hls_manifest_key (nullable, set after transcode)
  └── waveform_peaks_key (nullable, audio only)
  └── sync_offset_ms (alignment to master timeline)
  └── mic_number (nullable, audio only)

Participant
  └── id, session_id (FK), name, mg_model
  └── mic_number, media_file_id (FK → audio MediaFile)
  └── seat_angle, seat_distance (position in 360 frame)
  └── talk_time_seconds, sentiment_avg

Verbatim
  └── id, session_id (FK), participant_id (FK)
  └── text, start_ts, end_ts
  └── topic (enum), sentiment (enum), sentiment_score (float)

VerbatimEmbedding (separate table for model-agnostic embeddings)
  └── id, verbatim_id (FK), model_name, dimensions
  └── embedding (vector(1536))
  └── created_at

Keypoint
  └── id, session_id (FK), topic
  └── title, description, timestamp
  └── (linked via keypoint_verbatims / action_plan_verbatims join tables)

ActionPlan
  └── id, session_id (FK, nullable for cross-session)
  └── category (quick_win|strategic|monitor)
  └── title, description, ai_reasoning
  └── impact_score (1-10), cost_estimate (low|medium|high)
  └── cognitive_load (low|medium|high), time_estimate
  └── (linked via keypoint_verbatims / action_plan_verbatims join tables)
  └── status (pending|in_progress|done), assigned_to

ProcessingJob
  └── id, session_id (FK), status (queued|running|completed|failed)
  └── current_step, total_steps, progress (0-100)
  └── error_message, trigger_run_id
  └── failed_step (nullable), last_completed_step (default 0)
  └── created_at, completed_at

User (Supabase Auth)
  └── id, email, name, role (wav_admin|mg_client|moderator)
  └── organization (WAV|MG)
UserSession (join table for moderator assignments)
  └── user_id (FK → User), session_id (FK → Session)
```

### RLS policies

- **wav_admin**: full CRUD on all tables
- **mg_client**: SELECT on sessions (status = 'ready'), verbatims, keypoints, action_plans, participants, media_files
- **moderator**: SELECT on sessions/verbatims/participants/media_files WHERE session_id IN assigned_session_ids

### Topic enum

`marca | diseno | precio | infotainment | postventa | seguridad | garantia | convocatoria | otro`

### Sentiment enum

`positivo | neutro | negativo`

---

## 4. Media Storage & Streaming

### Storage volumes (annual estimate)

| Asset | Count/yr | Size/file | Total/yr |
|-------|----------|-----------|----------|
| 360 video (2hrs, 4K) | 36 | ~25-40 GB | ~1 TB |
| DSLR video (2hrs, 1080p) | 36 | ~10-20 GB | ~540 GB |
| Audio (2hrs, 32-bit float WAV) | 156 | ~1.3 GB | ~200 GB |
| **Total raw** | **228 files** | | **~1.7 TB** |

### R2 bucket structure

```
wav-intelligence-media/
  sessions/
    {session_id}/
      raw/
        360.mp4
        dslr.mp4
        audio/
          mic-01.wav
          mic-02.wav
          ... mic-13.wav
      processed/
        360/
          master.m3u8
          segment-001.ts ... segment-N.ts
          thumb-0000.jpg ... thumb-NNNN.jpg
        dslr/
          master.m3u8
          segment-001.ts ... segment-N.ts
        audio/
          mic-01-peaks.json
          mic-02-peaks.json
          ...
        sync-offsets.json
```

### Upload flow

1. WAV Admin selects files in browser
2. Frontend requests presigned upload URLs from API route
3. Browser uploads directly to R2 via presigned URLs (resumable)
4. On completion, API route records MediaFile entries in Supabase

### Streaming

- Videos transcoded to HLS (adaptive: 4K + 1080p for 360, 1080p + 720p for DSLR)
- HLS.js plays in browser via signed URLs
- 360 panoramic viewing via Video.js + videojs-vr (three.js)
- Audio waveforms rendered via Peaks.js from precomputed peak data

---

## 5. Multi-Track Synchronized Player

The core UI component. All media for a session plays in sync.

### Player layout

```
┌──────────────────────────────────────────────────┐
│  [360 view]  |  [DSLR view]  |  [Seating map]   │
│         Video area (switchable views)             │
│                                                   │
│  Speaker overlay: participant names at tagged      │
│  positions, active speaker highlighted (green)     │
│                                                   │
│         << >>  ||   01:23:45 / 02:00:00           │
├──────────────────────────────────────────────────┤
│  ══════●═══════════════════ master timeline       │
│  Topic markers: [Marca][Diseno][Precio]...        │
├──────────────────────────────────────────────────┤
│  Participant 1  ▁▃▅▇▅▃▁▁▃▅▃▁  SPEAKING           │
│  Participant 2  ▁▁▁▁▁▁▁▁▁▁▁▁                     │
│  ... (13 audio waveform tracks)                   │
├──────────────────────────────────────────────────┤
│  Transcript: follows playback, highlights current  │
│  verbatim. Click any line to seek.                │
└──────────────────────────────────────────────────┘
```

### Sync engine (detailed architecture)

**Master clock:** The 360 video is the time reference. All other tracks derive their position from it.

**Track state machine (per media element):**
```
idle → loading → buffered → playing → seeking → buffered → playing
                                    ↘ stalled → buffered (auto-resume)
```

**Sync coordinator:**
- Maintains shared `currentTime` state in React context
- On scrub: pauses master → seeks all tracks → waits until all report `buffered` → resumes master
- On stall: if any track stalls, coordinator pauses master clock until stalled track recovers
- On seek completion: tolerance of ±100ms (imperceptible for speech content)

**Audio offset:** Each track offset by `sync_offset_ms` (calculated during processing via cross-correlation of ambient sound captured by all mics, or manual clap marker detection)

**Active speaker detection:** Real-time RMS amplitude comparison across 13 audio tracks. Highest RMS above threshold = active speaker. Debounce 300ms to avoid flickering.

**Performance optimization:**
- Only render waveforms for tracks visible in the scrollable viewport
- Lazy-load 360° WebGL viewer (three.js) — initialize only when 360° tab is active
- Audio tracks use Web Audio API for amplitude monitoring without full decode
- Virtualize participant waveform list for sessions with many participants

### Speaker identification (audio-first, no facial recognition)

1. At setup, WAV Admin assigns mic-to-participant and tags seat positions on 360 frame
2. During playback, the active mic (highest amplitude) identifies the speaker
3. Name overlay on 360 video auto-rotates to speaker's tagged angle
4. Complies with MG brief: no facial analysis

---

## 6. Audio-to-Insights Pipeline

### Processing stages (Trigger.dev, self-hosted on Railway)

Each session triggers a `process-session` job with 7 retryable steps:

| Step | Action | Duration | Cost |
|------|--------|----------|------|
| 1 | Transcode 360 video to HLS (ffmpeg) | ~20 min | compute |
| 2 | Transcode DSLR video to HLS (ffmpeg) | ~15 min | compute |
| 3 | Generate audio waveform peaks | ~5 min | compute |
| 4 | Transcribe 13 audio files (ElevenLabs Scribe, Chilean Spanish) | ~20 min | ~$10.40 |
| 5 | AI enrichment: topics, sentiment, keypoints, action plans (AI Gateway) | ~10 min | ~$2-5 |
| 6 | Generate embeddings (OpenAI text-embedding-3-small) | ~3 min | ~$0.50 |
| 7 | Finalize: compute stats, mark ready, notify MG | ~1 min | — |
| **Total per session** | | **~1 hour** | **~$15-18** |
| **Total per year (36 sessions)** | | | **~$580-650** |

### Transcription provider strategy

ElevenLabs Scribe is the primary provider. The system uses an adapter pattern:

```typescript
interface TranscriptionProvider {
  transcribe(audioUrl: string, language: string): Promise<Transcript>
}
```

Implementations: `elevenlabs-scribe.ts` (primary), `deepgram-nova3.ts` (fallback), `whisper-local.ts` (self-hosted option).

**Mandatory before production:** A/B test with 10 minutes of real January 2026 focus group audio across all three providers. The winner becomes the default.

### Pipeline trigger (event-driven + cron fallback)

**Primary (event-driven):** When WAV Admin completes upload and clicks "Process Session":
1. `POST /api/sessions/[id]/upload-complete` saves MediaFile records
2. `POST /api/sessions/[id]/process` dispatches Trigger.dev job immediately
3. Zero latency — processing starts within seconds of upload completion

**Fallback (cron safety net):** Vercel Cron runs every 5 minutes: `GET /api/cron/check-uploads`
- Finds sessions with `status = 'uploaded'` that have no ProcessingJob
- Dispatches missed jobs (handles edge cases: browser crash, network error after upload)

**Status polling:** Dashboard polls `ProcessingJob` table for real-time progress bar

---

## 7. AI Features

### 7a. Topic classification

Each verbatim classified into predefined topics via LLM prompt. Batch processing (groups of 20 verbatims per API call for efficiency).

### 7b. Sentiment analysis

Per-verbatim: positivo/neutro/negativo + intensity score (0.0-1.0). Used for heatmaps, trend charts, and action plan scoring.

### 7c. Keypoint extraction

LLM groups related verbatims by topic, extracts headline insights with supporting quotes. Example: "Victoria Visual, Fracaso Digital" backed by 23 verbatims.

### 7d. Action plan generation (WAV Strategist)

The highest-value AI feature. Clusters related comments, scores by impact/cost/effort/time, and generates prioritized recommendations:

| Category | Definition | MG team action |
|----------|-----------|----------------|
| Quick Wins | High impact, low cost, low cognitive load | Do this week |
| Strategic | High impact, needs investment | Plan this quarter |
| Monitor | Low frequency or unclear trend | Review next session |

Each action plan includes: title, description, impact score (1-10), cost estimate, cognitive load rating, time estimate, supporting verbatims with quotes, and AI reasoning.

Cross-session tracking: after multiple sessions, AI tracks whether implemented actions reduced the issues they targeted.

### 7e. Semantic search (RAG)

- All verbatims embedded with text-embedding-3-small, stored in pgvector
- User searches: query embedded, cosine similarity search across all verbatims
- Returns ranked results with participant attribution, timestamp, topic, sentiment

### 7f. Free-form Q&A (/ask)

- User types natural language question
- System retrieves top-K relevant verbatims via embedding search
- LLM synthesizes answer citing specific quotes and participants
- Example: "What do ZS owners think about the infotainment?" returns a narrative answer with cited evidence

### 7g. Bilingual export

AI Gateway translates Spanish reports to English, preserving formatting and brand voice. PDF reports generated in both languages.

---

## 8. Frontend Pages

### Navigation structure

```
/ → redirect to /dashboard
/login
/dashboard                     (role-specific landing)
/sessions                      (all sessions, filterable)
/sessions/[id]                 (single session view)
  ├── tab: Player              (multi-track synced player)
  ├── tab: Transcripts         (full transcript, searchable)
  ├── tab: Participants        (profile cards + stats)
  ├── tab: Insights            (keypoints, topics, sentiment charts)
  ├── tab: Action Plan         (WAV Strategist recommendations)
  └── tab: Export              (PDF, CSV, raw data)
/trends                        (cross-session analysis)
/ask                           (RAG Q&A interface)
/admin/sessions/new            (WAV only: create session)
/admin/sessions/[id]/setup     (WAV only: upload + configure)
/admin/processing              (WAV only: pipeline status)
/admin/users                   (WAV only: manage accounts)
/settings                      (profile, notifications)
```

### Dashboard landing by role

| WAV Admin | MG Client | Moderator |
|-----------|-----------|-----------|
| Processing queue | Latest session | Assigned sessions |
| Upload CTA | Trend cards | Participant stats |
| All sessions | AI highlights | Review transcripts |
| User management | "Ask anything" | — |

### Design system

- Dark mode default (MG brand: `#080810` background)
- MG colors: Red `#A00022`, Smoke `#FD2F33`, White `#F7F3EF`
- Fonts: Favorit (sans), Favorit Mono (data/labels), Heatwood (accent, max 2 words)
- Built with shadcn/ui + custom MG theme tokens
- Desktop-first, mobile-responsive

---

## 9. Export & Deliverables

### Per-session exports

- **PDF report** (auto-generated): executive summary, topic breakdown, key verbatims, charts, action plan, bilingual ESP+ENG
- **CSV/Excel**: all verbatims with timestamps, topics, sentiment
- **Raw data package**: transcripts, audio files, metadata JSON

### Cross-session exports

- **Trend report** (PDF): quarter-over-quarter comparisons, topic evolution, AI narrative
- **Trend data** (CSV): aggregated metrics

### PDF generation

React-pdf renders styled templates with MG branding. Stored in Supabase Storage. Downloaded via signed URL.

---

## 10. API Endpoints

### Auth

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/callback` | — | Supabase Auth callback handler |

### Sessions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/sessions` | all roles | List sessions (filtered by RLS) |
| GET | `/api/sessions/[id]` | all roles | Session detail with stats |
| POST | `/api/sessions` | wav_admin | Create new session |
| PATCH | `/api/sessions/[id]` | wav_admin | Update session metadata |
| DELETE | `/api/sessions/[id]` | wav_admin | Delete session + cascade |

### Upload & Media

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/sessions/[id]/upload-url` | wav_admin | Get R2 presigned multipart upload URLs |
| POST | `/api/sessions/[id]/upload-complete` | wav_admin | Confirm upload, create MediaFile records |
| GET | `/api/sessions/[id]/media/[fileId]/stream` | all roles | Generate signed HLS manifest URL |
| GET | `/api/sessions/[id]/media/[fileId]/peaks` | all roles | Serve waveform peak data |

### Session Setup

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/sessions/[id]/participants` | wav_admin | Bulk upsert participants (mic assignment) |
| PUT | `/api/sessions/[id]/seating` | wav_admin | Save seat positions from 360 frame |
| POST | `/api/sessions/[id]/process` | wav_admin | Trigger processing pipeline |

### Processing

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/sessions/[id]/processing` | wav_admin | Get ProcessingJob status + progress |
| POST | `/api/sessions/[id]/processing/retry` | wav_admin | Retry failed job from last completed step |
| GET | `/api/cron/check-uploads` | cron_secret | Vercel Cron: find uploaded sessions, dispatch |

### Verbatims & Search

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/sessions/[id]/verbatims` | all roles | List verbatims (filterable by topic, participant, sentiment) |
| GET | `/api/search` | all roles | Semantic search across all accessible verbatims |
| POST | `/api/ask` | mg_client, wav_admin | RAG Q&A: free-form question, returns AI answer + citations |

### Insights & Action Plans

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/sessions/[id]/keypoints` | all roles | Session keypoints |
| GET | `/api/sessions/[id]/action-plans` | all roles | Session action plans |
| PATCH | `/api/action-plans/[id]` | mg_client, wav_admin | Update action plan status (pending/in-progress/done) |
| GET | `/api/trends` | mg_client, wav_admin | Cross-session trend data |

### Export

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/sessions/[id]/export/pdf` | all roles | Generate PDF report (bilingual) |
| GET | `/api/sessions/[id]/export/csv` | all roles | Download CSV of verbatims |

### Admin

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/admin/users` | wav_admin | List all users |
| POST | `/api/admin/users` | wav_admin | Invite user (sends email) |
| PATCH | `/api/admin/users/[id]` | wav_admin | Update role, assign sessions |
| POST | `/api/admin/users/[id]/sessions` | wav_admin | Assign sessions to moderator |

---

## 11. Authentication Flow

### Login method

Supabase Auth with **magic link** (email-based, passwordless). No passwords to manage.

### Role assignment

1. WAV Admin creates user via `/admin/users` → specifies role (mg_client or moderator)
2. Supabase Auth invitation email sent with magic link
3. On creation, user's `role` and `organization` are set in `auth.users.app_metadata` (admin-only, NOT `user_metadata` which users can self-modify)
4. RLS policies read `auth.jwt() -> 'app_metadata' ->> 'role'` for access control

**CRITICAL:** Role MUST be stored in `app_metadata`, never `user_metadata`. Users can modify their own `user_metadata` via `supabase.auth.updateUser()`, which would allow role escalation.

### Session verification in API routes

```
// Every API route:
1. Extract JWT from Authorization header (Supabase client handles this)
2. Verify JWT signature (Supabase middleware)
3. Read role from app_metadata (admin-only writable, immune to user self-modification)
4. RLS enforces data access at DB layer
5. API route checks role for write operations
```

### Moderator session assignment

Join table `user_sessions(user_id, session_id)` — WAV Admin assigns via UI. RLS policy: moderator can SELECT from sessions/verbatims WHERE session_id IN (SELECT session_id FROM user_sessions WHERE user_id = auth.uid()).

---

## 12. Error Handling & Recovery

### Pipeline failure strategy

| Scenario | Behavior |
|----------|----------|
| Step fails (transient) | Auto-retry 3 times with exponential backoff (1s, 5s, 25s) |
| Step fails (permanent) | Mark ProcessingJob as `failed`, record `failed_step` + `error_message` |
| Admin sees failure | Dashboard shows which step failed + error. "Retry" button retries from `failed_step`, not from start |
| External API down (ElevenLabs, AI Gateway) | Retry with backoff. After 3 retries, mark failed. Admin can retry later. |
| Partial progress | Each completed step saves results to DB. Retry resumes from last completed step — no duplicate work |

### ProcessingJob status flow

```
queued → running → completed
                 ↘ failed → (admin retries) → running → ...
```

### Data model addition

Add `failed_step` (nullable int) and `last_completed_step` (int, default 0) to ProcessingJob entity.

### Frontend error states

- **Upload failed**: retry button, show which file failed
- **Processing failed**: show step name + error message + retry CTA
- **Search/Ask timeout**: "Taking longer than expected, please try again"
- **Media streaming error**: fallback to download link

### Fallback behavior

| Service down | Fallback |
|-------------|----------|
| ElevenLabs | Switch to Deepgram adapter (auto or manual) |
| AI Gateway | Queue enrichment for later, mark session as "partially processed" (transcripts available, no AI analysis yet) |
| R2 | Uploads fail with retry prompt, existing streams use CDN cache |

---

## 13. Security

### API security

- **CORS**: restrict to dashboard domain only
- **Rate limiting**: `/api/ask` limited to 20 requests/minute per user (LLM cost protection)
- **CRON secret**: `CRON_SECRET` header verified on `/api/cron/*` routes
- **Input sanitization**: free-form Q&A input sanitized before LLM prompt (prevent prompt injection)
- **LLM prompt injection mitigation**: system prompt hardcoded, user input wrapped in delimiters, output validated

### Storage security

- **R2 bucket**: private, all access via presigned URLs with 1-hour expiry
- **Presigned upload URLs**: scoped to specific key prefix (`/sessions/{id}/raw/`), max file size enforced
- **Supabase Storage**: private bucket, access via Supabase auth tokens

### Database backup

- **Supabase PITR**: Point-in-time recovery enabled (included in Pro plan)
- **Weekly pg_dump**: Cron job exports full database dump to R2 bucket (`wav-intelligence-backups/`)
- **Retention**: 30 days of weekly backups, then monthly for 12 months
- **Recovery procedure**: documented in runbook (restore from PITR for <7 days, pg_dump for older)

### Auth security

- **Magic link expiry**: 1 hour
- **Session duration**: 7 days with refresh
- **RLS enforced on all tables**: even direct DB access respects roles
- **No service role key on frontend**: all client operations use anon key + JWT

### Upload security

- R2 multipart uploads: `CreateMultipartUpload` → `UploadPart` (chunks) → `CompleteMultipartUpload`
- Max file size: 50 GB per file (covers 360 4K video)
- Allowed MIME types: video/mp4, audio/wav, audio/x-wav
- File hash verification after upload completion

---

## 14. Environment Variables

```
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

# Transcription (primary)
ELEVENLABS_API_KEY=

# Transcription (fallback)
DEEPGRAM_API_KEY=

# AI (via Vercel AI Gateway — OIDC preferred)
# If not using AI Gateway OIDC:
OPENAI_API_KEY=

# Processing pipeline
TRIGGER_DEV_API_KEY=
TRIGGER_DEV_API_URL=

# Vercel Cron
CRON_SECRET=

# App
NEXT_PUBLIC_APP_URL=
```

---

## 15. Testing Strategy

| Type | Scope | Tools |
|------|-------|-------|
| **Unit** | Transcription adapters, sync offset calculation, topic classifier prompt, embedding generation | Vitest |
| **Integration** | Upload flow (presigned URL → R2 → DB), pipeline step execution (mock APIs), RLS policies | Vitest + Supabase local |
| **E2E** | Login → upload → process → view session → search → export PDF | Playwright |
| **Pipeline** | Process a real 10-min audio sample through all 7 steps | Manual + CI |
| **Load** | `/api/ask` with concurrent requests (rate limit verification) | k6 or artillery |
| **A/B transcription** | Compare ElevenLabs vs Deepgram vs Whisper on real Chilean audio | Manual benchmark script |

### Minimum coverage target: 80% on business logic (adapters, pipeline steps, RLS policies)

---

## 16. Database Indexes

```sql
-- Verbatim queries (most common)
CREATE INDEX idx_verbatims_session ON verbatims(session_id);
CREATE INDEX idx_verbatims_participant ON verbatims(participant_id);
CREATE INDEX idx_verbatims_topic ON verbatims(topic);
CREATE INDEX idx_verbatims_sentiment ON verbatims(sentiment);
CREATE INDEX idx_verbatims_session_topic ON verbatims(session_id, topic);

-- Vector similarity search (HNSW for pgvector, separate table)
CREATE INDEX idx_verbatim_embeddings_verbatim ON verbatim_embeddings(verbatim_id);
CREATE INDEX idx_verbatim_embeddings_vector ON verbatim_embeddings
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- Processing job lookups
CREATE INDEX idx_processing_jobs_session ON processing_jobs(session_id);
CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);

-- Moderator session assignment
CREATE INDEX idx_user_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_session ON user_sessions(session_id);

-- Media file lookups
CREATE INDEX idx_media_files_session ON media_files(session_id);
CREATE INDEX idx_media_files_type ON media_files(session_id, type);
```

---

## 17. Monitoring & Observability

- **Pipeline alerts**: notify WAV Admin (email) when ProcessingJob.status = 'failed'
- **Step duration logging**: track each pipeline step duration to detect degradation
- **R2 storage monitoring**: monthly report on storage growth vs budget
- **API latency**: Vercel Analytics for endpoint response times
- **LLM cost tracking**: AI Gateway built-in cost attribution per endpoint
- **Uptime**: Vercel status + Supabase status monitored via simple health check cron

---

## 18. Build Phases

| Phase | Scope | Depends on |
|-------|-------|-----------|
| P1 | Project scaffold + Supabase auth + DB schema + basic layout + MG theme | Nothing |
| P2 | Admin: session creation + file upload to R2 + mic/seat assignment UI | P1 |
| P3 | Processing pipeline: Trigger.dev + ffmpeg + ElevenLabs + AI enrichment | P2 |
| P4 | Session view: multi-track synced player (360 + DSLR + audio waveforms) | P2 |
| P5 | Semantic search + RAG Q&A (/ask page) | P3 |
| P6 | Trends: cross-session charts + topic evolution + action tracking | P3 |
| P7 | Export: PDF reports (bilingual) + CSV + raw data | P3 |
| P8 | Polish: notifications, onboarding, mobile responsive, error states | P1-P7 |

---

## 19. Cost Estimates (Annual)

| Service | Monthly | Annual |
|---------|---------|--------|
| Vercel (Pro) | $20 | $240 |
| Supabase (Pro) | $25 | $300 |
| Cloudflare R2 (~1.7 TB) | ~$25 | ~$300 |
| Trigger.dev Cloud | ~$30 | ~$360 |
| ElevenLabs Scribe (36 sessions) | — | ~$375 |
| AI Gateway (LLM + embeddings) | — | ~$180 |
| **Total** | | **~$1,755/yr** |

---

## 20. Open Questions

1. **Transcription A/B test**: ElevenLabs Scribe vs Deepgram Nova-3 vs Whisper with real Chilean audio — must complete before P3
2. **360 camera model**: Which camera will WAV use? File format affects transcode pipeline
3. **Sync method**: Clap/marker at session start? Timecode? Manual alignment?
4. **MG branding approval**: Can we use Favorit/Heatwood fonts in the dashboard (licensing)?
5. **Notification preferences**: Email only? In-app? WhatsApp?
6. **Data retention policy (proposed)**: Keep raw media in R2 for 24 months, then archive to R2 Infrequent Access tier. Processed HLS/peaks kept indefinitely (much smaller). Confirm with MG whether they need raw files beyond 2 years.

---

*Spec generated from brainstorming session 2026-03-25. Pending spec review and user approval.*
