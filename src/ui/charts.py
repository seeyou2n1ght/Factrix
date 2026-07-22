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

FACTOR_CHINESE_LABELS: Dict[str, str] = {
    'large_value': '大盘价值',
    'large_growth': '大盘成长',
    'small_value': '小盘价值',
    'small_growth': '小盘成长',
    'bond_index': '国债指数'
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
        colorscale="YlOrRd",
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
        'large_value': '#1e3a8a',   # Dark blue
        'large_growth': '#0284c7',  # Light blue
        'small_value': '#d97706',   # Amber
        'small_growth': '#dc2626',  # Red
        'bond_index': '#16a34a'     # Green
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
