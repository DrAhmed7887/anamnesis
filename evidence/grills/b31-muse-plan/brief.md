# Batch 31 design: one feature for the Best Agentic Use-Case prize

You are planning, not building. Work read-only:
- don't create, edit or delete any file;
- run no git command that changes state;
- make no network call, and use no API key;
- don't open anything under `evidence/` or `finetune/data*`, nor any `.env` file.

## 1. Goal
The plan is done ONLY when your reply has the five sections in §5, and every point cites a file and line you opened in this session.

## 2. The prize, and where the product stands
- **The prize, as the participant guide describes it:** it rewards the project that makes the strongest use of AI agents to complete meaningful tasks, make decisions or coordinate multi-step workflows. Judges weigh the level of autonomy, how well it completes its task, and practical usefulness.
- **Today:** the intake runs a fixed order of steps (`SPEC.md` §4, `anamnesis/agent/loop.py`), then stops for a person. If a pack is unreadable or a named medicine wasn't photographed, the clinician asks the patient for one new photo, and only that photo is processed (`anamnesis/review.py`: `requestable`, `request_photo`, `request_message`, `add_photo`, `approve`; `SPEC.md` §8). No model chooses an action (`SPEC.md`:349).

## 3. Hard limits: every proposal keeps all of them
- No medical advice. Every sentence shown to the patient or the clinician comes from `anamnesis/schema/templates.py`.
- Nothing is final until the clinician approves (`review.py`, `approve`).
- Every finding keeps its provenance: its turn and its region.
- Spend stays bounded by the session's call budget and dollar cap. No new model id, and no `*-contributor` model.
- It is one feature, buildable tonight in one small batch, with contract tests that run offline against fixture adapters.

## 4. The CEO's candidate: challenge it, or beat it
**The follow-up runs by itself.** A `follow_up(...)` function:
1. takes each target that `requestable(report)` returns;
2. opens the request and sends the patient the fixed `request_message`;
3. gets the patient's reply through a callback (a new photo, or nothing);
4. processes it through `add_photo`;
5. repeats until nothing is requestable or a round limit is reached;
6. returns the updated report and review, still a draft, with a log of what it asked and what came back.

The questions, their order and the stopping rule are fixed in code. Models only transcribe and read.

You may propose something stronger: for example, a model that makes a bounded decision. If you do, say exactly what the model decides, from which fixed set of options, and why every hard limit still holds.

## 5. Reply
1. **The feature:** one paragraph. Say what it does, what decides each step (code or a model), and why it scores on autonomy, effectiveness and usefulness.
2. **The design:** the functions, their signatures and what they return, where each change goes (file:line), and what the brief shows afterwards.
3. **Risks:** numbered, each with a file:line and how a test pins it. For instance: a loop that never ends, a reply that changes evidence it shouldn't, spend across rounds, a request for something already given, the approval gate.
4. **The contract:** the tests you would write first, each named with a one-line assertion.
5. **Open questions for the CEO.**

Keep it under 700 words.
