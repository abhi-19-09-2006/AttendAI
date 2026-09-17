# Analytics Test Data Leakage Fix

**Date**: 2026-09-17  
**Branch**: `arena/01a0ae8b-attendai`  
**Commit**: `d1f835b`  
**Previous Commit**: `9f37a2b` (143 passed, 9 failed - all in test_analytics.py)

---

## Problem

All 9 failures in the backend test suite were in `tests/test_analytics.py` with inflated counts:

| Test | Expected | Actual | Pattern |
|------|----------|--------|---------|
| `test_daily_trends` | 1 | 4 | 4× multiplier |
| `test_call_metrics` | 5 | 25 | 5× multiplier |
| `test_absence_reason_distribution` | 1 | 6 | 6× multiplier |
| `test_daily_report` | 1 | 7 | 7× multiplier |
| `test_followup_report` | 1 | 9 | 9× multiplier |
| `test_unreachable_report` | 1 | 10 | 10× multiplier |
| `test_analytics_summary_authenticated` | 5 | 60 | 12× multiplier |
| `test_analytics_call_metrics_endpoint` | 5 | 65 | 13× multiplier |
| `test_analytics_reports_unreachable_endpoint` | 1 | 16 | 16× multiplier |

The multipliers indicate cumulative data accumulation across test runs.

---

## Root Cause

The `analytics_data` fixture in `backend/tests/test_analytics.py`:

1. **Created test data**: 5 attendance records, 5 calls, 3 absence reports, 1 follow-up, 1 parent
2. **Committed the data**: `await db_session.commit()` at line 113
3. **Never cleaned up**: No teardown logic to delete the created records

**Result**: Each of the 17 tests using this fixture added a new set of records to the database. Tests that ran later saw accumulated data from all previous tests.

**Why this happened**:
- The `db_session` fixture uses `begin()` + `rollback()` in a finally block
- But when tests call `commit()`, the data is persisted to the database
- The `analytics_data` fixture explicitly called `commit()` to make data visible to HTTP clients
- Without cleanup, committed data survived across tests

**Why previous fixes didn't catch this**:
- Commit `603c6fa` used connection-scoped transactions that prevented commits from persisting → fixed isolation but broke HTTP client visibility (404 errors)
- Commit `9f37a2b` reverted to allow commits → restored HTTP visibility but re-introduced data leakage

---

## Solution

Added comprehensive cleanup logic to the `analytics_data` fixture:

### Changes to `backend/tests/test_analytics.py`

**Before**:
```python
@pytest.fixture
async def analytics_data(db_session: AsyncSession):
    # ... create data ...
    await db_session.commit()
    return entries  # No cleanup!
```

**After**:
```python
@pytest.fixture
async def analytics_data(db_session: AsyncSession):
    # Track created IDs for cleanup
    followup_ids = []
    absence_report_ids = []
    call_ids = []
    attendance_ids = []
    
    # ... create data, tracking IDs ...
    
    await db_session.commit()
    
    try:
        yield entries
    finally:
        # Cleanup: delete in reverse dependency order
        from sqlalchemy import delete
        
        if followup_ids:
            await db_session.execute(
                delete(FollowUp).where(FollowUp.id.in_(followup_ids))
            )
        
        if absence_report_ids:
            await db_session.execute(
                delete(AbsenceReport).where(AbsenceReport.id.in_(absence_report_ids))
            )
        
        if call_ids:
            await db_session.execute(
                delete(Call).where(Call.id.in_(call_ids))
            )
        
        if attendance_ids:
            await db_session.execute(
                delete(Attendance).where(Attendance.id.in_(attendance_ids))
            )
        
        # Delete parent (created by this fixture)
        await db_session.execute(
            delete(Parent).where(Parent.id == parent.id)
        )
        
        await db_session.commit()
```

### Key Design Decisions

1. **Track IDs during creation**: Store all created record IDs in lists for precise cleanup
2. **Use try/finally**: Ensure cleanup runs even if the test fails or raises an exception
3. **Delete in reverse dependency order**: 
   - Follow-ups (depends on absence reports and calls)
   - Absence reports (depends on calls and attendance)
   - Calls (depends on attendance and parents)
   - Attendance (depends on students and users)
   - Parent (depends on students)
4. **Commit cleanup**: Persist deletions so they're visible to subsequent tests
5. **Preserve seeded data**: Don't delete users or students (created by `seeded_db` fixture, used by other tests)

