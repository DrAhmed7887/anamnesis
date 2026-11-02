# What the CEO took from Muse's plan for batch 34 (2 Nov)

Muse Code planned read-only (`brief.md`, `muse.md`), on muse-spark-1.3 only, for $0.26612 at `muse_usage.price` (382,468 input tokens, 237,463 of them cached, and 11,586 output). It chose the CEO's candidate over the alternative: a separate table of Spanish salt words, read only in `_loose_salts`. Adding the Spanish names to `INN_ALIASES` would also change `canonical_inn`, `salt_of`, the validator, the claim parser's grounding and name matching.

**Taken into the contract**
- Risk 3, a Spanish and an English name of one salt are one salt: `test_a_spanish_and_an_english_name_of_one_salt_are_one_salt`.
- Risk 4, Spanish words that are ordinary words: the moiety-or-brand check (`test_a_spanish_salt_word_counts_only_beside_its_moiety_or_brand`). "calcio" is left out of the table (`test_calcio_the_noun_is_not_a_salt`).
- Risk 5, the hero's boxes now carry a salt: `test_the_spanish_heros_findings_stay`, with the name as said in set 3 and as heard in set 5.
- Risk 6, the only new abstentions are a side naming two salts: `test_two_salts_on_one_side_abstain`.
- Risk 7, nothing starts to agree, name matching included: `test_name_matching_is_unchanged`, and the 205 saved reports in `reference.md`.
- Risks 8 and 9, word order and punctuation, and the scalar `inn`: the parametrized labels, and `test_the_scalar_inn_is_read_as_before`.

**Not taken**
- Risks 1 and 2 as proposed: their tests expected `formulation_mismatch` from calcium against calcium trihydrate, which would pin a known limit (SPEC rule 6). Instead, `test_each_spanish_name_reads_as_its_english_name` asserts that each Spanish name gives what its English name gives, and `test_one_longer_spanish_salt_gives_one_salt` pins the suppression.
- Its `spanish_fumarato_label_vs_pack` test (fumarate against a "non-fumarate" bisoprolol pack): the only other bisoprolol salt is hemifumarate, the same known limit.
- Its table's "sódica", "sodica" and "potasio": amoxicillin and clavulanic acid are catalogued only in a combination, where a loose salt word can't attach, and both are ordinary words in diet text. "trihidrato" alone is left out for the same reason.
