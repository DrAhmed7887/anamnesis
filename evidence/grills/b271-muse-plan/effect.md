# Effect of Muse's plan grill on batch 27.1 (31 Oct, CEO)

Verdict: "Accept with the fixes below". The session's model is `muse-spark-1.3` throughout; the `contributor` count is the product's own refusal string.

| # | Muse's point | Effect |
|---|---|---|
| R1 | "five day course" and "one hour before breakfast" become durations | **Intended:** those numbers are a course length and a time, never a dose. "ten a day" is pinned as a daily amount. |
| R2 | Spanish and German per-day phrases overlap with duration words | **Already so:** the duration check looks only at the one word right after the run, so "diez al día" and "zehn am Tag" aren't durations. |
| R3 | Count before duration | **Yes:** rule 3's count comes first; "two tablets a day for a week" stays a count. |
| R4 | "weiß nicht" adjacency | **As designed:** the negation must be right after the word of knowing, in the same clause; "nicht fünf" still drops (pinned). |
| R5, R6 | The tablet-count drop and the pairing rule | **As designed:** only after a relation-check drop, kept when a rule-3 count of that value exists, applied before the pairing step. |
| Q1 | Only "nicht", or every negation word, after a word of knowing? | Every negation word, as the SPEC says; "nicht" is the case that occurs. |
| Q2 | Does a value-check drop also take unbacked units? | No: only a relation-check drop. The value check's behaviour stays as before batch 27. |
| Q3 | Does a dropped strength take units too? | Yes: "a claim's amount" covers the strength's amounts and the intake. |
| Q4 | A count word and a duration word in the same window? | Count first. |

No change to the SPEC or the contract.
