# Adversarial grill: the plan to the freeze, Spanish and German (29 Oct 2026)

You are an adversarial reviewer of a plan, not of finished code. Anamnesis is a pre-visit medication-intake tool: it reports where a patient's spoken account and the photos of their medicine packs disagree, and it never gives advice. The plan below adds Spanish and German two days before a feature freeze. Find what in it would make the product unsafe or wrong, overclaim in public, run late, or overspend. Every finding must name a plan step and cite the code or SPEC excerpt in this package that shows the problem.

**Worker mode:** skip any session-continuity steps. Don't use tools, and don't read or write files. Everything you need is in this package; answer only from it.

## Attack surfaces, in priority order
1. **Clinical safety of the new number words and release words.** Find any Spanish or German form that would make an amount "stated" when the patient did not state it, so that a model's invented amount survives the stated-amount check. Find any form that would read the wrong value. Cover German compound edge cases; Spanish "y", "un" and "una"; "halb" and "medio"; how the new words interact with the existing run rules and with the English and Arabic tables; and release words that could create a false match or a false conflict.
2. **The two parser fixes**, ingredient grounding and the empty-strength rule. Find any case where they would let a wrong amount or ingredient through, or drop a right one.
3. **The catalogue changes:** release set to unknown, the new entries and the codes. Look for false matches, wrong brand-implied facts, and codes without a provenance.
4. **The live cases.** Are the expected results right by the product's rules as excerpted here? Can any case not test what it claims to test?
5. **Schedule and scope.** What is too big for one builder batch before Friday night? What depends on what, what should be cut first, and what is missing (docs, data handling, tests)?
6. **The public story.** Which claims would the evidence not back?
7. **Spend, data handling and licences:** Meta's card, Modal, the synthetic voices, the public photos, CIMA reuse, the WHO ATC terms, and SNOMED CT in a public repository.

## Output
- A table of at most 15 rows, most severe first: `# | severity (critical/high/medium/low) | surface (1–7) | plan step | the problem, with its evidence from this package | the concrete fix`.
- For each critical or high row, one exact test case (input → expected) that would catch it.
- No praise, no summary and no rewrites of the plan.
- The last line is exactly: `GRILL: N findings (C critical, H high)`.

---

## The plan
# Plan to the freeze: Spanish and German, 29 Oct 2026, 15:30 CET (grilled before Ahmed decides)

## Where things stand
- **`main` at 25a9274:** 2,075 tests pass. The feature freeze is Sat 31 Oct 23:59 CET; submission is Wed 4 Nov by 15:00.
- **The fine-tune:**
  - r1's results are committed (f07e273): Glimmer + LoRA got 290/303 fully right, against Spark 1.3's 193/303.
  - r2 (the same recipe plus 80 Spanish brands from AEMPS CIMA) is trained, and its adapter is on Modal. Its eval hasn't run.
  - Spark 1.3 on `test_spain` (60 notes) is done: $0.80, with its replies saved but not yet committed.
- **The credits, read at their sources today at 14:45:**
  - **Meta:** $35.03 of $150. It ends 4 Nov, and a card is on file, so past $150 the card pays. Our stop line is $75.
  - **Modal:** $8.72 in October, all from credits, $0.00 billed. $342.41 of grants are left, with a $0 spend limit.
  - **Fireworks:** about $99.70.
  - **Baseten:** the $100 grant is unconfirmed, so no calls.
  - **Google:** $2.54 of $50.95.
- **The product today:**
  - It reads English and Egyptian-Arabic speech. Its number words are English and Arabic only (`anamnesis/providers/stated.py`), so "quinientos miligramos" and "fünfhundert Milligramm" state no amount, while "500 mg" does.
  - `catalogue.normalise()` casefolds, keeps accents and umlauts, and turns "ß" into "ss".
  - The release words (`reconcile.py` `_RELEASE_WORDS`) include "retard" and "depot", but no Spanish forms.
  - `scripts/intake_live.py` `LANGUAGES` has only en and ar.
  - The catalogue's 9 entries carry no codes.
  - The public photos include metoprolol 50 mg ratiopharm (DE), bisoprolol 2.5 mg Sandoz (ES) and Sortis 40 mg (atorvastatin, CZ).

## Steps, in order
### 0. r2's eval and write-up (Thu, engine; Modal about $2.50)
- **The run:** `modal run --detach finetune/modal_glimmer.py --step eval --run r2 --jobs glimmer-base@data_v2/test_spain,glimmer-lora-r1@data_v2/test_spain,glimmer-lora-r2@data_v2/test_spain,glimmer-lora-r2@test_iid,glimmer-lora-r2@test_shift,glimmer-lora-r2@test_codeswitch,glimmer-lora-r2@test_real`.
- **The write-up:** `evidence/finetune/summarize.py --table r2` goes into `results.md`, with every miss, and is committed with Spark's `test_spain` replies.

### 1. Batch 24's contract (Thu night, engine; $0)
`scripts/batch.sh start 24 es-de` makes the branch, then one commit "test(contract): batch 24" holds the SPEC lines, `tests/contract/test_b24_*.py` and `briefs/24.md`. The parts:
1. **Ingredient grounding** (`parse_claims_json`):
   - A claim's `inn` must occur, after `normalise`, in a turn it cites, or it becomes null.
   - An amount's label (the intake's `inn`, and each strength ingredient's `inn`) that is empty or doesn't occur becomes the claim's `name_text`.
   - **Contract pins:** test_iid #79's "string" label; an `inn` of "bisoprolol" when only "Concor" was said; a label of "".
