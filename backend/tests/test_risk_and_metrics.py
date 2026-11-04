from decimal import Decimal

import pytest

from app.analytics.metrics import metrics
from app.backtesting.engine import simulate
from app.portfolio.ledger import Ledger
from app.schemas.domain import ProfileConfig, default_strategy


def test_drawdown_and_sample_daily_returns():
    profile = ProfileConfig(starting_capital="100")
    ledger = Ledger(profile)
    curve = [{"equity": str(v), "exposure": "0"} for v in (100, 120, 90, 108)]
    result = metrics(curve, ledger, profile)
    assert result["total_return"] == pytest.approx(0.08)
    assert result["max_drawdown"] == pytest.approx(-0.25)
    assert result["drawdown_duration_sessions"] == 2
    assert result["daily_returns"] == pytest.approx([0, 0.2, -0.25, 0.2])
    assert result["annualized_return"] is None
    assert result["annualized_volatility"] > 0


def test_signal_time_quantity_rejects_unaffordable_opening_gap(data):
    bars = [
        b.model_copy(
            update={
                "open": Decimal(100),
                "high": Decimal(100),
                "low": Decimal(100),
                "close": Decimal(100),
            }
        )
        for b in data.bars[:3]
    ]
    bars[1] = bars[1].model_copy(
        update={
            "open": Decimal(500),
            "high": Decimal(500),
            "low": Decimal(500),
            "close": Decimal(500),
        }
    )
    fixture = data.model_copy(update={"bars": bars})
    profile = ProfileConfig(
        start_date=bars[0].session_date,
        end_date=bars[-1].session_date,
        account_currency="USD",
        fixed_fee="2.50",
    )
    config = default_strategy()
    config.sizing.value = Decimal("0.95")
    result = simulate(config, profile, fixture, benchmark=False, gross=False)
    first = result["orders"][0]
    assert first["status"] == "rejected"
    assert (
        "exposure" in first["rejection_reason"]
        or "allocation" in first["rejection_reason"]
        or "cash" in first["rejection_reason"]
    )
    assert first["quantity"] == "94"  # determined with 100, never the future 500 open
    assert first["fees"] == "0"


def test_order_frequency_limit_has_no_rejection_fees(data):
    bars = data.bars[:5]
    alternate = [b.model_copy(update={"symbol": "QQQ"}) for b in bars]
    fixture = data.model_copy(update={"bars": bars + alternate})
    profile = ProfileConfig(
        start_date=bars[0].session_date,
        end_date=bars[-1].session_date,
        symbols=["SPY", "QQQ"],
        max_orders_per_day=1,
    )
    result = simulate(default_strategy(), profile, fixture, benchmark=False, gross=False)
    assert any(o["rejection_reason"] == "daily order frequency limit" for o in result["orders"])
    assert all(Decimal(o["fees"]) == 0 for o in result["orders"] if o["status"] == "rejected")
    assert Decimal(result["metrics"]["total_commissions"]) == Decimal(
        result["metrics"]["executed_orders"]
    ) * Decimal("2.50")
