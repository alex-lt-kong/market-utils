# Project Memory

## Active Status

**Latest:** Added a **4th module** `modules/crypto_tracker/` (display "Crypto Tracker", slug
`crypto-tracker`, icon 🪙, `order=120` → sorts last on the landing menu) on branch
`feat/crypto-tracker`, cut from `feat/bloomberg-terminal-theme` so it inherits `terminal.css` and the
themed siblings. Ports a standalone Binance-TWR CLI into the module architecture: computes **TWR /
MWR (XIRR) / CAGR** over All-time/5Y/3Y/YTD/1Y/90D/30D for a multi-asset (BTC/ETH) portfolio whose
transactions live in a CSV of `(date, asset, delta, note)` rows, USD-proxied by Binance USDT-pair
closes. Same cache+scheduler shape as `ai_ratios`: in-memory `cache.py` (single-flight refresh, keeps
last-known-good + `last_error` on failure), 15-min `BackgroundScheduler` + one-off initial pull,
served by `views.py` (dashboard + `/api/data` + `POST /api/refresh`). Terminal-themed dashboard:
holdings table beside a sign-colored returns table (n/a under ~1y). Historical klines cached on disk
(`.price_cache.json`, gitignored — immutable). **`portfolio.csv` is gitignored** (real holdings stay
local, like `config.toml`); committed `portfolio.sample.csv` documents the schema. No host-config or
new dependency (`requests` already pinned). Prior `feat/bloomberg-terminal-theme` (price panel +
per-panel toggles, review-clean) is the unmerged base of this branch.

**Deferred (event-triggered, not scheduled):** a stock split will put a fake cliff in the
price panel because daily snapshots store raw `currentPrice` (`fetcher.py:46`) and are never
back-adjusted — only the `auto_adjust=True` backfill is. P/E lines are split-invariant so they
stay smooth, making price spuriously diverge. Fix WHEN the first split lands: read `yt.splits`
at crawl time, back-adjust prior stored `price`/`volume`, migrate existing rows. No split column
in `storage.py` today; no `yt.splits` read anywhere.

**Objective:** Ship the `crypto-tracker` module on `feat/crypto-tracker`. Because it branches off the
still-unmerged `feat/bloomberg-terminal-theme` (for `terminal.css`), merge order is bloomberg first,
then crypto-tracker — or rebase crypto-tracker onto `main` once bloomberg lands.

**Immediate next steps:** Commit/push `feat/crypto-tracker` and open its PR. **Binance egress is
unverified in this sandbox** — the live `compute()`/scheduler path (and thus the dashboard with real
data) has NOT been exercised here; only the network-free math + API/template tests have. Verify a live
refresh in an environment that can reach `api.binance.com` before relying on it. The pre-existing
`tests/test_app.py::test_landing_and_modules_open` hang is intermittent (passed in this run).

- `core/` — host shell: `module.py` (interface), `registry.py` (discovery), `auth.py`
  (token→cookie gate), typed `config.py` (Pydantic `HostConfig`), `main.py`
  (`build_app(config, modules)` factory + `create_app`), `__main__.py`. Tests in `tests/`.
- `modules/pe_monitor/` — P/E dashboard (was a standalone Flask app). `views.py` holds the
  APIRouter; `backfill/` tools still run standalone via the `_bootstrap` sys.path shim.
- `modules/ai_ratios/` — S&P AI-exposure ratio; computes via `core.py`, caches in `cache.py`
  with its own scheduler; `views.py` serves dashboard + JSON API.
- `modules/crypto_tracker/` — crypto portfolio TWR/MWR/CAGR. `twr.py` (math + `compute()`),
  `cache.py` (in-memory cache + 15-min scheduler), `views.py` (dashboard + JSON API). Reads
  `portfolio.csv` (gitignored; `portfolio.sample.csv` committed); disk price cache `.price_cache.json`.

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
- Live E2E (Playwright): `npm i playwright` in `~/pwtest` + `npx playwright install chromium`;
  run `python3 -m core --config config.toml` on :9090 (token `demo-token-1234`, prod-copy DB).
  Drive: select tickers via `gridApi.forEachNode(n => n.setSelected(true))`, click
  `.range-btn[data-range=...]`, then read `chartInstances` scales (geometry/ticks) or
  screenshot `#chart-card-<T>`. Jinja auto-reloads dashboard.html (no app restart needed).
  npm registry reachable here; external UAT host is NOT (sandbox egress).

