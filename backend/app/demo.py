"""Run the required, explicitly synthetic 2019–2022 acceptance scenario via the HTTP API."""

import argparse
import json
from copy import deepcopy
from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

from app.backtesting.engine import ENGINE_VERSION, simulate
from app.db.session import SessionLocal, engine
from app.main import app
from app.market_data.demo import synthetic_demo
from app.schemas.domain import Compare, ProfileConfig, StrategyConfig, default_strategy
from app.services.jobs import process_one


def ma_config(fast: int, slow: int) -> StrategyConfig:
    config = default_strategy()
    config.entry = Compare(
        type="compare",
        op="crosses_above",
        left={"type": "indicator", "name": "sma", "period": fast},
        right={"type": "indicator", "name": "sma", "period": slow},
    )
    config.exit = config.entry.model_copy(update={"op": "crosses_below"})
    config.sizing.value = Decimal("0.95")
    return config


def run_demo(output: Path) -> dict:
    def request(client, method, path, body=None):
        response = client.request(method, "/api" + path, json=body)
        response.raise_for_status()
        return response.json()

    with TestClient(app) as client:
        dataset = request(client, "POST", "/market-data/demo")
        profile = request(
            client,
            "POST",
            "/backtest-profiles",
            {"name": "Standard SGD Portfolio", "config": ProfileConfig().model_dump(mode="json")},
        )
        hold = default_strategy()
        hold.sizing.value = Decimal("0.95")
        mean = default_strategy()
        mean.entry = Compare(
            type="compare",
            op="lt",
            left={"type": "indicator", "name": "rsi", "period": 14},
            right={"type": "constant", "value": 30},
        )
        mean.exit = Compare(
            type="compare",
            op="gt",
            left={"type": "indicator", "name": "rsi", "period": 14},
            right={"type": "constant", "value": 65},
        )
        mean.sizing.value = Decimal("0.95")
        configs = [
            ("Buy and hold SPY", hold),
            ("MA crossover 20/50", ma_config(20, 50)),
            ("RSI mean reversion", mean),
        ]
        versions, strategies = [], []
        for name, config in configs:
            strategy = request(
                client,
                "POST",
                "/strategies",
                {
                    "name": name,
                    "description": "Synthetic acceptance scenario — not an investment recommendation.",
                    "config": config.model_dump(mode="json"),
                },
            )
            version = request(
                client,
                "POST",
                f"/strategies/{strategy['id']}/publish",
                {"expected_revision": 1, "change_summary": "Initial synthetic scenario"},
            )
            strategies.append(strategy)
            versions.append(version)
        schedule = {
            "strategy_version_ids": [v["id"] for v in versions],
            "profile_id": profile["id"],
            "dataset_id": dataset["id"],
            "experiment_name": "SYNTHETIC · Required 2019–2022 scenario",
            "acknowledge_synthetic": True,
        }
        runs = request(client, "POST", "/backtests", schedule)
        for _ in runs:
            process_one(SessionLocal)
        results = [request(client, "GET", f"/backtests/{r['id']}/results") for r in runs]
        original = deepcopy(results[1])
        strategy = strategies[1]
        edited = ma_config(10, 30)
        request(
            client,
            "PATCH",
            f"/strategies/{strategy['id']}",
            {
                "name": strategy["name"],
                "description": strategy["description"],
                "config": edited.model_dump(mode="json"),
                "expected_revision": 1,
            },
        )
        revised_version = request(
            client,
            "POST",
            f"/strategies/{strategy['id']}/publish",
            {
                "expected_revision": 2,
                "change_summary": "Compare 10/30 periods with immutable 20/50 baseline",
            },
        )
        revised_run = request(
            client,
            "POST",
            "/backtests",
            {
                **schedule,
                "strategy_version_ids": [revised_version["id"]],
                "experiment_name": "SYNTHETIC · Revised MA version",
            },
        )[0]
        process_one(SessionLocal)
        revised_result = request(client, "GET", f"/backtests/{revised_run['id']}/results")
        assert request(client, "GET", f"/backtests/{runs[1]['id']}/results") == original
        changed_profile = {**profile["config"], "fixed_fee": "5.00"}
        request(
            client,
            "PATCH",
            f"/backtest-profiles/{profile['id']}",
            {"name": profile["name"], "config": changed_profile},
        )
        assert request(client, "GET", f"/backtests/{runs[1]['id']}/results") == original
        assert (
            request(client, "GET", f"/backtests/{runs[1]['id']}")["profile_snapshot"]["fixed_fee"]
            == "2.50"
        )
        # Restore the user's useful demo profile, leaving completed snapshots untouched.
        request(
            client,
            "PATCH",
            f"/backtest-profiles/{profile['id']}",
            {"name": profile["name"], "config": profile["config"]},
        )

    data = synthetic_demo()
    cutoff = date(2020, 6, 30)
    mutated = data.model_copy(
        update={
            "bars": [
                b.model_copy(
                    update={
                        "open": b.open * 7,
                        "high": b.high * 7,
                        "low": b.low * 7,
                        "close": b.close * 7,
                        "volume": b.volume * 3,
                    }
                )
                if b.session_date > cutoff
                else b
                for b in data.bars
            ],
            "fx": [
                f.model_copy(update={"rate": f.rate * 2}) if f.observed_at.date() > cutoff else f
                for f in data.fx
            ],
        }
    )
    before = simulate(configs[1][1], ProfileConfig(), data, benchmark=False, gross=False)
    after = simulate(configs[1][1], ProfileConfig(), mutated, benchmark=False, gross=False)

    def early(result: dict, key: str, timestamp: str) -> list:
        return [
            row
            for row in result[key]
            if row[timestamp] is not None and row[timestamp][:10] <= str(cutoff)
        ]

    assert early(before, "signals", "timestamp") == early(after, "signals", "timestamp")
    assert early(before, "orders", "executed_at") == early(after, "orders", "executed_at")
    assert early(before, "equity", "date") == early(after, "equity", "date")
    report = {
        "engine_version": ENGINE_VERSION,
        "database_backend": engine.dialect.name,
        "synthetic": True,
        "real_data_scenario": "UNVERIFIED — no source credentials or real USD/SGD files provided",
        "dataset_hash": dataset["content_hash"],
        "experiment_id": runs[0]["experiment_id"],
        "runs": [
            {"name": name, "id": run["id"], "metrics": result["metrics"]}
            for (name, _), run, result in zip(
                configs + [("MA crossover 10/30 (v2)", edited)],
                runs + [revised_run],
                results + [revised_result],
                strict=True,
            )
        ],
        "assertions": {
            "original_version_results_unchanged": True,
            "profile_edit_did_not_change_results": True,
            "future_price_and_fx_mutation_invariance": True,
            "cutoff": str(cutoff),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Synthetic acceptance demonstration",
        "",
        f"Verified with engine {ENGINE_VERSION} on {engine.dialect.name}.",
        "",
        "This is deterministic SYNTHETIC data, not actual SPY or FX performance. The real-data scenario remains unverified because no provider credentials or real FX source files were supplied.",
        "",
        "Profile: SGD 10,000; SGD 2.50 per executed order; 0.05% slippage; 2019–2022; long-only, 1x leverage. 2018 observations provide warm-up.",
        "",
        "| Strategy | Final SGD | Net return | Max drawdown | Sharpe | Orders | Fees SGD |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["runs"]:
        m = row["metrics"]
        lines.append(
            f"| {row['name']} | {Decimal(m['ending_equity']):.2f} | {m['total_return']:.2%} | {m['max_drawdown']:.2%} | {m['sharpe_ratio']:.3f} | {m['executed_orders']} | {Decimal(m['total_commissions']):.2f} |"
        )
    lines += [
        "",
        "Verified through the API and worker: create/import/publish/schedule/persist/retrieve; original results unchanged after publishing revised periods and editing profile fees; all earlier signals, eligible fills, and equity unchanged after replacing later prices, volume, and FX after 2020-06-30.",
        "",
        f"Dataset content hash: `{dataset['content_hash']}`.",
        "",
        "Use `python -m app.demo` from backend to reproduce. View equity curves, individual orders, signal rules, fees and open positions in the web UI. This script creates explicitly labeled demo resources in the configured database.",
    ]
    (Path(__file__).resolve().parents[2] / "docs" / "demo-report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"output": str(output), "runs": len(report["runs"]), "assertions": report["assertions"]}
        )
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("../.local/demo-report.json"))
    run_demo(parser.parse_args().output)
