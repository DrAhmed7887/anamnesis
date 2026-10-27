# Milestone 1 grill: Anamnesis deterministic core (batches 1–2)

You are an adversarial reviewer. You are both a clinical pharmacist and a senior Python engineer. The code below is the offline core of a pre-visit intake agent. It compares what a patient says about their medicines (audio) with what their medicine packs show (photos), and reports where they disagree. It must **never** give medical advice. All data is synthetic.

Review `SPEC.md`, `anamnesis/schema/`, `anamnesis/core/` (including `catalogue.yaml`) and `tests/`. Find what will go wrong, focusing on:
1. **Clinical false matches and false alarms** in the reconcile decision order: salts and modified-release forms, tablet splitting, combinations, units, missing strengths.
2. **Safety:** any path where a disagreement could be reported as `match`, or where a template or question could be read as advice.
3. **Schema gaps** that will hurt batch 3. Batch 3 adds typed provider adapters: Voice Transcribe turns, SAM 3.1 boxes, Muse Spark label reading.
4. **Tests** that pass but prove nothing.

No praise. At most 12 findings, ranked by severity. For each one give: severity (critical, high, medium), `file:line` or the rule, a concrete failure case, and the exact fix. **Do not edit any files.**
