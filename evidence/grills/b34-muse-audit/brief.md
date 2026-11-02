# Batch 34 audit: double-check another Muse session's build, read-only

You are auditing code that another Muse Code session just wrote for batch 34 of Anamnesis. Work read-only:
- don't create, edit or delete any file;
- run no git command that changes state;
- make no network call, use no API key, and run no `modal` command;
- don't open anything under `evidence/` or `finetune/data*`, nor any `.env` file.

## 1. Goal
The audit is done ONLY when your reply has the three sections in §3, and every finding cites a file and line you opened, or a line of the diff below.

## 2. What the code must do
SPEC.md §3, "Decision order for one claim and one pack", rule 6, the bullet "Spanish salt names (batch 34)" and the bullets under it: open it in the repository. In short: a table of exactly eleven Spanish salt words, each mapped to an English salt `INN_ALIASES` curates, read only by `_loose_salts`, beside the English name, with the existing moiety-or-brand check; a Spanish word yields its English salt. Nothing that disagreed or abstained before may now agree, and name matching doesn't change.

The contract is `tests/contract/test_b34_spanish_salts.py`, and the build passes it. Look for what it doesn't catch:
- any pair that disagreed or abstained before and now agrees;
- a Spanish word read where it shouldn't be (an ordinary Spanish word, a word inside another word, another moiety's salt), or not read where it should be (accents, capitals, punctuation, word order, Arabic or mixed text);
- one salt read as two, or two salts read as one, across the two languages;
- the Spanish hero's boxes, "Emconcor® Cor 5 mg … Fumarato de bisoprolol …" and "Lopresor® 100 mg … Metoprolol, tartrato …", now carrying a salt: pairing in `reconcile_all`, rule 7's salt-basis equivalents, and anything else that reads `_pack_salts`;
- the rewrite of `_loose_salts` from a set comprehension to a loop: any change beyond the Spanish words.

## 3. Reply
1. **Verdict:** one line.
2. **Findings:** numbered, each with severity, file:line, the evidence and a fix.
3. **What you checked and found fine:** a short list.

Keep it under 500 words.

## The build: `git diff HEAD` (uncommitted in the batch worktree; this copy of the repository is at the contract commit)
```diff
diff --git a/anamnesis/core/reconcile.py b/anamnesis/core/reconcile.py
index 95d988c..d945f3d 100644
--- a/anamnesis/core/reconcile.py
+++ b/anamnesis/core/reconcile.py
@@ -7,6 +7,7 @@ from anamnesis.core.catalogue import ARABIC_CLITICS, Catalogue, normalise
 from anamnesis.schema import (
     INN_ALIASES,
     SALT_BASIS_EQUIVALENTS,
+    SPANISH_SALT_NAMES,
     Finding,
     IngredientAmount,
     PackObservation,
@@ -267,11 +268,16 @@ def _text_salts(text: str, catalogue: Catalogue) -> list[tuple[str, str]]:
 
 def _loose_salts(text: str, padded: str, catalogue: Catalogue) -> set[tuple[str, str]]:
     """Curated salt words that sit apart from the moiety, when the text names the moiety or its brand."""
-    present = {
-        (moiety, normalise(salt))
-        for moiety, salt in INN_ALIASES.values()
-        if salt and f" {normalise(salt)} " in padded and catalogue.mentions_moiety(text, moiety)
-    }
+    present = set()
+    for moiety, salt in set(INN_ALIASES.values()):
+        if not salt:
+            continue
+        names = [normalise(salt)]
+        names.extend(
+            normalise(spanish) for spanish, english in SPANISH_SALT_NAMES.items() if english == salt
+        )
+        if any(f" {name} " in padded for name in names) and catalogue.mentions_moiety(text, moiety):
+            present.add((moiety, normalise(salt)))
     return {
         (moiety, salt)
         for moiety, salt in present
diff --git a/anamnesis/schema/__init__.py b/anamnesis/schema/__init__.py
index 74fe0f5..f41fab7 100644
--- a/anamnesis/schema/__init__.py
+++ b/anamnesis/schema/__init__.py
@@ -5,6 +5,7 @@ from anamnesis.schema.findings import DiscrepancyType, Finding
 from anamnesis.schema.medication import (
     INN_ALIASES,
     SALT_BASIS_EQUIVALENTS,
+    SPANISH_SALT_NAMES,
     DoseRegimen,
     IngredientAmount,
     MedicationStatus,
@@ -37,6 +38,7 @@ __all__ = [
     "Readability",
     "Release",
     "SALT_BASIS_EQUIVALENTS",
+    "SPANISH_SALT_NAMES",
     "Strength",
     "StrengthPer",
     "Unit",
diff --git a/anamnesis/schema/medication.py b/anamnesis/schema/medication.py
index f0b4b7e..ef1e824 100644
--- a/anamnesis/schema/medication.py
+++ b/anamnesis/schema/medication.py
@@ -98,6 +98,20 @@ INN_ALIASES: dict[str, tuple[str, str | None]] = {
     "coffeinum": ("caffeine", None),
 }
 
+SPANISH_SALT_NAMES: dict[str, str] = {
+    "succinato": "succinate",
+    "tartrato": "tartrate",
+    "fumarato": "fumarate",
+    "hemifumarato": "hemifumarate",
+    "besilato": "besilate",
+    "maleato": "maleate",
+    "hidrocloruro": "hydrochloride",
+    "cálcica": "calcium",
+    "calcica": "calcium",
+    "cálcica trihidrato": "calcium trihydrate",
+    "calcica trihidrato": "calcium trihydrate",
+}
+
 SALT_BASIS_EQUIVALENTS: dict[tuple[str, str, Decimal], Decimal] = {
     ("metoprolol", "succinate", Decimal("23.75")): Decimal("25"),
     ("metoprolol", "succinate", Decimal("47.5")): Decimal("50"),
diff --git a/tests/unit/test_b34_extra.py b/tests/unit/test_b34_extra.py
new file mode 100644
index 0000000..e9cefda
--- /dev/null
+++ b/tests/unit/test_b34_extra.py
@@ -0,0 +1,29 @@
+"""Batch 34: the Spanish salt table beside INN_ALIASES (SPEC §3 rule 6)."""
+
+from anamnesis.schema import INN_ALIASES, SPANISH_SALT_NAMES
+
+
+def test_table_holds_exactly_the_spec_words() -> None:
+    assert SPANISH_SALT_NAMES == {
+        "succinato": "succinate",
+        "tartrato": "tartrate",
+        "fumarato": "fumarate",
+        "hemifumarato": "hemifumarate",
+        "besilato": "besilate",
+        "maleato": "maleate",
+        "hidrocloruro": "hydrochloride",
+        "cálcica": "calcium",
+        "calcica": "calcium",
+        "cálcica trihidrato": "calcium trihydrate",
+        "calcica trihidrato": "calcium trihydrate",
+    }
+
+
+def test_every_spanish_word_maps_to_a_curated_english_salt() -> None:
+    curated = {salt for _, salt in INN_ALIASES.values() if salt}
+    assert set(SPANISH_SALT_NAMES.values()) <= curated
+
+
+def test_deliberate_omissions_stay_out() -> None:
+    for word in ("calcio", "sódica", "trihidrato", "potasio", "succinat"):
+        assert word not in SPANISH_SALT_NAMES
```