## Activity Log

### 2026-06-26 — Add Crypto Tracker module (branch `feat/crypto-tracker`)
- New self-contained module `modules/crypto_tracker/` (4th; "Crypto Tracker", slug `crypto-tracker`,
  icon 🪙, `order=120`). Ports the standalone `twr.py` Binance CLI into the host architecture without
  changing its return math; assets in `config.ASSET_SYMBOLS` (BTC/ETH), 15-min refresh. Branched off
  `feat/bloomberg-terminal-theme` for `terminal.css`.
- `twr.py`: kept the original pure functions (`balance_at`, `xirr`/`xnpv`, `twr_over_range`,
  `mwr_over_range`, `annualize_cumul`) and added `compute()` → `{computed_at, as_of, total_value,
  holdings[], ranges[]}`; `main()` still prints standalone via `python -m modules.crypto_tracker.twr`.
  `load_portfolio()` returns `[]` when the CSV is absent.
- `cache.py`/`views.py` mirror `ai_ratios`: single-flight in-memory cache, `BackgroundScheduler`
  (interval + one-off initial), `GET /api/data`, `POST /api/refresh` (409 when busy). A failed
  refresh keeps last-known-good and sets `last_error`, so Binance being unreachable degrades to a
  warning rather than an error page.
- Dashboard (`templates/dashboard.html`, terminal-themed): holdings table + sign-colored
  TWR/MWR/CAGR table; renders a "no data yet" state from the empty cache (200 before first compute,
  like ai_ratios). Jinja `pct` macro for n/a/up/down; money via `{:,.2f}`.
