# What the CEO took from Muse's audit of batch 34 (2 Nov)

A fresh Muse Code session audited the build read-only (`brief.md`, `muse.md`), on muse-spark-1.3 only, for $0.26079 at `muse_usage.price` (387,203 input tokens, 260,631 of them cached, and 14,936 output). Its verdict was pass, with one Low finding.

1. **A decomposed (NFD) "cálcica" isn't read (Low):** right, and the supervisor's #3 says the same, more precisely: a part's label is composed by the schema's validator, so it is read there, but not in a name or label text, because `catalogue.normalise` doesn't compose. The proposed fix, composing only inside `_loose_salts`, would treat Spanish salt words differently from every other name the product matches. Not taken; written into SPEC rule 6's known limits, beside the README's older NFD limit.
