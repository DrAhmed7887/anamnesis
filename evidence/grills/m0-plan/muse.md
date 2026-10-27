muse: workspace root: <workspace> (cwd default)
muse: Including your Claude Code and Codex personal rules and 58 skills — manage with /settings.
muse: Skills: 97 loaded · 1 warning · 4 details hidden
muse:   `skills_catalog` was trimmed to fit its size limit (32 KB): 65 descriptions compacted, 0 skill ids omitted
muse:   Run `muse skills list --source all` for full diagnostics.
muse: Agent delegation: auto unavailable: workspace is untrusted.
## Verdict first

Day 1 plan is sound on scope cuts. Biggest risk is not APIs. It is the agent loop inventing links between voice turns and SAM boxes.

Do offline work before any live probe. A 1-token curl still exercises billing and wastes focus.

### 1. Agent Loop Feasibility: Spark + SAM 3.1 + Voice turns

* SAM returns regions, not drugs. Spark will want to name the drug from a blurry crop. Do not let it.
* Trap: coordinate systems. Store `x_min/y_min/x_max/y_max` normalized 0-1000 plus `image_hash + crop_id`. Otherwise you cannot audit a box later.
* Trap: many boxes, one label. SAM 3.1 will oversegment blister packs. Cap to top-k by area/confidence. Require reconciler to pick `region_id`, not "the white box".
* Trap: transcript drift. `muse-voice-transcribe-1.0` turns need `turn_id, start_ms, end_ms, lang, speaker`. Diarization will fail on code-switched Arabic/French/English intake. Keep original text, do not normalize early.
* Trap: refine loop. Spark -> "need clearer crop" -> SAM -> Spark can loop forever. Set `max_grounding_iters=2`, then abstain.
* Pattern for Day 1: independent evidence refs in your Pydantic models. e.g. `audio_evidence: list[turn_id]`, `visual_evidence: list[region_id]`. No cross-modal claim without both filled or explicit `missing_modality`.

### 2. Failure Modes: reconciliation

* Dose vs strength: you have this right in Batch 1. Enforce it. `strength_mg_per_unit` vs `dose_units_per_intake + frequency_per_day`. Most LLMs conflate "Metoprolol 50mg twice daily" into "100mg". Test that exact case.
* Brand-to-INN:
  * Concor -> Bisoprolol, usually fumarate. Salt matters.
  * Panadol -> Paracetamol, but Panadol Extra adds caffeine. Your 8-12 list must include one combo trap.
  * Augmentin -> Amoxicillin/Clavulanate ratio matters: 875/125 vs 500/125 are not interchangeable. Test ratio mismatch.
  * Same brand, different strength by country. Catalogue needs `country` field even if synthetic.
* Unreadable labels: need closed enum `UNREADABLE, PARTIAL, CONFLICT`. Default must be abstain + flag for clinician, never guess from shape/color.
* Negation/recency: "I stopped Concor" + old box on table. Audio negates visual. Your deterministic reconciler needs `status: active/discontinued/unknown`, with recency rule: patient statement of stopping wins, but marks `needs_review`.
* Your 8-12 cases are too few unless they are adversarial. Pick: 2 clean matches, 2 strength mismatches, 1 dose-frequency mismatch, 1 combo, 1 brand alias, 1 unreadable, 1 negation, 1 ratio trap.

### 3. Meta Tooling Footprint: what judges can see

Embed this in code, not slides:

* `providers/meta_voice.py`, `providers/meta_sam.py`, `providers/meta_spark.py` with literal `muse-spark-1.3`, `muse-voice-transcribe-1.0`, `sam-3.1` in code. Fixture adapters must implement the same interface.
* Log `model_id + version + latency_ms + tokens` into every output JSON. Judges score what they can trace.
* UI Day 1 stub: show transcript turns with `turn_id`, image with boxes + `region_id`, and final card citing both. That is cross-modal proof.
* Comparison harness: `evals/compare.py` Spark vs Glimmer 30B (Modal) vs Spark Open 816B (Baseten) on the same 8-12 fixtures. Meta path stays default. Open weights are comparison only.
* Template lock: `output/template_v1.txt` with fixed non-prescriptive wording + disclaimer + `needs_clinician_review` boolean. No free-text dosing advice.

### 4. Meta Model API gotchas to design around now

* Streaming breaks validation. Accumulate full JSON, then Pydantic-validate. Do not stream-parse partial tool calls on Day 1.
* Context blowup: transcript + multiple crops will hit token limits fast. Design truncation now: top-3 regions, transcript window, downscaled crops.
* Tool choice: `auto` may skip your reconciler tool, `required` can force loops. Use one tool: `submit_reconciliation`. No multi-tool chain on Day 1.
* Multilingual: pass explicit `locale_hint` to transcribe. Auto-detect fails on mixed intake.
* JSON mode is brittle on enums. Use closed string enums, lowercase, plus strict schema validation in pytest.
* Retries/timeouts: add timeout 30s, 1 retry, idempotency key per case. Log spend per call from day one against your $493 cap.
* Key hygiene: `ANAMNESIS_META_API_KEY` from env only. Never in repo. Your strict `.gitignore` should block `.env, *.wav, *.mp4, crops/`.

Suggested reorder for your 6 hours: repo init -> Batch 1 models + tests -> Batch 2 reconciler + adversarial 10 cases -> Batch 3 typed interfaces + fixtures -> commit. Move live probe to Day 2.

