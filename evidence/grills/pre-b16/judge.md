# Idea grill: Claude Opus 5.5 subagent as a judge-panel stand-in, 27 Oct 2026

Read-only, with web access. Inputs: README, SPEC, decisions, supervisor triage, the Arabic live report, the video playbook, the idea committee notes, the prize list, and the public event pages. Its full answer, lightly formatted:

**Verdict:** Anamnesis is rigorous and honest, but judges can't see any of that yet. On the current plan it won't place, because the video gets the fewest hours and the weakest case.

**Sources:** the participant guide (cerebralvalley.ai/e/meta-ai-developer-hackathon/details) needs a login, so it wasn't read. The public event page (cerebralvalley.ai/e/meta-ai-developer-hackathon) says Indie is judged on "creativity, technical ambition, and whether it works", with judging 4–8 Nov.

| Criterion | /10 | Evidence |
|---|---|---|
| Creativity | 6 | Checking the voice note against the box, with provenance, is fresh; "AI reads a pill box" isn't |
| Technical ambition | 6 | 3 models, a validator, Arabic normalisation, 421 tests; but a fixed loop and 8 catalogue entries |
| Works | 4 (7 after B16/B17) | Runs live for $0.027, but on drawn labels and macOS `say` voices; JSON output only |

**Why it won't place:** the headline finding means "possibly fine, ask". It comes from a drawn label and a text-to-speech voice, and the video gets 2 of about 20 hours. It looks like a toy.

**Wedge:** right: a remote "bring all your medicine boxes" check. The user is the clinician or pharmacist reconciling medicines before the visit. "No advice" is a strength; it becomes a weakness only if the demo shows nothing but hedging.

**Top 5 (win probability per hour)**
1. Video 6 h, not 2 (0 h net): cut B17 to 4 cases (hero, multi-pack, rambling note, glare) and usability to 1 h at most.
2. A real hero case (1 h, inside B17): Ahmed's own Egyptian Arabic note (fictional history) and two real over-the-counter boxes with the same ingredient (Panadol + Gelocatil). B16's same-ingredient check catches it; "same medicine, two names" lands in 3 s. Concor + Beloc-Zok stays as case 2.
3. A hosted replay that needs no key (1.5 h): the B16 brief on GitHub Pages with the clip, the photo overlays and the real call count and cost.
4. Repeat runs (0.75 h): commit the expected results first, run the hero live 10× (about $0.30), report "same findings in N/10".
5. Check each reading belongs to its box (1 h at most): the first read sends the whole photo with the box as text coordinates. On a multi-pack photo, draw each box with its label_text; if one describes a neighbouring pack, read crops first. Wrong provenance blocks release.

**Stop / cut:** playbook claims nothing backs (FHIR, the guardrail chat, the open-weight table, "fatal bradycardia", "saves 6 minutes", an invented "93.3% recall", "anamnesis.meta.ai", a wrong repo URL); the automated video pipeline (use a screen recording, a voiceover and captions); testing it yourself and calling that the usability check (get one outside pharmacist by 31 Oct, or drop it).

**Zoom:** show it only if it fires on a real photo, matches the label written down beforehand and changes the finding. Otherwise show the system declining to read and asking for a clearer photo. Never degrade a photo to force the zoom.

**Credibility:** commits dated from 27 Oct (don't squash them), the logged rejections, the per-call cost ledger, and results that include misses. Overclaims hurt: SPEC line 3 called text-to-speech audio "Egyptian Arabic with code-switching" (fix today); words like "agent", "validated" or "prevents errors".

**Hook (20 s)**
- 0–5 s: caption "Before a video visit: one voice note, one photo." The Arabic note plays beside both boxes with English subtitles.
- 5–11 s: an amber card: "Same active ingredient in 2 products reported as current: paracetamol. Concurrent use unconfirmed." VO: "Two brand names, one medicine. He says he takes both."
- 11–17 s: a click replays his words and SAM outlines both boxes. VO: "His own words, and the exact box behind each fact."
- 17–20 s: lower third: "Muse Voice Transcribe · SAM 3.1 · Muse Spark. Flags disagreements and duplicates; gives no medical advice." VO: "I'm Ahmed Zayed, a physician. This is Anamnesis."
