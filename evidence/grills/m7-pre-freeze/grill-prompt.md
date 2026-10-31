# Adversarial grill: the Anamnesis code as it stands (28 Oct)

You are an adversarial reviewer. Your job is to break the code in this package: find concrete inputs that make it violate its own SPEC or its safety rules. Each finding must be reproducible from the code alone, offline, with no model call. Give the exact input to a named function (a label text, a transcript, a reading, a claim, a report or a path), what SPEC.md says should happen, and what the code does instead. Skip any finding you can't give a concrete input for.

**Worker mode:** skip any session-continuity steps. Don't use tools, and don't read or write files. Everything you need is in the package below, so answer only from it.

## Attack surfaces, in priority order
1. **A wrong strength shown as fact.** Label texts that keep a wrong strength through the volume rule (`_per_other_volume`, SPEC §2) or the stated-amount check: syrups, drops, combination packs, salts, units, digits, and Arabic, Spanish and French wordings. A strength that fails closed (dropped to null) is not a finding. SPEC §2 lists the coverage it gives up on purpose.
2. **A false `match` or a wrong pairing** in the reconciler: brands, salts, release, combination products, two packs of one INN at different strengths, and a claim with no amount.
3. **Advice leakage:** any path where free text from a model or the pack reaches the brief outside the fixed templates and the quoting rules.
4. **Provenance:** a finding that cites a turn or region it didn't come from, a crop that isn't its region's, or a brief that renders media the report wasn't made from.
5. **Spend and model safety:** any call path that bypasses `SessionGuard` or `SpendGuard`, mis-charges a call, or lets a `*-contributor` id through, and the call budget.
6. **Data handling:** `scripts/intake_live.py --reader baseten` and `scripts/reader_eval.py` must never send a photo outside the public folders that `docs/DATA_HANDLING.md` allows. Find a path or an input that gets around their checks.
7. **Any other real bug,** such as a crash on valid input, or an unhandled error that loses a report.

## Output
- A table of at most 15 rows, most severe first: `# | severity (critical/high/medium/low) | surface (1–7) | file:function | exact input | SPEC says | code does`.
- For each critical or high row, a pytest-style test of at most 15 lines that would fail on this code.
- No praise, no summary and no rewrites of the code.
- The last line is exactly: `GRILL: N findings (C critical, H high)`.
