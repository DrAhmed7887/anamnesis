"""RxNorm drug vocabulary for the fine-tune's training-data generator: 60 INNs, every fact from RxNorm.

    .venv/bin/python scripts/rxnorm_drugs.py [--offline]

Writes evidence/data/rxnorm_drugs.json and .md. Only NLM's public RxNav REST API is called, and it receives
drug names and RxCUIs only. The cached, rate-limited client of scripts/rxnorm_ground.py is reused, so every
response lands in evidence/raw/rxnorm/ (git-ignored) and a rerun makes no calls. That script's own output is
untouched.

For each INN in DRUGS:
- Ingredient: looked up as written (exact, then normalized), then once under its US name from US_NAMES. The
  RxNorm name is kept, so "paracetamol" shows as acetaminophen.
- Clinical drugs: related.json?tty=BN+SCD gives the brands and the clinical drugs (SCD). Kept are the
  single-ingredient SCDs whose dose form RxNorm files under its group "Oral Product"
  (related.json?rela=inverse_isa), and that are marketed: RxNorm's attributes (allProperties) say
  HUMAN_DRUG and PRESCRIBABLE = Y. RxNorm also holds veterinary and discontinued products, and those are
  left out. The strength read from the name must agree with RxNorm's own AVAILABLE_STRENGTH. Combinations,
  non-oral forms and mass-per-mass strengths (MG/MG, for powders, pastes and gels) are left out and counted.
- Strengths: the distinct strengths of the kept SCDs, per-dose units before concentrations. If there are more
  than MAX_STRENGTHS, the ones found in the most RxNorm products (SCDs plus branded drugs) are kept.
- Brands: the BN concepts of that call that have a branded drug (related.json?tty=SBD) of a kept SCD, and
  that RxNorm says is marketed. Brands with the most such drugs come first, then the older RxCUI.
  MAX_BRANDS at most.
Nothing is guessed: a name that does not parse, or a brand with no BN concept, is recorded, not dropped.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from itertools import islice

import rxnorm_ground as rg

# fmt: off
DRUGS = (
    "amlodipine", "bisoprolol", "metoprolol", "atenolol", "carvedilol",
    "lisinopril", "enalapril", "ramipril", "losartan", "valsartan",
    "candesartan", "hydrochlorothiazide", "furosemide", "spironolactone", "indapamide",
    "atorvastatin", "rosuvastatin", "simvastatin", "ezetimibe", "metformin",
    "gliclazide", "glimepiride", "sitagliptin", "empagliflozin", "dapagliflozin",
    "levothyroxine", "omeprazole", "pantoprazole", "esomeprazole", "acetylsalicylic acid",
    "clopidogrel", "warfarin", "apixaban", "rivaroxaban", "paracetamol",
    "ibuprofen", "diclofenac", "naproxen", "amoxicillin", "azithromycin",
    "ciprofloxacin", "metronidazole", "doxycycline", "cetirizine", "loratadine",
    "montelukast", "prednisolone", "allopurinol", "colchicine", "tamsulosin",
    "sertraline", "escitalopram", "fluoxetine", "amitriptyline", "gabapentin",
    "pregabalin", "tramadol", "alendronic acid", "terbinafine", "famotidine",
)
# fmt: on
# The fallback for an INN that RxNorm does not resolve as written: INN to the RxNorm name. In the 05-Oct-2026
# release all 60 resolve as written, so none was used. These three differ from their RxNorm name, and each US
# name was checked to land on the same ingredient.
US_NAMES = {
    "acetylsalicylic acid": "aspirin",
    "alendronic acid": "alendronate",
    "paracetamol": "acetaminophen",
}
OUT = rg.OUT
ORAL_GROUP = "Oral Product"
MAX_BRANDS = 3
MAX_STRENGTHS = 6
# "[descriptors] ingredient strength unit dose form", for example
# "Modified 24 HR metformin hydrochloride 500 MG Extended Release Oral Tablet". A leading "24 HR" or "100 ML"
# is a duration or quantity, and a "24 HR" in the middle of the name is not a strength either.
PRODUCT = re.compile(
    r"(?:\d+(?:\.\d+)? [A-Z]+ )?(?P<ingredient>.+?) "
    r"(?P<value>\d+(?:\.\d+)?) (?P<unit>(?!HR )[A-Z%][A-Z0-9%/]*) (?P<form>.+)"
)
STRENGTH_UNIT = re.compile(r"(?:MG|MCG|G|UNT|MEQ)(?:/ML)?")  # per dose, or per mL of a liquid
# A branded drug's name ends in its brand: "amlodipine 5 MG Oral Tablet [Norvasc]".
BRAND = re.compile(r" \[([^\[\]]+)\]$")
KINDS = ("oral", "combination", "non_oral", "other_unit", "unparsed", "not_marketed", "strength_mismatch")


def oral_forms(rx: rg.RxNav) -> frozenset[str]:
    """The dose forms RxNorm files under its dose form group 'Oral Product'."""
    concepts, _ = rg.find(rx, ORAL_GROUP)
    groups = [c for c in concepts if c["tty"] == "DFG" and c["name"] == ORAL_GROUP]
    if len(groups) != 1:
        raise rg.RxNavError(f"expected one dose form group named {ORAL_GROUP!r}, found {len(groups)}")
    body = rx.get(f"rxcui/{groups[0]['rxcui']}/related.json", rela="inverse_isa")
    try:
        found = (body.get("relatedGroup") or {}).get("conceptGroup") or []
        members = [c for g in found if g["tty"] == "DF" for c in g.get("conceptProperties") or []]
        forms = frozenset(c["name"] for c in members)
    except KeyError as err:
        raise rg.RxNavError(f"the members of {ORAL_GROUP!r} lack {err}") from err
    if not forms:
        raise rg.RxNavError(f"RxNorm lists no dose forms under {ORAL_GROUP!r}")
    return forms


def attributes(rx: rg.RxNav, rxcui: str) -> dict[str, list[str]]:
    """RxNorm's attributes of a concept by name, for example {'PRESCRIBABLE': ['Y'], 'HUMAN_DRUG': ['US']}."""
    if not rxcui.isdigit():
        raise rg.RxNavError(f"unexpected RxCUI {rxcui!r}")
    body = rx.get(f"rxcui/{rxcui}/allProperties.json", prop="ATTRIBUTES")
    found: dict[str, list[str]] = defaultdict(list)
    try:
        for prop in (body.get("propConceptGroup") or {}).get("propConcept") or []:
            found[prop["propName"]].append(prop["propValue"])
    except KeyError as err:
        raise rg.RxNavError(f"attributes of RxCUI {rxcui} lack {err}") from err
    return dict(found)


