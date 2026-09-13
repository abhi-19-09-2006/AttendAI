# Phase 9: Faculty Dashboard - Complete

## ✅ PHASE 9 COMPLETE

**Completion Date**: September 13, 2026
**Status**: Ready for testing

---

## 📊 Summary of Deliverables

This phase finished the Next.js faculty dashboard that was scaffolded in the initial
frontend commit. It turns the placeholder UI into a fully wired console backed by the
existing FastAPI services.

### Backend Support (2 endpoints)

| Change | File | Purpose |
|--------|------|---------|
| `?call_id=` filter on absence reports | `backend/app/api/absence_reports.py` | Lets the call detail page fetch a call's transcript + extracted report |
| `POST /api/calls/{call_id}/retry` | `backend/app/api/calls.py` | Re-initiates a failed/unanswered call via `CallService`, increments the retry counter, validates state (only retryable statuses, max not exhausted) |

### Frontend (8 files)

| Page / File | Change |
|-------------|--------|
| **`/calls/[id]`** (NEW) | Call detail page: status, full timeline (initiated/answered/ended), duration, retry counter, student link, provider call ID, absence-report summary, and a chat-bubble **transcript viewer** that splits `Assistant:` / `Parent:` lines into styled bubbles |
| `calls/page.tsx` | Wired the "Retry" button to `useRetryCall` per row (via a `CallRow` subcomponent so hooks stay at the top level); added a "Details" link to the new detail page; shows retry progress on the button |
| `followups/page.tsx` | Fixed the dead "Mark Complete" mock button — now opens an inline resolution-notes form and calls `POST /followups/{id}/complete` correctly (removed the `useCompleteFollowUp('')` + `as any` hack); added student name + profile link per card |
| `students/page.tsx` | Implemented the previously-dead **Add Student** button as a modal form wired to `useCreateStudent` (validation + error display) |
| `attendance/page.tsx` | Replaced truncated student IDs with resolved student names; each row links to the student profile |
| `students/[id]/page.tsx` | Recent Communication entries now link through to the new call detail page |
| `DashboardLayout.tsx` | Renamed misleading "Call Campaigns" nav item to "Call Log" (the route it actually points to) |
| `hooks/useApi.ts` | Added `useRetryCall`, added `call_id` param to `useAbsenceReports` |

### Build Blockers Fixed

The scaffold had never been fully built (TypeScript + `@types/*` were missing from
`node_modules` because the machine's npm is configured with `omit=dev`). Fixed by
installing dev dependencies with `--include=dev` and escaping two pre-existing
apostrophes in `dashboard/page.tsx` that failed ESLint's `react/no-unescaped-entities`.

---

## ✅ Phase 9 Acceptance Criteria

| Requirement | Status | Notes |
|-------------|--------|-------|
| Login page with authentication | ✅ | From scaffold, tested |
| Dashboard homepage with statistics | ✅ | Client-side aggregation |
| Student list and search | ✅ | Pagination + search from scaffold |
| Student detail with attendance history | ✅ | Linked into call detail |
| Call history page | ✅ | List with retry action |
| **Call detail page with transcript viewer** | ✅ **NEW** | Styled transcript bubbles |
| Absence report display + review flow | ✅ | From scaffold (review/approve) |
| Follow-up queue interface | ✅ **FIXED** | Working completion flow |
| Calls retryable from the UI | ✅ **NEW** | Backed by new retry endpoint |
| Add a student from the UI | ✅ **NEW** | Modal form |
| Responsive layout | ✅ | Tailwind grid, mobile-nav fallback |

---

## ✅ Verification

- `tsc --noEmit` — passes with no errors
- `next build` — all 12 routes compile, static pages generate, `λ /calls/[id]` renders on demand
- Backend changed files pass `python -m py_compile`

---

## ▶️ Test It Now

```bash
# 1. Start the stack (backend + DB)
docker-compose up -d

# 2. Start the frontend
cd frontend && npm run dev

# 3. Open http://localhost:3000/login and sign in as a seeded faculty user

# 4. Exercise the new flows
#    - Calls → click "Details" on any call → transcript viewer + report summary
#    - A failed/no-answer call → click "Retry (n/max)"
#    - Follow-ups → "Mark Complete" on a pending task → add notes → Confirm
#    - Students → "Add Student" → fill the form → row appears in the list
#    - Attendance → pick a date → names resolve and link to profiles
```

---

## ⚠️ Notes & Limitations

- The transcript viewer renders `Assistant:`/`Parent:`/(`Student:`/`Unknown:`)
  prefixed lines as bubbles; any other line style falls back to plain italic text —
  the exact prefixes depend on the Vapi transcript format.
- Student-name lookups on the Attendance/Follow-ups pages fetch up to the backend
  cap of 100 students. Larger rosters would want a server-side join or a dedicated
  name-lookup endpoint.
- The retry endpoint delegates to `CallService.initiate_call`, so without configured
  Vapi credentials a retry will mark the call `failed` and surface a 500 to the UI —
  matching the existing test-call endpoint's behavior.
- Dashboard stats are still aggregated client-side; a dedicated
  `GET /api/calls/statistics` endpoint (backend `get_call_statistics` exists) is a
  candidate for Phase 10.

---

**Next**: Phase 10 (Analytics, Reports & Audit) or Phase 8 (Retry & Follow-up
engine) — Phase 8's background job scheduling would make auto-retries (rather than
manual UI retries) run unattended.