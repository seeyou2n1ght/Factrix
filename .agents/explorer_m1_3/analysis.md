> **BLUF**: 本报告针对 `src/ui/charts.py` 的 Plotly 图表架构，完成了 `create_alpha_beta_scatter` 函数的系统设计，实现了 CAPM 特征线、日收益率散点分布及基金单体 Alpha/Beta 的可视化呈现，全面匹配 Factrix 深色主题色彩规范。

# Plotly CAPM Alpha/Beta 散点回归图表设计报告

## 现存 Plotly 图表架构与主题规范分析

Factrix UI 层的 Plotly 图表统一存放在 `src/ui/charts.py` 文件中，目前包含 6 大核心分析维度的图表生成函数。
现存图表函数通过 `pio.templates["custom_premium"]` 全局模板与 `template="plotly_white"` 实现浅色风格渲染，而在 `create_portfolio_treemap` 中已使用 `template='plotly_dark'` 与深色背景 `#0f172a`。
新增的 `create_alpha_beta_scatter` 函数需完全遵循 Factrix 暗黑主题标准，采用指定的基础背景 `#1E1E1E` 与图表卡片区域背景 `#262626`。
配色方案严格绑定标准调色板：主线条与组合散点使用电光蓝 `#00D2FF`，超额 Alpha 提示与强收益使用荧光绿 `#00E676`，警示线与下行风险使用警示红 `#FF4B4B`。

- 包含 6 大已有图表函数与 1 个深色树状图函数 `create_portfolio_treemap`。
- 图表背景采用 `#1E1E1E`（外框背景）与 `#262626`（绘图区背景）。
- 坐标轴网格线采用 `#333333`，文本颜色采用 `#FFFFFF` 与 `#94A3B8`。
- 核心配色涵盖 `#00D2FF`（电光蓝）、`#00E676`（荧光绿）、`#FF4B4B`（霓虹红）。
- 支持空数据防御性降级，通过 `_create_empty_figure_dark` 返回规范图表对象。

## create_alpha_beta_scatter 函数接口与数据结构设计

`create_alpha_beta_scatter` 函数设计为同时支持输入完整字典 `alpha_beta_res` 或显式入参，确保与 `AlphaBetaEngine.calculate()` 产出接口缝结合。
数据来源涵盖组合与基准日收益率时间序列 DataFrame、CAPM 回归参数（Alpha, Beta, R^2）以及各单只基金的 Alpha/Beta 归因指标字典。
当传入数据为空或记录数低于有效阈值时，自动调用暗黑主题样式的空图表防护逻辑，防止 UI 渲染崩溃。
散点坐标系 X 轴对应基准日收益率 $R_m$，Y 轴对应组合日收益率 $R_p$，线性回归方程为 $R_p = \alpha_{\text{daily}} + \beta \cdot R_m$。

- 函数签名：`create_alpha_beta_scatter(alpha_beta_res: Optional[Dict[str, Any]] = None, scatter_df: Optional[pd.DataFrame] = None, theme: str = "dark") -> go.Figure`。
- 输入数据字典关键字段：`scatter_data` (包含 `date`, `market_return`, `portfolio_return`)、`portfolio_alpha`、`portfolio_beta`、`portfolio_r2`、`fund_metrics`。
- 输出类型：`plotly.graph_objects.Figure`。
- 象限划分：基于 $X=0$ 与 $Y=0$ 划分 4 大收益归因象限。
- 防御降级：支持缺失值填补与单点边界条件校验。

## 图表 Trace 图层与交互 Hover 模板规范

图表由 4 个核心 Trace 图层叠加构成，按从底层到顶层的顺序依次绘制。
底层为日收益率散点图层，采用 Marker 形式展现历史交易日组合与基准的收益对齐点。
中层为 CAPM 特征回归直线，通过最小二乘法斜率 Beta 与截距 Alpha 计算极值端点坐标绘制线段。
顶层为单只基金在 Alpha-Beta 空间中的归因分布散点，使用不同 Marker 形状与颜色标注不同基金代码。
交互 Hover 模板采用 HTML 格式格式化输出，展示日期、精确到小数点后二位的收益率及 Alpha/Beta 参数。

- 日收益率散点 Trace：`mode='markers'`，颜色 `#00D2FF`，透明度 0.65，Marker 大小 7px。
- CAPM 回归直线 Trace：`mode='lines'`，斜率 Beta，颜色 `#00E676`，线宽 3px。
- 单基金 Alpha-Beta 归因 Trace：`mode='markers+text'`，颜色映射收益率，支持基金代码文本标注。
- Hover 模板设计：`<b>日期: %{customdata}</b><br>基准日收益率: %{x:.2f}%<br>组合日收益率: %{y:.2f}%<extra></extra>`。
- 角落指标卡：Plotly Annotation 框，背景 `#262626`，边框 `#00D2FF`，实时显示 Alpha, Beta, R^2。

