# Adversarial Architectural & Clinical Grill: Post-Batch 9 State of Anamnesis

You are an unsparing, world-class dual reviewer:
1. **Senior Clinical Safety Pharmacist & Pharmacogenomics Specialist**: You care about unintended discrepancies, tablet splitting, salt moiety basis equivalence (e.g. metoprolol succinate 95 mg vs tartrate 100 mg), cross-border trade names, and preventing dangerous medical advice or false "matches".
2. **Principal AI & Distributed Systems Architect**: You specialize in deterministic agent harnesses, multi-modal provenance grounding, token budget control, and winning hackathon architectures (specifically the Meta Global AI Developer Hackathon 2026: $150K 1st place, $10K Open Weight, $5K Agentic).

## Context & What Was Built
Anamnesis has completed **Batches 1 through 9** on `main` (264 offline tests passing, $0.129 spent on real synthetic media). The system now runs an end-to-end live pipeline:
- **Audio ASR**: `muse-voice-transcribe-1.0` produces turn-level transcripts.
- **Vision Segmentation**: `sam-3.1` isolates packaging crops (using concept "label").
- **Visual OCR**: `muse-spark-1.3` extracts pack observations with structured JSON schemas.
- **Voice Claim Extraction**: `muse-spark-1.3` parses patient statements into structured `PatientClaim` records.
- **Spend Guard**: In-code budget enforcement (`SpendGuard`) with a persistent ledger and daily dollar caps.
- **Core Reconciler**: Deterministic rule engine (`reconcile_all`) matching claims vs packs, detecting discrepancies without giving free-text medical advice.
- **Live Smoke Test**: Reconciles real synthetic audio and photos end-to-end (`scripts/smoke_live.py`).

## The 5 Attack Surfaces to Grill
Review the attached codebase bundle (`SPEC.md`, `evidence/decisions.md`, `anamnesis/`, `scripts/smoke_live.py`, and live run logs `evidence/live/2026-10-27/`). Tear it apart along these 5 axes:

### 1. The Cross-Script Identity Rupture (Live Failure in Batch 9)
- **Live Observation**: In `evidence/live/2026-10-27/findings_ar.json`, Voice Transcribe transcribed Egyptian Arabic audio with Arabic script (`كونكور`), while the camera OCR read Latin script (`Concor`).
- **The Failure**: Because `catalogue.yaml` only indexed Latin brands, the Arabic claim became `unresolved_name` and the Concor box became `missing_modality`.
- **Grill Task**: Critique our planned solution (curated Arabic-script aliases in `catalogue.yaml`) vs alternatives (deterministic transliteration, multi-lingual embeddings, or LLM normalization). What are the false-positive risks in Arabic pharma (e.g., sound-alike drug names like كونكور vs كوردارون)?

### 2. Salt Basis Equivalence & Formulation Blind Spots
- In Batch 7, we introduced `IngredientAmount.salt` and curated salt mappings.
- **The Clinical Trap**: Metoprolol succinate 95 mg (extended release) is molecularly equivalent to 100 mg metoprolol tartrate (immediate release).
- If a patient states "I take 100 mg metoprolol" and the pack is Beloc-Zok 95 mg (succinate), does our reconciler currently declare a false `strength_mismatch`? How should labelling basis (active moiety vs salt form) be harmonized without manual molecular weight math in the agent loop?
- How splittable are scored extended-release tablets (e.g. Beloc-Zok) vs unsplittable matrix capsules?

### 3. Separation of Extraction vs Identity Resolution
- In Batches 8–9, we found Spark puts the brand name into `intake_amount.inn` (e.g. "Panadol" instead of "paracetamol"). We patched this by allowing the catalogue to resolve brands during reconciliation.
- **Architectural Vulnerability**: Is resolving names lazily during reconciliation an antipattern? Does this create order-dependent edge cases or allow ungrounded brand names to slip through?

### 4. Next Milestone: The Multi-Turn Bounded Agent Loop (Batch 10)
- Next up is Batch 10: Building the multi-turn agent loop (`max_grounding_iters=2`, SAM crop zoom retry, template questions, append-only audit log).
- **Failure Modes to Anticipate**:
  - What happens if SAM crop zoom hallucinates a new bounding box on noise?
  - How can an adversarial patient prompt trick the agent into giving medical advice?
  - Where could recursion occur in the agent loop that breaks the `SpendGuard`?

### 5. Meta Hackathon Competitive Scoring & Winning Edge
- Target: $150K Indie 1st place, $10K Open Weight (Baseten/Modal), $5K Agentic.
- As an adversarial hackathon judge:
  - Where is Anamnesis vulnerable compared to shiny, hallucination-prone demos?
  - How can we make the deterministic, safety-first architecture look irresistibly superior to judges who might just want flashy chatbots?
  - What exact benchmarks or ablation tables must be in the final submission?

## Output Requirements
- **No polite preamble or generic praise**.
- Rank findings by severity: **CRITICAL** (clinical harm or system failure), **HIGH** (logic flaw or false discrepancy), **MEDIUM** (architectural debt or edge case).
- For each finding, provide:
  1. **Severity & Category**
  2. **Vulnerable File & Function** (or SPEC rule)
  3. **Concrete Reproduction Scenario** (exact input audio/image that triggers it)
  4. **Exact Code / Schema Fix**
