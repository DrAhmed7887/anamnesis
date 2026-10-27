"""Extra unit tests for batch 13: salt collection, combination intakes, country order."""

from decimal import Decimal

from anamnesis.core.catalogue import Catalogue, CatalogueEntry, load_catalogue, normalise
from anamnesis.core.reconcile import _side_salts, _text_salts, reconcile_pair
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema import IngredientAmount, PackObservation, PatientClaim, Release, Strength

CAT = load_catalogue()


def mg(inn, amount):
    return IngredientAmount(inn=inn, amount=Decimal(str(amount)), unit="mg")


def claim(name, **kw):
    return PatientClaim(claim_id="c1", name_text=name, status="active", audio_evidence=["t1"], **kw)


def pack(label, **kw):
    return PackObservation(observation_id="o1", label_text=label, readability="readable",
                           visual_evidence=["r1"], **kw)


def test_normalise_is_public_and_folds_punctuation():
    assert normalise("METOPROLOL-Tartrate") == "metoprolol tartrate"


def test_text_salts_find_whole_words_only():
    assert _text_salts("metoprolol tartrates", CAT) == []
    assert _text_salts("Metoprolol/Succinate", CAT) == [("metoprolol", "succinate")]


def test_longer_alias_suppresses_its_prefix_alias():
    found = _text_salts("atorvastatin calcium trihydrate", CAT)
    assert found == [("atorvastatin", "calcium trihydrate")]


def test_side_salts_merge_all_sources():
    strength = Strength(ingredients=[mg("metoprolol", 100)], per="tablet")
    salts = _side_salts(strength, mg("metoprolol succinate", 100), None, "metoprolol tartrate", CAT)
    assert salts == {"metoprolol": frozenset({"succinate", "tartrate"})}


def test_same_salt_from_two_sources_is_not_a_conflict():
    c = claim("metoprolol succinate", intake_amount=mg("metoprolol succinate", 100))
    p = pack("Metoprolol succinate 100", strength=Strength(ingredients=[mg("metoprolol", 100)], per="tablet"))
    assert reconcile_pair(c, p, CAT).type is not D.INSUFFICIENT_INFORMATION


def test_country_match_beats_brand_order_and_is_case_insensitive():
    def entry(brand, country):
        return CatalogueEntry(brand=brand, inns=frozenset({"metoprolol"}), countries=(country,),
                              synthetic=True, release=Release.IMMEDIATE, splittable=None)
    cat = Catalogue((entry("Aaa", "GB"), entry("Zzz", "DE")))
    assert cat.resolve("metoprolol", "de").brand == "Zzz"
    assert cat.resolve("metoprolol", "fr").brand == "Aaa"
