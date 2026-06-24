import pytest
from fastapi.testclient import TestClient

from modules.averaging_calc import calc


def test_gain_dilution():
    p = calc.plan(qty=100, avg_cost=100, mkt_px=120, target_pct=15)
    assert p["shares_to_buy"] == pytest.approx(500 / 18)  # 27.78
    assert p["new_avg_cost"] == pytest.approx(120 / 1.15)
    assert p["new_pnl_pct"] == pytest.approx(15)
    assert p["current_pnl_pct"] == pytest.approx(20)


def test_loss_average_down():
    p = calc.plan(qty=100, avg_cost=100, mkt_px=80, target_pct=-10)
    assert p["shares_to_buy"] == pytest.approx(125)
    assert p["new_pnl_pct"] == pytest.approx(-10)


def test_dollar_pnl_unchanged_by_buying_at_market():
    p = calc.plan(qty=100, avg_cost=100, mkt_px=120, target_pct=15)
    assert p["pnl_amount"] == pytest.approx(2000)  # == qty * (px - avg), pre-buy
    assert p["capital_required"] == pytest.approx(p["shares_to_buy"] * 120)


@pytest.mark.parametrize("target", [0, 20, 25, -5])  # at/past current, wrong side, zero
def test_unreachable_target_rejected(target):
    with pytest.raises(ValueError):
        calc.plan(qty=100, avg_cost=100, mkt_px=120, target_pct=target)


@pytest.mark.parametrize("kw", [{"qty": 0}, {"avg_cost": 0}, {"mkt_px": -1}])
def test_non_positive_inputs_rejected(kw):
    args = {"qty": 100, "avg_cost": 100, "mkt_px": 120, "target_pct": 15, **kw}
    with pytest.raises(ValueError):
        calc.plan(**args)


def test_api_calc_ok_and_bad(make_app):
    c = TestClient(make_app())
    r = c.get("/averaging-calc/api/calc", params={"qty": 100, "avg_cost": 100, "mkt_px": 120, "target_pct": 15})
    assert r.status_code == 200 and r.json()["new_pnl_pct"] == pytest.approx(15)
    bad = c.get("/averaging-calc/api/calc", params={"qty": 100, "avg_cost": 100, "mkt_px": 120, "target_pct": 25})
    assert bad.status_code == 400


def test_page_loads(make_app):
    assert TestClient(make_app()).get("/averaging-calc/").status_code == 200
