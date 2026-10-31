"""Spanish (EU) drug vocabulary for the fine-tune's second run, r2 (evidence/finetune/plan.md, amended 29
Oct): each medicine's marketed brands in Spain, its WHO ATC code and its SNOMED CT VTM id, from AEMPS CIMA.

    .venv/bin/python scripts/drugs_v2.py [--offline]

Writes evidence/data/drugs_v2.json and .md. Only AEMPS's public CIMA REST API is called
(https://cima.aemps.es/cima/rest/), and it receives ingredient names and registration numbers only. Every
response is cached in evidence/raw/cima/ (git-ignored), so a rerun makes no calls; --offline fails on a cache
miss instead of calling.

For each INN of scripts/rxnorm_drugs.py's DRUGS:
- The Spanish name. CIMA searches its own Spanish names as substrings and ignores accents, so the INN is
  searched as written, then without a final "e", or under SPANISH_NAMES when its Spanish name doesn't contain
  it. The name kept is the one CIMA's own VTM (virtual therapeutic moiety) gives for a single ingredient: the
  search word, or the word plus "a" or "o". An INN with no such VTM is recorded as not mapped.
- Products: every marketed product (comerc=1, all pages) whose VTM is that ingredient alone, sold as a tablet
  or a capsule, whose name prints one strength in mg, g or micrograms.
- Brands: the first word of each such product, by finetune/drugs.py's brand rule, and never a word of the
  ingredient's names or a name starting with one. Generics count: a plain one is named after its ingredient
  ("BISOPROLOL CINFA"), which the rule drops, and a branded one ("ADIRO ... EFG") is what patients say. Up to
  MAX_BRANDS, those on the most products first.
- Strengths: the distinct printed strengths of all such products, generics included.
- Codes: the VTM id, and the level-5 ATC code in CIMA's record of each brand's first product. They must agree,
  or the codes are recorded as in disagreement and left empty.
The catalogue's 9 entries get the same codes, a combination through its combination VTM, beside their RxCUIs
from evidence/data/rxnorm_catalogue.json.
"""

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import rxnorm_drugs as rd  # noqa: E402
import rxnorm_ground as rg  # noqa: E402

from anamnesis.core.catalogue import load_catalogue  # noqa: E402
from anamnesis.providers.numbers import parse_amount_text  # noqa: E402
from finetune.drugs import usable_brand  # noqa: E402

CACHE = ROOT / "evidence/raw/cima"
OUT = ROOT / "evidence/data"
BASE = "https://cima.aemps.es/cima/rest"
HEADERS = {"User-Agent": "anamnesis-drugs-v2/1.0", "Accept": "application/json"}
MIN_INTERVAL = 0.35  # seconds between live calls
TIMEOUT = 30
ATTEMPTS = 4
RETRY_CODES = {429, 500, 502, 503, 504}
MAX_BRANDS = 4
# The Spanish names (DCI) that don't contain the INN as written or without its final "e". Each is only a
# search word: CIMA's own VTM must confirm it. caffeine and clavulanic acid serve the catalogue's
# combinations only.
SPANISH_NAMES = {
    "acetylsalicylic acid": "ácido acetilsalicílico", "alendronic acid": "ácido alendrónico",
    "allopurinol": "alopurinol", "amitriptyline": "amitriptilina", "amoxicillin": "amoxicilina",
    "azithromycin": "azitromicina", "doxycycline": "doxiciclina", "hydrochlorothiazide": "hidroclorotiazida",
    "levothyroxine": "levotiroxina", "spironolactone": "espironolactona", "caffeine": "cafeína",
    "clavulanic acid": "ácido clavulánico",
}
# CIMA's search finds no product under a name with a space, so these are searched by a fragment of it.
SEARCH_WORDS = {"acetylsalicylic acid": "acetilsalic", "alendronic acid": "alendr"}
# The strength a pack prints, read from the product's name ("EMCONCOR COR 2,5 mg COMPRIMIDOS", "... 1 g ...",
# "... 100 microgramos ..."): CIMA's dosis field sometimes gives the salt instead (escitalopram 12.77 mg for a
# 10 mg tablet). A per-volume strength ("100 mg/ml") is not a tablet's. Kept in mg, as rxnorm_drugs.py keeps
# RxNorm's strengths, and read by the product's own number rules, so an ambiguous "1.000" is dropped.
STRENGTH = re.compile(r"(?<![\d.,])(\d+(?:[.,]\d+)*)\s*(mg|g|mcg|µg|microgramos)\b(?!\s*/)", re.I)
TO_MG = {unit.casefold(): Decimal(factor) for unit, factor in
         (("mg", "1"), ("g", "1000"), ("mcg", "0.001"), ("µg", "0.001"), ("microgramos", "0.001"))}
