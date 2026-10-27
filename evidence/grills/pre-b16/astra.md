# Idea grill: GPT-6 Astra (gpt-6-astra), 27 Oct 2026

One message, at Ahmed's request before B16. Brief and bundle: README, SPEC, decisions, supervisor triage, the Arabic live report, the video playbook, the idea committee notes, the prize list.

**Verdict: Right wedge, credible engineering, not yet a placing demo—the biggest losing risk is presenting a dose-versus-tablet difference as a medication error without proving useful clinician work.**

### Scorecard — current evidence, not promised work

| Criterion | Score | Evidence |
|---|---:|---|
| Technical execution | **7/10** | Deterministic reconciliation, evidence-ID validation, bounded calls and live extraction; finished clinician workflow remains unproven. |
| Use of Meta models | **8/10** | Voice Transcribe, SAM and Spark perform substantive perception tasks; SAM’s incremental benefit is not yet demonstrated. |
| Real-world impact | **6/10** | Recognizable intake friction, but no observed time saving, independent usability result or realistic-case results yet. |
| Originality | **6/10** | Medication intake is familiar; source-linked bilingual comparison and explicit abstention distinguish this implementation. |
| Demo/presentation | **3/10** | The supplied artifact is JSON; the playbook advertises nonexistent features and unsupported outcomes. |

**User and wedge:** Keep it. The primary user is the clinician reviewing intake before a teleconsultation; the patient supplies evidence, and the clinic is the plausible buyer. Egyptian Arabic/English code-switching is a demonstrated starting point, not evidence of broad multilingual coverage. **“No advice” is a strength** when paired with a useful, reviewable output; a weakness only if presented as the product’s main achievement. Judges need to see work accomplished, not merely harm avoided.

### Top five changes, ranked by likely win-probability gain per hour

*These are substitutions or bounded refinements within the accepted plan—not another workstream.*

1. **Retire the stale playbook’s claims — 0.5 h.**  
   Make one submission claim checklist against SPEC. Delete “first,” fatal-error prevention, six-minute savings, FHIR, autonomous rotation, fabricated benchmarks and compliance assurances. Use **Wed 4 Nov, 20:00 CET** as the submission target. This prevents reputation damage and obvious judge contradictions.

2. **Replace the hero example, not the wedge — 1 h within B17.**  
   The supplied **50 mg intake versus 100 mg tablet is not necessarily a source disagreement**. Keep it as evidence of nuanced handling, not the opening alarm. Choose a staged case with an explicitly stated tablet strength conflicting with the photographed strength; annotate it before running. The hook below is conditional on that case working end to end.

3. **Probe the pairing blind spot — 1.5 h within B17.**  
   Test one explicitly associated claim/photo pair with disjoint ingredient identities: candidate pairing currently requires identity overlap, so it may produce two `missing_modality` findings rather than `ingredient_mismatch`. Also test ambiguous same-ingredient packs. Inspect the actual report before claiming “detects ingredient disagreements.” Fix only a demonstrated release blocker; otherwise disclose the limitation. A callable pairwise rule is not proof of end-to-end detection.

4. **Turn existing testing into judge-readable evidence — 2 h.**  
   Publish a compact case table: expected/observed finding, false agreement, abstention, evidence-link correctness, latency and cost. In the already-planned usability session, observe one concrete task—locating and verifying the disputed source values—and report comments, not generalized savings. **Show crop-zoom only if** an authentic partial/unreadable first read becomes annotation-correct on the source crop, with trace and unchanged provenance. Otherwise show abstention; do not manufacture a recovery.

5. **Package a credible public artifact — 1 h.**  
   Add a sample brief, staged-case results, architecture and exact replay instructions to the README; check public links logged out. Label cached replay and edited waiting time. State that source links enable verification, not that they establish truth. This—not reviewer counts—makes a physician-engineer portfolio piece credible. The synthetic catalogue and hosted-media boundary must be explicit.

### Three things to stop or cut

- **New video-production infrastructure:** use screen capture and clean narration, not a HyperFrames engineering project.
- **Further class-map expansion:** ship the accepted tiny overlap observation; do not drift into interaction checking.
- **Another broad grill cycle:** the accepted stop must actually happen; fix reproduced release blockers only.

### First 20 seconds

**[Staged-data label; Arabic audio, translated caption, pack photo.]**

“This staged patient says their tablets are 50 milligrams. The pack says 100. Before the teleconsultation, Anamnesis puts both sources in the clinician’s brief.”

**[Click: audio turn plays; source region highlights.]**

“Check what was said. Check what was photographed. It reports the disagreement—not treatment advice.”
