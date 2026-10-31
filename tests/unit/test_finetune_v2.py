"""r2's data (evidence/finetune/plan.md, amended 29 Oct): the Spanish vocabulary from AEMPS CIMA, the held-out
Spanish brands of test_spain, and r1's data left exactly as it was."""

import json
import re
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from anamnesis.core.catalogue import normalise
from finetune import gen
from finetune.common import DATA_DIR, read_jsonl
from finetune.drugs import (
    DRUGS_V2_FILE,
    all_names,
    held_out_keys,
    load_medicines,
    load_medicines_v2,
    spain_medicines,
    spain_split,
)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import drugs_v2  # noqa: E402

V2_DIR = ROOT / "finetune" / "data_v2"
VOCAB = json.loads(DRUGS_V2_FILE.read_text(encoding="utf-8"))


@pytest.mark.parametrize(("name", "mg"), [
    ("EMCONCOR COR 2,5 mg COMPRIMIDOS RECUBIERTOS", "2.5"), ("GELOCATIL 1 g COMPRIMIDOS", "1000"),
    ("EUTIROX 100 microgramos COMPRIMIDOS", "0.1"), ("NUROFEN 400 MG COMPRIMIDOS", "400"),
    ("APIRETAL 100 mg/ml SOLUCION ORAL", None), ("PARACETAMOL X 1.000 mg COMPRIMIDOS", None),
    ("TROMALYT 150, CAPSULAS DURAS", None), ("SIN DOSIS COMPRIMIDOS", None),
])
def test_a_strength_is_read_from_the_name_by_the_products_number_rules(name, mg):
    found = drugs_v2.dose_mg(name)
    assert (found if found is None else found.normalize()) == (mg if mg is None else Decimal(mg).normalize())


def test_every_mapped_medicine_carries_its_sources_and_codes():
    assert VOCAB["meta"]["fetched"] and "AEMPS" in VOCAB["meta"]["attribution"]
    assert "WHO Collaborating Centre" in VOCAB["meta"]["attribution"]
    mapped = [drug for drug in VOCAB["drugs"] if drug["status"] == "mapped"]
    assert len(mapped) >= 55
    for drug in mapped:
        assert drug["spanish_name"] and "vtm" not in drug  # SNOMED CT ids are never written (30 Oct)
        assert drug["atc"] is None or re.fullmatch(r"[A-Z]\d\d[A-Z][A-Z]\d\d", drug["atc"]["code"])
        for brand in drug["brands"]:
            assert brand["nregistro"] and brand["products"] == len(brand["nregistro"])
            assert normalise(brand["name"]) not in {normalise(drug["inn"]), normalise(drug["spanish_name"])}
        assert all(Decimal(value) > 0 for value in drug["strengths_mg"])


def test_no_brand_says_its_own_ingredient():
    for drug in VOCAB["drugs"]:
        for brand in drug["brands"]:
            folded = drugs_v2.fold(brand["name"])
            for name in (drug["inn"], drug["spanish_name"] or ""):
                assert not (name and (folded.startswith(drugs_v2.fold(name))
                                      or drugs_v2.fold(name).startswith(folded))), brand["name"]


def test_the_catalogue_entries_all_have_codes():
    rows = {row["brand"]: row for row in VOCAB["catalogue"]}
    assert rows["Concor"]["atc"]["code"] == "C07AB07" and "vtm" not in rows["Concor"]
    assert rows["Panadol Extra"]["atc"]["code"] == "N02BE51"
    assert all(row["atc"] and row["rxcui"] and "vtm" not in row for row in rows.values())


@pytest.fixture(scope="module")
def split():
    medicines = load_medicines()
    held = held_out_keys(medicines, gen.SEED + 1)
    trained, held_out = spain_split(medicines, held, gen.SEED + 2)
    return medicines, held, trained, held_out


def test_held_out_spanish_brands_are_new_names_and_a_fifth_of_them(split):
    medicines, held, trained, held_out = split
    known = {normalise(name) for medicine in medicines for name in all_names(medicine)}
    held_names = [name for names in held_out.values() for name in names]
    trained_names = [name for names in trained.values() for name in names]
    assert held_names and not {normalise(name) for name in held_names} & known
    assert not {normalise(name) for name in held_names} & {normalise(name) for name in trained_names}
    assert len(held_names) == (len(held_names) + len(trained_names)) // 5
    held_inns = {medicine.inns[0] for medicine in medicines if medicine.key in held}
    assert not held_inns & (set(trained) | set(held_out))


def test_v2_medicines_add_the_trained_brands_only(split):
    medicines, _, trained, held_out = split
    v2 = {medicine.key: medicine for medicine in load_medicines_v2(trained)}
    for medicine in medicines:
        assert v2[medicine.key].brands[: len(medicine.brands)] == medicine.brands
    all_v2 = {normalise(name) for medicine in v2.values() for name in medicine.brands}
    assert not all_v2 & {normalise(name) for names in held_out.values() for name in names}
    pool = spain_medicines(held_out, medicines)
    assert all(not medicine.ingredient_names and medicine.brands for medicine in pool)


def test_the_committed_v2_data_holds_the_split():
    meta = json.loads((V2_DIR / "meta.json").read_text(encoding="utf-8"))
    held = [name for names in meta["spanish_brands"]["held_out"].values() for name in names]
    text = (V2_DIR / "train.jsonl").read_text(encoding="utf-8") + (V2_DIR / "val.jsonl").read_text("utf-8")
    word = r"(?<![A-Za-z]){}(?![A-Za-z])"
    assert not [name for name in held if re.search(word.format(re.escape(name)), text, re.I)]
    rows = read_jsonl(V2_DIR / "test_spain.answers.jsonl")
    assert len(rows) == 60 and all(key.startswith("cima:") for row in rows for key in row["drugs"])
    said = {claim["name_text"] for row in rows for claim in row["claims"]}
    assert said and all(any(normalise(name) in normalise(text) for name in held) for text in said)
    v1 = json.loads((DATA_DIR / "meta.json").read_text(encoding="utf-8"))
    assert meta["held_out"] == v1["held_out"]


def test_r1s_data_is_regenerated_byte_for_byte(tmp_path):
    gen.generate(tmp_path, gen.SEED)
    for path in sorted(tmp_path.iterdir()):
        assert path.read_bytes() == (DATA_DIR / path.name).read_bytes(), path.name
