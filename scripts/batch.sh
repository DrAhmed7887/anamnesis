#!/bin/zsh
# One build batch, gated. Every step leaves evidence in evidence/batches/<n>/.
#   scripts/batch.sh start <n> <slug>   branch batch/<n>-<slug> from main (then commit tests/contract + briefs/<n>.md)
#   scripts/batch.sh run <n>            Muse Code (muse-spark-1.3) writes the code from briefs/<n>.md, then the gate runs
#   scripts/batch.sh round <n> <r>      fix round r: Muse works from evidence/batches/<n>/round<r>-brief.md, then the gate
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

# One Muse build from a brief, with its goal pinned, priced from Muse's own billing records.
#   muse_build <label> <brief> <raw log> <export> <model>
muse_build() {
  local label=$1 brief=$2 raw=$3 out=$4 model=$5
  print "muse $model, $label, started $(now)" > "$raw"
  # Muse's goal tracking (cookbook 07): headless "/goal" text isn't parsed as the command (probe, 27 Oct), so the
  # prompt asks Muse to pin the goal with its own goal tool, with an oracle it can run inside its sandbox.
  local goal="Before any other work, pin this objective as your session goal with your goal tool, and close it only when its check passes: $label is done ONLY when \`.venv/bin/ruff check .\` and \`.venv/bin/python -m pytest -q\` both pass and \`git status --porcelain tests/contract\` prints nothing."
  # Headless runs can't answer approval prompts; --disable-approval keeps the OS sandbox on (docs/muse/muse-code.md).
  muse exec --model "$model" --contributor-mode off --no-foreign-personal-context --disable-approval \
    "$(print -r -- "$goal"; print; cat briefs/_worker_preamble.md "$brief")" </dev/null >> "$raw" 2>&1 \
    || print "muse exited non-zero" >> "$raw"
  # The full transcript (every tool call and file read) stays in the git-ignored export.
  muse export --last --redacted --out "$out" </dev/null 2>/dev/null || true
  uv run python scripts/muse_usage.py "$n" "$out" || print -u2 "usage: no export to price"
}

# Committed reports keep no local paths: repo-relative paths, and "the repository" for the root itself.
repo_paths() { sed -e "s#$PWD/##g" -e "s#$PWD#the repository#g" "$@"; }

# Did Muse pin its goal, close it, and work under it? The caller prints it and keeps it in goal.md.
goal_check() { { uv run python scripts/goal_check.py "$1" || true; } | repo_paths; }

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
    raw="evidence/raw/batch-$n-muse.log"   # git-ignored: Muse's final report, with absolute local paths
    out="evidence/raw/batch-$n-muse_session.json"
    muse_build "batch $n" "briefs/$n.md" "$raw" "$out" "$model"
    print "goal check, batch $n:"
    { print "## Round 1"; goal_check "$out"; } | tee "$ev/goal.md"
    repo_paths "$raw" > "$ev/builder.md"
    gate
    ;;
  round)
    r=${3:?round number}
    brief="$ev/round$r-brief.md"
    [[ -f $brief ]] || { print -u2 "round: $brief missing"; exit 1; }
    [[ -f $ev/builder.md ]] || { print -u2 "round: run round 1 first (scripts/batch.sh run $n)"; exit 1; }
    # A fix round builds on the previous round's uncommitted change, so the tree is expected to be dirty.
    raw="evidence/raw/batch-$n-muse-r$r.log"
    out="evidence/raw/batch-$n-muse_session-r$r.json"
    muse_build "batch $n round $r" "$brief" "$raw" "$out" muse-spark-1.3
    print "goal check, batch $n round $r:"
    { print; print "## Round $r"; goal_check "$out"; } | tee -a "$ev/goal.md"
    { print; print "## Round $r"; repo_paths "$raw"; } >> "$ev/builder.md"
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
    git commit -q -m "feat: batch $n - $title" -m "Built by the batch builder (see Built-by in the review), gated (ruff + pytest + contract lock), reviewed by Claude Code (CEO). Evidence: $ev/"
    # The engine may build in its own worktree while main stays checked out in the main checkout: merge there.
    root=$(git worktree list --porcelain | awk '/^worktree /{wt=substr($0, 10)} $0 == "branch refs/heads/main" {print wt}')
    if [[ -n $root && $root != "$PWD" ]]; then
      [[ -z $(git -C "$root" status --porcelain --untracked-files=no) ]] || { print -u2 "merge: $root has uncommitted changes"; exit 1; }
      git -C "$root" merge -q --no-ff "$branch" -m "merge: $branch"
    else
      root=$PWD
      git switch -q main
      git merge -q --no-ff "$branch" -m "merge: $branch"
    fi
    sha=$(git -C "$root" rev-parse --short HEAD)
    tests=$(grep -Eo '"tests_passed":[0-9]+' "$ev/gate.json" | grep -Eo '[0-9]+$')
    model=$(head -1 "$ev/builder.md" 2>/dev/null | awk '{print $2}' | sed 's/,$//' || print muse-spark-1.3)
    builder=$(head -1 "$ev/builder.md" 2>/dev/null | awk '{print $1}' || print muse)
    # Who actually wrote the code: "Built-by: ..." in the review overrides the builder model (QM M2 #5).
    built_by=$(grep -m1 '^Built-by:' "$ev/review.md" | sed 's/^Built-by: *//' || true)
    built_by=${built_by:-$builder $model}
    contract=$(uv run pytest -q tests/contract 2>&1 | grep -Eo '[0-9]+ passed' | grep -Eo '[0-9]+' || print 0)
    unit=$(uv run pytest -q tests/unit 2>&1 | grep -Eo '[0-9]+ passed' | grep -Eo '[0-9]+' || print 0)
    print -r -- "{\"batch\":$n,\"branch\":\"$branch\",\"model\":\"$model\",\"built_by\":\"$built_by\",\"tests_passed\":$tests,\"contract_tests\":$contract,\"unit_tests\":$unit,\"verdict\":\"pass\",\"merge_commit\":\"$sha\",\"at\":\"$(now)\"}" >> "$root/$log"
    git -C "$root" add "$log" && git -C "$root" commit -q -m "chore: log batch $n"
    git -C "$root" push -q origin main 2>/dev/null && print "pushed main" || print "push skipped (no remote?)"
    ;;
  *) print -u2 "unknown command: $cmd"; exit 1 ;;
esac
