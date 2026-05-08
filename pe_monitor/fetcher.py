"""Fetch P/E snapshots from Yahoo Finance and run the periodic crawler."""

from datetime import date

import yfinance as yf
from apscheduler.schedulers.background import BackgroundScheduler

import storage


def _first(info: dict, *keys: str):
    """Return the first key whose value is not None. Yahoo often mirrors the
    same number under multiple keys (trailingEps / epsTrailingTwelveMonths,
    forwardEps / epsForward), so fall through aliases."""
    for k in keys:
        v = info.get(k)
        if v is not None:
            return v
    return None


def fetch_pe(ticker: str) -> dict:
    info = yf.Ticker(ticker).info

    price = _first(info, "currentPrice", "regularMarketPrice")
    trailing_eps = _first(info, "trailingEps", "epsTrailingTwelveMonths")
    forward_eps = _first(info, "forwardEps", "epsForward")
    ttm_pe = info.get("trailingPE")
    fwd_pe = info.get("forwardPE")

    if ttm_pe is None and price and trailing_eps and trailing_eps > 0:
        ttm_pe = price / trailing_eps
    if fwd_pe is None and price and forward_eps and forward_eps > 0:
        fwd_pe = price / forward_eps

    return {
        "date": date.today().isoformat(),
        "name": info.get("longName", ""),
        "currency": info.get("currency"),
        "price": price,
        "trailing_eps": trailing_eps,
        "forward_eps": forward_eps,
        "ttm_pe": ttm_pe,
        "forward_pe": fwd_pe,
    }


def snapshot_all(tickers: list[str], db_path: str) -> None:
    for t in tickers:
        try:
            snap = fetch_pe(t)
            storage.append_snapshot(db_path, t, snap)
        except Exception as e:
            print(f"  Warning: could not fetch {t}: {e}")


def start_scheduler(
    tickers: list[str], db_path: str, interval_seconds: int
) -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        snapshot_all,
        "interval",
        seconds=interval_seconds,
        args=[tickers, db_path],
        id="snapshot",
    )
    scheduler.start()
    snapshot_all(tickers, db_path)
    return scheduler
