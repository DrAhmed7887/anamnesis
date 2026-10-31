"""RxNorm grounding of the Anamnesis catalogue: each INN to its RxNorm ingredient, each brand to RxNorm.

    .venv/bin/python scripts/rxnorm_ground.py [--offline]

Reads anamnesis/core/catalogue.yaml and writes evidence/data/rxnorm_catalogue.json and .md. Only NLM's public
RxNav REST API is called (https://rxnav.nlm.nih.gov/REST, no key), and it receives drug names and RxCUIs only.
Every response is cached under evidence/raw/rxnorm/ (git-ignored), so a rerun makes no calls: delete that
folder to refresh, or pass --offline to fail on a cache miss instead of calling. At most 3 calls a second.

How a name is matched (API docs: https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html):
- search=0 (exact, case-insensitive) first, then search=1 (normalized: ignores word order, punctuation,
  plurals and salt forms). Together they are search=2, run apart so the output says which one matched.
- An INN is mapped only to a concept of term type IN. An INN that names a salt form resolves to a PIN, and its
  parent IN comes from the PIN's relations. A brand counts only as term type BN.
- An INN with no ingredient in RxNorm is retried once under its US adopted name from US_NAMES, and the output
  records that. Whatever is still unresolved is reported with its reason, never guessed.
Not being in RxNorm is a result, not an error: RxNorm covers US-marketed drugs. A failed API call is an error.
For a brand RxNorm holds, the branded dose forms (SBDF) it records are kept beside the catalogue's release
field, and a disagreement between the two is listed in the .md for a hand check.
"""

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "anamnesis/core/catalogue.yaml"
CACHE = ROOT / "evidence/raw/rxnorm"
OUT = ROOT / "evidence/data"
BASE = "https://rxnav.nlm.nih.gov/REST"
USER_AGENT = "anamnesis-rxnorm-ground/1.0"
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}
MIN_INTERVAL = 0.35  # seconds between live calls: under 3 a second, where NLM allows 20 a second per IP
TIMEOUT = 30
ATTEMPTS = 4
RETRY_CODES = {429, 500, 502, 503, 504}
# How RxNorm words a modified-release dose form, for example "Extended Release Oral Tablet".
MODIFIED_RELEASE = re.compile(r"(?:extended|delayed|modified|controlled)[ -]release|\b\d+ hr\b", re.I)
# The attribution the RxNav terms of service ask any application using its data to show.
ATTRIBUTION = (
    "This product uses publicly available data from the U.S. National Library of Medicine (NLM), "
    "National Institutes of Health, Department of Health and Human Services; NLM is not responsible "
    "for the product and does not endorse or recommend this or any other product."
)

# RxNorm names ingredients by US adopted name, so an INN can differ from it (paracetamol is acetaminophen).
# This table is the fallback: an INN with no ingredient in RxNorm is retried under the name given here, and
# the output records every use. In the 05-Oct-2026 release RxNorm resolves "paracetamol" itself, as a
# synonym of acetaminophen, so nothing needed the table; it stays for a release that drops the synonym.
US_NAMES: dict[str, str] = {"paracetamol": "acetaminophen"}


class RxNavError(RuntimeError):
    """An API call failed, or an answer was not what the API documents. Not the same as 'not in RxNorm'."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse redirects, so no request can leave rxnav.nlm.nih.gov."""

    def redirect_request(self, *_args, **_kwargs):
        return None


def _slug(url: str) -> str:
    readable = re.sub(r"[^A-Za-z0-9]+", "_", url.removeprefix(f"{BASE}/")).strip("_")[:80]
    return f"{readable}-{hashlib.sha256(url.encode()).hexdigest()[:10]}"


