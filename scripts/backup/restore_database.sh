#!/usr/bin/env bash
#
# AttendAI Database Restore Script
#
# Restores PostgreSQL database from a backup file.
# SAFE: Requires explicit confirmation before destructive operations.
#
# Usage:
#   ./scripts/backup/restore_database.sh <backup_file>
#   ./scripts/backup/restore_database.sh backups/attendai_backup_20260922_120000.sql.gz
#
# Environment Variables:
#   POSTGRES_HOST     - Database host (default: localhost)
#   POSTGRES_PORT     - Database port (default: 5432)
#   POSTGRES_DB       - Database name (required)
#   POSTGRES_USER     - Database user (required)
#   POSTGRES_PASSWORD - Database password (required)
#   FORCE             - Skip confirmation prompt (default: false)
#

set -euo pipefail

# Configuration
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
FORCE="${FORCE:-false}"

# Validation
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Example:"
    echo "  $0 backups/attendai_backup_20260922_120000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "ERROR: Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

if [[ -z "${POSTGRES_DB:-}" ]]; then
    echo "ERROR: POSTGRES_DB environment variable is required"
    exit 1
fi

if [[ -z "${POSTGRES_USER:-}" ]]; then
    echo "ERROR: POSTGRES_USER environment variable is required"
    exit 1
fi

if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
    echo "ERROR: POSTGRES_PASSWORD environment variable is required"
    exit 1
fi

# Safety confirmation
if [[ "$FORCE" != "true" ]]; then
    echo "⚠️  WARNING: This will OVERWRITE the existing database!"
    echo ""
    echo "  Database: ${POSTGRES_DB}"
    echo "  Host: ${POSTGRES_HOST}:${POSTGRES_PORT}"
    echo "  Backup: ${BACKUP_FILE}"
    echo ""
    echo "This operation is DESTRUCTIVE and cannot be undone."
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " -r
    echo
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Restore cancelled"
        exit 0
    fi
fi

echo "Starting database restore..."
echo "  Database: ${POSTGRES_DB}"
echo "  Host: ${POSTGRES_HOST}:${POSTGRES_PORT}"
echo "  Backup: ${BACKUP_FILE}"

# Export password for psql
export PGPASSWORD="${POSTGRES_PASSWORD}"

# Terminate existing connections
echo "Terminating existing connections..."
psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres <<EOF || true
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();
EOF

# Drop and recreate database
echo "Dropping existing database..."
psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres <<EOF || true
DROP DATABASE IF EXISTS ${POSTGRES_DB};
EOF

echo "Creating fresh database..."
psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres <<EOF
CREATE DATABASE ${POSTGRES_DB};
EOF

# Restore backup
echo "Restoring backup..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" | psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB"
else
    psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$BACKUP_FILE"
fi

echo "✓ Restore completed successfully"
echo ""
echo "Next steps:"
echo "  1. Run migrations: alembic upgrade head"
echo "  2. Restart application services"
echo "  3. Verify data integrity"
echo "  4. Test application functionality"
