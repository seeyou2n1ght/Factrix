"""Plotly Chart Generators for Factrix Streamlit Dashboard.

Provides interactive Plotly figure builder functions for all 6 core analysis dimensions:
1. Overlap Heatmap (PBSA Holdings Overlap)
2. Style Radar Chart (5 Benchmark Factor Exposures)
3. Rolling Style Drift Line Chart (60-day Rolling RBSA)
4. Black Swan CVaR Stress Testing Bar Chart
5. Prospect Theory Win-Loss Ratio Bubble Chart
6. Rebalance Trade Amount Bar Chart
"""

from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio

# Set premium global chart template
pio.templates["custom_premium"] = pio.templates["plotly_white"]
pio.templates["custom_premium"].layout.font.family = "Inter, -apple-system, sans-serif"
pio.templates["custom_premium"].layout.title.font.family = "Inter, -apple-system, sans-serif"
pio.templates.default = "custom_premium"

FACTOR_CHINESE_LABELS: Dict[str, str] = {
    'large_value': '大盘价值',
    'large_growth': '大盘成长',
    'small_value': '小盘价值',
    'small_growth': '小盘成长',
    'bond_index': '国债指数'
}

# 5 Broad Sectors + 其他 Color Palette (Vibrant Premium Colors)
SECTOR_COLORS: Dict[str, str] = {
    '科技制造': '#3b82f6',  # Bright Blue
    '大消费': '#f43f5e',    # Vibrant Rose
    '医药健康': '#10b981',  # Emerald
    '大金融': '#8b5cf6',    # Violet
    '周期资源': '#f59e0b',  # Amber
    '其他': '#94a3b8',      # Slate
}

# 4 Macro Asset Classes Color Palette
MACRO_ASSET_COLORS: Dict[str, str] = {
    '股票资产': '#2563eb',  # Royal Blue
    '债券资产': '#059669',  # Dark Emerald
    '现金货基': '#d97706',  # Dark Amber
    '其他资产': '#64748b',  # Slate
    '商品/其他': '#64748b',
    'Equity': '#2563eb',
    'Fixed Income': '#059669',
    'Commodity': '#64748b',
    'Cash': '#d97706',
}

MACRO_LABEL_MAP: Dict[str, str] = {
    'Equity': '股票资产',
    'Fixed Income': '债券资产',
    'Commodity': '商品/其他',
    'Cash': '现金货基',
}



