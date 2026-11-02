"""Batch 34: the Spanish salt table beside INN_ALIASES (SPEC §3 rule 6)."""

from anamnesis.schema import INN_ALIASES, SPANISH_SALT_NAMES


def test_table_holds_exactly_the_spec_words() -> None:
    assert SPANISH_SALT_NAMES == {
        "succinato": "succinate",
        "tartrato": "tartrate",
        "fumarato": "fumarate",
        "hemifumarato": "hemifumarate",
        "besilato": "besilate",
        "maleato": "maleate",
        "hidrocloruro": "hydrochloride",
        "cálcica": "calcium",
        "calcica": "calcium",
        "cálcica trihidrato": "calcium trihydrate",
        "calcica trihidrato": "calcium trihydrate",
    }


def test_every_spanish_word_maps_to_a_curated_english_salt() -> None:
    curated = {salt for _, salt in INN_ALIASES.values() if salt}
    assert set(SPANISH_SALT_NAMES.values()) <= curated


def test_deliberate_omissions_stay_out() -> None:
    for word in ("calcio", "sódica", "trihidrato", "potasio", "succinat"):
        assert word not in SPANISH_SALT_NAMES