## 阈值辅助线与四象限标注设计

在 CAPM 散点图中添加十字基准线（$X=0$ 与 $Y=0$）以及 $Beta=1$ 的基准参照线，构建直观的风险收益基准边界。
四个象限分别代表不同的市场行情与组合表现组合，通过 Annotation 文本框定位在坐标系四角。
第一象限（右上，$X>0, Y>0$）标注为“顺势进攻”，代表基准上涨且组合同步上涨。
第二象限（左上，$X<0, Y>0$）标注为“逆势抗跌”，代表基准下跌而组合实现正收益（Alpha 庇护）。
第三象限（左下，$X<0, Y<0$）与第四象限（右下，$X>0, Y<0$）分别标注为“同步回撤”与“逆势滞涨”。

- 十字零线：`add_shape` 绘制 $X=0$ 与 $Y=0$ 虚线，颜色 `#555555`，线宽 1.5px。
- 基准斜率线：绘制 $Y = X$ 虚线，代表 Beta = 1.0 的市场基准线。
- 左上象限标注：坐标固定于 $(-X_{max} \times 0.6, Y_{max} \times 0.7)$，文本“逆势抗跌 (Alpha 庇护)”，颜色 `#00E676`。
- 右上象限标注：坐标固定于 $(X_{max} \times 0.6, Y_{max} \times 0.7)$，文本“顺势进攻 (大盘同向)”，颜色 `#00D2FF`。
- 零数据降级暗黑空图：`_create_empty_figure_dark` 函数，文本颜色 `#94A3B8`，背景 `#1E1E1E`。

## 拟议代码实现方案

以下为拟在 `src/ui/charts.py` 中新增的完整 `create_alpha_beta_scatter` 函数代码逻辑与辅助暗黑空图函数。
代码包含完整的 Python 类型注解、防御性输入校验及格式化 Plotly Layout 配置。