def marketed(rx: rg.RxNav, rxcui: str) -> dict[str, list[str]] | None:
    """The attributes of a human drug that RxNorm lists as currently prescribable, else None."""
    found = attributes(rx, rxcui)
    return found if "HUMAN_DRUG" in found and found.get("PRESCRIBABLE") == ["Y"] else None


def strength_agrees(found: dict[str, list[str]], value: str, unit: str) -> bool:
    """RxNorm's AVAILABLE_STRENGTH says what the name says (it may add '(expressed as ...)')."""
    text = f"{value} {unit}"
    return any(s == text or s.startswith(f"{text} (") for s in found.get("AVAILABLE_STRENGTH", []))


def classify(name: str, oral: frozenset[str]) -> tuple[str, tuple[str, str, str] | None]:
    """One clinical drug name: why it is left out, or ('oral', (value, unit, dose form)) when it passes."""
    if " / " in name:
        return "combination", None
    found = PRODUCT.fullmatch(name)
    if not found:
        return "unparsed", None
    value, unit, form = found["value"], found["unit"], found["form"]
    if form not in oral:
        return "non_oral", None
    if not STRENGTH_UNIT.fullmatch(unit):
        return "other_unit", None
    return "oral", (value, unit, form)


def screen(rx: rg.RxNav, scds: list[dict], oral: frozenset[str]) -> tuple[list[dict], Counter, list[str]]:
    """Sort an ingredient's clinical drugs: those kept, a count by fate, and the names that did not parse."""
    kept, fates, unparsed = [], Counter(), []
    for drug in scds:
        fate, product = classify(drug["name"], oral)
        if product:
            found = marketed(rx, drug["rxcui"])
            if found is None:
                fate = "not_marketed"
            elif not strength_agrees(found, product[0], product[1]):
                fate = "strength_mismatch"
            else:
                kept.append({**drug, "value": product[0], "unit": product[1], "form": product[2]})
        if fate == "unparsed":
            unparsed.append(drug["name"])
        fates[fate] += 1
    return kept, fates, unparsed


def _order(strength: dict) -> tuple[bool, str, Decimal]:
    return "/" in strength["unit"], strength["unit"], Decimal(strength["value"])


