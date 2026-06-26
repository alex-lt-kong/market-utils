# Project Memory — Archive

Older activity-log entries pruned from `MEMORY.md` (newest first).

### 2026-06-23 — Forward-P/E money-losing handling (Design Y, branch `fix/pe-chart-gaps-and-ibes-neg`)
- Problem: a company forecast to lose money has negative forward EPS ⇒ forward P/E is
  undefined. Three write-sites stored a *negative* P/E (live `fetcher` via Yahoo
  `forwardPE`; `import_wayback_fwdpe`; `import_ibes` PRICE/MEANEST) that plotted below
  zero, and `_interpolate_series` *bridged* the loss gaps, faking a smooth trend.
- Design Y — store signed, break at serve: forward-P/E columns keep the raw *signed* ratio
  (negative = forecast loss); no source guards, no schema change. `_interpolate_series`
  reworked in EPS-space — nulls loss anchors and never interpolates a span a loss bounds,
  so the line breaks from last-profitable to next-profitable anchor (kills the near-zero
  +∞ interpolation spike: MU max served 115.7 vs a 2887 spike). TTM stays nulled-at-source
  (it isn't interpolated). `_hide_nonpositive_pe` enforces the rule on the latest grid.
- Chart `dashboard.html`: a `segment.borderColor` callback breaks a line only at *genuine*
  gaps (row present, value null) while still bridging *alignment* gaps (ticker lacks a union
  date) — both are `null` and `spanGaps` bridged both before. NOTE: first impl had a dead
  loop — Chart.js emits one segment per *adjacent* pair (p1DataIndex = p0DataIndex+1), so
  scanning indices *between* the endpoints never fired and no line broke (caught visually on
  UAT, not by tests). Fixed to test the segment's two endpoints against the genuine-gap mask.
- An earlier "drop negatives at source + null the DB" attempt was reverted in favour of Y.
  Verified: 33 tests pass (+`test_interpolate_breaks_across_forward_loss`); MU IBES breaks
  Jul–Sep 2023; 0 negatives served across all 39 tickers; NIO → 98 positive fwd-P/E days.
- Follow-up refactor (same branch): replaced the categorical *union-date* x-axis with a
  shared **linear time axis** (x = epoch-ms). The union made per-ticker density distort time
  — equal calendar spans rendered at unequal width (INTC 1986→ at 30d buckets vs ARM daily ⇒
  recent years ~15× wider). This deletes `unionDates`/`alignRows`/`col`/`genuineGap`, so
  `segmentBreak` is gone too — replaced by plain `spanGaps:false` (one ticker per chart ⇒
  every null is a genuine gap). `cutoffLine` maps date→pixel via the scale.
- Verified the axis math via **headless Chart.js** (node + stubbed canvas): line/bar data map
  to exact axis pixels. Caught+fixed there: bar charts default `offset:true`, insetting the
  volume bars to ~83% of the width while the lines use the full axis (looked like vol not
  matching the lines / data "squished") — forced `offset:false` on both x-axes.
- Stood up local **Playwright** E2E (headless Chromium + app on :9090). It caught what the
  headless axis-math missed: the volume x-axis reserves a right gutter for its last date
  label that the label-less P/E axis didn't → ~29px misalignment (pe_plot 1023 vs vol 994).
  Fixed with `pinX` (afterFit `paddingRight=36`) on both → both `[58,992]`. Also added even
  round-date ticks (`niceDateTicks` + `fmtDateTick`) and cleared the review findings (2 stale
  comments, single-point-extent guard). All Playwright-verified (geometry, ticks, no errors).
- **Loss shading** (`lossBandsPlugin`): a semi-transparent band tinted to each line over the
  periods its P/E is undefined (a missing line otherwise reads as a glitch). TTM: client-side,
  null P/E within trailing-EPS coverage (reaches edges; day-gaps in trailing-EPS don't
  fragment it). Forward/IBES: a server loss flag `<col>_loss` from `_interpolate_series` — the
  client can't tell a forecast-loss null from a no-data null at the *visible edge* (e.g. MU's
  IBES loss starts before its first in-window positive anchor). Sub-3-week gaps dropped as
  interp noise. Playwright-verified: INTC blue-only, MU blue+green, NIO blue+red+green.
