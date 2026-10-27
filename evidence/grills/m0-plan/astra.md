# Astra Milestone 0 Adversarial Grill — Day 1 Build Plan

**Date**: Tuesday, October 27, 2026  
**Auditor**: `gpt-6-astra` (Adversarial Gatekeeper)  
**Target**: Anamnesis Day 1 Build Plan  

---

## Verdict

**This is not a six-hour implementation plan. It is an integration-discovery plan with implementation scheduled after the unknowns.**

The critical path currently runs through account administration, undocumented tool behavior, spec synthesis, clinical data curation, and several unverified model integrations. Any one can consume the evening.

**The only defensible Day 1 target is: three reviewed commits delivering a tested, offline reconciliation core and explicit provider interfaces—not four working live integrations.** If “Batch 3 complete” means production-ready clients for every named service, remove the tonight guarantee now.

Also: **passing synthetic tests proves internal consistency, not clinical correctness, provider compatibility, or prize eligibility.**

---

## 1. Execution bottlenecks that will blow the budget

These are planning estimates, not measured durations.

| Work item | Likely time | Why the estimate in the plan is unsafe |
|---|---:|---|
| Preflight and billing | 20–60+ min | Keychain permissions, incorrect endpoint/auth assumptions, billing UI, payment verification, and credit delays are independent failure points. |
| Repository, remote, source-doc import, spec | 30–75 min | Condensing contracts correctly is design work. Seven thousand tokens is not a small handoff. |
| First successful Codex/Muse invocation | 15–60 min | Wrapper configuration, model availability, working directory, approvals, authentication, and output handling are unproven. |
| Batch 1 | 40–75 min | Schema design creates downstream obligations: identifiers, units, nullability, enum semantics, and validation. |
| Batch 2 as written | 120–240+ min | A 60-drug international catalogue is a data-quality project, before implementing reconciliation and safety behavior. |
| Batch 3 as written | 120–240+ min | Four integrations, audio normalization, an unverified dependency, provider response parsing, credentials, and fixtures. |
| Reviews, fixes, commits, adversarial gate | 45–90+ min | Reviewing a diff is not equivalent to accepting it; generated-code correction loops are missing from the schedule. |

Even generous overlap does not rescue the plan: **the single-writer rule serializes implementation and repair.**

### Biggest offender: the drug catalogue
What exactly is one “drug”?
- Active ingredient?
- Brand in a particular country?
- Specific formulation, concentration, and route?
- Combination product?
- Salt versus active-moiety equivalent?

Sixty plausible YAML entries are easy to generate. Sixty entries safe to normalize across languages, markets, strengths, and formulations are not.
**Cut to 8–12 explicitly synthetic catalogue entries designed around test cases.** Do not present them as a clinically validated international catalogue.

### Second-biggest offender: Batch 3
`voice.py`, segmentation/parser integration, and two model clients are not one small batch. Each has different contracts and failure behavior.
**Cut Batch 3 to typed interfaces, fixture implementations, response validation, and explicit unavailable-provider behavior.** A single live smoke test is a stretch goal after all three commits.

---

## 2. Sequencing and dependency flaws

### A. You are scheduling architecture discovery after architecture commitment
You cannot sensibly freeze schemas without knowing at least the shape of external inputs:
- Do speech results contain timestamps, segments, or just text?
- Does the image service return masks, boxes, extracted text, or something else?
- Which coordinate system and sample-rate assumptions apply?

**Fix:** inspect a documented or captured response shape before freezing adapters. Keep provider payloads separate from domain models so provider quirks do not dictate the entire schema. Do not require live calls for this inspection.

### B. Batch 1 names a provenance chain without specifying its semantics
`photo_id -> region_id -> spoken_span_id` suggests a hierarchy, but spoken evidence need not belong to a photo region. Relationships may be absent, ambiguous, or many-to-many.
**Fix:** independent evidence identifiers plus explicit associations. Do not force uncertain links into a mandatory chain.

### C. Batch 2 depends on decisions that the plan has not made
Dose-versus-strength separation is necessary, not sufficient. You still need rules for units, combination ingredients, and ambiguity surfacing.

---

## 3. What must be cut immediately

### Drop from the critical path
- Credit-card setup and credit-arrival investigation during build.
- The 7K-token narrative spec.
- The 60-drug international catalogue.
- General-purpose audio normalization.
- Multiple live model integrations on Day 1.
- GPU deployments.

### Preserve, but simplify
- **Batch 1 (Contracts)**: Minimal domain models, explicit missing/unknown states, independent evidence references, unit and identifier validation, focused schema tests.
- **Batch 2 (Deterministic core)**: 8–12 synthetic catalogue entries, a prewritten reconciliation decision table, exact/explicitly supported normalization only, fixed non-prescriptive output templates.
- **Batch 3 (Adapter boundary)**: Typed provider interfaces, fixture-backed implementations, strict response validation, explicit error handling.

---

## 4. Replacement Six-Hour Schedule

| Elapsed time | Deliverable |
|---|---|
| 00:00–00:15 | Verify Python, `uv`, Git, and one Codex invocation. Freeze package layout. Hard-stop account debugging. |
| 00:15–00:35 | Initialize repository, ignore rules, minimal contract/decision table, baseline commit. Attempt private remote creation once. |
| 00:35–01:25 | Batch 1 implementation, stable-diff review, tests, commit. |
| 01:25–02:45 | Batch 2 implementation, review, tests, commit. |
| 02:45–03:00 | Adversarial gate on contracts and reconciliation. |
| 03:00–04:00 | Batch 3 offline adapters, failure tests, review, commit. |
| 04:00–05:00 | Integration fixes and clean-checkout verification. |
| 05:00–06:00 | Buffer, documentation, push verification. |

## Tonight’s Acceptance Test
1. Three identifiable, reviewed batch commits.
2. A fresh checkout can install from the lockfile and run tests without provider credentials or network calls during tests.
3. Unknown, ambiguous, and unavailable states cannot masquerade as successful reconciliation.
4. No secrets or raw sensitive evidence are tracked.
5. Remote push status is verified.
