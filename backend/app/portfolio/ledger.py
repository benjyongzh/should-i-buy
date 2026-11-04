from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_DOWN, Decimal

from app.schemas.domain import ProfileConfig

D = Decimal


@dataclass
class Position:
    quantity: Decimal
    cost_basis: Decimal
    entry_price: Decimal
    opened_at: datetime
    opened_session: int


class Ledger:
    def __init__(self, profile: ProfileConfig):
        self.profile = profile
        self.cash = profile.starting_capital
        self.positions: dict[str, Position] = {}
        self.events: list[dict] = []
        self.trades: list[dict] = []
        self.fees = D(0)
        self.fx_costs = D(0)
        self.slippage_costs = D(0)
        self.realized_pnl = D(0)
        self.turnover = D(0)
        self.receivables: list[dict] = []

    def quantity(self, budget: Decimal, price: Decimal, fx: Decimal) -> Decimal:
        p = self.profile
        adverse = price * (1 + p.slippage + p.spread / 2)
        unit = (
            adverse
            * fx
            * (1 + (p.fx_markup if p.account_currency != "USD" else 0) + p.commission_pct)
        )
        affordable = max(D(0), budget - p.fixed_fee) / unit
        quantum = D("0.000001") if p.fractional_shares else D(1)
        return affordable.quantize(quantum, rounding=ROUND_DOWN)

    def execute(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        raw_price: Decimal,
        fx: Decimal,
        timestamp: datetime,
        session_index: int,
    ) -> dict:
        p = self.profile
        if quantity <= 0:
            raise ValueError("quantity rounds to zero")
        if side == "buy" and not p.fractional_shares and quantity != quantity.to_integral_value():
            raise ValueError("fractional order is disabled")
        if side == "buy" and symbol in self.positions:
            raise ValueError("duplicate position")
        if side == "sell" and (
            symbol not in self.positions or quantity != self.positions[symbol].quantity
        ):
            raise ValueError("sell requires the entire existing position")
        price = raw_price * (1 + (p.slippage + p.spread / 2) * (1 if side == "buy" else -1))
        notional = quantity * price * fx
        fee = p.fixed_fee + notional * p.commission_pct
        fx_cost = notional * p.fx_markup if p.account_currency != "USD" else D(0)
        cash_delta = -(notional + fee + fx_cost) if side == "buy" else notional - fee - fx_cost
        if self.cash + cash_delta < 0:
            raise ValueError("insufficient cash after commissions and conversion costs")
        if notional < p.min_notional:
            raise ValueError("below minimum order notional")
        if side == "buy":
            if len(self.positions) >= p.max_positions:
                raise ValueError("maximum concurrent positions")
            self.positions[symbol] = Position(
                quantity, -cash_delta, price, timestamp, session_index
            )
        else:
            position = self.positions.pop(symbol)
            pnl = cash_delta - position.cost_basis
            self.realized_pnl += pnl
            self.trades.append(
                {
                    "symbol": symbol,
                    "quantity": str(quantity),
                    "opened_at": position.opened_at.isoformat(),
                    "closed_at": timestamp.isoformat(),
                    "cost_basis": str(position.cost_basis),
                    "net_proceeds": str(cash_delta),
                    "realized_pnl": str(pnl),
                    "holding_sessions": session_index - position.opened_session,
                }
            )
        self.cash += cash_delta
        self.fees += fee
        self.fx_costs += fx_cost
        self.slippage_costs += abs(price - raw_price) * quantity * fx
        self.turnover += notional
        event = {
            "timestamp": timestamp.isoformat(),
            "kind": side,
            "symbol": symbol,
            "quantity": str(quantity),
            "price_usd": str(price),
            "fx_sgd_per_usd": str(fx),
            "notional": str(notional),
            "fees": str(fee),
            "fx_cost": str(fx_cost),
            "cash_delta": str(cash_delta),
            "cash_after": str(self.cash),
        }
        self.events.append(event)
        return event

    def split(self, symbol: str, ratio: Decimal, timestamp: datetime):
        if symbol in self.positions:
            position = self.positions[symbol]
            position.quantity *= ratio
            position.entry_price /= ratio
            self.events.append(
                {
                    "kind": "split",
                    "symbol": symbol,
                    "ratio": str(ratio),
                    "timestamp": timestamp.isoformat(),
                    "quantity": str(position.quantity),
                    "cost_basis": str(position.cost_basis),
                }
            )

    def dividend(self, symbol: str, amount: Decimal, payment_date, timestamp: datetime):
        if symbol in self.positions:
            amount_usd = self.positions[symbol].quantity * amount
            self.receivables.append(
                {"symbol": symbol, "amount_usd": amount_usd, "payment_date": payment_date}
            )
            self.events.append(
                {
                    "kind": "dividend_entitlement",
                    "symbol": symbol,
                    "timestamp": timestamp.isoformat(),
                    "amount_usd": str(amount_usd),
                    "payment_date": str(payment_date),
                }
            )

    def settle_dividends(self, day, fx: Decimal, timestamp: datetime):
        for receivable in list(self.receivables):
            if receivable["payment_date"] <= day:
                cash = receivable["amount_usd"] * fx
                self.cash += cash
                self.events.append(
                    {
                        "kind": "dividend_payment",
                        "symbol": receivable["symbol"],
                        "timestamp": timestamp.isoformat(),
                        "cash_delta": str(cash),
                        "cash_after": str(self.cash),
                    }
                )
                self.receivables.remove(receivable)

    def equity(self, prices: dict[str, Decimal], fx: Decimal) -> Decimal:
        return (
            self.cash
            + sum((r["amount_usd"] * fx for r in self.receivables), D(0))
            + sum((p.quantity * prices[s] * fx for s, p in self.positions.items()), D(0))
        )
