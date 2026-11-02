"""Extra offline checks for batch 32 (SPEC §3, "Spanish speech"): the rule is generic over the catalogue."""

import itertools
import re

from anamnesis.core.catalogue import load_catalogue, normalise
from anamnesis.schema.medication import INN_ALIASES

CAT = load_catalogue()
TOMAR = ("tomo", "toma", "tomas", "tomamos", "toman")
ARABIC_RE = re.compile(r"[؀-ۿ]")


def _latin_names(entry):
    names = [entry.brand, *entry.aliases]
    if len(entry.inns) == 1:
        (moiety,) = entry.inns
        names += [moiety, *(alias for alias, (target, _) in INN_ALIASES.items() if target == moiety)]
    return [name for name in names if not ARABIC_RE.search(name)]


def _swap_bv(text):
    return "".join({"b": "v", "v": "b"}.get(char, char) for char in text)


NAMES = [(name, entry) for entry in CAT.entries for name in _latin_names(entry)]

SALTED = {normalise(alias) for entry in CAT.entries if len(entry.inns) == 1
          for alias, (target, salt) in INN_ALIASES.items() if salt and target in entry.inns}
"""Normalised salt-bearing aliases of single-ingredient entries: matched only as written (SPEC §3)."""


def test_every_latin_name_resolves_bare():
    assert NAMES
    for name, entry in NAMES:
        found = CAT.resolve(name)
        assert found is not None and found.inns == entry.inns, name


def test_b_and_v_match_each_other_for_every_latin_name():
    for name, entry in NAMES:
        if normalise(name) in SALTED:
            continue
        swapped = _swap_bv(normalise(name))
        if swapped == normalise(name):
            continue
        found = CAT.resolve(swapped)
        assert found is not None and found.inns == entry.inns, swapped


def test_one_joined_tomar_form_resolves_and_covers_for_every_latin_name():
    for name, entry in NAMES:
        if normalise(name) in SALTED:
            continue
        for form in TOMAR:
            joined = form + normalise(name)
            found = CAT.resolve(joined)
            assert found is not None and found.inns == entry.inns, joined
            assert CAT.covers(joined), joined


def test_a_salted_name_is_matched_only_as_written():
    salted = [(name, entry) for name, entry in NAMES if normalise(name) in SALTED]
    assert salted
    for name, entry in salted:
        bare = normalise(name)
        found = CAT.resolve(bare)
        assert found is not None and found.inns == entry.inns, bare
        assert CAT.covers(bare), bare
        swapped = _swap_bv(bare)
        if swapped != bare:
            assert not CAT.covers(swapped), swapped
        for form in TOMAR:
            assert not CAT.covers(form + bare), form + bare


def test_anything_else_joined_to_a_name_never_matches():
    singles = [(name, entry) for name, entry in NAMES if " " not in normalise(name)]
    assert singles
    for name, _entry in singles:
        bare = normalise(name)
        for text in ("tomotomo" + bare, "tomo" + bare + "x", "tomo" + bare + "5",
                     "tomato" + bare, "tomaso" + bare, "xyz" + bare):
            assert CAT.resolve(text) is None, text


def test_a_separated_tomo_still_resolves_through_the_bare_name():
    for name, entry in NAMES:
        found = CAT.resolve("tomo " + normalise(name))
        assert found is not None and found.inns == entry.inns, name


def test_brand_helpers_follow_for_every_latin_brand():
    brands = [(name, entry) for entry in CAT.entries for name in (entry.brand, *entry.aliases)
              if not ARABIC_RE.search(name)]
    assert brands
    for name, entry in brands:
        bare = normalise(name)
        assert CAT.brand_entry(name) is not None and CAT.brand_entry(name).inns == entry.inns, name
        for text in ("tomo" + bare, _swap_bv(bare), "toma" + _swap_bv(bare)):
            assert CAT.matches_brand(text), text
            found = CAT.brand_entry(text)
            assert found is not None and found.inns == entry.inns, text


def test_mentions_moiety_follows_for_every_single_word_moiety_name():
    count = 0
    for entry in CAT.entries:
        if len(entry.inns) != 1:
            continue
        (moiety,) = entry.inns
        candidates = [moiety, *(a for a, (t, _) in INN_ALIASES.items() if t == moiety)]
        for candidate in candidates:
            bare = normalise(candidate)
            if ARABIC_RE.search(candidate) or " " in bare or bare in SALTED:
                continue
            count += 1
            for text in ("toman" + bare, _swap_bv(bare)):
                assert CAT.mentions_moiety(text, moiety), text
    assert count


def test_two_prefixed_products_still_resolve_to_none_and_read_ambiguous():
    pairs = 0
    seen = set()
    bare_names = [(name, entry) for name, entry in NAMES if normalise(name) not in SALTED]
    for (first, entry), (second, other) in itertools.product(bare_names, bare_names):
        if entry.inns == other.inns:
            continue
        key = tuple(sorted((entry.brand, other.brand)))
        if key in seen:
            continue
        seen.add(key)
        pairs += 1
        text = "tomo" + normalise(first) + " y toma" + normalise(second)
        assert CAT.resolve(text) is None, text
        assert CAT.is_ambiguous(text), text
    assert pairs


def test_arabic_clitics_resolve_as_before():
    count = 0
    for entry in CAT.entries:
        for alias in entry.aliases:
            if not ARABIC_RE.search(alias):
                continue
            count += 1
            base = CAT.resolve(alias)
            assert base is not None and base.inns == entry.inns, alias
            for clitic in ("ال", "وال", "بال", "فال", "لل", "و", "ف", "ب", "ل"):
                found = CAT.resolve(clitic + alias)
                assert found is not None and found.inns == entry.inns, clitic + alias
    assert count