2. **An empty strength object** (`"ingredients": []`) is no strength: it doesn't set off the rule that a dropped amount takes the other with it. **Pin:** Spark's reply to test_shift #34 keeps Naprosyn 550 mg.
3. **The catalogue release fix:** Glucophage and Augmentin get release `unknown`, because RxNorm records extended-release products under both brands (`evidence/data/rxnorm_catalogue.md`:43–46). **Pin:** "Glucophage 500 mg" against an XR pack gives `insufficient_information`, not `formulation_mismatch`.
4. **Spanish and German number words** (`stated.py`), with tables keyed by `normalise()` output:
   - **Spanish:**
     - cero to quince, dieciséis to diecinueve, veinte, veintiuno to veintinueve, treinta to noventa;
     - cien and ciento, doscientos to novecientos (with the -as forms), mil;
     - "y" joins a run; "un", "una" and "uno" are 1; "medio" and "media" are a half, so "y medio" adds 0.5.
   - **German:** one-word compounds up to 9,999 are parsed by a small helper:
     - units (ein, eins, eine, einen, zwei to neun), teens (zehn, elf, zwölf, dreizehn to neunzehn, with sechzehn and siebzehn), tens (zwanzig, dreissig to neunzig);
     - "und" inside a word, "hundert", "tausend";
     - "halb", "halbe" and "halben" are a half; "einhalb" and "eineinhalb" are 1.5; "zweieinhalb" and the rest are n + 0.5.
   - **Not numbers,** as English "twice" isn't one: "zweimal", "dreimal", "dos veces", "tres veces".
   - **SPEC §2 lines** say all of this. The contract pins about 20 forms per language, and checks that "ein"/"eine" before a noun reads as 1, the same way English "one" already does.
5. **Release words:** "prolongada", "modificada", "gastrorresistente", "gastrorresistentes", "retardtablette", "retardtabletten", "retardkapsel", "retardkapseln" and "magensaftresistent" join `_RELEASE_WORDS`. They are modified release: Ph. Eur. counts prolonged and delayed release as modified.
6. **The codes:**
   - **The catalogue:** entries gain optional `atc`, `rxcui` (a list) and `snomed_ct`, taken from `evidence/data/drugs_v2.json` `catalogue`. The loader checks the formats: ATC `^[A-Z]\d\d[A-Z][A-Z]\d\d$`, digit strings otherwise.
   - **The brief:** each resolved medicine's row shows "ATC C07AB07 · RxNorm 19484 · SNOMED CT [SNOMED CT id removed]", escaped. An entry without codes shows nothing.
   - **Pins:** Concor and Panadol Extra.
7. **New catalogue entries, all with CIMA's codes:**
   - **Nolotil:** ES, metamizole, capsule, release immediate, splittable null.
   - **Emconcor:** ES, bisoprolol. It's Merck's Spanish name for Concor, per CIMA.
   - **Sortis:** DE/CZ, atorvastatin. It's Pfizer's name for Lipitor, from the Commons photo and CIMA's ATC for atorvastatin.

   All three are marked `synthetic: true`, as the others are. A metamizole RxCUI comes from RxNav, which calls it dipyrone.
8. **The M7 low items,** only if there's room. These are the first cut.

### 2. Batch 24's build (Fri after 16:00, Muse; Meta about $5)
`scripts/batch.sh run 24`, then the gate, the Opus supervisor and round 2 if needed, then the merge. Usage is reported, as for every batch.

### 3. Live Spanish and German cases (Fri night, after the merge; Meta about $0.50)
- **Pre-registered:** the rows go in `evidence/batches/24/manifest.md` before any call.
- **The voices:** macOS `say`, Flo (Spanish, Spain) and Anna (German), for runs only and never in the film.
- **The runner:** `scripts/intake_live.py --lang es|de`, with `LANGUAGES` gaining `"es": ["Spanish"]` and `"de": ["German"]`.

| Case | Voice note | Photo | Expected, by the product's rules |
|---|---|---|---|
| S1 | "Tomo Emconcor cinco miligramos una vez al día." | none | one claim, Emconcor, 5 mg, once a day; `missing_modality` |
| S2 | "Tomo bisoprolol dos coma cinco miligramos por la mañana." | bisoprolol 2.5 mg Sandoz (ES) | `match` |
| S3 | "Tomo Gelocatil de un gramo cuando tengo dolor." | none | 1 g, as needed; `missing_modality` |
| S4 | "Tomo medio comprimido de Panadol de quinientos." | Panadol 500 mg (FI) | half a tablet; strength 500 mg; `match` or the splittability finding the rules give |
| G1 | "Ich nehme Metoprolol fünfzig Milligramm zweimal täglich." | metoprolol 50 mg ratiopharm (DE) | `match` |
| G2 | "Ich nehme morgens eine halbe Tablette Beloc-Zok hundert Milligramm." | none | 0.5 tablets of a 100 mg tablet; `missing_modality` |
| G3 | "Ich nehme Sortis vierzig Milligramm am Abend." | Sortis 40 mg (CZ) | `match` |
| G4 | "Ibuprofen vierhundert habe ich abgesetzt." | none | discontinued, 400 mg |

### 4. Sat
- the Gemini 4 check of batch 24 (Google, about $1);
- the freeze at 23:59;
- the `demo-freeze` tag;
- a clean-checkout live run of the hero, U12 (about $0.04).

### 5. The story (the judge session; Ahmed relays)
- English and Egyptian Arabic are the tested core.
- Spanish and German were added in batch 24 and tested on 8 synthetic-voice cases.
- Spain's official registry (CIMA) feeds the drug data, and `test_spain` measures unseen Spanish brands.
- German brand data is future work: Germany has no open drug registry.

## The cut order if time runs short
1. the M7 low items;
2. the new catalogue entries;
3. the brief's codes, keeping them in the catalogue;
4. live cases S4 and G3.

Never cut: the two parser fixes, the number words with their contract, and r2's write-up.

## Costs, if everything runs
- **Meta:** about $41 of $150 (27%).
- **Modal:** about $12 of grants.
- **Google:** about $3.50.
- **Fireworks and Baseten:** $0.

## Hours
- **The engine:** about 10 across Thu to Sat.
- **Ahmed:** about 15 minutes of approvals, plus a look at dev.meta.ai/billing on Sat.

---

## Package: the code and SPEC the plan touches

