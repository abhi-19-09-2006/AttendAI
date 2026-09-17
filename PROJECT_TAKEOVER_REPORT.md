# AttendAI — Project Takeover Report

**Date**: 2026-09-17  
**Branch**: `arena/01a0ae8b-attendai`  
**Commit**: `41167af` — "docs: add project and security documentation"  
**Status**: Analysis complete. No code modified.

---

## A. Product Idea

AttendAI is an AI-powered college attendance communication platform. When a student is marked absent, the system:

1. Detects the absence from attendance records
2. Creates a call task for the student's parent/guardian
3. An AI voice agent (via Vapi) calls the parent
4. Conducts a natural conversation about the absence
5. Generates a transcript of the conversation
6. An AI extraction service (OpenAI/Anthropic) converts the transcript into structured absence data
7. Stores the structured report in PostgreSQL
8. Faculty sees results on a dashboard
9. Low-confidence or important cases are flagged for follow-up/review

The target product is a real college automation platform, not a demo.

---

## B. Current Architecture

```
┌──────────────────────┐
│   Next.js Frontend   │  (React 18, TypeScript, Tailwind, TanStack Query)
│   Port 3000          │
└──────────┬───────────┘
           │ REST API (axios)
┌──────────▼──────────────────────────────────────────┐
│              FastAPI Backend  (Port 8000)            │
│  ┌─────────┐  ┌──────────┐  ┌─────────────────────┐│
│  │  Auth   │  │  API     │  │  Webhook Handlers   ││
│  │  JWT    │  │  Routers │  │  (Vapi HMAC-SHA256) ││
│  └─────────┘  └──────────┘  └─────────────────────┘│
│  ┌─────────┐  ┌──────────┐  ┌─────────────────────┐│
│  │ Call    │  │  AI/     │  │  Background Jobs    ││
│  │ Service │  │  Extract │  │  (RQ + Redis)       ││
│  └─────────┘  └──────────┘  └─────────────────────┘│
│  ┌─────────────────────────────────────────────────┐│
│  │    Repository Layer (SQLAlchemy async)          ││
│  └─────────────────────────────────────────────────┘│
└────────┬──────────────────────────────────┬─────────┘
         │                                  │
┌────────▼────────┐              ┌──────────▼──────┐
│   PostgreSQL    │              │  Redis (RQ)     │
│   (asyncpg)     │              │  4 queues       │
└─────────────────┘              └─────────────────┘
         │
┌────────▼──────────┐
│  Vapi Voice AI    │  (external API + webhooks)
│  / Mock Provider  │
└───────────────────┘
```

---

## C. Actual Repository Structure

