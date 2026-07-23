> 思维路径：针对 Milestone 1 审查意见，分析 src/engine/alpha_beta.py 中合成基准触发逻辑与零方差保护处理，以及 tests/test_alpha_beta.py 中的数学断言缺陷。通过修改合成基准回退条件、精细化异常捕获类型、调整零方差参数计算及更新测试套件断言，实现算法引擎逻辑规范化与测试用例 100% 匹配。

BLUF：已完成 `src/engine/alpha_beta.py` 与 `tests/test_alpha_beta.py` 的修复，合成基准仅在基准缺失或有效对齐天数小于 3 天时触发，零方差基准下正确返回 Beta=0.0、R2=0.0、Treynor=0.0，测试断言完全符合 CAPM 数学定义。

## Observation
- `src/engine/alpha_beta.py` 第 62 行原有逻辑在 `bm_var < 1e-12` 时强制覆写用户输入的基准数据为合成基准噪声，破坏了显示传入平坦基准数据的真实属性。
- `src/engine/alpha_beta.py` 第 190 行在 `_extract_benchmark_series` 中使用了宽泛的 `except Exception:` 捕获类型。
- `tests/test_alpha_beta.py` 第 86 行包含无效断言 `assert metrics["sharpe_ratio"] == metrics["treynor_ratio"]`，忽视了夏普比率与特雷诺比率分母物理含义的差异。
- `tests/test_alpha_beta.py` 第 146 行在零方差测试中错误预期 Alpha 为 0.0，未考虑无风险利率扣除后的真实超额收益率。

## Logic Chain
- 合成基准属于兜底降级方案，仅当用户未提供基准数据或对齐天数不足 3 天时方可触发；显式传入的零方差基准数据应保留原始序列，并将协方差相关指标设为 0.0。
- 将 `_extract_benchmark_series` 中的异常捕获限定为 `(ValueError, TypeError, AttributeError)`，可提升类型安全性并避免掩盖系统级异常。
- 夏普比率以总标准差为分母，特雷诺比率以 Beta 系数为分母，两者在数学上不相等，须基于各自的定义表达式分别校验。
- 在零收益与零方差基准下，组合超额收益率为负的无风险利率，按照 CAPM 模型 Alpha 应该等于 `-risk_free_rate`（即 -0.02），断言调整后完全符合确定性数学计算。

## Caveats
- No caveats.

## Conclusion
- `src/engine/alpha_beta.py` 的合成基准回退与零方差计算逻辑已修复，异常处理已完成精细化重构。
- `tests/test_alpha_beta.py` 中的测试断言已更新为符合独立数学公式的确定性检验。

## Verification Method
- 检查 `src/engine/alpha_beta.py` 中 `_extract_benchmark_series` 与 `calculate_metrics` 分支逻辑。
- 检查 `tests/test_alpha_beta.py` 中 `test_alpha_beta_engine_perfect_correlation` 与 `test_alpha_beta_engine_zero_variance` 的断言代码。
- 执行 `uv run pytest tests/test_alpha_beta.py` 验证 10 项测试通过。
- 执行 `uv run pytest tests/test_engine.py` 验证引擎集成测试通过。