- Review findings fixed: delta `now` → N/A when the latest forward P/E is a loss (was a stale
  pre-loss value); `_history_rows` reaches forward to the right anchor (new
  `storage.earliest_value_date`) so a custom window inside a sparse gap interpolates instead
  of rendering blank (verified on MU 2021-08: 0 → 5 values); a stored 0 P/E is nulled (was
  plotting y:0). +3 tests (36 total). Deferred to a follow-up PR: gap-aware downsampling,
  explicit-series-state refactor, Playwright/JS E2E.

### 2026-06-23 — Review `feat/pe-chart-enhancements`
- Compared the fetched feature ref against `origin/main` (3 commits; 4 files).
- Found overlapping history requests can populate/render the cache with an obsolete
  range after the user has selected a newer range.
- Found history is clipped to a custom start before interpolation, so a window starting
  inside a sparse forward-P/E gap loses values until the next in-window anchor.
- Refactoring opportunities: share the duplicated column chooser and replace the
  categorical union-date axis with a true time axis.

### 2026-06-22 — Review fixes on `feat/delta-fwd-pe` (sort, config hardening, delta perf)
- Reviewed the whole project; fixed four items, each its own commit:
  1. Delta page sorted wrong — the `delta_pct` column's `sort: "desc"` overrode the JS
     magnitude sort. Dropped it so default order is |Δ%|-desc (header still sortable).
  2. `HostConfig` now `extra="forbid"` — a typo'd `auth_token` no longer silently
     disables auth.
  3. `build_app` calls `check_secret` (renamed from `_check_secret`) so a weak secret +
     auth is rejected regardless of construction path, not just via `load_config`.
  4. `api_delta` read the full per-ticker history (back to 1986, ~10k rows × 39) every
     request. New `storage.latest_value_date` + `views._delta_rows` bound the read to
     `[latest forward_pe+price anchor <= window target, now]`; provably identical to the
     full interpolation (full-read fallback when no priced anchor predates target).
     ~29x faster for 1M, ~5x for 1Y/YTD. `_window_target` shared by `_delta_rows`/`_delta_point`.
- Tests: +`test_unknown_key_rejected`, +`test_build_app_rejects_weak_secret_with_auth`,
  +`test_bounded_read_matches_full_history` (6 tickers × 4 windows). 30 pass.
- Also trimmed README 103→65 lines.

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

### 2026-06-22 — Security & robustness hardening (review follow-up)
- Secrets masked in the startup banner (opt-in via `GAMBLERS_TOOLBOX_LOG_SECRETS`).
- Refuse to start when `auth_tokens` set but `secret_key` is default/empty/short.
- Sessions store the token hash and revalidate each request, so removing a token revokes
  its cookies; session `max_age` set to 7 days.
- Clear "copy config.sample.toml" errors; README documents per-module config + upgrade
  data migration.
- ai_ratios: coverage threshold (keep last-good below 95%), single-flight refresh (409),
  Wikipedia timeout + bounded Yahoo deadline.
- Lifecycle: schedulers started synchronously + retained; both modules have on_shutdown.

### 2026-06-22 — Unify pe_monitor + ai_ratios under one FastAPI app
- Built `core/` host shell with a pluggable `Module` interface and auto-discovery of
  `modules/*` exposing `MODULE`.
- Moved `pe_monitor/` → `modules/pe_monitor/` (git mv; backfill `_bootstrap` unaffected).
  Converted `app.py` → `views.py` (APIRouter); made `scheduler.py` imports relative;
  fixed dashboard `url_for(path=)`, prefixed client `fetch` calls and the manifest.
- Built `modules/ai_ratios/` from the old `ai_ratios.py` CLI: split compute (`core.py`),
  added cache + own scheduler (`cache.py`), router + Jinja dashboard. Dropped the CLI.
- Added shared auth (`SessionMiddleware` + token gate), default-disabled.
- Consolidated dependencies into a single top-level `requirements.txt` (FastAPI/uvicorn;
  dropped Flask). Verified end-to-end: landing, both modules, static, `/docs` (tagged per
  module), auth on/off, and backfill imports.