```
AttendAI/
├── docker-compose.yml          # 5 services: postgres, redis, backend, worker, frontend
├── .env.example
├── .gitignore                  # NOTE: accidentally ignores frontend/src/lib/
├── ARCHITECTURE.md
├── DEVELOPMENT_PLAN.md
├── EXTRACTION_REPORT.md
├── GIT_REVIEW_REPORT.md
├── PHASE1_COMPLETE.md
├── PHASE2_COMPLETE.md
├── PHASE2_REPORT.md
├── PHASE4_REPORT.md
├── PHASE4_VAPI_SETUP.md
├── PHASE9_REPORT.md
├── PRIORITY_3_TOKEN_HARDENING.md
├── PRIORITY_4_SENSITIVE_DATA.md
├── PROJECT_UNDERSTANDING_REPORT.md
├── QUICKSTART.md
├── README.md
├── SECURITY_HARDENING_COMPLETION.md
├── SECURITY_HARDENING_PLAN.md
├── SECURITY_PHASE_SUMMARY.md
├── SECURITY_QUICK_REFERENCE.md
│
├── backend/
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── pyproject.toml
│   ├── create_db.py
│   ├── create_test_schema.py
│   ├── test_alembic.py
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       ├── 20260912_0555_001_initial_schema.py
│   │       └── 20260914_1100_002_add_job_table_for_rq_background_jobs.py
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, rate-limit middleware, routers
│   │   ├── tasks.py             # RQ task implementations (async bridge)
│   │   ├── worker.py            # RQ worker entry point
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic Settings (env-based)
│   │   │   ├── database.py      # AsyncSession, engine, get_db dependency
│   │   │   ├── db_worker.py     # Worker session management, run_async_task bridge
│   │   │   ├── auth.py          # JWT auth dependencies (get_current_user, require_role)
│   │   │   ├── security.py      # Password hashing, JWT create/decode
│   │   │   ├── rate_limit.py    # Token bucket middleware
│   │   │   ├── rq_config.py     # Redis/RQ queue factory, health checks
│   │   │   └── logging.py       # Structured logging setup
│   │   ├── models/
│   │   │   ├── __init__.py      # Exports all models + enums
│   │   │   ├── enums.py         # UserRole, CallStatus, etc.
│   │   │   ├── user.py          # User model
│   │   │   ├── student.py       # Student model
│   │   │   ├── parent.py        # Parent/guardian model
│   │   │   ├── attendance.py    # Attendance record
│   │   │   ├── call.py          # Call + CallAttempt models
│   │   │   ├── call_campaign.py # CallCampaign model
│   │   │   ├── absence_report.py# AbsenceReport (AI-extracted)
│   │   │   ├── followup.py      # FollowUp task model
│   │   │   ├── audit_log.py     # AuditLog model
│   │   │   └── job.py           # Job model (RQ tracking + idempotency)
│   │   ├── schemas/
│   │   │   ├── __init__.py      # All Pydantic request/response schemas
│   │   │   └── extraction.py    # ExtractedAbsenceInfo schema
│   │   ├── repositories/
│   │   │   ├── base.py          # Generic CRUD BaseRepository
│   │   │   ├── user_repository.py
│   │   │   └── student_repository.py
│   │   ├── services/
│   │   │   ├── call_service.py       # Call orchestration (create, initiate, process)
│   │   │   ├── ai_service.py         # AI extraction facade
│   │   │   ├── extraction_provider.py# Abstract extraction interface
│   │   │   ├── extraction_factory.py # Factory: OpenAI or Anthropic
│   │   │   ├── openai_extractor.py   # OpenAI function-calling extraction
│   │   │   ├── anthropic_extractor.py# Anthropic Claude extraction
│   │   │   ├── prompt_manager.py     # Versioned prompts + schemas
│   │   │   ├── voice_provider.py     # Abstract voice interface
│   │   │   ├── vapi_provider.py      # Vapi.ai implementation
│   │   │   ├── vapi_client.py        # Low-level Vapi HTTP client (legacy?)
│   │   │   ├── mock_provider.py      # Mock voice for tests/dev
│   │   │   └── job_service.py        # Job lifecycle + idempotency
│   │   └── api/
│   │       ├── auth.py          # Login, refresh, register
│   │       ├── users.py         # User CRUD, /me
│   │       ├── students.py      # Student CRUD
│   │       ├── parents.py       # Parent CRUD
│   │       ├── attendance.py    # Attendance CRUD, absentees/today
│   │       ├── calls.py         # Call management, campaigns
│   │       ├── absence_reports.py# Report CRUD, review
│   │       ├── followups.py     # Follow-up CRUD, my-tasks, complete
│   │       ├── webhooks.py      # Vapi webhook + signature verification
│   │       ├── test_calls.py    # Single test call endpoint
│   │       └── health.py        # Health/readiness/liveness probes
│   ├── scripts/
│   │   └── seed_data.py
│   └── tests/
│       ├── conftest.py              # Fixtures, DB seeding, engine management
│       ├── test_api.py              # 9 tests (auth, user, student API)
│       ├── test_extraction.py       # 21 tests (AI extraction logic)
│       ├── test_health.py           # 5 tests (health endpoints)
│       ├── test_models.py           # 5 tests (model creation)
│       ├── test_phase10_foundations.py # 15 tests (job service, idempotency)
│       ├── test_phase10_step5.py    # 29 tests (scheduling, retries, dispatch)
│       ├── test_rate_limit.py       # 18 tests (rate limiting)
│       ├── test_voice_services.py   # 5 tests (voice providers)
│       └── test_webhooks.py         # 9 tests (webhook handling)
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── next.config.js
    ├── tailwind.config.ts
    ├── tsconfig.json
    ├── .eslintrc.json
    └── src/
        ├── app/
        │   ├── layout.tsx        # Root layout with Providers
        │   ├── page.tsx          # Root → redirect to /dashboard
        │   ├── providers.tsx     # QueryClient + AuthProvider
        │   ├── globals.css
        │   ├── login/page.tsx    # Login page
        │   ├── dashboard/page.tsx # Faculty dashboard
        │   ├── students/
        │   │   ├── page.tsx      # Student list
        │   │   └── [id]/page.tsx # Student detail
        │   ├── attendance/page.tsx # Attendance management
        │   ├── calls/
        │   │   ├── page.tsx      # Call log
        │   │   └── [id]/page.tsx # Call detail
        │   ├── absence-reports/
        │   │   ├── page.tsx      # Report list
        │   │   └── [id]/page.tsx # Report detail
        │   └── followups/page.tsx # Follow-up tasks
        ├── components/
        │   ├── DashboardLayout.tsx # Nav + layout wrapper
        │   ├── ProtectedRoute.tsx # Auth guard
        │   └── ui/
        │       ├── Badge.tsx     # Badge + domain badges
        │       └── Button.tsx    # Button component
        ├── context/
        │   └── AuthContext.tsx   # Auth state, login, logout, tokens
        ├── hooks/
        │   └── useApi.ts        # TanStack Query hooks for all API endpoints
        └── types/
            └── index.ts         # TypeScript type definitions
```

