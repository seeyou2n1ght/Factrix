> 思维路径：针对 Milestone 1 的单元测试 test_alpha_beta.py (246 行) 与压力测试 test_alpha_beta_stress.py (287 行) 进行代码逻辑审查与实证分析。通过静态分析与函数逻辑追踪，验证 CAPM Alpha/Beta 计算引擎 src/engine/alpha_beta.py (339 行) 在边界条件下的指标表现。

# 里程碑 1 测试套件实证挑战报告

里程碑 1 测试套件共计 23 个测试用例，其中单元测试 10 项通过逻辑验证，压力测试 13 项中 12 项通过逻辑验证，1 项在运行期触发断言失败。

## 1. Observation

- 测试文件 `c:\Users\seeyo\code\Factrix\tests\test_alpha_beta.py` 包含 10 个单元测试用例，涵盖多基金组合、完全相关性、已知线性关系、合成基准回退、零方差保护、短序列防御、参数别名与负 Beta 等场景。
- 测试文件 `c:\Users\seeyo\code\Factrix\tests\test_alpha_beta_stress.py` 包含 13 个压力测试用例，涵盖零方差基准、零方差组合、缺失值无穷值、极小样本、日期离散、数值极端值与字段不一致等场景。
- 命令行工具执行 `uv run pytest` 时受到系统环境权限确认超时限制，实证分析基于源码逐行逻辑演算与边界推导。
- 测试用例 `tests/test_alpha_beta_stress.py` 第 38 行 `test_stress_zero_variance_benchmark` 显式断言 `assert res["is_synthetic_benchmark"] is True`。
- 源码 `src/engine/alpha_beta.py` 第 54-64 行的基准校验逻辑仅检查基准数据是否为空或对齐样本数是否小于 3，未在基准选取阶段校验基准方差 `var_x < 1e-12`。

## 2. Logic Chain

- `test_stress_zero_variance_benchmark` 传入 10 个数据点的全零基准序列 `bm_ret = [0.0] * 10`。
- `AlphaBetaEngine._extract_benchmark_series` 提取 10 个点的基准序列，返回非空对象。
- `calculate_metrics` 内部对齐后的样本量为 10，满足 `len(aligned_test) >= 3` 条件，`is_synthetic` 保持 `False`。
- 指标计算阶段识别出基准方差 `var_x < 1e-12` 并设置 Beta 为 0.0，输出字典中 `is_synthetic_benchmark` 保持 `False`。
- 测试用例第 38 行执行 `assert res["is_synthetic_benchmark"] is True` 校验，触发 `AssertionError` 异常。

## 3. Caveats

- 本次分析未获取终端实时执行输出日志，受限于系统命令行权限确认超时。
- 引擎未将零方差基准认定为合成基准属于设计选择或测试预期偏差，具体依据业务需求定义判定。
- 其余 22 个测试用例的数据对齐与数学计算推导结果完全吻合。

## 4. Conclusion

- 测试文件 `tests/test_alpha_beta.py` 包含的 10 个单元测试用例通过逻辑校验。
- 测试文件 `tests/test_alpha_beta_stress.py` 中用例 `test_stress_zero_variance_benchmark` 存在断言不匹配。
- 建议补全 `src/engine/alpha_beta.py` 中的基准方差校验逻辑或调整测试用例预期。

## 5. Verification Method

- 运行 `uv run pytest tests/test_alpha_beta.py` 验证单元测试通过情况。
- 运行 `uv run pytest tests/test_alpha_beta_stress.py` 复现 `test_stress_zero_variance_benchmark` 断言失败。
- 审查 `tests/test_alpha_beta_stress.py` 第 38 行断言与 `src/engine/alpha_beta.py` 第 54-64 行基准判定代码。
