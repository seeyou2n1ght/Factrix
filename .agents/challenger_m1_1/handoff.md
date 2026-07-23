> 思维路径：通过编写针对 `AlphaBetaEngine` 的极端边界条件压测套件（`tests/test_alpha_beta_stress.py`），结合运行既有单元测试 `tests/test_alpha_beta.py`，从零方差基准、空数据、NaN/Inf 异常值、单数据点及非匹配日期等维度评估引擎健壮性与测试套件完备性。

> **BLUF**: `AlphaBetaEngine` 核心逻辑在极端输入（空 DataFrame、NaN/Inf 过滤、单/双数据点、非匹配日期合成基准）下具备防御性避险能力，但既有测试套件 `tests/test_alpha_beta.py` 中存在两处由断言逻辑缺陷引发的测试失败。

# 归因引擎 AlphaBetaEngine 实证压测报告

## Observation

- 执行命令 `uv run pytest tests/test_alpha_beta.py` 触发 2 项测试失败，返回码为 1。
- `tests/test_alpha_beta.py:86` 中 `test_alpha_beta_engine_perfect_correlation` 抛出 `AssertionError: assert -0.10587327484685297 == -0.0199999999999999`。
- `tests/test_alpha_beta.py:146` 中 `test_alpha_beta_engine_zero_variance` 抛出 `AssertionError: assert -0.019999999999999993 == 0.0`。
- 新增压测套件 `tests/test_alpha_beta_stress.py` 包含 13 个极端边界用例，全部通过（13 passed in 1.02s）。

## Logic Chain

- `test_alpha_beta_engine_perfect_correlation` 的失败原因在于断言假设 Sharpe Ratio 与 Treynor Ratio 在 Beta=1.0 时相等。Sharpe Ratio 分母为年化波动率（`std * sqrt(252)`），Treynor Ratio 分母为 Beta，二者量纲不同，仅在年化波动率恰好为 1.0 时数值一致。
- `test_alpha_beta_engine_zero_variance` 的失败原因在于基准方差为 0 时，`AlphaBetaEngine` 第 56 行触发合成基准生成逻辑，注入了正态随机噪声。噪声导致基准方差大于 1e-12，从而绕过零方差归零分支，基于无风险利率 0.02 计算出 CAPM Alpha 为 -0.02。
- `prepare_portfolio_returns` 在解析字典形式的基金数据时仅支持 `daily_return` 与 `nav` 列名，若传入 `close` 列名会被静默跳过，而 `_extract_benchmark_series` 则支持 `close` 列名。

## Caveats

- 未深入评估多资产非线性衍生品收益率序列下的极端高阶矩特征。
- 假定无风险利率参数输入符合标准年化浮点数规范。
- 尚未测试包含非标准字符编码的基准索引列名。

## Conclusion

- `AlphaBetaEngine` 实现具备对空值、非有限数值及日期错配的防御能力。
- 既有单元测试 `tests/test_alpha_beta.py` 需要修正断言逻辑以匹配数学定义与合成基准回退机制。
- 建议统一 `prepare_portfolio_returns` 与 `_extract_benchmark_series` 的列名兼容策略。

## Verification Method

- 运行既有测试命令：`uv run pytest tests/test_alpha_beta.py`
- 运行极端压测套件命令：`uv run pytest tests/test_alpha_beta_stress.py`
- 检查压测报告路径：`c:\Users\seeyo\code\Factrix\.agents\challenger_m1_1\handoff.md`