---

## D. Backend Implementation Status

### Fully Implemented
- FastAPI application with lifespan, CORS, exception handling
- JWT authentication (access + refresh tokens)
- Role-based access control (admin, faculty, staff)
- All CRUD API routers: users, students, parents, attendance, calls, campaigns, absence reports, follow-ups
- Call orchestration service (create_calls_for_absentees, initiate_call, process_call_completion)
- Automatic follow-up creation from low-confidence extractions
- Vapi voice provider (full implementation with assistant config, system prompts, webhook parsing)
- Mock voice provider (for testing/development)
- Webhook handler with HMAC-SHA256 signature verification
- Rate limiting middleware (token bucket, per-endpoint configuration)
- AI extraction service (OpenAI + Anthropic providers, function calling, prompt versioning)
- Extraction schema with confidence scoring and follow-up triage
- RQ background job infrastructure (worker, queues, async bridge)
- Job service with idempotency keys, retry scheduling, deferred dispatch
- Background tasks: initiate_pending_call, retry_failed_call, activate_campaign, schedule_campaign_calls, create_followup_calls, schedule_followups, schedule_retry, dispatch_due_retries
- Audit log model
- Health/readiness/liveness endpoints
- Alembic migrations (2 migrations: initial schema + jobs table)
- Repository pattern (BaseRepository + UserRepository + StudentRepository)
- Structured logging
- Pydantic settings from environment

### Partially Implemented
- Test call endpoint (works but uses VapiProvider() directly, not configurable)
- vapi_client.py (appears to be a legacy low-level client; not referenced by current code)
- Health check: database check says "not yet implemented" in detailed endpoint

---

## E. Frontend Implementation Status

### Fully Implemented
- Next.js 14.1 with App Router
- TypeScript throughout
- Tailwind CSS + custom primary color theme
- Authentication context (login/logout, token storage in localStorage)
- Protected route component
- Dashboard layout with navigation
- TanStack Query hooks for all API endpoints (students, attendance, calls, absence reports, follow-ups, campaigns)
- Full type definitions matching backend schemas
- Dashboard page with stats cards and today's absentees
- Login page
- Student list + detail pages
- Attendance page
- Call log + detail pages
- Absence report list + detail pages
- Follow-up tasks page
- UI components: Button, Badge (with domain-specific variants)