### anamnesis/providers/stated.py (whole file)
```python
"""Numbers a source text states, digits or number words (SPEC §2, batch 20)."""

import re
from decimal import Decimal

from anamnesis.core import catalogue
from anamnesis.providers.numbers import parse_amount_text

ENGLISH_NUMBERS: dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

ENGLISH_HUNDRED = frozenset({"hundred"})
ENGLISH_THOUSAND = frozenset({"thousand"})
ENGLISH_HALF = frozenset({"half"})

ARABIC_NUMBERS: dict[str, int] = {
    "واحد": 1, "واحده": 1, "احد": 1,
    "اتنين": 2, "اثنين": 2, "اثنان": 2, "اتنان": 2, "اثنا": 2, "اثني": 2,
    "تلاته": 3, "ثلاثه": 3, "تلات": 3, "ثلاث": 3,
    "اربعه": 4, "اربع": 4,
    "خمسه": 5, "خمس": 5,
    "سته": 6, "ست": 6,
    "سبعه": 7, "سبع": 7,
    "تمانيه": 8, "ثمانيه": 8, "تماني": 8, "ثماني": 8, "تمن": 8, "ثمان": 8,
    "تسعه": 9, "تسع": 9,
    "عشره": 10, "عشر": 10,
    "حداشر": 11, "اتناشر": 12, "تلتاشر": 13, "اربعتاشر": 14, "خمستاشر": 15,
    "ستاشر": 16, "سبعتاشر": 17, "تمنتاشر": 18, "تسعتاشر": 19,
    "عشرين": 20, "عشرون": 20,
    "تلاتين": 30, "ثلاثين": 30, "ثلاثون": 30,
    "اربعين": 40, "اربعون": 40,
    "خمسين": 50, "خمسون": 50,
    "ستين": 60, "ستون": 60,
    "سبعين": 70, "سبعون": 70,
    "تمانين": 80, "ثمانين": 80, "ثمانون": 80,
    "تسعين": 90, "تسعون": 90,
    "ميتين": 200, "مايتين": 200, "مئتين": 200, "مئتان": 200,
    "مائتين": 200, "مائتان": 200,
    "الفين": 2000,
}

ARABIC_HUNDRED = frozenset({"ميه", "مايه", "مائه", "مئه", "ميت"})
ARABIC_THOUSAND = frozenset({"الف", "الاف"})
ARABIC_HALF = frozenset({"نص", "نصف"})

ARABIC_HUNDRED_SUFFIXES = ("مايه", "مائه", "ميه", "مئه")
ARABIC_HUNDRED_STEMS: dict[str, int] = {
    "تلت": 3, "ثلاث": 3, "ربع": 4, "اربع": 4, "خمس": 5, "ست": 6,
    "سبع": 7, "تمن": 8, "ثمان": 8, "تسع": 9,
}

_PLAIN = ENGLISH_NUMBERS | ARABIC_NUMBERS
_HUNDRED = ENGLISH_HUNDRED | ARABIC_HUNDRED
_THOUSAND = ENGLISH_THOUSAND | ARABIC_THOUSAND
_HALF = ENGLISH_HALF | ARABIC_HALF

_DIGIT_RUN = re.compile(r"(?<![\d.,٬])(?>[0-9٠-٩۰-۹]+(?:[.,٬][0-9٠-٩۰-۹]+)?)(?!\d)")
_RUN_BREAK = re.compile(r"[,.;:!?،؛؟\r\n]+")


def _combined_hundreds(word: str) -> int | None:
    """A 300-900 one-word form such as خمسميه (SPEC §2)."""
    for suffix in ARABIC_HUNDRED_SUFFIXES:
        if word.endswith(suffix) and len(word) > len(suffix):
            stem = ARABIC_HUNDRED_STEMS.get(word[: -len(suffix)])
            if stem is not None:
                return stem * 100
    return None


def _classify(token: str) -> tuple[str, int | None]:
    """Kind and plain value of one normalised token."""
    if token in _PLAIN:
        return "plain", _PLAIN[token]
    if token in _HUNDRED:
        return "hundred", 100
    if token in _THOUSAND:
        return "thousand", 1000
    if token in _HALF:
        return "half", None
    if token in ("and", "و"):
        return "and", None
    if token == "point":
        return "point", None
    if token == "a":
        return "a", None
    combined = _combined_hundreds(token)
    if combined is not None:
        return "plain", combined
    if token.startswith("و") and len(token) > 1:
        rest = token[1:]
        if rest in _PLAIN:
            return "plain", _PLAIN[rest]
        if rest in _HUNDRED:
            return "hundred", 100
        if rest in _THOUSAND:
            return "thousand", 1000
        if rest in _HALF:
            return "half", None
        combined = _combined_hundreds(rest)
        if combined is not None:
            return "plain", combined
    return "other", None


def _run_value(words: list[tuple[str, int | None]]) -> Decimal:
    total, current = Decimal(0), Decimal(0)
    for kind, value in words:
        if kind == "plain" and value is not None:
            if value >= 1000:
                total += Decimal(value)
                current = Decimal(0)
            else:
                current += Decimal(value)
        elif kind == "hundred":
            current = (current if current != 0 else Decimal(1)) * 100
        elif kind == "thousand":
            total += (current if current != 0 else Decimal(1)) * 1000
            current = Decimal(0)
        elif kind == "half":
            current += Decimal("0.5")
    return total + current


def _word_values(words: list[tuple[str, int | None]], found: set[Decimal]) -> None:
    for kind, value in words:
        if kind == "plain" and value:
            found.add(Decimal(value))
        elif kind == "hundred":
            found.add(Decimal(100))
        elif kind == "thousand":
            found.add(Decimal(1000))
        elif kind == "half":
            found.add(Decimal("0.5"))


def _close(words: list[tuple[str, int | None]], found: set[Decimal]) -> None:
    if not words:
        return
    value = _run_value(words)
    if value > 0:
        found.add(value)
    _word_values(words, found)
    words.clear()


def _since_thousand(words: list[tuple[str, int | None]]) -> Decimal:
    """Run value after its last thousand word (SPEC §2, batch 21)."""
    start = 0
    for pos, (kind, value) in enumerate(words):
        if kind == "thousand" or (kind == "plain" and value is not None and value >= 1000):
            start = pos + 1
    return _run_value(words[start:])


def _hundred_cut(words: list[tuple[str, int | None]], token: str) -> int:
    """Where a new hundreds group starts; a final 1-9 moves with it."""
    if words and words[-1][0] == "plain" and words[-1][1] is not None:
        if 1 <= words[-1][1] <= 9 and not token.startswith("و"):
            return len(words) - 1
    return len(words)


def _word_amounts(part: str, found: set[Decimal]) -> None:
    """Number-word runs in one punctuation-delimited part (SPEC §2)."""
    tokens = catalogue.normalise(part).split()
    kinds = [_classify(token) for token in tokens]
    words: list[tuple[str, int | None]] = []
    index = 0
    while index < len(tokens):
        kind, value = kinds[index]
        if kind in ("plain", "hundred", "thousand", "half"):
            if kind == "hundred" and _since_thousand(words) >= 100:
                if index > 0 and kinds[index - 1][0] == "a":
                    cut = len(words)
                else:
                    cut = _hundred_cut(words, tokens[index])
                earlier = words[:cut]
                words = words[cut:]
                _close(earlier, found)
            elif kind == "plain" and value is not None and value >= 100:
                if _since_thousand(words) >= 100:
                    _close(words, found)
            words.append((kind, value))
        elif kind == "a":
            if index == 0 or kinds[index - 1][0] != "and":
                _close(words, found)
            # else: filler inside "and a half", the run stays open
        elif kind == "point":
            digits: list[int] = []
            look = index + 1
            while look < len(tokens) and ENGLISH_NUMBERS.get(tokens[look], 10) <= 9:
                digits.append(ENGLISH_NUMBERS[tokens[look]])
                look += 1
            if digits:
                base = _run_value(words)
                value = base + Decimal("0." + "".join(str(d) for d in digits))
                if value > 0:
                    found.add(value)
                _word_values(words, found)
                for digit in digits:
                    if digit:
                        found.add(Decimal(digit))
                words.clear()
                index = look - 1
            else:
                _close(words, found)
        elif kind != "and":
            _close(words, found)
        index += 1
    _close(words, found)


def stated_amounts(text: str) -> frozenset[Decimal]:
    """Every positive number the text states (SPEC §2, batch 20)."""
    found: set[Decimal] = set()
    for match in _DIGIT_RUN.finditer(text.replace("٫", ".")):
        amount = parse_amount_text(match.group(0))
        if amount is not None:
            found.add(amount)
    for part in _RUN_BREAK.split(text):
        _word_amounts(part, found)
    return frozenset(found)
```

