from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.market_data.view import fx_at
from scripts.combined_source_review import declared_usd, dividend_from_evidence, weekly_fx


def notice(clock, amount="1.245568", identifier="original"):
    return {
        "id": identifier,
        "broadcast_at": clock,
        "text": f"SPDR S&P 500 ETF Trust (SPY) Distribution Announcement USD {amount}",
    }


def test_weekly_fx_does_not_use_anomalous_same_day_vintage_early():
    fx, changes = weekly_fx(
        [
            {"date": "2018-07-20", "realtime_start": "2018-07-23", "value": "1.3632"},
            {"date": "2018-07-23", "realtime_start": "2018-07-23", "value": "1.3653"},
            {"date": "2018-07-24", "realtime_start": "2018-07-31", "value": "."},
        ]
    )
    assert len(fx) == 2 and len(changes) == 1
    assert fx_at(fx, datetime(2018, 7, 30, 23, tzinfo=UTC), 14) == Decimal("1.3632")
    assert fx_at(fx, datetime(2018, 7, 31, 4, tzinfo=UTC), 14) == Decimal("1.3653")


def test_later_fx_vintage_is_never_brought_forward_across_dst():
    fx, changes = weekly_fx(
        [{"date": "2021-03-12", "realtime_start": "2021-03-22", "value": "1.3433"}]
    )
    assert not changes
    assert fx[0].available_at == datetime(2021, 3, 23, 4, tzinfo=UTC)
    with pytest.raises(ValueError, match="no historically available"):
        fx_at(fx, datetime(2021, 3, 23, 3, 59, tzinfo=UTC), 14)


def test_original_usd_rate_is_distinct_from_later_currency_conversion():
    assert declared_usd("SPDR S&P 500 ETF Trust (SPY) USD 1. 580000") == {Decimal("1.58")}
    assert declared_usd(notice("2020-01-01T00:00:00Z")["text"]) == {Decimal("1.245568")}
    assert (
        declared_usd(
            "SPDR S&P 500 ETF Trust SPY Distribution Foreign Exchange Rate Announcement USD 1.245568"
        )
        == set()
    )
    assert declared_usd("SPDR S&P 500 ETF Trust (SPY) US$1.580000") == {Decimal("1.58")}
    with pytest.raises(ValueError, match="does not identify"):
        declared_usd("Different ETF USD 1.245568")


def test_publication_uses_sydney_clock_and_end_of_minute_without_cdi_dates():
    action, evidence = dividend_from_evidence(
        date(2018, 6, 15),
        date(2018, 7, 31),
        Decimal("1.245568"),
        [
            notice("2018-06-15T09:33:00+10:00"),
            notice("2018-06-15T10:00:00+10:00", identifier="amended"),
            notice("2018-07-31T09:00:00+10:00", identifier="too-late"),
        ],
    )
    assert action.available_at == datetime(2018, 6, 15, 0, 1, tzinfo=UTC)
    assert action.session_date == date(2018, 6, 15)
    assert action.payment_date == date(2018, 7, 31)
    assert evidence == ["amended", "original"]


@pytest.mark.parametrize("clock", ["2018-06-15T10:00:00-04:00", "2018-06-15T09:33:00"])
def test_unavailable_or_naive_dividend_evidence_fails(clock):
    with pytest.raises(ValueError, match="No matching|timezone"):
        dividend_from_evidence(
            date(2018, 6, 15), date(2018, 7, 31), Decimal("1.245568"), [notice(clock)]
        )


def test_weekly_floor_does_not_hide_invalid_source_chronology():
    with pytest.raises(ValueError, match="release precedes observation"):
        weekly_fx([{"date": "2018-07-23", "realtime_start": "2018-07-20", "value": "1.3653"}])


def test_evidenced_later_weekly_release_delays_anomalous_vintage_further():
    fx, changes = weekly_fx(
        [{"date": "2018-07-23", "realtime_start": "2018-07-23", "value": "1.3653"}],
        {date(2018, 7, 23): date(2018, 7, 31)},
    )
    assert fx[0].available_at == datetime(2018, 8, 1, 4, tzinfo=UTC)
    assert changes[0]["conservative_release_floor"] == "2018-07-31"


def test_unrelated_older_distribution_with_same_amount_is_not_current_evidence():
    with pytest.raises(ValueError, match="No matching"):
        dividend_from_evidence(
            date(2018, 6, 15),
            date(2018, 7, 31),
            Decimal("1.245568"),
            [notice("2018-03-16T09:00:00+11:00")],
        )


def test_action_waits_for_later_payment_date_evidence():
    clock = datetime(2018, 6, 15, 0, 5, tzinfo=UTC)
    action, _ = dividend_from_evidence(
        date(2018, 6, 15),
        date(2018, 7, 31),
        Decimal("1.245568"),
        [notice("2018-06-15T09:33:00+10:00")],
        required_at=clock,
    )
    assert action.available_at == clock


@pytest.mark.parametrize(
    "clock", [datetime(2018, 6, 15, 14, tzinfo=UTC), datetime(2018, 6, 15, 0, 5)]
)
def test_late_or_naive_payment_date_evidence_is_rejected(clock):
    with pytest.raises(ValueError, match="unavailable before|requires timezone"):
        dividend_from_evidence(
            date(2018, 6, 15),
            date(2018, 7, 31),
            Decimal("1.245568"),
            [notice("2018-06-15T09:33:00+10:00")],
            required_at=clock,
        )