def _load(file: Path, url: str) -> dict:
    try:
        record = json.loads(file.read_text(encoding="utf-8"))
        if record["url"] == url and isinstance(record["response"], dict) and record["fetched"]:
            return record
    except (OSError, ValueError, KeyError, TypeError) as err:
        raise RxNavError(f"unreadable cache file {file}: delete it to refetch ({err})") from err
    raise RxNavError(f"cache file {file} does not belong to {url}: delete it to refetch")


class RxNav:
    """Cached, rate-limited RxNav client. A cache miss is a live call, which --offline forbids."""

    def __init__(self, cache: Path, offline: bool = False) -> None:
        self.cache = cache
        self.offline = offline
        self.live = 0
        self.cached = 0
        self.dates: set[str] = set()  # UTC dates of every response used, so reruns reproduce the outputs
        self._last_call = 0.0
        self._opener = urllib.request.build_opener(_NoRedirect)

    def get(self, path: str, **params: str | int) -> dict:
        """The parsed JSON answer to one request, from the cache when it is there."""
        query = urllib.parse.urlencode(params)
        url = f"{BASE}/{path}" + (f"?{query}" if query else "")
        file = self.cache / f"{_slug(url)}.json"
        if file.exists():
            record = _load(file, url)
            self.cached += 1
        elif self.offline:
            raise RxNavError(f"--offline, and nothing is cached for {url}")
        else:
            fetched = datetime.now(UTC).isoformat(timespec="seconds")
            record = {"url": url, "fetched": fetched, "response": self._call(url)}
            self.cache.mkdir(parents=True, exist_ok=True)
            partial = file.with_suffix(".part")  # written whole or not at all
            partial.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            partial.replace(file)
            self.live += 1
        self.dates.add(record["fetched"][:10])
        return record["response"]

    def _call(self, url: str) -> dict:
        for attempt in range(1, ATTEMPTS + 1):
            time.sleep(max(0.0, self._last_call + MIN_INTERVAL - time.monotonic()))
            self._last_call = time.monotonic()
            request = urllib.request.Request(url, headers=HEADERS)
            try:
                with self._opener.open(request, timeout=TIMEOUT) as reply:
                    answer = json.load(reply)
            except urllib.error.HTTPError as err:
                if err.code not in RETRY_CODES:
                    raise RxNavError(f"HTTP {err.code} from {url}") from err
                failure = f"HTTP {err.code}"
            except OSError as err:  # unreachable, timed out, reset
                failure = str(err)
            except ValueError as err:
                raise RxNavError(f"an answer that is not JSON from {url}") from err
            else:
                if not isinstance(answer, dict):
                    raise RxNavError(f"an answer that is not a JSON object from {url}")
                return answer
            if attempt == ATTEMPTS:
                raise RxNavError(f"{failure} from {url}, after {ATTEMPTS} tries")
            time.sleep(2**attempt)
        raise AssertionError("unreachable")


def concept(rx: RxNav, rxcui: str) -> dict | None:
    """{rxcui, name, tty} of an RxNorm concept, or None when RxNorm does not hold it as active."""
    if not rxcui.isdigit():
        raise RxNavError(f"unexpected RxCUI {rxcui!r}")
    props = rx.get(f"rxcui/{rxcui}/properties.json").get("properties")
    if not props:
        return None
    try:
        return {"rxcui": str(props["rxcui"]), "name": props["name"], "tty": props["tty"]}
    except KeyError as err:
        raise RxNavError(f"properties of RxCUI {rxcui} lack {err}") from err


def find(rx: RxNav, name: str) -> tuple[list[dict], str | None]:
    """The RxNorm concepts called `name`, exact match first and normalized second, and which one hit."""
    for search, how in ((0, "exact"), (1, "normalized")):
        ids = (rx.get("rxcui.json", name=name, search=search).get("idGroup") or {}).get("rxnormId") or []
        concepts = [found for found in (concept(rx, str(rxcui)) for rxcui in ids) if found]
        if concepts:
            return concepts, how
    return [], None


def _brief(item: dict) -> dict:
    return {"rxcui": str(item["rxcui"]), "name": item["name"]}