### anamnesis/providers/numbers.py: parse_amount_text
```python
"""Parse model-written amount strings into Decimals (SPEC §2, batch 16)."""

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from anamnesis.schema import Strength

_AMOUNT_RE = re.compile(r"[0-9٠-٩۰-۹]+(?:[.,][0-9٠-٩۰-۹]+)?")
_WORD_RE = re.compile(r"(?:[^\W\d_]|ـ)+")


def parse_amount_text(value: object) -> Decimal | None:
    """Return a positive Decimal for one model-written amount, else None.

    ``"2.5"`` and the decimal comma ``"2,5"`` both parse; a comma is a
    decimal mark only when 1-2 digits follow it (``"1,000"`` is ambiguous).
    A dot followed by exactly three digits with a non-zero whole part
    (``"1.000"``) is ambiguous the same way, unless the whole part is zero
    (``"0.125"`` parses). A single number word, the whole amount, parses as
    its value. Ranges, two or more words, empty strings, zero and negatives
    return None.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value if value > 0 else None
    if isinstance(value, int):
        return Decimal(value) if value > 0 else None
    if isinstance(value, float):
        value = str(value)
    if not isinstance(value, str):
        return None
    text = value.strip().replace("٫", ".")
    if not _AMOUNT_RE.fullmatch(text):
        if not _WORD_RE.fullmatch(value.strip()):
            return None
        from anamnesis.core import catalogue
        from anamnesis.providers.stated import ARABIC_NUMBERS, ENGLISH_NUMBERS, _combined_hundreds

        word = catalogue.normalise(value.strip())
        number = ENGLISH_NUMBERS.get(word)
        if number is None:
            number = ARABIC_NUMBERS.get(word)
        if number is None:
            number = _combined_hundreds(word)
        if number is None or number <= 0:
            return None
        return Decimal(number)
    if "," in text:
        head, _, tail = text.partition(",")
        if not 1 <= len(tail) <= 2:
            return None
        text = f"{head}.{tail}"
    elif "." in text:
        head, _, tail = text.partition(".")
        if len(tail) == 3 and int(head) != 0:
            return None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    return number if number > 0 else None

```

### anamnesis/core/catalogue.py: normalise
```python
def normalise(text: str) -> str:
    """Casefold, strip Arabic marks and punctuation, split scripts: the one matching form."""
    text = text.casefold().replace("®", "").replace("™", "")
    text = re.sub(r"[\u0640\u064b-\u065f\u0670]", "", text)
    text = text.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه"}))
    text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789"))
    text = re.sub(r"(?<=[\u0600-\u06ff])(?=[a-z])|(?<=[a-z])(?=[\u0600-\u06ff])", " ", text)
    text = re.sub(r"[^\w\s]|_", " ", text)
    return " ".join(text.split())


ARABIC_CLITICS = r"(?:وال|بال|فال|لل|ال|و|ف|ب|ل)?"
"""Attached Arabic clitics accepted before a matched word (SPEC §2, §3)."""
```

### anamnesis/providers/claims.py: parse_claims_json
```python
def parse_claims_json(text: str, turns: list[AudioTurn]) -> list[PatientClaim]:
    """Validate Spark JSON and attach only cited transcript turns as evidence."""
    try:
        raw_claims = _validate_raw_shape(json.loads(text))
        transcripts = {turn.turn_id: turn.transcript for turn in turns}
        claims = []
        for index, raw in enumerate(raw_claims, start=1):
            _check_no_advice(_advice_strings(raw))
            assert_no_advice_in_ingredients(raw)
            turn_ids = raw["turn_ids"]
            invalid_turn_ids = any(
                not isinstance(turn_id, str) or turn_id not in transcripts for turn_id in turn_ids
            ) if isinstance(turn_ids, list) else True
            if not isinstance(turn_ids, list) or not turn_ids or invalid_turn_ids:
                raise ValueError("claim turn_ids must cite existing turns")
            _check_grounded(raw["name_text"], turn_ids, transcripts)
            strength = (
                coerce_strength(raw["strength"]) if raw["strength"] is not None else None
            )
            intake_amount = _coerce_intake(raw["intake_amount"])
            regimen = _coerce_regimen(raw["regimen"])
            said: set = set()
            for cited in turn_ids:
                said |= stated_amounts(transcripts[cited])
            if isinstance(strength, dict) and not all(
                part["amount"] in said for part in strength["ingredients"]
            ):
                strength = None
            if isinstance(intake_amount, dict) and intake_amount["amount"] not in said:
                intake_amount = None
            units_sent = (
                isinstance(raw.get("regimen"), dict)
                and raw["regimen"].get("units_per_intake") is not None
            )
            units_dropped = units_sent and (
                not isinstance(regimen, dict) or regimen.get("units_per_intake") is None
            )
            if (raw["strength"] is not None and strength is None) or (
                raw["intake_amount"] is not None and intake_amount is None
            ) or units_dropped:
                # A dropped claim amount takes the other one with it (SPEC §2).
                strength = None
                intake_amount = None
            values = {
                **{key: value for key, value in raw.items() if key != "turn_ids"},
                "regimen": regimen,
                "intake_amount": intake_amount,
                "strength": strength,
                "claim_id": f"c{index}",
                "audio_evidence": turn_ids,
            }
            claims.append(PatientClaim.model_validate(values))
        return claims
    except (TypeError, ValueError, ValidationError) as exc:
        raise ProviderError("spark", f"malformed patient claims: {exc}", retryable=True) from exc

```

