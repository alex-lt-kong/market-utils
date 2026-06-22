# Project Memory

## Active Status

**Objective:** Gambler's Toolbox (GitHub `alex-lt-kong/gamblers-toolbox`) is a single
FastAPI app (`core/`) that auto-discovers plugin modules under `modules/` behind one
landing page, one port, and one shared auth layer. A review (see log) raised five bugs
+ refactors; #1, #5, and the `_parse_iso_date` bug are now fixed.

**Immediate next steps (remaining review items):** #3 bound AI-ratios Yahoo work with
per-call network timeouts (executor deadline can't kill running threads); #4 token-in-URL
is by-design (shareable links) — only revisit if you want POST/Authorization; small
refactors left: `extra="forbid"` on HostConfig, port/slug validation, scope
`latest_per_ticker` to requested tickers.

- `core/` — host shell: `module.py` (interface), `registry.py` (discovery), `auth.py`
  (token→cookie gate), typed `config.py` (Pydantic `HostConfig`), `main.py`
  (`build_app(config, modules)` factory + `create_app`), `__main__.py`. Tests in `tests/`.
- `modules/pe_monitor/` — P/E dashboard (was a standalone Flask app). `views.py` holds the
  APIRouter; `backfill/` tools still run standalone via the `_bootstrap` sys.path shim.
- `modules/ai_ratios/` — S&P AI-exposure ratio; computes via `core.py`, caches in `cache.py`
  with its own scheduler; `views.py` serves dashboard + JSON API.

**Run:** `pip install -r requirements.txt` then `python -m core --config config.toml`
(`--config` is mandatory; default bind 9090). Auth is off until `auth_tokens` are set;
when enabled a strong `secret_key` is required or the app refuses to start.

**Parked (not planned — unnecessary for the current single-process deploy):**
ai_ratios JSON-snapshot persistence; an exempt `/healthz` endpoint.

**Notes:**
- `Module` now has two hooks: `lifespan` (resource setup, e.g. DB init — runs on every
  instance) and `scheduler` (background jobs — skipped when `enable_schedulers=false`).
  Each hook owns a local scheduler instance (no module globals).
- `build_app(config, modules)` has no import-time side effects; uvicorn runs it via
  `--factory core.main:create_app`. Run schedulers on one instance only.
- Refreshes are single-flight; ai_ratios keeps last-known-good below 95% coverage.
- Tests: `pip install -r requirements-dev.txt && python -m pytest` (21 integration tests).

## Activity Log

### 2026-06-22 — Add Δ-forward-P/E page to pe_monitor (branch `feat/delta-fwd-pe`)
- New page `/pe-monitor/delta` + `delta.html`: per-ticker forward-P/E change over a
  selectable window (1D/1W/1M/3M/6M/YTD/1Y), ag-grid leaderboard sorted by |Δ%|, nav
  links both ways. No schema change.
- `GET /pe-monitor/api/delta?window=` and `_delta_point` in `views.py`. Live `forward_pe`
  only (no IBES). Critical: the raw live series is sparse, so it's interpolated to daily
  (same `_interpolate_series` as the chart) **before** snapping `then` to now−window —
  otherwise a 1-month delta snaps to an anchor a year back. Interpolated endpoints are
  flagged (`≈`); `then` is null when the window predates coverage.
- `tests/test_delta.py` (6 tests): window/snap/interp logic + endpoint shape/fallback. 27 pass.
- Branch `feat/delta-fwd-pe`, rebased onto `main` after PR #6 (unified-fastapi-landing)
  merged; pushed for its own PR.

### 2026-06-22 — Fix review bugs #1, #5, dates; pin dependency set (#2)
- Split `Module` into `lifespan` (always-run resource setup) + `scheduler` (gated by
  `enable_schedulers`); `core/main.py` enters lifespans on every instance and schedulers
  only when enabled — so a scheduler-disabled replica still runs `init_db` (#1).
- Both module schedulers now live in a local variable inside their `scheduler` CM; the
  module-global `_scheduler` (and ai_ratios `start`/`stop`) are gone, so concurrent app
  instances no longer clobber each other (#5).
- `_parse_iso_date` canonicalises via `.isoformat()` so basic-format/week-date inputs no
  longer break SQLite lexical date comparisons.
- Tests: rewrote lifecycle tests (instance capture + a schedulers-disabled-still-inits
  guard), added `_parse_iso_date` unit tests; README module example updated. 21 pass.
- #2: pinned requirements to the tested set (compatible-release `~=`), incl. starlette.
  Stayed on `httpx` for TestClient (the deprecation points at an unverified `httpx2`
  package — sandbox flagged it as supply-chain risk); silenced the warning in `pytest.ini`.

### 2026-06-22 — Review unified FastAPI branch
- Reviewed the complete `main...origin/feat/unified-fastapi-landing` diff; the
  19-test suite hangs on its first request with the currently resolved unbounded
  FastAPI/Starlette/httpx dependency set.
- Found scheduler-disabled replicas skip P/E database initialization/migrations;
  global scheduler ownership makes app lifespans non-reentrant.
- Found AI-ratios timeout leaves running worker threads behind and URL query-token
  authentication exposes bearer secrets to normal request logging.
- Noted strict config/date validation and stale module-example docs as cleanup work.

### 2026-06-22 — Rename project to Gambler's Toolbox
- Renamed branding to **Gambler's Toolbox** / slug `gamblers-toolbox`: FastAPI title,
  landing page, manifest, icon, README, config comments, log banner prefix.
- Renamed env vars `MARKET_UTILS_CONFIG`→`GAMBLERS_TOOLBOX_CONFIG`,
  `MARKET_UTILS_LOG_SECRETS`→`GAMBLERS_TOOLBOX_LOG_SECRETS` (breaking for external
  launchers; update systemd/launch scripts). Tests updated to match.
- GitHub repo renamed `market-monitors`→`gamblers-toolbox`; updated the `origin` URL.
- Left the local working dir name and a stale notebook path string as-is.

### 2026-06-22 — Refactor: factory, typed config, tests, scheduler flag
- Added a pytest+TestClient integration suite (`tests/`): config/secret validation, auth
  on/off + revocation, discovery + duplicate-slug rejection, prefixed routes, 409
  concurrent refresh, lifecycle, schedulers-disabled.
- `build_app(config, modules)` is now a pure factory with no import-time config/DB side
  effects; uvicorn uses `--factory core.main:create_app`; pe_monitor config is lazy.
- Module `on_startup`/`on_shutdown` replaced by a per-module `lifespan` context manager.
- Typed `HostConfig` (Pydantic); startup validates unique slugs + static mount names.
- `enable_schedulers` host flag (default on) to run background jobs on one instance only.

_(Older entries moved to `MEMORY_ARCHIVE.md`.)_
