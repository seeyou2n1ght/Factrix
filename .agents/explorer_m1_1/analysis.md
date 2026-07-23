> **BLUF**: AlphaBetaEngine 采用 CAPM 线性回归模型与 252 交易日年化标准，通过严格数据对齐与零方差/短序列退化保护机制，为组合及单只基金提供 Alpha、Beta、R2、Sharpe、Treynor、Tracking Error 与 Information Ratio 的高鲁棒性业绩归因计算。

# Alpha & Beta 业绩归因引擎设计规范

## 1. 核心数学模型与算式定义

### CAPM 线性回归模型
CAPM 每日超额收益回归方程公式如下：

$$R_{p,t} - R_{f,\text{daily}} = \alpha_{\text{daily}} + \beta (R_{m,t} - R_{f,\text{daily}}) + \epsilon_t$$

- 日度无风险利率 $R_{f,\text{daily}} = \frac{R_{f,\text{annual}}}{252}$（默认年化无风险利率 $R_{f,\text{annual}} = 0.015$）。
- 组合日度超额收益率 $y_t = R_{p,t} - R_{f,\text{daily}}$。
- 基准大盘（如 000300.SH 沪深300）日度超额收益率 $x_t = R_{m,t} - R_{f,\text{daily}}$。

### 组合 Alpha 与 Beta 计算
采用最小二乘法 (OLS) 求解回归系数：

- Portfolio Beta ($\beta$):
  $$\beta = \frac{\text{Cov}(x, y)}{\text{Var}(x)} = \frac{\sum_{t=1}^T (x_t - \bar{x})(y_t - \bar{y})}{\sum_{t=1}^T (x_t - \bar{x})^2}$$

- 年化 Alpha ($\alpha_{\text{annual}}$):
  $$\alpha_{\text{daily}} = \bar{y} - \beta \bar{x}$$
  $$\alpha_{\text{annual}} = \alpha_{\text{daily}} \times 252$$

- 拟合优度 ($R^2$):
  $$R^2 = \frac{[\text{Cov}(x, y)]^2}{\text{Var}(x) \cdot \text{Var}(y)}$$

### 风险调整与归因指标
风险收益比与跟踪误差算式如下：

- 年化夏普比率 (Sharpe Ratio):
  $$\text{Sharpe} = \frac{\text{mean}(R_p - R_{f,\text{daily}})}{\text{std}(R_p)} \times \sqrt{252}$$

- 年化特雷诺比率 (Treynor Ratio):
  $$\text{Treynor} = \frac{\text{mean}(R_p - R_{f,\text{daily}}) \times 252}{\beta}$$

- 年化跟踪误差 (Tracking Error, TE):
  $$TE = \text{std}(R_p - R_m) \times \sqrt{252}$$

- 年化信息比率 (Information Ratio, IR):
  $$IR = \frac{\text{mean}(R_p - R_m)}{\text{std}(R_p - R_m)} \times \sqrt{252} = \frac{\text{mean}(R_p - R_m) \times 252}{TE}$$

## 2. 边界条件与异常降级策略

### 观测样本不足 (T < 10)
- 交易日对齐后有效样本数少于 10 天时触发降级保护。
- 所有数值型指标均返回 0.0。
- fund_metrics 返回空字典 {}。
- scatter_data 返回空列表 []。

### 基准方差为零 (Var(Rm) = 0)
- 基准指数收益率为常数时方差为 0。
- Beta 系数设为 0.0。
- 年化 Alpha 设为 0.0。
- R2 拟合优度设为 0.0。
- Treynor 比率设为 0.0。

### 组合方差为零或 Beta 为零 (Var(Rp) = 0 / Beta = 0)
- 组合收益率为常数时 Sharpe 比率设为 0.0。
- Beta 绝对值小于 1e-8 时 Treynor 比率设为 0.0。
- 跟踪误差 TE 为 0.0 时 Information Ratio 设为 0.0。
- 缺失值 NaN 及无穷值 Inf 在交集对齐阶段直接剔除。

## 3. 接口契约与输出结构

### 输入参数契约
- nav_df_dict: Dict[str, pd.DataFrame]，基金代码映射至净值数据框。
- market_benchmark_df: pd.DataFrame，大盘基准指数（如 000300.SH）数据框。
- fund_market_values: Dict[str, float]，基金代码映射至持仓市值。
- rf_rate: float，默认值 0.015（年化 1.5% 无风险利率）。

### 输出字典结构
- portfolio_alpha: 年化 Alpha 收益率 (float)。
- portfolio_beta: 组合 Beta 系数 (float)。
- portfolio_r2: CAPM 回归 R2 (float)。
- sharpe_ratio: 年化夏普比率 (float)。
- treynor_ratio: 年化特雷诺比率 (float)。
- information_ratio: 年化信息比率 (float)。
- tracking_error: 年化跟踪误差 (float)。
- fund_metrics: Dict[str, Dict[str, float]]，单只基金指标字典。
- scatter_data: List[Dict[str, Any]]，回归散点图绘制数据列表。

## 4. 单基金归因与散点图数据流

### 单只基金指标 (fund_metrics)
- 遍历 nav_df_dict 中的每只基金代码。
- 将单基金日收益率与基准指数在相同交易日进行交集对齐。
- 单独执行 CAPM OLS 回归并计算该基金的 Alpha, Beta, R2, Sharpe, Treynor, IR, TE。
- 将计算结果写入 fund_metrics[fund_code] 字典。

### 散点图数据结构 (scatter_data)
- 提取组合与基准在每个共同交易日的收益率。
- 记录 date, portfolio_return, market_return, portfolio_excess_return, market_excess_return 字段。
- 浮点数结果统一保留 6 位小数以提升传输效率。
- 直接适配 src/ui/charts.py 的 Plotly 回归散点图渲染接口。
