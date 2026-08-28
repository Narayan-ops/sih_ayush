# DECISIONS.md — IP-SAKTI Sahayak

Architecture Decision Log. Each entry: what was decided, what alternatives were considered, why they were rejected. **New architectural decisions get appended here, not made silently in code.** If a future change would reverse or weaken one of these, that's a new decision requiring the same treatment — not a routine code change.

---

### ADR-001: Self-hosted LLM/embeddings as default, external providers opt-in
**Decision:** Default LLM (Llama 3.1 8B/12B via vLLM) and embeddings (BGE-large/E5-large) are self-hosted in-cluster on GoI-empanelled cloud. OpenAI/Anthropic available only as explicit, consented, opt-in alternative via a provider-abstraction layer.
**Alternatives considered:** Default to OpenAI GPT-4o + `text-embedding-3-large` (higher out-of-box quality, faster to stand up).
**Why rejected:** Users describe unpatented/undisclosed formulation ingredients during classification — IP-sensitive, trade-secret-adjacent data. Routing this through a US-hosted third-party API by default on a government IP-protection tool directly contradicts the data-sovereignty requirement and would likely fail review. Provider abstraction layer keeps this reversible without a rewrite if self-hosted quality proves insufficient.
**Status:** Locked. Revisiting requires a new ADR, not a code change.

### ADR-002: Formulation classifier is a deterministic decision tree, not free-form LLM judgment
**Decision:** Classification logic lives in code (decision tree); LLM only performs natural-language slot-filling to answer the tree's fixed questions.
**Alternatives considered:** Let the LLM directly infer/output the formulation category from the user's description.
**Why rejected:** Classical vs. proprietary vs. new-drug classification has real IP consequences (e.g., Section 3(p) patentability bar). A free-form LLM judgment is neither auditable nor reproducible, and is more exposed to prompt-injection manipulation toward a favorable-but-wrong category. A deterministic tree keeps the classification testable and stable.
**Status:** Locked.

### ADR-003: Jurisdiction separation enforced at vector-index namespace level
**Decision:** India (`in_*`) and International (`intl_*`) content lives in separate index namespaces, not a shared index filtered by metadata.
**Alternatives considered:** Single shared index with a jurisdiction metadata filter applied at query time.
**Why rejected:** A prompt-level or filter-level separation is the kind of thing that quietly breaks under retrieval-ranking edge cases or future refactors. Namespace-level separation makes cross-jurisdiction leakage structurally harder, not just discouraged.
**Status:** Locked.

### ADR-004: Embedding model — BGE-large/E5-large baseline, not MiniLM, not OpenAI embeddings
**Decision:** MVP baseline is `BAAI/bge-large-en-v1.5` or `intfloat/e5-large-v2`, self-hosted, with Phase 1.5 contrastive fine-tuning on the corpus.
**Alternatives considered:** `all-MiniLM-L6-v2` (cheap, fast, originally proposed by Devin); OpenAI `text-embedding-3-large` (strong quality, but external/non-sovereign, conflicts with ADR-001).
**Why rejected (MiniLM):** General-purpose 384-dim embeddings don't reliably separate fine-grained legal distinctions (e.g., Section 3(p) vs 3(d)) — exactly the precision this product depends on for citation-grade retrieval.
**Status:** Locked for MVP baseline. Fine-tuning is Phase 1.5, gated by the regression-eval requirement in ADR-006.

### ADR-005: GPU sizing — start at 8B/12B, not 70B, by default
**Decision:** Default self-hosted LLM is Llama 3.1 8B or Mistral-NeMo 12B on a single A100-40GB/A10G-class GPU. 70B (multi-GPU tensor parallelism) is provisioned only if MVP evaluation shows the smaller model's quality is the binding constraint.
**Alternatives considered:** Default straight to 70B for maximum quality.
**Why rejected:** "GPU nodes if available" was not an actual capacity plan. A government pilot's GPU budget is a real constraint, not a detail to defer. RAG grounding partially offsets the smaller model's weaker parametric recall (the model's job is closer to "extract and rephrase retrieved text" than "recall facts"). The provider-abstraction layer (ADR-001) makes this a config change later, not a rewrite — so starting small and measuring is lower-risk than over-provisioning speculatively.
**Status:** Locked for MVP. Upgrade decision requires MVP eval data, not assumption.

### ADR-006: CI-enforced embedding/reranker regression gate
**Decision:** No change to the embedding model, fine-tuning, or reranker ships without passing `tests/eval/embedding_regression_gate.py` in CI — measuring citation-correctness rate, retrieval precision@k, and near-miss retrieval rate against a locked baseline.
**Alternatives considered:** Treat re-evaluation as documented policy/manual step rather than a CI-blocking gate.
**Why rejected:** A policy that isn't enforced by CI is a policy an agent (or a human under deadline pressure) will eventually skip. Near-miss retrieval — a wrong-but-adjacent statute section — is the single highest-stakes failure mode for a legal citation tool, so it's the one metric that must never regress silently.
**Status:** Locked. Emergency override exists but is itself audited — not a routine bypass path.

### ADR-007: Auth via Keycloak (self-hosted), not Auth0 or other SaaS IdP
**Decision:** OAuth2/OIDC via self-hosted Keycloak.
**Alternatives considered:** Auth0 (originally proposed by Devin — faster to integrate, managed).
**Why rejected:** Same data-sovereignty logic as ADR-001 — a government-facing tool's auth layer (which touches user identity/role data) shouldn't depend on a third-party SaaS IdP by default.
**Status:** Locked.

### ADR-008: Dual-store (Qdrant + Elasticsearch) writes are transactional, with consistency alerting
**Decision:** All ingestion writes to Qdrant and Elasticsearch go through an atomic transaction manager with rollback on partial failure; any detected inconsistency triggers a page, not a background log entry.
**Alternatives considered:** Best-effort writes to both stores independently, reconciled periodically.
**Why rejected:** A partial write (embedded-but-not-indexed, or vice versa) directly threatens the "every answer traceable to a source" guarantee that's the product's core promise. This isn't a performance nice-to-have; it's correctness-critical.
**Status:** Locked.

### ADR-009: KG versioning mirrors corpus versioning (Phase 2)
**Decision:** Every Knowledge Graph node/edge carries the source chunk's `version_hash`; superseded edges are marked `superseded_at`, never deleted.
**Alternatives considered:** Re-derive the KG fresh on each corpus publish, discarding old edges.
**Why rejected:** If law amends and old KG edges are simply deleted, a previously-given answer that cited the old edge becomes unreconstructable — breaking the audit-trail guarantee (ADR/§9 of ARCHITECTURE.md) for anything KG-derived.
**Status:** Locked, applies from Phase 2 onward.

### ADR-010: 18-week MVP timeline is production-track, not hackathon-demo-track
**Decision:** Confirmed 2026-08-28 — this is a full production build for AIIA/Ministry of AYUSH, not a hackathon-window deliverable. No separate "thin demo" slice was cut.
**Context:** Raised as an open question during planning; resolved directly by the project owner.
**Status:** Locked. If a demo need re-emerges, it requires a new ADR defining what subset ships early and what corners (if any) are acceptable to cut for a demo-only build — not a silent scope change to the production plan.
