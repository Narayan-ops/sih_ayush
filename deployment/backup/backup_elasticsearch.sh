#!/bin/bash
#
# Elasticsearch Backup Script
# Per ARCHITECTURE-ADDENDUM: Sparse store snapshots for disaster recovery
#

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backups/elasticsearch}"
ES_HOST="${ES_HOST:-localhost}"
ES_PORT="${ES_PORT:-9200}"
REPO_NAME="${REPO_NAME:-ipsakti_backup_repo}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${RETENTION_DAYS:-2555}"  # 7 years

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "Starting Elasticsearch backup at $(date)"

# Register snapshot repository (if not exists)
curl -X PUT "http://${ES_HOST}:${ES_PORT}/_snapshot/${REPO_NAME}" \
    -H "Content-Type: application/json" \
    -d "{
        \"type\": \"fs\",
        \"settings\": {
            \"location\": \"${BACKUP_DIR}\"
        }
    }" || echo "Repository may already exist"

# Create snapshot
SNAPSHOT_NAME="snapshot_${TIMESTAMP}"
curl -X PUT "http://${ES_HOST}:${ES_PORT}/_snapshot/${REPO_NAME}/${SNAPSHOT_NAME}" \
    -H "Content-Type: application/json" \
    -d '{
        "indices": "*",
        "ignore_unavailable": true,
        "include_global_state": false
    }'

echo "Snapshot created: ${SNAPSHOT_NAME}"

# Clean up old snapshots using find
if command -v find &> /dev/null; then
    find "$BACKUP_DIR" -name "snapshot_*" -mtime +$RETENTION_DAYS -delete 2>/dev/null || echo "Cleanup skipped"
else
    echo "find command not available - manual cleanup required"
fi

echo "Old snapshots cleaned up (retention: $RETENTION_DAYS days)"
echo "Backup process finished at $(date)"
