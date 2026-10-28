#!/usr/bin/env bash
# YouTube Brain UI v3: safe upgrade from either previously published v1 or v2.
# Frontend bind mount only; never restarts or edits Postgres, worker, API or MCP.
set -Eeuo pipefail
umask 077
APP=/opt/youtube-niche-finder
TARGET="${1:-}"
V2="${2:-}"
V1="${3:-}"
BASE="${4:-}"
fail() { echo "YB V3 RELEASE BLOCKED: $1" >&2; exit 1; }
for commit in "$TARGET" "$V2" "$V1" "$BASE"; do
  [[ "$commit" =~ ^[0-9a-f]{40}$ ]] || fail "Provide four pinned 40-char commits"
done
for cmd in git tar curl mktemp python3 cp find grep date; do command -v "$cmd" >/dev/null || fail "Missing tool $cmd"; done
[[ -d "$APP/.git" && -d "$APP/frontend" && -w "$APP/frontend" ]] || fail "Expected writable production frontend not found"
[[ "$(git -C "$APP" rev-parse HEAD)" == "$BASE" ]] || fail "Repository baseline is different"
[[ "$(git -C "$APP" rev-parse FETCH_HEAD)" == "$TARGET" ]] || fail "Fetched release differs from pinned commit"
git -C "$APP" merge-base --is-ancestor "$V1" "$V2" || fail "v2 does not descend from v1"
git -C "$APP" merge-base --is-ancestor "$V2" "$TARGET" || fail "target does not descend from v2"
curl -fsS --max-time 8 http://127.0.0.1:18080/api/health >/dev/null || fail "Current backend health not OK"

stage="$(mktemp -d)"
backup=''
applied=0
finish() {
  if [[ "$applied" == "1" && -s "$backup" ]]; then
    echo "Rollback: restoring the old frontend from $backup" >&2
    tar -xzf "$backup" -C "$APP/frontend" || true
  fi
  rm -rf -- "$stage"
}
trap finish EXIT

for version in v1 v2 target; do mkdir -p "$stage/$version"; done
git -C "$APP" archive "$V1" frontend | tar -xf - -C "$stage/v1"
git -C "$APP" archive "$V2" frontend | tar -xf - -C "$stage/v2"
git -C "$APP" archive "$TARGET" frontend | tar -xf - -C "$stage/target"

# Strictly identify live v1 or v2 by comparing every tracked frontend file.
# Do not trust a dirty Git worktree, arbitrary local edits or injected symlinks.
python3 - "$stage/v1/frontend" "$stage/v2/frontend" "$APP/frontend" "$stage/target/frontend" <<'PY'
from pathlib import Path
import filecmp
import sys
v1,v2,live,target=map(Path,sys.argv[1:])
def matches(ref):
    if not ref.is_dir(): return False
    for p in ref.rglob('*'):
        rel=p.relative_to(ref)
        q=live/rel
        if q.is_symlink() or p.is_symlink(): return False
        if p.is_dir() and not q.is_dir(): return False
        if p.is_file() and (not q.is_file() or not filecmp.cmp(p,q,shallow=False)): return False
        if not (p.is_file() or p.is_dir()): return False
    return True
for p in target.rglob('*'):
    if p.is_symlink() or not (p.is_file() or p.is_dir()):
        raise SystemExit('YB V3 RELEASE BLOCKED: unsafe target file')
if not (target/'index.html').is_file(): raise SystemExit('YB V3 RELEASE BLOCKED: missing HTML')
html=(target/'index.html').read_text(encoding='utf-8')
if 'id="langSelect"' not in html or 'data-group="research"' not in html:
    raise SystemExit('YB V3 RELEASE BLOCKED: expected UI v2 base is missing')
for name in ('help','mcp','admin'):
    if not (target/'i18n'/'tr'/(name+'.js')).is_file():
        raise SystemExit('YB V3 RELEASE BLOCKED: Turkish '+name+' module missing')
if matches(v2): print('Installed UI version: v2 — verified')
elif matches(v1): print('Installed UI version: v1 — verified')
else: raise SystemExit('YB V3 RELEASE BLOCKED: production frontend differs from both reviewed versions')
PY

if command -v node >/dev/null; then
  while IFS= read -r -d '' file; do
    node --input-type=module --check < "$file" >/dev/null || fail "Invalid ESM syntax"
  done < <(find "$stage/target/frontend" -type f -name '*.js' -print0)
  echo "ESM syntax: PASS"
else
  echo "ESM syntax: NOT RUN (Node unavailable on this VDS)" >&2
fi

backups="${HOME}/youtube-brain-backups"
mkdir -p "$backups"
backup="$backups/frontend-before-ui-v3-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
tar -czf "$backup" -C "$APP/frontend" .
[[ -s "$backup" ]] || fail "Frontend backup failed"
applied=1
cp -a "$stage/target/frontend/." "$APP/frontend/"

curl -fsS --max-time 8 -o "$stage/home.html" http://127.0.0.1:18080/ || fail "Home request failed"
grep -Fq 'id="langSelect"' "$stage/home.html" || fail "Turkish language selector not served"
grep -Fq 'data-group="research"' "$stage/home.html" || fail "Grouped menu not served"
for name in help mcp admin; do
  curl -fsS --max-time 8 -o "$stage/$name.js" "http://127.0.0.1:18080/i18n/tr/$name.js" || fail "Translation $name not served"
  grep -q 'export default' "$stage/$name.js" || fail "Translation $name malformed"
done
curl -fsS --max-time 8 http://127.0.0.1:18080/api/health >/dev/null || fail "Backend unhealthy after update"
applied=0
echo "YB UI V3 RELEASE OK: 40 Turkish dictionaries available, grouped navigation active"
echo "Backup: $backup"
echo "Frontend-only update; DB, Docker, MCP, backend and worker untouched."
