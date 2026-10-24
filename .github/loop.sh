#!/usr/bin/env bash
# Long-running update loop: every INTERVAL seconds pull OKX (read-only) -> publish
# index.html + data.json + history.json as one commit force-pushed to gh-pages (Pages source)
# and data (history backup). A failed iteration is logged and skipped, never fatal.
set -u
INTERVAL=${INTERVAL:-360}          # 6 min = 10 Pages builds/hour (GitHub soft limit)
RUN_FOR=${RUN_FOR:-20700}          # 5h45m, under the 6h job limit
START=$(date +%s); DEADLINE=$((START + RUN_FOR)); n=0
git config user.name "arena-bot"; git config user.email "arena-bot@users.noreply.github.com"

# restore equity history
if git fetch -q origin data 2>/dev/null; then git show origin/data:history.json > history.json 2>/dev/null || rm -f history.json; fi

iteration() {
  git fetch -q origin main || echo "::warning::fetch main failed (using last index.html)"
  timeout 120 python updater.py || { echo "::warning::updater failed"; return 1; }
  rm -rf /tmp/pub && mkdir -p /tmp/pub
  git show origin/main:index.html > /tmp/pub/index.html || return 1
  cp data.json history.json /tmp/pub/ && touch /tmp/pub/.nojekyll
  export GIT_INDEX_FILE=/tmp/pub.idx; rm -f "$GIT_INDEX_FILE"
  git --work-tree=/tmp/pub add -A . && tree=$(git write-tree) || { unset GIT_INDEX_FILE; return 1; }
  unset GIT_INDEX_FILE
  c=$(git commit-tree "$tree" -m "site $(date -u +%FT%TZ)") || return 1
  for a in 1 2 3; do
    timeout 60 git push -qf origin "$c:refs/heads/gh-pages" "$c:refs/heads/data" && { echo "published $c"; return 0; }
    sleep 10
  done
  echo "::warning::push failed"; return 1
}

while :; do
  n=$((n + 1)); echo "=== iteration $n $(TZ=Asia/Taipei date '+%F %T') Taipei"
  iteration || echo "::warning::iteration $n failed, continuing"
  next=$((START + n * INTERVAL))
  [ "$next" -ge "$DEADLINE" ] && break
  now=$(date +%s); [ "$next" -gt "$now" ] && sleep $((next - now))
done

echo "deadline reached after $n iterations, dispatching next loop run"
for a in 1 2 3 4 5; do gh workflow run update.yml --ref main -f reason=chain && exit 0; sleep 15; done
echo "::error::could not dispatch next loop; cron watchdog will restart it"; exit 0
