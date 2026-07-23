> 思维路径：基于对 Factrix 项目根目录、pyproject.toml、app.py、run_debug.py 以及 src/ 目录下所有模块与 tests/ 单元测试文件的静态代码研读与结构映射，全面分析数据管道、引擎计算逻辑、风格/风险归因架构及 UI 可视化集成点，导出供 Orchestrator 决策的架构分析报告。

**BLUF**：Factrix 是基于 Python 与 Streamlit 框架构建的个人公募基金持仓穿透与智能诊断系统，采用模块化分层架构（Data/Engine/UI），当前由 7 大分析引擎驱动，整体依赖 `uv` 与 `pyproject.toml` 进行管理。

# Factrix 代码库结构分析报告

## 项目结构与依赖配置

Factrix 项目采用标准 Python 包结构，代码主体位于 `src/` 目录，测试用例位于 `tests/` 目录。
环境依赖使用 `uv` 依赖管理器进行锁定，关键依赖包括 Streamlit (>=1.30.0)、Pandas (>=2.0.0)、NumPy (>=1.24.0)、SciPy (>=1.10.0)、AkShare (>=1.12.0) 及 Plotly (>=5.18.0)。
系统数据持久化由 SQLite 数据库文件 `fund_data.db` 承担，缓存基金历史净值、持仓明细、行业配置及基准指数数据。

- `app.py`: Streamlit Web 可视化看板入口文件，包含 5 大视图 Tab 与 `load_and_analyze_data` 主数据流水线。
- `run_debug.py`: CLI 命令行调试与数据校验入口，调用 `load_and_analyze_data` 并递归输出分析数据结构。
- `src/config.py`: 项目全局配置模块，定义 5 大基准指数、申万与证监会行业映射表、前景理论参数及赎回费率阶梯。
- `src/data/`: 数据解析与获取层，包含 CSV/Excel 解析器 (`csv_parser.py`)、AkShare 接口数据抓取器 (`fetcher.py`) 及 SQLite 本地缓存存储器 (`storage.py`)。
- `src/engine/`: 核心计算引擎层，包含 PBSA 穿透 (`pbsa.py`)、RBSA 风格回归 (`rbsa.py`)、Rolling RBSA 风格漂移 (`rolling_rbsa.py`)、CVaR 压力测试 (`cvar_stress.py`)、前景理论效用 (`prospect_theory.py`)、二次规划调仓 (`rebalance.py`)、健康度综合诊断 (`health_score.py`) 及 Markdown 报告生成 (`report.py`)。
- `src/ui/`: 前端渲染组件层，包含 Plotly 图表构建器 (`charts.py`) 与 Streamlit 自定义 CSS、卡片及白话导读组件 (`components.py`)。

## 数据加载与分析主流程

系统数据分析流以 `load_and_analyze_data` 函数为核心枢纽，负责完成从文件解析到 7 大引擎并发调用的完整闭环。
解析器 `parse_fundlist_csv` 自动识别 Excel 与 CSV 格式，读取 `基金代码`、`持有份额`、`资产情况` 等字段并执行代码补零与份额加总。
`FundFetcher` 优先读取 SQLite 数据库缓存，缓存失效时通过 AkShare API 异步补全 NAV 与持仓，若网络异常则自动触发防崩溃合成数据机制。
各引擎计算结果统一封装进字典结构 `res_dict`，并由 `ReportGeneratorEngine` 同步导出为 Markdown 报告 `Factrix_Report.md`。

- 入口函数：`load_and_analyze_data(csv_path: str) -> Dict[str, Any]` (位于 `app.py` 第 164 行)。
- 数据源解析：`parse_fundlist_csv(csv_path, aggregate=True)` (位于 `src/data/csv_parser.py` 第 19 行)。
- 缓存与 API 交互：`FundFetcher` 与 `SQLiteStorage` (位于 `src/data/fetcher.py` 第 24 行与 `src/data/storage.py` 第 15 行)。
- 7 大引擎依次执行：PBSA -> RBSA -> Rolling RBSA -> CVaR Stress -> Prospect Theory -> Rebalance -> Health Score。
- 调试入口：`run_debug.py` 调用 `load_and_analyze_data` 后使用 `check_dict` 递归输出 DataFrame 维度与缺失值统计。

## 引擎计算与风险归因逻辑

