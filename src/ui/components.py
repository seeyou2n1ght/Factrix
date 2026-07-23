"""UI Components module for Factrix Streamlit dashboard.

Provides custom CSS injections, panorama health diagnostic cards, plain-language (vernacular)
educational callouts, rebalance trade action guides, stock penetration tables, retail risk profiling cards,
and RMB loss simulations.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px


VERNACULAR_EXPLANATIONS: Dict[str, Dict[str, str]] = {
    "PBSA": {
        "title": "💡 白话小贴士：防抱团持仓穿透 (PBSA)",
        "content": (
            "**表面分散，背地抱团？**\n\n"
            "买多只基金不等于分散风险！穿透算法会把您投出去的每一百块钱拆解到底层持有的股票上。"
            "如果不同基金经理背地里都在买同一批‘核心资产’（比如茅台、宁德时代），热力图就会亮起红灯警告！"
        ),
    },
    "RBSA": {
        "title": "💡 白话小贴士：真实风格画像 (投资照妖镜 RBSA)",
        "content": (
            "**不看宣传看疗效！**\n\n"
            "基金经理报告里写的投资理念可能存在滞后或偏差。我们拿基金每天的真实涨跌幅去和市场上"
            "‘大盘价值’、‘大盘成长’、‘小盘价值’、‘小盘成长’、‘国债’5大纯正标尺比对，长得最像什么，"
            "说明他背地里真正买了什么。"
        ),
    },
    "Rolling_RBSA": {
        "title": "💡 白话小贴士：风格漂移监测 (言行一致性)",
        "content": (
            "**基金经理有没有漂移追热点？**\n\n"
            "通过 60 天滚动窗口监测风格演变。如果招股书上说是坚持‘大盘价值’，中途却偷偷跑去追高"
            "‘小盘成长’热点，折线图就会剧烈波动，提示您言行一致性较低。"
        ),
    },
    "CVaR": {
        "title": "💡 白话小贴士：黑天鹅压力测试 (防暴雨体检)",
        "content": (
            "**万一遇到三十年一遇的特大台风，您的持仓会淹多深？**\n\n"
            "常规波动率只告诉您平时下雨小磕小碰。CVaR 尾部风险与历史黑天鹅回放（如 2015 股市踩踏、2022 股债双杀）"
            "直接模拟极端市场暴跌，算清您的 10 万元持仓在暴风雨中最多预估亏损多少钱。"
        ),
    },
    "Prospect_Theory": {
        "title": "💡 白话小贴士：胜率赔率与性价比算盘 (前景理论)",
        "content": (
            "**去打牌不能只看胜率，更要看赚赔比！**\n\n"
            "评估持仓是‘赢了赚100包辣条，输了只赔5包’的划算买卖，还是‘赢了赚5包，输了赔干家底’的亏本买卖。"
            "结合诺贝尔奖 Kahneman-Tversky 损失厌恶模型（λ=2.25），替您的真实心理承受力打分。"
        ),
    },
    "Rebalance": {
        "title": "💡 白话小贴士：智能保养与调仓导航 (带摩擦二次规划)",
        "content": (
            "**车跑偏了或机油少了，仪表盘亮灯提醒您保养！**\n\n"
            "调仓算法不仅帮您找出该买卖哪只基金，还把赎回手续费（如 <7 天 1.5% 惩罚费）精确算进去。"
            "只有‘调仓后省下的风险和多赚的钱绝对覆盖过路费’时，才会输出买卖金额指令与避费贴士。"
        ),
    },
}


def set_global_css() -> None:
    """Inject modern, responsive global CSS styles into Streamlit app."""
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

    /* Main layout & typography styling */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        background-color: #f8fafc;
    }

    /* Metric cards styling override */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.5);
        border-radius: 16px;
        padding: 20px 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03), 0 1px 3px rgba(0, 0, 0, 0.05);
        transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    [data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.07), 0 4px 8px rgba(0, 0, 0, 0.04);
    }

    /* Panorama Health Diagnostic Card Container */
    .health-card-container {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%);
        border-radius: 20px;
        padding: 32px 36px;
        color: #f8fafc;
        box-shadow: 0 16px 40px -10px rgba(15, 23, 42, 0.6), 0 8px 16px rgba(0, 0, 0, 0.3);
        margin-bottom: 32px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        position: relative;
        overflow: hidden;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .health-card-container:hover {
        transform: translateY(-2px);
        box-shadow: 0 20px 48px -10px rgba(15, 23, 42, 0.7), 0 10px 20px rgba(0, 0, 0, 0.4);
    }

    .health-card-container::before {
        content: '';
        position: absolute;
        top: -50%; left: -50%; width: 200%; height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 60%);
        pointer-events: none;
    }

    .health-header-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        position: relative;
        z-index: 1;
    }
    
    .health-title {
        font-size: 1.6rem;
        font-weight: 800;
        color: #f1f5f9;
        letter-spacing: 0.5px;
        margin: 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    /* Grade Color Badges */
    .grade-badge {
        display: inline-block;
        padding: 8px 24px;
        border-radius: 30px;
        font-size: 1.2rem;
        font-weight: 800;
        text-align: center;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        position: relative;
        z-index: 1;
    }
    
    .badge-excellent {
        background: linear-gradient(135deg, #059669 0%, #34d399 100%);
        color: #ffffff;
        box-shadow: 0 0 20px rgba(16, 185, 129, 0.6), inset 0 2px 4px rgba(255,255,255,0.3);
    }
    
    .badge-good {
        background: linear-gradient(135deg, #2563eb 0%, #60a5fa 100%);
        color: #ffffff;
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.6), inset 0 2px 4px rgba(255,255,255,0.3);
    }
    
    .badge-medium {
        background: linear-gradient(135deg, #d97706 0%, #fbbf24 100%);
        color: #ffffff;
        box-shadow: 0 0 20px rgba(245, 158, 11, 0.6), inset 0 2px 4px rgba(255,255,255,0.3);
    }
    
    .badge-maintenance {
        background: linear-gradient(135deg, #dc2626 0%, #f87171 100%);
        color: #ffffff;
        box-shadow: 0 0 20px rgba(239, 68, 68, 0.6), inset 0 2px 4px rgba(255,255,255,0.3);
    }
    
    .score-number {
        font-size: 4.2rem;
        font-weight: 900;
        line-height: 1;
        background: linear-gradient(135deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
        position: relative;
        z-index: 1;
    }

    .summary-box {
        background: rgba(255, 255, 255, 0.08);
        border-left: 5px solid #38bdf8;
        padding: 20px 24px;
        border-radius: 16px;
        font-size: 1.1rem;
        line-height: 1.8;
        color: #f1f5f9;
        margin-top: 24px;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        position: relative;
        z-index: 1;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* Action & Trade Badges */
    .action-buy {
        background: linear-gradient(135deg, #059669 0%, #10b981 100%);
        color: #ffffff;
        padding: 6px 16px;
        border-radius: 10px;
        font-weight: 700;
        font-size: 0.95rem;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
    }
    
    .action-sell {
        background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
        color: #ffffff;
        padding: 6px 16px;
        border-radius: 10px;
        font-weight: 700;
        font-size: 0.95rem;
        box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3);
    }

    .tip-box {
        background: linear-gradient(135deg, #fefce8 0%, #fef08a 100%);
        border: 1px solid #fde047;
        padding: 14px 18px;
        border-radius: 12px;
        color: #854d0e;
        font-size: 0.95rem;
        font-weight: 600;
        margin-top: 14px;
        box-shadow: 0 2px 10px rgba(253, 224, 71, 0.2);
    }
    
    /* Vernacular Callout Card */
    .vernacular-card {
        background: rgba(240, 249, 255, 0.85);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-left: 6px solid #0284c7;
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 24px;
        color: #0c4a6e;
        box-shadow: 0 8px 24px rgba(2, 132, 199, 0.08), 0 2px 8px rgba(2, 132, 199, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.6);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .vernacular-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 28px rgba(2, 132, 199, 0.12), 0 4px 12px rgba(2, 132, 199, 0.06);
    }
    .vernacular-card h5 {
        margin-top: 0;
        margin-bottom: 10px;
        color: #0369a1;
        font-weight: 800;
        font-size: 1.2rem;
        letter-spacing: 0.3px;
    }
    
    /* Dataframe overrides */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_vernacular_callout(topic: str) -> None:
    """Render plain-language educational callout box for finance concepts.

    Args:
        topic: Key in VERNACULAR_EXPLANATIONS ('PBSA', 'RBSA', 'Rolling_RBSA', 'CVaR', etc.)
    """
    info = VERNACULAR_EXPLANATIONS.get(topic)
    if not info:
        return

    st.markdown(
        f"""
        <div class="vernacular-card">
            <h5>{info['title']}</h5>
            <div>{info['content'].replace(chr(10), '<br>')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_health_score_card(diagnostic_res: Dict[str, Any]) -> None:
    """Render C-position panorama health score diagnostic card.

    Args:
        diagnostic_res: Result dict from HealthScoreEngine.calculate().
    """
    if not diagnostic_res or not isinstance(diagnostic_res, dict):
        st.warning("暂无全景诊断数据")
        return

    score = diagnostic_res.get("total_score", 100)
    level = diagnostic_res.get("level", "良")
    summary_text = diagnostic_res.get("summary_text", "")
    key_findings = diagnostic_res.get("key_findings", [])
    deductions = diagnostic_res.get("deductions", [])

    # Map level to CSS badge class
    level_css_map = {
        "优": "badge-excellent",
        "良": "badge-good",
        "中": "badge-medium",
        "需保养": "badge-maintenance",
    }
    badge_class = level_css_map.get(level, "badge-good")

    # Render Card HTML
    card_html = f"""
    <div class="health-card-container">
        <div class="health-header-row">
            <div>
                <span class="health-title">🧭 组合全景体检健康诊断</span>
            </div>
            <div>
                <span class="grade-badge {badge_class}">评级：{level}</span>
            </div>
        </div>
        <div style="display: flex; align-items: baseline; gap: 16px;">
            <div class="score-number">{score}</div>
            <div style="color: #94a3b8; font-size: 1.1rem; font-weight: 500;">/ 100 分 (综合7大维度算盘)</div>
        </div>
        <div class="summary-box">
            {summary_text.replace(chr(10), '<br>')}
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    # Score deduction expander
    if deductions:
        with st.expander("🔍 查看扣分项明细", expanded=False):
            df_ded = pd.DataFrame(deductions)
            df_ded.columns = ["诊断维度", "扣除分数", "扣分原因"]
            st.table(df_ded)


def render_rebalance_guide(rebalance_res: Dict[str, Any]) -> None:
    """Render intelligent rebalance guide, trade action items, and fee saving tips.

    Args:
        rebalance_res: Result dict from RebalanceEngine.calculate().
    """
    if not rebalance_res or not isinstance(rebalance_res, dict):
        st.info("当前组合无需调仓")
        return

    trade_actions = rebalance_res.get("trade_actions", [])
    net_benefit = rebalance_res.get("net_benefit", 0.0)
    trigger_reasons = rebalance_res.get("trigger_reasons", [])

    # Render Trigger Reasons
    if trigger_reasons:
        st.markdown("##### 🚨 调仓触发信号原因")
        for reason in trigger_reasons:
            st.info(f"• {reason}")

    # Render Expected Benefit Metric
    st.metric(
        label="预估年度扣除手续费后净收益提升",
        value=f"¥ {net_benefit:,.2f} 元",
        delta="正收益" if net_benefit >= 0 else "优化损耗",
    )

    # Render Trade Actions List
    if not trade_actions:
        st.success("🎉 当前组合配置符合最优二次规划目标，暂无需执行买卖调仓。")
        return

    st.markdown("##### 📋 建议具体买卖操作指南清单")

    for idx, item in enumerate(trade_actions, 1):
        action = item.get("action", "BUY")
        fund_code = item.get("fund_code", "")
        amount = item.get("amount", 0.0)
        fee_tip = item.get("fee_saved_tip", "")

        action_badge = (
            f'<span class="action-buy">买入 (BUY)</span>'
            if action == "BUY"
            else f'<span class="action-sell">卖出 (SELL)</span>'
        )

        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%); border: 1px solid #e2e8f0; border-radius: 16px; padding: 18px; margin-bottom: 14px; box-shadow: 0 4px 16px -2px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-weight: 700; font-size: 1.1rem; color: #0f172a; margin-right: 12px;">{idx}. 基金代码：{fund_code}</span>
                        {action_badge}
                    </div>
                    <div style="font-weight: 800; font-size: 1.25rem; color: #0f172a;">
                        金额：¥ {amount:,.2f} 元
                    </div>
                </div>
                {f'<div class="tip-box">💡 赎回避费小贴士：{fee_tip}</div>' if fee_tip else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_top_stocks_table(top_stocks_df: pd.DataFrame, top_n: int = 10) -> None:
    """Render top penetrated individual stock holdings table.

    Args:
        top_stocks_df: DataFrame output from PBSAEngine.calculate()['top_stocks'].
        top_n: Number of top stocks to display (default: 10).
    """
    if top_stocks_df is None or top_stocks_df.empty:
        st.warning("暂无持仓穿透个股数据")
        return

    df_display = top_stocks_df.head(top_n).copy()

    # Format columns for user display
    col_rename = {
        "stock_code": "股票代码",
        "stock_name": "股票名称",
        "broad_sector": "大类行业",
        "sector": "细分行业",
        "amount_per_100": "每百元持仓金额 (元)",
        "weight_pct": "组合穿透占比 (%)",
    }

    display_cols = [c for c in col_rename.keys() if c in df_display.columns]
    df_render = df_display[display_cols].rename(columns=col_rename)

    if "每百元持仓金额 (元)" in df_render.columns:
        df_render["每百元持仓金额 (元)"] = df_render["每百元持仓金额 (元)"].apply(lambda x: f"¥ {float(x):.2f}")
    if "组合穿透占比 (%)" in df_render.columns:
        df_render["组合穿透占比 (%)"] = df_render["组合穿透占比 (%)"].apply(lambda x: f"{float(x):.2f}%")

    st.dataframe(df_render, width="stretch")


def create_portfolio_treemap(drilldown_data: List[Dict[str, Any]]) -> Any:
    """Create a multi-level interactive Plotly Treemap for portfolio visualization.
    
    Args:
        drilldown_data: List of dicts with keys ['macro', 'sector', 'fund', 'stock', 'weight'].
        
    Returns:
        Plotly Figure object.
    """
    if not drilldown_data:
        return None
        
    df = pd.DataFrame(drilldown_data)
    
    # Premium vibrant color palette
    premium_colors = ['#00F0FF', '#FF0055', '#8A2BE2', '#FF7F00', '#00ffaa', '#ffe600', '#00bfff', '#ff1493']
    
    fig = px.treemap(
        df,
        path=[px.Constant("全景持仓 (Portfolio)"), 'macro', 'sector', 'fund', 'stock'],
        values='weight',
        color='macro',
        color_discrete_sequence=premium_colors,
        template='plotly_dark'
    )
    
    # Customize traces for a glassmorphism/modern feel
    fig.update_traces(
        textinfo="label+percent parent",
        textfont=dict(family="Inter, Roboto, sans-serif", size=16, color="white", weight="bold"),
        hovertemplate='<span style="font-size:18px; font-weight:bold;">%{label}</span><br><br>全局占比: %{value:.2f}%<br>在父级中占比: %{percentParent}<extra></extra>',
        marker=dict(
            line=dict(width=2, color='#0f172a'),
            pad=dict(t=35, l=4, r=4, b=4)
        ),
        pathbar=dict(
            visible=True,
            textfont=dict(family="Inter, Roboto, sans-serif", size=14, color="white"),
        ),
        root_color="#0f172a"
    )
    
    # High-end dark aesthetic layout
    fig.update_layout(
        margin=dict(t=20, l=10, r=10, b=10),
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        hoverlabel=dict(
            bgcolor="rgba(15, 23, 42, 0.8)",
            bordercolor="rgba(255, 255, 255, 0.2)",
            font=dict(family="Inter, sans-serif", size=14, color="white")
        ),
        height=600
    )
    
    return fig


def render_risk_profile_card(
    risk_profile: str,
    cvar_95: float,
    max_drawdown: float = 0.0
) -> None:
    """Render plain-language retail investor risk profiling card (保守型 / 稳健型 / 积极型).

    Args:
        risk_profile: Profile category string ('保守型', '稳健型', '积极型', or custom).
        cvar_95: Portfolio 95% CVaR value (decimal or percentage).
        max_drawdown: Portfolio Maximum Drawdown value (decimal or percentage).
    """
    if not isinstance(risk_profile, str) or not risk_profile.strip():
        risk_profile = "稳健型"

    try:
        cvar_val = float(cvar_95) if cvar_95 is not None else 0.0
        if np.isnan(cvar_val) or np.isinf(cvar_val):
            cvar_val = 0.0
    except (ValueError, TypeError):
        cvar_val = 0.0

    try:
        mdd_val = float(max_drawdown) if max_drawdown is not None else 0.0
        if np.isnan(mdd_val) or np.isinf(mdd_val):
            mdd_val = 0.0
    except (ValueError, TypeError):
        mdd_val = 0.0

    cvar_pct = cvar_val * 100.0 if abs(cvar_val) <= 1.0 else cvar_val
    mdd_pct = mdd_val * 100.0 if abs(mdd_val) <= 1.0 else mdd_val

    profiles_data = {
        "保守型": {
            "title": "🛡️ 保守型投资者画像 (低风险·本金安全优先)",
            "color": "#059669",
            "border_color": "#10b981",
            "bg_color": "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)",
            "traits": "追求本金极度安全与低波动，无法忍受较大暂性回撤，偏好稳定收益。",
            "thresholds": "建议 95% CVaR 风险 < 5%，历史最大回撤控制在 8% 以内。",
            "advice": "💡 白话指南：适合配置固收+、货币基金及高股息大盘价值资产，切忌盲目追高高估值赛道。"
        },
        "稳健型": {
            "title": "⚖️ 稳健型投资者画像 (中风险·平衡增值)",
            "color": "#2563eb",
            "border_color": "#3b82f6",
            "bg_color": "linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)",
            "traits": "追求风险与收益的有机平衡，能接受适度波动以换取中长期稳健资本增值。",
            "thresholds": "建议 95% CVaR 风险 < 15%，历史最大回撤控制在 18% 以内。",
            "advice": "💡 白话指南：推荐股债均衡多资产配置，通过风格穿透防止隐形抱团，定期动态再平衡锁住收益。"
        },
        "积极型": {
            "title": "🚀 积极型投资者画像 (高风险·资本长远高增值)",
            "color": "#dc2626",
            "border_color": "#ef4444",
            "bg_color": "linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%)",
            "traits": "追求高额资本增值，具备强风险承受能力与长期投资周期，能接纳较大幅度净值回撤。",
            "thresholds": "95% CVaR 容忍度可达 25%+，最大回撤容忍度通常 > 25%。",
            "advice": "💡 白话指南：可重点布局高弹性成长股与行业主题基金，但需做好黑天鹅极端压力测试，严防尾部风险。"
        }
    }

    profile_key = "稳健型"
    for k in profiles_data.keys():
        if k in risk_profile:
            profile_key = k
            break

    prof = profiles_data[profile_key]

    card_html = f"""
    <div style="background: {prof['bg_color']}; border-left: 6px solid {prof['border_color']}; border-radius: 16px; padding: 24px; margin-bottom: 24px; box-shadow: 0 4px 16px rgba(0,0,0,0.05);">
        <h4 style="margin-top:0; color: {prof['color']}; font-weight: 800; font-size: 1.25rem;">{prof['title']}</h4>
        <p style="margin: 8px 0; color: #1e293b; font-size: 1.0rem;"><b>投资者特征:</b> {prof['traits']}</p>
        <p style="margin: 8px 0; color: #1e293b; font-size: 1.0rem;"><b>损失耐受阀值:</b> {prof['thresholds']}</p>
        <div style="display: flex; gap: 24px; margin: 16px 0; background: rgba(255,255,255,0.7); padding: 12px 16px; border-radius: 12px; border: 1px solid rgba(0,0,0,0.05);">
            <div><span style="color: #64748b; font-size: 0.9rem;">当前组合 95% CVaR 风险:</span> <b style="color: #0f172a; font-size: 1.1rem;">{cvar_pct:.2f}%</b></div>
            <div><span style="color: #64748b; font-size: 0.9rem;">当前组合 最大回撤 (MDD):</span> <b style="color: #0f172a; font-size: 1.1rem;">{mdd_pct:.2f}%</b></div>
        </div>
        <div style="margin-top: 12px; color: #334155; font-weight: 600; font-size: 0.95rem;">{prof['advice']}</div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def render_rmb_loss_simulation(
    portfolio_value: float,
    cvar_95: float,
    cvar_99: float = 0.0
) -> None:
    """Render intuitive RMB loss simulation cards converting statistical parameters to financial figures.

    Args:
        portfolio_value: Total portfolio value in RMB (float).
        cvar_95: 95% CVaR loss ratio (float, decimal or percentage).
        cvar_99: 99% CVaR loss ratio (float, decimal or percentage).
    """
    try:
        p_val = float(portfolio_value) if portfolio_value is not None else 0.0
        if np.isnan(p_val) or np.isinf(p_val) or p_val < 0:
            p_val = 0.0
    except (ValueError, TypeError):
        p_val = 0.0

    try:
        cvar95_val = float(cvar_95) if cvar_95 is not None else 0.0
        if np.isnan(cvar95_val) or np.isinf(cvar95_val):
            cvar95_val = 0.0
    except (ValueError, TypeError):
        cvar95_val = 0.0

    try:
        cvar99_val = float(cvar_99) if cvar_99 is not None else 0.0
        if np.isnan(cvar99_val) or np.isinf(cvar99_val):
            cvar99_val = 0.0
    except (ValueError, TypeError):
        cvar99_val = 0.0

    cvar95_ratio = cvar95_val / 100.0 if abs(cvar95_val) > 1.0 else cvar95_val
    cvar99_ratio = cvar99_val / 100.0 if abs(cvar99_val) > 1.0 else cvar99_val

    cvar95_ratio = abs(cvar95_ratio)
    cvar99_ratio = abs(cvar99_ratio)

    loss_95_amt = p_val * cvar95_ratio
    loss_99_amt = p_val * cvar99_ratio

    st.markdown("#### 💰 人民币真实亏损情景模拟算盘")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="当前持仓总资产规模",
            value=f"¥ {p_val:,.2f} 元",
            help="计算亏损模拟的基本盘总计本金"
        )
    with col2:
        st.metric(
            label="95% 极端概率下预估亏损金额",
            value=f"¥ {loss_95_amt:,.2f} 元",
            delta=f"-{cvar95_ratio * 100.0:.2f}%",
            delta_color="inverse",
            help="在 95% 置信水平下，极端下行行情中预估的最大平均本金亏损"
        )
    with col3:
        st.metric(
            label="99% 黑天鹅剧烈暴跌下预估亏损",
            value=f"¥ {loss_99_amt:,.2f} 元" if cvar99_ratio > 0 else "未评估 / 0.00 元",
            delta=f"-{cvar99_ratio * 100.0:.2f}%" if cvar99_ratio > 0 else None,
            delta_color="inverse",
            help="在 99% 置信水平下（百年一遇极端踩踏），预估的最大本金损失"
        )

    st.markdown(
        f"""
        <div class="tip-box" style="margin-top: 12px; background: #fffbe6; border-color: #ffe58f; color: #873800;">
            💡 <b>白话换算视角:</b> 以您的 <b>¥ {p_val:,.0f} 元</b> 总投资计算，在 95% 概率的最坏 5% 交易日里，
            预计平均损失约 <b>¥ {loss_95_amt:,.2f} 元</b>。
            {f'在 99% 极度恶化场景下，预计损失可达 <b>¥ {loss_99_amt:,.2f} 元</b>。' if cvar99_ratio > 0 else ''}
        </div>
        """,
        unsafe_allow_html=True
    )
