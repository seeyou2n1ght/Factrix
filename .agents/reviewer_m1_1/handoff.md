> **BLUF**: 审查判定为 **REQUEST_CHANGES**。`tests/test_alpha_beta.py` 存在 2 项测试失败（`test_alpha_beta_engine_perfect_correlation` 与 `test_alpha_beta_engine_zero_variance`），源于测试公式假定错误及基准零方差平滑逻辑与测试期望不匹配。

# Milestone 1 Review & Criticism Report

## Observation
- 执行 `uv run pytest tests/test_alpha_beta.py` 触发 2 项失败：`test_alpha_beta_engine_perfect_correlation` 与 `test_alpha_beta_engine_zero_variance`。
- `test_alpha_beta_engine_perfect_correlation` 在 `tests/test_alpha_beta.py:86` 断言 `sharpe_ratio == treynor_ratio` 失败，实际输出 Sharpe 比率为 `-0.105873`，Treynor 比率为 `-0.020000`。
- `test_alpha_beta_engine_zero_variance` 在 `tests/test_alpha_beta.py:146` 断言 `portfolio_alpha == 0.0` 失败，实际输出 Alpha 为 `-0.019999999999999993`。
- 执行 `uv run pytest tests/test_engine.py` 结果为 17 passed in 1.44s。
- 接口契约校验显示 `src/engine/alpha_beta.py` 输出了 `PROJECT.md` 约定的全量字典字段。

## Logic Chain
- Sharpe 比率分母采用年化波动率（$\sigma_p \cdot \sqrt{252}$），Treynor 比率分母采用 Beta 系数（$\beta_p$）。输入序列 `np.linspace(-0.02, 0.02, 50)` 年化标准差为 `0.187`，导致两项指标数值必然不同。
- `AlphaBetaEngine.calculate_metrics` 在第 62 行检测到基准方差 `bm_var < 1e-12` 时强制生成合成噪声基准。合成基准引入随机波动后，以 `risk_free_rate = 0.02` 重新回归，使 0 收益组合计算出年化 Alpha `-0.02`。
- 代码防守性设计包含了空数据、长度不足 3 日、非有限值过滤与除零保护，类型注解与标准文档覆盖完整。

## Caveats
- 未对包含 1000 支以上基金的大规模持仓组合进行高并发性能压测。
- 未评估合成基准在极极端行情下的伪随机种子冲突概率。

## Conclusion
- 最终判定：**REQUEST_CHANGES**。
- 需由开发人员修复 `test_alpha_beta_engine_perfect_correlation` 中关于 Sharpe 与 Treynor 相等的错误假设断言。
- 需由开发人员优化 `AlphaBetaEngine._extract_benchmark_series` 与零方差处理分支，避免对显式传入的零方差基准进行强制伪随机替换。

## Verification Method
- 终端运行命令 `uv run pytest tests/test_alpha_beta.py`
- 终端运行命令 `uv run pytest tests/test_engine.py`
- 检查点：全量测试套件 100% 通过且无断言异常

## Review Findings

### Critical Finding 1: Test Suite Assertion Error in `test_alpha_beta.py`
- 位置：`tests/test_alpha_beta.py:86`
- 现象：`assert pytest.approx(res["sharpe_ratio"], abs=1e-5) == res["treynor_ratio"]` 抛出断言错误。
- 根因：Sharpe 比率计算公式为 $(R_p - R_f) / \sigma_{annual}$，Treynor 比率计算公式为 $(R_p - R_f) / \beta$。当序列年化波动率不等于 1.0 时，两者物理含义与数值逻辑均不相等。

### Major Finding 2: Zero-Variance Benchmark Fallback Contradiction
- 位置：`src/engine/alpha_beta.py:62` 及 `tests/test_alpha_beta.py:146`
- 现象：基准收益率全 0 时，`bm_var < 1e-12` 触发 `_generate_synthetic_benchmark` 插入高斯噪声，导致 Alpha 计算结果为 `-0.02` 而非 `0.0`。
- 根因：引擎在检测到用户基准零方差时覆盖原始数据，与真实基准零方差场景及测试预期发生冲突。

### Minor Finding 3: Generic Exception Handling in Benchmark Extraction
- 位置：`src/engine/alpha_beta.py:190`
- 现象：`except Exception:` 静默捕获了索引转换过程中的所有异常。
- 根因：未限定具体的 `KeyError` 或 `ValueError` 异常类型。
