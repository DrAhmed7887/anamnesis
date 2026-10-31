# Batch 27 audit: double-check another Muse session's build, read-only

You are auditing code that another Muse Code session just wrote for batch 27 of Anamnesis. Work read-only:
- don't create, edit or delete any file;
- run no git command that changes state;
- make no network call, use no API key, and run no `modal` command;
- don't open anything under `evidence/` or `finetune/data*`, nor any `.env` file.

## 1. Goal
The audit is done ONLY when your reply has the three sections in §3, and every finding cites a file and line you opened, or a line of the diff below.

## 2. What the code must do
SPEC.md §2, "Relation checks (batch 27)": open it in the repository. After the value check, six word rules decide what each number in a cited turn was said about (negation, another unit, a count, another medicine's amount, a past amount, a split daily total), and an amount whose every mention is excluded is dropped, taking the other amount with it. Rule 5 and rule 6 each have one exception that only ever keeps an amount.

The contract is `tests/contract/test_b27_relations.py`, and the build passes it. Look for what it doesn't catch:
- a fail-open path: an exception, an empty or odd turn, an unknown status or a malformed claim that keeps an amount the rules would drop, or a new crash in `parse_claims_json`;
- a rule that drops what the SPEC keeps: a bare number, an open unit, a negation three or more tokens away, "before breakfast", "once a day";
- word lists or conditions that differ from the SPEC;
- how far the exceptions' 4-letter prefix match reaches;
- any change to `stated_amounts`, labels, `regimen` or the reconciler.

## 3. Reply
1. **Verdict:** one line.
2. **Findings:** numbered, each with severity, file:line, the evidence and a fix.
3. **What you checked and found fine:** a short list.

Keep it under 500 words.

## The build: `git diff HEAD` (uncommitted in the batch worktree; this copy of the repository is at the contract commit)
```diff
diff --git a/anamnesis/providers/claims.py b/anamnesis/providers/claims.py
index fd5f088..577fe84 100644
--- a/anamnesis/providers/claims.py
+++ b/anamnesis/providers/claims.py
@@ -12,6 +12,12 @@ from anamnesis.core.guardrails import AdviceLeak, assert_no_advice, assert_no_ad
 from anamnesis.providers.base import ProviderError, ProviderTrace, cost_usd, with_one_retry
 from anamnesis.providers.meta import MetaClient, spark_call_estimate
 from anamnesis.providers.numbers import coerce_strength, parse_amount_text
+from anamnesis.providers.relations import (
+    another_names_for_claim,
+    is_amount_grounded,
+    mentions_for_cited_turns,
+    own_names_for_claim,
+)
 from anamnesis.providers.spend import SpendGuard
 from anamnesis.providers.stated import UNIT_WORDS, has_number_role, stated_amounts
 from anamnesis.schema import (
@@ -356,6 +362,30 @@ def parse_claims_json(
                 strength = None
             if isinstance(intake_amount, dict) and intake_amount["amount"] not in said:
                 intake_amount = None
+            if isinstance(strength, dict) or isinstance(intake_amount, dict):
+                entry = cat.resolve(raw["name_text"]) if isinstance(raw.get("name_text"), str) else None
+                other_texts = [
+                    other.get("name_text")
+                    for pos, other in enumerate(raw_claims) if pos != index - 1
+                ]
+                own = own_names_for_claim(raw.get("name_text"), grounded_inn, cat)
+                another = another_names_for_claim(
+                    own, entry, cat, other_texts, raw.get("name_text"),
+                )
+                mentions = mentions_for_cited_turns(
+                    cited, own, another, raw.get("status") == "discontinued",
+                )
+                if isinstance(strength, dict) and not all(
+                    is_amount_grounded(
+                        part["amount"], part["unit"], mentions, False,
+                    )
+                    for part in strength["ingredients"]
+                ):
+                    strength = None
+                if isinstance(intake_amount, dict) and not is_amount_grounded(
+                    intake_amount["amount"], intake_amount["unit"], mentions, True,
+                ):
+                    intake_amount = None
             units_sent = (
                 isinstance(raw.get("regimen"), dict)
                 and raw["regimen"].get("units_per_intake") is not None
diff --git a/anamnesis/providers/relations.py b/anamnesis/providers/relations.py
new file mode 100644
index 0000000..b974277
--- /dev/null
+++ b/anamnesis/providers/relations.py
@@ -0,0 +1,684 @@
+"""Relation checks: what an amount was said about (SPEC sect 2, batch 27)."""
+
+from __future__ import annotations
+
+import re
+import unicodedata
+from dataclasses import dataclass
+from decimal import Decimal
+
+from anamnesis.core.catalogue import ARABIC_CLITICS, Catalogue, normalise
+from anamnesis.providers.stated import (
+    GATE_WORDS,
+    SPANISH_DOSE_WORDS,
+    has_number_role,
+    stated_amounts,
+)
+
+CLAUSE_END_WORDS = frozenset({
+    "now", "but", "currently",
+    "دلوقتي", "دلوقت", "حاليا", "بس",
+    "ahora", "pero", "actualmente",
+    "jetzt", "aber", "derzeit",
+})
+"""Words that end a clause (SPEC sect 2, Relation checks, Clauses)."""
+
+NEGATION_WORDS = frozenset({
+    "not", "no", "never", "dont", "doesnt", "didnt", "isnt", "wasnt",
+    "مش", "مو", "مب",
+    "nunca",
+    "nicht", "kein", "keine", "keinen", "nie",
+})
+"""Negation words one or two tokens before a run (SPEC sect 2, rule 1)."""
+
+DON_PREFIXES = frozenset({"don", "doesn", "didn", "isn", "wasn", "aren", "haven", "won"})
+"""Prefixes whose `t` token counts as negation, so don't (SPEC sect 2, rule 1)."""
+
+MG_WORDS = (
+    "mg", "milligram", "milligrams", "miligramo", "miligramos", "milligramm",
+    "ملي جرام", "مللي جرام", "ملي جم",
+    "مليجرام", "ملليجرام", "ميليجرام", "ملجرام", "ملجم", "مجم", "ملغ", "ملغم", "مغ",
+)
+"""Words that give a mention mg (SPEC sect 2, rule 2)."""
+
+MCG_WORDS = (
+    "mcg", "µg", "μg", "microgram", "micrograms", "microgramo", "microgramos",
+    "mikrogramm",
+    "ميكرو جرام", "ميكروجرام", "ميكروغرام", "مكجم",
+)
+"""Words that give a mention mcg (SPEC sect 2, rule 2)."""
+
+G_WORDS = (
+    "g", "gram", "grams", "gramo", "gramos", "gramm",
+    "جرام", "جم", "غ", "غرام",
+)
+"""Words that give a mention g (SPEC sect 2, rule 2)."""
+
+ML_WORDS = (
+    "ml", "millilitre", "millilitres", "milliliter", "milliliters",
+    "mililitro", "mililitros",
+    "ملي لتر", "مل",
+)
+"""Words that give a mention ml (SPEC sect 2, rule 2)."""
+
+IU_WORDS = ("iu", "unit", "units", "وحده", "وحده دوليه")
+"""Words that give a mention iu (SPEC sect 2, rule 2)."""
+
+OPEN_UNIT_WORDS = frozenset({"ملي", "مللي", "ميكرو"})
+"""Alone these leave the unit open (SPEC sect 2, rule 2)."""
+
+COUNT_EN_WORDS = (
+    "tablet", "tablets", "pill", "pills", "capsule", "capsules",
+    "caplet", "caplets", "puff", "puffs", "drop", "drops",
+    "sachet", "sachets",
+)
+"""English count words (SPEC sect 2, rule 3)."""
+
+COUNT_AR_WORDS = (
+    "حبايه", "حبايات", "حبه", "حبات", "حبوب",
+    "قرص", "اقراص",
+    "كبسوله", "كبسولات",
+    "برشامه", "برشامات",
+)
+"""Arabic count words (SPEC sect 2, rule 3)."""
+
+GERMAN_DOSE_WORDS = frozenset({
+    "tablette", "tabletten",
+    "filmtablette", "filmtabletten",
+    "retardtablette", "retardtabletten",
+    "kapsel", "kapseln", "retardkapsel", "retardkapseln",
+    "dragee", "dragees",
+})
+"""German tablet and capsule words (SPEC sect 2, rule 3 and round 6)."""
+
+SOBRE_WORDS = frozenset({"sobre", "sobres"})
+"""Extra count words (SPEC sect 2, rule 3)."""
+
+JOINER_WORDS = frozenset({"and", "و", "y", "und", "the", "a"})
+"""Joiners skipped when walking back (SPEC sect 2, rule 4)."""
+
+OF_WORDS = frozenset({"of", "من", "de", "del", "von"})
+"""Words linking an amount to a following name (SPEC sect 2, rule 4)."""
+
+PAST_MARKERS = (
+    "used to", "previously", "formerly", "was taking", "were taking", "in the past",
+    "كنت", "زمان", "قبل كده", "قبل كدا",
+    "solía", "solia", "tomaba",
+    "früher", "fruher", "nahm",
+)
+"""Past markers earlier in the same clause (SPEC sect 2, rule 5)."""
+
+PER_DAY_PHRASES = (
+    "a day", "per day", "daily", "every day", "each day",
+    "في اليوم", "يوميا", "باليوم", "كل يوم",
+    "al día", "por día", "diarios", "diarias", "cada día",
+    "am Tag", "pro Tag", "täglich", "taglich", "jeden Tag",
+)
+"""Phrases that make a mention a daily total (SPEC sect 2, rule 6)."""
+
+
+def _norm(word: str) -> str:
+    return normalise(unicodedata.normalize("NFC", word))
+
+
+def _norm_list(words: tuple[str, ...] | frozenset[str] | set[str]) -> frozenset[str]:
+    return frozenset(_norm(word) for word in words)
+
+
+def _phrase_lists(phrases: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
+    out: list[tuple[str, ...]] = []
+    for phrase in phrases:
+        parts = tuple(_norm(phrase).split())
+        if parts:
+            out.append(parts)
+    return tuple(out)
+
+
+_CLAUSE_END = _norm_list(CLAUSE_END_WORDS)
+_NEGATION = _norm_list(NEGATION_WORDS)
+_DON = _norm_list(DON_PREFIXES)
+_OPEN_UNIT = _norm_list(OPEN_UNIT_WORDS)
+_JOINER = _norm_list(JOINER_WORDS)
+_OF = _norm_list(OF_WORDS)
+_COUNT = (
+    _norm_list(COUNT_EN_WORDS)
+    | _norm_list(COUNT_AR_WORDS)
+    | SPANISH_DOSE_WORDS
+    | _norm_list(GERMAN_DOSE_WORDS)
+    | _norm_list(SOBRE_WORDS)
+)
+_PAST = _phrase_lists(PAST_MARKERS)
+_PER_DAY = _phrase_lists(PER_DAY_PHRASES)
+
+_UNIT_SINGLE: dict[str, str] = {}
+_UNIT_TWO: dict[tuple[str, str], str] = {}
+
+
+def _add_units(words: tuple[str, ...], unit: str) -> None:
+    for raw in words:
+        parts = tuple(_norm(raw).split())
+        if len(parts) == 1:
+            _UNIT_SINGLE.setdefault(parts[0], unit)
+        elif len(parts) == 2:
+            _UNIT_TWO.setdefault((parts[0], parts[1]), unit)
+
+
+_add_units(MG_WORDS, "mg")
+_add_units(MCG_WORDS, "mcg")
+_add_units(G_WORDS, "g")
+_add_units(ML_WORDS, "ml")
+_add_units(IU_WORDS, "iu")
+
+_UNIT_SKIP: frozenset[str] = (
+    frozenset(_UNIT_SINGLE)
+    | {word for pair in _UNIT_TWO for word in pair}
+    | _OPEN_UNIT
+)
+_GATE_EXTRA: frozenset[str] = frozenset(_UNIT_SINGLE) | _OPEN_UNIT
+
+
+@dataclass(frozen=True)
+class Token:
+    """One token of a cited turn: a digit run kept raw, or a normalised word."""
+
+    text: str
+    is_digit: bool
+    clause: int
+
+
+@dataclass(frozen=True)
+class Mention:
+    """One value of one number run, with its unit and daily-total flag."""
+
+    value: Decimal
+    unit: str | None
+    is_daily_total: bool
+    run_id: object
+    clause_has_another: bool = False
+
+
+_DIGIT_RUN_RE = re.compile(r"(?<![\d.,٬٫])[0-9٠-٩۰-۹]+(?:[.,٫][0-9٠-٩۰-۹]+)?(?!\d)")
+_ALWAYS_END = frozenset({";", ":", "!", "?", "؛", "؟", "،"})
+
+
+def _flush_chunk(
+    buf: list[str], clause: int, tokens: list[Token],
+) -> int:
+    if buf:
+        for word in normalise("".join(buf)).split():
+            tokens.append(Token(text=word, is_digit=False, clause=clause))
+            if word in _CLAUSE_END:
+                clause += 1
+        buf.clear()
+    return clause
+
+
+def _is_boundary_dot(text: str, pos: int) -> bool:
+    prev = text[pos - 1] if pos > 0 else ""
+    nxt = text[pos + 1] if pos + 1 < len(text) else ""
+    return not (prev.isdigit() and nxt.isdigit())
+
+
+def tokenize_turn(text: str) -> list[Token]:
+    """Cut one turn into digit tokens and normalised words with clause ids."""
+    source = unicodedata.normalize("NFC", text)
+    spans = [(m.start(), m.end(), m.group(0)) for m in _DIGIT_RUN_RE.finditer(source)]
+    tokens: list[Token] = []
+    clause = 0
+    pos = 0
+    for start, end, raw in [*spans, (len(source), len(source), "")]:
+        gap = source[pos:start]
+        gap_start = pos
+        buf: list[str] = []
+        idx = 0
+        while idx < len(gap):
+            char = gap[idx]
+            orig = gap_start + idx
+            if char == "\r" or char == "\n":
+                clause = _flush_chunk(buf, clause, tokens)
+                while idx < len(gap) and gap[idx] in "\r\n":
+                    idx += 1
+                clause += 1
+                continue
+            if char in _ALWAYS_END:
+                clause = _flush_chunk(buf, clause, tokens)
+                while idx < len(gap) and gap[idx] in _ALWAYS_END:
+                    idx += 1
+                clause += 1
+                continue
+            if char == "." or char == ",":
+                if not _is_boundary_dot(source, orig):
+                    buf.append(char)
+                    idx += 1
+                    continue
+                clause = _flush_chunk(buf, clause, tokens)
+                idx += 1
+                clause += 1
+                while idx < len(gap):
+                    nxt_char = gap[idx]
+                    nxt_orig = gap_start + idx
+                    if nxt_char in "\r\n" or nxt_char in _ALWAYS_END:
+                        idx += 1
+                        continue
+                    if nxt_char in ".," and _is_boundary_dot(source, nxt_orig):
+                        idx += 1
+                        continue
+                    break
+                continue
+            buf.append(char)
+            idx += 1
+        clause = _flush_chunk(buf, clause, tokens)
+        if raw:
+            tokens.append(Token(text=raw, is_digit=True, clause=clause))
+        pos = end
+    return tokens
+
+
+def _number_runs(tokens: list[Token]) -> list[tuple[int, int, int]]:
+    runs: list[tuple[int, int, int]] = []
+    idx = 0
+    while idx < len(tokens):
+        token = tokens[idx]
+        qualifies = token.is_digit or has_number_role(token.text)
+        if not qualifies:
+            idx += 1
+            continue
+        start = idx
+        clause = token.clause
+        end = idx
+        while (
+            end + 1 < len(tokens)
+            and tokens[end + 1].clause == clause
+            and (tokens[end + 1].is_digit or has_number_role(tokens[end + 1].text))
+        ):
+            end += 1
+        runs.append((start, end, clause))
+        idx = end + 1
+    return runs
+
+
+def _run_unit(tokens: list[Token], end: int, clause: int) -> tuple[str | None, int]:
+    if (
+        end + 2 < len(tokens)
+        and tokens[end + 1].clause == clause
+        and tokens[end + 2].clause == clause
+        and not tokens[end + 1].is_digit
+        and not tokens[end + 2].is_digit
+    ):
+        pair = (tokens[end + 1].text, tokens[end + 2].text)
+        if pair in _UNIT_TWO:
+            return _UNIT_TWO[pair], 2
+    if (
+        end + 1 < len(tokens)
+        and tokens[end + 1].clause == clause
+        and not tokens[end + 1].is_digit
+        and tokens[end + 1].text in _UNIT_SINGLE
+    ):
+        return _UNIT_SINGLE[tokens[end + 1].text], 1
+    return None, 0
+
+
+def _is_daily_total(tokens: list[Token], end: int, unit_len: int, clause: int) -> bool:
+    after = end + 1 + unit_len
+    for phrase in _PER_DAY:
+        if after + len(phrase) > len(tokens):
+            continue
+        ok = True
+        for offset, word in enumerate(phrase):
+            token = tokens[after + offset]
+            if token.is_digit or token.clause != clause or token.text != word:
+                ok = False
+                break
+        if ok:
+            return True
+    return False
+
+
+def _is_negated(tokens: list[Token], start: int, clause: int) -> bool:
+    for dist in (1, 2):
+        idx = start - dist
+        if idx < 0 or tokens[idx].clause != clause or tokens[idx].is_digit:
+            continue
+        word = tokens[idx].text
+        if word in _NEGATION:
+            return True
+        if word == "t" and idx - 1 >= 0:
+            prev = tokens[idx - 1]
+            if not prev.is_digit and prev.clause == clause and prev.text in _DON:
+                return True
+    return False
+
+
+def _is_count(
+    tokens: list[Token], start: int, end: int, clause: int, has_unit: bool,
+) -> bool:
+    if has_unit:
+        return False
+    for dist in (1, 2):
+        idx = end + dist
+        if idx < len(tokens) and tokens[idx].clause == clause:
+            token = tokens[idx]
+            if not token.is_digit and token.text in _COUNT:
+                if dist == 1:
+                    return True
+                between = tokens[end + 1]
+                if between.is_digit or between.text not in _UNIT_SINGLE:
+                    return True
+    for dist in (1, 2):
+        idx = start - dist
+        if idx >= 0 and tokens[idx].clause == clause:
+            token = tokens[idx]
+            if not token.is_digit and token.text in _COUNT:
+                if dist == 1:
+                    return True
+                between = tokens[start - 1]
+                if between.is_digit or between.text not in _UNIT_SINGLE:
+                    return True
+    return False
+
+
+def _names_to_token_lists(names: list[str]) -> list[list[str]]:
+    lists: list[list[str]] = []
+    for name in names:
+        if not isinstance(name, str):
+            continue
+        norm = _norm(name)
+        if not norm:
+            continue
+        parts = norm.split()
+        lists.append(parts)
+        if len(parts) > 1:
+            glued = norm.replace(" ", "")
+            if glued:
+                lists.append([glued])
+    return lists
+
+
+def _has_arabic(word: str) -> bool:
+    return any(0x0600 <= ord(char) <= 0x06FF for char in word)
+
+
+def _find_name_occs(
+    tokens: list[Token], lists: list[list[str]], kind: str,
+) -> list[tuple[int, int, str]]:
+    occs: list[tuple[int, int, str]] = []
+    for wanted in lists:
+        size = len(wanted)
+        for pos in range(len(tokens) - size + 1):
+            ok = True
+            for offset, word in enumerate(wanted):
+                token = tokens[pos + offset]
+                if token.is_digit:
+                    ok = False
+                    break
+                if _has_arabic(word):
+                    if not re.fullmatch(ARABIC_CLITICS + re.escape(word), token.text):
+                        ok = False
+                        break
+                elif token.text != word:
+                    ok = False
+                    break
+            if ok:
+                occs.append((pos, pos + size - 1, kind))
+    return occs
+
+
+def _resolve_occs(occs: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
+    ordered = sorted(occs, key=lambda o: (-(o[1] - o[0] + 1), 0 if o[2] == "own" else 1))
+    kept: list[tuple[int, int, str]] = []
+    taken: set[int] = set()
+    for start, end, kind in ordered:
+        if any(pos in taken for pos in range(start, end + 1)):
+            continue
+        kept.append((start, end, kind))
+        taken.update(range(start, end + 1))
+    return kept
+
+
+def _is_another(
+    tokens: list[Token],
+    start: int,
+    end: int,
+    clause: int,
+    unit_len: int,
+    another_ends: set[int],
+    another_starts: set[int],
+) -> bool:
+    idx = start - 1
+    while idx >= 0:
+        token = tokens[idx]
+        if not token.is_digit and token.text in _CLAUSE_END:
+            idx -= 1
+            continue
+        if token.is_digit or has_number_role(token.text):
+            idx -= 1
+            continue
+        if not token.is_digit and token.text in _UNIT_SKIP:
+            idx -= 1
+            continue
+        if not token.is_digit and token.text in _JOINER:
+            idx -= 1
+            continue
+        break
+    if idx >= 0 and idx in another_ends:
+        return True
+    after_unit = end + 1 + unit_len
+    if (
+        after_unit < len(tokens)
+        and tokens[after_unit].clause == clause
+        and not tokens[after_unit].is_digit
+        and tokens[after_unit].text in _OF
+    ):
+        name_at = after_unit + 1
+        if (
+            name_at < len(tokens)
+            and tokens[name_at].clause == clause
+            and name_at in another_starts
+        ):
+            return True
+    return False
+
+
+def _find_past_occs(tokens: list[Token]) -> list[tuple[int, int]]:
+    occs: list[tuple[int, int]] = []
+    for phrase in _PAST:
+        size = len(phrase)
+        for pos in range(len(tokens) - size + 1):
+            if all(
+                not tokens[pos + offset].is_digit
+                and tokens[pos + offset].text == word
+                for offset, word in enumerate(phrase)
+            ):
+                occs.append((pos, pos + size - 1))
+    return occs
+
+
+def _is_past(
+    tokens: list[Token],
+    start: int,
+    clause: int,
+    past: list[tuple[int, int]],
+    blockers: list[tuple[int, int]],
+) -> bool:
+    for pstart, pend in past:
+        if not (pend < start and tokens[pstart].clause == clause and tokens[pend].clause == clause):
+            continue
+        if any(bstart > pend and bend < start for bstart, bend in blockers):
+            continue
+        return True
+    return False
+
+
+def mentions_in_turn(
+    transcript: str,
+    own_names: list[str],
+    another_names: list[str],
+    is_discontinued: bool = False,
+) -> list[Mention]:
+    """Every value of every number run the claim keeps, with unit and daily flag.
+
+    Rules 1 and 3-5 exclude runs; rule 2 gives each kept run its unit (or none).
+    A past marker does not reach past another medicine's name: "I used to take
+    Protonix ... also taking Concor 5" keeps the 5, which a careful listener
+    hears as present (the fine-tune generator's Arabic notes say it this way).
+    The blocking name also matches on a shared prefix of 4+ letters, since the
+    generator's brand slips ("Zyrtectec") keep the name's start.
+    """
+    tokens = tokenize_turn(transcript)
+    if not tokens:
+        return []
+    occs = _find_name_occs(tokens, _names_to_token_lists(own_names), "own")
+    occs += _find_name_occs(tokens, _names_to_token_lists(another_names), "another")
+    kept = _resolve_occs(occs)
+    another_ends = {end for _, end, kind in kept if kind == "another"}
+    another_starts = {start for start, _, kind in kept if kind == "another"}
+    another_spans = [(start, end) for start, end, kind in kept if kind == "another"]
+    own_covered = {pos for start, end, kind in kept if kind == "own" for pos in range(start, end + 1)}
+    fuzzy_words = {
+        word
+        for parts in _names_to_token_lists(another_names)
+        for word in parts
+        if len(word) >= 4
+    }
+    for pos, token in enumerate(tokens):
+        if token.is_digit or pos in own_covered or len(token.text) < 4:
+            continue
+        if any(token.text.startswith(word) or word.startswith(token.text) for word in fuzzy_words):
+            another_spans.append((pos, pos))
+    another_clauses = {
+        tokens[pos].clause for start, end in another_spans for pos in range(start, end + 1)
+    }
+    past = _find_past_occs(tokens)
+    mentions: list[Mention] = []
+    for run_index, (start, end, clause) in enumerate(_number_runs(tokens)):
+        parts = [token.text for token in tokens[start:end + 1]]
+        nxt = end + 1
+        if (
+            nxt < len(tokens)
+            and tokens[nxt].clause == clause
+            and not tokens[nxt].is_digit
+            and (tokens[nxt].text in GATE_WORDS or tokens[nxt].text in _GATE_EXTRA)
+        ):
+            parts.append(tokens[nxt].text)
+        values = stated_amounts(" ".join(parts))
+        if not values:
+            continue
+        unit, unit_len = _run_unit(tokens, end, clause)
+        if _is_negated(tokens, start, clause):
+            continue
+        if _is_count(tokens, start, end, clause, unit is not None):
+            continue
+        if _is_another(tokens, start, end, clause, unit_len, another_ends, another_starts):
+            continue
+        if not is_discontinued and _is_past(tokens, start, clause, past, another_spans):
+            continue
+        daily = _is_daily_total(tokens, end, unit_len, clause)
+        for value in values:
+            mentions.append(Mention(
+                value=value,
+                unit=unit,
+                is_daily_total=daily,
+                run_id=run_index,
+                clause_has_another=clause in another_clauses,
+            ))
+    return mentions
+
+
+def mentions_for_cited_turns(
+    transcripts: list[str],
+    own_names: list[str],
+    another_names: list[str],
+    is_discontinued: bool = False,
+) -> list[Mention]:
+    """Kept mentions over every cited turn, with globally unique run ids."""
+    all_mentions: list[Mention] = []
+    for turn_index, text in enumerate(transcripts):
+        for mention in mentions_in_turn(text, own_names, another_names, is_discontinued):
+            all_mentions.append(Mention(
+                value=mention.value,
+                unit=mention.unit,
+                is_daily_total=mention.is_daily_total,
+                run_id=(turn_index, mention.run_id),
+                clause_has_another=mention.clause_has_another,
+            ))
+    return all_mentions
+
+
+def own_names_for_claim(
+    name_text: object, grounded_inn: object, catalogue: Catalogue,
+) -> list[str]:
+    """The claim's own names: name_text, its entry's names, its kept inn."""
+    names: list[str] = []
+    if isinstance(name_text, str) and name_text:
+        names.append(name_text)
+    entry = catalogue.resolve(name_text) if isinstance(name_text, str) else None
+    if entry is not None:
+        names.append(entry.brand)
+        names.extend(entry.aliases)
+        names.extend(sorted(entry.inns))
+    if isinstance(grounded_inn, str) and grounded_inn:
+        names.append(grounded_inn)
+    return names
+
+
+def another_names_for_claim(
+    own_names: list[str],
+    claim_entry: object,
+    catalogue: Catalogue,
+    other_name_texts: list[object],
+    claim_name_text: object,
+) -> list[str]:
+    """Every other medicine's names: catalogue entries plus other claims."""
+    claim_inns: frozenset[str] | None = getattr(claim_entry, "inns", None)
+    names: list[str] = []
+    for entry in catalogue.entries:
+        if claim_inns is None or entry.inns != claim_inns:
+            names.append(entry.brand)
+            names.extend(entry.aliases)
+            names.extend(sorted(entry.inns))
+    claim_norm = _norm(claim_name_text) if isinstance(claim_name_text, str) else ""
+    for other in other_name_texts:
+        if not isinstance(other, str) or not other:
+            continue
+        if claim_inns is not None:
+            other_entry = catalogue.resolve(other)
+            if other_entry is not None and other_entry.inns == claim_inns:
+                continue
+        other_norm = _norm(other)
+        if claim_norm and other_norm and (claim_norm in other_norm or other_norm in claim_norm):
+            continue
+        names.append(other)
+    own_norms = {_norm(name) for name in own_names if isinstance(name, str)}
+    return [name for name in names if _norm(name) not in own_norms]
+
+
+def is_amount_grounded(
+    value: Decimal,
+    unit: str,
+    mentions: list[Mention],
+    is_intake: bool,
+) -> bool:
+    """True when a kept mention grounds the amount; rule 6 applies to intakes.
+
+    Rule 2 holds for every claim: the unit must match unless the mention
+    says no unit, whether or not the claim resolves to a catalogue entry.
+
+    A rule 6 splitter must not share its clause with another medicine's name:
+    metoprolol's 25 must not split Flolipid's 40 a day.
+    """
+    grounding = [
+        mention for mention in mentions
+        if mention.value == value
+        and (mention.unit is None or mention.unit == unit)
+    ]
+    if not grounding:
+        return False
+    if not is_intake or not all(mention.is_daily_total for mention in grounding):
+        return True
+    grounding_runs = {mention.run_id for mention in grounding}
+    for mention in mentions:
+        if mention.run_id in grounding_runs or mention.clause_has_another:
+            continue
+        if value == mention.value * 2 or value == mention.value * 3 or value == mention.value * 4:
+            return False
+    return True
diff --git a/tests/unit/test_b27_extra.py b/tests/unit/test_b27_extra.py
new file mode 100644
index 0000000..d7f2a8a
--- /dev/null
+++ b/tests/unit/test_b27_extra.py
@@ -0,0 +1,109 @@
+"""Batch 27 extra unit checks: relation rules on invented transcripts."""
+
+import json
+from decimal import Decimal
+
+from anamnesis.providers.claims import parse_claims_json
+from anamnesis.providers.relations import (
+    is_amount_grounded,
+    mentions_in_turn,
+    tokenize_turn,
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
+def _claim(name, amount=None, unit="mg", status="active", turn_ids=("turn-0",)):
+    intake = None if amount is None else {"inn": name, "amount": str(amount), "unit": unit}
+    return {
+        "name_text": name, "inn": None, "strength": None, "intake_amount": intake,
+        "regimen": {"units_per_intake": None, "intakes_per_day": None, "as_needed": None},
+        "status": status, "turn_ids": list(turn_ids),
+    }
+
+
+def _intake(texts, *claims, index=0):
+    texts = texts if isinstance(texts, tuple) else (texts,)
+    kept = parse_claims_json(json.dumps({"claims": list(claims)}), _turns(*texts))[index].intake_amount
+    return None if kept is None else kept.amount
+
+
+def test_tokenizer_keeps_decimals_and_splits_clauses():
+    tokens = tokenize_turn("I take 2.5 mg but now I take 5 mg.")
+    texts = [(token.text, token.is_digit) for token in tokens]
+    assert ("2.5", True) in texts
+    first = next(token for token in tokens if token.text == "2.5")
+    last = next(token for token in tokens if token.text == "5")
+    assert first.clause != last.clause
+
+
+def test_bare_number_grounds_any_unit():
+    assert _intake("I take Concor five.", _claim("Concor", 5)) == Decimal(5)
+    assert _intake("I take Concor five.", _claim("Concor", 5, "mcg")) == Decimal(5)
+
+
+def test_german_keine_negates_while_later_clause_keeps_five():
+    said = "Ich nehme Concor, keine zehn Milligramm, ich nehme aber fünf Milligramm."
+    assert _intake(said, _claim("Concor", 10)) is None
+    assert _intake(said, _claim("Concor", 5)) == Decimal(5)
+
+
+def test_german_daily_total_split_is_not_one_intake():
+    said = "Ich nehme Concor, zehn Milligramm täglich, fünf Milligramm morgens."
+    assert _intake(said, _claim("Concor", 10)) is None
+    assert _intake(said, _claim("Concor", 5)) == Decimal(5)
+
+
+def test_count_word_before_the_number_is_a_count():
+    assert _intake("She takes Concor capsules three daily.", _claim("Concor", 3)) is None
+
+
+def test_of_phrase_with_other_medicine_drops_for_this_claim():
+    said = "I take twenty milligrams of Lipitor and Concor five milligrams."
+    assert _intake(said, _claim("Concor", 20)) is None
+    assert _intake(said, _claim("Concor", 5)) == Decimal(5)
+    assert _intake(said, _claim("Lipitor", 20)) == Decimal(20)
+
+
+def test_third_split_daily_total_is_not_one_intake():
+    said = "I take Concor, fifteen milligrams a day, five each time, three times."
+    assert _intake(said, _claim("Concor", 15)) is None
+    assert _intake(said, _claim("Concor", 5)) == Decimal(5)
+
+
+def test_unresolved_claim_still_matches_the_unit():
+    said = "I take Zyloric ein Gramm daily."
+    assert _intake(said, _claim("Zyloric", 1, "g")) == Decimal(1)
+    assert _intake(said, _claim("Zyloric", 1)) is None
+
+
+def test_past_marker_does_not_reach_past_another_medicine():
+    said = "I used to take Protonix twenty milligrams also taking Concor five milligrams."
+    both = [_claim("Protonix", 20), _claim("Concor", 5)]
+    assert _intake(said, *both, index=0) is None
+    assert _intake(said, *both, index=1) == Decimal(5)
+
+
+def test_splitter_in_another_medicines_clause_does_not_split():
+    said = "I take metoprolol the pill has twenty-five milligrams and Concor forty milligrams a day."
+    both = [_claim("metoprolol", 25), _claim("Concor", 40)]
+    assert _intake(said, *both, index=1) == Decimal(40)
+
+
+def test_past_blocker_survives_a_brand_slip_suffix():
+    said = "I used to take Protonixix twenty milligrams also taking Concor five milligrams."
+    both = [_claim("Protonix", 20), _claim("Concor", 5)]
+    assert _intake(said, *both, index=1) == Decimal(5)
+
+
+def test_mentions_carry_units_and_grounding_matches_them():
+    mentions = mentions_in_turn("I take five micrograms.", ["Concor"], ["Panadol"])
+    assert [(m.value, m.unit) for m in mentions] == [(Decimal(5), "mcg")]
+    assert is_amount_grounded(Decimal(5), "mcg", mentions, True)
+    assert not is_amount_grounded(Decimal(5), "mg", mentions, True)
```
