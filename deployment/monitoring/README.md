# Monitoring Configuration

This directory contains monitoring and alerting configuration for IP-SAKTI Sahayak.

## Components

### Prometheus (`prometheus.yml`)
Prometheus configuration for scraping metrics from all services:
- API Gateway (port 8000)
- Orchestrator (port 8001)
- Ingestion (port 8002)
- PostgreSQL (via postgres-exporter)
- Qdrant (port 6333)
- Elasticsearch (via elasticsearch-exporter)
- Node Exporter (system metrics)
- Keycloak (port 8080)

### Alert Rules (`prometheus-alerts.yaml`)
Per ARCHITECTURE-ADDENDUM alert thresholds:

| Alert | Threshold | Severity | Description |
|-------|-----------|----------|-------------|
| HighCitationRejectionRate | >15% in 1h | Critical | Citation engine rejecting too many answers |
| HighRetrievalLatency | p95 > 2s | Warning | Retrieval taking too long |
| HighEndToEndLatency | p95 > 3s | Warning | End-to-end latency exceeding SLA |
| ConfidenceDrop | >20% week-over-week | Warning | Median confidence dropped significantly |
| HighEscalationRate | 2x baseline | Warning | Escalation triggers doubled |
| DualStoreConsistencyFailure | Any failure | Critical | Qdrant/Elasticsearch write inconsistency (ADR-008) |
| HighExternalProviderUsage | >5% of sessions | Info | External provider usage review (ADR-001) |

### Grafana Dashboard (`grafana-dashboard.json`)
Overview dashboard with key metrics:
- Request rate
- Error rate
- End-to-end latency (p95)
- Retrieval latency (p95)
- Citation rejection rate
- Median confidence
- External provider usage
- Service health

## Deployment

### Prometheus
```bash
docker run -d \
  -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  -v $(pwd)/prometheus-alerts.yaml:/etc/prometheus/prometheus-alerts.yaml \
  prom/prometheus
```

### Grafana
```bash
docker run -d \
  -p 3000:3000 \
  grafana/grafana
```

Import dashboard from `grafana-dashboard.json`

## Alert Management

Alerts are configured in `prometheus-alerts.yaml`. Per ADR-006, the embedding regression gate has its own enforcement in CI.

## Data Residency

All monitoring data stays within GoI empanelled cloud infrastructure per ARCHITECTURE.md §10.
