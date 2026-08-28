#!/bin/bash
#
# Qdrant Backup Script
# Per ARCHITECTURE-ADDENDUM: Vector store snapshots for disaster recovery
#

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backups/qdrant}"
QDRANT_HOST="${QDRANT_HOST:-localhost}"
QDRANT_PORT="${QDRANT_PORT:-6333}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${RETENTION_DAYS:-2555}"  # 7 years

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "Starting Qdrant backup at $(date)"

# Get list of collections
COLLECTIONS=$(curl -s "http://${QDRANT_HOST}:${QDRANT_PORT}/collections" | \
    python -c "import sys, json; print(' '.join([c['name'] for c in json.load(sys.stdin)['result']]))")

# Create snapshot for each collection
for collection in $COLLECTIONS; do
    echo "Creating snapshot for collection: $collection"
    
    # Trigger snapshot creation
    SNAPSHOT_NAME="${collection}_${TIMESTAMP}"
    curl -X PUT "http://${QDRANT_HOST}:${QDRANT_PORT}/collections/${collection}/snapshots" \
        -H "Content-Type: application/json" \
        -d "{\"snapshot_name\": \"${SNAPSHOT_NAME}\"}"
    
    # Download snapshot
    curl -o "${BACKUP_DIR}/${collection}_${TIMESTAMP}.snapshot" \
        "http://${QDRANT_HOST}:${QDRANT_PORT}/collections/${collection}/snapshots/${SNAPSHOT_NAME}"
    
    # Compress
    gzip "${BACKUP_DIR}/${collection}_${TIMESTAMP}.snapshot"
    
    echo "Snapshot created: ${collection}_${TIMESTAMP}.snapshot.gz"
done

# Clean up old snapshots
if command -v find &> /dev/null; then
    find "$BACKUP_DIR" -name "*.snapshot.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || echo "Cleanup skipped"
else
    echo "find command not available - manual cleanup required"
fi

echo "Old snapshots cleaned up (retention: $RETENTION_DAYS days)"
echo "Backup process finished at $(date)"
