# WAV Intelligence Dashboard — System Design

**Date:** 2026-03-25
**Author:** Federico Elgueta (WAV BTL) + Claude
**Status:** Draft — pending review

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
| Processing pipeline | Trigger.dev (self-hosted on Railway) | Multi-step durable jobs, ffmpeg support, ~$5/mo |
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
Supabase                    Trigger.dev (Railway)
  ├── Auth (3 roles + RLS)      └── process-session job
  ├── Postgres + pgvector            ├── transcode (ffmpeg)
  └── Storage (small files)          ├── transcribe (ElevenLabs)
                                     ├── analyze (AI Gateway)
Cloudflare R2                        ├── embed (OpenAI)
  └── /sessions/{id}/               └── finalize
       ├── raw/ (uploads)
       └── processed/ (HLS + peaks)
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
  └── embedding (vector(1536))

Keypoint
  └── id, session_id (FK), topic
  └── title, description, timestamp
  └── supporting_verbatim_ids (array)

ActionPlan
  └── id, session_id (FK, nullable for cross-session)
  └── category (quick_win|strategic|monitor)
  └── title, description, ai_reasoning
  └── impact_score (1-10), cost_estimate (low|medium|high)
  └── cognitive_load (low|medium|high), time_estimate
  └── supporting_verbatim_ids (array)
  └── status (pending|in_progress|done), assigned_to

ProcessingJob
  └── id, session_id (FK), status (queued|running|completed|failed)
  └── current_step, total_steps, progress (0-100)
  └── error_message, trigger_run_id
  └── created_at, completed_at

User (Supabase Auth)
  └── id, email, name, role (wav_admin|mg_client|moderator)
  └── organization (WAV|MG)
  └── assigned_session_ids (moderators only)
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

### Sync engine

- Shared `currentTime` state managed in React
- 360 video is the master clock
- Audio tracks offset by `sync_offset_ms` (calculated during processing)
- Scrubbing any element updates all others
- Active speaker detected from audio amplitude of each mic track

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

### Pipeline trigger

- Vercel Cron runs every 5 minutes: `GET /api/cron/check-uploads`
- Finds sessions with `status = 'uploaded'`
- Dispatches `process-session` job to Trigger.dev via SDK
- Dashboard polls `ProcessingJob` table for real-time status

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

## 10. Build Phases

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

## 11. Cost Estimates (Annual)

| Service | Monthly | Annual |
|---------|---------|--------|
| Vercel (Pro) | $20 | $240 |
| Supabase (Pro) | $25 | $300 |
| Cloudflare R2 (~1.7 TB) | ~$25 | ~$300 |
| Railway (Trigger.dev host) | ~$5 | ~$60 |
| ElevenLabs Scribe (36 sessions) | — | ~$375 |
| AI Gateway (LLM + embeddings) | — | ~$180 |
| **Total** | | **~$1,455/yr** |

---

## 12. Open Questions

1. **Transcription A/B test**: ElevenLabs Scribe vs Deepgram Nova-3 vs Whisper with real Chilean audio — must complete before P3
2. **360 camera model**: Which camera will WAV use? File format affects transcode pipeline
3. **Sync method**: Clap/marker at session start? Timecode? Manual alignment?
4. **MG branding approval**: Can we use Favorit/Heatwood fonts in the dashboard (licensing)?
5. **Notification preferences**: Email only? In-app? WhatsApp?
6. **Data retention**: How long to keep raw media in R2? Archive policy?

---

*Spec generated from brainstorming session 2026-03-25. Pending spec review and user approval.*
