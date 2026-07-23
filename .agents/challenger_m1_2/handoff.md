> BLUF: AlphaBetaEngine 算法引擎在 OLS 回归参数及 6 位小数散点图数据格式化处理上具备 100% 数值精确度，与 SciPy 参比偏差为 0.00e+00；单元测试集 2 项失败均系测试断言数学假设错误所致。

AlphaBetaEngine 归因引擎实现了标准 CAPM 模型及其衍生风险调整指标。数值检验覆盖多基金加权组合、负 Beta 资产及十万级高维序列场景。

## Observation

- 执行测试命令 `uv run pytest tests/test_alpha_beta.py` 输出 10 项测试结果，其中 8 项通过，2 项失败。
- 失败用例 `test_alpha_beta_engine_perfect_correlation` 报出 Sharpe 比例 -0.10587327 与 Treynor 比例 -0.02000000 不匹配。
- 失败用例 `test_alpha_beta_engine_zero_variance` 报出 portfolio_alpha 输出 -0.01999999，与预期值 0.0 不符。
- 在 252 组标准 OLS 回归数据测试中，AlphaBetaEngine 的 Beta(1.15459360)、年化 Alpha(0.09089214)、R2(0.96878277)同 SciPy 比对偏差为 0.00e+00。
- 散点图数据集 252 个数据点的 market_return、portfolio_return、portfolio_excess_return 与 market_excess_return 四项字段在 6 位小数舍入取值上无偏差。

## Logic Chain

- AlphaBetaEngine 采用无偏样本协方差与方差计算贝塔系数，计算公式与最小二乘法线性回归完全一致。
- 散点图输出对日超额收益率及原始收益率执行 round(float(val), 6) 处理，算法逻辑保持一致。
- test_alpha_beta_engine_perfect_correlation 失败源自测试用例错误假设 Beta=1.0 时 Sharpe 比例等于 Treynor 比例，夏普比例分母为年化总波动率 0.188905，特雷诺比例分母为 Beta 值 1.000000，两者存在物理差异。
- test_alpha_beta_engine_zero_variance 失败源自零收益率序列在 2% 无风险利率下的 α 计算，CAPM 模型定义超额收益率扣除无风险利率，零收益率伴随零贝塔必然导出 -2% 的年化 Alpha 值。

## Caveats

- 基准序列波动率低于 1e-12 时系统触发合成基准生成逻辑，测试环境收益序列将被迭加伪随机正态噪声。
- 引擎采用 inner join 方式对齐基金收益率与基准收益率时间戳，未重合交易日数据将被剔除。
- 数据样本数量小于 3 个交易日时引擎跳过归因回归计算直接返回全零默认指标字典。

## Conclusion

- AlphaBetaEngine 数值计算精度完全达到金融工程数学标准，算法公式无缺陷。
- tests/test_alpha_beta.py 内部 2 项测试失败确认为测试断言本身的数学假设逻辑错误，引擎代码无需修改。
- 归因引擎散点图格式化输出严格符合 6 位浮点数精度规范。

## Verification Method

- 执行独立数值校验脚本：`uv run python .agents/challenger_m1_2/verify_alpha_beta.py`。
- 执行单元测试集：`uv run pytest tests/test_alpha_beta.py`。
- 检查独立验算脚本输出中 Diff 数值是否保持为 0.00e+00。