### anamnesis/core/reconcile.py: release words and the claim release
```python
def _release(
    strength: Strength | None, text: str, catalogue: Catalogue, country: str | None = None
) -> Release:
    if strength and strength.release is not Release.UNKNOWN:
        return strength.release
    return catalogue.implied_release(text, country)


_RELEASE_WORDS = frozenset({
    "retard", "depot", "xr", "xl", "sr", "er", "cr", "mr", "prolonged", "extended",
    "modified", "sustained", "controlled", "slow", "immediate", "ممتد", "بطيء",
    "ممتده", "بطيئه",
})

_ARABIC_RELEASE_WORDS = frozenset({"ممتد", "بطيء", "ممتده", "بطيئه"})


def _says_release(normalised: str) -> bool:
    """A curated release word said as a whole word; Arabic words accept attached clitics."""
    if any(f" {word} " in f" {normalised} " for word in _RELEASE_WORDS - _ARABIC_RELEASE_WORDS):
        return True
    return any(
        re.search(rf"(?<!\w){ARABIC_CLITICS}{re.escape(word)}(?!\w)", normalised)
        for word in _ARABIC_RELEASE_WORDS
    )


def _claim_release(
    claim: PatientClaim, catalogue: Catalogue, pack_release: Release,
) -> Release:
    """A claim's explicit release counts when the claim says so (SPEC §3, C8).

    An unsaid release that agrees with the pack is not trusted: it would
    manufacture a match, so the brand-implied release is used instead. An
    unsaid release that disagrees with the pack still flags a conflict.
    """
    strength = claim.strength
    if strength and strength.release is not Release.UNKNOWN:
        said = _says_release(normalise(claim.name_text))
        if said or catalogue.matches_brand(claim.name_text) or strength.release is not pack_release:
            return strength.release
    return catalogue.implied_release(claim.name_text)


```

