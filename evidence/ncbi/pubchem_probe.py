"""Probe: does PubChem agree with Anamnesis's INN_ALIASES? Read-only, writes JSON. Run by hand to refresh the
snapshot that tests/contract/test_pubchem_aliases.py pins (written by the NCBI review session, 31 Oct; reformatted
for ruff by the engine, logic unchanged).

    uv run python evidence/ncbi/pubchem_probe.py anamnesis/schema/medication.py evidence/ncbi/pubchem_aliases.json
"""

import importlib.util
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

ROOT = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/"
cache: dict[str, list] = {}


def get(path: str) -> list:
    if path not in cache:
        time.sleep(0.25)  # PubChem allows 5 requests a second
        try:
            with urllib.request.urlopen(ROOT + path, timeout=20) as reply:
                cache[path] = json.load(reply)["IdentifierList"]["CID"]
        except urllib.error.HTTPError as exc:
            cache[path] = [] if exc.code in (400, 404) else [f"HTTP {exc.code}"]
    return cache[path]


def cids(name: str, kind: str) -> list:
    found = get("name/" + urllib.parse.quote(name) + "/cids/JSON")
    if kind == "standard":
        return found
    parents: set = set()
    for cid in found:
        parents |= (set(get(f"cid/{cid}/cids/JSON?cids_type=parent"))
                    or set(get(f"cid/{cid}/cids/JSON?cids_type=component")) or {cid})
    return sorted(parents)


def main() -> None:
    spec = importlib.util.spec_from_file_location("med", sys.argv[1])
    med = importlib.util.module_from_spec(spec)
    sys.modules["med"] = med
    spec.loader.exec_module(med)
    rows = []
    for alias, (moiety, salt) in med.INN_ALIASES.items():
        moiety_cid = set(cids(moiety, "standard")[:1])
        parents = set(cids(alias, "parent"))
        verdict = "not_in_pubchem" if not parents else ("agrees" if moiety_cid & parents else "DISAGREES")
        rows.append({"alias": alias, "moiety": moiety, "salt": salt, "moiety_cid": sorted(moiety_cid),
                     "alias_parent_cids": sorted(parents), "verdict": verdict})
    with open(sys.argv[2], "w", encoding="utf-8") as out:
        json.dump(rows, out, ensure_ascii=False, indent=1)
    print(Counter(row["verdict"] for row in rows))
    for row in rows:
        if row["verdict"] != "agrees":
            print(row["verdict"], row["alias"], "->", row["moiety"], row["moiety_cid"], row["alias_parent_cids"][:3])


if __name__ == "__main__":
    main()
