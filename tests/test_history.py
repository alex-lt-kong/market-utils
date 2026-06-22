import os
import tempfile
from datetime import date, timedelta

from modules.pe_monitor import storage
from modules.pe_monitor.views import _history_rows


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
