# Batch 22: supervisor review

## Round 1 (Opus 5.5, high effort, 28 Oct). Builder: Muse Code (`muse-spark-1.3`)

SUPERVISOR: CHANGES

The verdict rests on finding 1. The other findings are minor and don't block the merge.

**1. major: `anamnesis/providers/numbers.py:37-42`. A qualified word amount is now read as an exact amount and can reach `match`.**
- **Cause:** the new branch only checks that the stripped text is one whitespace token. It then runs `catalogue.normalise`, which turns punctuation into spaces. So `"-five"`, `"~five"`, `"<five"`, `">five"`, `"five?"`, `"five+"`, `"five%"`, `"≈five"`, `"(five)"` and `"five."` all parse as 5. The digit forms (`"-5"`, `"<5"`, `"~5"`) still give None.
- **Negatives:** SPEC §2 says negatives never parse, but `"-five"` now does.
- **Input run end to end** (`run_intake`, contract helpers, pack "Concor 5 mg" with bisoprolol 5 mg):
  - Turn: "I take Concor, less than five milligrams."
  - Claim `intake_amount.amount`: `"<five"`.
  - After the change: intake 5 mg, finding `match`.
  - At the lock: intake None, `insufficient_information`. With `"<5"` it is still `insufficient_information`.
  - `">five"` ("more than five"), `"five?"` ("maybe five"), `"~five"` ("about five") and `"-five"` all give `match` after the change and `insufficient_information` at the lock.
- **Why the stated-amount check doesn't stop it:** the patient did say "five", so 5 is in `stated_amounts`.
- **Same root, also run:** `normalise` strips tashkeel. So «خُمس» (a fifth), «عُشر» (a tenth), «سُبع» and «تُسع» become 5, 10, 7 and 9. The damma is the only mark that separates them from the numbers.
- **Fix:** before `normalise`, require the stripped text to be letters plus tatweel only: `_WORD_RE = re.compile(r"(?:[^\W\d_]|ـ)+")`, and `if not _WORD_RE.fullmatch(value.strip()): return None` in place of line 37.
- **Fix tested** in the after copy: 1075 passed; every contract word case still parses, including tatweel and alef/ya/ta-marbuta variants, «خمسمية», «ميتين» and «الفين»; all the qualified forms and the tashkeel fractions give None; the `"<five"` input falls back to `insufficient_information`. With the fix, the second split check at line 43 becomes dead code.

**2. minor: `anamnesis/providers/openweight.py:67`. The contributor refusal is narrower than `scripts/batch.sh:77`.**
- `batch.sh` refuses `*-contributor*`. The reader only refuses an exact `-contributor` suffix.
- Refused: `muse-spark-open-contributor`. Accepted: `muse-spark-open-Contributor`, `muse-spark-open-contributor-v2`, `accounts/fireworks/models/muse-spark-open-contributor:latest` and `"muse-spark-open-contributor "` (trailing space).
- The real model id never reaches the trace or the ledger, which only name `price_key`, so `ProviderTrace`'s own check can't catch these either. The builder followed the brief's wording ("ending in"), which is where the gap comes from.
- **Fix:** `if "-contributor" in model.strip().casefold(): raise ValueError(...)`.

**3. minor: `openweight.py:120, 130` (and the `exc.provider` pass-through at 139). The reader's own errors name `"spark"`.**
- The client's errors correctly say `fireworks`/`baseten`. But a malformed reply, a length stop or a failed label parse from the open-weight reader carries `provider == "spark"`. Ran: a reply with advice in `inn` gives `ProviderError.provider == "spark"`.
- `anamnesis/agent/session.py:15` prints `error: {exc.provider} …`. In a run comparing Spark 1.3 with the open-weight model, these failures would be counted as Spark's.
- **Fix:** raise with `self.client.provider` at 120 and 130, and pass it at 139 instead of `exc.provider`. The "Meta …" message text is cosmetic while the `provider` field is right.

**4. minor: four mutants of `openweight.py` survive the full suite** (each still gave 1075 passed):
- the estimate priced with the wrong key (`"model": "muse-spark-1.3"`), which survives because the two prices are identical;
- estimated ledger lines named with the real model id (`with_one_retry(..., model_id=self.model)`);
- the timeout argument dropped (the client falls back to 30 s);
- `_safe` removed from the parse-error path (a test gap only, the same as `MetaLabelReader`).
- Caught: the length stop made retryable, plus the contract's checks on provider, contributor, `response_format` and fence.

**5. minor (maintainability): `openweight.py:29, 75-144`.** `_data_url` is a copy of `meta._data_url`: import it. `read()` is about 70 lines and copies `MetaLabelReader.read`; the contract's body-equality test pins the messages, so drift would be caught. Note only.

**Probes run** (scratch copies only; the worktree untouched)
- Earlier contract cases: base gives 10 failed, 1031 passed, 1 collection error; the 10 failures are exactly the 9 new word cases plus the b16 `"two"` case. After the change, 1075 passed, so no earlier contract outcome flipped. `catalogue.normalise` only runs on the new fallback branch; `stated_amounts` calls `parse_amount_text` only on digit runs.
- Word parsing beyond finding 1 behaves as the brief asks: "five hundred", "twenty-five", "five5", "5five", "fivemg", "five-mg", "five/ten", "½", "once", "twice", "thrice", "zero", "half", "hundred", "thousand", «ألف», «مية», «نص», «صفر», «ربع», «تلت», «ثلث», clitics («وخمسة», «الخمسة», «بخمسة») and «خمسة٥» give None. `"FİVE"`, fullwidth `ｆｉｖｅ` and `Ⅴ` give None; `"ſix"` gives 6 (harmless). `regimen.units_per_intake` and `intakes_per_day` have no stated check, so a word there now parses the way a digit already did: not a new class of risk.
- Imports: `numbers`, `stated`, `catalogue` or `openweight` imported first, each in a fresh interpreter, all work; no cycle and no new import-time side effect.
- `OpenWeightClient` keeps every `MetaClient` behaviour against a mock transport (timeout, transport error, 500, non-JSON 200 and a JSON array are retryable and billable-uncertain with 2 estimated ledger lines; 401 is neither, with none), with `provider` `fireworks` in every case.
- API key: redacted in every message, absent from `repr(client)`, the headers' `repr` and a formatted traceback. Reachable only as an object behind a suppressed context (`__context__.request.headers` on httpx errors raised `from None`, and `JSONDecodeError.doc` if a server echoes the key in a non-JSON body), both inherited from `MetaClient` unchanged.
- Request messages are byte-identical to `MetaLabelReader`'s, cropped and uncropped, apart from the one appended schema sentence; no `reasoning_effort`, and no `response_format` with JSON mode off.
- Spend: the estimate is priced by `price_key` while the real model id is sent; the cap refuses before any request; both attempts are charged on a retry; a length stop is charged once and not retried.
- Fence strip removes one surrounding ```` ``` ```` or ```` ```json ```` fence. Everything else (```` ```JSON ````, ```` ```js ````, prose before the fence, two fences, a lone ```` ``` ````) goes to `parse_label_json` as is and fails safe as a malformed reply, retried once with both attempts charged. A fence inside a JSON string is left alone.