- Data: `portfolio.csv` **gitignored** (real holdings local-only — user's call), seeded by committed
  `portfolio.sample.csv`; `.price_cache.json` gitignored (immutable klines). README table + Run steps
  updated. No host-config change; `requests` already pinned.
- Tests: `tests/test_crypto_tracker.py` (17) — TWR doubles on a single deposit; TWR≈0 vs MWR>0 on a
  flat-price dip-buy (the time- vs money-weighted distinction); XIRR recovers 10%; CAGR n/a under a
  year; populated-template render; refresh single-flight (409) + keeps-last-good on failure. Updated
  `test_app.py` discovery-order/landing/openapi-tag assertions for the 4th module. **93 tests pass.**
  Network-free — the live Binance `compute()` path was NOT exercised here (sandbox egress).

### 2026-06-25 — Price panel + per-panel toggles on pe-monitor charts (branch `feat/bloomberg-terminal-theme`)
- Added a third stacked panel (cyan `#3bc9ff` line) above P/E, reusing the existing
  `pinX`/`Y_AXIS_WIDTH`/`offset:false` machinery so price, P/E and volume share one date axis.
  Front-end only; `price`/`currency` already in each history row. Commit `531aaea`.
- Rationale: P/E = price/EPS, so price diverging from TTM P/E is the visual tell of an EPS
  revision. Chose a separate panel over a dual y-axis (avoids the arbitrary-scale trap and the
  right-pinned-axis layout from `581d9f7`).
- Refined (`0416547`): panel 110px→240px and a **logarithmic** price y-axis (price is always
  positive, so log is safe; P/E stays linear because it can go negative/null). Equal % moves now
  read as equal height, fixing the price-vs-P/E amplitude mismatch the short linear panel caused.
- Added three independent global **panel toggles** (Price / P/E / Volume) that show/hide each
  panel across all ticker charts via `hide-*` classes on `section.charts`; persisted in
  `localStorage`. Distinct from the TTM/Forward/IBES legend, which toggles lines inside the P/E panel.
- Extended `test_chart_e2e.py`: price panel exists and aligns with P/E + volume; Volume toggle hides panels.
- Split handling deliberately deferred until the first split occurs (see Active Status).
- Review pass `34179f3` — four findings fixed: (1) P1 font license — added verbatim SIL OFL 1.1
  at `core/static/fonts/OFL.txt` beside the `.woff2` files (canonical text; upstream fetch only
  paraphrased, so worth a re-check). (2) Hiding Volume stripped every date label (only Volume
  showed the x axis) — date labels now follow `bottomVisiblePanel()` via a shared `dateX(key)`;
  toggles re-render through new `redrawCharts()`. (3) Value tags could pile up at the plot bottom —
  added an upward bounce pass after the downward spacing pass. (4) Mouse-only chips — shared
  `makeChip()` gives series + panel chips `role=button`/`tabindex`/`aria-pressed` + Enter/Space.
- e2e now guards the date-axis re-homing (Volume visible→owns axis; hidden→labels move to P/E) and
  chip a11y attributes. No deterministic test for the tag-overlap case (tag pixel positions aren't exposed).

### 2026-06-24 — Review `feat/bloomberg-terminal-theme`
- Fetched and compared the four-commit branch with current `origin/main` (15 changed files);
  `git diff --check`, Python compilation, and 75-test collection pass.
- Found Chart.js visibility is checked through the tri-state `meta.hidden`; a newly rebuilt chart
  has `meta.hidden === null`, so a dataset configured with `hidden: true` still gets a ghost
  last-value tag. Use `chart.isDatasetVisible(i)` and cover reload/range rebuilds.
- Found the last-value plugin scans backward over terminal nulls, so a series currently undefined
  during a forecast-loss window can show a stale pre-loss value pinned to the right axis.
- Found the two redistributed IBM Plex Mono WOFF2 files have no OFL/copyright text in the tree.
- Full and non-E2E pytest runs timed out; `-vv` locates the stall at the first TestClient request,
  `tests/test_app.py::test_landing_and_modules_open`, before any branch-specific assertion. The
  same isolated test also times out on an exported `origin/main` tree, confirming it is not a
  regression from this branch.

### 2026-06-24 — Bloomberg-terminal theme + rename to "Gambler's Terminal" (branch `feat/bloomberg-terminal-theme`)
- Overhauled look/feel to mimic a Bloomberg Terminal. New shared `core/static/terminal.css`
  (served at `/static/terminal.css`, linked by every page): black canvas, amber chrome, green/red
  data, cyan functions/links, sharp corners, dense monospace. Palette centralized in CSS vars,
  reusing legacy `--bg/--surface/--ink/--muted/--border/--accent` names so the variable-driven
  `dashboard.html` recolored almost for free (data pages drop their inline `:root` colours).
- Pages: landing → "function menu" (amber header + live clock, amber function bar, numbered rows,
  cyan mnemonics, fixed bottom status bar); calculator + ai_ratios + delta + dashboard all themed.
- ag-grid `themeQuartz.withParams` → dark (amber headers, black rows) on both pe_monitor grids.
  Chart.js: TTM→amber, forward→red, IBES→green on black; dim grid/ticks via `Chart.defaults`;
  loss-band tints + cutoff line retinted; volume bars muted. Bloomberg *GP*-style conventions
  added: price axis moved to the **right** on both stacked charts (pe/vol stay pixel-aligned via
  `pinX` now padding *both* ends — moving y off the left un-pinned it), plus a `lastValueTagPlugin`
  drawing a colored latest-value chip per line over the right axis (vertically dodged when close).
  Crosshair declined by user. e2e alignment test still green.
- Follow-up UI tweaks (same branch): the struck legend series and the selected time range now
  persist via localStorage (`pe-hidden-series`, `pe-range`) — a hidden line survives a range/
  ticker rebuild instead of resurrecting (it was rebuilt fresh each `renderChart`), and the page
  reopens on the last-selected range, not "All". Playwright-verified.
- Then: replaced the repeated per-chart legends with ONE shared HTML legend (`#series-legend`,
  three TTM/Forward/IBES chips that drive `hiddenSeries` across every chart; per-chart Chart.js
  legends set `display:false`). Added column filters to the **delta** page (ag-grid floating-filter
  row — text on ids, `agNumberColumnFilter` on values, e.g. Fwd P/E < 20). Playwright-verified
  (3 chips, toggle hides line+tag on all charts; delta `now<20` → 20/39 rows). e2e still green.
- Font: bundled **IBM Plex Mono** locally (OFL, `core/static/fonts/*.woff2`, no CDN) as `--mono`
  + ag-grid `fontFamily` + `Chart.defaults.font.family`. Closest free face to the Terminal's
  institutional monospace (VT323/Share Tech Mono compared, rejected). Emoji fallbacks appended;
  sandbox has no emoji font so module icons (📈🗻🤖) tofu in screenshots only, fine in-browser.
- Rename **Gambler's Toolbox → Gambler's Terminal** across display strings only (FastAPI title,
  landing, README, manifest name/short_name + black theme colour, config-sample comments). Kept
  internal ids (slug `gamblers-toolbox`, env var `GAMBLERS_TOOLBOX_CONFIG`, log prefix) unchanged.
- Verified: 76 tests pass (incl. chart e2e geometry — recolor moved no pixels); Playwright drove
  all pages, `document.fonts.check` confirms IBM Plex Mono loaded, zero console errors. Local
  commit; not pushed, no PR.

### 2026-06-24 — Add Pyramiding Calculator module (branch `feat/avg-down-calculator`)
- New self-contained module `modules/averaging_calc/` (display name "Pyramiding Calculator",
  slug `averaging-calc`, icon 🗻 Mount Fuji — Unicode has no pyramid glyph): given a position
  (qty, avgCost, mktPx) and a target P/L%, returns the shares to add at market to move the %
  from its current level to the target. Landing card at order=20. Primary use: pressing a
  *winning* position — raise cost basis to dial a gaudy gain back (e.g. +20→+15); also averages
  down a loss. No data/scheduler/lifespan. README module table updated.
- Math (`calc.py`): `x = qty·(px − avgCost·(1+t)) / (px·t)`, i.e. new% = Q(P−C)/(QC+xP) =
  constant dollar P/L over a growing cost basis. P/L% only shrinks toward 0; reachable band is
  strictly between 0 and current%. Dollar P/L is unchanged by the buy.
- **Single source of truth (Approach A):** all math lives in `calc.py::evaluate()`; the page
  `calculator.html` just `fetch()`es `GET /api/calc` (debounced, race-guarded) and renders — no
  formula in the browser, so nothing can drift. `target_pct` is optional (current-only readout);
  an unreachable target is `200 {reachable:false, plan:null}`, not an error; whole-share figures
  are computed server-side too.
- **Hardening from an independent review (all verified):** (1) non-finite inputs `inf`/`nan`/
  `1e309` were returning HTTP **500** (Starlette `JSONResponse` uses `allow_nan=False`) — now
  `math.isfinite` validates all four inputs → **400**; (2) a `_require_finite_result` guard on
  *every* derived value — the top-level readout (`current_pnl_pct`/`pnl_amount`, which leaked
  `inf` for extreme finite inputs like `avg_cost=1e-308`) **and** the plan (incl. before
  `math.ceil`, which `OverflowError`s on `inf`) — so all overflow 400s, never 500; (3)
  `target==current` float knife-edge could emit a ~1e-12 *negative*
  share count — guarded by requiring `shares_to_buy > 0` before marking reachable.
- Verified: re-derived formula independently; 200k+50k random round-trips reproduce the target%
  to ~1e-13; monotonicity 0 violations; **Playwright** browser drive renders correctly with no
  console errors. `tests/test_averaging_calc.py` (18) + `test_discovery_order_and_unique_slugs`
  fix. **76 tests pass.** Pushed; PR not yet opened.

_(Older entries moved to `MEMORY_ARCHIVE.md`.)_
