# Strategy DSL

## Engine 2.0.0 additions

Optional `execution_policy`, `universe` and `sizing_rules` preserve legacy hashes
when absent. New numeric variants are `market`, `calendar`, `portfolio`,
`corporate_action`, `event` and `arithmetic`. These work in nested conditions,
selection/ranking and sizing rules. The visual editor exposes them; the JSON
editor and server validation remain authoritative. `/api/strategy-definitions/requirements`
checks selected run inputs, and `/api/strategy-capabilities` reports configured
connections without credentials. The assistant uses `/api/llm/plan-strategy`,
retaining interpretation/assumptions/requirements/unsupported requests; blocked
plans cannot be accepted. Draft acceptance and publication remain separate.
See [complete semantics](strategy-capabilities.md).

The authoritative contracts are `backend/app/schemas/domain.py`, `GET /api/strategy-schema`, and generated OpenAPI. Unknown keys, indicators and operators are rejected; trees are bounded to 500 nodes and depth 20. No dynamic evaluation, import or Python execution exists.

```json
{
  "schema_version": 1,
  "entry": {"type":"compare","op":"crosses_above","left":{"type":"indicator","name":"sma","period":20,"field":"close"},"right":{"type":"indicator","name":"sma","period":50,"field":"close"}},
  "exit": {"type":"compare","op":"crosses_below","left":{"type":"indicator","name":"sma","period":20,"field":"close"},"right":{"type":"indicator","name":"sma","period":50,"field":"close"}},
  "sizing": {"mode":"equity_percent","value":"0.1"},
  "risk": {"max_allocation":"1","max_positions":5,"stop_loss":"0.03","take_profit":"0.06"}
}
```

Numeric expressions: `constant(value)`, `price(field)`, `indicator(name,period,field)`, `macd`, `stochastic`, `external`, and recursive `multiply(left,right)`. Price indicators refer to the current symbol and completed, available bars.

Engine 1.3.0 adds these operands without changing the serialized defaults or hashes of existing strategies:

```json
{"type":"macd","fast_period":12,"slow_period":26,"signal_period":9,"component":"histogram","field":"close"}
{"type":"stochastic","period":14,"smooth_k":3,"smooth_d":3,"component":"k"}
{"type":"external","series_id":"FEAR_GREED_US","max_age_days":7}
```

MACD fast/slow EMAs are independently SMA-seeded; the signal EMA is seeded from the first N MACD values. Components are `line`, `signal`, and `histogram` (line minus signal). Fast must be shorter than slow. Line needs slow-period bars; signal/histogram need slow + signal − 1. Slow stochastic calculates raw %K from trailing high/low and close, then applies `smooth_k` and `smooth_d` simple averages. A zero high/low range uses neutral 50. %K needs period + smooth_k − 1 bars; %D additionally needs smooth_d − 1. These are explicit application conventions; equivalence to every vendor's seed convention is not claimed.

An external operand requires an explicitly selected, reviewed snapshot at run scheduling. Its latest observation must have a known publication timestamp no later than the decision clock. Maximum age is 1–366 elapsed days measured from observation-date midnight in New York, not the retrieval date. Missing/stale values fail coverage validation; they are not substituted. Crossovers compare the current and previous trading-session decision clocks, including separately filtered price history. A late publication of an older observation does not replace a newer known observation. The interpreter receives only eligible current/prior scalar values. Source hashes and exact revision IDs are frozen in run provenance and the worker checks them again.

See [strategy inputs](strategy-inputs.md) for importing and reviewing sources. RSI, EMA200, price volume, average volume, MACD and stochastic can participate directly in entry/exit conditions; these are not restricted to charts.

Engine **1.4.0** additionally supports optional `trading` controls for daily,
weekly, monthly or once-only entry decisions, repeated additions and fractional
rule exits. Sizing adds `cash_percent` and `target_allocation`; both require an
explicit trading policy. Legacy absent/null policies are omitted from canonical
serialization so existing published hashes remain valid. See [the full timing,
sizing, funding and pooled-basis contract](funding-and-trade-controls.md).
Monthly salary contributions belong to the profile, not strategy JSON. The LLM
uses the same schema and remains subject to validation, proposal acceptance and
separate explicit publication.

Conditions: `compare(op,left,right)` with `gt/lt/gte/lte/eq/crosses_above/crosses_below`; recursive `all/any(conditions)`; `not(condition)`; `always(value)`. False or unknown means hold. An entry rule runs when flat; an exit rule runs when holding. Crossovers compare current and previous permissible observations; a persistent inequality is not another crossover.

Indicators: SMA and volume average use trailing N observations; EMA is SMA-seeded then recursively updated with 2/(N+1); RSI uses Wilder's averages with N+1 initial prices (flat=50, zero loss=100); momentum is `(current/price_N_observations_ago - 1)*100`; rolling high/low use trailing N highs/lows. Insufficient warm-up is unknown, including under logical NOT. Periods range from 2 to 500. Current completed candles are included; express a volume multiplier with `multiply`.

Sizing is a fraction of equity (0.1=10%) or a fixed notional in account currency. Quantity is computed at signal time using permissible close/FX and estimated costs; it is never sized with the next day's price. Whole shares round down, fractional orders use six decimal places. The execution engine independently rejects cash/exposure/position violations after opening gaps.

Published definitions cannot change. Draft edits use `expected_revision`; stale edits return 409. Cloning a strategy creates a new parent. Using an old version as a draft records its parent without rewriting historical versions. The UI supports all condition/indicator kinds and an advanced JSON view, both validated by the backend.

LLM authoring uses a configurable OpenAI-compatible strict structured-output request generated from the same strategy schema, including the new operands. A persisted proposal carries prompt/model metadata and source draft revision. Explicit acceptance changes a draft; separate publication makes it backtestable. Malformed/refused/truncated output is rejected. A generated external expression still requires a separately reviewed snapshot at scheduling. The implementation follows [official structured-output documentation](https://developers.openai.com/api/docs/guides/structured-outputs); dated live checks are recorded in `verification.md`.
