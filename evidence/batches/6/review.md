# Batch 6 review: live format fixes (reviewer-built)

Built by Claude Code directly: a 3-line change didn't justify a Sol run. Gate: pass, 196 tests.

Verdict: PASS

## What the first live calls showed (27 Oct 2026, synthetic media, $0.0162 total so far)
- **Voice Transcribe:** worked first time in English and in Egyptian Arabic with code-switching. `keywords` biasing brought "BelocZok" back in Latin script in the middle of an Arabic sentence.
- **SAM 3.1:** the concepts "medicine box", "box", "white rectangle" and "medicine package" returned **0 regions** on the flat mock photo. **"label" found both packs**, with exact boxes. Its output differs from `docs/muse/sam-3-1.md` in two ways:
  1. The mask carries its own confidence: `<|mask;x=0;y=0;c=0.59;data=…|>`.
  2. The text ends with `\n`.
- Our parser rejected that output as malformed.

## Fix
- The mask header accepts an optional `;c=…`, and trailing whitespace is stripped.
- Contract: `tests/contract/test_b6_live_format.py` replays the **real captured output** (`tests/fixtures/sam31_label_packs_live.txt`) and pins both pack boxes.

## Noted
- The SAM response carried `"store": true`, so Meta keeps the response. That's fine for synthetic media. Real patient photos are out of scope for this project anyway.
