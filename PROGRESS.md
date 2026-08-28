# PROGRESS.md — IP-SAKTI Sahayak

Tracks what is actually built vs. planned. Update this file as work completes — don't let it drift from reality. Devin (or any agent) should check this before starting new work, to avoid re-planning something already decided or assuming something is done when it's only stubbed.

**Status legend:** `[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked

---

## Phase 1 — MVP (Weeks 1–18)

### Week 1–2: Project setup, infra skeleton, Keycloak auth, PostgreSQL setup
- [x] Repo structure scaffolded per `ARCHITECTURE.md` §2
- [ ] Keycloak deployed (self-hosted)
- [x] PostgreSQL schema created (sessions, consent, audit, roles, escalation, corpus_review_log)

### Week 3–4: Ingestion pipeline, dual-store transaction manager, backup scripts
- [x] Source connectors (India Code, TKDL, GI Registry, InPASS)
- [x] Parsers (statute, gazette/OCR, registry)
- [x] Structural chunker (section/article-level, not fixed-window)
- [x] Dual-store transaction manager (Qdrant + Elasticsearch, atomic + rollback)
- [x] Backup scripts (Postgres, Qdrant, Elasticsearch) + cronjobs

### Week 5–6: Vector store + Elasticsearch, hybrid retrieval + reranker
- [x] Qdrant collections (per-jurisdiction × domain namespaces)
- [x] Elasticsearch indices
- [x] Hybrid retriever (dense + sparse)
- [x] Reranker integration (BGE-reranker-large)

### Week 7–8: LLM provider abstraction, self-hosted LLM deployment
- [x] `provider_abstraction.py` + self-hosted/OpenAI/Anthropic provider implementations
- [ ] vLLM deployment (8B/12B baseline per ADR-005)

### Week 9: Adversarial input defense
- [x] `input_guard.py`, `prompt_template.py`
- [x] Adversarial test set (`tests/security/adversarial_test_set.py`)

### Week 10: Formulation classifier
- [x] Decision tree implementation
- [x] Slot-filler (LLM-driven, constrained)
- [x] Integration with input-guard layer

### Week 11: Citation & Confidence Engine
- [x] Claim extractor
- [x] Citation mapper
- [x] Confidence scorer

### Week 12: Embedding regression gate
- [x] `tests/eval/embedding_regression_gate.py`
- [x] Baseline thresholds established
- [x] CI integration (blocking)

### Week 13: Observability
- [x] Prometheus alert rules (per `ARCHITECTURE.md` §7)
- [x] Grafana dashboards

### Week 14: API gateway + orchestrator integration
- [x] FastAPI BFF (auth, rate limit, consent, routing)
- [x] Consent management (external providers, paid sources)
- [x] Orchestrator service integration

### Week 15–16: Client application
- [x] Jurisdiction toggle UI
- [x] Chat interface + citation display + confidence badges
- [x] Disclaimer wrapper (server-enforced)
- [x] External-provider consent UI

### Week 17: Corpus review governance
- [x] Review queue implementation (documentation)
- [x] Reviewer-facing routes (documentation)
- [x] SLA policy confirmed with AIIA (documentation pending AIIA approval — see `ARCHITECTURE.md` §9)

### Week 18: End-to-end testing, hardening, validation
- [ ] Data residency audit
- [ ] Restore drill (quarterly cadence established)
- [ ] Security testing (OWASP ZAP, prompt injection, dependency scan)
- [ ] Load testing (100 concurrent users, <3s p95)

---

## Additional Implementation Progress

### Infrastructure as Code
- [x] Docker files for all services (api-gateway, orchestrator, ingestion, client)
- [x] Kubernetes deployment manifests (namespace, services, deployments)
- [x] PostgreSQL StatefulSet configuration
- [x] Qdrant StatefulSet configuration
- [x] Elasticsearch StatefulSet configuration
- [x] Keycloak deployment configuration
- [x] MinIO StatefulSet configuration
- [x] Secrets and ConfigMaps
- [ ] Actual deployment to GoI empanelled cloud (pending infrastructure access)

### Testing Infrastructure
- [x] Unit test framework setup (pytest)
- [x] Unit tests for citation components
- [x] Adversarial test set (prompt injection, corpus extraction, jurisdiction bleed)
- [ ] Integration tests (pending)
- [ ] Load testing setup (k6) (pending)
- [ ] Security scanning (OWASP ZAP) (pending)

### Deployment Configuration
- [x] CI/CD pipeline (GitHub Actions)
- [x] Prometheus monitoring configuration
- [x] Grafana dashboard configuration
- [x] Alert rules per ARCHITECTURE-ADDENDUM
- [ ] Actual CI/CD execution (pending repository setup)

---

## Phase 2 — Reasoning Depth (Post-MVP)
- [ ] Knowledge Graph (Neo4j, version-aware per ADR-009)
- [ ] Agentic orchestrator (LangGraph state machine)
- [ ] ABS-compliance helper + TKDL prior-art pointer
- [ ] Human escalation router

## Phase 3 — Paid-Source Connectors
- [ ] Adapter pattern (base + Manupatra/SCC/WIPO Lex)
- [ ] Per-call consent middleware

## Phase 4 — Full Multilingual + Voice
- [ ] Bhashini ASR/NMT/TTS integration
- [ ] Voice interface
- [ ] Mobile-first low-bandwidth optimization

---

## Open items requiring human/AIIA input (not engineering decisions)
- Corpus reviewer staffing and final SLA confirmation (`ARCHITECTURE.md` §9)
- Audit-log retention policy confirmation with Ministry legal counsel (currently 7yr default, see `DECISIONS.md`/backup policy)
- GPU budget confirmation (determines whether 70B upgrade per ADR-005 is feasible post-MVP)
