#!/usr/bin/env bash
# Pinned YouTube Brain PR3-7 release. Only frontend and one backend module.
set -Eeuo pipefail
umask 077
APP=/opt/youtube-niche-finder
WEB=http://127.0.0.1:18080
BASE=d87201454cd6210eb9a604fc663e2db61cefd2ca
V1=915627afa7008520f70987afe5a5a0173284c04f
V2=acdb89de910dfffa56796379efbbca6074acb589
V3=1a18651558b9fb1d1266c5cd7a969730751d4bed
V4=4e309040372579a9d8264afc95fbccb70f1cfe48
V5=a4846e4fcff68afe24e159d290b0b5fb095d62ce
fail() { echo "RELEASE BLOCKED: $*" >&2; exit 1; }
[[ "$#" == 1 && "$1" =~ ^[0-9a-f]{40}$ ]] || fail "A pinned 40-character commit is required"
TARGET="$1"
[[ "$(id -u)" == 0 ]] || fail "Run as root on the second VDS"
for cmd in git tar curl docker python3 mktemp cp cmp grep date find; do
  command -v "$cmd" >/dev/null || fail "Missing $cmd"
done
[[ -d "$APP/.git" && -d "$APP/frontend" && -f "$APP/backend/application/niche_ranking.py" ]] || fail "Unexpected installation directory"
[[ "$(git -C "$APP" rev-parse HEAD)" == "$BASE" ]] || fail "Unexpected Git baseline"
[[ "$(git -C "$APP" rev-parse FETCH_HEAD)" == "$TARGET" ]] || fail "Fetched SHA mismatch"
for sha in "$V1" "$V2" "$V3" "$V4" "$V5"; do
  git -C "$APP" merge-base --is-ancestor "$sha" "$TARGET" || fail "Ancestry mismatch"
done
curl -fsS --max-time 10 "$WEB/api/health" >/dev/null || fail "Current health failed"

python3 - "$APP" <<'PY'
import json, subprocess, sys
from pathlib import Path
app=Path(sys.argv[1]).resolve()
c=json.loads(subprocess.check_output(["docker","inspect","niche-finder-web"],text=True))[0]
if c["State"]["Status"]!="running": raise SystemExit("RELEASE BLOCKED: web not running")
mounts={(m["Destination"],m["Type"]):Path(m["Source"]).resolve() for m in c["Mounts"]}
if mounts.get(("/app","bind")) != app/"backend" or mounts.get(("/frontend","bind")) != app/"frontend":
    raise SystemExit("RELEASE BLOCKED: expected code bind mounts missing")
print("Web container mounts: verified")
PY

stage="$(mktemp -d)"
backup=''
applied=0
finish() {
  local rc="$?"
  trap - EXIT
  if [[ "$rc" -ne 0 && "$applied" -eq 1 ]]; then
    echo "FAILED: restoring backup and restarting only niche-finder-web" >&2
    python3 "$stage/sync.py" "$stage/backup/frontend" "$APP/frontend" || true
    cp -a "$stage/backup/backend/application/niche_ranking.py" "$APP/backend/application/niche_ranking.py" || true
    docker restart niche-finder-web >/dev/null || true
    curl -fsS --max-time 10 "$WEB/api/health" >/dev/null || echo "WARNING: manual health check needed" >&2
  fi
  rm -rf -- "$stage"
  exit "$rc"
}
trap finish EXIT
mkdir -p "$stage/target" "$stage/backup" "$stage/reference" "$stage/baseline"
git -C "$APP" archive "$TARGET" frontend backend/application/niche_ranking.py | tar -xf - -C "$stage/target"
git -C "$APP" show "$BASE:backend/application/niche_ranking.py" > "$stage/baseline/niche_ranking.py"
cmp -s "$APP/backend/application/niche_ranking.py" "$stage/baseline/niche_ranking.py" ||
  fail "Live backend module was customized"
python3 - "$stage/target/frontend" "$APP/frontend" <<'PY'
import sys
from pathlib import Path
target,live=map(Path,sys.argv[1:])
for root in (target,live):
    for p in root.rglob("*"):
        if p.is_symlink() or not (p.is_file() or p.is_dir()):
            raise SystemExit("RELEASE BLOCKED: unsafe frontend entry: "+str(p))
html=(target/"index.html").read_text(encoding="utf-8")
if 'id="langSelect"' not in html or 'data-group="research"' not in html:
    raise SystemExit("RELEASE BLOCKED: not the expected grouped frontend")
