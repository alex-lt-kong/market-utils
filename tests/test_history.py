import os
import tempfile
from datetime import date, timedelta

from modules.pe_monitor import storage
from modules.pe_monitor.views import (
    _collapse_bucket,
    _downsample,
    _history_rows,
    _interpolate_series,
    _pick_bucket,
)


def _mkdb(rows):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    storage.init_db(path)
    for r in rows:
        storage.append_snapshot(path, "T", r)
    return path


def test_history_fills_window_start_gap():
    # Two forward_pe anchors 40 days apart over a daily price series. A window
    # starting inside the gap must still get an interpolated value at its first
    # row — the read reaches back to the prior anchor, then clips to the window.
    base = date(2020, 1, 1)
    rows = []
    for i in range(41):
        r = {"date": (base + timedelta(days=i)).isoformat(), "price": 100.0 + i}
        if i == 0:
            r["forward_pe"] = 10.0
        if i == 40:
            r["forward_pe"] = 20.0
        rows.append(r)
    db = _mkdb(rows)
    try:
        start = (base + timedelta(days=20)).isoformat()
        out = _history_rows(db, "T", start, None)
        assert out[0]["date"] == start
        assert out[0]["forward_pe"] is not None
        assert out[0]["forward_pe_interpolated"] is True
        assert all(r["date"] >= start for r in out)  # pre-window rows clipped off
    finally:
        os.unlink(db)


def test_interpolate_breaks_across_forward_loss():
    # June: profit; Aug & Sep: forecast loss (negative stored P/E); Oct: profit.
    # The line must break across the loss — never bridge it or plot a negative.
    rows = [
        {"date": "2023-06-15", "price": 68.0, "forward_pe": 115.0},  # eps ~ +0.59
        {"date": "2023-07-15", "price": 60.0},                       # gap day
        {"date": "2023-08-15", "price": 62.0, "forward_pe": -60.0},  # loss anchor
        {"date": "2023-09-15", "price": 64.0, "forward_pe": -58.0},  # loss anchor
        {"date": "2023-10-15", "price": 67.0, "forward_pe": 13.0},   # eps ~ +5.1
    ]
    by = {r["date"]: r.get("forward_pe")
          for r in _interpolate_series([dict(r) for r in rows], "forward_pe", "f_i")}
    assert by["2023-06-15"] == 115.0   # positive anchor kept
    assert by["2023-07-15"] is None    # span bounded by a loss -> gap
    assert by["2023-08-15"] is None    # loss anchor served as gap
    assert by["2023-09-15"] is None    # loss anchor served as gap
    assert by["2023-10-15"] == 13.0    # positive anchor kept
    assert all(v is None or v > 0 for v in by.values())  # never negative


def test_history_fills_custom_window_between_anchors():
    # A custom [start, end] window strictly between two sparse anchors must still
    # interpolate — the read reaches forward to the right anchor, not just back.
    base = date(2020, 1, 1)
    rows = []
    for i in range(41):
        r = {"date": (base + timedelta(days=i)).isoformat(), "price": 100.0 + i}
        if i == 0:
            r["forward_pe"] = 10.0
        if i == 40:
            r["forward_pe"] = 20.0
        rows.append(r)
    db = _mkdb(rows)
    try:
        s = (base + timedelta(days=15)).isoformat()
        e = (base + timedelta(days=20)).isoformat()
        out = _history_rows(db, "T", s, e)
        assert out and out[0]["date"] == s and out[-1]["date"] == e
        assert all(r["forward_pe"] is not None for r in out)   # interpolated, not blank
        assert all(s <= r["date"] <= e for r in out)           # clipped to the window
    finally:
        os.unlink(db)


def test_interpolate_nulls_zero_pe():
    # A zero P/E is a degenerate placeholder, not a value -> served as a gap, not y:0.
    rows = [
        {"date": "2026-01-01", "price": 100.0, "forward_pe": 0.0},   # edge zero
        {"date": "2026-02-01", "price": 110.0, "forward_pe": 10.0},
        {"date": "2026-03-01", "price": 120.0, "forward_pe": 12.0},
    ]
    by = {r["date"]: r.get("forward_pe")
          for r in _interpolate_series([dict(r) for r in rows], "forward_pe", "f_i")}
    assert by["2026-01-01"] is None     # zero nulled, not plotted at y:0
    assert by["2026-02-01"] == 10.0


def test_collapse_bucket_preserves_loss_over_recovered_last_row():
    # A historical bucket: a loss earlier in it must survive even when the last row
    # recovered — otherwise coarse zoom hides the break/band the daily view shows.
    bucket = [
        {"date": "2024-01-01", "forward_pe": None, "forward_pe_loss": True,
         "forward_pe_ibes": None, "forward_pe_ibes_loss": True,
         "ttm_pe": None, "trailing_eps": -1.0, "volume": 10},
        {"date": "2024-01-15", "forward_pe": 12.0, "forward_pe_loss": False,
         "forward_pe_ibes": 11.0, "forward_pe_ibes_loss": False,
         "ttm_pe": 8.0, "trailing_eps": 3.0, "volume": 20},
    ]
    out = _collapse_bucket(bucket)
    assert out["forward_pe"] is None and out["forward_pe_loss"] is True
    assert out["forward_pe_ibes"] is None and out["forward_pe_ibes_loss"] is True
    assert out["ttm_pe"] is None          # TTM loss preserved despite recovered last row
    assert out["volume"] == 30            # volume still sums