def _by_name(item: dict) -> tuple[str, str]:
    return item["name"].casefold(), item["rxcui"]


def related(rx: RxNav, rxcui: str, *ttys: str) -> dict[str, list[dict]]:
    """Concepts related to an RxCUI, by term type. Every term type asked for is a key, empty if none."""
    body = rx.get(f"rxcui/{rxcui}/related.json", tty=" ".join(ttys))
    groups = (body.get("relatedGroup") or {}).get("conceptGroup") or []
    try:
        by_tty = {g["tty"]: [_brief(item) for item in g.get("conceptProperties") or []] for g in groups}
    except KeyError as err:
        raise RxNavError(f"related concepts of RxCUI {rxcui} lack {err}") from err
    return {tty: sorted(by_tty.get(tty, []), key=_by_name) for tty in ttys}


def lookup_ingredient(rx: RxNav, name: str) -> tuple[dict | None, str]:
    """One name as an RxNorm ingredient: ({in, pin, match}, "") or (None, why not)."""
    concepts, how = find(rx, name)
    if not concepts:
        return None, f"RxNorm has no concept named '{name}'"
    candidates = [c for c in concepts if c["tty"] in ("IN", "PIN")]
    if not candidates:
        held = ", ".join(sorted({c["tty"] for c in concepts}))
        return None, f"RxNorm holds '{name}' only as term type {held}, not as an ingredient"
    if len(candidates) > 1:
        listing = ", ".join(f"{c['name']} ({c['tty']} {c['rxcui']})" for c in candidates)
        return None, f"'{name}' is ambiguous in RxNorm: {listing}"
    (hit,) = candidates
    if hit["tty"] == "IN":
        return {"in": hit, "pin": None, "match": how}, ""
    parents = related(rx, hit["rxcui"], "IN")["IN"]  # a salt form: its parent ingredient is the IN
    if len(parents) != 1:
        return None, f"RxNorm gives {len(parents)} ingredients for the precise ingredient '{hit['name']}'"
    return {"in": {**parents[0], "tty": "IN"}, "pin": hit, "match": how}, ""


def resolve_ingredient(rx: RxNav, inn: str) -> dict:
    """One catalogue INN as an RxNorm ingredient (IN), plus the PIN when the INN itself is a salt form."""
    names = [inn, US_NAMES[inn]] if inn in US_NAMES else [inn]
    reasons = []
    for name in names:
        hit, reason = lookup_ingredient(rx, name)
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
                "precise_ingredients": related(rx, hit["in"]["rxcui"], "PIN")["PIN"],
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
        "precise_ingredients": [],
        "reason": "; ".join(reasons),
    }


def squash(text: str) -> str:
    return re.sub(r"[\W_]+", "", text.casefold())


def check_ingredients(listed: list[dict], rxnorm: list[dict]) -> dict:
    """Compare the catalogue's ingredients for a brand with the ones RxNorm records for it, by RxCUI."""
    if not rxnorm:
        return {"status": "not_checked", "catalogue_only": [], "rxnorm_only": []}
    ours = {item["rxcui"]: item["inn"] for item in listed if item["rxcui"]}
    theirs = {item["rxcui"]: item["name"] for item in rxnorm}
    catalogue_only = [inn for rxcui, inn in ours.items() if rxcui not in theirs]
    catalogue_only += [item["inn"] for item in listed if not item["rxcui"]]  # no RxCUI, so cannot match
    rxnorm_only = [name for rxcui, name in theirs.items() if rxcui not in ours]
    return {
        "status": "differs" if catalogue_only or rxnorm_only else "match",
        "catalogue_only": catalogue_only,
        "rxnorm_only": rxnorm_only,
    }


