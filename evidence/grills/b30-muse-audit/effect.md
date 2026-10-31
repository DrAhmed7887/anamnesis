# Effect of the fresh Muse audit on batch 30 (31 Oct, CEO)

Verdict: "Request changes — combined-`inn` salts are dropped (false-`match` risk), plus two minor split gaps." The session's model is `muse-spark-1.3` throughout; the `contributor` count is the product's own refusal string.

| # | Finding | Effect |
|---|---|---|
| 1 | High: salts named in a combined `inn` never reach the salt rules | **Accepted into round 2:** one salt pair per part. The Opus supervisor found the same, with three false-`match` probes. |
| 2 | Low: a single part left by a stray separator resolves the raw string | **Accepted into round 2.** |
| 3 | Low: an «و» attached to the next word doesn't split | **Rejected:** Arabic drug names can begin with «و» («وارفارين», warfarin), so an attached «و» can't be split safely. It stays a known limit that fails safe; the SPEC now asks for a spaced «و» only. |
