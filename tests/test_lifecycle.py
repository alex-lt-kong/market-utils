from fastapi.testclient import TestClient

import modules.ai_ratios.cache as cache
import modules.pe_monitor.scheduler as sched
from modules.pe_monitor import storage


def _capture(store, fn):
    def wrap(*a, **k):
        obj = fn(*a, **k)
        store.append(obj)
        return obj
    return wrap


def test_lifespan_starts_and_stops_schedulers(make_app, monkeypatch):
    # keep startup hermetic: no real network in the one-off initial jobs
    monkeypatch.setattr(cache, "_scheduled_refresh", lambda: None)
    monkeypatch.setattr(sched, "_snapshot_safe", lambda *a, **k: None)
    pe, ai = [], []
    monkeypatch.setattr(sched, "start_scheduler", _capture(pe, sched.start_scheduler))
    monkeypatch.setattr(cache, "BackgroundScheduler", _capture(ai, cache.BackgroundScheduler))

    with TestClient(make_app()) as c:        # runs lifespan startup
        assert c.get("/").status_code == 200
    # context exit ran shutdown: each module stopped its own local scheduler
    assert pe and not pe[0].running
    assert ai and not ai[0].running


def test_schedulers_disabled_still_initialises(make_app, monkeypatch):
    started = []
    monkeypatch.setattr(sched, "start_scheduler", lambda *a, **k: started.append(1))
    monkeypatch.setattr(cache, "BackgroundScheduler", lambda *a, **k: started.append(1))
    inited = []
    real_init = storage.init_db
    monkeypatch.setattr(storage, "init_db", _capture(inited, real_init))

    with TestClient(make_app(enable_schedulers=False)) as c:
        assert c.get("/").status_code == 200
    assert not started     # no background jobs when disabled
    assert inited          # but resource init (DB) still ran (#1)
