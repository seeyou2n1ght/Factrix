## 2026-07-23T07:37:08Z

You are teamwork_preview_worker assigned to Milestone 2 (R2 Enhanced Risk Factor Exposure Dashboard) of Factrix project extensions.

Working Directory: c:\Users\seeyo\code\Factrix\.agents\worker_m2

Task Objectives:
1. Extend `src/ui/charts.py`:
   - Implement `create_risk_gauge_chart(risk_score: float, risk_level: str = "中风险") -> go.Figure`:
     Returns an interactive Plotly indicator/gauge figure (using `go.Indicator` or custom arcs) displaying a 0-100 risk score, colored risk bands (0-30 conservative green, 30-70 balanced yellow, 70-100 aggressive red), risk level title/text, and premium dark/light theme styling consistent with `charts.py`. Handles empty or invalid inputs gracefully using `_create_empty_figure`.
   - Implement `create_alpha_beta_scatter(scatter_data: List[Dict[str, Any]], alpha: float = 0.0, beta: float = 1.0) -> go.Figure`:
     Returns a Plotly scatter plot figure displaying daily portfolio returns vs benchmark returns from `scatter_data` (list of dicts with keys 'market_return' and 'portfolio_return'), OLS regression line (y = beta * x + alpha / 252), alpha/beta annotation metrics, hover tooltips, and custom premium styling. Handles empty or invalid `scatter_data` gracefully using `_create_empty_figure`.

2. Extend `src/ui/components.py`:
   - Implement `render_risk_profile_card(risk_profile: str, cvar_95: float, max_drawdown: float = 0.0) -> None`:
     Renders plain-language retail investor risk profiling card (保守型 / 稳健型 / 积极型), detailing investor characteristics, loss tolerance thresholds, and vernacular advisory callouts.
   - Implement `render_rmb_loss_simulation(portfolio_value: float, cvar_95: float, cvar_99: float = 0.0) -> None`:
     Renders intuitive RMB loss simulation cards showing real RMB loss estimates (e.g. for ¥100,000 portfolio, estimated ¥X loss in 95% CVaR and ¥Y loss in 99% CVaR stress), converting academic statistical parameters into clear financial figures.

3. Create unit test suite in `tests/test_ui_components.py` and update `tests/test_ui.py`:
   - Add comprehensive tests for `create_risk_gauge_chart`, `create_alpha_beta_scatter`, `render_risk_profile_card`, and `render_rmb_loss_simulation`.
   - Test both normal inputs and edge cases (empty lists, negative values, NaN/None values).
   - Execute `uv run pytest` to verify all unit tests pass cleanly with 0 failures.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Provide complete implementation with full defensive type hints and standard docstrings. Run `uv run pytest` and report execution results in handoff.md in your working directory.
