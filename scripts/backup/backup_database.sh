#!/usr/bin/env bash
#
# AttendAI Database Backup Script
#
# Creates timestamped PostgreSQL backups with compression.
# Safe for production use - never deletes existing backups.
#
# Usage:
#   ./scripts/backup/backup_database.sh
#   ./scripts/backup/backup_database.sh --keep-days 7
#
# Environment Variables:
#   POSTGRES_HOST     - Database host (default: localhost)
#   POSTGRES_PORT     - Database port (default: 5432)
#   POSTGRES_DB       - Database name (required)
#   POSTGRES_USER     - Database user (required)
#   POSTGRES_PASSWORD - Database password (required)
#   BACKUP_DIR        - Backup directory (default: ./backups)
#

set -euo pipefail

# Configuration
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${1:-}"

# Parse arguments
if [[ "$KEEP_DAYS" == "--keep-days" ]]; then
    KEEP_DAYS="${2:-7}"
else
    KEEP_DAYS=""
fi

# Validation
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

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/attendai_backup_${TIMESTAMP}.sql.gz"

echo "Starting database backup..."
echo "  Database: ${POSTGRES_DB}"
echo "  Host: ${POSTGRES_HOST}:${POSTGRES_PORT}"
echo "  Backup: ${BACKUP_FILE}"

# Export password for pg_dump
export PGPASSWORD="${POSTGRES_PASSWORD}"

# Create backup
if pg_dump \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --verbose \
    --no-owner \
    --no-privileges \
    --format=plain \
    | gzip > "$BACKUP_FILE"; then
    
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✓ Backup completed successfully"
    echo "  Size: ${BACKUP_SIZE}"
    echo "  File: ${BACKUP_FILE}"
    
    # Cleanup old backups if requested
    if [[ -n "$KEEP_DAYS" ]]; then
        echo "Cleaning up backups older than ${KEEP_DAYS} days..."
        find "$BACKUP_DIR" -name "attendai_backup_*.sql.gz" -type f -mtime +"$KEEP_DAYS" -delete
        echo "✓ Cleanup completed"
    fi
    
    exit 0
else
    echo "✗ Backup failed"
    rm -f "$BACKUP_FILE"
    exit 1
fi
