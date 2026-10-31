# Batch 30 audit: double-check another Muse session's build, read-only

You are auditing code that another Muse Code session just wrote for batch 30 of Anamnesis. Work read-only:
- don't create, edit or delete any file;
- run no git command that changes state;
- make no network call, use no API key, and run no `modal` command;
- don't open anything under `evidence/` or `finetune/data*`, nor any `.env` file.

## 1. Goal
The audit is done ONLY when your reply has the three sections in §3, and every finding cites a file and line you opened, or a line of the diff below.

## 2. What the code must do
SPEC.md §3, "Identity of one side", the bullet "An `inn` that names several ingredients (batch 30)": open it. An `inn` string joined by "/", "+", "&", ",", "and" or «و» names the set of its parts, each resolved as any `inn`. With a strength the set must equal the strength's ingredients; without one it is the side's identity. A one-part `inn` behaves exactly as before. The contract is `tests/contract/test_b30_combined_inn.py`, and the build passes it. Look for what it doesn't catch: a split that wrongly breaks a single ingredient's name, a combined `inn` that now hides a real conflict (a false `match`), and any change to other reconciler rules.

## 3. Reply
1. **Verdict:** one line.
2. **Findings:** numbered, each with severity, file:line, the evidence and a fix.
3. **What you checked and found fine:** a short list.

Keep it under 300 words.

