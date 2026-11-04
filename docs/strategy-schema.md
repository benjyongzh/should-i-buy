# Strategy DSL

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

Numeric expressions: `constant(value)`, `price(field)`, `indicator(name,period,field)`, and recursive `multiply(left,right)`. They refer to the current symbol, never to another symbol's future data.

Conditions: `compare(op,left,right)` with `gt/lt/gte/lte/eq/crosses_above/crosses_below`; recursive `all/any(conditions)`; `not(condition)`; `always(value)`. False or unknown means hold. An entry rule runs when flat; an exit rule runs when holding. Crossovers compare current and previous permissible observations; a persistent inequality is not another crossover.

Indicators: SMA and volume average use trailing N observations; EMA is SMA-seeded then recursively updated with 2/(N+1); RSI uses Wilder's averages with N+1 initial prices (flat=50, zero loss=100); momentum is `(current/price_N_observations_ago - 1)*100`; rolling high/low use trailing N highs/lows. Insufficient warm-up is unknown, including under logical NOT. Periods range from 2 to 500. Current completed candles are included; express a volume multiplier with `multiply`.

Sizing is a fraction of equity (0.1=10%) or a fixed notional in account currency. Quantity is computed at signal time using permissible close/FX and estimated costs; it is never sized with the next day's price. Whole shares round down, fractional orders use six decimal places. The execution engine independently rejects cash/exposure/position violations after opening gaps.

Published definitions cannot change. Draft edits use `expected_revision`; stale edits return 409. Cloning a strategy creates a new parent. Using an old version as a draft records its parent without rewriting historical versions. The UI supports all condition/indicator kinds and an advanced JSON view, both validated by the backend.

LLM authoring uses a configurable OpenAI-compatible strict structured-output request. A server-persisted proposal carries prompt/model metadata and source draft revision. Explicit acceptance changes a draft; a separate publication makes it backtestable. Malformed/refused/truncated output is rejected. The implementation follows [official structured-output documentation](https://developers.openai.com/api/docs/guides/structured-outputs); no live LLM call was made during verification.
