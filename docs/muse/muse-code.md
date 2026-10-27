# Muse Code (the `muse` CLI)

Verified 2026-10-26

Meta's coding agent for the terminal and CI, built for Muse Spark; approvals and an OS sandbox are on from the first run ([overview](https://dev.meta.ai/docs/muse-code), [landing](https://dev.meta.ai/lp/muse-code)). Local install checked: `~/.local/bin/muse`, `Muse Code 1.4.13 (1.4.13-R6996.1)` (from `muse --version`; no login was performed while writing this).

## Install and login

- Install: `curl -fsSL https://dev.meta.ai/install.sh | sh` (macOS, Linux); Windows `irm https://dev.meta.ai/install.ps1 | iex` ([overview](https://dev.meta.ai/docs/muse-code)). The landing page shows `| bash` instead; both are shown by Meta. Put `~/.local/bin` on PATH.
- Login (do not do this unprompted): `muse login` approves a code in the browser; `/login` inside the TUI; or an API key. Priority: `META_API_KEY` env var, then a stored key (`muse auth set --api-key-stdin`, key read from stdin only), then the stored browser session. `muse logout` clears stored credentials but not an exported variable. Meta Managed Accounts must use an API key ([auth](https://dev.meta.ai/docs/muse-code/auth), local `muse login --help`, `muse auth set --help`).
- Note the variable name: Muse Code reads `META_API_KEY`; direct API calls use `MODEL_API_KEY` ([auth](https://dev.meta.ai/docs/muse-code/auth), [authentication](https://dev.meta.ai/docs/authentication)).
- Billing: pay-as-you-go tokens, or subscriptions: Everyday $5, High $15, Power $50, Maximum $200 per month ([landing](https://dev.meta.ai/lp/muse-code)). Subscriptions default to Contributor mode (Meta may train on your content); toggle in settings ([subscriptions](https://dev.meta.ai/docs/muse-code/subscriptions#contributor-mode)). Never send patient-like data in Contributor mode.

## Models, providers, effort

- Default model `muse-spark-1.2`; override with `--model` or `/models` ([configuration](https://dev.meta.ai/docs/muse-code/configuration)). Available: Spark 1.3 and 1.2 (Standard and Contributor), Muse Wonder, Muse Image; Wonder Full only on Power and Maximum plans; Spark 1.1 not available ([models](https://dev.meta.ai/docs/models)).
- `--reasoning-effort none|minimal|low|medium|high|xhigh|max|ultra`, default `high` (`ultra` is client-side). `muse model-profile show <model> --effort <tier>` prints how a model resolves per knob (local help, [configuration](https://dev.meta.ai/docs/muse-code/configuration)).
- `--provider echo|meta|local` (default meta) and `--base-url` exist (local `muse --help`). What `local` points at: Not documented.
- Settings file `~/.config/muse/settings.json` must contain `"schema_version": 1` or every command fails ([configuration](https://dev.meta.ai/docs/muse-code/configuration)).

## Headless: `muse exec`

```shell
muse exec "Update the changelog and run the tests."
muse exec --prompt-file ./task.txt
muse exec --json "..."            # JSONL events on stdout
```

Source: [extending, headless](https://dev.meta.ai/docs/muse-code/extending). Useful flags (local `muse exec --help`): `--output-schema <FILE>` (shape the final answer with a JSON schema, Meta provider only), `--image <PATH>` (repeatable), `--max-model-steps <N>`, `--workspace <PATH>`, `--session-id <UUID>`, `--approval-mode untrusted|on-request|never`, `--disable-approval` (keeps sandbox), `--yolo` (no approval, no sandbox, trusts workspace; disposable containers only), `--disable-web-tools`, `--no-session-log`. Exit code: 0 = turn completed, 1 = failed or cancelled (including step cap), 2 = usage error, 130/143 = signal. Exit 0 does not mean the work is correct; run your own tests. A headless run cannot answer approval prompts, so pick the policy up front. On Linux CI the sandbox needs bubblewrap.

Sandbox network default is `proxy-only` (`--sandbox-network restricted|enabled|proxy-only`), so shell commands that call APIs may need `enabled` ([permissions](https://dev.meta.ai/docs/muse-code/permissions)).

## Voice

- `muse voice transcribe <FILE>` prints the words in an audio clip ("Slack's audio_message.m4a, or any wav") (local `muse voice transcribe --help`). Backend and limits: Not documented. For a real ASR integration use [muse-voice-transcribe.md](muse-voice-transcribe.md).
- In the TUI, Alt+V (option-V on macOS) toggles voice dictation; on by default on macOS, unavailable on Windows ([interactive](https://dev.meta.ai/docs/muse-code/interactive#voice)).

## Skills

Sources: built-in, user (`$XDG_CONFIG_HOME/muse/skills`, `~/.agents/skills`, and by default also `~/.claude/skills` and `$CODEX_HOME/skills`), project (`<repo>/.agents/skills/<id>/SKILL.md`, also `.claude/skills`, `.codex/skills`), plugin ([extending](https://dev.meta.ai/docs/muse-code/extending#skills)). Commands: `muse skills list|inspect|enable|disable|install|validate|update|uninstall`, and `muse skills import --from claude|codex` (local `muse skills --help`). Built-ins include `plan`, `grill`, `taste`, `git`, `create-skill`, `migrate`, `resume-claude`, `resume-codex`, `doctor` (local `muse skills list --source built-in`). Project skills load only after you trust the workspace.

## `muse init`, AGENTS.md and config

`muse init` writes ONE file, `AGENTS.md`, in the current directory and nothing else; `--dry-run` previews, `--force` overwrites ([configuration](https://dev.meta.ai/docs/muse-code/configuration)). The dry-run template has sections Project (name), Common Commands, Project Layout (checked locally in an empty scratch dir). Instruction lookup walks from the workspace root up to the nearest `.git`; at each level the first of `AGENTS.md`, `CLAUDE.md`, `.agents/AGENTS.md`, `.claude/CLAUDE.md` wins. Project rules load only after the workspace is trusted. Muse Code does not commit or push unless asked.

## Using other agents with Meta models

Claude Code or the Anthropic SDK: base URL `https://api.meta.ai` via the Messages API. Codex: `~/.codex/config.toml` with `wire_api = "responses"`. OpenCode: `@ai-sdk/openai` provider with base URL `https://api.meta.ai/v1` ([coding agents](https://dev.meta.ai/docs/coding-agents), [quickstart](https://dev.meta.ai/docs/quickstart)). SDK for driving Muse Code from code: `npm install @muse-code/sdk`, protocol via `muse serve` / `muse schema` ([overview](https://dev.meta.ai/docs/muse-code)).

## Cookbook: `04_muse_code` recipes

Source: [04_muse_code README](https://github.com/meta-models/meta-model-cookbook/tree/main/04_muse_code). Directories `01_append_only_audit_log`, `02_deterministic_replay`, `03_staged_approvals`, `04_contained_execution` exist exactly as named.

| # | Recipe | One line |
|---|---|---|
| 01 | append_only_audit_log | Export the append-only session log as replayable evidence; kill the harness mid-task and resume with no duplicate side effects |
| 02 | deterministic_replay | Turn recorded events into a golden fixture and replay it in CI as a merge-blocking check |
| 03 | staged_approvals | Split compound shell commands into stages, auto-clear safe ones, hold risky or unparseable ones; fails closed |
| 04 | contained_execution | Run shell commands in an OS sandbox that probes its own enforcement and refuses to run if containment fails |
| 05 | immutable_guardrails | The agent cannot rewrite its own guardrail file; the write stops for human review |
| 06 | subagent_fanout | Parallel subagents each in an isolated git worktree, steered from one point |
| 07 | goal_tracking | Pin an objective with `/goal`; it is audited against acceptance checks before closing |
| 08 | bundled_skills | Drive built-in `/plan`, `/grilling`, `/grill-with-docs`, `/taste` end to end |
| 09 | loop_and_cron | Schedule recurring or one-time agent work in natural language |
| 10 | side_chats | Branch a side conversation with `/side` (alias `/btw`) off the main thread |
| 11 | mcp_security_tooling | Wire Burp Suite, Ghidra and LLDB into Muse Code over MCP for security research |

Other cookbook sections: 01_api_fundamentals (10 notebooks), 02_agent_patterns, 03_use_cases (15), 05_muse_image, 06_muse_voice, 07_sam ([README](https://github.com/meta-models/meta-model-cookbook)).
