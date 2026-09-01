# IP-SAKTI Sahayak: beginner production runbook

This guide gets the application running locally first. Do not expose the local Docker stack to the internet. A production rollout belongs on the approved GoI cloud/Kubernetes environment with real secrets, Keycloak and a self-hosted vLLM GPU service.

## 1. Install prerequisites

Install Docker Desktop, Git, Node.js 20 LTS, Python 3.10 or 3.11, and NVIDIA drivers/CUDA appropriate for the machine that will run vLLM. Start Docker Desktop and open PowerShell in the repository root (`C:\Users\DELL\Desktop\ayush`).

## 2. Create local secrets

Copy `.env.example` to `.env`. Replace every placeholder password with a long, unique value. Do not commit `.env`.

```powershell
Copy-Item .env.example .env
```

## 3. Start the data services

```powershell
docker compose up -d postgres qdrant elasticsearch minio
docker compose ps
```

Wait until PostgreSQL, Elasticsearch and MinIO show `healthy`.

## 4. Apply the database migration

For a fresh database, the compose mount applies the schema automatically. For an existing database, run this safe, repeatable migration:

```powershell
docker cp data/relational-store/schema.sql ip-sakti-postgres:/tmp/ipsakti-schema.sql
docker exec ip-sakti-postgres psql -v ON_ERROR_STOP=1 -U $env:POSTGRES_USER -d $env:POSTGRES_DB -f /tmp/ipsakti-schema.sql
```

If PowerShell cannot find `$env:POSTGRES_USER`, open `.env`, note the values, and substitute them directly in the last command. Confirm the extra session columns exist:

```powershell
docker exec ip-sakti-postgres psql -U <your-postgres-user> -d <your-database-name> -c "\d sessions"
```

You should see `provider`, `classification_state`, `original_query`, and `deleted_at`.

## 5. Validate and ingest the local corpus

The checked-in corpus is deliberately ingested as `pending_review`; it is never
silently promoted to authoritative. First validate its structure without
printing its legal text or contacting the internet:

```powershell
python ingestion/ingest_corpus.py --source data/corpus.zip --dry-run
```

Start the ingestion service as part of step 7, then execute the same command
without `--dry-run`. It will stop and compensate both retrieval stores if it
cannot prove that every deterministic chunk exists in both places. Do not
delete an existing corpus until this command completes successfully and an AIIA
reviewer has approved the resulting corpus records.

## 6. Start the self-hosted model service

The orchestrator uses a vLLM-compatible API, not Ollama. Start vLLM on the GPU host so it exposes `http://localhost:8000/health` and `POST /v1/completions`. Set the exact served model ID in `.env`:

```text
SELF_HOSTED_MODEL=meta-llama/Llama-3.1-8B-Instruct
```

Do not switch to OpenAI or Anthropic as a convenience; that violates the product’s default data-residency constraint.

## 7. Start the complete local application

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Open `http://localhost:8080`. The gateway is `http://localhost:8000`; the orchestrator is `http://localhost:8001`.

## 8. Verify before a demo

In a second PowerShell window:

```powershell
Invoke-RestMethod http://localhost:8000/health/readiness
Invoke-RestMethod http://localhost:8000/health/detailed
Invoke-RestMethod http://localhost:8001/health
npm run build --prefix client
```

Then ask a direct India question, such as “Can a classical Ayurvedic formulation be patented in India?” Verify citations are displayed. Check that an audit event was written:

```powershell
docker exec ip-sakti-postgres psql -U <your-postgres-user> -d <your-database-name> -c "SELECT timestamp, corpus_version, provider_used, citation_count FROM audit_trail ORDER BY timestamp DESC LIMIT 5;"
```

## 9. If you see “research service is unavailable”

The UI now displays a safe backend reason. Use this order:

1. `docker compose ps` — all stores, API gateway and orchestrator must be running.
2. `Invoke-RestMethod http://localhost:8000/health/detailed` — database must say `healthy`.
3. `Invoke-RestMethod http://localhost:8001/health` — retrieval and model components must not be `unhealthy`.
4. `docker compose logs api-gateway --tail 100` and `docker compose logs orchestrator --tail 100` — use the first error, not the last symptom.
5. Confirm the migration in step 4 and vLLM in step 5.

## 10. Production rollout checklist

- Build versioned images in CI and deploy only signed, vulnerability-scanned images.
- Create the required Kubernetes Secrets outside Git. `secrets.example.yaml` is a template only and must never be applied.
- Run `deployment/kubernetes/db-migration-job.yaml` once for each release before rolling out the API gateway.
- Deploy Keycloak and replace development authentication with JWKS validation before allowing users.
- Deploy vLLM on approved in-country GPU infrastructure; do not route sensitive queries externally.
- Configure TLS, an ingress allow-list/CORS allow-list, network policies, backups, alerting, and quarterly restore drills.
- Run security, corpus/citation regression, load, and disaster-recovery tests as release gates.
- Confirm all corpus additions have the required human-review state before treating them as authoritative.

## 11. Important current limits

Comparative answers, ABS automation, TKDL lookup, Bhashini multilingual delivery, and human escalation directory routing still require their dedicated product modules. Do not present them as enabled until their source-cited, audited flows are implemented and tested.
