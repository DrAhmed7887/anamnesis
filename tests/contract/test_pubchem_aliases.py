"""The INN aliases against a committed PubChem snapshot (31 Oct, from the NCBI review session's probe). No network:
`evidence/ncbi/pubchem_probe.py` refreshes the snapshot by hand, and this test then pins it. It supports the claim
"35 of 52 aliases agree with PubChem, none disagree, 17 aren't listed there", never "verified against PubChem"
alone (`evidence/ncbi/README.md`). Written by the CEO; Muse must not edit it."""

import json
from pathlib import Path

from anamnesis.schema.medication import INN_ALIASES

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = json.loads((ROOT / "evidence/ncbi/pubchem_aliases.json").read_text(encoding="utf-8"))
ROWS = {row["alias"]: row for row in SNAPSHOT}
NOT_IN_PUBCHEM = {
    "amlodipinbesilat", "amlodipini besilas", "atorvastatinum calcicum", "bisoprololfumarat", "bisoprololi fumaras",
    "cafeína", "caféine", "clavulansäure", "metforminhydrochlorid", "metformini hydrochloridum",
    "metoprololi succinas", "metoprololi tartras", "metoprololsuccinat", "metoprololtartrat", "métoprolol",
    "paracétamol", "ácido clavulánico",
}


def test_every_alias_has_a_snapshot_row_with_the_same_mapping():
    assert set(ROWS) == set(INN_ALIASES), "refresh evidence/ncbi/pubchem_aliases.json with pubchem_probe.py"
    for alias, (moiety, salt) in INN_ALIASES.items():
        assert (ROWS[alias]["moiety"], ROWS[alias]["salt"]) == (moiety, salt), alias


def test_no_alias_disagrees_with_pubchem():
    assert [row["alias"] for row in SNAPSHOT if row["verdict"] not in ("agrees", "not_in_pubchem")] == []


def test_the_agreeing_aliases_share_their_moietys_compound():
    for row in SNAPSHOT:
        if row["verdict"] == "agrees":
            assert set(row["moiety_cid"]) & set(row["alias_parent_cids"]), row["alias"]


def test_the_claim_is_35_agree_and_these_17_unlisted():
    agree = {row["alias"] for row in SNAPSHOT if row["verdict"] == "agrees"}
    unlisted = {row["alias"] for row in SNAPSHOT if row["verdict"] == "not_in_pubchem"}
    assert (len(agree), unlisted) == (35, NOT_IN_PUBCHEM)