## The build: `git diff HEAD` (uncommitted in the batch worktree; this copy of the repository is at the contract commit)
```diff
diff --git a/anamnesis/core/reconcile.py b/anamnesis/core/reconcile.py
index 27953b7..87fc6ac 100644
--- a/anamnesis/core/reconcile.py
+++ b/anamnesis/core/reconcile.py
@@ -19,6 +19,18 @@ from anamnesis.schema import (
 from anamnesis.schema import DiscrepancyType as D
 from anamnesis.schema.templates import QUESTION_FOR, TEMPLATES
 
+_COMBINED_INN_SPLIT = re.compile(r"\s*(?:[/+&,]|\band\b|(?<!\w)و(?!\w))\s*", re.IGNORECASE)
+
+
+def _split_inn_parts(inn: str) -> list[str]:
+    """Split a combined `inn` into its named ingredients (SPEC §3, batch 30)."""
+    parts = []
+    for chunk in _COMBINED_INN_SPLIT.split(inn):
+        chunk = chunk.strip()
+        if chunk:
+            parts.append(chunk)
+    return parts
+
 
 def _identity(
     strength: Strength | None, inn: str | None, text: str, catalogue: Catalogue,
@@ -34,10 +46,20 @@ def _identity(
             or (name_inns is not None and inns != name_inns)
             or len(inns) < len(strength.ingredients)
         )
-        if inn and _resolve_inn(inn, catalogue) not in inns:
-            conflict = True
+        if inn:
+            parts = _split_inn_parts(inn)
+            if len(parts) >= 2:
+                named = frozenset(_resolve_inn(part, catalogue) for part in parts)
+                if named != inns:
+                    conflict = True
+            elif _resolve_inn(inn, catalogue) not in inns:
+                conflict = True
         return inns, conflict
     if inn:
+        parts = _split_inn_parts(inn)
+        if len(parts) >= 2:
+            inns = frozenset(_resolve_inn(part, catalogue) for part in parts)
+            return inns, ambiguous or (name_inns is not None and inns != name_inns)
         inns = frozenset({_resolve_inn(inn, catalogue)})
         return inns, ambiguous or (name_inns is not None and inns != name_inns)
     if ambiguous:
diff --git a/tests/unit/test_b30_extra.py b/tests/unit/test_b30_extra.py
new file mode 100644
index 0000000..ddb14e2
--- /dev/null
+++ b/tests/unit/test_b30_extra.py
@@ -0,0 +1,103 @@
+"""Extra checks for batch 30: combined `inn` names its ingredient set."""
+
+from decimal import Decimal
+
+import pytest
+
+from anamnesis.core.catalogue import load_catalogue
+from anamnesis.core.reconcile import claim_identity_conflict, pack_identity_conflict, reconcile_pair
+from anamnesis.schema import DiscrepancyType as D
+from anamnesis.schema import IngredientAmount, PackObservation, PatientClaim, Strength
+
+CAT = load_catalogue()
+
+
+def part(inn: str, amount: str) -> IngredientAmount:
+    return IngredientAmount(inn=inn, amount=Decimal(amount), unit="mg")
+
+
+def strength(*parts: IngredientAmount) -> Strength:
+    return Strength(ingredients=list(parts), per="tablet")
+
+
+def claim(
+    name: str, inn: str | None = None, pack_strength: Strength | None = None
+) -> PatientClaim:
+    return PatientClaim(
+        claim_id="c1",
+        name_text=name,
+        inn=inn,
+        strength=pack_strength,
+        status="active",
+        audio_evidence=["turn-0"],
+    )
+
+
+def pack(label: str, inn: str | None = None, pack_strength: Strength | None = None) -> PackObservation:
+    return PackObservation(
+        observation_id="o0",
+        label_text=label,
+        inn=inn,
+        strength=pack_strength,
+        readability="readable",
+        visual_evidence=["r-0"],
+    )
+
+
+AUGMENTIN = strength(part("amoxicillin", "875"), part("clavulanic acid", "125"))
+PANADOL_EXTRA = strength(part("paracetamol", "500"), part("caffeine", "65"))
+
+
+@pytest.mark.parametrize(
+    "inn",
+    [
+        "amoxicillin و clavulanic acid",
+        "clavulanic acid و amoxicillin",
+        "amoxicillin AND clavulanic acid",
+        "amoxicillin And clavulanic acid",
+        "amoxicillin+clavulanic acid",
+        "amoxicillin&clavulanic acid",
+        "amoxicillin,clavulanic acid",
+    ],
+)
+def test_combined_inn_delimiters_name_their_set(inn: str) -> None:
+    observation = pack("Augmentin 875 mg/125 mg", inn, AUGMENTIN)
+    assert not pack_identity_conflict(observation, CAT)
+    assert reconcile_pair(claim("Augmentin", None, AUGMENTIN), observation, CAT).type is D.MATCH
+
+
+def test_each_part_resolves_like_any_inn() -> None:
+    french = pack("Augmentin 875 mg/125 mg", "amoxicilline/acide clavulanique", AUGMENTIN)
+    assert not pack_identity_conflict(french, CAT)
+    alias = pack("Panadol Extra", "acetaminophen/caffeine", PANADOL_EXTRA)
+    assert not pack_identity_conflict(alias, CAT)
+    assert (
+        reconcile_pair(claim("Panadol Extra", None, PANADOL_EXTRA), alias, CAT).type is D.MATCH
+    )
+
+
+def test_combined_inn_matches_any_combination_pack() -> None:
+    observation = pack("Panadol Extra", "caffeine + paracetamol", PANADOL_EXTRA)
+    assert not pack_identity_conflict(observation, CAT)
+    assert (
+        reconcile_pair(claim("Panadol Extra", None, PANADOL_EXTRA), observation, CAT).type
+        is D.MATCH
+    )
+
+
+def test_single_inn_among_combination_strength_is_not_a_conflict() -> None:
+    assert not pack_identity_conflict(pack("Augmentin 875 mg/125 mg", "amoxicillin", AUGMENTIN), CAT)
+    assert pack_identity_conflict(pack("Augmentin 875 mg/125 mg", "paracetamol", AUGMENTIN), CAT)
+
+
+@pytest.mark.parametrize("inn", ["candesartan", "دواء"])
+def test_and_or_waw_inside_a_word_does_not_split(inn: str) -> None:
+    one = strength(part(inn, "8"))
+    assert not pack_identity_conflict(pack(inn, inn, one), CAT)
+    assert pack_identity_conflict(pack("Concor 5 mg", inn, strength(part("bisoprolol", "5"))), CAT)
+
+
+def test_combined_inn_without_strength_mismatch_is_a_conflict() -> None:
+    assert pack_identity_conflict(pack("Augmentin", "amoxicillin/sulbactam"), CAT)
+    assert claim_identity_conflict(claim("Augmentin", "amoxicillin/sulbactam"), CAT)
+    assert not claim_identity_conflict(claim("Augmentin", "amoxicillin/clavulanic acid"), CAT)
```