### **CRITICAL ISSUE: Missing `src/lib/` directory**
- `frontend/src/lib/api.ts` (axios client) — **MISSING**
- `frontend/src/lib/utils.ts` (cn, formatDate, formatDateTime, formatDuration) — **MISSING**
- These files are imported by virtually every frontend file
- Root cause: `.gitignore` includes `lib/` pattern (meant for Python) which also ignores `frontend/src/lib/`
- **The frontend cannot build or run without these files**

### Not Implemented
- Analytics/reports page (no dedicated analytics route)
- Campaign management UI
- Bulk attendance entry UI

---

## F. Database / Migrations

### Models (12 tables)
| Table | Description |
|-------|-------------|
| users | Faculty/staff/admin accounts |
| students | Student records |
| parents | Parent/guardian contacts (FK → students) |
| attendance | Daily attendance records (FK → students, users) |
| call_campaigns | Organized call batches |
| calls | Call records (FK → campaigns, students, parents, attendance) |
| call_attempts | Individual call attempt records |
| absence_reports | AI-extracted absence info (1:1 with calls) |
| followups | Follow-up tasks |
| audit_logs | Operation audit trail |
| jobs | RQ job tracking + idempotency |

### Migrations
1. `001_initial_schema` — All tables except jobs
2. `002_add_job_table` — Jobs table for RQ background jobs

### Key Design
- All primary keys are UUID strings (36 chars)
- Timestamps are naive UTC DateTime
- Proper foreign keys and indexes throughout
- Unique constraints (e.g., student+date+period for attendance)

---

## G. AI Architecture

### Extraction Pipeline
1. Call transcript received via webhook
2. `CallService._extract_and_save_absence_info()` invokes `AIService`
3. `AIService` delegates to `ExtractionProvider` (factory pattern)
4. Provider (OpenAI or Anthropic) calls LLM with:
   - System prompt from `ExtractionPromptManager` (v1.1)
   - User prompt with transcript + student context
   - Function calling schema (OpenAI) or JSON instructions (Anthropic)
5. Response validated through `ExtractedAbsenceInfo` Pydantic model
6. Confidence scoring: 0-1.0 with automatic tier classification
7. Follow-up auto-created when confidence < 0.85 or refusal detected

### Providers
- **OpenAI**: GPT-4o with function calling (`record_absence_information`)
- **Anthropic**: Claude 3.5 Sonnet with JSON structured output
- Both have retry logic (2 retries with exponential backoff)
- Prompt versioning system (v1.0, v1.1, LATEST)

---

## H. Voice / Vapi Architecture

### Provider Abstraction
- `VoiceProvider` ABC: create_call, get_call_status, cancel_call, parse_webhook_payload
- `VapiProvider`: Full implementation with:
  - Dynamic assistant config per call (student name, date in first message + system prompt)
  - Pre-created assistant support (assistantId + overrides)
  - Metadata-based correlation (correlation_id in webhook metadata)
  - Webhook payload parsing (transcript from messages array)
- `MockVoiceProvider`: In-memory simulation with helper methods (simulate_answer, simulate_no_answer, simulate_failed)

### Webhook Flow
1. Vapi sends POST to `/webhooks/vapi` with HMAC-SHA256 signature
2. Signature verified via `X-Vapi-Signature` header
3. Payload parsed for correlation_id (our internal Call.id)
4. Call completion triggers extraction pipeline
5. Failed calls trigger retry logic

---

## I. Background Job Architecture

### Technology
- **Redis** as message broker
- **RQ** (Redis Queue) for job execution
- Synchronous RQ tasks bridged to async via `run_async_task()`

### Queues (4 dedicated)
| Queue | Purpose |
|-------|---------|
| calls | Call initiation |
| retries | Call retry execution |
| campaigns | Campaign activation + scheduling |
| followups | Follow-up batch creation |

