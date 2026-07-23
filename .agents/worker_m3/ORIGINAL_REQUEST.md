## 2026-07-23T00:00:00Z
You are teamwork_preview_worker assigned to Milestone 3 (R3 Integration into app.py & run_debug.py) of Factrix project extensions.

Working Directory: c:\Users\seeyo\code\Factrix\.agents\worker_m3

Task Objectives:
1. Integrate `AlphaBetaEngine` into `load_and_analyze_data` in `app.py`:
   - Import `AlphaBetaEngine` from `src.engine.alpha_beta`.
   - In `load_and_analyze_data`: Calculate `alpha_beta_res = AlphaBetaEngine.calculate(nav_df_dict=nav_df_dict, market_benchmark_df=benchmark_nav_dict.get('large_value'), fund_market_values=market_values)`.
   - Add `'alpha_beta_res'` to the returned `res_dict`.

2. Update Streamlit Web UI in `app.py`:
   - Integrate `AlphaBetaEngine` output and Milestone 2 Risk Exposure components into the Streamlit UI:
     - Render `create_risk_gauge_chart` and `render_risk_profile_card` in Tab 4 (or Tab 1/Tab 3).
     - Render `create_alpha_beta_scatter` and CAPM metric callouts (Alpha, Beta, Sharpe, Treynor, Information Ratio, Tracking Error) in Tab 3 (真实风格与 CAPM 绩效归因).
     - Render `render_rmb_loss_simulation` in Tab 4 (尾部防御与极值亏损模拟).
   - Ensure premium dark-mode styling, responsive layout, and 100% crash-proof fallback behavior when data is missing or empty.

3. Update CLI verification script `run_debug.py`:
   - Verify `run_debug.py` cleanly invokes `load_and_analyze_data` and inspects `alpha_beta_res`, `pbsa_res`, `rbsa_res`, `cvar_res`, `rebalance_res`, `health_res`.
   - Ensure running `uv run python run_debug.py` outputs all metrics cleanly with zero exceptions.

4. Update automated test suite in `tests/test_ui.py` & `tests/test_e2e_app.py`:
   - Update `test_app_load_and_analyze_data` and add tests ensuring `alpha_beta_res` is returned in `load_and_analyze_data` output with keys `portfolio_alpha`, `portfolio_beta`, `sharpe_ratio`, `scatter_data`.
   - Run `uv run pytest` and `uv run python run_debug.py` to confirm 100% passing tests and exception-free execution.
