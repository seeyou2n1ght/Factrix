## 2026-07-22T23:26:47Z

Implement `AlphaBetaEngine` in `src/engine/alpha_beta.py` and unit tests in `tests/test_alpha_beta.py`.

Please carefully read:
1. `c:\Users\seeyo\code\Factrix\PROJECT.md`
2. `c:\Users\seeyo\code\Factrix\.agents\explorer_m1_1\analysis.md`
3. `c:\Users\seeyo\code\Factrix\.agents\explorer_m1_2\analysis.md`
4. `c:\Users\seeyo\code\Factrix\.agents\explorer_m1_3\analysis.md`

REQUIREMENTS:
1. Create `src/engine/alpha_beta.py` with class `AlphaBetaEngine`:
   - `calculate_metrics(nav_df_dict: Dict[str, pd.DataFrame], market_benchmark_df: pd.DataFrame, fund_market_values: Dict[str, float], risk_free_rate: float = 0.02) -> Dict[str, Any]`
   - Calculate annualized Alpha, Beta, R^2, Sharpe ratio, Treynor ratio, Information ratio, Tracking error for each fund and for the overall weighted portfolio.
   - Prepare regression scatter plot dataset (points and trendline data) for Plotly visualization.
2. Defensive Programming:
   - Full Type Hints for all functions and methods.
   - Comprehensive docstrings (Chinese/English standard).
   - Defensive checks for empty DataFrames, date alignment (inner merge), zero variance/divide by zero prevention, negative beta edge cases.
3. Unit Tests:
   - Create `tests/test_alpha_beta.py`.
   - Run `uv run pytest tests/test_alpha_beta.py` and ensure 100% tests pass.
4. MANDATORY INTEGRITY WARNING:
   DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
5. Create `c:\Users\seeyo\code\Factrix\.agents\worker_m1_gen2\handoff.md` summarizing work done, test results, and status, and send a message back to parent.
