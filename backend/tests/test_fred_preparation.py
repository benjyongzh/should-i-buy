import json
from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
import pytest

from app.market_data.view import fx_at
from scripts import prepare_fred_fx
from scripts.prepare_fred_fx import PARAMS, archive_values, audit_clocks, get, normalize


def test_initial_release_is_unavailable_until_conservative_boundary_and_respects_dst():
    rows = [
        {"date": "2020-03-06", "realtime_start": "2020-03-09", "value": "1.3820"},
        {"date": "2020-03-05", "realtime_start": "2020-03-09", "value": "."},
    ]
    fx = normalize(rows)
    assert len(fx) == 1
    assert fx[0].observed_at.astimezone(UTC) == datetime(2020, 3, 6, 17, tzinfo=UTC)
    assert fx[0].available_at.astimezone(UTC) == datetime(2020, 3, 10, 4, tzinfo=UTC)
    with pytest.raises(ValueError, match="no historically available"):
        fx_at(fx, datetime(2020, 3, 10, 3, 59, tzinfo=UTC))
    assert fx_at(fx, datetime(2020, 3, 10, 4, tzinfo=UTC)) == Decimal("1.3820")


@pytest.mark.parametrize("value", ["NaN", "Infinity", "0", "-1"])
def test_invalid_source_rates_are_rejected(value):
    with pytest.raises(ValueError):
        normalize([{"date": "2019-01-02", "realtime_start": "2019-01-07", "value": value}])


def test_duplicate_and_reversed_release_dates_are_rejected():
    row = {"date": "2019-01-02", "realtime_start": "2019-01-07", "value": "1.3652"}
    with pytest.raises(ValueError, match="Duplicate"):
        normalize([row, row])
    with pytest.raises(ValueError, match="precedes"):
        normalize([{**row, "realtime_start": "2019-01-01"}])


def test_weekly_reference_rate_age_is_measured_from_observation_not_publication():
    fx = normalize([{"date": "2018-12-21", "realtime_start": "2018-12-26", "value": "1.3700"}])
    report = audit_clocks(fx, date(2019, 1, 2), date(2019, 1, 2))
    assert report["clocks"] == 3
    assert report["age_limit_failures"]["7"]["count"] == 3
    assert report["age_limit_failures"]["14"]["count"] == 0
    assert 12 < report["maximum_observation_age_days"] < 13


ARCHIVE = """Release Date: January 7, 2019
<table title="Foreign Exchange Rates -- H.10 Weekly"><tr>
<th>COUNTRY</th><th>CURRENCY</th><th>Dec. 31</th><th>Jan. 1</th>
<th>Jan. 2</th><th>Jan. 3</th><th>Jan. 4</th></tr><tr>
<th>SINGAPORE</th><td>DOLLAR</td><td>1.3623</td><td>ND</td>
<td>1.3652</td><td>1.3637</td><td>1.3594</td></tr></table>"""


def test_archive_reconciliation_handles_year_boundary_and_preserves_missing_values():
    values = archive_values(ARCHIVE, date(2019, 1, 7))
    assert values == {
        date(2018, 12, 31): "1.3623",
        date(2019, 1, 1): "ND",
        date(2019, 1, 2): "1.3652",
        date(2019, 1, 3): "1.3637",
        date(2019, 1, 4): "1.3594",
    }
    # Some historical Fed releases use the older statistics layout without a title.
    legacy = ARCHIVE.replace('title="Foreign Exchange Rates -- H.10 Weekly"', 'class="statistics"')
    assert archive_values(legacy, date(2019, 1, 7)) == values
    with pytest.raises(ValueError, match="release date mismatch"):
        archive_values(ARCHIVE, date(2019, 1, 8))
    with pytest.raises(ValueError, match="unexpected columns"):
        archive_values(ARCHIVE.replace("<th>Jan. 4</th>", ""), date(2019, 1, 7))


def test_provider_errors_never_include_credential_or_response_body():
    token = "private-fixture-key"
    transport = httpx.MockTransport(lambda _: httpx.Response(403, text=token))
    with httpx.Client(transport=transport) as client:
        with pytest.raises(ValueError) as error:
            get(client, "https://example.test/fred", {"api_key": token})
    assert token not in str(error.value)
    assert "403" in str(error.value)


def test_unavailable_archive_is_reported_and_completed_outputs_cannot_be_overwritten(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("FRED_API_KEY", "private-fixture-key")
    payload = {
        **PARAMS,
        "count": 1,
        "offset": 0,
        "observations": [{"date": "2017-12-01", "realtime_start": "2017-12-04", "value": "1.3450"}],
    }

    def source(client, url, params=None):
        if "stlouisfed.org" in url:
            return httpx.Response(200, json=payload)
        raise ValueError("Source HTTP 404; response/query suppressed")

    monkeypatch.setattr(prepare_fred_fx, "get", source)
    monkeypatch.setattr(prepare_fred_fx.time, "sleep", lambda _: None)
    output = tmp_path / "prepared"
    report = prepare_fred_fx.prepare(output)
    assert report["archive_unavailable"][0]["release"] == "2017-12-04"
    assert report["archive_matched_rows"] == 0
    assert "unresolved" in report["review_status"]
    assert report["coverage"][0]["age_limit_failures"]["14"]["count"] > 0
    assert (output / "usd-sgd-candidate.csv").exists()
    assert "private-fixture-key" not in (output / "report.json").read_text()
    assert json.loads((output / "raw/fred-page-0.json").read_text()) == payload
    with pytest.raises(ValueError, match="immutable"):
        prepare_fred_fx.prepare(output, resume=True)
