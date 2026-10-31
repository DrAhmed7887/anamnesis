#!/bin/zsh
# Build the filtered public copy of Anamnesis in a new work folder. It pushes nothing and publishes nothing.
#   scripts/public/make_public.sh <new work dir>
# The replace rules and the author mapping name what they remove, so they live outside git, in
# evidence/raw/public-kit/ (rules.txt, mailmap). See scripts/public/README.md.
set -euo pipefail
W=${1:?new work dir}
SRC=$HOME/Projects/anamnesis
KIT=$SRC/scripts/public
PRIVATE=$SRC/evidence/raw/public-kit
RAW=$HOME/Projects/anamnesis-b21/evidence/raw
PY=$SRC/.venv/bin/python  # the project's Python (3.13); the system one is too old for muse_usage.py
[[ ! -e "$W" ]] || { print -u2 "make_public: $W exists; give a new work dir"; exit 1; }
mkdir -p "$W"

print "== 1. a fresh single-branch clone of main"
git clone -q --no-local --single-branch --branch main "$SRC" "$W/public"
cd "$W/public"

print "== 2. filter every commit: the rules, the author mapping, and no raw Muse exports"
git filter-repo --force --quiet --replace-text "$PRIVATE/rules.txt" --replace-message "$PRIVATE/rules.txt" \
  --mailmap "$PRIVATE/mailmap" --path-glob '*muse_session*.json' --invert-paths

print "== 3. Muse's sessions back, cleaned: the grills at their paths, the builds under evidence/muse-sessions/"
for f in $(git -C "$SRC" ls-files 'evidence/grills/*muse_session*.json'); do
  mkdir -p "$(dirname "$f")"
  "$PY" "$KIT/clean_muse_session.py" "$PRIVATE/rules.txt" "$SRC/$f" "$f" >/dev/null
done
mkdir -p evidence/muse-sessions
for f in "$RAW"/*muse_session*.json; do
  "$PY" "$KIT/clean_muse_session.py" "$PRIVATE/rules.txt" "$f" "evidence/muse-sessions/$(basename "$f").gz" >/dev/null
done
"$PY" "$KIT/index_sessions.py" "$SRC" evidence/muse-sessions > evidence/muse-sessions/README.md

print "== 4. commit ids cited in the tree, remapped to this history"
"$PY" "$KIT/remap_shas.py" .git/filter-repo/commit-map

NAME=$(head -1 "$PRIVATE/mailmap" | sed -E 's/ <.*//')
EMAIL=$(head -1 "$PRIVATE/mailmap" | sed -E 's/^[^<]*<([^>]*)>.*/\1/')
git add -A
git -c user.name="$NAME" -c user.email="$EMAIL" commit -q -m "chore(public): Muse's sessions, cleaned; commit ids remapped to this history

The grill sessions are back at their paths, and the build sessions are in evidence/muse-sessions/, each with every
event Muse recorded except its encrypted reasoning and the session owner's personal context. Paths are
repo-relative."
print "== done: $(git rev-list --count HEAD) commits, $(du -sh .git | cut -f1) .git"
