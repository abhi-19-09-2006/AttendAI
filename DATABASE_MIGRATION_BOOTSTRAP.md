# Database Migration Bootstrap Procedure

## Problem Statement

AttendAI databases may exist in one of three states:

1. **Fresh database**: No tables, no `alembic_version` table
2. **Existing database (pre-Alembic)**: Tables created by `Base.metadata.create_all()`, no `alembic_version` table
3. **Managed database**: Tables created by Alembic, has `alembic_version` table

Phase 14 introduced schema changes that require proper migration handling:
- `refresh_tokens` table (new)
- `audit_logs.changes` column (may be missing in pre-Alembic databases)

## Migration Chain

```
001 (initial schema) → 002 (jobs table) → 003 (refresh_tokens + audit_logs.changes)
```

## Bootstrap Procedure

### For Existing Databases (Most Common Case)

If your database was created before Alembic migrations were added (i.e., `alembic_version` table does NOT exist):

```bash
cd backend

# Step 1: Verify current state
alembic current
# Expected output: (no output, or "Current revision(s) for <db_url>: (none)")

# Step 2: Check if tables exist
psql -U attendai -d attendai_db -c "\dt"
# You should see: users, students, parents, attendance, calls, etc.

# Step 3: Stamp the database to migration 002
# This tells Alembic "the database is already at this state"
alembic stamp 002

# Step 4: Verify stamp worked
alembic current
# Expected output: "002 (head)"

# Step 5: Apply migration 003 (adds refresh_tokens and ensures audit_logs.changes)
alembic upgrade head

# Step 6: Verify final state
alembic current
# Expected output: "003 (head)"
```

### For Fresh Databases

If you're starting with a completely empty database:

```bash
cd backend

# Just run all migrations from the beginning
alembic upgrade head

# Verify
alembic current
# Expected output: "003 (head)"
```

### For Already-Managed Databases

If your database already has `alembic_version` and is at migration 002:

```bash
cd backend

# Check current state
alembic current
# Expected output: "002"

# Upgrade to latest
alembic upgrade head

# Verify
alembic current
# Expected output: "003 (head)"
```

## Verification

After running the appropriate bootstrap procedure, verify the schema:

```bash
# Check that refresh_tokens table exists
psql -U attendai -d attendai_db -c "\dt refresh_tokens"

# Check that audit_logs.changes column exists
psql -U attendai -d attendai_db -c "\d audit_logs" | grep changes

# Expected output should show:
#  changes | json  |  |  | 
```

## Troubleshooting

### Error: "relation already exists" when running `alembic upgrade head`

This means your database already has tables but no `alembic_version`. Use the "Existing Databases" procedure above.

### Error: "column 'changes' does not exist"

This means your `audit_logs` table was created from an older model version. Migration 003 will add this column automatically. Run the bootstrap procedure.

### Error: "relation 'alembic_version' does not exist"

This is expected for pre-Alembic databases. Use `alembic stamp` as shown in the "Existing Databases" procedure.

### Error: "target revision '002' not found"

Make sure you're in the `backend` directory and that the migration files exist:
```bash
ls alembic/versions/
# Should show: 001_*.py, 002_*.py, 003_*.py
```

## What Migration 003 Does

Migration 003 is **idempotent** and safe to run on any database state:

1. **Checks if `audit_logs.changes` exists**: Only adds the column if it's missing
2. **Creates `refresh_tokens` table**: Required for Phase 14 authentication hardening
3. **Creates indexes**: For performance on `refresh_tokens` queries

The migration uses SQLAlchemy's inspector to check column existence before adding, making it safe for:
- Databases that already have the `changes` column (no-op)
- Databases missing the `changes` column (adds it)
- Fresh databases (creates everything)

## Rollback

If you need to rollback migration 003:

```bash
alembic downgrade 002
```

This will:
- Drop the `refresh_tokens` table and its indexes
- **NOT** remove the `audit_logs.changes` column (it was part of the original schema)

## Testing

After migration, run the test suite to verify:

```bash
cd backend
pytest tests/test_api.py::test_login_success -v
pytest tests/test_admin.py -v
pytest tests/test_e2e_vapi_integration.py -v
pytest tests/ -v
```

All tests should pass with no schema errors.

## Production Deployment

For production deployment:

1. **Backup your database first**
2. Run the appropriate bootstrap procedure above
3. Verify with `alembic current` showing "003 (head)"
4. Deploy the application code
5. Monitor logs for any schema-related errors

## Summary

- **Existing databases**: `alembic stamp 002` → `alembic upgrade head`
- **Fresh databases**: `alembic upgrade head`
- **Managed databases**: `alembic upgrade head`

Migration 003 is idempotent and handles all edge cases safely.