def strengths_of(kept: list[dict], branded: list[dict]) -> list[dict]:
    """Distinct strengths in display order, with their dose forms, SCDs and RxNorm product count."""
    by_name = {drug["name"]: drug for drug in kept}
    branded_at: Counter[tuple[str, str]] = Counter()
    for drug in branded:
        suffix = BRAND.search(drug["name"])
        base = by_name.get(drug["name"][: suffix.start()]) if suffix else None
        if base:
            branded_at[(base["value"], base["unit"])] += 1
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for drug in kept:
        groups[(drug["value"], drug["unit"])].append(drug)
    rows = [
        {
            "strength": f"{value} {unit}",
            "value": value,
            "unit": unit,
            "dose_forms": sorted({drug["form"] for drug in group}),
            "products": len(group) + branded_at[(value, unit)],
            "scd": [{"rxcui": drug["rxcui"], "name": drug["name"]} for drug in group],
        }
        for (value, unit), group in groups.items()
    ]
    return sorted(rows, key=_order)


def most_common(strengths: list[dict]) -> list[dict]:
    """The MAX_STRENGTHS strengths found in the most RxNorm products, kept in display order."""
    best = sorted(strengths, key=lambda s: -s["products"])[:MAX_STRENGTHS]  # a stable sort: ties keep order
    return sorted(best, key=_order)


def pick_brands(
    rx: rg.RxNav, brands: list[dict], branded: list[dict], kept: list[dict]
) -> tuple[list[dict], list[str]]:
    """The best MAX_BRANDS brands with a marketed branded drug of a kept SCD, and brand names with no BN."""
    names = {drug["name"] for drug in kept}
    drugs: dict[str, list[dict]] = defaultdict(list)
    for drug in branded:
        suffix = BRAND.search(drug["name"])
        if suffix and drug["name"][: suffix.start()] in names:
            drugs[suffix.group(1).casefold()].append(drug)
    by_name = {brand["name"].casefold(): brand for brand in brands}
    ranked = sorted(
        (key for key in drugs if key in by_name),
        key=lambda key: (-len(drugs[key]), int(by_name[key]["rxcui"]), key),
    )
    verified = (key for key in ranked if any(marketed(rx, d["rxcui"]) for d in drugs[key]))  # lazy
    chosen = list(islice(verified, MAX_BRANDS))
    return [by_name[key] for key in chosen], sorted(key for key in drugs if key not in by_name)


def resolve(rx: rg.RxNav, inn: str) -> dict:
    """The INN as an RxNorm ingredient, as written first and under its US name second."""
    names = [inn, US_NAMES[inn]] if inn in US_NAMES else [inn]
    reasons = []
    for name in names:
        hit, reason = rg.lookup_ingredient(rx, name)
        if hit:
            return {
                "inn": inn,
                "status": "mapped",
                "rxcui": hit["in"]["rxcui"],
                "tty": "IN",
                "rxnorm_name": hit["in"]["name"],
                "match": hit["match"],
                "us_name_used": None if name == inn else name,
                "pin": hit["pin"],
                "reason": None,
            }
        reasons.append(reason)
    return {
        "inn": inn,
        "status": "unmapped",
        "rxcui": None,
        "tty": None,
        "rxnorm_name": None,
        "match": None,
        "us_name_used": names[-1] if len(names) > 1 else None,
        "pin": None,
        "reason": "; ".join(reasons),
    }


def build_drug(rx: rg.RxNav, inn: str, oral: frozenset[str]) -> dict:
    """One INN's record: the ingredient, up to MAX_BRANDS brands, up to MAX_STRENGTHS oral strengths."""
    ingredient = resolve(rx, inn)
    if ingredient["status"] != "mapped":
        return {
            **ingredient,
            "brands": [],
            "oral_strengths": [],
            "oral_strengths_total": 0,
            "oral_dose_forms": [],
            "scd_counts": dict.fromkeys(("total", *KINDS), 0),
            "unparsed_names": [],
            "brand_names_without_bn": [],
        }
    listed = rg.related(rx, ingredient["rxcui"], "BN", "SCD")
    branded = rg.related(rx, ingredient["rxcui"], "SBD")["SBD"]
    kept, fates, unparsed = screen(rx, listed["SCD"], oral)
    strengths = strengths_of(kept, branded)
    brands, unmatched = pick_brands(rx, listed["BN"], branded, kept)
    return {
        **ingredient,
        "brands": brands,
        "oral_strengths": most_common(strengths),
        "oral_strengths_total": len(strengths),
        "oral_dose_forms": sorted({drug["form"] for drug in kept}),
        "scd_counts": {"total": len(listed["SCD"]), **{kind: fates[kind] for kind in KINDS}},
        "unparsed_names": unparsed,
        "brand_names_without_bn": unmatched,
    }


