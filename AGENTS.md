# AGENTS.md — IP-SAKTI Sahayak

**Read this file at the start of every session before making any change.**
This is not a summary of the architecture — it's the list of constraints that must never be silently weakened, reinterpreted, or "simplified" while implementing or modifying this system. If a task seems to require violating one of these, STOP and flag it to the human rather than proceeding with a workaround.

Full references: `ARCHITECTURE.md` (system design), `DECISIONS.md` (why each choice was made, with alternatives considered).

---

## Non-negotiable constraints

1. **No answer without a citable source.** Every generated sentence must map to a retrieved chunk with a `source_id`, `section/article`, `version_hash`. The Citation & Confidence Engine rejects unmapped sentences — this gate must never be bypassed, weakened, or made "best-effort" to hit a deadline or simplify a demo.

2. **Jurisdiction separation is structural, not cosmetic.** India and International answers are served from separate vector-index namespaces (`in_*` / `intl_*`). Never merge them into a shared index "for simplicity," and never rely on prompt instructions alone to keep them apart — the separation must exist in the retrieval layer itself. Comparative mode is explicit opt-in only, rendered as two clearly labeled columns, never a blended answer.

3. **Formulation classification is a deterministic decision tree.** The LLM's only role is natural-language slot-filling (extracting answers to fixed questions). The classification *logic* itself must never become free-form LLM judgment — this is what keeps classification auditable and resistant to prompt injection. Do not "improve" this by letting the LLM infer the category directly.

4. **No user data leaves GoI cloud infrastructure by default.** Self-hosted LLM and embedding models are the default path for all formulation/query processing. External providers (OpenAI, Anthropic, etc.) are opt-in only, per-session, with an explicit logged consent event — never invoked silently, never made the default even for speed or quality reasons, without a human decision to change that default (which would need a new entry in `DECISIONS.md`).

5. **"Information, not legal advice" is enforced server-side.** The disclaimer is a non-strippable response wrapper, not just UI copy. Any flow that starts producing something closer to "here is your completed filing" or a drafted legal opinion is out of scope — those flows terminate at a registry link + human-facilitator handoff.

6. **Dual-store writes (Qdrant + Elasticsearch) are transactional.** Never write to one store without the other succeeding too. Any inconsistency is a page-worthy alert, not a background issue (see `deployment/monitoring/prometheus-alerts.yaml`).

7. **No embedding model or reranker change ships without passing the regression gate.** `tests/eval/embedding_regression_gate.py` must pass in CI before any change to the embedding/reranking pipeline is merged. The override flag exists for emergencies only and is itself audited — using it is not a way to skip the gate under normal circumstances.

8. **Corpus changes go through human review before being treated as authoritative.** New/amended statutory content is queryable but marked `pending_review` and treated as lower-confidence until an AIIA-designated reviewer signs off (see `docs/governance/corpus_review_policy.md`). Never auto-publish scraped legal text as fully authoritative.

9. **Audit trail is immutable and complete.** Every response logs corpus version, retrieved chunk IDs, model version, and provider used, in PostgreSQL, with 7-year retention. Never skip audit logging for performance reasons — this is a compliance requirement, not an optimization target.

10. **Data residency is architectural, not aspirational.** All default infrastructure runs on GoI-empanelled cloud (MeghRaj/NIC). DR failover targets a second availability zone within the same empanelled cloud — never a cross-cloud or foreign-region failover.

---

## When asked to make a change

- If a requested change would touch any of the above, implement it in a way that **preserves** the constraint, and say so explicitly rather than silently complying with something that weakens it.
- If a change genuinely requires revisiting one of these (e.g., "let's default to GPT-4o because self-hosted quality isn't good enough") — that's a real architectural decision, not a code change. Flag it, don't just do it. It belongs in `DECISIONS.md` with the human's sign-off, not implemented ad hoc.
- Before implementing a new feature, check `PROGRESS.md` for current state — don't assume something is unbuilt or re-plan something already decided in `DECISIONS.md`.
- Any new module should have a corresponding entry in the relevant test suite (`tests/unit/`, `tests/integration/`, `tests/eval/`, `tests/security/`) before being considered done.

## Project identity

- **Product:** IP-SAKTI Sahayak — multilingual, RAG-based AI assistant for Ayurveda IPR & regulatory guidance
- **Owner org:** Ministry of AYUSH / All India Institute of Ayurveda (AIIA)
- **Deployment target:** Production (not a hackathon demo) — 18-week phased build, see `PROGRESS.md` for current phase