### Tasks Implemented
| Task | Type | Description |
|------|------|-------------|
| `initiate_pending_call` | INITIATE_CALL | Initiate a single pending call via Vapi |
| `retry_failed_call` | RETRY_CALL | Retry a failed/no-answer call |
| `activate_campaign` | SCHEDULE_CAMPAIGN_CALLS | Activate campaign, defer to scheduled_start |
| `schedule_campaign_calls` | SCHEDULE_CAMPAIGN_CALLS | Create calls for campaign absences |
| `create_followup_calls` | CREATE_FOLLOWUP_CALLS | Batch create follow-ups for completed calls |
| `schedule_followups` | CREATE_FOLLOWUP_CALLS | Queue a follow-up batch (singleton) |
| `schedule_retry` | RETRY_CALL | Schedule deferred retry with backoff |
| `dispatch_due_retries` | RETRY_CALL | Dispatch all due deferred retries |

### Idempotency
- Each task creates a DB `Job` record with unique `idempotency_key`
- Duplicate detection: same key → return existing job
- Active job detection: QUEUED/STARTED/DEFERRED jobs block new scheduling
- Deferred retries stored in DB (survive worker restarts)
- Retry backoff: 5min → 15min → 1hr (configurable)

---

## J. Security Status

### IMPLEMENTED ✅
| Feature | Implementation |
|---------|---------------|
| JWT authentication | Access + refresh tokens, HS256, configurable expiry |
| Role-based access | admin/faculty/staff with dependency injection |
| Password hashing | bcrypt via passlib |
| Webhook signature | HMAC-SHA256 with constant-time comparison |
| Rate limiting | Token bucket middleware, per-endpoint, per-client IP |
| CORS | Configurable origins |
| Audit log model | Stores action, entity, user, IP, user_agent, changes JSON |

### PARTIALLY IMPLEMENTED ⚠️
| Feature | Status |
|---------|--------|
| Token refresh | Endpoint exists but no token rotation (same sub → new tokens, old refresh still valid) |
| Register endpoint | Open to anyone (no admin-only restriction in production) |
| Audit logging | Model exists but not wired into API routes (no middleware/interceptor) |

### DESIGNED BUT NOT IMPLEMENTED 📋
| Feature | Status |
|---------|--------|
| httpOnly cookie tokens | Design documented in PRIORITY_3_TOKEN_HARDENING.md |
| CSRF protection | Design documented |
| AES-256-GCM sensitive data encryption | Design documented in PRIORITY_4_SENSITIVE_DATA.md |
| Row-level access control (RLAC) | Design documented |
| Data masking | Design documented |
| Retention policy enforcement | Config exists, no cron/job to enforce |

### NOT IMPLEMENTED ❌
| Feature | Status |
|---------|--------|
| Token revocation/blacklist | Not implemented |
| Session management | Not implemented |
| MFA | Not implemented |
| API key authentication for service-to-service | Not implemented |
| Request/response logging middleware | Not implemented |
| Sensitive field encryption at rest | Not implemented |

### Frontend Security Concerns
- Tokens stored in **localStorage** (XSS vulnerable)
- No CSRF protection
- No token auto-refresh logic in frontend

---

## K. Testing Status

### Test Counts (from source code analysis)
| Test File | Tests | Status |
|-----------|-------|--------|
| test_api.py | 9 | Auth, user, student API tests |
| test_extraction.py | 21 | AI extraction unit tests |
| test_health.py | 5 | Health endpoint tests |
| test_models.py | 5 | Model creation tests |
| test_phase10_foundations.py | 15 | Job service, idempotency |
| test_phase10_step5.py | 29 | Scheduling, retries, dispatch |
| test_rate_limit.py | 18 | Rate limiting middleware |
| test_voice_services.py | 5 | Voice provider tests |
| test_webhooks.py | 9 | Webhook handling tests |
| **Total** | **116** | **Matches historical report** |

### Test Configuration
- pytest-asyncio with `asyncio_mode = auto`
- Tests use real PostgreSQL database (not test DB isolation)
- Session-scoped seeding: TRUNCATE + seed 3 users + 1 student
- Per-test: transaction rollback (except tests with explicit commit)
- Coverage: pytest-cov configured (`--cov=app --cov-report=html`)
- Tests require running PostgreSQL instance

### Test Isolation Issues
- Tests share a real database (not a separate test DB)
- Some tests use explicit `commit()` which bypasses rollback
- The conftest truncates all tables at session start to handle this

