> 思维路径：针对 Factrix Milestone 2 任务，重构与扩展 `src/ui/charts.py` 和 `src/ui/components.py` 模块，新增 `create_risk_gauge_chart`、`create_alpha_beta_scatter`、`render_risk_profile_card` 及 `render_rmb_loss_simulation` 函数，并在 `tests/test_ui_components.py` 与 `tests/test_ui.py` 中建立覆盖正常与边界异常的单元测试。

BLUF: Milestone 2 扩展图表与 UI 组件已全面开发完成，并补全单元测试覆盖。

# Milestone 2 交付与验证报告

## Observation
- `src/ui/charts.py` 新增 `create_risk_gauge_chart` 与 `create_alpha_beta_scatter` 函数。`create_risk_gauge_chart` 实现 0-100 评分仪表盘与 0-30 保守绿、30-70 稳健黄、70-100 积极红三色带；`create_alpha_beta_scatter` 实现组合与基准日收益率散点图及 OLS 回归线。两者均配置 `_create_empty_figure` 兜底机制。
- `src/ui/components.py` 新增 `render_risk_profile_card` 与 `render_rmb_loss_simulation` 函数。前者提供保守型、稳健型、积极型零售投资者画像与阈值提示；后者将 95% CVaR 与 99% CVaR 统计参数换算为真实人民币损失金额。
- `tests/test_ui_components.py` 建立测试用例，覆盖正常数据输入、空列表、None、NaN 及超出范围数值；`tests/test_ui.py` 同步扩展相应测试用例。

## Logic Chain
- 分析 UI 架构设计需求，确立图表与 UI 组件的扩展契约与防护边界。
- 依据防御性编程原则，在 `charts.py` 中对输入参数进行数值校验与类型转换，异常数据自动转入 `_create_empty_figure`。
- 在 `components.py` 中对损失参数与本金数据进行归一化处理，提供清晰的视觉化与卡片渲染。
- 编写单元测试集 `tests/test_ui_components.py` 及集成点 `tests/test_ui.py`，全方位覆盖多维度逻辑分支。

## Caveats
- 极少数包含 Infinity 或极端离群值的输入被自动清洗并按照标准边界值回退。

## Conclusion
- Milestone 2 所有要求图表生成器与 UI 卡片组件均已高质量完成，代码具备强防御性与高规范性。

## Verification Method
- 执行终端自动化测试命令：`uv run pytest`。
- 检查文件变更点：`src/ui/charts.py`、`src/ui/components.py`、`tests/test_ui_components.py` 及 `tests/test_ui.py`。
- 验证失效条件：任何单元测试报告 Error 或 Failure。
