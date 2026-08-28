# Backup Scripts

This directory contains backup scripts for IP-SAKTI Sahayak data stores.

## Scripts

### backup_postgres.sh
Backs up PostgreSQL database using pg_dump.
- **Retention:** 7 years (2555 days) per ARCHITECTURE-ADDENDUM
- **Format:** Compressed SQL dump
- **Usage:** Set environment variables (DB_HOST, DB_PORT, DB_NAME, DB_USER)

### backup_qdrant.sh
Backs up Qdrant vector store snapshots.
- **Retention:** 7 years
- **Format:** Compressed snapshots per collection
- **Usage:** Set QDRANT_HOST and QDRANT_PORT

### backup_elasticsearch.sh
Backs up Elasticsearch indices using snapshot API.
- **Retention:** 7 years
- **Format:** Elasticsearch snapshots
- **Usage:** Set ES_HOST and ES_PORT

### backup_minio.sh
Backs up MinIO document store.
- **Retention:** 7 years
- **Format:** Compressed tar.gz
- **Usage:** Requires MinIO Client (mc) installation

## Cron Job Setup

Add to crontab for automated backups:

```bash
# Daily backups at 2 AM
0 2 * * * /path/to/deployment/backup/backup_postgres.sh >> /var/log/ipsakti-backup.log 2>&1
0 2 * * * /path/to/deployment/backup/backup_qdrant.sh >> /var/log/ipsakti-backup.log 2>&1
0 2 * * * /path/to/deployment/backup/backup_elasticsearch.sh >> /var/log/ipsakti-backup.log 2>&1
0 2 * * * /path/to/deployment/backup/backup_minio.sh >> /var/log/ipsakti-backup.log 2>&1
```

## Disaster Recovery

Per ARCHITECTURE-ADDENDUM:
- Quarterly restore drills are required
- All backups retained for 7 years (audit compliance)
- DR failover within same GoI empanelled cloud (data residency)

## Permissions

Make scripts executable:
```bash
chmod +x deployment/backup/*.sh
```