ATTRIBUTION = (
    "Source: Agencia Española de Medicamentos y Productos Sanitarios (AEMPS), CIMA, https://cima.aemps.es. "
    "ATC codes as CIMA lists them; the ATC classification is the WHO Collaborating Centre for Drug "
    "Statistics Methodology's (Oslo)."
)


class CimaError(RuntimeError):
    """A call failed, or an answer was not what CIMA documents. Not the same as 'not in CIMA'."""


def _slug(url: str) -> str:
    readable = re.sub(r"[^A-Za-z0-9]+", "_", url.removeprefix(f"{BASE}/")).strip("_")[:80]
    return f"{readable}-{hashlib.sha256(url.encode()).hexdigest()[:10]}"


class Cima:
    """Cached, rate-limited CIMA client, like rxnorm_ground.py's RxNav. A cache miss is a live call."""

    def __init__(self, cache: Path, offline: bool = False) -> None:
        self.cache, self.offline = cache, offline
        self.live = self.cached = 0
        self.dates: set[str] = set()
        self._last_call = 0.0
        self._opener = urllib.request.build_opener(rg._NoRedirect)

    def get(self, path: str, **params: str | int) -> dict:
        url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
        file = self.cache / f"{_slug(url)}.json"
        if file.exists():
            record = json.loads(file.read_text(encoding="utf-8"))
            if record.get("url") != url:
                raise CimaError(f"cache file {file} does not belong to {url}: delete it to refetch")
            self.cached += 1
        elif self.offline:
            raise CimaError(f"--offline, and nothing is cached for {url}")
        else:
            record = {"url": url, "fetched": datetime.now(UTC).isoformat(timespec="seconds"),
                      "response": self._call(url)}
            self.cache.mkdir(parents=True, exist_ok=True)
            partial = file.with_suffix(".part")
            partial.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            partial.replace(file)
            self.live += 1
        self.dates.add(record["fetched"][:10])
        return record["response"]

    def _call(self, url: str) -> dict:
        for attempt in range(1, ATTEMPTS + 1):
            time.sleep(max(0.0, self._last_call + MIN_INTERVAL - time.monotonic()))
            self._last_call = time.monotonic()
            try:
                request = urllib.request.Request(url, headers=HEADERS)
                with self._opener.open(request, timeout=TIMEOUT) as reply:
                    answer = json.load(reply)
            except urllib.error.HTTPError as err:
                if err.code not in RETRY_CODES:
                    raise CimaError(f"HTTP {err.code} from {url}") from err
                failure = f"HTTP {err.code}"
            except OSError as err:
                failure = str(err)
            except ValueError as err:
                raise CimaError(f"an answer that is not JSON from {url}") from err
            else:
                if not isinstance(answer, dict):
                    raise CimaError(f"an answer that is not a JSON object from {url}")
                return answer
            if attempt == ATTEMPTS:
                raise CimaError(f"{failure} from {url}, after {ATTEMPTS} tries")
            time.sleep(2**attempt)
        raise AssertionError("unreachable")


def fold(text: str) -> str:
    """Casefolded, without accents: how CIMA's own search compares names."""
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).casefold()


def search(cima: Cima, word: str) -> list[dict]:
    """Every marketed product whose active ingredients contain the word, over all pages."""
    rows: list[dict] = []
    page = 1
    while True:
        body = cima.get("medicamentos", practiv1=word, comerc=1, pagina=page)
        try:
            found, total = body["resultados"], int(body["totalFilas"])
        except (KeyError, TypeError, ValueError) as err:
            raise CimaError(f"a search answer without resultados or totalFilas for {word!r}") from err
        rows += found
        if not found or len(rows) >= total:
            return rows
        page += 1


def vtm(row: dict) -> tuple[str, str] | None:
    found = row.get("vtm") or {}
    return (str(found["id"]), found["nombre"]) if found.get("id") and found.get("nombre") else None


