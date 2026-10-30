#!/bin/zsh
# Milestone grill: the brief goes to Muse Code (Meta, Standard mode).
#   scripts/grill.sh <milestone-dir>    reads evidence/grills/<dir>/brief.md
# Outputs: evidence/grills/<dir>/{muse.md, muse_session.json}; raw logs go to evidence/raw/ (git-ignored).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
dir="evidence/grills/${1:?milestone dir}"
mkdir -p evidence/raw

# Standard mode only: *-contributor ids let Meta train on what we send (docs/muse/gotchas.md).
muse exec --model muse-spark-1.3 --contributor-mode off --no-foreign-personal-context -w --max-model-steps 12 \
  "$(cat "$dir/brief.md")" </dev/null > "evidence/raw/${1}-muse.out" 2>&1
sed "s#$PWD/.muse/worktrees/[0-9-]*/##g" "evidence/raw/${1}-muse.out" > "$dir/muse.md"
muse export --last --redacted --out "$dir/muse_session.json" </dev/null
grep -c -E "contributor" "$dir/muse_session.json" && print -u2 "WARNING: contributor model in session" || true