def ground(rx: rg.RxNav) -> dict:
    """Look every INN up and gather the records with their counts."""
    oral = oral_forms(rx)
    drugs = [build_drug(rx, inn, oral) for inn in DRUGS]
    version = rx.get("version.json")
    dates = sorted(rx.dates)
    mapped = [d for d in drugs if d["status"] == "mapped"]
    meta = {
        "script": "scripts/rxnorm_drugs.py",
        "api": rg.BASE,
        "rxnorm_release": version.get("version"),
        "api_version": version.get("apiVersion"),
        "retrieved": dates[0] if len(dates) == 1 else f"{dates[0]} to {dates[-1]}",
        "oral_dose_forms_in_rxnorm": sorted(oral),
        "marketed_rule": "attribute HUMAN_DRUG present and PRESCRIBABLE = Y",
        "limits": {"brands": MAX_BRANDS, "strengths": MAX_STRENGTHS},
        "inn_us_name_table": dict(US_NAMES),
        "inn_us_name_used": {d["inn"]: d["us_name_used"] for d in mapped if d["us_name_used"]},
        "counts": {
            "inns": len(drugs),
            "mapped": len(mapped),
            "unmapped": len(drugs) - len(mapped),
            "with_brand": sum(bool(d["brands"]) for d in drugs),
            "brands": sum(len(d["brands"]) for d in drugs),
            "with_oral_strength": sum(bool(d["oral_strengths"]) for d in drugs),
            "strengths": sum(len(d["oral_strengths"]) for d in drugs),
            "capped": sum(d["oral_strengths_total"] > MAX_STRENGTHS for d in drugs),
            "dose_forms": len({form for d in drugs for form in d["oral_dose_forms"]}),
            "scd": {kind: sum(d["scd_counts"][kind] for d in drugs) for kind in ("total", *KINDS)},
        },
    }
    return {"meta": meta, "drugs": drugs}


def _list(names: list[str]) -> str:
    return ", ".join(f"`{name}`" for name in names) or "none"


def _md_head(meta: dict) -> list[str]:
    counts, limits = meta["counts"], meta["limits"]
    return [
        "# Drug vocabulary from RxNorm",
        "",
        f"`{meta['script']}` takes {counts['inns']} INNs and records, from RxNorm only, each one's "
        f"ingredient, up to {limits['brands']} brands, up to {limits['strengths']} oral strengths and "
        "the oral dose forms. Machine-readable twin: `rxnorm_drugs.json`, which pairs each strength "
        "with its dose forms and the RxNorm clinical drugs behind it.",
        "",
        f"- **Date:** {meta['retrieved']} (UTC)",
        f"- **API:** NLM RxNav REST API, `{meta['api']}` (no key): `rxcui.json`, "
        "`rxcui/{rxcui}/properties.json`, `rxcui/{rxcui}/related.json` "
        "(`tty=BN+SCD`, `tty=SBD`, `rela=inverse_isa`), `rxcui/{rxcui}/allProperties.json`, `version.json`",
        f"- **RxNorm release:** {meta['rxnorm_release']} (API {meta['api_version']})",
        "",
        "## Rules",
        "",
        f"- Oral: a dose form RxNorm files under its dose form group `{ORAL_GROUP}` "
        f"({len(meta['oral_dose_forms_in_rxnorm'])} forms).",
        "- Marketed: RxNorm's attributes say `HUMAN_DRUG` and `PRESCRIBABLE` = Y. Veterinary and "
        "discontinued products are left out, and the parsed strength must match `AVAILABLE_STRENGTH`.",
        "- Strengths: single-ingredient clinical drugs (SCD) only, in RxNorm's units (MG, MG/ML). Past "
        f"{limits['strengths']}, the ones found in the most RxNorm products are kept.",
        "- Brands: a BN with a marketed branded drug of a kept SCD. The most such drugs first, then the "
        "older RxCUI.",
    ]


