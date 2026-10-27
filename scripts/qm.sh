#!/bin/zsh
# Quality-manager review of a milestone, by Gemini 4 Argon (Medium) via Antigravity.
#   scripts/qm.sh <milestone-dir> <first-batch> <last-batch>
# Builds one self-contained package (prompt + evidence + spec + key code) so the model needs no tools.
# Output: evidence/grills/<milestone>/qm.md. Package and raw log: evidence/raw/ (git-ignored).
# Manual alternative: paste evidence/raw/<milestone>-qm-package.md into Antigravity with model Gemini 4 Argon (Medium).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
m=${1:?milestone dir}; first=${2:?first batch}; last=${3:?last batch}
dir="evidence/grills/$m"
pkg="evidence/raw/$m-qm-package.md"
mkdir -p evidence/raw

section() { printf '\n\n===== %s =====\n' "$1"; }
{
  cat evidence/grills/QM_PROMPT.md
  section "PACKAGE: milestone $m, batches $first-$last"
  for f in evidence/grills/*/effect.md SPEC.md evidence/decisions.md evidence/batch_log.jsonl evidence/spend/ledger.jsonl; do
    [[ -f $f ]] && { section "$f"; cat "$f"; }
  done
  for n in $(seq "$first" "$last"); do
    for f in briefs/$n.md evidence/batches/$n/review.md evidence/batches/$n/gate.json; do
      [[ -f $f ]] && { section "$f"; cat "$f"; }
    done
  done
  section "git log (first-parent, last 40)"; git log --first-parent --oneline -40
  section "contract tests (names)"; uv run pytest -q --collect-only tests/contract 2>/dev/null | grep '::' | sed 's/\[.*//' | sort -u
  section "test totals"; uv run pytest -q 2>&1 | tail -1
  for f in anamnesis/core/reconcile.py anamnesis/core/catalogue.py anamnesis/schema/findings.py anamnesis/providers/base.py; do
    section "$f"; cat "$f"
  done
} > "$pkg"
print "package: $pkg ($(wc -c < "$pkg" | tr -d ' ') bytes)"

inbox="${QM_SESSIONS_INBOX:-/nonexistent}"
before=$(ls "$inbox" 2>/dev/null | wc -l | tr -d ' ')
# Flags must come before -p: agy reads the word right after -p as the prompt.
agy --model gemini-4-argon-medium --sandbox --disable-slash-commands --print-timeout 600s \
  -p "$(cat "$pkg")" </dev/null > "evidence/raw/$m-qm.out" 2>&1 || print "agy exited non-zero" >> "evidence/raw/$m-qm.out"
cp "evidence/raw/$m-qm.out" "$dir/qm.md"
after=$(ls "$inbox" 2>/dev/null | wc -l | tr -d ' ')
[[ $before == $after ]] || print -u2 "WARNING: Antigravity wrote $((after - before)) file(s) to QM_SESSIONS_INBOX"
head -1 "$dir/qm.md"
