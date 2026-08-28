# ARCHITECTURE.md — IP-SAKTI Sahayak

**SIH 2026 | PS 26045 | Ministry of AYUSH — AIIA**
Multilingual, RAG-based, source-cited AI assistant for Ayurveda IPR & regulatory guidance.
Production build. See `AGENTS.md` for non-negotiable constraints derived from this document, and `DECISIONS.md` for the reasoning behind each choice.

---

## 1. Design Principles

1. No answer without a citable source — every claim traces to a stored source ID; low confidence → abstain.
2. Jurisdiction (India vs International) is never blended — hard-partitioned at the index level.
3. Classification before advice — IP posture depends on drug category; the classifier is a gate.
4. Information, not legal advice — enforced server-side, not just displayed.
5. Staged build: MVP (RAG + citations) → Knowledge Graph + Agentic reasoning → Paid-source connectors → Full multilingual/voice.
6. Privacy/audit by construction — DPDP-aligned, consent-logged, no silent retention.
7. Data sovereignty by default — self-hosted models, GoI-empanelled cloud, external providers opt-in only.

---

## 2. High-Level Architecture

```
CLIENT LAYER (React PWA, Bhashini language switch, voice Phase 4)
        │
API GATEWAY / BFF (FastAPI — auth, rate limit, consent capture, logging)
        │
ORCHESTRATION LAYER (Agentic Controller — LangGraph state machine)
   ├── Formulation Classifier (deterministic decision tree + LLM slot-filling)
   ├── RAG Retrieval Engine (per-jurisdiction hybrid dense+sparse)
   ├── Knowledge Graph Reasoner (Phase 2)
   ├── ABS / TKDL Prior-Art Pointer
   ├── Citation & Confidence Engine
   └── Human Escalation Router
        │
DATA / KNOWLEDGE LAYER
   Qdrant (vectors, per-jurisdiction namespaces) · Elasticsearch (sparse) ·
   PostgreSQL (sessions/consent/audit/roles/escalation/review log) ·
   MinIO (versioned document store) · Neo4j (Phase 2 KG)
        │
INGESTION / CORPUS PIPELINE (offline, scheduled)
   Source connectors → parse/OCR → structural chunk → embed → rerank →
   dual-store transaction → version-diff → human review → publish
```

---

## 3. Core Functional Modules

### 3.1 Formulation Classifier
Deterministic decision tree; LLM does slot-filling only, never the classification judgment itself. Categories: classical/generic, patent-or-proprietary, new/non-classical drug, phytopharmaceutical, Ayurveda-Aahar/nutraceutical, cosmetic. Output (`formulation_class`) scopes every downstream module's answer. Protected by the input-guard layer (§3.9) against adversarial manipulation toward a favorable-but-wrong category.

### 3.2 Jurisdiction Toggle
Session parameter (`India` | `International` | `Comparative`, opt-in). Enforced at three points: UI selector, retrieval-layer index namespace (`in_*` vs `intl_*`), and prompt assembly (no cross-jurisdiction inference without explicit comparative request).

