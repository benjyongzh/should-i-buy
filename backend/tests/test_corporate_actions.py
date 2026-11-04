from decimal import Decimal

from app.backtesting.engine import simulate
from app.market_data.calendar import session_times
from app.portfolio.ledger import Ledger
from app.schemas.domain import Action, ProfileConfig, default_strategy


def test_dividend_entitlement_is_not_spendable_before_payment(data):
    profile = ProfileConfig(fixed_fee="0", slippage="0")
    ledger = Ledger(profile)
    day0, day1, day2 = [b.session_date for b in data.bars[:3]]
    now = session_times(day0)[0]
    ledger.execute("SPY", "buy", Decimal(10), Decimal(100), Decimal(1), now, 0)
    ledger.dividend("SPY", Decimal(2), day2, session_times(day1)[0])
    assert ledger.cash == 9000
    assert ledger.equity({"SPY": Decimal(100)}, Decimal(1)) == 10020
    ledger.execute("SPY", "sell", Decimal(10), Decimal(100), Decimal(1), now, 1)
    ledger.settle_dividends(day1, Decimal(1), now)
    assert ledger.cash == 10000
    ledger.settle_dividends(day2, Decimal("1.4"), now)
    assert ledger.cash == 10028
    assert not ledger.receivables


def test_split_does_not_make_a_fake_loss_in_engine(data):
    bars = [
        b.model_copy(
            update={
                "open": Decimal(100),
                "high": Decimal(100),
                "low": Decimal(100),
                "close": Decimal(100),
            }
        )
        for b in data.bars[:5]
    ]
    split_day = bars[3].session_date
    bars[3:] = [
        b.model_copy(
            update={
                "open": Decimal(50),
                "high": Decimal(50),
                "low": Decimal(50),
                "close": Decimal(50),
            }
        )
        for b in bars[3:]
    ]
    action = Action(
        symbol="SPY",
        session_date=split_day,
        available_at=session_times(split_day)[0],
        kind="split",
        value=2,
    )
    fixture = data.model_copy(update={"bars": bars, "actions": [action]})
    profile = ProfileConfig(
        start_date=bars[0].session_date,
        end_date=bars[-1].session_date,
        account_currency="USD",
        fixed_fee="0",
        slippage="0",
    )
    result = simulate(default_strategy(), profile, fixture)
    assert all(Decimal(r["equity"]) == 10000 for r in result["equity"])
    assert result["positions"]["SPY"]["quantity"] == "20"
