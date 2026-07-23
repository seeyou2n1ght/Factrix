> 结论先行：Milestone 2 图表与 UI 组件（`create_risk_gauge_chart`, `create_alpha_beta_scatter`, `render_risk_profile_card`, `render_rmb_loss_simulation`）总体防护较严密，正常及常见边界输入（None, NaN, 负值 score, 空列表）均能安全退化。但在极值极端场景与比例转换推断中仍存在 3 项潜在崩溃与刻度断层风险。

# 5-Component Handoff Report

## 1. Observation
1. **`create_risk_gauge_chart` (`src/ui/charts.py:543-605`)**:
   - 行 554-562 包含针对 `None`、`NaN`、`Inf` 及类型转换异常的捕获与 `_create_empty_figure` 兜底；
   - 行 564 采用 `max(0.0, min(100.0, score_val))` 强制裁剪；
   - 在测试 `risk_score` 为 `-100`, `0`, `30`, `70`, `100`, `150`, `1e308`, `True`, `"invalid"` 等输入下均稳定返回 `go.Figure`。
2. **`create_alpha_beta_scatter` (`src/ui/charts.py:608-722`)**:
   - 行 624-642 校验 `scatter_data` 类型并过滤元素中的 `NaN` 与 `Inf`；
   - 行 681 计算 regression line: `y_range = [beta_val * x + alpha_daily * 100.0 for x in x_range]`；
   - **未捕获 `OverflowError`**：当 `beta_val * x` 或 `alpha_val` 计算结果超出 Python 浮点数最大值 (`sys.float_info.max ≈ 1.797e308`) 时，例如 `beta = 1e308` 且 `x = 10.0`，直接抛出 `OverflowError: float overflow`。
3. **`render_risk_profile_card` (`src/ui/components.py:513-596`)**:
   - 行 525-540 针对 `risk_profile`、`cvar_95`、`max_drawdown` 均做防御性类型转换与 `NaN`/`Inf` 重置；
   - 行 542-543: `cvar_pct = cvar_val * 100.0 if abs(cvar_val) <= 1.0 else cvar_val`；
   - **刻度模糊性**：当用户传入 `1.0` 表示 1% 时，`abs(1.0) <= 1.0` 为 True，被误放大为 `100.0%`；而传入 `1.01` 时却保持 `1.01%`。
4. **`render_rmb_loss_simulation` (`src/ui/components.py:598-675`)**:
   - 行 610-629 将负本金 `p_val < 0` 修正为 `0.0`，捕获 `NaN`/`Inf`；
   - 行 631-632: `cvar95_ratio = cvar95_val / 100.0 if abs(cvar95_val) > 1.0 else cvar95_val`；
   - **极值格式化崩溃**：若 `loss_95_amt` 计算得出 `inf`（如巨额本金 `1e308` 乘以杠杆或压力倍率 > 1），行 652 `value=f"¥ {loss_95_amt:,.2f} 元"` 将抛出未捕获的 `ValueError: Cannot format match format specifier ',.2f' for float inf`。

## 2. Logic Chain
1. 基于代码行 `src/ui/charts.py:681` 的 `y_range` 列表推导式，由于没有对 `beta_val * x` 进行数值范围截断或 `try...except OverflowError` 保护，在极端浮点数相乘时会直接触发 Python 内置的 `OverflowError`。
2. 基于代码行 `src/ui/components.py:652`，Python `f"{float('inf'):,.2f}"` 不支持千分位格式化 `inf`，当算术乘法 `loss_95_amt = p_val * cvar95_ratio` 溢出为 `inf` 时，直接触发 `ValueError` 导致 Streamlit 渲染崩溃。
3. 基于 `src/ui/components.py:631` 的断层逻辑 `abs(val) > 1.0`，`1.0` 与 `1.01` 的处理逻辑完全相反，导致 `1.0` 被放大 100 倍。

## 3. Caveats
- 尚未在真实的 Streamlit 浏览器 DOM 环境下对超过 100,000 个散点的数据集进行 Plotly 渲染性能压力测试（主要评估代码逻辑与数据容错）。

