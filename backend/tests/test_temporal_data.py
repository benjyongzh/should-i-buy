from datetime import date, timedelta

import pytest

from app.market_data.calendar import session_times, sessions
from app.market_data.providers import csv_records
from app.market_data.validation import validate_coverage, validate_dataset
from app.market_data.view import DataView, fx_at, require_mature_labels
from app.schemas.domain import ProfileConfig


def test_future_observation_blocked(data):
    now = session_times(date(2020, 6, 15))[1]
    view = DataView(data.bars, now)
    assert all(b.session_date <= date(2020, 6, 15) for b in view.history("SPY"))
    with pytest.raises(ValueError, match="future"):
        view.history("SPY", now + timedelta(days=30))


def test_fx_availability_and_no_future_fill(data):
    now = data.fx[0].observed_at
    with pytest.raises(ValueError, match="historically available"):
        fx_at(data.fx, now)
    assert fx_at(data.fx, data.fx[0].available_at) == data.fx[0].rate
    with pytest.raises(ValueError, match="stale"):
        fx_at(data.fx[:1], now + timedelta(days=20))


def test_unmatured_training_labels(data):
    with pytest.raises(ValueError, match="not matured"):
        require_mature_labels([data.fx[-1].available_at], data.fx[0].available_at)


def test_import_quality_and_calendar(data):
    assert not validate_dataset(data)["SPY"]["missing_sessions"]
    assert date(2020, 7, 3) not in sessions(date(2020, 7, 1), date(2020, 7, 6))
    assert session_times(date(2020, 11, 27))[1].hour == 18  # early close EST
    duplicate = data.model_copy(update={"bars": data.bars + [data.bars[0]]})
    with pytest.raises(ValueError, match="duplicate"):
        validate_dataset(duplicate)
    early = data.bars[0].model_copy(
        update={"available_at": data.bars[0].available_at - timedelta(hours=1)}
    )
    with pytest.raises(ValueError, match="precedes close"):
        validate_dataset(data.model_copy(update={"bars": [early]}))


def test_missing_session_rejected_no_future_replacement(data):
    broken = data.model_copy(update={"bars": data.bars[1:]})
    profile = ProfileConfig(
        start_date=data.bars[0].session_date, end_date=data.bars[-1].session_date
    )
    with pytest.raises(ValueError, match="missing 1 sessions"):
        validate_coverage(broken, profile)


def test_real_raw_data_requires_split_history_review(data):
    real = data.model_copy(update={"synthetic": False})
    profile = ProfileConfig(
        start_date=data.bars[0].session_date, end_date=data.bars[-1].session_date
    )
    with pytest.raises(ValueError, match="reviewed corporate-action"):
        validate_coverage(real, profile)
    reviewed = real.model_copy(update={"corporate_actions_reviewed": True})
    validate_coverage(reviewed, profile)


def test_bad_csv():
    with pytest.raises(ValueError, match="inconsistent"):
        csv_records("symbol,open\nSPY,1,2")
    with pytest.raises(ValueError, match="unique"):
        csv_records("symbol,symbol\nSPY,SPY")
