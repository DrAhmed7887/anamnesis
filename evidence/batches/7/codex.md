codex gpt-6-sol, batch 7, started 2026-10-27T10:24:47Z

The existing code normalizes only acetaminophen, and catalogue matching special cases that name. I’ll put the curated aliases in the schema, use them for single ingredient catalogue entries, and check differing salts at the formulation gate.
apply patch
patch: completed
<repo>/anamnesis/schema/medication.py
diff --git a/anamnesis/schema/medication.py b/anamnesis/schema/medication.py
index 412f62d6a71e1c1164a5c007658f0c2097db6bc8..5da431716aff114a1c881a3055d578b44b341c27
--- a/anamnesis/schema/medication.py
+++ b/anamnesis/schema/medication.py
@@ -42,10 +42,45 @@
     UNKNOWN = "unknown"
 
 
+INN_ALIASES: dict[str, tuple[str, str | None]] = {
+    "bisoprolol fumarate": ("bisoprolol", "fumarate"),
+    "bisoprolol hemifumarate": ("bisoprolol", "hemifumarate"),
+    "metoprolol succinate": ("metoprolol", "succinate"),
+    "metoprolol tartrate": ("metoprolol", "tartrate"),
+    "amlodipine besilate": ("amlodipine", "besilate"),
+    "amlodipine besylate": ("amlodipine", "besilate"),
+    "amlodipine mesilate": ("amlodipine", "mesilate"),
+    "amlodipine maleate": ("amlodipine", "maleate"),
+    "metformin hydrochloride": ("metformin", "hydrochloride"),
+    "metformin hcl": ("metformin", "hydrochloride"),
+    "atorvastatin calcium": ("atorvastatin", "calcium"),
+    "atorvastatin calcium trihydrate": ("atorvastatin", "calcium trihydrate"),
+    "amoxicillin trihydrate": ("amoxicillin", "trihydrate"),
+    "amoxicillin sodium": ("amoxicillin", "sodium"),
+    "potassium clavulanate": ("clavulanic acid", "potassium"),
+    "clavulanate potassium": ("clavulanic acid", "potassium"),
+    "acetaminophen": ("paracetamol", None),
+}
+
+
+def _inn_and_salt(name: str) -> tuple[str, str | None]:
+    normalised = name.strip().casefold()
+    if normalised.endswith(")") and " (as " in normalised:
+        moiety, alias = normalised[:-1].split(" (as ", 1)
+        mapped = INN_ALIASES.get(alias)
+        if mapped and mapped[0] == moiety:
+            return mapped
+    return INN_ALIASES.get(normalised, (normalised, None))
+
+
 def canonical_inn(name: str) -> str:
     """Normalise an ingredient name for identity comparisons."""
-    normalised = name.strip().casefold()
-    return {"acetaminophen": "paracetamol"}.get(normalised, normalised)
+    return _inn_and_salt(name)[0]
+
+
+def salt_of(name: str) -> str | None:
+    """Return a curated salt for an ingredient name, if one is known."""
+    return _inn_and_salt(name)[1]
 
 
 class IngredientAmount(BaseModel):
@@ -54,9 +89,21 @@
     model_config = ConfigDict(extra="forbid")
 
     inn: NonEmptyStr
+    salt: str | None = None
     amount: Decimal = Field(gt=0)
     unit: Unit
 
+    @model_validator(mode="before")
+    @classmethod
+    def split_inn_and_salt(cls, data: object) -> object:
+        if not isinstance(data, dict) or not isinstance(data.get("inn"), str):
+            return data
+        result = data.copy()
+        result["inn"], inferred_salt = _inn_and_salt(data["inn"])
+        if "salt" not in result:
+            result["salt"] = inferred_salt
+        return result
+
 
 class Strength(BaseModel):
     """Ingredient amounts per tablet, capsule, volume, or dose."""

ERROR: exceeded retry limit, last status: 429 Too Many Requests
ERROR: exceeded retry limit, last status: 429 Too Many Requests
tokens used
25,789
codex exited non-zero
