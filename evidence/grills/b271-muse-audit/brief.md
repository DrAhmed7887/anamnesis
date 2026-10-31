# Batch 27.1 audit: double-check another Muse session's build, read-only

You are auditing code that another Muse Code session just wrote for batch 27.1 of Anamnesis. Work read-only:
- don't create, edit or delete any file;
- run no git command that changes state;
- make no network call, use no API key, and run no `modal` command;
- don't open anything under `evidence/` or `finetune/data*`, nor any `.env` file.

## 1. Goal
The audit is done ONLY when your reply has the three sections in §3, and every finding cites a file and line you opened, or a line of the diff below.

## 2. What the code must do
SPEC.md §2, "Relation checks (batch 27)": the three places marked "batch 27.1". A number with no unit word followed by a duration word is a duration, never a mention (but "ten a day" is a daily amount); a negation word right after a word of knowing ("weiß nicht") doesn't negate the number; and when the relation checks drop a claim's amount, its `units_per_intake` goes too unless a rule-3 count mention has that value.

The contract is `tests/contract/test_b271_relations.py` (and batch 27's), and the build passes it. Look for what it doesn't catch: a duration that swallows a real dose, a units drop that happens without a relation-check drop (or misses one), an interaction with the pairing rule, and anything that changes batch 27's behaviour elsewhere.

## 3. Reply
1. **Verdict:** one line.
2. **Findings:** numbered, each with severity, file:line, the evidence and a fix.
3. **What you checked and found fine:** a short list.

Keep it under 400 words.

## The build: `git diff HEAD` (uncommitted in the batch worktree; this copy of the repository is at the contract commit)
```diff
diff --git a/anamnesis/providers/claims.py b/anamnesis/providers/claims.py
index 577fe84..e37cb4a 100644
--- a/anamnesis/providers/claims.py
+++ b/anamnesis/providers/claims.py
@@ -14,6 +14,7 @@ from anamnesis.providers.meta import MetaClient, spark_call_estimate
 from anamnesis.providers.numbers import coerce_strength, parse_amount_text
 from anamnesis.providers.relations import (
     another_names_for_claim,
+    count_values_for_cited_turns,
     is_amount_grounded,
     mentions_for_cited_turns,
     own_names_for_claim,
@@ -362,6 +363,7 @@ def parse_claims_json(
                 strength = None
             if isinstance(intake_amount, dict) and intake_amount["amount"] not in said:
                 intake_amount = None
+            relation_dropped = False
             if isinstance(strength, dict) or isinstance(intake_amount, dict):
                 entry = cat.resolve(raw["name_text"]) if isinstance(raw.get("name_text"), str) else None
                 other_texts = [
@@ -382,10 +384,19 @@ def parse_claims_json(
                     for part in strength["ingredients"]
                 ):
                     strength = None
+                    relation_dropped = True
                 if isinstance(intake_amount, dict) and not is_amount_grounded(
                     intake_amount["amount"], intake_amount["unit"], mentions, True,
                 ):
                     intake_amount = None
+                    relation_dropped = True
+            if (
+                relation_dropped
+                and isinstance(regimen, dict)
+                and regimen.get("units_per_intake") is not None
+                and regimen["units_per_intake"] not in count_values_for_cited_turns(cited)
+            ):
+                regimen = {**regimen, "units_per_intake": None}
             units_sent = (
                 isinstance(raw.get("regimen"), dict)
                 and raw["regimen"].get("units_per_intake") is not None
diff --git a/anamnesis/providers/relations.py b/anamnesis/providers/relations.py
index aaab6d7..e447e8f 100644
--- a/anamnesis/providers/relations.py
+++ b/anamnesis/providers/relations.py
@@ -102,6 +102,18 @@ GERMAN_DOSE_WORDS = frozenset({
 SOBRE_WORDS = frozenset({"sobre", "sobres"})
 """Extra count words (SPEC sect 2, rule 3)."""
 
+DURATION_WORDS = (
+    "year", "years", "month", "months", "week", "weeks", "day", "days",
+    "hour", "hours",
+    "سنه", "سنين", "سنوات", "شهر", "شهور", "اشهر",
+    "اسبوع", "اسابيع", "يوم", "ايام", "ساعه", "ساعات",
+    "año", "años", "mes", "meses", "semana", "semanas",
+    "día", "días", "hora", "horas",
+    "Jahr", "Jahre", "Jahren", "Monat", "Monate", "Monaten",
+    "Woche", "Wochen", "Tag", "Tage", "Tagen", "Stunde", "Stunden",
+)
+"""Duration words that make a run a duration, never an amount (SPEC sect 2, rule 3, batch 27.1)."""
+
 JOINER_WORDS = frozenset({"and", "و", "y", "und", "the", "a"})
 """Joiners skipped when walking back (SPEC sect 2, rule 4)."""
 
@@ -158,6 +170,7 @@ _COUNT = (
 )
 _PAST = _phrase_lists(PAST_MARKERS)
 _PER_DAY = _phrase_lists(PER_DAY_PHRASES)
+_DURATION = _norm_list(DURATION_WORDS)
 
 _UNIT_SINGLE: dict[str, str] = {}
 _UNIT_TWO: dict[tuple[str, str], str] = {}
@@ -360,12 +373,25 @@ def _is_negated(tokens: list[Token], start: int, clause: int) -> bool:
             continue
         word = tokens[idx].text
         negated = word in _NEGATION
+        is_t_neg = False
         if not negated and word == "t" and idx - 1 >= 0:
             prev = tokens[idx - 1]
             if not prev.is_digit and prev.clause == clause and prev.text in _DON:
                 negated = True
-        if negated and tokens[idx + 1].text not in _KNOWING:
-            return True
+                is_t_neg = True
+        if not negated:
+            continue
+        if tokens[idx + 1].text in _KNOWING:
+            continue
+        before = idx - 2 if is_t_neg else idx - 1
+        if (
+            before >= 0
+            and tokens[before].clause == clause
+            and not tokens[before].is_digit
+            and tokens[before].text in _KNOWING
+        ):
+            continue
+        return True
     return False
 
 
@@ -397,6 +423,22 @@ def _is_count(
     return False
 
 
+def _is_duration(
+    tokens: list[Token], end: int, clause: int, has_unit_word: bool,
+) -> bool:
+    if has_unit_word:
+        return False
+    if not tokens[end].is_digit and tokens[end].text == "a":
+        return False
+    nxt = end + 1
+    return (
+        nxt < len(tokens)
+        and tokens[nxt].clause == clause
+        and not tokens[nxt].is_digit
+        and tokens[nxt].text in _DURATION
+    )
+
+
 def _names_to_token_lists(names: list[str]) -> list[list[str]]:
     lists: list[list[str]] = []
     for name in names:
@@ -600,6 +642,8 @@ def mentions_in_turn(
             continue
         if _is_count(tokens, start, end, clause, unit_len > 0):
             continue
+        if _is_duration(tokens, end, clause, unit_len > 0):
+            continue
         if _is_another(
             tokens, start, end, clause, unit_len, another_ends, another_starts,
             own_starts,
@@ -639,6 +683,34 @@ def mentions_for_cited_turns(
     return all_mentions
 
 
+def count_values_for_cited_turns(transcripts: list[str]) -> set[Decimal]:
+    """Values of the runs rule 3 reads as counts (SPEC sect 2, rule 3, batch 27.1)."""
+    values: set[Decimal] = set()
+    for text in transcripts:
+        tokens = tokenize_turn(text)
+        for start, end, clause in _number_runs(tokens):
+            parts = [token.text for token in tokens[start:end + 1]]
+            nxt = end + 1
+            if (
+                nxt < len(tokens)
+                and tokens[nxt].clause == clause
+                and not tokens[nxt].is_digit
+                and (tokens[nxt].text in GATE_WORDS or tokens[nxt].text in _GATE_EXTRA)
+            ):
+                parts.append(tokens[nxt].text)
+            run_values = stated_amounts(" ".join(parts))
+            if not run_values:
+                continue
+            _, unit_len = _run_unit(tokens, end, clause)
+            if unit_len > 0:
+                continue
+            if _is_duration(tokens, end, clause, False):
+                continue
+            if _is_count(tokens, start, end, clause, False):
+                values.update(run_values)
+    return values
+
+
 def own_names_for_claim(
     name_text: object, grounded_inn: object, catalogue: Catalogue,
 ) -> list[str]:
diff --git a/tests/unit/test_b271_extra.py b/tests/unit/test_b271_extra.py
new file mode 100644
index 0000000..92be501
--- /dev/null
+++ b/tests/unit/test_b271_extra.py
@@ -0,0 +1,107 @@
+"""Batch 27.1 extra unit checks: durations, knowing-negation, dropped counts."""
+
+import json
+from decimal import Decimal
+
+from anamnesis.providers.claims import parse_claims_json
+from anamnesis.providers.relations import (
+    DURATION_WORDS,
+    count_values_for_cited_turns,
+)
+from anamnesis.schema import AudioTurn
+
+
+def _turns(*texts):
+    return [
+        AudioTurn(turn_id=f"turn-{i}", start_ms=4000 * i, end_ms=4000 * i + 3500, transcript=text)
+        for i, text in enumerate(texts)
+    ]
+
+
+def _claim(name, amount=None, unit="mg", units=None, per_day=None, status="active"):
+    intake = None if amount is None else {"inn": name, "amount": str(amount), "unit": unit}
+    return {
+        "name_text": name, "inn": None, "strength": None, "intake_amount": intake,
+        "regimen": {"units_per_intake": units, "intakes_per_day": per_day, "as_needed": None},
+        "status": status, "turn_ids": ["turn-0"],
+    }
+
+
+def _parse(texts, *claims):
+    texts = texts if isinstance(texts, tuple) else (texts,)
+    return parse_claims_json(json.dumps({"claims": list(claims)}, ensure_ascii=False), _turns(*texts))
+
+
+def _intake(texts, *claims, index=0):
+    kept = _parse(texts, *claims)[index].intake_amount
+    return None if kept is None else kept.amount
+
+
+def _units(texts, *claims, index=0):
+    regimen = _parse(texts, *claims)[index].regimen
+    return None if regimen is None else regimen.units_per_intake
+
+
+def test_duration_words_cover_the_spec_lists():
+    for word in ("years", "months", "weeks", "days", "hours", "سنين", "شهور", "años", "semanas",
+                 "Jahren", "Monaten", "Wochen", "Tagen", "Stunden"):
+        assert word in DURATION_WORDS
+
+
+def test_duration_in_months_neither_splits_nor_grounds():
+    said = "I take Concor twelve milligrams a day for six months."
+    assert _intake(said, _claim("Concor", 12, per_day="1")) == Decimal(12)
+    assert _intake(said, _claim("Concor", 6)) is None
+
+
+def test_run_ending_in_a_is_never_a_duration():
+    said = "I take Concor twenty a day for ten years."
+    assert _intake(said, _claim("Concor", 20, per_day="1")) == Decimal(20)
+    assert _intake(said, _claim("Concor", 10)) is None
+
+
+def test_arabic_duration_in_months_keeps_the_daily_amount():
+    said = "باخد كونكور عشرة ملي جرام بقالي خمس شهور"
+    assert _intake(said, _claim("كونكور", 10)) == Decimal(10)
+    assert _intake(said, _claim("كونكور", 5)) is None
+
+
+def test_german_duration_with_digits_is_never_an_amount():
+    said = "Ich nehme Concor 5 Milligramm seit 2 Wochen."
+    assert _intake(said, _claim("Concor", 5)) == Decimal(5)
+    assert _intake(said, _claim("Concor", 2)) is None
+
+
+def test_spanish_duration_with_digits_is_never_an_amount():
+    said = "Tomo Concor 5 miligramos durante 2 semanas."
+    assert _intake(said, _claim("Concor", 5)) == Decimal(5)
+    assert _intake(said, _claim("Concor", 2)) is None
+
+
+def test_negation_right_after_knowing_keeps_the_amount():
+    assert _intake("Ich nehme Concor sicher nicht fünf Milligramm", _claim("Concor", 5)) == Decimal(5)
+    assert _intake("With Concor I know not five milligrams", _claim("Concor", 5)) == Decimal(5)
+
+
+def test_plain_negation_still_drops_the_amount():
+    assert _intake("Ich nehme Concor nicht zehn Milligramm", _claim("Concor", 10)) is None
+    assert _intake("With Concor I know five milligrams, not ten", _claim("Concor", 10)) is None
+
+
+def test_dropped_amount_keeps_a_backed_tablet_count():
+    said = "I take Concor not ten milligrams, two tablets a day."
+    assert _intake(said, _claim("Concor", 10, units="2")) is None
+    assert _units(said, _claim("Concor", 10, units="2")) == Decimal(2)
+
+
+def test_dropped_amount_drops_an_unbacked_tablet_count():
+    said = "I take Concor not ten milligrams, two a day."
+    assert _intake(said, _claim("Concor", 10, units="2")) is None
+    assert _units(said, _claim("Concor", 10, units="2")) is None
+
+
+def test_count_values_read_only_rule_3_counts():
+    assert count_values_for_cited_turns(["I take two tablets a day."]) == {Decimal(2)}
+    assert count_values_for_cited_turns(["I take two a day."]) == set()
+    assert count_values_for_cited_turns(["I take Concor for five years."]) == set()
+    assert count_values_for_cited_turns(["I take five milligrams."]) == set()
```
