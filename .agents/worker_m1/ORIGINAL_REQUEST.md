## 2026-07-22T16:33:58Z
You are Worker subagent for Milestone 1 (R1 Alpha & Beta Attribution Engine).
Your working directory is: c:\Users\seeyo\code\Factrix\.agents\worker_m1

Scope Document: c:\Users\seeyo\code\Factrix\PROJECT.md
Explorer Reports:
- Math & Metrics: c:\Users\seeyo\code\Factrix\.agents\explorer_m1_1\analysis.md
- Engine Design: c:\Users\seeyo\code\Factrix\.agents\explorer_m1_2\analysis.md
- Chart Design: c:\Users\seeyo\code\Factrix\.agents\explorer_m1_3\analysis.md

## MANDATORY INTEGRITY WARNING
> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Code & Quality Principles
- Think before coding. Defensive programming with Type Hints, standard docstrings, boundary checks, and error handling.
- Primary interaction/comment language: Chinese (technical terms in English).
- Use `uv` environment manager (`uv run python ...`, `uv run pytest`).

## Tasks
1. Implement `src/engine/alpha_beta.py`:
   - Class `AlphaBetaEngine` with static method:
     `calculate(nav_df_dict: Dict[str, pd.DataFrame], market_benchmark_df: Optional[pd.DataFrame], fund_market_values: Dict[str, float], rf_rate: float = 0.015, annualization_factor: float = 252.0) -> Dict[str, Any]`
   - Calculate portfolio annualized Alpha, Beta, R^2, Sharpe Ratio, Treynor Ratio, Information Ratio, Tracking Error.
   - Calculate per-fund Alpha, Beta, R^2, Sharpe Ratio in `fund_metrics`.
   - Output `scatter_data` list of dicts for regression scatter plot.
   - Implement synthetic benchmark fallback when benchmark NAV is missing/empty/zero-variance/short (<10 days), setting `is_synthetic_benchmark: True`.
   - Comprehensive type hints, standard docstrings, zero-variance / divide-by-zero checks.
2. Implement `create_alpha_beta_scatter` in `src/ui/charts.py`:
   - Signature: `create_alpha_beta_scatter(alpha_beta_res: Optional[Dict[str, Any]] = None, scatter_df: Optional[pd.DataFrame] = None, theme: str = "dark") -> go.Figure`
   - Dark mode styling (`#1E1E1E`, `#262626`, `#00D2FF`, `#00E676`, `#FF4B4B`).
   - Four quadrant annotations ("逆势抗跌", "顺势进攻", "同步回撤", "逆势滞涨").
   - Defensive fallback for empty/invalid inputs (`_create_empty_figure_dark`).
3. Update `tests/test_engine.py`:
   - Add unit tests for `AlphaBetaEngine`: `test_alpha_beta_engine_normal`, `test_alpha_beta_engine_perfect_correlation`, `test_alpha_beta_engine_synthetic_fallback`, `test_alpha_beta_engine_zero_variance`, `test_alpha_beta_engine_empty_input`.
4. Run `uv run pytest` to verify all tests pass.
5. Create `progress.md` and `handoff.md` in `c:\Users\seeyo\code\Factrix\.agents\worker_m1\`.
6. Send message to parent with build/test results when complete.
