# Batch 18 review: crop-first label reads, the 2x zoom, and Spark estimates with length stops (Z8, C6, C7)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 1 round, goal pinned with its goal tool

**Who did what:**
- Claude Code (Opus 5.5), as CEO, wrote the SPEC lines, the brief and the contract. It updated the b12, b14 and b15.5 contracts for crop-first reads.
- Before Muse started, the CEO ran the contract against a throwaway reference build: all 438 contract tests passed.
- Muse wrote all the code.

**Gate:** pass, 575 tests (558 before). The contract lock held.

**Goal:**
- Muse's first step was `create_goal`, with the batch's check as the objective (ruff and pytest pass, `tests/contract` untouched). Its last was `update_goal` with status complete.
- All 37 main-agent model calls after the goal was created are attributed to it in the export. The other calls with no goal are Muse's reminder sub-agents, which never carry one.
- The goal reminder confirmed the check before closing.

**Muse cost:** **$0.93266**, priced from its own billing records (`usage.json`): 3,579,226 input tokens (3,364,778 cached) and 37,620 output.

Verdict: PASS (supervisor APPROVE, round 1)

## What changed
- **Z8, crop-first reads:** the label reader only ever sees its own region's crop (PNG, `cropped=True`), never the full photo. A reading can't describe a neighbouring pack. A crop that fails logs one `read` step with no call. Once the budget is spent, nothing is cut or logged.
- **The zoom** is the same crop upscaled 2x (Lanczos), capped at 2,048 px on its longest side. A crop already at the cap gets no zoom and no step.
- **C6, estimates:** a Spark call is checked against the caps with `spark_call_estimate(body)`, computed from the request it will send, instead of a fixed $0.03. The same figure is charged when billing is uncertain. Claim extraction asks for 16,000 tokens.
- **C7, length stops:** a reply cut at `max_tokens` is charged at its real usage and raised as a non-retryable error with its call id. Retrying would stop again.

## Follow-ups (from the supervisor; none blocking)
- The estimate also has to count the `response_format` schema to be a strict upper bound. A live-sized length stop can overrun the cap by $0.0002. This goes into the next contract.
- Pin label reads at `max_tokens: 4000` and the Lanczos upscale in that same contract.
- `scripts/zoom_live.py` labels first reads and zooms by order (fixed on main after this merge).
