# IP-SAKTI Sahayak — Architecture Addendum
**Covers gaps identified in implementation-plan review: embedding model selection, input security, backup/DR, KG versioning, observability thresholds, and corpus review governance.**

---

## A1. Embedding Model Selection (replaces `all-MiniLM-L6-v2`)

**Problem:** General-purpose sentence embeddings don't reliably separate fine-grained legal distinctions (e.g. Section 3(p) vs 3(d) patentability exclusions) that this product's accuracy depends on.

**Decision:** Two-stage approach.

1. **MVP baseline:** `BAAI/bge-large-en-v1.5` or `intfloat/e5-large-v2` — both self-hostable, both meaningfully stronger than MiniLM on retrieval benchmarks, both handle longer legal-text chunks better (up to ~512 tokens natively).
2. **Phase 1.5 upgrade:** Fine-tune the chosen base model on the ingested corpus using contrastive learning — positive pairs built from (question, cited-section) pairs harvested from the legal-expert-graded evaluation set (§7 of the main architecture doc). This is the single highest-leverage quality investment available, because it directly targets the failure mode ("near-miss" statute retrieval) most likely to produce a wrong-but-plausible citation.

**Reranker:** Add a cross-encoder reranker (`BAAI/bge-reranker-large` or similar, self-hostable) on top of retrieval — bi-encoder embeddings alone are not precise enough for legal citation-grade retrieval; the reranker is what actually enforces precision at the top-k cutoff.

**Evaluation gate:** No embedding model change ships to production without re-running the citation-correctness eval set (§7) and confirming no regression.

---

## A2. Adversarial Input Defense

**Threat model:**
- User pastes adversarial/malformed text (prompt injection) into the formulation classifier or chat, attempting to manipulate classification toward a favorable-but-incorrect category (e.g. steering "new drug" → "classical" to dodge clinical-evidence requirements).
- User pastes text copied from a scanned document/OCR output containing hidden instructions.
- User attempts to extract system prompt / corpus contents verbatim (IP leakage from the corpus itself).

**Design:**
- `orchestrator/src/security/input_guard.py` — pre-processes all user input before it reaches the classifier or retrieval prompt:
  - Strip/flag instruction-like patterns ("ignore previous instructions", role-play framing, etc.)
  - Enforce a strict separation between "user-supplied formulation description" and "system instructions" in the prompt template (never string-concatenate raw user text into an instruction-bearing prompt region)
  - Length and character-set sanity limits on classifier input
- **Classification integrity check:** the deterministic decision tree (§3.1 of the main doc) is the actual safeguard here — because classification logic lives in code, not an LLM's free judgment, injected text can influence *slot extraction* at worst, not the classification rule itself. This should be explicitly tested: adversarial test set feeding manipulated input through slot-filling and asserting the decision tree output is unaffected by injected instructions.
- **Corpus extraction defense:** rate-limit + pattern-detect attempts to systematically enumerate corpus contents verbatim via repeated near-identical queries; citation engine already limits verbatim reproduction to cited spans, which caps single-query leakage.

---

## A3. Backup & Disaster Recovery

| Store | Backup method | Frequency | Retention | Restore-test cadence |
|---|---|---|---|---|
| PostgreSQL (sessions, consent, audit, escalation) | WAL archiving + nightly `pg_dump` snapshot | Continuous WAL + daily snapshot | 7 years (audit/legal traceability requirement — matches DPDP + potential dispute timelines) | Quarterly restore drill |
| Qdrant (vectors) | Snapshot API to object storage | Daily | 90 days rolling + permanent snapshot at each corpus version publish | Quarterly |
| Elasticsearch | Snapshot to object storage (repository-s3/minio) | Daily | 90 days rolling | Quarterly |
| MinIO (document store) | Cross-zone replication (if multi-zone available) + versioned bucket | Continuous (replication) | Indefinite (immutable corpus — this *is* the source of truth) | N/A (replication, not restore) |
| Neo4j (Phase 2) | Native backup/dump | Daily | 90 days | Quarterly |

**Audit trail is the highest-priority store** — it's the thing that makes any answer legally reconstructible after the fact. Its retention policy should be treated as a compliance requirement, not an ops default, and confirmed with AIIA/Ministry legal counsel rather than assumed.

**DR failover:** given the GoI-cloud residency constraint, DR target is a second availability zone within the same empanelled cloud (MeghRaj/NIC), not a cross-provider failover — cross-cloud DR would itself violate the residency principle.

---

## A4. GPU Sizing for Self-Hosted LLM

**Problem:** "GPU nodes if available" is not a plan.

