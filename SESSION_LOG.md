# Session Log

## Projekt Status
- **Letztes Update:** 2026-05-20
- **Status:** Local YouTube Tool is live and MCP smoke-tested; Focus Digest is the separate multi-user product track

## Letzter Stand

### Local YouTube Tool finalized (2026-05-20)
- Scope clarified: "YouTube Tool" = personal/local MCP over `yt.lucia-allegra.com`; "Focus Digest" = separate multi-user Cloudflare Worker product.
- Fixed `mcp_server.py` API requests by adding JSON `Accept` and a stable `User-Agent`; Python `urllib` was otherwise blocked with HTTP 403 by the live endpoint.
- Fixed MCP dependency command from `--with mcp` to `--with mcp[cli]` in `~/.mcp.json` and `~/.local/bin/mcp-toggle`.
- Smoke-tested live API:
  - `/api/status`
  - `/api/videos?limit=1&status=active`
  - `/api/video/<id>`
  - `/api/search?q=psychology`
  - `/api/video/<id>/download`
- Smoke-tested MCP stdio:
  - `initialize`
  - `tools/list`
  - `tools/call get_stats`

### MCP Server (2026-03-22)
- Created `mcp_server.py` - MCP server exposing video database to AI agents
- Tools: `search_videos`, `get_video_summary`, `list_recent_videos`, `get_stats`
- Runs via `uv run --no-project --with 'mcp[cli]'` (no global install needed)
- Registered globally in `~/.mcp.json` as `yt-summarizer`
- Also added to `mcp-toggle` for per-project use
- Improved API endpoints: `/api/videos` strips transcript/summary, `/api/video/<id>` returns full detail, `/api/search` returns summary snippets

### Fixes (2026-02-28)
- Fixed OAuth scope mismatch: added `OAUTHLIB_RELAX_TOKEN_SCOPE=1`
- Cleaned up playlist: removed 36 already-summarized videos, processed 2 new ones
- LAK tunnel token hardcoded in docker-compose.yml (was losing .env file)

### Deployment (2026-02-07)
- Fixed Cloudflare Tunnel "LAK" (was down since Feb 2, no container existed)
- Created `/volume1/docker/lak-tunnel/` with docker-compose.yml (token hardcoded)
- Uploaded all changed files to NAS via scp
- Rebuilt Docker image (new dependencies: gunicorn, supervisor)
- Ran `migrate_to_sqlite.py` - 270 videos migrated from JSON to SQLite
- Container running with supervisord managing web (gunicorn) + worker

### Phase 1-3 (DONE)
- gunicorn, configurable Claude model, XSS fix, health endpoint
- SQLite with WAL mode, migration from JSON
- Structured logging, transcript retry, supervisord, quota tracking

## Infrastructure

### MCP Server
- **Name:** `yt-summarizer`
- **Config:** `~/.mcp.json` (global) + `mcp-toggle add yt-summarizer` (per-project)
- **Command:** `uv run --no-project --with 'mcp[cli]' /Users/jankutschera/dev/youtube-summarizer-oauth2/mcp_server.py`
- **API Base:** `https://yt.lucia-allegra.com/api`

### API Endpoints
| Endpoint | Purpose |
|----------|---------|
| `GET /api/videos?limit=N&status=active` | List videos (no transcript/summary) |
| `GET /api/video/<id>` | Single video with full summary + transcript |
| `GET /api/search?q=keyword` | Search with summary snippets |
| `GET /api/status` | Worker status, quota, video counts |

### Cloudflare Tunnels on NAS
| Tunnel | Container | Config |
|--------|-----------|--------|
| LAK | `lak-tunnel` | `/volume1/docker/lak-tunnel/docker-compose.yml` (token hardcoded) |
| health | `health-tunnel` | `/volume1/docker/health/docker-compose.yml` |

### NAS Access
- SSH: `ssh nullergy` (192.168.188.50, user: admin)
- Docker: `/usr/local/bin/docker` (not in PATH, needs full path)
- SCP: needs `-O` flag for legacy protocol

## Nächste Schritte
- [ ] Restart/new agent session to load the corrected `yt-summarizer` MCP registration
- [ ] Continue Focus Digest as separate multi-user product track
- [ ] Monitor SQLite DB growth and worker retry behavior

## Files Changed
| File | Action |
|------|--------|
| `mcp_server.py` | Added request headers so MCP tool calls reach the live API reliably |
| `web_app.py` | Improved API: `/api/videos` strips heavy fields, new `/api/video/<id>`, `/api/search` with snippets, OAuth scope fix |
| **NEW:** `mcp_server.py` | MCP server for AI agent access to video database |
| `~/.mcp.json` | `yt-summarizer` MCP globally, corrected to `mcp[cli]` |
| `~/.local/bin/mcp-toggle` | `yt-summarizer` config corrected to `mcp[cli]` |

## Offene Fragen
- None