def test_collapse_bucket_keeps_last_when_no_loss():
    bucket = [
        {"date": "2024-01-01", "forward_pe": 10.0, "forward_pe_loss": False,
         "ttm_pe": 9.0, "trailing_eps": 3.0, "volume": 10},
        {"date": "2024-01-15", "forward_pe": 12.0, "forward_pe_loss": False,
         "ttm_pe": 8.0, "trailing_eps": 3.0, "volume": 20},
    ]
    out = _collapse_bucket(bucket)
    assert out["forward_pe"] == 12.0 and out["ttm_pe"] == 8.0 and out["volume"] == 30


def test_collapse_bucket_open_keeps_recovered_last_value():
    # The open (latest) bucket drives the chart endpoint + header: a loss earlier in
    # it that recovered by the last row must NOT null today's value to a gap/N/A.
    bucket = [
        {"date": "2024-01-01", "forward_pe": None, "forward_pe_loss": True,
         "forward_pe_ibes": None, "forward_pe_ibes_loss": True,
         "ttm_pe": None, "trailing_eps": -1.0, "volume": 10},
        {"date": "2024-01-15", "forward_pe": 12.0, "forward_pe_loss": False,
         "forward_pe_ibes": 11.0, "forward_pe_ibes_loss": False,
         "ttm_pe": 8.0, "trailing_eps": 3.0, "volume": 20},
    ]
    out = _collapse_bucket(bucket, is_open=True)
    assert out["forward_pe"] == 12.0 and not out["forward_pe_loss"]
    assert out["forward_pe_ibes"] == 11.0 and not out["forward_pe_ibes_loss"]
    assert out["ttm_pe"] == 8.0
    assert out["volume"] == 30            # volume still sums


def test_downsample_open_bucket_keeps_recovered_endpoint():
    # End to end through _downsample: a loss inside the final (open) bucket whose
    # last raw row recovered must leave the chart endpoint on the recovered value,
    # while a historical loss bucket still collapses to a gap.
    base = date(2022, 1, 1)
    rows = [{"date": (base + timedelta(days=i)).isoformat(), "price": 100.0,
             "forward_pe": 10.0, "forward_pe_loss": False,
             "ttm_pe": 9.0, "trailing_eps": 3.0, "volume": 5} for i in range(900)]
    bucket = _pick_bucket(len(rows))
    assert bucket > 1                                  # downsampling actually engages
    last_b = date.fromisoformat(rows[-1]["date"]).toordinal() // bucket
    last_idxs = [i for i, r in enumerate(rows)
                 if date.fromisoformat(r["date"]).toordinal() // bucket == last_b]
    assert len(last_idxs) >= 2                          # open bucket has a mid-bucket point
    rows[last_idxs[0]].update(forward_pe=None, forward_pe_loss=True, ttm_pe=None)
    rows[-1].update(forward_pe=15.0, forward_pe_loss=False, ttm_pe=12.0)
    out = _downsample(rows, bucket, open_end=True)
    assert out[-1]["forward_pe"] == 15.0 and not out[-1].get("forward_pe_loss")
    assert out[-1]["ttm_pe"] == 12.0
    # Same data as a custom historical window (open_end=False): the right-edge loss
    # must be kept, not exempted just for being the final bucket.
    hist = _downsample([dict(r) for r in rows], bucket, open_end=False)
    assert hist[-1]["forward_pe"] is None and hist[-1]["forward_pe_loss"] is True
    assert hist[-1]["ttm_pe"] is None


def test_api_history_keeps_loss_at_custom_historical_edge(monkeypatch):
    # The route must only exempt the final bucket when the window reaches the latest
    # row. A custom `end` in the past has a historical right edge: a recovered loss
    # there stays a gap, while the live `range=all` view shows the recovery.
    from modules.pe_monitor import config as pe_config, views
    base = date(2022, 1, 1)
    base_ord = base.toordinal()
    n, end_idx = 900, 860
    rows = [{"date": (base + timedelta(days=i)).isoformat(), "price": 100.0,
             "forward_pe": 10.0, "forward_pe_ibes": 10.0} for i in range(n)]
    bucket = _pick_bucket(end_idx + 1)
    assert bucket > 1                                       # the window downsamples
    last_b = (base_ord + end_idx) // bucket
    fb = [i for i in range(end_idx + 1) if (base_ord + i) // bucket == last_b]
    assert len(fb) >= 2                                     # final bucket spans >1 day
    rows[fb[0]]["forward_pe"] = -10.0                       # forecast loss at the right edge
    db = _mkdb(rows)
    monkeypatch.setattr(pe_config, "load_config",
                        lambda *a, **k: {"database_path": db, "tickers": ["T"]})
    views._cfg.cache_clear()
    try:
        hist = views.api_history("T", end=rows[end_idx]["date"])
        assert hist[-1]["date"] <= rows[end_idx]["date"]
        assert hist[-1]["forward_pe"] is None and hist[-1]["forward_pe_loss"] is True
        full = views.api_history("T", range_="all")
        assert full[-1]["forward_pe"] == 10.0              # latest row profitable -> shown
    finally:
        views._cfg.cache_clear()
        os.unlink(db)