def resolve_brand(rx: RxNav, brand: str, listed: list[dict]) -> dict:
    """The brand as an RxNorm brand name (BN), with the ingredients and dose forms RxNorm records for it."""
    result = {
        "queried": brand,
        "in_rxnorm": False,
        "rxcui": None,
        "tty": None,
        "rxnorm_name": None,
        "match": None,
        "note": "not in RxNorm",
        "rxnorm_ingredients": [],
        "rxnorm_multi_ingredient": [],
        "rxnorm_precise_ingredients": [],
        "rxnorm_dose_forms": [],
        "ingredient_check": None,
    }
    concepts, how = find(rx, brand)
    brands = [c for c in concepts if c["tty"] == "BN"]
    if concepts and not brands:
        held = ", ".join(sorted({c["tty"] for c in concepts}))
        return {**result, "note": f"not in RxNorm as a brand name: the name is held only as term type {held}"}
    if how == "normalized":  # normalization can slide to another name, so only the same name counts
        other = [c["name"] for c in brands if squash(c["name"]) != squash(brand)]
        brands = [c for c in brands if squash(c["name"]) == squash(brand)]
        if other and not brands:
            return {**result, "note": f"not in RxNorm: a normalized search found only {', '.join(other)}"}
    if len(brands) > 1:
        listing = ", ".join(f"{c['name']} ({c['rxcui']})" for c in brands)
        return {**result, "note": f"ambiguous: {listing}"}
    if not brands:
        return result
    (bn,) = brands
    links = related(rx, bn["rxcui"], "IN", "MIN", "PIN")
    forms = related(rx, bn["rxcui"], "SBDF")["SBDF"]
    return {
        **result,
        "in_rxnorm": True,
        "rxcui": bn["rxcui"],
        "tty": "BN",
        "rxnorm_name": bn["name"],
        "match": how,
        "note": None,
        "rxnorm_ingredients": links["IN"],
        "rxnorm_multi_ingredient": links["MIN"],
        "rxnorm_precise_ingredients": links["PIN"],
        "rxnorm_dose_forms": [form["name"] for form in forms],
        "ingredient_check": check_ingredients(listed, links["IN"]),
    }


def read_catalogue(path: Path) -> list[dict]:
    """The catalogue's brands, INNs and release field, validated, in file order."""
    records = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise ValueError(f"{path}: expected a non-empty list of entries")
    entries = []
    for number, record in enumerate(records, 1):
        brand = record.get("brand") if isinstance(record, dict) else None
        inns = record.get("inns") if isinstance(record, dict) else None
        if not isinstance(brand, str) or not brand.strip():
            raise ValueError(f"{path}: entry {number} has no brand name")
        if not isinstance(inns, list) or not inns or not all(isinstance(i, str) and i.strip() for i in inns):
            raise ValueError(f"{path}: entry {number} ({brand}) needs a non-empty list of INN names")
        release = record.get("release")
        entries.append(
            {
                "brand": brand.strip(),
                "inns": [inn.strip() for inn in inns],
                "release": release if isinstance(release, str) else None,
            }
        )
    return entries


