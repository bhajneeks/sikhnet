#!/usr/bin/env bash
# Prints what every teammate is doing, read from their OWN branch on origin,
# so a session sees work that hasn't been merged to main yet.
# Runs automatically at session start (.claude/settings.json) and via the team-sync skill.

cd "$(git rev-parse --show-toplevel 2>/dev/null || dirname "$0"/..)" || exit 0

# Fetch quietly; never block a session start for more than ~8s.
( GIT_TERMINAL_PROMPT=0 git fetch --quiet --prune origin 2>/dev/null ) &
fetch_pid=$!
for _ in 1 2 3 4 5 6 7 8; do kill -0 "$fetch_pid" 2>/dev/null || break; sleep 1; done
kill "$fetch_pid" 2>/dev/null

echo "=== sikhnet team context ($(date '+%Y-%m-%d %H:%M')) ==="
echo "You are: $(git config user.name 2>/dev/null || echo unknown) on branch $(git branch --show-current 2>/dev/null)"
echo

for name in manveer bhajneek avneet jaspreet; do
  branch=$(git for-each-ref --format='%(refname:short)' "refs/remotes/origin/$name/" 2>/dev/null | head -1)
  echo "----- $name ${branch:+($branch)}"
  status=""
  [ -n "$branch" ] && status=$(git show "$branch:docs/brain/status/$name.md" 2>/dev/null)
  [ -z "$status" ] && status=$(cat "docs/brain/status/$name.md" 2>/dev/null)
  if [ -n "$status" ]; then
    echo "$status" | sed -n '1,25p'
  else
    echo "(no status file yet)"
  fi
  if [ -n "$branch" ]; then
    commits=$(git log --oneline -n 5 "origin/main..$branch" 2>/dev/null)
    last=$(git log -1 --format='%cr' "$branch" 2>/dev/null)
    echo "  last commit: ${last:-n/a}"
    [ -n "$commits" ] && echo "  unmerged commits:" && echo "$commits" | sed 's/^/    /'
  fi
  echo
done

echo "----- recent team decisions"
ls docs/brain/decisions/*.md 2>/dev/null | grep -v README | tail -5 | while read -r f; do
  echo "  $(basename "$f"): $(grep -m1 '^title:' "$f" | sed 's/title: //')"
done
echo
echo "----- open friction (top 5)"
grep -m5 '^- ' docs/brain/friction.md 2>/dev/null || echo "  none"
