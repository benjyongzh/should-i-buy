"""Catalog browsing must not load every licensed archive or bypass run hash checks."""

import json

import pytest
from platform_fixtures import event, event_source, platform_data
from sqlalchemy import event as sql_event

from app.api.strategy_inputs import summary
from app.services.strategy_inputs import checked_input, input_catalog, retain_input


def assert_catalog_projection(factory):
    data, intraday = platform_data()
    sources = [
        event_source(
            [
                event(
                    details={
                        "type": "news",
                        "article_id": "SYNTHETIC",
                        "version_available_at": "2020-01-02T15:30:00Z",
                        "text": "SYNTHETIC archive body " * 1000,
                    }
                )
            ]
        ),
        intraday,
    ]
    with factory() as db:
        rows = [retain_input(db, source) for source in sources]
        expected = {row.id: summary(row) for row in rows}
    captured = []
    engine = factory.kw["bind"]

    def capture(connection, cursor, statement, parameters, context, many):
        captured.append(statement)

    sql_event.listen(engine, "before_cursor_execute", capture)
    try:
        with factory() as db:
            actual = input_catalog(db)
            assert not db.identity_map, "catalog must not load full source ORM objects"
    finally:
        sql_event.remove(engine, "before_cursor_execute", capture)
    assert len(captured) == 1
    assert "array_length" in captured[0] and ("json_remove" in captured[0] or " - " in captured[0])
    by_id = {row["id"]: row for row in actual}
    for identifier, row in expected.items():
        assert by_id[identifier] == row
        assert not {"bars", "states", "events"} & by_id[identifier].keys()
        assert "SYNTHETIC archive body" not in json.dumps(by_id[identifier])


def test_catalog_uses_one_metadata_only_query_for_events_and_intraday(database):
    assert_catalog_projection(database)


def test_full_export_and_engine_boundary_still_reject_tampering(database):
    with database() as db:
        row = retain_input(db, event_source([event()]))
        row.payload = {
            **row.payload,
            "events": [{**row.payload["events"][0], "title": "SYNTHETIC tamper"}],
        }
        with pytest.raises(ValueError, match="hash mismatch"):
            checked_input(row)
