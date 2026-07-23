## 2026-07-23T07:47:13Z
You are teamwork_preview_worker assigned to fix defensive boundary guards in `app.py`.

Working Directory: c:\Users\seeyo\code\Factrix\.agents\worker_m3_fix

Task Objectives:
1. Fix potential `StopIteration`/`KeyError` in `app.py`:
   - Line 230: Safely handle `first_nav_dates`. If `nav_df_dict` is empty, generate fallback date range `pd.date_range(end=pd.Timestamp.now(), periods=180, freq='B').strftime('%Y-%m-%d')`.
   - Line 325-331: In `main()`, after calling `data = load_and_analyze_data(csv_input_path)`, check `if not data or 'df_funds' not in data: st.warning("⚠️ 无法解析持仓文件或数据为空"); st.stop()`.

2. Run `uv run pytest` and `uv run python run_debug.py` to confirm zero errors or regressions.
3. Write handoff.md in your working directory.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work.