def spanish_name(cima: Cima, inn: str) -> tuple[str | None, list[str], list[dict]]:
    """CIMA's Spanish name for one ingredient, the words searched, and the rows of the search found it in."""
    tried: list[str] = []
    if inn in SPANISH_NAMES:
        words = [SEARCH_WORDS.get(inn, SPANISH_NAMES[inn])]
    else:
        words = [inn] + ([inn[:-1]] if inn.endswith("e") else [])
    for word in words:
        tried.append(word)
        rows = search(cima, word)
        if inn in SPANISH_NAMES:
            wanted = {fold(SPANISH_NAMES[inn])}
        else:
            wanted = {fold(word), fold(word) + "a", fold(word) + "o"}
        names = {found[1] for row in rows if (found := vtm(row)) and "+" not in found[1]
                 and fold(found[1]) in wanted}
        if len(names) == 1:
            return names.pop(), tried, rows
    return None, tried, []


def dose_mg(name: str | None) -> Decimal | None:
    """The first strength printed in a product's name, in mg; None if there is none or it is ambiguous."""
    match = STRENGTH.search(name or "")
    value = parse_amount_text(match.group(1)) if match else None
    return value * TO_MG[match.group(2).casefold()] if value is not None else None


def solid_form(row: dict) -> str | None:
    form = fold((row.get("formaFarmaceuticaSimplificada") or {}).get("nombre") or "")
    return "tablet" if form.startswith("comprimido") else "capsule" if form.startswith("capsula") else None


def atc_codes(cima: Cima, nregistro: str) -> set[tuple[str, str]]:
    """The level-5 ATC codes of one product's CIMA record."""
    record = cima.get("medicamento", nregistro=nregistro)
    return {(atc["codigo"], atc["nombre"]) for atc in record.get("atcs") or [] if atc.get("nivel") == 5}


def map_inn(cima: Cima, inn: str, rxnorm_name: str) -> dict:
    spanish, tried, rows = spanish_name(cima, inn)
    result: dict = {"inn": inn, "searched": tried, "spanish_name": spanish, "status": "not_mapped",
                    "vtm": None, "atc": None, "brands": [], "strengths_mg": [], "dropped": {}}
    if spanish is None:
        result["reason"] = "no single-ingredient VTM in CIMA under the words searched"
        return result
    dropped: Counter = Counter()
    kept = []
    for row in rows:
        found = vtm(row)
        if not found or fold(found[1]) != fold(spanish):
            dropped["other_ingredients"] += 1
        elif solid_form(row) is None:
            dropped["not_tablet_or_capsule"] += 1
        elif dose_mg(row.get("nombre")) is None:
            dropped["no_strength_in_name"] += 1
        else:
            kept.append(row)
    names = (inn, rxnorm_name, spanish)
    # A brand that is a word of the ingredient's name ("ACIDO ACETILSALICILICO"), starts with it ("Aspirina")
    # or is its start ("Vals", valsartan) would be saying the ingredient, as finetune/drugs.py's rule says.
    words = {word for name in names for word in fold(name).split()}
    brands: dict[str, list[str]] = {}
    for row in kept:
        brand = usable_brand(row["nombre"].split()[0], names)
        if brand and fold(brand) not in words and not any(
                fold(brand).startswith(fold(n)) or fold(n).startswith(fold(brand)) for n in names):
            brands.setdefault(brand, []).append(str(row["nregistro"]))
    chosen = sorted(brands, key=lambda name: (-len(brands[name]), name))[:MAX_BRANDS]
    vtms = {vtm(row) for row in kept}
    codes = {code for name in chosen for code in atc_codes(cima, sorted(brands[name])[0])}
    if not chosen and kept:
        codes = atc_codes(cima, sorted(str(row["nregistro"]) for row in kept)[0])
    result.update(
        status="mapped" if kept else "no_products",
        brands=[{"name": name, "products": len(brands[name]), "nregistro": sorted(brands[name])}
                for name in chosen],
        strengths_mg=sorted({format(dose_mg(row["nombre"]).normalize(), "f") for row in kept}, key=Decimal),
        forms=sorted({solid_form(row) for row in kept}),
        products=len(kept),
        dropped=dict(dropped),
    )
    if len(vtms) == 1:
        result["vtm"] = dict(zip(("id", "name"), vtms.pop(), strict=True))
    if len(codes) == 1:
        result["atc"] = dict(zip(("code", "name"), codes.pop(), strict=True))
    elif codes:
        result["atc_disagreement"] = sorted(code for code, _ in codes)
    return result


