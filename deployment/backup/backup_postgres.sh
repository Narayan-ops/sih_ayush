#!/bin/bash
#
# PostgreSQL Backup Script
# Per ARCHITECTURE-ADDENDUM: 7-year audit retention requirement
#

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backups/postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-ipsakti}"
DB_USER="${DB_USER:-postgres}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${RETENTION_DAYS:-2555}"  # 7 years = 2555 days

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "Starting PostgreSQL backup at $(date)"

# Perform backup
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -F c -f "$BACKUP_DIR/ipsakti_${TIMESTAMP}.dump"

# Compress backup
gzip "$BACKUP_DIR/ipsakti_${TIMESTAMP}.dump"

echo "Backup completed: ipsakti_${TIMESTAMP}.dump.gz"

# Clean up old backups (per 7-year retention)
# Note: This script is designed for Linux/Unix environments
# For Windows, use PowerShell scheduled tasks with equivalent logic
if command -v find &> /dev/null; then
    find "$BACKUP_DIR" -name "ipsakti_*.dump.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || echo "Cleanup skipped"
else
    echo "find command not available - manual cleanup required"
fi

echo "Old backups cleaned up (retention: $RETENTION_DAYS days)"
echo "Backup process finished at $(date)"
