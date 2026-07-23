> 思维路径：基于对 Factrix 项目整体架构、数据处理流、7 大核心计算引擎、前端可视化及测试用例的深入代码研读，梳理出客观观察事实、推导逻辑链、存在局限性、最终结论与可复现的验证方法，形成供 Orchestrator 与 Implementer 使用的交接报告。

**BLUF**：探索工作已全面完成， Factrix 代码库具有高度模块化和防御性编程特征，交接文档包含了完整的文件路径、行号与接口约定，可无缝支持 AlphaBetaEngine 扩展与散户可视化增强。

# Factrix 代码库探索交接报告

## 观察事实

在项目根目录 `c:\Users\seeyo\code\Factrix` 中，静态检查确认了完整的包结构与模块划分。
文件 `pyproject.toml` 第 11-20 行定义了项目核心依赖为 streamlit、pandas、numpy、scipy、akshare、plotly、pytest 与 openpyxl。
数据主流程入口位于 `app.py` 第 164 行 `load_and_analyze_data` 函数，按序调用 CSV 解析、AkShare 数据获取与 SQLite 本地缓存 (`fund_data.db`)，并依次驱动 7 大计算引擎。
核心引擎位于 `src/engine/` 目录，包括 `pbsa.py` (第 97 行 `PBSAEngine.calculate`)、`rbsa.py` (第 190 行 `RBSAEngine.calculate`)、`rolling_rbsa.py` (第 76 行 `RollingRBSAEngine.calculate`)、`cvar_stress.py` (第 19 行 `CVaRStressEngine.calculate`)、`prospect_theory.py` (第 19 行 `ProspectTheoryEngine.calculate`)、`rebalance.py` (第 19 行 `RebalanceEngine.calculate`) 及 `health_score.py` (第 15 行 `HealthScoreEngine.calculate`)。
入口文件 `run_debug.py` 第 38 行直接调用 `load_and_analyze_data` 并使用 `check_dict` 函数输出分析数据结构的字段维度与空值统计。

- 配置文件与入口：`pyproject.toml` (第 1-49 行)、`app.py` (第 1-474 行)、`run_debug.py` (第 1-47 行)。
- 数据层模块：`src/data/csv_parser.py` (第 19 行)、`src/data/storage.py` (第 15 行)、`src/data/fetcher.py` (第 24 行)。
- 引擎层模块：`src/engine/pbsa.py`、`src/engine/rbsa.py`、`src/engine/rolling_rbsa.py`、`src/engine/cvar_stress.py`、`src/engine/prospect_theory.py`、`src/engine/rebalance.py`、`src/engine/health_score.py`、`src/engine/report.py`。
- UI 层模块：`src/ui/charts.py` (第 12-541 行)、`src/ui/components.py` (第 13-509 行)。
- 测试用例集：`tests/test_data_layer.py`、`tests/test_engine.py`、`tests/test_ui.py`、`tests/test_infra.py`、`tests/test_e2e_app.py`。

## 逻辑推理链

首先，通过检查 `pyproject.toml` 与 `uv.lock` 确认项目开发与运行环境依赖配置完整，支持通过 `uv run pytest` 执行完整的单元测试。
其次，分析 `load_and_analyze_data` 函数与 `run_debug.py` 的数据流动，得出所有分析引擎均输入标准化字典或 DataFrame 数据，并输出格式统一的字典结果。
再次，推演 `AlphaBetaEngine` 的扩展路径，确定其最佳接入点为 `src/engine/alpha_beta.py`，需在 `load_and_analyze_data` 中引入大盘基准数据（如 `000300.SH`）并参与 `HealthScoreEngine` 诊断。
最后，评估现有 UI 组件 `src/ui/charts.py` 与 `src/ui/components.py` 的可扩展性，确定散户风险画像问卷与直观风险仪表盘可无缝挂载至 Tab 1 与 Tab 3。

- 第一步：验证依赖与架构分布 -> 确认分层清晰，模块解耦良好。
- 第二步：分析数据流与调试入口 -> 确认 `run_debug.py` 可作为 CLI 验证新引擎输出的靶场。
- 第三步：推演 `AlphaBetaEngine` 设计 -> 确定输入接口 `(nav_df_dict, benchmark_nav, market_values)` 与输出数据规范。
- 第四步：推演 UI 散户化增强 -> 确定白话小贴士 `VERNACULAR_EXPLANATIONS` 与可视化图表的扩展点。

## 局限与假设

本次探索过程基于静态代码研读与模块分析，未直接对外部 API 接口进行网络调用。
假设现有 SQLite 缓存 `fund_data.db` 及降级合成数据逻辑在无网络环境下能够正常工作。
未针对大规模持仓组合（如超过 100 只基金）的矩阵运算性能瓶颈进行压力测试。

- 网络集成：假定 AkShare API 接口规范保持稳定，网络失效时自动触发合成降级数据。
- 持仓规模：假定个人公募基金持仓数量通常在 5 至 30 只之间，矩阵计算在毫秒级内完成。

## 结论

Factrix 架构具备高度的内聚性与防御性，代码质量良好，测试覆盖全面。
建议 Project Orchestrator 安排 Implementer 创建 `src/engine/alpha_beta.py` 模块，并在 `load_and_analyze_data` 与 `HealthScoreEngine` 中完成对接。
建议在 `src/ui/components.py` 中扩充散户风险画像偏好选择器，提升散户投资者的互动体验与风险直观感知。

- 架构评估：模块划分清晰，类型注解与防御性降级完善。
- 新增引擎方向：实现 `AlphaBetaEngine`，提供 Alpha、Beta、Sharpe、Treynor 及 Tracking Error 指标。
- UI 优化方向：增强散户风险偏好交互与极端亏损金额直观可视化。

## 验证方法

执行项目自动化测试套件以验证基础功能完整性。
运行命令行调试脚本验证数据流管线输出。
运行 Streamlit Web dashboard 查看各 Tab 视图渲染效果。

- 命令 1：`uv run pytest` (运行全部单元测试)
- 命令 2：`uv run python run_debug.py` (运行 CLI 调试流水线并检查字典字段)
- 命令 3：`uv run streamlit run app.py` (启动 Web 界面)
