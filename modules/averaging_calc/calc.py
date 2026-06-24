"""Averaging math: shares to buy to move a position's P/L% to a target.

Buying x shares at the market price pulls the average cost toward that price, so
the P/L% always shrinks toward 0 — it can never reach 0 or grow past the current
level. The reachable target band is therefore strictly between 0 and current%.
Dollar P/L is unchanged: shares bought at market add no instant gain or loss.
"""


def _strictly_between_zero_and(target: float, current: float) -> bool:
    if current == 0 or target == 0:
        return False
    return (current > 0 and 0 < target < current) or (current < 0 and current < target < 0)


def shares_to_target(qty: float, avg_cost: float, mkt_px: float, target_frac: float) -> float:
    """Shares to buy at mkt_px so the position's P/L fraction becomes target_frac."""
    if qty <= 0 or avg_cost <= 0 or mkt_px <= 0:
        raise ValueError("qty, avg_cost and mkt_px must be positive")
    current = mkt_px / avg_cost - 1.0
    if not _strictly_between_zero_and(target_frac, current):
        raise ValueError(
            f"target {target_frac:.4%} is unreachable; it must lie strictly "
            f"between 0% and the current {current:.4%}"
        )
    return qty * (mkt_px - avg_cost * (1.0 + target_frac)) / (mkt_px * target_frac)


def plan(qty: float, avg_cost: float, mkt_px: float, target_pct: float) -> dict:
    """Full averaging plan for the given target P/L percent."""
    add = shares_to_target(qty, avg_cost, mkt_px, target_pct / 100.0)
    new_qty = qty + add
    new_avg = (qty * avg_cost + add * mkt_px) / new_qty
    pnl_amount = qty * (mkt_px - avg_cost)  # unchanged by buying at market
    return {
        "current_pnl_pct": (mkt_px / avg_cost - 1.0) * 100.0,
        "pnl_amount": pnl_amount,
        "shares_to_buy": add,
        "capital_required": add * mkt_px,
        "new_qty": new_qty,
        "new_avg_cost": new_avg,
        "new_pnl_pct": (mkt_px / new_avg - 1.0) * 100.0,
    }