def ground(rx: RxNav, entries: list[dict]) -> dict:
    """Look every INN (once) and every brand up, and gather the records with their counts."""
    distinct = list(dict.fromkeys(inn for entry in entries for inn in entry["inns"]))
    resolved = {inn: resolve_ingredient(rx, inn) for inn in distinct}
    records = []
    for entry in entries:
        listed = [resolved[inn] for inn in entry["inns"]]
        records.append(
            {
                "brand": entry["brand"],
                "inns": entry["inns"],
                "catalogue_release": entry["release"],
                "ingredients": listed,
                "brand_rxnorm": resolve_brand(rx, entry["brand"], listed),
            }
        )
    version = rx.get("version.json")
    dates = sorted(rx.dates)
    mapped = [item for item in resolved.values() if item["status"] == "mapped"]
    meta = {
        "script": "scripts/rxnorm_ground.py",
        "catalogue": str(CATALOGUE.relative_to(ROOT)),
        "api": BASE,
        "rxnorm_release": version.get("version"),
        "api_version": version.get("apiVersion"),
        "retrieved": dates[0] if len(dates) == 1 else f"{dates[0]} to {dates[-1]}",
        "inn_us_name_table": dict(US_NAMES),
        "inn_us_name_used": {i["inn"]: i["us_name_used"] for i in mapped if i["us_name_used"]},
        "counts": {
            "entries": len(entries),
            "inns_listed": sum(len(entry["inns"]) for entry in entries),
            "inns_distinct": len(distinct),
            "inns_mapped": len(mapped),
            "inns_unmapped": len(distinct) - len(mapped),
            "brands_in_rxnorm": sum(r["brand_rxnorm"]["in_rxnorm"] for r in records),
            "brands_not_in_rxnorm": sum(not r["brand_rxnorm"]["in_rxnorm"] for r in records),
        },
    }
    return {"meta": meta, "entries": records}


def _names(items: list[dict]) -> str:
    return ", ".join(f"{item['name']} ({item['rxcui']})" for item in items) or "none"


def _md_head(meta: dict) -> list[str]:
    counts = meta["counts"]
    return [
        "# Catalogue grounded in RxNorm",
        "",
        f"`{meta['script']}` maps `{meta['catalogue']}` to RxNorm, the US National Library of Medicine's "
        "drug ontology. Only each brand name and its INNs are looked up; the Arabic aliases are not sent. "
        "The same data, one record per entry, is in `rxnorm_catalogue.json`.",
        "",
        f"- **Date:** {meta['retrieved']} (UTC)",
        f"- **API:** NLM RxNav REST API, `{meta['api']}` (no key): `rxcui.json` (exact, then normalized), "
        "`rxcui/{rxcui}/properties.json`, `rxcui/{rxcui}/related.json`, `version.json`",
        f"- **RxNorm release:** {meta['rxnorm_release']} (API {meta['api_version']})",
        "",
        "## Counts",
        "",
        f"- Catalogue entries: {counts['entries']}",
        f"- INNs: {counts['inns_listed']} listed across the entries, {counts['inns_distinct']} distinct",
        f"- Distinct INNs that map to an RxNorm ingredient (IN): {counts['inns_mapped']} of "
        f"{counts['inns_distinct']}",
        f"- Brands in RxNorm as a brand name (BN): {counts['brands_in_rxnorm']} of {counts['entries']}. "
        f"The other {counts['brands_not_in_rxnorm']} are not in RxNorm, which is expected for non-US brands.",
    ]


def _name_note(item: dict) -> str:
    ingredient = f"RxNorm's ingredient is `{item['rxnorm_name']}` ({item['rxcui']})"
    if item["us_name_used"]:
        return f"- `{item['inn']}`: {ingredient}, reached through the table name `{item['us_name_used']}`"
    if item["pin"]:
        pin = item["pin"]
        precise = f"`{pin['name']}` ({pin['rxcui']})"
        return f"- `{item['inn']}`: {ingredient}; the INN is its precise ingredient {precise}"
    return f"- `{item['inn']}`: {ingredient}, and RxNorm resolves the INN as a synonym of it"


def _md_inns(meta: dict, ingredients: list[dict]) -> list[str]:
    table = ", ".join(f"`{inn}` to `{us}`" for inn, us in meta["inn_us_name_table"].items()) or "empty"
    lines = ["", "## INN to US-name mappings", ""]
    if meta["inn_us_name_used"]:
        lines.append(f"Used, where the INN itself had no ingredient in RxNorm. Fallback table: {table}.")
    else:
        lines.append(f"None needed: RxNorm resolved every INN under its own name. Fallback table: {table}.")
    mapped = [i for i in ingredients if i["status"] == "mapped"]
    differing = [i for i in mapped if squash(i["inn"]) != squash(i["rxnorm_name"])]
    if differing:
        lines += ["", "Where RxNorm's ingredient name differs from the INN:", "", *map(_name_note, differing)]
    lines += ["", "## INNs that did not map", ""]
    lines += [f"- `{i['inn']}`: {i['reason']}" for i in ingredients if i["status"] == "unmapped"] or ["None."]
    normalized = [i for i in ingredients if i["match"] == "normalized"]
    if normalized:
        lines += ["", "## Matched only after normalization, so check by hand", ""]
        lines += [f"- `{i['inn']}`: {i['rxnorm_name']} ({i['rxcui']})" for i in normalized]
    return lines


