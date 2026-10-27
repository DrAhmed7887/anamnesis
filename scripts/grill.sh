#!/bin/zsh
# Milestone grill: the same brief goes to Muse Code (Meta, Standard mode) and to GPT-6 Astra (one message).
#   scripts/grill.sh <milestone-dir>    reads evidence/grills/<dir>/brief.md and bundle.txt (the file list)
# Outputs: evidence/grills/<dir>/{muse.md, muse_session.json, astra.md}; raw logs go to evidence/raw/ (git-ignored).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
dir="evidence/grills/${1:?milestone dir}"
mkdir -p evidence/raw

{ cat "$dir/brief.md"; for f in $(cat "$dir/bundle.txt"); do printf '\n\n===== %s =====\n' "$f"; cat "$f"; done; } \
  > "evidence/raw/${1}-bundle.md"
ask -m gpt-6-astra "Follow the grill brief at the top of the attached bundle exactly." \
  < "evidence/raw/${1}-bundle.md" > "$dir/astra.md" &

# Standard mode only: *-contributor ids let Meta train on what we send (docs/muse/gotchas.md).
muse exec --model muse-spark-1.3 --no-foreign-personal-context -w --max-model-steps 12 \
  "$(cat "$dir/brief.md")" </dev/null > "evidence/raw/${1}-muse.out" 2>&1
sed "s#$PWD/.muse/worktrees/[0-9-]*/##g" "evidence/raw/${1}-muse.out" > "$dir/muse.md"
muse export --last --redacted --out "$dir/muse_session.json" </dev/null
wait
grep -c -E "contributor" "$dir/muse_session.json" && print -u2 "WARNING: contributor model in session" || true
