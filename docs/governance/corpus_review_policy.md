# Corpus Review Policy

**IP-SAKTI Sahayak — Governance Document**

## Overview

This policy defines the human-in-the-loop review process for corpus changes in the IP-SAKTI Sahayak system. All new or amended statutory content must pass through this review process before being treated as fully authoritative.

**Per ARCHITECTURE.md §9:** Corpus reviewer staffing and final SLA confirmation pending AIIA approval.

---

## Review Process

### 1. Ingestion Pipeline Flagging

The ingestion pipeline automatically flags content for review when:
- New statutes or treaty text is ingested
- Amendments to existing statutes are detected via version-diff
- Version hash changes indicate content modification
- High-visibility changes are detected (e.g., Patents Rules amendments)

### 2. Review Queue

Flagged content enters the review queue with the following states:
- `pending_review`: Awaiting reviewer assignment
- `in_review`: Currently under review
- `completed`: Review finished
- `approved`: Content approved for authoritative use
- `rejected`: Content rejected or requires revision

### 3. Reviewer Assignment

**Proposed Reviewer Pool (pending AIIA confirmation):**
- AIIA-designated AYUSH-IP subject matter expert(s)
- Legal-drafting familiarity preferred
- 1-2 people for MVP scope

### 4. Review Criteria

Reviewers must verify:
- **Accuracy:** Content accurately reflects the source legal text
- **Completeness:** No missing sections or amendments
- **Format:** Proper section/article/clause-level chunking
- **Metadata:** Correct jurisdiction, domain, and version information
- **Cross-references:** Accurate internal and external references

### 5. Review SLAs

**Routine Amendments:**
- Target: 5 business days from ingestion-pipeline flag to review completion
- Purpose: Standard statutory updates, minor amendments

**High-Visibility Changes:**
- Target: 24-48 hours expedited path
- Triggers: Patents Rules amendments, major legislative changes
- Purpose: Critical updates requiring rapid deployment

**Missed SLA Escalation:**
- If SLA is missed, the content remains queryable but is marked `pending_review`
- Confidence engine treats unreviewed content as lower-confidence
- Escalation to AIIA project management for resolution

---

## Content Handling During Review

### Pending Review State

Content in `pending_review` state:
- **Remains queryable** through the system
- **Marked as lower-confidence** by the Citation & Confidence Engine
- **Not treated as fully authoritative** until sign-off
- **Visible to users** with appropriate confidence indicators

### Approved State

Content in `approved` state:
- **Treated as fully authoritative**
- **Normal confidence scoring** applies
- **Used for all retrieval operations** without special marking

### Rejected State

Content in `rejected` state:
- **Removed from active retrieval** or marked as deprecated
- **Reason for rejection** documented in review log
- **May require re-ingestion** after corrections

---

## Review Record

### Database Storage

All review decisions are stored in the `corpus_review_log` table (PostgreSQL):

```sql
review_id UUID PRIMARY KEY
chunk_id VARCHAR(255) NOT NULL
version_hash VARCHAR(64) NOT NULL
reviewer_id UUID REFERENCES user_roles(user_id)
decision VARCHAR(20) CHECK (decision IN ('pending_review', 'approved', 'rejected'))
timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
notes TEXT
review_status VARCHAR(20) DEFAULT 'pending_review'
metadata JSONB
```

### Audit Trail

The review log is part of the system's audit trail per ARCHITECTURE.md §9:
- 7-year retention requirement
- Immutable and complete
- Full traceability for legal disputes

---

## Reviewer Responsibilities

### Required Actions

1. **Timely Review:** Complete reviews within specified SLAs
2. **Accurate Assessment:** Thoroughly verify content accuracy and completeness
3. **Clear Documentation:** Document decisions with specific reasons
4. **Quality Assurance:** Ensure chunking and metadata meet system requirements

### Prohibited Actions

1. **Auto-approval:** Never approve content without proper review
2. **Skip Review:** Cannot bypass review queue for any content
3. **Modifications Outside System:** All changes must go through the ingestion pipeline

---

## Dispute Resolution

### Reviewer Disagreements

If multiple reviewers disagree:
- Senior reviewer or AIIA designated authority makes final decision
- Disagreement documented in review notes
- Content remains in review until resolution

### System Escalation

If review process is blocked:
- Escalate to AIIA project management
- Document blocking issue in project management system
- Consider temporary downgrade of confidence if urgent

---

## Compliance Notes

### DPDP Act Alignment

- **Purpose Limitation:** Review process limited to corpus quality assessment
- **Data Minimization:** Only content metadata is logged, not user queries
- **Right to Erasure:** Reviewer data handled per organizational privacy policy

### Data Residency

- All review data stored in PostgreSQL on GoI empanelled cloud (MeghRaj/NIC)
- No cross-cloud data transfer
- DR failover within same empanelled cloud per architecture

---

## Version History

| Version | Date | Changes | Approver |
|---------|------|---------|----------|
| 1.0 | 2026-08-28 | Initial policy creation | Pending AIIA approval |

---

## Appendix: AIIA Confirmation Required

The following items require explicit AIIA confirmation before this policy becomes operational:

1. **Reviewer Pool:** Final confirmation of reviewer staffing and qualifications
2. **SLA Finalization:** Confirmation of 5-day routine and 24-48hr expedited SLAs
3. **Escalation Procedures:** Final approval of escalation paths and authorities
4. **Review Criteria:** Any additions or modifications to review criteria

Until these items are confirmed, this policy remains in draft status.
