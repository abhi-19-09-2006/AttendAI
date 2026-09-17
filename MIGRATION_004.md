# Migration 004: Add Missing Audit Logs Columns

## Issue

After applying migration 003, the `audit_logs` table was still missing required columns:
- `changes` (JSON, nullable)
- `ip_address` (VARCHAR(45), nullable)
- `user_agent` (Text, nullable)

This caused `test_login_success` to fail with:
```
asyncpg.exceptions.UndefinedColumnError: column "changes" of relation "audit_logs" does not exist
```

## Root Cause

Migration 003 only checked for and added the `changes` column, but the AuditLog model requires three columns for request context:
- `changes`: Store before/after values for tracked operations
- `ip_address`: Capture client IP address (supports IPv6, max 45 chars)
- `user_agent`: Capture client user agent string

The original `audit_logs` table (created before Phase 14) only had:
- id
- user_id
- action
- entity_type
- entity_id
- created_at

## Solution

Migration 004 adds all three missing columns idempotently:

```python
# Add 'changes' column if missing
if 'changes' not in audit_logs_columns:
    op.add_column('audit_logs', sa.Column('changes', sa.JSON(), nullable=True))

# Add 'ip_address' column if missing
if 'ip_address' not in audit_logs_columns:
    op.add_column('audit_logs', sa.Column('ip_address', sa.String(length=45), nullable=True))

# Add 'user_agent' column if missing
if 'user_agent' not in audit_logs_columns:
    op.add_column('audit_logs', sa.Column('user_agent', sa.Text(), nullable=True))
```

## Application

From the `backend` directory:

```bash
# Check current migration
alembic current
# Expected: 003 (head)

# Apply migration 004
alembic upgrade head

# Verify
alembic current
# Expected: 004 (head)
```

## Verification

After applying migration 004:

1. **Check schema**:
```bash
psql -U attendai -d attendai_db -c "\d audit_logs"
```

Should show all columns including:
- `changes` (json)
- `ip_address` (varchar(45))
- `user_agent` (text)

2. **Run tests**:
```bash
pytest tests/test_api.py::test_login_success -v
pytest tests/test_admin.py::test_admin_reset_password_success -v
pytest tests/test_e2e_vapi_integration.py -v
pytest tests/ -v
```

## Idempotency

Migration 004 is fully idempotent:
- Checks if each column exists before adding
- Safe to run multiple times
- Safe for databases that already have some columns
- Preserves all existing audit log data

## Rollback

If needed (not recommended for production):

```bash
alembic downgrade 003
```

This will drop the three columns, but **will lose any audit data stored in them**.

## Migration Chain

```
001 → 002 → 003 → 004 (current head)
```

- 001: Initial schema
- 002: Added job_status enum
- 003: Added refresh_tokens table, added changes column to audit_logs
- 004: Added missing audit_logs columns (ip_address, user_agent, and changes if not added by 003)
