#!/bin/zsh
# One build batch, gated. Every step leaves evidence in evidence/batches/<n>/.
#   scripts/batch.sh start <n> <slug>   branch batch/<n>-<slug> from main (then commit tests/contract + briefs/<n>.md)
#   scripts/batch.sh run <n>            Muse Code (muse-spark-1.3) writes the code from briefs/<n>.md, then the gate runs
#   scripts/batch.sh gate <n>           rerun the gate (after a fix)
#   scripts/batch.sh merge <n>          needs "Verdict: PASS" in evidence/batches/<n>/review.md
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

cmd=${1:?command}; n=${2:?batch number}
ev="evidence/batches/$n"
log="evidence/batch_log.jsonl"
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
# Changes in build paths only: files other tools leave elsewhere in the repo do not block a batch.
build_changes() { git status --porcelain -- anamnesis tests briefs scripts SPEC.md pyproject.toml uv.lock; }

contract_base() {
  # The commit that added this batch's contract tests: the reference the gate compares against.
  git log --format=%H -1 --grep="^test(contract): batch $n\$" || true
}

gate() {
  local base; base=$(contract_base)
  [[ -n $base ]] || { print -u2 "gate: no 'test(contract): batch $n' commit on this branch"; return 1; }
  local touched
  touched=$( { git diff --name-only "$base" -- tests/contract; git ls-files --others --exclude-standard tests/contract; } | sort -u)
  local result=pass reason="" tests="0"
  if [[ -n $touched ]]; then
    result=fail reason="contract tests were edited: ${touched//$'\n'/ }"
  elif ! uv run ruff check . > "$ev/ruff.log" 2>&1; then
    result=fail reason="ruff failed (see ruff.log)"
  elif ! uv run pytest -q > "$ev/pytest.log" 2>&1; then
    result=fail reason="pytest failed (see pytest.log)"
  fi
  [[ -f $ev/pytest.log ]] && tests=$(grep -Eo '[0-9]+ passed' "$ev/pytest.log" | grep -Eo '[0-9]+' || print 0)
  git add -N anamnesis tests 2>/dev/null || true   # count new build files in the diff stat
  local stat; stat=$(git diff --shortstat "$base" | sed 's/^ //')
  print -r -- "{\"batch\":$n,\"result\":\"$result\",\"reason\":\"$reason\",\"tests_passed\":$tests,\"diff\":\"$stat\",\"at\":\"$(now)\"}" > "$ev/gate.json"
  cat "$ev/gate.json"
  [[ $result == pass ]]
}

case $cmd in
  start)
    slug=${3:?slug}
    [[ -z $(build_changes) ]] || { print -u2 "start: working tree not clean"; exit 1; }
    git switch -q main
    git switch -c "batch/$n-$slug"
    mkdir -p "$ev"
    ;;
  run)
    model=${3:-muse-spark-1.3}
    [[ $model != *-contributor* ]] || { print -u2 "run: contributor models are forbidden"; exit 1; }
    [[ -f briefs/$n.md ]] || { print -u2 "run: briefs/$n.md missing"; exit 1; }
    [[ -n $(contract_base) ]] || { print -u2 "run: commit the contract tests first"; exit 1; }
    [[ -z $(build_changes) ]] || { print -u2 "run: working tree not clean"; exit 1; }
    mkdir -p "$ev" evidence/raw
    raw="evidence/raw/batch-$n-muse.log"   # git-ignored: the full transcript can echo local files
    print "muse $model, batch $n, started $(now)" > "$raw"
    # Headless runs can't answer approval prompts; --disable-approval keeps the OS sandbox on (docs/muse/muse-code.md).
    muse exec --model "$model" --no-foreign-personal-context --disable-approval \
      "$(cat briefs/_worker_preamble.md briefs/$n.md)" </dev/null >> "$raw" 2>&1 || print "muse exited non-zero" >> "$raw"
    muse export --last --redacted --out "evidence/raw/batch-$n-muse_session.json" </dev/null 2>/dev/null || true
    grep -c -E "contributor" "evidence/raw/batch-$n-muse_session.json" 2>/dev/null && print -u2 "WARNING: contributor model in session" || true
    cp "$raw" "$ev/builder.md"
    gate
    ;;
  gate)
    gate
    ;;
  merge)
    grep -q '^Verdict: PASS' "$ev/review.md" 2>/dev/null || { print -u2 "merge: no PASS verdict in $ev/review.md"; exit 1; }
    gate
    branch=$(git branch --show-current)
    title=$(head -1 "briefs/$n.md" | sed 's/^# *//')
    # Stage only build paths, so files another tool drops in the repo never ride along.
    git add anamnesis tests "$ev" "briefs/$n.md" SPEC.md pyproject.toml uv.lock
    git commit -q -m "feat: batch $n - $title" -m "Built by the batch builder (see Built-by in the review), gated (ruff + pytest + contract lock), reviewed by Antigravity. Evidence: $ev/"
    git switch -q main
    git merge -q --no-ff "$branch" -m "merge: $branch"
    sha=$(git rev-parse --short HEAD)
    tests=$(grep -Eo '"tests_passed":[0-9]+' "$ev/gate.json" | grep -Eo '[0-9]+$')
    model=$(head -1 "$ev/builder.md" 2>/dev/null | awk '{print $2}' | sed 's/,$//' || print muse-spark-1.3)
    builder=$(head -1 "$ev/builder.md" 2>/dev/null | awk '{print $1}' || print muse)
    # Who actually wrote the code: "Built-by: ..." in the review overrides the builder model (QM M2 #5).
    built_by=$(grep -m1 '^Built-by:' "$ev/review.md" | sed 's/^Built-by: *//' || true)
    built_by=${built_by:-$builder $model}
    contract=$(uv run pytest -q tests/contract 2>&1 | grep -Eo '[0-9]+ passed' | grep -Eo '[0-9]+' || print 0)
    unit=$(uv run pytest -q tests/unit 2>&1 | grep -Eo '[0-9]+ passed' | grep -Eo '[0-9]+' || print 0)
    print -r -- "{\"batch\":$n,\"branch\":\"$branch\",\"model\":\"$model\",\"built_by\":\"$built_by\",\"tests_passed\":$tests,\"contract_tests\":$contract,\"unit_tests\":$unit,\"verdict\":\"pass\",\"merge_commit\":\"$sha\",\"at\":\"$(now)\"}" >> "$log"
    git add "$log" && git commit -q -m "chore: log batch $n"
    git push -q origin main 2>/dev/null && print "pushed main" || print "push skipped (no remote?)"
    ;;
  *) print -u2 "unknown command: $cmd"; exit 1 ;;
esac
