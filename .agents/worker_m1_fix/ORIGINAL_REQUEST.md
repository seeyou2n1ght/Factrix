## 2026-07-23T07:30:57Z
Fix zero-variance benchmark handling in `src/engine/alpha_beta.py` and test assertions in `tests/test_alpha_beta.py`.

Review Findings to Fix:
1. `src/engine/alpha_beta.py`:
   - Change synthetic benchmark fallback condition: synthetic benchmark (`_generate_synthetic_benchmark`) should ONLY be triggered if benchmark data is missing (None/empty) or aligned trading days < 3. If explicit valid benchmark data is passed but has zero variance (constant values), do NOT overwrite user benchmark data with synthetic noise; instead, safely set `beta = 0.0`, `r2 = 0.0`, `treynor_ratio = 0.0` (avoiding divide-by-zero).
   - Refine exception handling in `_extract_benchmark_series` to avoid blanket `except Exception:`.
2. `tests/test_alpha_beta.py`:
   - In `test_alpha_beta_engine_perfect_correlation`: Remove the invalid `assert metrics["sharpe_ratio"] == metrics["treynor_ratio"]` assertion. Instead, verify Sharpe ratio and Treynor ratio independently against their respective mathematical definitions.
   - In `test_alpha_beta_engine_zero_variance`: Adjust expected assertions to reflect deterministic calculations with zero-variance benchmark (Beta = 0.0, etc.).

Verification:
1. Run `uv run pytest tests/test_alpha_beta.py` -> All 10 tests MUST pass.
2. Run `uv run pytest tests/test_engine.py` -> All tests MUST pass.