def release_conflict(entry: dict) -> str | None:
    """Where the catalogue's release field and RxNorm's dose forms for the brand disagree, say how."""
    brand = entry["brand_rxnorm"]
    forms = [form for form in brand["rxnorm_dose_forms"] if MODIFIED_RELEASE.search(form)]
    if entry["catalogue_release"] == "immediate" and forms:
        return f"- {entry['brand']}: the catalogue says immediate, and RxNorm also records `{forms[0]}`"
    if entry["catalogue_release"] == "modified" and brand["rxnorm_dose_forms"] and not forms:
        return f"- {entry['brand']}: the catalogue says modified, and RxNorm records no modified-release form"
    return None


def _md_brands(entries: list[dict]) -> list[str]:
    lines = ["", "## Brands", ""]
    lines.append("| Brand | RxCUI (BN) | Ingredients RxNorm records for it | Against the catalogue |")
    lines.append("|---|---|---|---|")
    for entry in entries:
        brand = entry["brand_rxnorm"]
        if not brand["in_rxnorm"]:
            lines.append(f"| {entry['brand']} | none | {brand['note']} | |")
            continue
        check = brand["ingredient_check"]
        verdict = check["status"]
        if verdict == "differs":
            verdict += f" (catalogue only: {', '.join(check['catalogue_only']) or 'none'}; "
            verdict += f"RxNorm only: {', '.join(check['rxnorm_only']) or 'none'})"
        found = _names(brand["rxnorm_ingredients"])
        lines.append(f"| {entry['brand']} | {brand['rxcui']} | {found} | {verdict} |")
    conflicts = [note for note in map(release_conflict, entries) if note]
    if conflicts:
        lines += ["", "## Release forms to check by hand", "", *conflicts]
    return lines


def render_md(data: dict) -> str:
    """The short human summary of one run, built from the JSON payload so reruns reproduce it exactly."""
    ingredients = list({i["inn"]: i for entry in data["entries"] for i in entry["ingredients"]}.values())
    lines = [*_md_head(data["meta"]), *_md_inns(data["meta"], ingredients), *_md_brands(data["entries"])]
    return "\n".join([*lines, "", "---", "", ATTRIBUTION, ""])


def main() -> None:
    parser = argparse.ArgumentParser(description="Ground the Anamnesis catalogue in RxNorm.")
    parser.add_argument("--offline", action="store_true", help="use the cache only, and fail on a miss")
    args = parser.parse_args()
    rx = RxNav(CACHE, offline=args.offline)
    try:
        data = ground(rx, read_catalogue(CATALOGUE))
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "rxnorm_catalogue.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        (OUT / "rxnorm_catalogue.md").write_text(render_md(data), encoding="utf-8")
    except (RxNavError, ValueError, OSError, yaml.YAMLError) as err:
        sys.exit(f"error: {err}")
    counts = data["meta"]["counts"]
    print(
        f"{counts['entries']} entries, {counts['inns_distinct']} distinct INNs: "
        f"{counts['inns_mapped']} mapped, {counts['inns_unmapped']} not. "
        f"Brands in RxNorm: {counts['brands_in_rxnorm']} of {counts['entries']}. "
        f"Calls: {rx.live} live, {rx.cached} from the cache."
    )


if __name__ == "__main__":
    main()