PBSA 引擎通过矩阵运算实现基金持仓向下穿透，计算 4 大宏观资产占比、5 大股票大类行业分布及基金间余弦相似度重合矩阵。
RBSA 引擎基于二次规划算法（SLSQP），将组合日收益率对 5 大基准风格指数进行约束回归，求解风格暴露权重与拟合优度 R^2。
Rolling RBSA 引擎采用 60 日滚动窗口追踪风格漂移轨迹，计算各因子时间序列方差并输出言行一致性预警信号。
CVaR 引擎基于 Cornish-Fisher 展式计算 95% 与 99% 置信度下的尾部期望亏损，并结合 RBSA 风格权重模拟 2015 股灾、2022 股债双杀等黑天鹅场景。
前景理论引擎基于 Kahneman-Tversky 价值函数计算前景效用值 V(r)、胜率、盈亏比及 Omega 比率；Rebalance 引擎利用带赎回费率摩擦的二次规划求解最优调仓买卖指令。

- `PBSAEngine.calculate`: 输入 `holdings_dict` 与 `fund_market_values`，输出 `stock_weights`、`sector_weights`、`macro_asset_weights` 及 `overlap_matrix` (位于 `src/engine/pbsa.py` 第 97 行)。
- `RBSAEngine.calculate`: 输入 `nav_df_dict` 与 `benchmark_nav_dict`，利用 `scipy.optimize.minimize` 求解权重 $w \ge 0, \sum w_i = 1$ (位于 `src/engine/rbsa.py` 第 190 行)。
- `RollingRBSAEngine.calculate`: 采用预对齐 NumPy 数组切片提高 60 日窗口求解效率，输出时间序列 `rolling_series` (位于 `src/engine/rolling_rbsa.py` 第 76 行)。
- `CVaRStressEngine.calculate`: 结合偏度与峰度修正分位数，输出 95%/99% CVaR 及场景损失金额 (位于 `src/engine/cvar_stress.py` 第 19 行)。
- `RebalanceEngine.calculate`: 结合 `get_redemption_fee_rate` 梯级费率（<7天 1.5%、<30天 0.75%），输出带避费小贴士的买卖建议 (位于 `src/engine/rebalance.py` 第 19 行)。

## AlphaBetaEngine 整合设计方案

为增强组合的 Alpha/Beta 风险收益归因能力，需新建 `AlphaBetaEngine` 模块。
该引擎将组合日收益率对市场大盘基准指数（如沪深300指数 `000300.SH`）进行单因子 CAPM 线性回归。
回归输出包括年化 Alpha 收益率、Beta 系数、Sharpe 比率、Treynor 比率、Information Ratio 及 Tracking Error。
计算结果将集成至 `load_and_analyze_data` 的 `res_dict` 中，并在 Tab 3（真实风格与言行一致）或 Tab 1（全景诊断结论）进行展示。

- 新建模块路径：`src/engine/alpha_beta.py`，类名 `AlphaBetaEngine`。
- 模块核心方法：`AlphaBetaEngine.calculate(nav_df_dict: Dict, market_benchmark_df: pd.DataFrame, fund_market_values: Dict) -> Dict[str, Any]`。
- 集成逻辑：在 `app.py` 的 `load_and_analyze_data` 中新增基准 `000300.SH` 的抓取与计算，并将 `alpha_beta_res` 传入 `HealthScoreEngine` 与 `ReportGeneratorEngine`。
- 图表增强：在 `src/ui/charts.py` 中新增 `create_alpha_beta_scatter`，绘制 CAPM 回归直线与散点分布图。

## 散户风险画像与可视化增强路径

散户投资者对复杂的金融工程指标缺乏直观感受，需要将定量指标转化为场景化、互动化的体验。
可通过引入散户风险偏好问卷与风险承受力画像，动态调整调仓阈值与风险预警线。
增强可视化包括增加极值亏损模拟器（如 10 万元持仓在暴跌下的直观金额损失柱状图）、赎回避费省钱对照图及组合 Beta 风险仪表盘。
白话小贴士组件 `VERNACULAR_EXPLANATIONS` 可进一步扩充 Alpha/Beta 与最大回撤的通俗化解释，降低散户理解门槛。

- 风险画像联动：增加用户风险偏好选择器（保守型/稳健型/积极型），动态调节 `HealthScoreEngine` 扣分权重与 `RebalanceEngine` 目标风险系数。
- 图表扩展：在 `src/ui/charts.py` 中增加 CAPM 特征线散点图、风险仪表盘（Gauge Chart）与赎回费率节省对比柱状图。
- UI 组件扩展：在 `src/ui/components.py` 的 `VERNACULAR_EXPLANATIONS` 中新增 Alpha/Beta、Sharpe 比率与最大回撤的白话小贴士。