def _md_counts(meta: dict) -> list[str]:
    counts, limits, scd = meta["counts"], meta["limits"], meta["counts"]["scd"]
    return [
        "",
        "## Counts",
        "",
        f"- INNs: {counts['inns']}, of which {counts['mapped']} map to an RxNorm ingredient",
        f"- INNs with a brand: {counts['with_brand']} ({counts['brands']} brands in all)",
        f"- INNs with an oral strength: {counts['with_oral_strength']} "
        f"({counts['strengths']} strengths kept; {counts['capped']} INNs have more than "
        f"{limits['strengths']} in RxNorm)",
        f"- Distinct oral dose forms seen: {counts['dose_forms']}",
        f"- RxNorm clinical drugs read: {scd['total']}. Kept {scd['oral']}. Left out: {scd['combination']} "
        f"combinations, {scd['non_oral']} non-oral, {scd['not_marketed']} oral but not a marketed human "
        f"drug, {scd['other_unit']} mass-per-mass (MG/MG), {scd['strength_mismatch']} whose strength "
        f"disagreed with RxNorm's, {scd['unparsed']} unparsed.",
    ]


def _md_names(meta: dict, drugs: list[dict]) -> list[str]:
    table = ", ".join(f"`{inn}` to `{us}`" for inn, us in meta["inn_us_name_table"].items()) or "empty"
    lines = ["", "## US-name mappings", ""]
    if meta["inn_us_name_used"]:
        used = ", ".join(f"`{inn}` to `{us}`" for inn, us in meta["inn_us_name_used"].items())
        lines.append(f"Needed: {used}. Fallback table: {table}.")
    else:
        lines.append(f"None needed: every INN resolved as written. Fallback table: {table}.")
    mapped = [d for d in drugs if d["status"] == "mapped"]
    differing = [d for d in mapped if rg.squash(d["inn"]) != rg.squash(d["rxnorm_name"])]
    if differing:
        lines += ["", "RxNorm names the ingredient differently for:", ""]
        lines += [f"- `{d['inn']}`: `{d['rxnorm_name']}` ({d['rxcui']})" for d in differing]
    normalized = [d["inn"] for d in drugs if d["match"] == "normalized"]
    if normalized:
        lines += ["", f"Matched only after normalization, so check by hand: {_list(normalized)}."]
    return lines


def _md_gaps(drugs: list[dict]) -> list[str]:
    mapped = [d for d in drugs if d["status"] == "mapped"]
    unmapped = [f"`{d['inn']}` ({d['reason']})" for d in drugs if d["status"] == "unmapped"]
    no_brand = _list([d["inn"] for d in mapped if not d["brands"]])
    no_strength = _list([d["inn"] for d in mapped if not d["oral_strengths"]])
    odd = [d for d in mapped if d["unparsed_names"] or d["scd_counts"]["strength_mismatch"]]
    return [
        "",
        "## INNs with no brand",
        "",
        f"{no_brand}.",
        "",
        "## INNs with no oral strength",
        "",
        f"{no_strength}.",
        "",
        "## Not in RxNorm",
        "",
        "; ".join(unmapped) + "." if unmapped else "None.",
        "",
        "## Check by hand",
        "",
        f"Strength disagreed with RxNorm, or name did not parse: {_list([d['inn'] for d in odd])}.",
    ]


def render_md(data: dict) -> str:
    """The short human summary of one run, built from the JSON payload so reruns reproduce it exactly."""
    meta, drugs = data["meta"], data["drugs"]
    lines = [*_md_head(meta), *_md_counts(meta), *_md_names(meta, drugs), *_md_gaps(drugs)]
    return "\n".join([*lines, "", "---", "", rg.ATTRIBUTION, ""])


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the RxNorm drug vocabulary for the fine-tune.")
    parser.add_argument("--offline", action="store_true", help="use the cache only, and fail on a miss")
    args = parser.parse_args()
    rx = rg.RxNav(rg.CACHE, offline=args.offline)
    try:
        data = ground(rx)
        OUT.mkdir(parents=True, exist_ok=True)
        text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        (OUT / "rxnorm_drugs.json").write_text(text, encoding="utf-8")
        (OUT / "rxnorm_drugs.md").write_text(render_md(data), encoding="utf-8")
    except (rg.RxNavError, ValueError, OSError) as err:
        sys.exit(f"error: {err}")
    counts = data["meta"]["counts"]
    print(
        f"{counts['inns']} INNs: {counts['mapped']} mapped; {counts['with_brand']} with a brand "
        f"({counts['brands']} brands); {counts['with_oral_strength']} with an oral strength "
        f"({counts['strengths']} kept). Calls: {rx.live} live, {rx.cached} from the cache."
    )


if __name__ == "__main__":
    main()