---

## Why This Approach

### Evaluated Alternatives

1. **Connection-scoped transactions** (commit `603c6fa`):
   - ✅ Perfect isolation
   - ❌ Broke HTTP client tests (404 errors)
   - ❌ App sessions couldn't see uncommitted test data

2. **Truncate entire database between tests**:
   - ✅ Guaranteed clean state
   - ❌ Too slow (would add seconds per test)
   - ❌ Would break `seeded_db` fixture (users, students needed by other tests)
   - ❌ Overkill for this specific problem

3. **Use unique date ranges per test**:
   - ✅ No cleanup needed
   - ❌ Requires changing all test assertions
   - ❌ Violates "don't blindly change assertions" constraint
   - ❌ Fragile (date collisions possible)

4. **Targeted cleanup of fixture-created data** (chosen):
   - ✅ Precise (only deletes what the fixture created)
   - ✅ Fast (5 DELETE statements per test)
   - ✅ Preserves seeded data (users, students remain)
   - ✅ Works with HTTP clients (data is committed, then cleaned)
   - ✅ No changes to test assertions or production code

---

## Testing Strategy

Per the user's instructions, run tests in this order:

### Step 1: Run only the 9 failing Analytics tests
```bash
cd backend
pytest tests/test_analytics.py::test_daily_trends \
       tests/test_analytics.py::test_call_metrics \
       tests/test_analytics.py::test_absence_reason_distribution \
       tests/test_analytics.py::test_daily_report \
       tests/test_analytics.py::test_followup_report \
       tests/test_analytics.py::test_unreachable_report \
       tests/test_analytics.py::test_analytics_summary_authenticated \
       tests/test_analytics.py::test_analytics_call_metrics_endpoint \
       tests/test_analytics.py::test_analytics_reports_unreachable_endpoint \
       -v
```

**Expected**: 9 passed

### Step 2: Run complete `tests/test_analytics.py`
```bash
pytest tests/test_analytics.py -v
```

**Expected**: 17 passed (11 service tests + 6 API tests)

### Step 3: Run complete 9-test E2E suite
```bash
pytest tests/test_e2e_vapi_integration.py -v
```

**Expected**: 9 passed (confirms shared fixtures not broken)

### Step 4: Run full backend suite
```bash
pytest tests/ -v
```

**Expected**: 152 passed, 0 failed

---

## Files Changed

1. `backend/tests/test_analytics.py` (1 file)
   - Added ID tracking during data creation (4 lists)
   - Wrapped fixture return in try/finally
   - Added 5 DELETE statements in finally block
   - Added commit after cleanup

**Total**: 1 file, 49 insertions, 1 deletion, 0 production code changes

---

## Constraints Satisfied

✅ No changes to Analytics production query logic  
✅ No weakened assertions  
✅ No test skips or xfails  
✅ No arbitrary filters added for tests  
✅ No production analytics behavior changes  
✅ No new database architecture  
✅ No unrelated refactoring  
✅ Minimal, focused change  
✅ Token-efficient inspection  
✅ Preserves HTTP client visibility  
✅ Preserves seeded authentication data  
✅ Deterministic cleanup  

---

## Expected Results

After this fix:

- **Analytics tests**: 17/17 passing (no inflated counts)
- **E2E tests**: 9/9 passing (shared fixtures intact)
- **Admin tests**: 11/11 passing (campaign visibility works)
- **API/Auth tests**: 10/10 passing
- **Other tests**: 105/105 passing
- **Total**: 152 passed, 0 failed

---

## Verification Required

The sandbox doesn't have PostgreSQL, so I couldn't run the tests. **You must verify on your Windows environment**:

```bash
cd backend
pytest tests/test_analytics.py -v
pytest tests/test_e2e_vapi_integration.py -v
pytest tests/ -v
```

If all tests pass, the backend suite is genuinely green at **152 passed, 0 failed**.

---

## Summary

**Root cause**: `analytics_data` fixture created and committed data but never cleaned it up, causing accumulation across 17 tests.

**Fix**: Added try/finally cleanup that deletes all fixture-created records in reverse dependency order.

**Result**: Each analytics test now starts with a clean dataset while preserving HTTP client visibility and seeded authentication data.

**Commit**: `d1f835b` pushed to `origin/arena/01a0ae8b-attendai`