### Not Tested
- Frontend has no tests (no jest, vitest, or playwright configured)
- No integration tests
- No E2E tests

---

## L. Current Git / Commit State

- **Branch**: `arena/01a0ae8b-attendai` (branched from `main`)
- **Commit**: `41167af` — "docs: add project and security documentation"
- **Working tree**: Clean (no uncommitted changes)
- **Only 1 commit** visible on this branch (shallow clone or squashed)
- **Remote**: `origin/main` available
- **Historical commits mentioned** (4efe937, 286ef2b) are not visible in this checkout

---

## M. Completed Features (A)

1. ✅ Full database schema (12 models, 2 migrations)
2. ✅ FastAPI application with all CRUD routers
3. ✅ JWT authentication + RBAC
4. ✅ Student/Parent/Attendance CRUD
5. ✅ Call management (create, initiate, complete)
6. ✅ Call campaigns
7. ✅ Call attempts tracking
8. ✅ Vapi voice provider integration
9. ✅ Mock voice provider for dev/test
10. ✅ Webhook handling with HMAC-SHA256 verification
11. ✅ AI extraction (OpenAI + Anthropic) with confidence scoring
12. ✅ Absence reports with review workflow
13. ✅ Follow-up auto-creation + manual CRUD
14. ✅ RQ background job infrastructure
15. ✅ Job idempotency + retry scheduling + deferred dispatch
16. ✅ Campaign scheduling
17. ✅ Follow-up batch scheduling
18. ✅ Rate limiting middleware
19. ✅ Audit log model
20. ✅ Health/readiness/liveness endpoints
21. ✅ Frontend: Login, Dashboard, Students, Attendance, Calls, Reports, Follow-ups pages
22. ✅ Frontend: All API hooks (TanStack Query)
23. ✅ Frontend: Auth context + protected routes
24. ✅ Docker Compose (5 services)
25. ✅ 116 backend tests

---

## N. Partially Completed Features (B)

1. ⚠️ **Frontend build is broken** — missing `src/lib/api.ts` and `src/lib/utils.ts` (gitignored)
2. ⚠️ **Audit logging** — model exists but not wired into routes
3. ⚠️ **Token refresh** — no rotation, no revocation
4. ⚠️ **Health check** — database check not fully implemented
5. ⚠️ **Test isolation** — shared real database, no test-specific DB
6. ⚠️ **Register endpoint** — open to public (should be admin-only in production)
7. ⚠️ **Call retry flow** — task exists but `_handle_retry` in CallService only increments count; doesn't actually enqueue via `schedule_retry`

---

## O. Designed But Not Implemented (C)

1. 📋 httpOnly cookie-based token storage (design in PRIORITY_3_TOKEN_HARDENING.md)
2. 📋 CSRF protection (design in PRIORITY_3_TOKEN_HARDENING.md)
3. 📋 Token rotation on refresh
4. 📋 AES-256-GCM encryption for sensitive parent/student data (PRIORITY_4_SENSITIVE_DATA.md)
5. 📋 Row-level access control (RLAC)
6. 📋 Data masking for PII
7. 📋 Retention policy enforcement job
8. 📋 Analytics/reporting page (frontend types include `DashboardStats` but no analytics page)

---

## P. Missing Features (D)

1. ❌ Analytics/reports dashboard page
2. ❌ Bulk attendance import
3. ❌ Campaign management UI
4. ❌ Email/SMS notification channels
5. ❌ Parent portal (parent self-service)
6. ❌ Multi-language voice support
7. ❌ Call recording playback in UI
8. ❌ Export/download reports (CSV/PDF)
9. ❌ Real-time dashboard updates (WebSocket/SSE)
10. ❌ Frontend test suite
11. ❌ E2E test suite
12. ❌ CI/CD pipeline
13. ❌ Production deployment configuration
14. ❌ Monitoring/alerting (Prometheus client in requirements but unused)
15. ❌ Multi-tenancy
16. ❌ SMS fallback for unreachable parents
17. ❌ Voicemail detection and handling
18. ❌ Calendar integration for expected return dates

---

## Q. Known Risks

