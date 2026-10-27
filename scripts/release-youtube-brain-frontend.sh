#!/usr/bin/env bash
# YouTube Brain - pinned, reversible, frontend-only release. No container restart.
set -Eeuo pipefail
umask 077
APP="/opt/youtube-niche-finder"
EXPECTED_COMMIT="${1:-}"
EXPECTED_BASE="${2:-}"
fail() { echo "RELEASE BLOCKED: $1" >&2; exit 1; }
[[ "$EXPECTED_COMMIT" =~ ^[0-9a-f]{40}$ ]] || fail "Pinned release SHA required"
[[ "$EXPECTED_BASE" =~ ^[0-9a-f]{40}$ ]] || fail "Pinned baseline SHA required"
for cmd in git tar curl mktemp cp python3 grep find date; do command -v "$cmd" >/dev/null || fail "Missing $cmd"; done
[[ -d "$APP/.git" && -d "$APP/frontend" && -w "$APP/frontend" ]] || fail "Expected writable installation missing"
[[ -f "$APP/docker-compose.yml" ]] || fail "Compose file missing"
[[ "$(git -C "$APP" rev-parse HEAD)" == "$EXPECTED_BASE" ]] || fail "Installed source differs from reviewed baseline"
[[ "$(git -C "$APP" rev-parse FETCH_HEAD)" == "$EXPECTED_COMMIT" ]] || fail "Fetched SHA differs from pinned release"
git -C "$APP" diff --quiet -- frontend || fail "Installed frontend contains local changes"
git -C "$APP" diff --cached --quiet -- frontend || fail "Frontend index contains changes"
curl -fsS --max-time 8 http://127.0.0.1:18080/api/health >/dev/null || fail "Current site unhealthy"

tmp="$(mktemp -d)"
backups="${HOME}/youtube-brain-backups"
mkdir -p "$backups"
backup="$backups/frontend-before-${EXPECTED_COMMIT:0:12}-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
applied=0
rollback() {
  if [[ "$applied" = 1 ]]; then
    echo "Health check failed; restoring previous frontend from $backup" >&2
    tar -xzf "$backup" -C "$APP/frontend" || true
  fi
}
trap 'rollback; rm -rf -- "$tmp"' EXIT

git -C "$APP" archive --format=tar "$EXPECTED_COMMIT" frontend | tar -xf - -C "$tmp"
[[ -f "$tmp/frontend/index.html" && -f "$tmp/frontend/i18n/tr/app.js" ]] || fail "Missing YouTube Brain frontend"
python3 - "$tmp/frontend" <<'PY'
import sys
from pathlib import Path
root = Path(sys.argv[1])
for p in root.rglob('*'):
    if p.is_symlink() or not (p.is_file() or p.is_dir()):
        raise SystemExit('RELEASE BLOCKED: unexpected symlink or file type')
if '<title>YouTube Brain' not in (root/'index.html').read_text(encoding='utf8'):
    raise SystemExit('RELEASE BLOCKED: wrong application branding')
PY
if command -v node >/dev/null; then
  while IFS= read -r -d '' js; do
    node --input-type=module --check < "$js" >/dev/null || fail "JS syntax problem"
  done < <(find "$tmp/frontend" -type f -name '*.js' -print0)
  echo "ESM syntax: PASS"
else
  echo "ESM syntax: SKIPPED (Node not installed on VDS)" >&2
fi
tar -czf "$backup" -C "$APP/frontend" .
[[ -s "$backup" ]] || fail "Backup failed"
applied=1
cp -a "$tmp/frontend/." "$APP/frontend/"
curl -fsS --max-time 8 -o "$tmp/home.html" http://127.0.0.1:18080/ || fail "Site unavailable"
grep -Fq '<title>YouTube Brain' "$tmp/home.html" || fail "Branded home page not served"
curl -fsS --max-time 8 -o "$tmp/tr.js" http://127.0.0.1:18080/i18n/tr/app.js || fail "Turkish assets unavailable"
grep -q 'themeLight' "$tmp/tr.js" || fail "Turkish module not served"
curl -fsS --max-time 8 http://127.0.0.1:18080/api/health >/dev/null || fail "Site health failed"
applied=0
echo "RELEASE OK: YouTube Brain frontend live on :18080"
echo "Backup: $backup"
echo "Backend, database, worker, MCP, Docker, env and volumes unchanged."