for name in ("channel-evidence.js","coverage-insights.js","niche-evidence.js",
             "i18n/tr/admin.js","i18n/tr/mcp.js","i18n/tr/help.js"):
    if not (target/name).is_file(): raise SystemExit("RELEASE BLOCKED: missing "+name)
PY

match=''
for sha in "$V1" "$V2" "$V3" "$V4" "$V5"; do
  git -C "$APP" archive "$sha" frontend | tar -xf - -C "$stage/reference"
  if python3 - "$stage/reference/frontend" "$APP/frontend" <<'PY'
from pathlib import Path
import filecmp,sys
ref,live=map(Path,sys.argv[1:])
def files(root):
    return {str(p.relative_to(root)):p for p in root.rglob("*") if p.is_file()}
a,b=files(ref),files(live)
assert a.keys()==b.keys(), "different frontend files"
assert all(filecmp.cmp(a[k],b[k],shallow=False) for k in a), "changed frontend content"
PY
  then match="$sha"; break; fi
  rm -rf "$stage/reference"
  mkdir -p "$stage/reference"
done
[[ -n "$match" ]] || fail "Live frontend differs from the reviewed v1-v5"
echo "Live frontend version verified: $(printf %s "$match" | cut -c1-12)"

python3 -m py_compile "$stage/target/backend/application/niche_ranking.py"
if command -v node >/dev/null; then
  while IFS= read -r -d '' js; do
    node --input-type=module --check < "$js" >/dev/null || fail "JS syntax error"
  done < <(find "$stage/target/frontend" -type f -name '*.js' -print0)
  echo "JS syntax: PASS"
else echo "NOTE: Node is missing; browser JS tests remain required" >&2; fi

cat > "$stage/sync.py" <<'PY'
from pathlib import Path
import shutil,sys
src,dst=map(Path,sys.argv[1:])
if not src.is_dir() or not dst.is_dir(): raise SystemExit("Invalid sync directories")
for p in src.rglob("*"):
    if p.is_symlink() or not (p.is_file() or p.is_dir()):
        raise SystemExit("Unsafe release file")
# Keep dst itself in place: Docker bind mounts reference this directory.
for p in dst.iterdir():
    if p.is_dir() and not p.is_symlink(): shutil.rmtree(p)
    else: p.unlink()
shutil.copytree(src,dst,dirs_exist_ok=True)
PY
mkdir -p /root/youtube-brain-backups
backup="/root/youtube-brain-backups/before-batch-3-7-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
tar -czf "$backup" -C "$APP" frontend backend/application/niche_ranking.py
[[ -s "$backup" ]] || fail "Backup failed"
tar -xzf "$backup" -C "$stage/backup"
echo "Backup created: $backup"

applied=1
python3 "$stage/sync.py" "$stage/target/frontend" "$APP/frontend"
cp -a "$stage/target/backend/application/niche_ranking.py" "$APP/backend/application/niche_ranking.py"
docker restart niche-finder-web >/dev/null
curl --retry 10 --retry-connrefused --retry-delay 2 -fsS --max-time 10 "$WEB/api/health" >/dev/null || fail "New site unhealthy"
curl -fsS --max-time 10 "$WEB/" > "$stage/home.html" || fail "Homepage failed"
grep -Fq 'id="langSelect"' "$stage/home.html" || fail "Language switch missing"
grep -Fq 'data-group="research"' "$stage/home.html" || fail "Grouped navigation missing"
for file in channel-evidence.js coverage-insights.js niche-evidence.js i18n/tr/help.js i18n/tr/mcp.js i18n/tr/admin.js; do
  curl -fsS --max-time 10 "$WEB/$file" > "$stage/served.js" || fail "Asset unavailable: $file"
  cmp -s "$stage/served.js" "$stage/target/frontend/$file" || fail "Wrong asset served: $file"
done
curl -fsS --max-time 30 "$WEB/api/niches/ranking" > "$stage/ranking.json" || fail "Niche ranking endpoint failed"
python3 - "$stage/ranking.json" <<'PY'
import json,sys
with open(sys.argv[1],encoding="utf-8") as f: data=json.load(f)
assert isinstance(data.get("niches"),list), "Niches field missing"
assert all(type(r.get("channels")) is int and r["channels"]>=0 for r in data["niches"]), \
    "Distinct channel counts are missing or invalid"
print("Backend ranking and distinct channel counts: PASS")
PY
applied=0
echo "BATCH RELEASE OK: YouTube Brain PR3-7 running on :18080"
echo "Backup: $backup"
echo "Only niche-finder-web restarted; database, worker, MCP, VEVOffice unchanged."