### SPEC.md §2: stated amounts and number words
- **`stated_amounts(text) -> frozenset[Decimal]`** (`anamnesis/providers/stated.py`) is every positive number the text states:
  - **Digits.** The same three digit sets count as digits, and `٫` as a dot. Each run of digits, with at most one `.`, `,` or `٬` and more digits after it, and no digit, `.`, `,` or `٬` just before it, is read with `parse_amount_text`. A run never touches a digit of another set, and it is matched as a whole: `"１5"`, `"5５"` and `"1.5５"` state nothing, not 1 (supervisor 21 #6 and round 2 #3). So `"2,5"` is 2.5, `"100mg"` is 100, `"875 mg/125 mg"` is 875 and 125, and the ambiguous `"1,000"` or `"1.000"` states nothing. So do `"١٬٠٠٠"` and `"٢٬٥"`, since `٬` doesn't parse (they used to state 1, or 2 and 5), and `"۵ ملغ"` states 5 (batch 21).
  - **Number words** in English and Egyptian or Modern Standard Arabic, matched on the tokens of `catalogue.normalise(text)` (so `ة` is `ه` and `أ` is `ا`). A word with the Arabic `و` ("and") attached in front counts as the word.
    - English: `zero`–`nineteen` (zero states nothing on its own), `twenty`–`ninety` by tens, `hundred`, `thousand`, `half`.
    - Arabic: 1 `واحد واحده احد`; 2 `اتنين اثنين اثنان اتنان اثنا اثني`; 3 `تلاته ثلاثه تلات ثلاث`; 4 `اربعه اربع`; 5 `خمسه خمس`; 6 `سته ست`; 7 `سبعه سبع`; 8 `تمانيه ثمانيه تماني ثماني تمن ثمان`; 9 `تسعه تسع`; 10 `عشره عشر`; 11–19 `حداشر اتناشر تلتاشر اربعتاشر خمستاشر ستاشر سبعتاشر تمنتاشر تسعتاشر`; the tens 20–90 `عشرين عشرون`, `تلاتين ثلاثين ثلاثون`, `اربعين اربعون`, `خمسين خمسون`, `ستين ستون`, `سبعين سبعون`, `تمانين ثمانين ثمانون`, `تسعين تسعون`; 200 `ميتين مايتين مئتين مئتان مائتين مائتان`; 300–900 as one word, a stem (`تلت ثلاث`, `ربع اربع`, `خمس`, `ست`, `سبع`, `تمن ثمان`, `تسع`) followed by `ميه`, `مايه`, `مائه` or `مئه` (`خمسميه` is 500); 2000 `الفين`. Hundred `ميه مايه مائه مئه ميت`, thousand `الف الاف`, half `نص نصف`.
    - **A run** is consecutive number words, also joined by `and` or `و` (`a` is allowed only after `and`, as in "and a half"). **A run also ends at any of `, . ; : ! ? ، ؛ ؟` or a line break in the raw text** (a hyphen or a slash doesn't end it), so "five, two" states 5 and 2, never 7 (supervisor 20 #5); the digit pass is unaffected. Its value: start with total = current = 0; a plain number adds to current; hundred sets current to (current or 1) × 100; thousand adds (current or 1) × 1000 to total and resets current; half adds 0.5 to current. In English, `point` followed by digit words (`zero`–`nine`) adds them as decimals and ends the run. The run states total + current, and **each of its words also states its own value** (a hundred or thousand word states 100 or 1000, half 0.5).
    - So "five" is 5, "twenty-five" 25, "two hundred and fifty" 250, "two and a half" 2.5, "two point five" 2.5, "خمسة" 5, "خمسين" 50, "خمسه وعشرين" 25, "ميتين وخمسين" 250, "اتنين ونص" 2.5, "تلات ميه" 300 and "خمسمية" 500. "once" and "twice" state nothing.
    - **A second hundreds group starts a new number** (batch 21; round 2, supervisor 21 #1–3).
      - **The trigger:** a hundred word, or a one-word Arabic hundred (`ميتين`, `تلتمية` … `تسعمية`), that comes when the run's value since its last thousand is already 100 or more. It closes the earlier number.
      - **What moves:** only a final plain word worth 1–9, just before a hundred word, goes with the new number as its multiplier ("… one hundred", "… وتلات مية"). Nothing moves when the hundred word carries its own `و` ("ومية").
      - **Examples:**
        - "eight hundred seventy-five (and) one hundred twenty-five" states 875 and 125, never 876 or 87625;
        - "خمسمية وتلات مية" states 500 and 300, never 503;
        - "خمسمية وميتين" states 500 and 200, never 700;
        - "تمنمية خمسة وسبعين ومية خمسة وعشرين" states 875 and 125.

### SPEC.md §3: reconciliation rules and the catalogue
- The `formulation_mismatch` note names both causes: **"Reported and pack formulations differ (salt or release form)."** It used to say "release forms differ" even when only the salts did (QM M4 code #5; batch 19.1). Its patient question asks about both as well: **"What salt or release form is shown on your medicine pack?"** (QM M4 code round 2 #4; batch 21).

### Identity of one side
- Every ingredient field uses one resolver: a known catalogue moiety is canonicalised with `canonical_inn`; otherwise a name resolving to a single-INN catalogue entry resolves to that INN; otherwise the canonicalised input stays unchanged (unknown names remain unknown).
- **Identity set:** the resolved INNs of `strength.ingredients` if a strength exists. Otherwise the resolved scalar `{inn}`, otherwise the INNs of the catalogue entry that `name_text` (or `label_text`) resolves to.
- If a side has a strength and a resolvable name, or (when strength is absent) a scalar `inn` and a resolvable name, and their INN sets differ, that is an extraction conflict and the result is `insufficient_information`.
- When a side has both a strength and a scalar `inn`, the `inn`'s resolved moiety must be in the strength's ingredient set, otherwise it is an extraction conflict. A salt form of the same moiety is not.
- **Brand-implied facts** (`release`, `splittable`) come from the catalogue only when the text matched a **brand** name, never an INN. "Beloc-Zok" implies modified release; "metoprolol" implies nothing.
- **A text that names 2+ different catalogue products** (`name_text` or `label_text`, e.g. a label read as "Beloc-Zok 100 mg Concor 5 mg") is an extraction conflict on that side, even when the side's identity comes from its strength. (C4; batch 17)
- **Claim-side release is trusted only when the claim says so** (C8; batch 17): a claim's explicit `strength.release` counts only if `name_text` contains a curated release word (whole word after `normalise`: `retard`, `depot`, `xr`, `xl`, `sr`, `er`, `cr`, `mr`, `prolonged`, `extended`, `modified`, `sustained`, `controlled`, `slow`, `immediate`, `ممتد`, `بطيء`, and the feminine `ممتدة`, `بطيئة` (matched after `normalise`, which writes them `ممتده`, `بطيئه`; QM M4 #3, batch 19.1); the Arabic words also with the attached clitics `ال`, `وال`, `بال`, `فال`, `لل`, `و`, `ف`, `ب`, `ل`) or matches a catalogue brand. An unsaid explicit release still counts when it **disagrees** with the pack, so it can raise `formulation_mismatch`, but never when it agrees: then the claim's release is the brand-implied one (usually `unknown`), so a guessed release can't make a `match`. (Batch 17: the older contracts, b3 `release_ir_vs_er` and b10 `f01b`, keep a bare-name `immediate` claim against a modified pack as `formulation_mismatch`.) Pack-side release is read from the label and trusted as before.

### Decision order for one claim and one pack (`reconcile_pair`)
The first rule that applies wins.
1. Pack `partial` or `unreadable` → `unreadable_source`.
2. Either identity set can't be built → `unresolved_name`.
3. Extraction conflict on either side → `insufficient_information`. This includes one side naming two different salts of the same ingredient (checked here, before any cross-side comparison, even if the other side names no salt).
4. The identity sets differ → `ingredient_mismatch`.
5. The claim's status is `discontinued` → `discontinued_but_present`.
6. **Known formulation conflicts:** named salts for the same canonical ingredient differ, or both release forms (explicit, otherwise brand-implied) are known and differ → `formulation_mismatch`. Salts for each side come from one shared path: strength ingredients, `intake_amount` (claim only), `salt_of(inn)` and whole-word curated salt aliases found in `name_text` / `label_text` after `catalogue.normalise` (a longer alias suppresses a shorter one it contains).
7. Both sides have a strength: compare amounts in mg (g ×1000, mcg ×0.001; `ml` and `iu` only against the same unit). When the claim names no salt, curated pack salt-basis equivalents compare against the nominal amount for both strength and intake. A stated tablet strength is exact: it matches the literal pack amount or the nominal amount, never a multiple or fraction of either; only intakes use the 0.5, 2, 3 and 4 dose ratios. Formulation checks still apply first. Unequal → `strength_mismatch` or `ratio_mismatch`.
8. The claim has an `intake_amount` and the pack strength has more than one ingredient → `insufficient_information` (a single amount can't be checked against a combination; strength-only combination claims still compare under rule 7). Otherwise, when the claim has an `intake_amount` (also when 7 found equal strengths): compare its INN, resolved by the same ingredient resolver, with a single-ingredient pack strength; a mismatch → `insufficient_information`.
   - `per` ∉ {tablet, capsule} → `insufficient_information`.
   - Compute r = intake / unit strength. r = 1 → continue.
   - r ∈ {2, 3, 4} → `intake_differs_from_unit_strength`.
   - r = 0.5 on a tablet. Splittability is per product, because some scored ER tablets such as Beloc-Zok may be halved: `splittable: true` → `intake_differs_from_unit_strength`; `false`, or a capsule → `strength_mismatch`; unknown → `insufficient_information`.
   - Otherwise → `strength_mismatch`.
   - **Units per intake (C1, batch 17).** When `regimen.units_per_intake` = u with u ≠ 1, u is the ratio r against one pack unit and the same mapping applies (`per` ∉ {tablet, capsule} → `insufficient_information`; u ∈ {2, 3, 4} → `intake_differs_from_unit_strength`; u = 0.5 → by splittability as above; any other u → `strength_mismatch`). This runs after rule 7 found equal strengths (or the claim has no strength) and after an `intake_amount` comparison came out at r = 1 (or there is none): a model often copies the tablet strength into `intake_amount` for "half of the 20 mg", so the intake alone can't rule the units out (supervisor 17 #1). It never produces `match` and doesn't count as a comparison for rule 9. ("Half of the 20 mg Lipitor": strength 20 + u 0.5 against non-splittable Lipitor 20 → `strength_mismatch`, was `match`.)
9. No amount comparison was possible on either rule 7 or rule 8 → `insufficient_information`.
10. One release is `modified` and the other is `unknown` → `insufficient_information`.
11. Otherwise → `match`.

### Pairing (`reconcile_all`)
- Only readable packs can pair. Candidate pairs have overlapping identity sets.
- Score each candidate: 3 = same identity and equal strength, 2 = same identity, 1 = overlap. **A claim with no strength whose intake amount reconciles as `match` with the pack scores 3 as well** (batch 21). Live, 28 Oct, "Norvasc 5 mg in the evening" against a 10 mg box and a 5 mg box tied at 2. The tie went to the 10 mg box by id, so the 5 mg box was reported as not mentioned (staged case U5).
- **A named brand is compared with its own pack first** (batch 19): before the score, a pair whose claim `name_text` and pack `label_text` match the same catalogue brand comes first. With Panadol and Gelocatil both paracetamol, ID order alone could pair Panadol's claim with Gelocatil's pack. Ranking by score first could pair "Panadol 1 g" with an equal-strength Gelocatil 1 g pack and hide that the Panadol pack says 500 mg (supervisor 19 #4).
- Take candidates greedily by that preference, then score, then `claim_id`, then `observation_id`. Ties are broken by **ID**, not by list position, so the set of findings doesn't depend on the order of claims or packs. Findings come back sorted by `finding_id`.
- Leftovers:
  - an unreadable pack → `unreadable_source`
  - an unresolvable name → `unresolved_name`
  - otherwise → `missing_modality`

### Catalogue resolution
- `-` and `/` count as spaces and matching is on whole words. Each match records its character span; a match is suppressed only when its span is contained inside a longer match's span. Brand matches also cover INN or alias matches whose INN sets are within the brand's INNs. Text that names 2+ different brands or products → `None`; INN/alias-only matches sharing one INN set resolve deterministically by brand name.
- Arabic names remove diacritics and tatweel, normalize alef/ya/ta marbuta and Arabic-Indic digits, split Arabic/Latin boundaries, and accept the attached clitics `ال`, `وال`, `بال`, `فال`, `لل`, `و`, `ف`, `ب` and `ل`; curated Arabic brand aliases retain the brand's release and splittability.
- The country is a preference, never a filter: candidate entries sort country-match first (case-insensitive), then by brand, so the result is deterministic.
- Entries carry `release` and `splittable` (`true`, `false` or `null`). All entries are synthetic.

## 4. Agent loop (`anamnesis/agent/`, batches 14 and 15.5)
`run_intake(audio, images, ...)` runs a **fixed order**; no model chooses actions, nothing a model wrote is surfaced except source data (transcripts, label text), and there are no outer retries (adapters retry once themselves).
0. **Prepare** every photo before any model sees it (`prepare_image(data, mime) -> (data, mime)`, `anamnesis/agent/media.py`). Phones store the pixels sideways and record the turn in EXIF; SAM applies it and Spark does not (live, 27 Oct: on a portrait photo, 2 of 3 labels were read from the wrong pack). Preparation turns the pixels upright for every EXIF orientation (1–8) and drops all metadata (EXIF including GPS and camera tags, XMP, IPTC, ICC profiles, comments, PNG text chunks, and any extra frames such as an HDR gain map), so SAM, Spark, the crop and the brief see the same pixels and no location leaves the machine. A JPEG or PNG that is already upright and carries none of these is returned byte for byte. Otherwise a JPEG (including a multi-picture MPO, primary frame only) is re-encoded as JPEG (quality 95, 4:4:4 chroma), and anything else as PNG. Preparation is deterministic and idempotent; region hashes and `intake_id` use the prepared bytes, and callers that show a photo (the brief) show the prepared bytes. Bytes that can't be decoded raise `ValueError`; the loop then logs one `segment` step `error: image cannot be decoded` with no call ids, sends that photo to no model, and goes on with the next.
1. `transcribe` if there is audio. 2. `extract_claims` if there are turns.

### anamnesis/core/catalogue.yaml (all entries)
```yaml
- brand: Concor
  aliases: [كونكور]
  release: immediate
  splittable: true
  inns: [bisoprolol]
  countries: [DE, ES, GB]
  synthetic: true
- brand: Beloc-Zok
  aliases: [بيلوك زوك, بلوك زوك]
  release: modified
  splittable: true
  inns: [metoprolol]
  countries: [DE, ES, GB]
  synthetic: true
- brand: Norvasc
  aliases: [نورفاسك]
  release: immediate
  splittable: null
  inns: [amlodipine]
  countries: [DE, ES, GB]
  synthetic: true
- brand: Glucophage
  aliases: [جلوكوفاج]
  release: immediate
  splittable: null
  inns: [metformin]
  countries: [DE, ES, GB]
  synthetic: true
- brand: Panadol
  aliases: [بنادول, بانادول]
  release: immediate
  splittable: null
  inns: [paracetamol]
  countries: [DE, ES, GB]
  synthetic: true
- brand: Panadol Extra
  aliases: [بنادول اكسترا, بانادول اكسترا]
  release: immediate
  splittable: null
  inns: [paracetamol, caffeine]
  countries: [DE, ES, GB]
  synthetic: true
- brand: Augmentin
  aliases: [اوجمنتين]
  release: immediate
  splittable: false
  inns: [amoxicillin, clavulanic acid]
  countries: [DE, ES, GB]
  synthetic: true
- brand: Lipitor
  aliases: [ليبيتور]
  release: immediate
  splittable: false
  inns: [atorvastatin]
  countries: [DE, ES, GB]
  synthetic: true
- brand: Gelocatil
  aliases: [جيلوكاتيل, جلوكاتيل]
  release: immediate
  splittable: null
  inns: [paracetamol]
  countries: [ES]
  synthetic: true
```

### docs/DATA_HANDLING.md (the rules on where media and text may go)
# Data handling for the staged real-media tests (batch 21)

Until now, Anamnesis has run only on synthetic media: rendered photos and macOS text-to-speech voices. Batch 21 adds the first real phone photos and a real human voice. This note sets the rules before anything is recorded (supervisor review of 27 Oct, item 9). It covers every photo and voice note used in tests, the demo and the video.

## What may be recorded
- **Packs.** Real medicine boxes and blister strips, photographed on a plain surface.
  - Prefer over-the-counter packs that Ahmed bought himself. Never use a family member's current prescription.
  - No pack with a pharmacy dispensing label, unless the label is fully covered with paper before the photo is taken. Covering means covering, not blurring afterwards.
- **Voice.** Only Ahmed's own voice, reading a fictional script.
  - The patient in the script is invented: the medicines, amounts and history are nobody's real history, Ahmed's included.
  - No other voices: no family, no children, no background conversation or TV.
- Ahmed records everything on his own phone and consents to sending it to Meta's Model API, as described below.

## What must never be in a photo or a recording
- Names, addresses, dates of birth, phone numbers, prescription or insurance numbers, pharmacy or prescriber names.
- Faces or other people, children, documents, screens, mail, house numbers, or anything that shows where the photo was taken.
- Real symptoms or diagnoses of a real person.

If something slips in, the file is retaken, never edited afterwards.

## Where the files live
- **Raw files** go to `evidence/raw/media/real/` on the Pro. That folder is git-ignored: no raw photo or recording is committed, synced to Drive or put in Notion.
- **Photos.** Before any model sees a photo, the pipeline turns it upright and strips all its metadata, GPS included (SPEC §4 step 0). Turning off Location for the camera is still recommended. iPhone HEIC files are converted to JPEG locally with `sips`.
- **Voice notes** are converted locally to 16 kHz mono WAV with their metadata removed (`ffmpeg -map_metadata -1`), the only format Voice Transcribe accepts. From 28 Oct, `scripts/intake_live.py` also re-writes each WAV to its audio frames alone before any call, so a skipped conversion step can't send a metadata chunk.
- **Deletion:** after judging, on Ahmed's word, the raw files move to the Trash.

## What leaves the machine
- **Only to Meta's Model API**, on Ahmed's account:
  - the prepared photo and the crops cut from it, to SAM 3.1 and Muse Spark 1.3;
  - the WAV, to Muse Voice Transcribe.
- **Standard models only**, never a `*-contributor` id. Meta's pricing page says contributor mode lets Meta train on prompts, files and responses. Our notes (`docs/muse/`) don't record what Meta keeps in standard mode, so anything sent counts as having left our control.
- **Public test photos only, for the open-weight comparison (batch 22) and the intake with Spark Open as its label reader (28 Oct, Ahmed's yes):** the Wikimedia Commons and Cairo University CC BY photos may also go to Fireworks or Baseten, to be read by Meta's open-weight Muse Spark Open. `scripts/intake_live.py --reader baseten` refuses any other photo before the first call. **Ahmed's own photos and voice never go there.**
- **The Glimmer fine-tune (29 Oct, Ahmed's call):** the generated fine-tune data (`finetune/data/` and `finetune/data_v2/`, whose Spanish brand names come from AEMPS's public CIMA registry), with the 33 synthetic-voice transcripts of its real slice, may go to Modal, where Meta's open-weight Muse Glimmer is trained and run. Its weights come from the Hugging Face Hub, and nothing goes to the Hub. No photo, no audio and nothing of Ahmed's goes to Modal.
- **The reviewers never see the media.** The batch supervisor (Claude) and the quality manager (Gemini) get code and text evidence only.

## What is committed or published
- **Committed:**
  - the expected results, written down before any model sees a file;
  - the transcripts of the fictional scripts;
  - each run's findings, cost and latency;
  - the summary tables.
- **Never committed:** photos, audio, crops, or a clinician brief that embeds them. Briefs stay in `evidence/raw/briefs/`.
- **Published only with Ahmed's yes:** a hosted demo brief or video that uses his voice or the real photos needs his explicit yes for that file.

## How results are reported
- As staged tests with real packaging and a fictional history. They are not a validation, not clinical use, and involve no real patient.
- The expected results come first, and every run is reported as it came out (correct, wrong or missed), failures included.
- Spend is capped at $1 on the Meta ledger for all staged runs (`SpendGuard`), and each intake has its own session cap.

### Fact sheet
- `scripts/intake_live.py`: `LANGUAGES = {"en": ["English"], "ar": ["Arabic", "English"]}`; it passes `language_bias=LANGUAGES[lang]` and `lang_hint=lang` to Voice Transcribe.
- r1 eval (29 Oct): Glimmer + LoRA 290/303 fully right, 0 harmful; Spark 1.3 193/303, 1 harmful (an intake labelled "string"); base Glimmer 50/303, 54 harmful. Post-hoc: rewriting only empty strength objects and empty or ungrounded labels in Spark's 303 replies keeps 23 more intakes, loses none, takes Spark to 203/303 and clears the harmful label.
- AEMPS CIMA (Spain) is a public REST API whose records carry SNOMED CT VTM ids and ATC codes. WHO Collaborating Centre terms for ATC: "Use of all or parts of the material requires reference to the WHO Collaborating Centre for Drug Statistics Methodology. Copying and distribution for commercial purposes is not allowed. Changing or manipulating the material is not allowed." Germany has no open drug registry API.
- The repository goes public at submission (4 Nov). The video uses no synthetic voice (macOS licence).
