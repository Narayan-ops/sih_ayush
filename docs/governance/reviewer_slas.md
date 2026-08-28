# Reviewer Service Level Agreements (SLAs)

**IP-SAKTI Sahayak — Governance Document**

## Overview

This document defines the service level agreements for corpus reviewers in the IP-SAKTI Sahayak system. SLAs are designed to ensure timely review of legal content while maintaining quality standards.

**Per ARCHITECTURE.md §9:** These SLAs are pending AIIA confirmation.

---

## Service Level Targets

### Routine Amendment Review

**Target:** 5 business days

**Definition:**
- **Start Time:** When content is flagged by the ingestion pipeline
- **End Time:** When reviewer completes review (approved/rejected decision)
- **Business Days:** Monday-Friday, excluding public holidays

**Triggers:**
- Standard statutory updates
- Minor amendments to existing statutes
- Routine gazette notifications
- Regular updates to TKDL classification docs

**Acceptable Deviation:**
- Up to 7 business days during peak periods (with prior notification)
- Extension requires AIIA project management approval

### High-Visibility Review

**Target:** 24-48 hours

**Definition:**
- **24-Hour Target:** For critical amendments requiring immediate attention
- **48-Hour Target:** For high-visibility but non-critical changes

**Triggers:**
- Patents Rules amendments
- Major legislative changes affecting core IP frameworks
- Biological Diversity Act amendments
- Supreme Court judgments affecting IP interpretation
- TRIPS-related treaty changes

**Acceptable Deviation:**
- None for 24-hour target (critical path)
- Up to 72 hours for 48-hour target (with escalation)

### Expedited Review Process

When high-visibility content is detected:

1. **Automatic Flagging:** Ingestion pipeline marks as `high_priority`
2. **Immediate Notification:** Reviewer receives immediate notification
3. **Priority Queue:** Content moved to front of review queue
4. **Reviewer Assignment:** Automatic assignment to available reviewer
5. **Escalation Timer:** SLA timer started with automated alerts

---

## Reviewer Availability

### Standard Availability

**Business Hours:** 9:00 AM - 6:00 PM IST, Monday-Friday
**Response Time:** Within 4 hours for review assignment
**Queue Check:** Minimum twice daily (morning and evening)

### Emergency Availability

**For High-Visibility Reviews:**
- **Response Time:** Within 2 hours for notification
- **Review Start:** Within 4 hours of notification
- **Weekend Availability:** Required for critical amendments

### Unavailability Handling

When reviewer is unavailable:
- **Planned Absence:** Notify AIIA project management 2 business days in advance
- **Emergency Absence:** Immediate notification, backup reviewer assigned
- **Vacation:** Minimum 1-week advance notice with coverage plan

---

## Monitoring and Reporting

### SLA Compliance Tracking

**Metrics Tracked:**
- Average review time by content type
- SLA achievement rate (percentage within target)
- Number of SLA breaches per month
- Average queue length
- Reviewer utilization rate

**Reporting:**
- **Weekly:** Individual reviewer performance report
- **Monthly:** SLA compliance dashboard
- **Quarterly:** Comprehensive review with AIIA project management

### Alert Thresholds

**Warnings:**
- SLA at 80% of target time → Yellow alert to reviewer
- Queue length > 10 items → Yellow alert to team

**Escalations:**
- SLA at 90% of target time → Orange alert to AIIA PM
- SLA missed → Red alert to AIIA PM and escalation

---

## Quality Standards Within SLAs

### Speed vs Quality Balance

SLAs do not compromise review quality:
- **Minimum Review Time:** At least 30 minutes per substantial amendment
- **Quality Checklists:** Must complete all checklist items regardless of time pressure
- **Rush Review:** For high-visibility content, additional reviewer may be assigned

### Quality Gates

All reviews must pass these gates before SLA clock stops:
- **Accuracy Verification:** Content compared against source
- **Completeness Check:** All sections and amendments verified
- **Metadata Validation:** All metadata fields confirmed
- **Cross-reference Check:** Internal and external references validated

---

## Penalties and Remediation

### SLA Breaches

**First Breach:**
- **Consequence:** Verbal warning from AIIA PM
- **Remediation:** Process review and improvement plan

**Second Breach (within quarter):**
- **Consequence:** Written warning and SLA performance improvement plan
- **Remediation:** Additional training or process changes

**Third Breach (within quarter):**
- **Consequence:** Formal performance review
- **Remediation:** Possible reassignment or supplemental reviewer assignment

### Chronic Non-Compliance

If SLA achievement rate falls below 80% for two consecutive months:
- **Action:** Formal review of reviewer assignment
- **Possible Outcome:** Increased reviewer staffing or process redesign

---

## Exception Handling

### Force Majeure Events

In case of force majeure (natural disasters, pandemics, etc.):
- **SLA Pause:** SLAs temporarily suspended
- **Notification:** AIIA PM notifies all stakeholders
- **Resumption:** SLAs resume when normal operations restored

### System Outages

If the review system is unavailable:
- **SLA Pause:** Clock paused during outage
- **Extension:** SLA deadline extended by outage duration
- **Notification:** Automatic alerts to all stakeholders

---

## Reviewer Capacity Planning

### Capacity Calculations

**Assumptions:**
- Routine amendments: ~20 per month
- High-visibility amendments: ~2-3 per month
- Average review time: 2 hours per amendment

**Capacity Required:**
- Single reviewer: ~40 hours/month = 1 FTE
- Recommended: 1.5 FTE to handle peaks and vacations

### Seasonal Variations

**Peak Periods:**
- **End of Fiscal Year:** Increased legislative activity
- **Parliament Sessions:** Higher amendment frequency
- **Planning:** Additional reviewer coverage during peak periods

---

## Appendix: SLA Calculation Examples

### Example 1: Routine Amendment

- **Flagged:** Monday, 10:00 AM
- **SLA Target:** 5 business days = Friday, 10:00 AM
- **Reviewer assigned:** Monday, 2:00 PM
- **Review completed:** Thursday, 4:00 PM
- **SLA Status:** Met (within target)

### Example 2: High-Visibility Amendment

- **Flagged:** Tuesday, 3:00 PM
- **SLA Target:** 24 hours = Wednesday, 3:00 PM
- **Reviewer assigned:** Tuesday, 4:00 PM
- **Review completed:** Wednesday, 2:00 PM
- **SLA Status:** Met (within target)

### Example 3: SLA Breach

- **Flagged:** Monday, 10:00 AM
- **SLA Target:** 5 business days = Friday, 10:00 AM
- **Review completed:** Following Monday, 2:00 PM
- **SLA Status:** Breached (3 business days late)
- **Action:** Escalation to AIIA PM

---

## Version History

| Version | Date | Changes | Approver |
|---------|------|---------|----------|
| 1.0 | 2026-08-28 | Initial SLA creation | Pending AIIA approval |