**Decision, staged by budget reality:**
- **If GPU budget is constrained (likely for a hackathon-origin government pilot):** default to a 7B–13B class open-weight model (e.g. Llama 3.1 8B or Mistral-NeMo 12B, both vLLM-compatible) — single A100-40GB or even A10G-class GPU sufficient for MVP concurrency (target: 100 concurrent users, §Success Criteria). Accuracy gap versus 70B is real but partially offset by the RAG grounding (the model's job is closer to "extract and rephrase retrieved text" than "recall facts from parameters").
- **If GPU budget allows:** Llama 3.1 70B via vLLM with tensor parallelism across 2–4 A100-80GB, only justified once MVP eval shows the smaller model's classification/generation quality is the binding constraint (test this — don't assume it).
- **Either way:** the LLM provider abstraction layer already built into the plan makes this a config change, not an architecture change — so it's fine to start small and measure before over-provisioning GPUs the pilot may not get funded for.

---

## A5. Knowledge Graph Versioning (Phase 2)

**Problem:** Document corpus has version-diffing; KG entities/edges have no equivalent, so an amended statute could leave stale graph edges pointing at superseded law.

**Design:**
- Every KG node/edge derived from a corpus document carries the same `version_hash` as its source chunk (from §4.1 of the main architecture doc).
- On corpus re-publish with a diff, the entity-extraction step re-runs *only* on changed chunks, and old edges sourced from the superseded version are marked `superseded_at: <version>` rather than deleted outright (preserves historical answer-reconstruction — if an old answer cited an old edge, that edge must still be inspectable).
- KG queries by default filter to `current` edges only; historical/audit queries can traverse superseded edges explicitly.

---

## A6. Observability: Alert Thresholds

Tools (OpenTelemetry + Jaeger/Prometheus) were already specified; this defines what triggers action.

| Signal | Threshold | Action |
|---|---|---|
| Citation-rejection rate (Citation Engine rejecting generated sentences) | >15% of responses in a rolling 1hr window | Page on-call — likely a retrieval or corpus quality regression |
| Retrieval latency (p95) | >2s | Alert — approaching the 3s total-response SLA |
| End-to-end response latency (p95) | >3s | Alert (SLA breach) |
| Confidence-score distribution | Median confidence drops >20% week-over-week | Alert to eval team — possible corpus staleness or retrieval degradation, not necessarily urgent |
| Escalation-router trigger rate | Sudden spike (>2x rolling baseline) | Alert — could indicate a corpus gap or a new class of query the system can't handle |
| Dual-store (Qdrant/Elasticsearch) consistency check failures | Any failure | Page on-call — direct threat to citation traceability guarantee |
| External-provider (opt-in LLM) usage rate | >5% of sessions | Review — should stay rare given self-hosted default; a spike suggests self-hosted quality issues driving user opt-in |

---

## A7. Corpus & Legal Review Governance

**Problem:** Human-in-the-loop review queue exists architecturally but has no defined reviewers or SLA — without this, "keep corpus current" is aspirational.

**Proposed structure** (to be confirmed with AIIA, not something engineering can decide unilaterally):
- **Reviewer pool:** AIIA-designated AYUSH-IP subject matter expert(s), ideally with legal-drafting familiarity — likely 1–2 people for MVP scope, not a full legal team.
- **Review SLA:** target 5 business days from ingestion-pipeline flag to review completion for routine amendments; expedited 24–48hr path for high-visibility changes (e.g. a Patents Rules amendment).
- **Escalation on missed SLA:** flagged (not amended) chunks remain queryable but are marked `pending_review` in the confidence calculation — the Citation & Confidence Engine should treat unreviewed-but-ingested content as lower-confidence by default until sign-off, rather than either blocking it entirely or treating it as fully authoritative.
- **Review record:** stored in PostgreSQL (`corpus_review_log` table: chunk_id, version_hash, reviewer_id, decision, timestamp, notes) — itself part of the audit trail.

---

## Summary of New Artifacts Introduced by This Addendum

- `orchestrator/src/security/input_guard.py`
- Reranker service/config (bge-reranker-large or equivalent)
- Embedding fine-tuning pipeline (Phase 1.5, post-MVP-baseline)
- Backup/snapshot jobs per store (§A3) + quarterly restore-drill runbook
- GPU sizing decision recorded in `deployment/kubernetes/vllm-deployment.yaml` config (explicit node pool, not "if available")
- KG `version_hash` + `superseded_at` fields on all nodes/edges (Phase 2)
- Prometheus alert rules matching §A6 thresholds
- `corpus_review_log` table (PostgreSQL) + reviewer SLA policy (pending AIIA confirmation)
