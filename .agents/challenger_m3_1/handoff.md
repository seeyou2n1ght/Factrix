> [思维路径] 对 Milestone 3 的 app.py、run_debug.py 以及 AlphaBetaEngine 集成进行代码审查与静态对抗测试，分析空 CSV 输入、缺失基准、单基金组合及 NAV 数据损坏等边界条件，定位 2 处潜在未捕获异常崩溃点并制定独立验证方案。

# Handoff Report — Milestone 3 Integration & Stress Testing

## 1. Observation

针对 Milestone 3 的系统集成与调试代码进行了全路径静态对账与对抗性逻辑推演，具体观测事实如下：

- 观测点 1 (`app.py` 第 331 行)：`main()` 函数中的 `df_funds = data['df_funds']` 语句位于 `try...except` 异常捕获块外部。当输入的 CSV 文件无有效持仓记录时，`load_and_analyze_data` 返回空字典 `{}`，引发未捕获的 `KeyError: 'df_funds'` 导致 Streamlit 界面直接崩溃。
- 观测点 2 (`app.py` 第 230 行)：`first_nav_dates = next(iter(nav_df_dict.values()))['date']` 强行假设 `nav_df_dict` 的首个 DataFrame 包含 `'date'` 列。若 NAV 数据结构缺失该列或字典为空，程序抛出 `KeyError: 'date'` 或 `StopIteration`。
- 观测点 3 (`run_debug.py` 第 43-73 行)：脚本成功集成了 `alpha_beta_res`、`pbsa_res`、`rbsa_res`、`cvar_res`、`rebalance_res` 及 `health_res` 6 大引擎输出校验，并输出了 Alpha、Beta、Sharpe、Treynor、IR 与 TE 核心 CAPM 指标。
- 观测点 4 (`src/engine/alpha_beta.py` 与 `src/engine/pbsa.py`)：单基金组合输入下，PBSA 引擎生成 1x1 对角重合矩阵，AlphaBetaEngine 正常计算单基金 Alpha/Beta 归因指标，未发生除零或矩阵奇异错误。
- 观测点 5 (`app.py` 第 71-101 行及第 232-240 行)：当基准大盘指数缺失或抓取失败时，`generate_fallback_benchmark` 与 `AlphaBetaEngine._generate_synthetic_benchmark` 自动生成合成基准数据，防崩溃降级机制生效。

## 2. Logic Chain

基于上述观测事实，推导结论如下：

- 步骤 1 (空 CSV 崩溃逻辑)：`parse_fundlist_csv` 遇到空文件返回空 DataFrame。`load_and_analyze_data` 触发 `if df_funds.empty:` 条件返回空字典 `{}`。由于 `main()` 中的字典提取逻辑位于 `try` 块之外且缺少 `if not data:` 判空校验，程序直接访问 `data['df_funds']` 引发未捕获异常。
- 步骤 2 (NAV 数据结构损坏逻辑)：当获取的基金净值 DataFrame 缺失 `'date'` 列但行数大于等于 5 时，流程绕过生成合成 NAV 的降级逻辑。后续在获取基准指数日期索引时，直接引用 `['date']` 列名抛出 `KeyError`。
- 步骤 3 (单基金与缺失基准稳健性逻辑)：单基金输入时，各引擎均包含单元素数组处理分支与正则化逻辑。基准数据缺失时，合成基准生成器以随机游走与组合收益率线性映射补齐时间序列，保障了后续线性回归与 CAPM 计算的闭环。

## 3. Caveats

本评估存在以下局限与未覆盖范围：

- 终端交互执行在当前环境下因权限等待超时未能直接运行命令，所有测试基于静态代码审查与推演。
- 未在真实 AkShare 网络高并发请求下测试 HTTP 429 速率限制与超时重试的极限性能。
- Plotly 图表在浏览器端的实际渲染帧率与内存占用不在本报告评估范围内。

## 4. Conclusion

Milestone 3 的 AlphaBetaEngine 与 Risk Dashboard 集成整体架构完备，单基金组合与缺失基准降级逻辑均符合预期。然而，`app.py` 在处理空 CSV 输入及损坏 NAV 列名时存在 2 处未捕获的 `KeyError` 异常，需在 `app.py` 中增加防御性判空与列名存在性校验以达到 100% 崩溃防护。

## 5. Verification Method

独立验证步骤如下：

- 执行命令 `uv run python run_debug.py`，检查控制台输出中 `alpha_beta_res` 及其他 5 大引擎指标是否正常打印。
- 执行命令 `uv run pytest`，确认自动化测试套件无失败项。
- 检查 `app.py` 第 230 行与第 331 行，验证是否增加 `if not data:` 校验及 safe `.get()` 降级保护。
