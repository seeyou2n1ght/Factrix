# Project: Factrix Extensions

> **BLUF**: Factrix 项目扩展旨在交付 Alpha/Beta 绩效归因引擎 (`AlphaBetaEngine`)、散户通俗化风险暴露仪表盘，并无缝集成至 `app.py` 及 `run_debug.py`。

## Architecture
- **Data Layer (`src/data/`)**: CSV/Excel 解析、AkShare 接口数据抓取及 SQLite 本地缓存存储。
- **Engine Layer (`src/engine/`)**: 8 大核心分析引擎，包含 PBSA, RBSA, Rolling RBSA, CVaR Stress, Prospect Theory, Rebalance, Health Score, 及新增的 `AlphaBetaEngine` (`alpha_beta.py`)。
- **UI Layer (`src/ui/`)**: Streamlit 控件、暗色调高级 UI 样式、Plotly 图表及白话通俗化导读组件 (`components.py`, `charts.py`)。
- **Entry Points (`app.py`, `run_debug.py`)**: Web Dashboard 与 CLI 程序化调试与数据校验流。

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Alpha & Beta Engine (`AlphaBetaEngine`) | 实现 `src/engine/alpha_beta.py`，计算 CAPM Alpha, Beta, Sharpe, Treynor, Tracking Error, Information Ratio 及生成 Alpha/Beta 回归散点 Plotly 图表 | None | PLANNED |
| 2 | M2: Enhanced Risk Exposure Dashboard | 扩充 `src/ui/components.py` 与 `src/ui/charts.py`，提供散户通俗化风险画像（保守/稳健/积极）、极值亏损金额直观模拟与风险仪表盘 | M1 | PLANNED |
| 3 | M3: System Integration & Debug Test Script | 集成 `AlphaBetaEngine` 与 Risk Dashboard 到 `load_and_analyze_data` (app.py) 与 `run_debug.py`，更新测试套件 `tests/` | M1, M2 | PLANNED |

## Interface Contracts

### `AlphaBetaEngine` (`src/engine/alpha_beta.py`)
- **Input**:
  - `nav_df_dict: Dict[str, pd.DataFrame]` (基金代码 -> 净值 DataFrame)
  - `market_benchmark_df: pd.DataFrame` (基准大盘指数 DataFrame，例如 000300.SH 沪深300)
  - `fund_market_values: Dict[str, float]` (基金代码 -> 持仓市值)
- **Output**:
  - `Dict[str, Any]`：
    - `portfolio_alpha`: float (年化 Alpha 收益率)
    - `portfolio_beta`: float (组合 Beta 系数)
    - `portfolio_r2`: float (CAPM 回归 R^2)
    - `sharpe_ratio`: float (夏普比率)
    - `treynor_ratio`: float (特雷诺比率)
    - `information_ratio`: float (信息比率)
    - `tracking_error`: float (跟踪误差)
    - `fund_metrics`: Dict[str, Dict[str, float]] (单只基金 Alpha/Beta/Sharpe/R2)
    - `scatter_data`: List[Dict[str, Any]] (回归散点数据)

### `RiskProfile` & Visualization (`src/ui/components.py`, `src/ui/charts.py`)
- **Risk Profile Selection**: 散户风险偏好交互控件（保守型/稳健型/积极型）
- **Vernacular Explanations**: 通俗化风控解读卡片与风险级别评分
- **Plotly Visuals**: CAPM 散点回归图 `create_alpha_beta_scatter`、风险仪表盘 `create_risk_gauge_chart`

### `load_and_analyze_data` (`app.py`)
- 输入：`csv_path: str`
- 输出：`res_dict` 包含 `alpha_beta_res` 与 `risk_profile_res`

## Code Layout
- `src/engine/alpha_beta.py`: Alpha & Beta Performance Attribution engine
- `src/ui/components.py`: Streamlit UI components, risk profile selectors & vernacular guides
- `src/ui/charts.py`: Plotly charts including Alpha/Beta scatter plots & risk gauges
- `app.py`: Main Streamlit web application & `load_and_analyze_data` pipeline
- `run_debug.py`: Programmatic test & CLI verification script
- `tests/`: Automated test suite