def _create_empty_figure(title: str, message: str = "暂无有效数据") -> go.Figure:
    """Helper to return a clean empty Plotly figure when input data is missing."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=16, color="#94a3b8")
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#1e293b")),
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False, showticklabels=False),
        height=350,
        margin=dict(l=40, r=40, t=60, b=40)
    )
    return fig


def create_overlap_heatmap(overlap_df: pd.DataFrame) -> go.Figure:
    """Create Fund Holdings Cosine Overlap Heatmap.

    Args:
        overlap_df: pd.DataFrame of shape (N, N) with fund codes as index/columns
                    and overlap ratio values in [0, 1].

    Returns:
        plotly.graph_objects.Figure instance.
    """
    if overlap_df is None or not isinstance(overlap_df, pd.DataFrame) or overlap_df.empty:
        return _create_empty_figure("基金持仓穿透重合度热力图 (防抱团)")

    fund_codes = [str(c) for c in overlap_df.columns]
    z_matrix = overlap_df.values

    # Format text labels for hover
    hover_text = [
        [f"基金 {fund_codes[i]} 与 基金 {fund_codes[j]}<br>持仓重合度: {z_matrix[i][j]*100:.1f}%"
         for j in range(len(fund_codes))]
        for i in range(len(fund_codes))
    ]

    fig = go.Figure(data=go.Heatmap(
        z=z_matrix,
        x=fund_codes,
        y=fund_codes,
        hoverinfo="text",
        text=hover_text,
        colorscale=[
            [0.0, '#f8fafc'],
            [0.25, '#fef08a'],
            [0.6, '#f97316'],
            [1.0, '#dc2626'],
        ],
        zmin=0.0,
        zmax=1.0,
        colorbar=dict(
            title=dict(text="重合度比例", font=dict(size=12)),
            tickformat=".0%",
            len=0.9
        )
    ))

    fig.update_layout(
        title=dict(text="🔥 基金持仓穿透重合度热力图 (防抱团)", font=dict(size=16, color="#0f172a")),
        xaxis=dict(title="基金代码", type="category", tickangle=-45),
        yaxis=dict(title="基金代码", type="category", autorange="reversed"),
        height=450,
        margin=dict(l=60, r=60, t=60, b=60),
        template="plotly_white"
    )

    return fig


def create_macro_asset_pie(macro_dict: Union[Dict[str, float], pd.Series]) -> go.Figure:
    """Create 4 Macro Asset Classes Donut Chart (Before Penetration).

    Args:
        macro_dict: Dict or pd.Series mapping macro asset names to percentage in [0, 100].

    Returns:
        plotly.graph_objects.Figure instance.
    """
    if macro_dict is None:
        return _create_empty_figure("4大隔离宏观资产配置比例 (穿透前)")
    if isinstance(macro_dict, pd.Series):
        if macro_dict.empty:
            return _create_empty_figure("4大隔离宏观资产配置比例 (穿透前)")
        data_dict = macro_dict.to_dict()
    elif isinstance(macro_dict, dict):
        if not macro_dict:
            return _create_empty_figure("4大隔离宏观资产配置比例 (穿透前)")
        data_dict = macro_dict
    else:
        return _create_empty_figure("4大隔离宏观资产配置比例 (穿透前)")

    raw_labels = list(data_dict.keys())
    labels = [MACRO_LABEL_MAP.get(lbl, lbl) for lbl in raw_labels]
    values = [float(v) for v in data_dict.values()]
    colors = [MACRO_ASSET_COLORS.get(lbl, MACRO_ASSET_COLORS.get(raw_lbl, '#64748b')) for lbl, raw_lbl in zip(labels, raw_labels)]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.52,
        marker=dict(colors=colors, line=dict(color='#ffffff', width=2)),
        textinfo='label+percent',
        hovertemplate="<b>%{label}</b><br>占比: %{percent:.1%}<br>权重: %{value:.2f}%<extra></extra>"
    )])

    fig.update_layout(
        title=dict(text="📦 穿透前：4大隔离宏观资产配置占比", font=dict(size=15, color="#0f172a")),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        height=400,
        margin=dict(l=30, r=30, t=50, b=50),
        template="plotly_white"
    )
    return fig


def create_sector_pie(sector_series: pd.Series, renormalized: bool = True) -> go.Figure:
    """Create 5 Broad Stock Sectors Donut Chart (100% Re-normalized After Penetration).

    Args:
        sector_series: pd.Series mapping broad sector names to weights.
        renormalized: Whether to re-normalize stock weights to sum to 100%.

    Returns:
        plotly.graph_objects.Figure instance.
    """
    if sector_series is None or sector_series.empty or sector_series.sum() <= 0:
        return _create_empty_figure("100% 重归一化股票行业占比 (穿透后)")

    total_val = float(sector_series.sum())
    if renormalized:
        values = [(float(v) / total_val) * 100.0 for v in sector_series.values]
        title_text = "📊 穿透后：100% 重归一化股票行业占比"
    else:
        values = [float(v) for v in sector_series.values]
        title_text = "📊 穿透后：股票行业占比"

    labels = list(sector_series.index)
    colors = [SECTOR_COLORS.get(lbl, '#64748b') for lbl in labels]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.52,
        marker=dict(colors=colors, line=dict(color='#ffffff', width=2)),
        textinfo='label+percent',
        hovertemplate="<b>%{label}</b><br>股票内占比: %{percent:.1%}<br>权重: %{value:.2f}%<extra></extra>"
    )])

    fig.update_layout(
        title=dict(text=title_text, font=dict(size=15, color="#0f172a")),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        height=400,
        margin=dict(l=30, r=30, t=50, b=50),
        template="plotly_white"
    )
    return fig



def create_style_radar(style_dict: Union[Dict[str, float], Dict[str, Any]]) -> go.Figure:
    """Create 5-Factor Style Exposure Radar Chart (RBSA).

    Args:
        style_dict: Dict containing factor weights e.g.
                    {'large_value': 0.3, 'large_growth': 0.2, ...}
                    or {'radar_data': {'labels': [...], 'values': [...]}}

    Returns:
        plotly.graph_objects.Figure instance.
    """
    if not style_dict or not isinstance(style_dict, dict):
        return _create_empty_figure("5大风格暴露雷达图 (投资照妖镜)")

    # Extract labels and values
    if 'radar_data' in style_dict and isinstance(style_dict['radar_data'], dict):
        r_data = style_dict['radar_data']
        labels = list(r_data.get('labels', []))
        values = list(r_data.get('values', []))
    elif 'labels' in style_dict and 'values' in style_dict:
        labels = list(style_dict.get('labels', []))
        values = list(style_dict.get('values', []))
    else:
        labels = [FACTOR_CHINESE_LABELS.get(k, k) for k in FACTOR_CHINESE_LABELS.keys()]
        values = [float(style_dict.get(k, 0.2)) for k in FACTOR_CHINESE_LABELS.keys()]

    if not labels or not values or len(labels) != len(values):
        return _create_empty_figure("5大风格暴露雷达图 (投资照妖镜)")

    # Close radar loop
    radar_labels = labels + [labels[0]]
    radar_values = values + [values[0]]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=radar_values,
        theta=radar_labels,
        fill='toself',
        name='真实风格暴露',
        line=dict(color='#2563eb', width=2.5),
        fillcolor='rgba(37, 99, 235, 0.25)',
        marker=dict(size=6, color='#1d4ed8')
    ))

    max_v = max(values) if values else 1.0
    radial_max = min(1.0, max(0.4, max_v * 1.15))

    fig.update_layout(
        title=dict(text="🎯 5大风格暴露雷达图 (真实投资照妖镜)", font=dict(size=16, color="#0f172a")),
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0.0, radial_max],
                tickformat=".0%",
                gridcolor="#e2e8f0"
            ),
            angularaxis=dict(
                gridcolor="#cbd5e1",
                tickfont=dict(size=12, color="#334155")
            )
        ),
        showlegend=False,
        height=420,
        margin=dict(l=60, r=60, t=60, b=60),
        template="plotly_white"
    )

    return fig


def create_style_drift_line(rolling_df: pd.DataFrame) -> go.Figure:
    """Create 60-day Rolling RBSA Style Drift Line Chart over time.

    Args:
        rolling_df: pd.DataFrame indexed by date string, columns = factor keys.

    Returns:
        plotly.graph_objects.Figure instance.
    """
    if rolling_df is None or not isinstance(rolling_df, pd.DataFrame) or rolling_df.empty:
        return _create_empty_figure("60日 Rolling RBSA 风格漂移轨迹 (言行一致性)")

    fig = go.Figure()

    color_map = {
        'large_value': '#2563eb',   # Royal blue
        'large_growth': '#ec4899',  # Pink / Magenta
        'small_value': '#8b5cf6',   # Purple
        'small_growth': '#f59e0b',  # Amber
        'bond_index': '#10b981'     # Emerald green
    }

    dates = rolling_df.index.tolist()

    for factor_key in rolling_df.columns:
        chinese_name = FACTOR_CHINESE_LABELS.get(factor_key, factor_key)
        line_color = color_map.get(factor_key, '#64748b')
        y_vals = rolling_df[factor_key].values

        fig.add_trace(go.Scatter(
            x=dates,
            y=y_vals,
            mode='lines',
            name=chinese_name,
            line=dict(color=line_color, width=2),
            hovertemplate=f"<b>{chinese_name}</b>: %{{y:.2%}}<extra></extra>"
        ))

    fig.update_layout(
        title=dict(text="📈 60日 Rolling RBSA 风格漂移轨迹 (言行一致性)", font=dict(size=16, color="#0f172a")),
        xaxis=dict(title="日期", showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(title="风格因子暴露权重", tickformat=".0%", range=[0.0, 1.05], showgrid=True, gridcolor="#f1f5f9"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=420,
        margin=dict(l=50, r=40, t=70, b=50),
        template="plotly_white"
    )

    return fig


def create_cvar_stress_bar(stress_dict: Dict[str, Any]) -> go.Figure:
    """Create Black Swan Historical Stress Test Loss Bar Chart.

    Args:
        stress_dict: Dict mapping scenario keys to dict with 'scenario_name',
                     'loss_pct', 'loss_amount'.

    Returns:
        plotly.graph_objects.Figure instance.
    """
    if not stress_dict or not isinstance(stress_dict, dict):
        return _create_empty_figure("黑天鹅历史场景预估冲击压力测试")

    scenarios = []
    loss_pcts = []
    loss_amounts = []
    descriptions = []

    for k, v in stress_dict.items():
        if isinstance(v, dict):
            scenarios.append(v.get('scenario_name', k))
            loss_pcts.append(float(v.get('loss_pct', 0.0)) * 100.0)
            loss_amounts.append(float(v.get('loss_amount', 0.0)))
            descriptions.append(v.get('description', ''))

    if not scenarios:
        return _create_empty_figure("黑天鹅历史场景预估冲击压力测试")

    text_labels = [f"-{lp:.1f}% (亏损 ¥{la:,.0f}元)" for lp, la in zip(loss_pcts, loss_amounts)]

    fig = go.Figure(data=go.Bar(
        x=scenarios,
        y=loss_pcts,
        text=text_labels,
        textposition='outside',
        marker=dict(
            color=['#ef4444', '#f97316', '#eab308'][:len(scenarios)],
            line=dict(color='#991b1b', width=1.5)
        ),
        hovertemplate="<b>%{x}</b><br>预估跌幅: -%{y:.1f}%<br>描述: %{customdata}<extra></extra>",
        customdata=descriptions
    ))

    max_loss = max(loss_pcts) if loss_pcts else 10.0

    fig.update_layout(
        title=dict(text="🌪️ 黑天鹅历史场景预估冲击压力测试 (防暴雨)", font=dict(size=16, color="#0f172a")),
        xaxis=dict(title="历史黑天鹅极端场景"),
        yaxis=dict(title="组合预估最大跌幅 (%)", range=[0.0, max(40.0, max_loss * 1.25)], ticksuffix="%"),
        height=420,
        margin=dict(l=50, r=40, t=60, b=50),
        template="plotly_white"
    )

    return fig


def create_prospect_bubble(
    win_rate: float,
    payoff_ratio: float,
    prospect_utility: float,
    omega_ratio: float = 1.0
) -> go.Figure:
    """Create Prospect Theory Win-Loss Ratio Bubble Chart with 4 Quadrants.

    Args:
        win_rate: Win rate float in [0, 1].
        payoff_ratio: Payoff (gain/loss) ratio float.
        prospect_utility: Kahneman-Tversky prospect utility float score.
        omega_ratio: Omega ratio float score.

    Returns:
        plotly.graph_objects.Figure instance.
    """
    win_pct = float(win_rate) * 100.0
    payoff = float(payoff_ratio)
    utility = float(prospect_utility)

    # Bubble size scaled by omega ratio / utility magnitude
    bubble_size = max(25, min(80, int(abs(utility) * 5000 + omega_ratio * 20)))

    fig = go.Figure()

    # Current Portfolio Marker Trace
    fig.add_trace(go.Scatter(
        x=[win_pct],
        y=[payoff],
        mode='markers+text',
        name='当前组合性价比',
        text=[f"当前组合<br>(胜率 {win_pct:.1f}%, 赔率 {payoff:.2f})"],
        textposition="top center",
        marker=dict(
            size=bubble_size,
            color='#2563eb',
            opacity=0.85,
            line=dict(color='#1e3a8a', width=3)
        ),
        hovertemplate=(
            "<b>当前组合性价比</b><br>"
            "胜率: %{x:.1f}%<br>"
            "赔率(盈亏比): %{y:.2f}<br>"
            f"前景效用 V(r): {utility:.6f}<br>"
            f"Omega 比率: {omega_ratio:.2f}<extra></extra>"
        )
    ))

    # Reference Quadrant Line Thresholds: Win Rate = 50%, Payoff = 1.0
    fig.add_shape(type="line", x0=0, y0=1.0, x1=100, y1=1.0, line=dict(color="#cbd5e1", width=2, dash="dash"))
    fig.add_shape(type="line", x0=50, y0=0, x1=50, y1=max(5.0, payoff * 1.3), line=dict(color="#cbd5e1", width=2, dash="dash"))

    # Quadrant Background Annotations
    fig.add_annotation(x=75, y=max(3.5, payoff * 1.15), text="⭐ 高胜率·高赔率<br>(理想圣杯组合)", showarrow=False, font=dict(color="#15803d", size=13, weight="bold"))
    fig.add_annotation(x=25, y=max(3.5, payoff * 1.15), text="🚀 低胜率·高赔率<br>(趋势爆利型)", showarrow=False, font=dict(color="#0369a1", size=12))
    fig.add_annotation(x=75, y=0.4, text="⚠️ 高胜率·低赔率<br>(小利大亏钝刀割肉)", showarrow=False, font=dict(color="#b45309", size=12))
    fig.add_annotation(x=25, y=0.4, text="❌ 低胜率·低赔率<br>(亏本买卖)", showarrow=False, font=dict(color="#b91c1c", size=12))

    fig.update_layout(
        title=dict(text="🧮 前景理论胜率赔率性价比算盘 (Kahneman-Tversky)", font=dict(size=16, color="#0f172a")),
        xaxis=dict(title="滚动持有期胜率 (%)", range=[0, 100], ticksuffix="%"),
        yaxis=dict(title="赔率 (盈亏比 = 平均盈利 / 平均亏损)", range=[0, max(4.5, payoff * 1.35)]),
        height=420,
        margin=dict(l=50, r=40, t=60, b=50),
        template="plotly_white"
    )

    return fig


def create_rebalance_bar(trade_actions: List[Dict[str, Any]]) -> go.Figure:
    """Create Rebalance Buy/Sell Signed Amount Bar Chart.

    Args:
        trade_actions: List of trade action dicts containing
                       'action' ('BUY'/'SELL'), 'fund_code', 'amount'.

    Returns:
        plotly.graph_objects.Figure instance.
    """
    if not trade_actions or not isinstance(trade_actions, list):
        return _create_empty_figure("智能调仓建议买卖金额", "当前组合无需买卖调仓")

    fund_codes = []
    amounts = []
    colors = []
    texts = []

    for item in trade_actions:
        action = item.get('action', 'BUY')
        code = str(item.get('fund_code', ''))
        amt = float(item.get('amount', 0.0))

        fund_codes.append(code)
        if action == 'BUY':
            amounts.append(amt)
            colors.append('#10b981')  # Green for BUY
            texts.append(f"+¥{amt:,.0f}")
        else:
            amounts.append(-amt)
            colors.append('#ef4444')  # Red for SELL
            texts.append(f"-¥{amt:,.0f}")

    if not fund_codes:
        return _create_empty_figure("智能调仓建议买卖金额", "当前组合无需买卖调仓")

    fig = go.Figure(data=go.Bar(
        x=fund_codes,
        y=amounts,
        text=texts,
        textposition='outside',
        marker=dict(color=colors, line=dict(color='#334155', width=1)),
        hovertemplate="<b>基金代码: %{x}</b><br>调仓金额: ¥%{y:,.2f}<extra></extra>"
    ))

    max_amt = max(abs(a) for a in amounts) if amounts else 1000.0

    fig.update_layout(
        title=dict(text="⚖️ 智能调仓建议买卖金额 (正向买入 / 负向卖出)", font=dict(size=16, color="#0f172a")),
        xaxis=dict(title="基金代码", type="category"),
        yaxis=dict(title="调仓变动金额 (元)", range=[-max_amt * 1.3, max_amt * 1.3]),
        height=400,
        margin=dict(l=50, r=40, t=60, b=50),
        template="plotly_white"
    )

    return fig


def create_risk_gauge_chart(risk_score: float, risk_level: str = "中风险") -> go.Figure:
    """Create interactive Plotly indicator gauge chart for portfolio risk score (0-100).

    Args:
        risk_score: Numerical risk score between 0 and 100.
        risk_level: Descriptive risk level string (e.g. "保守型", "中风险", "高风险").

    Returns:
        plotly.graph_objects.Figure instance.
    """
    title_text = "🛡️ 组合风险综合评估仪表盘"
    if risk_score is None:
        return _create_empty_figure(title_text)

    try:
        score_val = float(risk_score)
        if np.isnan(score_val) or np.isinf(score_val):
            return _create_empty_figure(title_text)
    except (ValueError, TypeError):
        return _create_empty_figure(title_text)

    score_clamped = max(0.0, min(100.0, score_val))

    if score_clamped <= 30.0:
        bar_color = "#10b981"
    elif score_clamped <= 70.0:
        bar_color = "#f59e0b"
    else:
        bar_color = "#ef4444"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score_clamped,
        number={'suffix': " 分", 'font': {'size': 36, 'color': '#0f172a'}},
        title={
            'text': f"<b>{title_text}</b><br><span style='font-size:0.85em;color:#64748b'>风险等级: {risk_level}</span>",
            'font': {'size': 16, 'color': '#0f172a'}
        },
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#475569"},
            'bar': {'color': bar_color, 'thickness': 0.6},
            'bgcolor': "#f8fafc",
            'borderwidth': 1,
            'bordercolor': "#e2e8f0",
            'steps': [
                {'range': [0, 30], 'color': 'rgba(16, 185, 129, 0.2)'},
                {'range': [30, 70], 'color': 'rgba(245, 158, 11, 0.2)'},
                {'range': [70, 100], 'color': 'rgba(239, 68, 68, 0.2)'},
            ],
            'threshold': {
                'line': {'color': '#0f172a', 'width': 4},
                'thickness': 0.75,
                'value': score_clamped,
            },
        }
    ))

    fig.update_layout(
        height=380,
        margin=dict(l=40, r=40, t=60, b=40),
        template="plotly_white",
    )
    return fig


def create_alpha_beta_scatter(
    scatter_data: List[Dict[str, Any]],
    alpha: float = 0.0,
    beta: float = 1.0
) -> go.Figure:
    """Create Scatter Plot of Portfolio Returns vs Benchmark Returns with OLS Regression Line.

    Args:
        scatter_data: List of dicts containing 'market_return' and 'portfolio_return'.
        alpha: Annualized Jensen's Alpha (float).
        beta: Portfolio Beta relative to benchmark (float).

    Returns:
        plotly.graph_objects.Figure instance.
    """
    title_text = "📊 Alpha / Beta 收益回归散点图"
    if not scatter_data or not isinstance(scatter_data, list):
        return _create_empty_figure(title_text)

    market_rets = []
    port_rets = []

    for item in scatter_data:
        if isinstance(item, dict) and 'market_return' in item and 'portfolio_return' in item:
            try:
                m_ret = float(item['market_return'])
                p_ret = float(item['portfolio_return'])
                if not (np.isnan(m_ret) or np.isnan(p_ret) or np.isinf(m_ret) or np.isinf(p_ret)):
                    market_rets.append(m_ret)
                    port_rets.append(p_ret)
            except (ValueError, TypeError):
                continue

    if not market_rets or not port_rets or len(market_rets) != len(port_rets):
        return _create_empty_figure(title_text)

    m_pcts = [m * 100.0 for m in market_rets]
    p_pcts = [p * 100.0 for p in port_rets]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=m_pcts,
        y=p_pcts,
        mode='markers',
        name='日收益率对',
        marker=dict(
            size=7,
            color='#2563eb',
            opacity=0.6,
            line=dict(width=1, color='#1e40af')
        ),
        hovertemplate="基准日收益率: %{x:.2f}%<br>组合日收益率: %{y:.2f}%<extra></extra>"
    ))

    x_min, x_max = min(m_pcts), max(m_pcts)
    x_range = np.linspace(x_min, x_max, 100)

    try:
        alpha_val = float(alpha) if alpha is not None else 0.0
        if np.isnan(alpha_val) or np.isinf(alpha_val):
            alpha_val = 0.0
    except (ValueError, TypeError):
        alpha_val = 0.0

    try:
        beta_val = float(beta) if beta is not None else 1.0
        if np.isnan(beta_val) or np.isinf(beta_val):
            beta_val = 1.0
    except (ValueError, TypeError):
        beta_val = 1.0

    alpha_daily = alpha_val / 252.0
    y_range = [beta_val * x + alpha_daily * 100.0 for x in x_range]

    fig.add_trace(go.Scatter(
        x=x_range,
        y=y_range,
        mode='lines',
        name='OLS 回归线',
        line=dict(color='#ef4444', width=2.5, dash='solid'),
        hovertemplate="拟合线 (Beta=%{customdata[0]:.2f}): y = %{y:.2f}%<extra></extra>",
        customdata=[[beta_val]] * len(x_range)
    ))

    annotation_text = (
        f"<b>回归分析指标:</b><br>"
        f"年化 Alpha: <b>{alpha_val * 100.0:.2f}%</b><br>"
        f"贝塔 Beta: <b>{beta_val:.2f}</b>"
    )

    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.03, y=0.95,
        text=annotation_text,
        showarrow=False,
        align="left",
        bgcolor="rgba(255, 255, 255, 0.85)",
        bordercolor="#cbd5e1",
        borderwidth=1,
        borderpad=8,
        font=dict(size=12, color="#0f172a")
    )

    fig.update_layout(
        title=dict(text=f"<b>{title_text}</b>", font=dict(size=16, color="#0f172a")),
        xaxis=dict(title="基准日收益率 (%)", showgrid=True, gridcolor="#f1f5f9", ticksuffix="%"),
        yaxis=dict(title="组合日收益率 (%)", showgrid=True, gridcolor="#f1f5f9", ticksuffix="%"),
        height=420,
        margin=dict(l=50, r=40, t=60, b=50),
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig

