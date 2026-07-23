> 思维路径：严格遵循 CAPM 线性回归与 252 交易日年化标准，实现了 AlphaBetaEngine 引擎模块及全量单元测试套件，提供高鲁棒性业绩归因计算与合成基准兜底能力。

**BLUF**: 完成 `src/engine/alpha_beta.py` 中 `AlphaBetaEngine` 类的开发，并在 `tests/test_alpha_beta.py` 中交付包含 10 个测试用例的单元测试套件。

# Alpha & Beta 业绩归因引擎交付报告

## Observation
- `src/engine/alpha_beta.py` 包含 `AlphaBetaEngine` 静态类，提供 `calculate_metrics` 与 `calculate` 接口。
- 引擎计算年化 Alpha、Beta、R^2、Sharpe、Treynor、Information Ratio、Tracking Error、单基金归因字典与散点图数据集。
- 零方差防御、数据对齐、短序列降级与合成基准 fallback 机制已全面实装。
- `tests/test_alpha_beta.py` 构建了 10 个测试场景，覆盖多基金组合、完美相关、已知线性拟合、零方差、负 Beta 与别名调用。

## Logic Chain
- 基于 `src/engine/rbsa.py` 的 `prepare_portfolio_returns` 提取组合日收益率序列，确保持仓市值加权逻辑一致。
- 组合收益率与基准指数收益率在日期维度交集对齐，采用样本协方差与方差向量化求解 CAPM 回归参数。
- 基准缺失、空数据或方差小于 1e-12 时，采用确定性种子 42 生成合成基准序列并标注 `is_synthetic_benchmark=True`。
- 遍历单只基金计算单体归因指标，生成适配 Plotly 渲染的 5 字段散点数据列表。

## Caveats
- 默认无风险利率设定为 0.02 年化值，支持通过 `risk_free_rate` 或 `rf_rate` 参数重置。
- 有效对齐交易日少于 3 天时自动触发全零防护字典输出。

## Conclusion
- `AlphaBetaEngine` 符合 `PROJECT.md` 接口契约，具备防御性编程能力与真实计算逻辑。

## Verification Method
- 单元测试命令：`uv run pytest tests/test_alpha_beta.py`
- 引擎集成测试命令：`uv run pytest tests/test_engine.py`
