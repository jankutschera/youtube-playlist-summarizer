# Session Log

## Projekt Status
- **Letztes Update:** 2026-02-07
- **Status:** Fully deployed to Synology NAS with SQLite, supervisord, gunicorn

## Letzter Stand

### Deployment (2026-02-07)
- Fixed Cloudflare Tunnel "LAK" (was down since Feb 2, no container existed)
- Created `/volume1/docker/lak-tunnel/` with docker-compose.yml + .env for persistent tunnel management
- Uploaded all changed files to NAS via scp
- Rebuilt Docker image (new dependencies: gunicorn, supervisor)
- Ran `migrate_to_sqlite.py` - 270 videos migrated from JSON to SQLite
- Container running with supervisord managing web (gunicorn) + worker
- Fixed supervisord.conf: added supervisorctl/rpcinterface sections for management
- All endpoints verified: dashboard (200), /api/status (200), quota tracking active

### Phase 1: Quick Wins (DONE)
- Added gunicorn as production web server
- Made Claude model configurable via `CLAUDE_MODEL` env var (default: claude-sonnet-4-5-20250929)
- Removed redundant `youtube.readonly` OAuth scope
- Fixed XSS: added `markupsafe.escape()` to `markdown_to_html` filter
- Added `/api/status` health endpoint with worker status + quota info

### Phase 2: SQLite Migration (DONE)
- Created `database.py` with WAL mode, parameterized queries, all CRUD operations
- Created `migrate_to_sqlite.py` one-time migration script (JSON -> SQLite)
- Updated `youtube_summarizer.py` to use SQLite via database module (removed load_state/save_state)
- Updated `web_app.py` to use SQLite (removed all JSON file I/O)
- Updated templates to use `added_at or processed_at` for date display

### Phase 3: Reliability (DONE)
- Replaced all `print()` with structured `logging` (timestamps + levels)
- Added transcript retry logic: failed transcripts retry 3x with 7-day intervals
- Added supervisord for process management (web + worker with auto-restart)
- Added YouTube API quota tracking with 80%/95% thresholds

## Infrastructure

### Cloudflare Tunnels on NAS
| Tunnel | Container | Status | Config |
|--------|-----------|--------|--------|
| LAK | `lak-tunnel` | healthy | `/volume1/docker/lak-tunnel/docker-compose.yml` |
| health | `health-tunnel` | healthy | `/volume1/docker/health/docker-compose.yml` |

### LAK Tunnel Routes
- `yt.lucia-allegra.com` -> localhost:8080
- `service.lucia-allegra.com` -> localhost:80
- `postiz.lucia-allegra.com` -> localhost:8100
- `postiz-api.lucia-allegra.com` -> localhost:8101
- `n8n.lucia-allegra.com` -> localhost:5678
- `vektor.lucia-allegra.com` -> localhost:8103
- `billing.truebrew-birdie.com` -> localhost:8082

### NAS Access
- SSH: `ssh nullergy` (192.168.188.50, user: admin)
- Docker: `/usr/local/bin/docker` (not in PATH, needs full path)
- SCP: needs `-O` flag for legacy protocol

## Nächste Schritte
- [ ] Delete old OAuth token, re-authenticate at https://yt.lucia-allegra.com/login (scope changed)
- [ ] Remove remaining ~30 processed videos from playlist
- [ ] Monitor SQLite DB growth and worker retry behavior

## Files Changed
| File | Action |
|------|--------|
| `requirements.txt` | Added gunicorn, supervisor |
| `start.sh` | Now uses supervisord |
| `docker-compose.yml` | Added CLAUDE_MODEL, volume mounts, healthcheck on /api/status, production REDIRECT_URI |
| `Dockerfile` | Copies new files, CMD uses start.sh |
| `youtube_summarizer.py` | SQLite, logging, retry, configurable model, quota tracking |
| `web_app.py` | SQLite, logging, health endpoint, XSS fix |
| `templates/dashboard.html` | Updated date display field |
| `templates/archive.html` | Updated date display field |
| **NEW:** `database.py` | SQLite abstraction layer |
| **NEW:** `migrate_to_sqlite.py` | One-time JSON->SQLite migration |
| **NEW:** `supervisord.conf` | Process management config (with supervisorctl support) |

## Offene Fragen
- None
