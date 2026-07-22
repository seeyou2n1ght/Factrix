"""UI Components module for Factrix Streamlit dashboard.

Provides custom CSS injections, panorama health diagnostic cards, plain-language (vernacular)
educational callouts, rebalance trade action guides, and stock penetration tables.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import streamlit as st


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
    /* Main layout & background styling */
    .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* Panorama Health Diagnostic Card Container */
    .health-card-container {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 16px;
        padding: 24px;
        color: #f8fafc;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        margin-bottom: 24px;
        border: 1px solid #334155;
    }
    
    .health-header-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
    }
    
    .health-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #e2e8f0;
        margin: 0;
    }
    
    /* Grade Color Badges */
    .grade-badge {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 1.2rem;
        font-weight: 800;
        text-align: center;
    }
    
    .badge-excellent {
        background-color: #059669;
        color: #ffffff;
        box-shadow: 0 0 12px rgba(16, 185, 129, 0.4);
    }
    
    .badge-good {
        background-color: #2563eb;
        color: #ffffff;
        box-shadow: 0 0 12px rgba(59, 130, 246, 0.4);
    }
    
    .badge-medium {
        background-color: #d97706;
        color: #ffffff;
        box-shadow: 0 0 12px rgba(245, 158, 11, 0.4);
    }
    
    .badge-maintenance {
        background-color: #dc2626;
        color: #ffffff;
        box-shadow: 0 0 12px rgba(239, 68, 68, 0.4);
    }
    
    .score-number {
        font-size: 3rem;
        font-weight: 900;
        line-height: 1;
        background: linear-gradient(90deg, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .summary-box {
        background-color: rgba(255, 255, 255, 0.05);
        border-left: 4px solid #38bdf8;
        padding: 14px 18px;
        border-radius: 6px;
        font-size: 1.05rem;
        line-height: 1.6;
        color: #f1f5f9;
        margin-top: 16px;
        margin-bottom: 16px;
    }
    
    /* Action & Trade Badges */
    .action-buy {
        background-color: #10b981;
        color: #ffffff;
        padding: 4px 12px;
        border-radius: 6px;
        font-weight: 700;
    }
    
    .action-sell {
        background-color: #ef4444;
        color: #ffffff;
        padding: 4px 12px;
        border-radius: 6px;
        font-weight: 700;
    }

    .tip-box {
        background-color: #fffbe6;
        border: 1px solid #ffe58f;
        padding: 10px 14px;
        border-radius: 8px;
        color: #8c6b00;
        font-size: 0.95rem;
        margin-top: 6px;
    }
    
    /* Vernacular Callout Card */
    .vernacular-card {
        background-color: #f0f9ff;
        border-left: 5px solid #0284c7;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 20px;
        color: #0c4a6e;
    }
    .vernacular-card h5 {
        margin-top: 0;
        margin-bottom: 8px;
        color: #0369a1;
        font-weight: 700;
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
            <div style="color: #94a3b8; font-size: 1.1rem;">/ 100 分 (综合7大维度算盘)</div>
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
            <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-weight: 700; font-size: 1.1rem; color: #1e293b; margin-right: 12px;">{idx}. 基金代码：{fund_code}</span>
                        {action_badge}
                    </div>
                    <div style="font-weight: 800; font-size: 1.2rem; color: #0f172a;">
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

    st.dataframe(df_render, use_container_width=True)
