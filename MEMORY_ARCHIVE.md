# Project Memory — Archive

Older activity-log entries pruned from `MEMORY.md` (newest first).

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
