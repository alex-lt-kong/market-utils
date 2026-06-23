import os
import tempfile
from datetime import date, timedelta

from modules.pe_monitor import storage
from modules.pe_monitor.views import _history_rows, _interpolate_series


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