```python
def _create_empty_figure_dark(title: str, message: str = "暂无有效 Alpha/Beta 回归数据") -> go.Figure:
    """创建暗黑主题下的空 Plotly 图表降级对象。"""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=15, color="#94A3B8")
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#FFFFFF")),
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False, showticklabels=False),
        paper_bgcolor="#1E1E1E",
        plot_bgcolor="#262626",
        height=450,
        margin=dict(l=50, r=40, t=60, b=50)
    )
    return fig


def create_alpha_beta_scatter(
    alpha_beta_res: Optional[Dict[str, Any]] = None,
    scatter_df: Optional[pd.DataFrame] = None,
    theme: str = "dark"
) -> go.Figure:
    """生成 CAPM 特征线与 Alpha/Beta 收益归因散点图。

    Args:
        alpha_beta_res: AlphaBetaEngine.calculate() 返回的字典结果。
        scatter_df: 可选的日收益率 DataFrame (列: date, market_return, portfolio_return)。
        theme: 主题模式 (默认 "dark")。

    Returns:
        plotly.graph_objects.Figure 对象。
    """
    if alpha_beta_res is None:
        alpha_beta_res = {}

    df = scatter_df
    if df is None and "scatter_data" in alpha_beta_res:
        raw_data = alpha_beta_res.get("scatter_data")
        if isinstance(raw_data, pd.DataFrame):
            df = raw_data
        elif isinstance(raw_data, list) and len(raw_data) > 0:
            df = pd.DataFrame(raw_data)

    portfolio_alpha = float(alpha_beta_res.get("portfolio_alpha", 0.0))
    portfolio_beta = float(alpha_beta_res.get("portfolio_beta", 1.0))
    portfolio_r2 = float(alpha_beta_res.get("portfolio_r2", 0.0))
    fund_metrics = alpha_beta_res.get("fund_metrics", {})

    if df is None or not isinstance(df, pd.DataFrame) or df.empty or len(df) < 3:
        return _create_empty_figure_dark("Alpha & Beta 收益归因与 CAPM 回归特征线")

    req_cols = ["market_return", "portfolio_return"]
    if not all(col in df.columns for col in req_cols):
        return _create_empty_figure_dark("Alpha & Beta 收益归因与 CAPM 回归特征线", "收益率数据列缺失")

    m_ret = df["market_return"].values * 100.0 if df["market_return"].max() <= 1.0 else df["market_return"].values
    p_ret = df["portfolio_return"].values * 100.0 if df["portfolio_return"].max() <= 1.0 else df["portfolio_return"].values
    dates = df["date"].astype(str).tolist() if "date" in df.columns else [f"T-{i}" for i in range(len(df))]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=m_ret,
        y=p_ret,
        mode="markers",
        name="日收益率对齐点",
        customdata=dates,
        marker=dict(
            size=7,
            color="#00D2FF",
            opacity=0.65,
            line=dict(width=0.5, color="#FFFFFF")
        ),
        hovertemplate="<b>日期: %{customdata}</b><br>基准日收益率: %{x:.2f}%<br>组合日收益率: %{y:.2f}%<extra></extra>"
    ))

    x_min, x_max = float(np.min(m_ret)), float(np.max(m_ret))
    x_range = np.array([x_min, x_max])
    daily_alpha = portfolio_alpha / 252.0 * 100.0
    y_range = daily_alpha + portfolio_beta * x_range

    line_color = "#00E676" if portfolio_alpha >= 0 else "#FF4B4B"

    fig.add_trace(go.Scatter(
        x=x_range,
        y=y_range,
        mode="lines",
        name=f"CAPM 回归特征线 (β={portfolio_beta:.2f}, R²={portfolio_r2:.2f})",
        line=dict(color=line_color, width=3),
        hovertemplate=(
            f"<b>CAPM 回归特征线</b><br>"
            f"组合 Beta (β): {portfolio_beta:.2f}<br>"
            f"年化 Alpha: {portfolio_alpha:.2%}<br>"
            f"拟合度 (R²): {portfolio_r2:.2f}<extra></extra>"
        )
    ))

    if isinstance(fund_metrics, dict) and len(fund_metrics) > 0:
        f_codes = []
        f_alphas = []
        f_betas = []
        for code, metrics in fund_metrics.items():
            if isinstance(metrics, dict):
                f_codes.append(str(code))
                f_alphas.append(float(metrics.get("alpha", 0.0)) * 100.0)
                f_betas.append(float(metrics.get("beta", 1.0)))

        if len(f_codes) > 0:
            fig.add_trace(go.Scatter(
                x=f_betas,
                y=f_alphas,
                mode="markers+text",
                name="单只基金归因",
                text=f_codes,
                textposition="top center",
                textfont=dict(color="#E2E8F0", size=11),
                marker=dict(
                    size=11,
                    color="#FF4B4B",
                    symbol="diamond",
                    line=dict(width=1, color="#FFFFFF")
                ),
                xaxis="x2",
                yaxis="y2",
                hovertemplate="<b>基金代码: %{text}</b><br>Beta: %{x:.2f}<br>年化 Alpha: %{y:.2f}%<extra></extra>",
                visible="legendonly"
            ))

    fig.add_shape(type="line", x0=x_min, y0=0, x1=x_max, y1=0, line=dict(color="#555555", width=1.5, dash="dash"))
    fig.add_shape(type="line", x0=0, y0=float(np.min(p_ret)), x1=0, y1=float(np.max(p_ret)), line=dict(color="#555555", width=1.5, dash="dash"))

    max_y = max(abs(float(np.min(p_ret))), abs(float(np.max(p_ret))), 1.0)
    max_x = max(abs(x_min), abs(x_max), 1.0)

    fig.add_annotation(x=-max_x * 0.6, y=max_y * 0.7, text="逆势抗跌 (Alpha 庇护)", showarrow=False, font=dict(color="#00E676", size=12))
    fig.add_annotation(x=max_x * 0.6, y=max_y * 0.7, text="顺势进攻 (大盘同向)", showarrow=False, font=dict(color="#00D2FF", size=12))
    fig.add_annotation(x=-max_x * 0.6, y=-max_y * 0.7, text="同步回撤", showarrow=False, font=dict(color="#FF4B4B", size=12))
    fig.add_annotation(x=max_x * 0.6, y=-max_y * 0.7, text="逆势滞涨", showarrow=False, font=dict(color="#FF4B4B", size=12))

    summary_text = f"年化 Alpha: {portfolio_alpha:+.2%} | 组合 Beta: {portfolio_beta:.2f} | R²: {portfolio_r2:.2f}"
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.02, y=0.98,
        text=summary_text,
        showarrow=False,
        align="left",
        bgcolor="#262626",
        bordercolor="#00D2FF",
        borderwidth=1,
        borderpad=6,
        font=dict(color="#FFFFFF", size=12)
    )

    fig.update_layout(
        title=dict(text="Alpha & Beta 收益归因与 CAPM 回归特征线", font=dict(size=16, color="#FFFFFF")),
        xaxis=dict(
            title=dict(text="基准日收益率 (%)", font=dict(color="#E2E8F0")),
            tickfont=dict(color="#94A3B8"),
            gridcolor="#333333",
            zeroline=False
        ),
        yaxis=dict(
            title=dict(text="组合日收益率 (%)", font=dict(color="#E2E8F0")),
            tickfont=dict(color="#94A3B8"),
            gridcolor="#333333",
            zeroline=False
        ),
        paper_bgcolor="#1E1E1E",
        plot_bgcolor="#262626",
        hoverlabel=dict(
            bgcolor="#262626",
            bordercolor="#00D2FF",
            font=dict(color="#FFFFFF", family="Inter, sans-serif", size=13)
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#E2E8F0")
        ),
        height=450,
        margin=dict(l=60, r=40, t=70, b=60)
    )

    return fig
```
