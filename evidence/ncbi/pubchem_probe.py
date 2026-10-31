"""Probe: does PubChem agree with Anamnesis's INN_ALIASES? Read-only, writes JSON."""
import json, sys, time, urllib.parse, urllib.request, importlib.util
spec = importlib.util.spec_from_file_location("med", sys.argv[1]); med = importlib.util.module_from_spec(spec)
sys.modules["med"] = med; spec.loader.exec_module(med)
ROOT = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/"
cache = {}
def get(path):
    if path not in cache:
        time.sleep(0.25)
        try:
            with urllib.request.urlopen(ROOT + path, timeout=20) as r:
                cache[path] = json.load(r)["IdentifierList"]["CID"]
        except urllib.error.HTTPError as e:
            cache[path] = [] if e.code in (400, 404) else [f"HTTP {e.code}"]
    return cache[path]
def cids(name, kind):
    found = get("name/" + urllib.parse.quote(name) + "/cids/JSON")
    if kind == "standard":
        return found
    parents = set()
    for cid in found:
        parents |= set(get(f"cid/{cid}/cids/JSON?cids_type=parent")) or set(get(f"cid/{cid}/cids/JSON?cids_type=component")) or {cid}
    return sorted(parents)
rows = []
for alias, (moiety, salt) in med.INN_ALIASES.items():
    m = set(cids(moiety, "standard")[:1])
    p = set(cids(alias, "parent"))
    verdict = "not_in_pubchem" if not p else ("agrees" if m & p else "DISAGREES")
    rows.append({"alias": alias, "moiety": moiety, "salt": salt, "moiety_cid": sorted(m), "alias_parent_cids": sorted(p), "verdict": verdict})
json.dump(rows, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
from collections import Counter
print(Counter(r["verdict"] for r in rows))
for r in rows:
    if r["verdict"] != "agrees": print(r["verdict"], r["alias"], "->", r["moiety"], r["moiety_cid"], r["alias_parent_cids"][:3])
