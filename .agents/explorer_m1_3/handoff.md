> **BLUF**: Explorer 3 完成了 Milestone 1 关于 Plotly CAPM Alpha/Beta 回归散点图 (`create_alpha_beta_scatter`) 的只读架构研读与策略设计，产出了完整规范的分析报告 `analysis.md`。

# Explorer 3 移交报告 (Handoff Report)

## Observation

在研读 `c:\Users\seeyo\code\Factrix\src\ui\charts.py`（第 1 行至 541 行）与 `src/ui/components.py`（第 1 行至 509 行）的过程中，确认了 Plotly 图表的全局模板与深色主题呈现规范。
查看 `c:\Users\seeyo\code\Factrix\PROJECT.md` 第 37 至 40 行，确认了 `create_alpha_beta_scatter` 的接口契约需求。
结合 `c:\Users\seeyo\code\Factrix\.agents\explorer_m1_1\analysis.md` 与 `explorer_m1_2\analysis.md` 的引擎算法产出，厘清了输入字典 `alpha_beta_res` 的结构定义。

- 目标源文件：`src/ui/charts.py`。
- 深色配色要求：背景 `#1E1E1E`，绘图区 `#262626`，辅助线 `#333333`，主调色 `#00D2FF`、`#00E676`、`#FF4B4B`。
- 输入数据契约：`scatter_data`、`portfolio_alpha`、`portfolio_beta`、`portfolio_r2`、`fund_metrics`。
- 交互功能：HTML 级 Hover 模板、CAPM 回归直线拟合、四象限文本标注与极值降级防护。
- 设计报告产出：`c:\Users\seeyo\code\Factrix\.agents\explorer_m1_3\analysis.md`。

## Logic Chain

基于 `src/ui/charts.py` 的现有构架，图表渲染需要兼顾美观性、一致性与数据防御能力。
第一步，从 `alpha_beta_res` 提取日收益率数据与 CAPM 参数，如果缺失则通过 `_create_empty_figure_dark` 输出暗黑空图提示。
第二步，利用日收益率数组对齐 `m_ret` 与 `p_ret`，绘制半透明电光蓝散点图层代表交易日样本对齐。
第三步，计算 CAPM 特征线端点 $Y = \alpha_{\text{daily}} + \beta \cdot X$，叠加斜率 Beta 与 R^2 拟合优度，线色根据 Alpha 正负切换为荧光绿或霓虹红。
第四步，配置 `paper_bgcolor='#1E1E1E'` 与 `plot_bgcolor='#262626'`，嵌入浮动指标卡与象限标注，完成图表生成。

- 步骤 1：解析输入字典，执行数据完整性校验与格式转换。
- 步骤 2：绘制 `m_ret` 对 `p_ret` 历史日收益率散点 Trace。
- 步骤 3：计算并叠加 CAPM 一元线性回归特征线 Trace。
- 步骤 4：注入深色主题 Layout 样式、零线辅助线及四象限标注。
- 步骤 5：封装函数并导出供 Implementer 模块集成。

## Caveats

只读探索阶段尚未对 `src/ui/charts.py` 进行物理代码修改，所有的代码与设计以方案形式呈现在 `analysis.md` 中。
假定 `AlphaBetaEngine` 提供的 `scatter_data` 中收益率为浮点数（小数值或百分数值），函数内已包含自动补全与量纲转换逻辑。
如果前端 Streamlit 页面后续切换为全浅色主题，需要额外调整 `theme="light"` 的参数分支。

- 尚未在 `src/ui/charts.py` 中写人代码（遵守 Read-only 限制）。
- 假定 `scatter_data` 数据点不少于 3 个，否则触发空图降级。
- 目前针对 Streamlit 暗黑主题进行了专项配色优化。

## Conclusion

`create_alpha_beta_scatter` 函数方案设计全面完成，完全契合 Factrix 架构契约与视觉规范。
方案包含完整 Python 源码实现、防崩溃边界处理及高级 Hover 交互，可由 Implementer 直接采纳并写入 `src/ui/charts.py`。

- 方案输出完备，逻辑自洽，无阻碍后续开发项。
- 支持单只基金与组合层面的双重归因可视化。
- 暗黑调色盘与 Factrix 前端保持强一致性。

## Verification Method

验证 `analysis.md` 中设计方案的有效性可按以下方式独立检验：
1. 检查 `c:\Users\seeyo\code\Factrix\.agents\explorer_m1_3\analysis.md` 是否存在并包含完整的代码块。
2. 在 Python 环境中导入 `plotly.graph_objects`、`pandas` 与 `numpy`，执行 `analysis.md` 拟议代码片段。
3. 传入构造的模拟数据字典验证图形生成结果与 Layout 字段取值是否为 `#1E1E1E` 和 `#262626`。

- 检验命令：`python -c "import plotly, pandas, numpy; print('Imports fine')"`。
- 文件查看：`analysis.md` 中的 `create_alpha_beta_scatter` 源码。
- 失效条件：`create_alpha_beta_scatter` 在空 DataFrame 输入时抛出 Uncaught Exception。
