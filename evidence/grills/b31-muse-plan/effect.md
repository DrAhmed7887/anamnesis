# Batch 31 plan: triage of Muse's read-only plan (1 Nov, 13:20)

Muse's reply is in `muse.md`. The session used `muse-spark-1.3` only: every "contributor" hit in `muse_session.json` is the brief's or SPEC's own text.

| # | Muse's point | Verdict | Where it goes |
|---|---|---|---|
| 1 | The follow-up loop: code opens each request, sends only template text, processes replies through `add_photo`, stops on nothing requestable or the round limit, and never approves | **Taken** | SPEC §8 "The follow-up by itself"; `tests/contract/test_b31_follow_up.py` |
| 2 | One bounded model choice: a model picks which requestable target goes next, or STOP | **Not taken.** A model's STOP is the one way the loop could leave evidence ungathered. With code asking every requestable target within the round limit, the order doesn't change the result. It would add a model call and a prompt each round, and it would break SPEC.md:349 ("no model chooses an action"), the verifiable-agent design the brief is built on | — |
| 3 | Risk: a loop that never ends | **Taken:** a round limit, and a stop when nothing new is requestable | contract: round limit |
| 4 | Risk: a reply that changes old evidence | **Taken:** turns, claims and earlier observations are kept, and only the answered pack is superseded | contract: evidence kept |
| 5 | Risk: spend across rounds | **Taken:** each reply gets `add_photo`'s own call budget, and the total is bounded by asks × budget | contract: calls bounded |
| 6 | Risk: asking again for something already given | **Taken:** a repeated photo is logged `duplicate` and sent to no model, and a target with an open request isn't asked again | contract: duplicate, open request |
| 7 | Risk: skipping the approval | **Taken:** follow-up never approves, and refuses an approved review | contract: never approves |
| 8 | Risk: a model inventing text or a target | **Taken** as "every message is a template", and moot for targets, since no model picks one | contract: messages |
| Q1 | The round limit | **2:** a pack still unreadable after its new photo gets one more try | SPEC |
| Q2 | No reply | **The request stays open** (the brief says it waits for the patient), and that target isn't asked again | SPEC |
| Q3–Q4 | What the model sees, and which model id | **Moot** (row 2) | — |