### 3.3 RAG Retrieval Engine
Hybrid dense + sparse retrieval + cross-encoder reranker. Per-jurisdiction, per-domain indices (Patents, GI, Trademarks, Designs, Copyright, Plant Variety, BDA/ABS, Drugs & Cosmetics, Advertising, FSSAI // TRIPS, CBD/Nagoya, WIPO GRATK, PCT, Madrid, Hague, Budapest, export-market herbal regimes). Retrieval-then-generate with mandatory span-level citation. Confidence indicator from retrieval-score distribution + reranker margin + source-count agreement; below threshold → safe abstention.

**Embedding model:** `BAAI/bge-large-en-v1.5` or `intfloat/e5-large-v2` (self-hosted MVP baseline) → Phase 1.5 contrastive fine-tuning on the corpus using (question, cited-section) pairs from the eval set. **Reranker:** `BAAI/bge-reranker-large`, self-hosted. No change to either ships without passing `tests/eval/embedding_regression_gate.py`.

### 3.4 Knowledge Graph Reasoner (Phase 2)
Neo4j graph: `Formulation ↔ IngredientTaxon ↔ TKDL Record ↔ Statute/Section ↔ CaseLaw ↔ Registry Record ↔ Jurisdiction`. Every node/edge carries the source chunk's `version_hash`; superseded edges are marked `superseded_at: <version>`, never deleted (preserves historical answer-reconstruction). Default queries see `current` edges only.

### 3.5 Agentic Orchestrator (Phase 2)
LangGraph deterministic state machine (fixed tool set, not open-ended agent autonomy): classify → retrieve (per jurisdiction) → cross-check KG → check ABS applicability → assemble citations → confidence-score → decide abstain/answer/escalate.

### 3.6 ABS-Compliance Helper & TKDL/Prior-Art Pointer
Flags Biological Diversity Act ABS obligations from ingredient list + classification. Points to TKDL codes/prior-art as search starting points — never a legal prior-art opinion.

### 3.7 Citation & Confidence Engine
Post-processes every answer: maps claims to source spans, computes a per-answer confidence badge, rejects/regenerates unmapped sentences (anti-hallucination gate).

### 3.8 Human Escalation Router
Triggers: low confidence, explicit request, detected legal-advice-seeking phrasing, out-of-scope query. Routes to empanelled AYUSH IP facilitator directory (PostgreSQL) — metadata only.

### 3.9 Adversarial Input Defense
Pre-processes all user input before it reaches classifier/retrieval prompts: strips/flags instruction-like injection patterns, enforces strict separation between user text and system instructions in prompt templates, applies length/character sanity limits. The deterministic decision tree (§3.1) is the ultimate safeguard — injected text can influence slot extraction at worst, never the classification rule itself. Rate-limiting + pattern detection guard against systematic corpus-extraction attempts.

### 3.10 Multilingual Layer
Bhashini ASR/NMT/TTS at the client-BFF boundary. Pivot-language approach: retrieval/generation in English against the English-annotated corpus, translation at the edges.

### 3.11 Paid-Source Connector Layer (Phase 3)
Adapter pattern per provider (Manupatra, SCC Online, WIPO Lex Plus-tier). Every call requires explicit, logged, per-session consent — never invoked silently.

---

## 4. Data Architecture

### 4.1 Corpus Ingestion Pipeline
```
Source connectors (TKDL, India Code, IP India/InPASS, GI Registry, NBA/ABS,
WIPO Lex, PCT/Madrid/Hague, FSSAI, case-law feeds)
  → Parse/OCR
  → Structural segmentation (section/article/clause-level — never fixed-window)
  → Embed (self-hosted) → Rerank
  → Dual-store transaction (Qdrant + Elasticsearch, atomic, rollback on partial failure)
  → Version-diff (hash-based; flag amendments)
  → Human-in-the-loop legal review queue (mandatory before publish)
  → Publish (versioned, immutable snapshots)
```

### 4.2 Storage

| Store | Role | Backup | Retention |
|---|---|---|---|
| Qdrant | Vector search, per-jurisdiction namespaces | Daily snapshot | 90d rolling + permanent per corpus version |
| Elasticsearch | Sparse/BM25 search | Daily snapshot | 90d rolling |
| MinIO | Versioned immutable document store | Cross-zone replication | Indefinite |
| PostgreSQL | Sessions, consent, audit, roles, escalation directory, corpus review log | WAL + nightly `pg_dump` | 7 years |
| Neo4j (Phase 2) | Knowledge graph | Daily native backup | 90 days |

DR target: second availability zone within the same GoI-empanelled cloud (MeghRaj/NIC). Cross-cloud DR is prohibited (violates data residency). Quarterly restore drills on all stores.

### 4.3 Initial MVP Corpus
Patents Act 1970 (+ amendments), Biological Diversity Act 2002, TKDL classification docs, GI Registry public data, Drugs & Cosmetics Act (relevant sections).

---

## 5. Tech Stack

| Layer | Choice |
|---|---|
| Client | React + Vite PWA, TypeScript |
| API Gateway | FastAPI |
| Orchestrator | Python + LangGraph |
| Vector store | Qdrant (self-hosted) |
| Sparse retrieval | Elasticsearch/OpenSearch (self-hosted) |
| Document store | MinIO (self-hosted) |
| Relational store | PostgreSQL (self-hosted) |
| Knowledge Graph | Neo4j (self-hosted, Phase 2) |
| LLM (default) | Self-hosted open-weight (Llama 3.1 8B / Mistral-NeMo 12B via vLLM), scalable to 70B if justified |
| LLM (opt-in) | OpenAI GPT-4o / Anthropic — via provider abstraction, explicit consent only |
| Embeddings | BGE-large-en-v1.5 / E5-large-v2 (self-hosted) → fine-tuned Phase 1.5 |
| Reranker | BGE-reranker-large (self-hosted) |
| Auth | Keycloak (self-hosted OAuth2/OIDC) |
| Multilingual | Bhashini APIs |
| Observability | OpenTelemetry + Prometheus + Grafana + Jaeger |
| Infra | Kubernetes on GoI-empanelled cloud (MeghRaj/NIC) |

---

## 6. Security, Privacy & Compliance

- DPDP-aligned consent capture, purpose limitation, data minimization, right-to-erasure.
- Paid-source access: per-call consent + audit log.
- Full answer-provenance audit trail (corpus version, chunk IDs, model version) — 7-year retention.
- Adversarial input defense (§3.9) against prompt injection and corpus-extraction attempts.
- Guardrails: hard stop before any flow crosses from "information" into drafting legal opinions/filings — terminates at registry link + human-facilitator handoff.
- Standing disclaimer enforced server-side as a non-strippable response wrapper.
- Data sovereignty: no user data leaves GoI cloud without explicit per-session consent.

---

## 7. Observability — Alert Thresholds

| Signal | Threshold | Action |
|---|---|---|
| Citation-rejection rate | >15%/1hr rolling | Page on-call |
| Retrieval latency p95 | >2s | Alert |
| End-to-end latency p95 | >3s | Alert (SLA breach) |
| Confidence-score median | drops >20% WoW | Alert eval team |
| Escalation trigger rate | >2x rolling baseline | Alert |
| Dual-store consistency failure | any | Page on-call |
| External-provider usage rate | >5% of sessions | Review |

---

## 8. Evaluation Framework

| Metric | Method |
|---|---|
| Answer accuracy | Legal-expert-graded test set per domain × jurisdiction |
| Citation correctness | Automated span-verification + spot-audit |
| Safe abstention | Adversarial/out-of-scope test set |
| Multilingual quality | Back-translation consistency + native-speaker review |
| Jurisdiction-separation integrity | Regression suite, no cross-contamination absent explicit comparative request |
| Embedding/reranker regression | `tests/eval/embedding_regression_gate.py` — CI-blocking |

---

## 9. Corpus Review Governance

AIIA-designated AYUSH-IP reviewer(s), 1–2 people at MVP scope. SLA: 5 business days routine, 24–48hr expedited for high-visibility amendments. Unreviewed content is queryable but marked `pending_review` and treated as lower-confidence, never fully authoritative until sign-off. Review record in PostgreSQL `corpus_review_log`. **Reviewer staffing and SLA pending AIIA confirmation** — not an engineering decision.

---

## 10. Staged Build Plan

**Phase 1 — MVP:** Classifier + jurisdiction toggle + hybrid RAG (BGE/E5 + reranker) + citations + confidence + input guard + Postgres (sessions/consent/audit) + backup/DR + observability + corpus review governance. English-only, no KG, no agentic planning, no paid sources.

**Phase 2 — Reasoning depth:** Knowledge Graph (version-aware) + agentic orchestration + ABS-compliance helper + TKDL pointer + human escalation.

**Phase 3 — Paid-source connectors:** consented, audited subscription-database access.

**Phase 4 — Full multilingual + voice:** Bhashini ASR/TTS, mobile-first low-bandwidth experience.

Full implementation-order-by-week breakdown: see `PROGRESS.md`.

---

## 11. Key Architectural Risks

| Risk | Mitigation |
|---|---|
| Hallucinated citations | Citation Engine rejects unmapped sentences |
| Jurisdiction bleed | Namespace-level index separation |
| Stale law after amendment | Version-diff + mandatory review queue |
| Classical-formulation misclassification | Deterministic decision tree, human-review flag on ambiguous cases |
| Prompt injection | Input-guard layer + decision-tree safeguard |
| Embedding precision | BGE/E5 + reranker baseline + regression-gated fine-tuning |
| Dual-store desync | Transactional writes + consistency alerting |
| Backup/DR failure | Quarterly restore drills, 7-year audit retention |
| Trade-secret exposure | Self-hosted-by-default processing, consent-gated external calls |
