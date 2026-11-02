# What the CEO took from Muse's plan for batch 33 (2 Nov)

Muse Code planned read-only (`brief.md`, `muse.md`), on muse-spark-1.3 only, for $0.2562 at `muse_usage.price` (252,397 input tokens, 107,987 of them cached, and 13,991 output). It agreed with the candidate: the change goes in `_side_salts`, through `_text_salts`, because the joined label needs the loose salt-word pass.

**Taken into the contract**
- Risk 3, one longer alias gives one salt: `test_one_longer_alias_gives_one_salt` (atorvastatin calcium, and calcium trihydrate).
- Risk 4, the "(as …)" form: "metoprolol (as succinate)" is in `SUCCINATE_LABELS`.
- Risk 5, Arabic: `test_an_arabic_brand_label_with_a_salt_of_its_moiety` (نورفاسك with maleate).
- Risk 6, a pack reading that names two salts abstains: `test_a_pack_reading_that_names_two_salts_abstains`. Muse was right that this is `insufficient_information`, not `formulation_mismatch`.
- Risk 7, each label on its own: the parametrized cases.
- Risk 8, nothing newly agrees: in rule 7 a claim with no salt still matches through the pack's salt-basis equivalents, and one with a label salt behaves as the exact label does. A further break test pins that the pack's salt-basis lookup doesn't start reading labels.
- Risk 2, a combination: `test_a_combination_keeps_its_salts_apart` (Augmentin).

**Not taken**
- Risk 1, two moieties in one ingredient label: such a part already fails its side's identity, so it can't reach the salt rule. The supervisor may probe it.
- The proposed `spanish_salt_still_unread` test: it would make a known false agreement ("Metoprolol succinato" matching tartrate) something the code must keep. SPEC keeps it as a known limit instead.

**The CEO's slip:** the plan brief cited "SPEC.md §6" for the decision order, which is §3. Muse found the rule anyway (it cites SPEC.md:303).