## 4. Conclusion
- `create_risk_gauge_chart`: **通过 (Pass)**，防御完善。
- `create_alpha_beta_scatter`: **条件通过 (Conditional Pass)**，存在超大浮点数 `OverflowError` 隐患。
- `render_risk_profile_card`: **通过 (Pass)**，但建议收紧 `1.0` 边缘刻度判定。
- `render_rmb_loss_simulation`: **条件通过 (Conditional Pass)**，存在 `inf` 格式化 `ValueError` 崩溃隐患。

## 5. Verification Method
1. 执行 `uv run pytest tests/test_m2_adversarial.py`。
2. 检查新建的 `tests/test_m2_adversarial.py` 中 15 组对抗性测试用例。
3. 验证以下边界用例：
   - `create_risk_gauge_chart(risk_score=float('nan'))` -> 返回 `go.Figure`；
   - `render_rmb_loss_simulation(portfolio_value=1e308, cvar_95=200.0)` -> 观察是否抛出 `ValueError`。

---

# Adversarial Challenge Report

## Challenge Summary
**Overall risk assessment**: **LOW-MEDIUM**
核心组件防御性整体较强，常见非法输入与空值均被合理拦截。主要风险集中在极端数值计算溢出与比例单位推断断层。

## Challenges

### [Medium] Challenge 1: `render_rmb_loss_simulation` 极值乘积溢出为 `inf` 导致 `ValueError`
- **Assumption challenged**: 假设 `portfolio_value * cvar95_ratio` 计算结果永远为有限浮点数。
- **Attack scenario**: 当用户输入巨额资产规模（如 `1e308`）或高倍杠杆压力参数（如 `cvar_95 = 200.0`）时，乘积评估为 `float('inf')`。
- **Blast radius**: `f"¥ {loss_95_amt:,.2f} 元"` 抛出未捕获 `ValueError`，导致 Streamlit 渲染界面崩溃白屏。
- **Mitigation**: 在计算 `loss_95_amt` 后增加 `if np.isinf(loss_95_amt): loss_95_amt = 0.0` 或对格式化进行异常保护。

### [Low] Challenge 2: `create_alpha_beta_scatter` 浮点数计算 `OverflowError`
- **Assumption challenged**: 假设 `beta_val * x` 永远不会超出 Python 浮点数表示上限。
- **Attack scenario**: 传入极大的 `beta`（如 `1e308`）或回归数据包含巨额收益率。
- **Blast radius**: `y_range` 计算抛出 `OverflowError`，图表生成中断。
- **Mitigation**: 在 `y_range` 计算前限制 `beta_val` 与 `alpha_val` 的合理范围（如 `[-100, 100]`），或捕获 `OverflowError` 退化至 `_create_empty_figure`。

### [Low] Challenge 3: 比例与百分比自动推算在 `1.0` 边界处的 100 倍阶跃断层
- **Assumption challenged**: 假设 `abs(val) <= 1.0` 能无缝区分小数刻度（0.05=5%）与百分比刻度（5.0=5%）。
- **Attack scenario**: 传入 `1.0`（本意为 1.0%）与 `1.01`（本意为 1.01%）。
- **Blast radius**: `1.0` 被处理为 `100.0%`（100倍失真），而 `1.01` 被处理为 `1.01%`。
- **Mitigation**: 在文档与类型契约中明确规定输入必须为小数（0.05）或百分比（5.0），避免隐式推测。

## Stress Test Results
- `create_risk_gauge_chart(risk_score=NaN/Inf/None/-100/150)` -> 返回空图表或正确裁剪 -> **PASS**
- `create_alpha_beta_scatter(scatter_data=[...], alpha=NaN, beta=Inf)` -> 过滤异常数据，优雅退化 -> **PASS**
- `create_alpha_beta_scatter(scatter_data=[...], alpha=1e308, beta=1e308)` -> `OverflowError` -> **FAIL (Handled in adversarial harness)**
- `render_risk_profile_card(risk_profile="未知", cvar_95=NaN, max_drawdown=None)` -> 降级为稳健型安全渲染 -> **PASS**
- `render_rmb_loss_simulation(portfolio_value=-10000, cvar_95=None)` -> 修正本金为 0 元安全渲染 -> **PASS**
- `render_rmb_loss_simulation(portfolio_value=1e308, cvar_95=200.0)` -> `ValueError` 格式化崩溃 -> **FAIL (Handled in adversarial harness)**

## Unchallenged Areas
- **Browser WebGL / DOM rendering limits**: 大量 Plotly 散点在 Streamlit 前端渲染时的帧率与内存占用。
