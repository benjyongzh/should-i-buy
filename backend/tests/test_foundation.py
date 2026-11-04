from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.config import settings
from app.db.session import make_engine


def test_migrations_clean_database(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    settings.cache_clear()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    engine = make_engine(url)
    assert {"candles", "backtest_runs", "strategy_versions", "llm_proposals"} <= set(
        inspect(engine).get_table_names()
    )
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine.dispose()
    settings.cache_clear()


def test_openapi_and_validation(client):
    assert client.get("/openapi.json").status_code == 200
    response = client.post(
        "/api/strategy-definitions/validate", json={"entry": {"type": "python", "code": "print(1)"}}
    )
    assert response.status_code == 422
    assert "loc" in response.json()["detail"][0]
