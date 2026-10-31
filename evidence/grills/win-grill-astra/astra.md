## 1. Five biggest risks, ranked

### 1. “The headline model win doesn’t survive the actual product.”
**Hits:** whether it works; technical ambition.

Generated-text extraction improves dramatically, but full-intake results are 4/8, 3/8 and, after the reader fix, 5/8. The hero produces all three findings only 6/10 times—and scores 0/10 under its registered expectation.

**Do:** pin one backend configuration; evaluate it prospectively without selecting successful runs. Lead with a supported finding **and an unresolved source that gets resolved through re-photo**, not three simultaneous disagreements. Show what remains unresolved: abstention is useful only when incompleteness is visible.

### 2. “Your provenance checks prove words occurred, not that the finding follows.”
**Hits:** whether it works; engineering credibility.

A name and amount appearing in one turn do not establish their relationship. Negation, another medicine’s amount, tablet counts and combination ingredients can defeat lexical checks. Printed pack strength and reported intake are different quantities.

**Do:** audit the hero’s expected type against the actual utterance. Test cross-medicine attribution, negation and combination-component alignment. Where the relationship is unsupported, require `insufficient_information`, not an asserted discrepancy. Don’t “repair” an absent printed brand through catalogue inference.

### 3. “You haven’t demonstrated the difficult part of your audience’s input.”
**Hits:** creativity; whether it works.

Generated transcripts and macOS voices do not establish performance on natural Egyptian Arabic/English switching, local brand pronunciation or hesitations. RxNorm/ATC grounding does not establish Egyptian pack coverage.

**Do:** add a tiny, clearly labelled human-acted acceptance set using invented medication histories. Check the exact catalogue mappings used in the demo. Fluent-speaker availability and local-brand coverage are **unknown**; check both.

### 4. “This looks like a fixed pipeline with a pause button, not an agent.”
**Hits:** Best Agentic Use-Case; technical ambition.

The described workflow establishes orchestration, but not necessarily adaptive agent control. A timeline of calls is observability, not agency.

**Do:** expose the actual state transitions: evidence received, unresolved finding, clinician request, pause, replacement evidence, resumed reconciliation. Identify who makes each decision. Whether model output changes execution beyond fixed stages is **unknown**. Don’t imply autonomous re-photo decisions if the clinician initiates them.

### 5. “The open-weight model is optional, and its strongest evidence is off-path.”
**Hits:** Best Build on Meta Open Weight Models; use of Meta tooling.

The tuned extractor has credible task-level evidence, but no demonstrated end-to-end correctness advantage. Optional deployment weakens its importance.

**Do:** show the tuned extractor actually serving the demonstrated intake, with an exact configuration and trace. Verify official prize eligibility, accepted models and attribution requirements; those are **unknown from these notes**. Don’t assume either that Claude’s planning disqualifies you or that it is irrelevant.

## 2. What’s missing

Efforts below are estimates.

### (a) Before freeze: **four hours total**

| Item | Effort | Risk | Why it matters |
|---|---:|---|---|
| Audit/add only missing semantic fixtures: hero type, negation, cross-medicine amount, combination alignment | 1 h | Medium: may expose larger defects | Prioritises false findings over cosmetic improvements. If a repair exceeds the budget, abstain on that unsupported pattern. Preserve the original hero score. |
| Record three invented notes—English, Egyptian Arabic, mixed—with consenting fluent speakers; run all three and repeat the predetermined demo twice | 2 h | Medium: speaker availability and API latency | Tests the advertised input rather than more generated text. Declare scripts, configuration and scoring before running; publish every result. This is a smoke test, not validation. |
| Verify the complete re-photo path, unresolved-source visibility and pinned backend configuration; patch only demonstrated demo-path defects | 1 h | Low–medium | Prevents a successful-looking brief from concealing missing evidence or a resume failure. |

### (b) Video, README or demo by Wednesday

- **Evidence-first film — 3 h; medium editing risk.** Show the utterance, cited crop, finding, unresolved source and clinician-controlled recovery. Label staged inputs. State aggregate success rates; don’t present a selected recording as representative reliability.
- **One evidence/configuration ledger — 1.5 h; low risk.** Separate generated extraction, label reading, full intakes and hero runs. Include model/provider settings, code revisions, denominators, abstentions and failures. Keep registered and revised scoring separate.
- **Eligibility, reproduction and licence audit — 1 h; medium external uncertainty.** Check official bonus rules, adapter/base-model permissions, executable reproduction instructions and image attribution. Apache-2.0 product code does not relicense third-party photographs.
- **One independent clinician walkthrough, if available — 0.5 h; high scheduling risk.** Ask them to locate supporting evidence and identify unresolved items without coaching. Report the observation, not a workflow-benefit claim.

### (c) Tempting but not worth it

- **Another training sweep — 4–12 h; high risk.** Extraction is not the demonstrated full-intake bottleneck.
- **Another serving provider — 3–8 h; high integration risk.** You already have a provider/prompt failure confounding the comparison.
- **FHIR, barcode integration, patient app or longitudinal record — roughly 8–40+ h each; high scope risk.** None fixes the current disagreement classification, label-reading or recovery demonstration.
- **A new Chinese-brand inference layer — 6–16 h; high provenance risk.** An unprinted brand is not a missing feature to hallucinate into existence.

## 3. Overclaim check

- **“Zero harmful claims.”** Say: “Zero outputs scored harmful under our stated rubric in these runs, after product checks.” This is not a general safety guarantee. Publish the rubric and abstentions.
- **“The fine-tune beats Spark.”** Say: “290/303 versus 203/303 on held-out generated notes, one run each.” Template/generator leakage controls are **unknown**; disclose them. No end-to-end superiority is established.
- **“Held-out Spanish brands prove generalisation.”** The result supports a narrow unseen-brand test, not unseen speech, photographs or populations.
- **“Fireworks timeouts were caused by no reasoning effort.”** Say: “Failures were attributed to timeouts; after changing effort, observed correctness rose from 1/8 to 5/8.” One before/after pass does not isolate causality.
- **“Serving matches evaluation.”** Say: “Five tested notes returned byte-identical claims.” That establishes a smoke-test result, not general equivalence.
- **“Hero success: 6/10.”** Report both: “Registered score 0/10; all three observed findings appeared in 6/10 under the revised interpretation.”
- **“Independent reviewers; 2,519 tests.”** Specify reviewer identities/session separation and test categories. Fresh model sessions are not independent external validation.
- **“Chinese-only pack was a miss.”** Check whether the gold expectation required an unprinted brand. Correct abstention should count as correct under a prospectively repaired rubric.

## 4. Bonus prizes

**Agentic:** credible bounded-workflow evidence, but not yet undeniable agentic control. A trace showing genuine evidence-dependent execution and clinician-controlled pause/resume would strengthen it. If execution is entirely fixed, say so; don’t bolt on theatrical autonomy.

**Open weights:** substantial fine-tuning evidence and live serving, but uncertain eligibility and limited product-level benefit. Make the contribution inspectable: eligible base model, adapter/configuration access as permitted, exact serving trace, reproducible evaluation, and measured extraction latency without implying better full-intake accuracy.

## 5. Single most important change

**Replace the flaky three-finding hero with a repeatedly tested, human-acted bilingual intake that visibly turns an unresolved source into an evidence-backed finding through clinician-requested re-photo.**