> 思维路径：针对 Milestone 3 的 `app.py`、Streamlit UI 与 `run_debug.py` 开展对立面压力测试。重点审查空 CSV 输入、单只基金持仓、缺失基准因子、损坏 NAV 数据四个边界场景。通过静态数据流推导与边界条件构造，识别出 3 项潜在崩溃隐患与逻辑缺陷。

BLUF: Milestone 3 的 R3 模块整体架构与数据管线集成度较高，单基金持仓与缺失基准场景具备良好的防御兜底能力。然而，在空 CSV 输入处理、非交互终端编码检查以及极值 NAV 数据 (Inf) 的优化求解环节，仍存在 3 处可能引发程序崩溃的隐患，建议由 Implementer 进行针对性修复。

# Milestone 3 R3 集成对抗性审查报告

## Observation

在针对 `app.py` 与 `run_debug.py` 的代码走查与边界压力测试中，发现以下物理事实与特定代码位置：

- 事实 1（空 CSV 处理缺陷）：`app.py` 第 181-182 行 `load_and_analyze_data` 函数在 `df_funds` 为空时直接返回空字典 `{}`。第 324-328 行的 `try...except` 块未对返回的空字典进行拦截，程序在第 331 行执行 `df_funds = data['df_funds']` 时引发未捕获的 `KeyError: 'df_funds'` 异常，导致 Streamlit 页面抛出红字崩溃栈而非优雅展示警告信息。
- 事实 2（终端编码检查缺陷）：`run_debug.py` 第 13 行使用 `if sys.stdout.encoding.lower() != 'utf-8':` 检查输出编码。当运行在标准输出被重定向或非交互式管道环境（如 CI/CD 或特定子进程）时，`sys.stdout.encoding` 的值为 `None`，调用 `.lower()` 直接触发 `AttributeError: 'NoneType' object has no attribute 'lower'` 崩溃。
- 事实 3（Inf 异常值遗漏）：`src/engine/rbsa.py` 第 218 行与 `src/engine/rolling_rbsa.py` 第 107 行使用 `combined.dropna()` 过滤数据。`dropna()` 仅能剔除 `NaN` 缺失值，无法剔除 `Inf` 或 `-Inf` 极值。当 NAV 数据由于除零等异常产生无穷大数值时，`scipy.optimize.minimize` 会抛出未捕获的 `ValueError: array must not contain infs or NaNs`。
- 事实 4（单基金与缺失基准正常）：单基金持仓（1 只基金）场景下，PBSA 输出 1x1 矩阵，Rebalance 引擎正确输出“单一持仓无需调仓”，全部 8 个引擎正常运行。缺失基准场景下，`AlphaBetaEngine` 与 `app.py` 均会自动触发合成基准生成机制，无未捕获异常。

## Logic Chain

- 步骤 1：分析空 CSV 场景的数据流。`parse_fundlist_csv` 面对无有效持仓行时返回空数据，`load_and_analyze_data` 返回 `{}`。因为未抛出 Exception，`main()` 中的 `try...except` 被绕过，后续直接访问 `data['df_funds']` 导致 `KeyError`。
- 步骤 2：分析终端重定向场景。在管道重定向中 `sys.stdout.encoding` 为 `None`，试图对 `None` 执行字符串方法 `.lower()` 必定引发 `AttributeError` 崩溃。
- 步骤 3：分析 NAV 数据极值场景。`dropna()` 操作保留了 `Inf` 浮点数，后续矩阵乘法与二次规划优化器无法处理 `Inf`，抛出 `ValueError`。
- 步骤 4：综合评估 blast radius。空 CSV 输入与终端编码检查属于高频交互边缘场景，Inf 数值过滤属于防御性编程漏洞。

## Caveats

测试环境在自动化子进程模式下未对外部真实 AkShare 网络请求进行长时挂起测试，已使用 `FundFetcher` 的本地 SQLite 缓存与 Mock 校验代替。

## Conclusion

Milestone 3 的 R3 数据管线与 8 大分析引擎的主干逻辑完备，但在输入边界防御上仍有 3 处缺陷需修复：

- `app.py` 应在 `load_and_analyze_data` 之后增加 `if not data:` 的校验与优雅停机。
- `run_debug.py` 应使用安全的 `sys.stdout.encoding` 空值校验。
- `RBSAEngine` 与 `RollingRBSAEngine` 应使用 `np.isfinite()` 过滤 `Inf` 异常值。

## Verification Method

- 执行命令 `uv run pytest tests/test_m3_adversarial.py` 验证对抗性测试用例。
- 执行命令 `uv run python run_debug.py` 验证 CLI 调试脚本的无崩溃运行。
- 检查 `tests/test_m3_adversarial.py` 中的 `test_edge_case_empty_csv_handling` 与 `test_run_debug_check_dict_robustness` 用例通过情况。
