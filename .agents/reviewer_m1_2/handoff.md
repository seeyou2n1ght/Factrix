> **思维路径**: 审查 Milestone 1 的 CAPM Attribution Engine (`src/engine/alpha_beta.py`) 与测试集 (`tests/test_alpha_beta.py`)。经 252 日年化标准数学公式核对与 `uv run pytest tests/test_alpha_beta.py` 自动化测试验证，引擎实现具备完整的 CAPM 指标计算框架，无硬编码或伪造代码等合规违规现象。由于测试套件中存在 2 项测试失败（1 项源于零方差基准被强制替换为随机噪声，1 项源于测试用例对 Sharpe 与 Treynor 比率相等的错误假设），本次审查结果判定为 REQUEST_CHANGES。

# Milestone 1 Review Handoff Report

## Observation
- 执行 `uv run pytest tests/test_alpha_beta.py` 获得结果为 2 failed, 8 passed in 1.33s。
- `tests/test_alpha_beta.py:86` 触发断言错误，期望 `sharpe_ratio == treynor_ratio`，实际输出 Sharpe 为 `-0.105873`，Treynor 为 `-0.020000`。
- `tests/test_alpha_beta.py:146` 触发断言错误，期望 `portfolio_alpha == 0.0`，实际输出 Alpha 为 `-0.019999999999999993`。
- `src/engine/alpha_beta.py:63` 在 `bm_var < 1e-12` 时强制调用 `_generate_synthetic_benchmark` 生成正态分布伪随机序列。
- `src/engine/alpha_beta.py` 严格基于 252 交易日标准完成了年化 Alpha、Beta、R^2、Sharpe、Treynor、Information Ratio 及 Tracking Error 数学计算。

## Logic Chain
- 组合年化 Alpha 公式 $(\bar{R}_p - R_f) - \beta(\bar{R}_m - R_f)$ 与标准差年化因子 $\sqrt{252}$ 在 `_compute_metrics_from_aligned_series` 中推导正确。
- Sharpe 比率分母使用收益率年化波动率（$\sigma_p \cdot \sqrt{252}$），Treynor 比率分母使用 Beta 系数（$\beta_p$），当序列年化波动率不等于 1.0 时两者在数学上不相等。
- 引擎在显式传入零方差基准数据时通过 `bm_var < 1e-12` 判定并插入高斯噪声，导致本应为 0 的 Alpha 计算出 `-0.02` 的无风险利率偏移量。
- 组合权重计算逻辑 `prepare_portfolio_returns` 采用持仓市值归一化加权，缺失市值时自动回退为等权重平均，逻辑严密符合业务设计。
- 模块不存在硬编码结果或欺骗性虚假实现，防守性类型校验与边界处理覆盖完备。

## Caveats
- 评估基于单线程测试环境，未开展万级基金高并发场景的性能压力测试。
- 伪随机合成基准使用了固定随机种子 42，存在极端情况下的数据重合风险。

## Conclusion
- 本次 Milestone 1 审查判定为 REQUEST_CHANGES。
- 需优化 `src/engine/alpha_beta.py:63` 逻辑，仅在基准数据缺失或对齐日期不足 3 日时触发合成基准生成，保留显式传入的合法零方差基准。
- 需修正 `tests/test_alpha_beta.py:86` 断言，移除 Sharpe 比率与 Treynor 比率数值相等的错误假设。

## Verification Method
- 执行终端命令 `uv run pytest tests/test_alpha_beta.py` 验证全量测试用例通过率。
- 执行终端命令 `uv run pytest tests/test_engine.py` 验证系统引擎集成测试用例通过率。
- 检查 `src/engine/alpha_beta.py` 零方差分支与 `tests/test_alpha_beta.py` 断言修复情况。

## Review Summary

**Verdict**: REQUEST_CHANGES

## Findings

### Major Finding 1: Excess Synthetic Benchmark Overwrite on Zero Variance
- What: 显式传入零方差基准时引擎强制替换为高斯噪声基准。
- Where: `src/engine/alpha_beta.py:63`
- Why: 破坏了输入数据的确定性，导致零收益组合计算出非零 Alpha。
- Suggestion: 修改合成基准触发条件，仅在基准缺失或有效对齐天数小于 3 时回退。

### Major Finding 2: Incorrect Financial Assertion in Test Suite
- What: 测试断言假设 Beta 为 1 时 Sharpe 比率等于 Treynor 比率。
- Where: `tests/test_alpha_beta.py:86`
- Why: Sharpe 比率基于总波动率，Treynor 比率基于系统性风险 Beta，概念与数值不同。
- Suggestion: 修正测试用例，调整为分别验证 Sharpe 比率与 Treynor 比率各自的期望公式值。
