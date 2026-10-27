#!/bin/zsh
# Quality-manager review of a milestone, by Gemini 4 Argon (Medium) via Antigravity.
#   scripts/qm.sh <milestone-dir> <first-batch> <last-batch> [evidence|code]   (batch numbers may be decimal: 15.5)
# Builds one self-contained package so the model needs no tools. agy cuts a long prompt off (a 315 KB package
# reached Gemini as about 191 KB, QM M4, 27 Oct), so a large milestone is audited in two halves: "evidence"
# (grill tables, briefs, reviews, ledgers) and "code" (SPEC, contract test names, the code). With no part given,
# one package holds both. The package ends with a marker, and the model says PACKAGE TRUNCATED when it can't see it.
# Output: evidence/grills/<milestone>/qm.md (qm-evidence.md, qm-code.md for a half). Packages and raw logs:
# evidence/raw/ (git-ignored). Manual alternative: paste the package into Antigravity with Gemini 4 Argon (Medium).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
m=${1:?milestone dir}; first=${2:?first batch}; last=${3:?last batch}; part=${4:-all}
case $part in
  all) tag="" ;;
  evidence|code) tag="-$part" ;;
  *) print -u2 "qm: the part is evidence or code"; exit 1 ;;
esac
dir="evidence/grills/$m"
pkg="evidence/raw/$m-qm$tag-package.md"
raw="evidence/raw/$m-qm$tag.out"
limit=180000
mkdir -p evidence/raw "$dir"

section() { printf '\n\n===== %s =====\n' "$1"; }

evidence_part() {
  for f in evidence/grills/*/effect.md README.md CLAUDE.md SPEC.md evidence/decisions.md evidence/batch_log.jsonl \
           evidence/spend/ledger.jsonl evidence/spend/muse_ledger.jsonl; do
    [[ -f $f ]] && { section "$f"; cat "$f"; }
  done
  for n in $(ls evidence/batches | sort -n); do
    (( n >= first && n <= last )) || continue
    for f in briefs/$n.md evidence/batches/$n/round*-brief.md(N) evidence/batches/$n/review.md evidence/batches/$n/supervisor.md \
             evidence/batches/$n/gate.json evidence/batches/$n/goal.md evidence/batches/$n/usage.json; do
      [[ -f $f ]] && { section "$f"; cat "$f"; }
    done
  done
  section "git log (first-parent, last 40)"; git log --first-parent --oneline -40
}

code_part() {
  if [[ $part == code ]]; then section "SPEC.md"; cat SPEC.md; fi
  section "contract tests (names)"; uv run pytest -q --collect-only tests/contract 2>/dev/null | grep '::' | sed 's/\[.*//' | sort -u
  for f in anamnesis/core/reconcile.py anamnesis/core/catalogue.py anamnesis/core/overlap.py anamnesis/core/guardrails.py \
           anamnesis/schema/findings.py anamnesis/schema/templates.py anamnesis/schema/report.py anamnesis/providers/base.py \
           anamnesis/providers/spend.py anamnesis/providers/meta.py anamnesis/providers/claims.py anamnesis/providers/spark.py \
           anamnesis/providers/numbers.py anamnesis/agent/*.py anamnesis/brief.py anamnesis/brief_html.py; do
    section "$f"; cat "$f"
  done
}

{
  cat evidence/grills/QM_PROMPT.md
  if [[ $part == code ]]; then
    printf '\nThis is the **code half** of the milestone package: SPEC, the contract test names and the code. The evidence half (grill tables, briefs, reviews, ledgers) is audited separately. Judge areas 2, 4, 5 and 8 here; leave out 1, 3, 6 and 7.\n'
  elif [[ $part == evidence ]]; then
    printf '\nThis is the **evidence half** of the milestone package. The code is audited separately. Judge every area from the evidence.\n'
  fi
  section "PACKAGE: milestone $m, batches $first-$last ($part)"
  if [[ $part != code ]]; then evidence_part; fi
  section "test totals"; uv run pytest -q 2>&1 | tail -1
  if [[ $part != evidence ]]; then code_part; fi
  section "END OF PACKAGE $m"
} > "$pkg"
size=$(wc -c < "$pkg" | tr -d ' ')
print "package: $pkg ($size bytes)"
(( size <= limit )) || print -u2 "WARNING: $size bytes is over the ${limit}-byte budget agy delivers whole; run the evidence and code halves"

inbox="${QM_SESSIONS_INBOX:-/nonexistent}"
before=$(ls "$inbox" 2>/dev/null | wc -l | tr -d ' ')
if [[ ${QM_VIA:-agy} == vertex ]]; then
  # The same model on Vertex AI, billed to the gcloud project's billing account, when agy's quota is used up.
  uv run python scripts/vertex_ask.py "$pkg" --thinking medium > "$raw" 2> "$raw.usage" \
    || print "vertex exited non-zero" >> "$raw"
  cat "$raw.usage" >&2
else
  # Flags must come before -p: agy reads the word right after -p as the prompt.
  agy --model gemini-4-argon-medium --sandbox --disable-slash-commands --print-timeout 600s \
    -p "$(cat "$pkg")" </dev/null > "$raw" 2>&1 || print "agy exited non-zero" >> "$raw"
fi
cp "$raw" "$dir/qm$tag.md"
after=$(ls "$inbox" 2>/dev/null | wc -l | tr -d ' ')
[[ $before == $after ]] || print -u2 "WARNING: Antigravity wrote $((after - before)) file(s) to QM_SESSIONS_INBOX"
head -2 "$dir/qm$tag.md"