def catalogue_codes(cima: Cima, drugs: list[dict]) -> list[dict]:
    """The catalogue entries' codes: a single ingredient's from its row above, a combination's from CIMA."""
    by_inn = {drug["inn"]: drug for drug in drugs}
    grounded = json.loads((OUT / "rxnorm_catalogue.json").read_text(encoding="utf-8"))["entries"]
    rxcuis = {entry["brand"]: [part["rxcui"] for part in entry["ingredients"] if part.get("rxcui")]
              for entry in grounded}
    entries = []
    for entry in load_catalogue().entries:
        inns = sorted(entry.inns)
        row: dict = {"brand": entry.brand, "inns": inns, "rxcui": rxcuis.get(entry.brand), "vtm": None,
                     "atc": None}
        if len(inns) == 1 and by_inn.get(inns[0], {}).get("status") == "mapped":
            row.update(vtm=by_inn[inns[0]]["vtm"], atc=by_inn[inns[0]]["atc"])
        elif len(inns) > 1:
            spanish = [by_inn[inn]["spanish_name"] if inn in by_inn else SPANISH_NAMES[inn] for inn in inns]
            wanted = sorted(fold(name) for name in spanish)
            matches = [r for r in search(cima, spanish[0]) if (found := vtm(r))
                       and sorted(fold(part.strip()) for part in found[1].split("+")) == wanted]
            if len({vtm(r) for r in matches}) == 1:
                row["vtm"] = dict(zip(("id", "name"), vtm(matches[0]), strict=True))
                codes = atc_codes(cima, sorted(str(r["nregistro"]) for r in matches)[0])
                if len(codes) == 1:
                    row["atc"] = dict(zip(("code", "name"), codes.pop(), strict=True))
        entries.append(row)
    return entries


def markdown(data: dict) -> str:
    lines = ["# Spanish (EU) drug vocabulary for r2, from AEMPS CIMA", "",
             f"Read {', '.join(data['meta']['fetched'])} from {BASE}. {ATTRIBUTION}", "",
             "| INN | Spanish name | Brands in Spain (products) | Strengths, mg | ATC |",
             "|---|---|---|---|---|"]
    for drug in data["drugs"]:
        brands = ", ".join(f"{b['name']} ({b['products']})" for b in drug["brands"]) or "none"
        atc = (drug["atc"] or {}).get("code") or ("disagree" if drug.get("atc_disagreement") else "—")
        lines.append(f"| {drug['inn']} | {drug['spanish_name'] or drug['status']} | {brands} | "
                     f"{', '.join(drug['strengths_mg']) or '—'} | {atc} |")
    lines += ["", "## The catalogue's codes", "", "| Entry | INNs | ATC | RxCUI |",
              "|---|---|---|---|"]
    for row in data["catalogue"]:
        atc = (row["atc"] or {}).get("code", "—")
        lines.append(f"| {row['brand']} | {' + '.join(row['inns'])} | {atc} | "
                     f"{', '.join(row['rxcui'] or []) or '—'} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="fail on a cache miss instead of calling")
    args = parser.parse_args()
    cima = Cima(CACHE, offline=args.offline)
    rxnorm = {record["inn"]: record for record in
              json.loads((OUT / "rxnorm_drugs.json").read_text(encoding="utf-8"))["drugs"]}
    drugs = [map_inn(cima, inn, rxnorm[inn]["rxnorm_name"]) for inn in rd.DRUGS]
    data = {"meta": {"source": BASE, "attribution": ATTRIBUTION, "max_brands": MAX_BRANDS,
                     "fetched": sorted(cima.dates)},
            "drugs": drugs, "catalogue": catalogue_codes(cima, drugs)}
    data["meta"]["fetched"] = sorted(cima.dates)
    for record in data["drugs"] + data["catalogue"]:
        record.pop("vtm", None)  # SNOMED CT ids map CIMA's records but are licensed content: never written
    text = json.dumps(data, indent=1, ensure_ascii=False) + "\n"
    (OUT / "drugs_v2.json").write_text(text, encoding="utf-8")
    (OUT / "drugs_v2.md").write_text(markdown(data), encoding="utf-8")
    mapped = sum(drug["status"] == "mapped" for drug in drugs)
    brands = sum(len(drug["brands"]) for drug in drugs)
    print(f"{mapped} of {len(drugs)} INNs mapped, {brands} Spanish brands; CIMA calls: {cima.live} live, "
          f"{cima.cached} cached")


if __name__ == "__main__":
    main()
