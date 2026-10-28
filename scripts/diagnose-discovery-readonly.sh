#!/usr/bin/env bash
# YouTube Brain Niche Finder / second VDS — READ ONLY, zero YouTube API quota.
# Never print the API key or a full container environment.
set -Eeuo pipefail
APP=/opt/youtube-niche-finder
cd "$APP"
echo "=== DISCOVERY WORKER STATUS (NO QUOTA) ==="
if ! docker inspect niche-finder-worker > /dev/null 2>&1; then
  echo "WORKER: MISSING (the docker compose worker has not been created)"
else
  docker inspect niche-finder-worker | python3 -c '
import json, sys
c=json.load(sys.stdin)[0]
st=c.get("State", {})
env={}
for row in c.get("Config",{}).get("Env",[]):
    k,_,v=row.partition("=")
    env[k]=v
queries=[q.strip() for q in env.get("WORKER_QUERIES","").split(",") if q.strip()]
print("WORKER:",st.get("Status","unknown"),"| restarts:",c.get("RestartCount","unknown"))
print("YouTube API key configured:",bool(env.get("YOUTUBE_API_KEY")))
print("Discovery queries configured:",len(queries))
print("Daily scan cadence (minutes):",env.get("WORKER_DAILY_INTERVAL_MIN","default"))
print("Query window:",env.get("WORKER_QUERY_PERIOD","default"))
print("Query pages:",env.get("WORKER_QUERY_PAGES","default"))
print("Trending enabled:",env.get("WORKER_TRENDING","default"))
print("Trending regions:",env.get("WORKER_REGIONS","default"))
print("LAST STARTED:",st.get("StartedAt","unknown"))
if not queries:
    print("DISCOVERY WARNING: WORKER_QUERIES empty. Topic discovery is disabled.")
if st.get("Status")!="running":
    print("WORKER WARNING: background processing is not running.")
'
fi
echo
echo "=== LAST WORKER CYCLES + CORPUS (DB READ ONLY) ==="
if docker inspect niche-finder-web >/dev/null 2>&1; then
  docker exec -i niche-finder-web python - <<'PY'
import infrastructure.postgres as db
c=db.get_conn()
try:
    for name in ("worker_last_daily","worker_last_hot","worker_last_rss",
                 "worker_last_topic_search","worker_quota_blocked_until"):
        val=db.get_meta(c,name)
        print(name,":",val if val else "(not recorded)")
    for table in ("channels","videos","niches","video_stats_history"):
        n=c.execute("SELECT COUNT(*) AS n FROM "+table).fetchone()["n"]
        print("DB "+table+":",n)
finally:
    c.close()
PY
else
  echo "WEB MISSING: cannot inspect worker cycle markers"
fi
echo "READ ONLY FINISHED: no API request, no restart, no .env changes"