### Critical
1. **Frontend cannot build** — `src/lib/api.ts` and `src/lib/utils.ts` are missing (gitignored by `lib/` pattern in `.gitignore`)
2. **Tokens in localStorage** — vulnerable to XSS attacks; should migrate to httpOnly cookies
3. **No token revocation** — compromised tokens remain valid until expiry
4. **Open registration** — `/api/auth/register` is publicly accessible

### High
5. **No test database isolation** — tests share production-like DB; flaky under concurrent runs
6. **Audit logging not wired** — model exists but no automatic logging on API operations
7. **No frontend tests** — zero test coverage on the frontend
8. **No CI/CD** — no automated testing/deployment pipeline
9. **Sensitive data unencrypted** — parent phone numbers, student data stored in plaintext
10. **No production secrets management** — `.env` based only

### Medium
11. **Celery in requirements.txt** — unused dependency (project uses RQ only)
12. **next-auth in package.json** — unused dependency (project uses custom auth)
13. **vapi_client.py** — appears to be dead code (VapiProvider handles all Vapi calls directly)
14. **No database connection health check** in detailed health endpoint
15. **Single commit history** — historical commits (4efe937, 286ef2b) not visible; may have been squashed

---

## R. Recommended Next Phase

### Immediate Priority: Fix Critical Blockers

**Phase 11 — Critical Fixes & Frontend Completion**

1. **Fix gitignore** — Remove or scope the `lib/` pattern so `frontend/src/lib/` is tracked
2. **Create `frontend/src/lib/api.ts`** — Axios client with auth token injection and base URL
3. **Create `frontend/src/lib/utils.ts`** — `cn()` helper, date formatting utilities
4. **Verify frontend builds** — `npm run build` should pass
5. **Verify backend tests pass** — Run the 116-test suite
6. **Restrict registration endpoint** — Require admin role or disable in production

### Then: Security & Production Readiness

**Phase 12 — Security Hardening (Implementation)**
- Migrate tokens to httpOnly cookies
- Implement CSRF protection
- Add token rotation on refresh
- Wire audit logging into API routes
- Encrypt sensitive fields at rest

**Phase 13 — Analytics & Reporting**
- Analytics dashboard page
- Report generation/export
- Real-time updates

**Phase 14 — Production Deployment**
- CI/CD pipeline
- Production secrets management
- Monitoring/alerting
- Load testing

---

## S. Recommended Implementation Order

| # | Task | Priority | Effort |
|---|------|----------|--------|
| 1 | Fix `.gitignore` + create missing `frontend/src/lib/` files | Critical | 30 min |
| 2 | Verify frontend builds (`npm run build`) | Critical | 15 min |
| 3 | Verify backend tests (116/116 passing) | Critical | 15 min |
| 4 | Restrict registration endpoint | High | 30 min |
| 5 | Add token auto-refresh in frontend | High | 2 hours |
| 6 | Wire audit logging into API routes | High | 3 hours |
| 7 | Create dedicated test database | High | 1 hour |
| 8 | Remove unused dependencies (celery, next-auth) | Medium | 15 min |
| 9 | Remove dead code (vapi_client.py) | Medium | 15 min |
| 10 | httpOnly cookie migration | High | 4 hours |
| 11 | Analytics dashboard page | Medium | 6 hours |
| 12 | Frontend test suite (vitest + testing-library) | Medium | 8 hours |
| 13 | CI/CD pipeline (GitHub Actions) | Medium | 4 hours |
| 14 | Production deployment config | High | 4 hours |
| 15 | Sensitive data encryption | Medium | 6 hours |

---

## Summary

AttendAI has a solid, well-architected backend with comprehensive CRUD operations, AI extraction, voice integration, and background job processing. The frontend has good page coverage and type definitions but has a **critical blocker** (missing lib files due to gitignore). Security hardening has been designed but only partially implemented (webhook verification and rate limiting are done; cookie tokens, CSRF, and encryption remain as designs only). The 116-test backend suite matches historical reports. The project is at approximately **Phase 10 complete** with security partially complete, ready for critical fixes and then production-readiness work.
