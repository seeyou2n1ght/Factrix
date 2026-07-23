"""Unit and Integration Tests for UI Components, Plotly Charts, and app.py.

Verifies that:
1. components.py functions run safely without exceptions.
2. charts.py plotly figure generators return valid go.Figure objects.
3. app.py loads, analyzes sample fund list, and integrates all 7 engines without error.
"""

from pathlib import Path
import pytest
import pandas as pd
import plotly.graph_objects as go

from src.ui.components import (
    set_global_css,
    render_vernacular_callout,
    render_health_score_card,
    render_rebalance_guide,
    render_top_stocks_table,
    render_risk_profile_card,
    render_rmb_loss_simulation,
)
from src.ui.charts import (
    create_overlap_heatmap,
    create_macro_asset_pie,
    create_sector_pie,
    create_style_radar,
    create_style_drift_line,
    create_cvar_stress_bar,
    create_prospect_bubble,
    create_rebalance_bar,
    create_risk_gauge_chart,
    create_alpha_beta_scatter,
)
import app


# --- Test UI Components ---

def test_set_global_css():
    """Verify set_global_css executes cleanly."""
    try:
        set_global_css()
    except Exception as e:
        pytest.fail(f"set_global_css raised unexpected exception: {e}")


def test_render_vernacular_callout():
    """Verify render_vernacular_callout handles valid and invalid topics."""
    for topic in ["PBSA", "RBSA", "Rolling_RBSA", "CVaR", "Prospect_Theory", "Rebalance"]:
        render_vernacular_callout(topic)
    # Invalid topic should handle gracefully
    render_vernacular_callout("INVALID_TOPIC")


def test_render_health_score_card():
    """Verify render_health_score_card renders with valid data and empty input."""
    sample_health_res = {
        "total_score": 85,
        "health_score": 85,
        "level": "良",
        "summary_text": "您的组合全景诊断得分为【85分】，持仓整体稳健。",
        "key_findings": ["第一大重仓股集中度适中"],
        "deductions": [{"诊断维度": "持仓穿透", "扣除分数": -5, "扣分原因": "测试扣分"}],
    }
    render_health_score_card(sample_health_res)
    render_health_score_card({})


def test_render_rebalance_guide():
    """Verify render_rebalance_guide renders trade actions and empty list."""
    sample_rebalance_res = {
        "trade_actions": [
            {"action": "BUY", "fund_code": "000001", "amount": 5000.0, "fee_saved_tip": ""},
            {"action": "SELL", "fund_code": "000002", "amount": 5000.0, "fee_saved_tip": "建议再持有2天避开惩罚费率"},
        ],
        "net_benefit": 250.0,
        "trigger_reasons": ["夏普比率显著衰减"],
    }
    render_rebalance_guide(sample_rebalance_res)
    render_rebalance_guide({"trade_actions": [], "net_benefit": 0.0, "trigger_reasons": []})


def test_render_top_stocks_table():
    """Verify render_top_stocks_table handles valid DataFrame and empty input."""
    df_stocks = pd.DataFrame([
        {"stock_code": "600519", "stock_name": "贵州茅台", "broad_sector": "大消费", "sector": "食品饮料", "amount_per_100": 8.5, "weight_pct": 8.5},
        {"stock_code": "0700", "stock_name": "腾讯控股", "broad_sector": "科技制造", "sector": "软件与服务", "amount_per_100": 6.2, "weight_pct": 6.2},
    ])
    render_top_stocks_table(df_stocks, top_n=10)
    render_top_stocks_table(pd.DataFrame())


# --- Test Plotly Chart Generators ---

def test_create_overlap_heatmap():
    """Verify create_overlap_heatmap returns a valid go.Figure."""
    df_overlap = pd.DataFrame(
        [[1.0, 0.45], [0.45, 1.0]],
        index=["000001", "000002"],
        columns=["000001", "000002"],
    )
    fig = create_overlap_heatmap(df_overlap)
    assert isinstance(fig, go.Figure)

    fig_empty = create_overlap_heatmap(pd.DataFrame())
    assert isinstance(fig_empty, go.Figure)


def test_create_macro_asset_pie():
    """Verify create_macro_asset_pie returns a valid go.Figure for both dict and native PBSA pd.Series inputs."""
    macro_dict = {
        "股票资产": 75.0,
        "债券资产": 15.0,
        "现金货基": 6.0,
        "其他资产": 4.0,
    }
    fig = create_macro_asset_pie(macro_dict)
    assert isinstance(fig, go.Figure)

    macro_series = pd.Series({"Equity": 80.0, "Fixed Income": 10.0, "Commodity": 5.0, "Cash": 5.0})
    fig_series = create_macro_asset_pie(macro_series)
    assert isinstance(fig_series, go.Figure)

    fig_empty = create_macro_asset_pie({})
    assert isinstance(fig_empty, go.Figure)


def test_create_sector_pie():
    """Verify create_sector_pie returns a valid go.Figure."""
    sec_series = pd.Series({
        "科技制造": 35.0,
        "大消费": 25.0,
        "医药健康": 20.0,
        "大金融": 10.0,
        "周期资源": 10.0,
    })
    fig = create_sector_pie(sec_series, renormalized=True)
    assert isinstance(fig, go.Figure)

    fig_empty = create_sector_pie(pd.Series(dtype=float))
    assert isinstance(fig_empty, go.Figure)


def test_create_style_radar():
    """Verify create_style_radar returns a valid go.Figure."""
    style_dict = {
        "large_value": 0.35,
        "large_growth": 0.25,
        "small_value": 0.15,
        "small_growth": 0.15,
        "bond_index": 0.10,
    }
    fig = create_style_radar(style_dict)
    assert isinstance(fig, go.Figure)

    fig_empty = create_style_radar({})
    assert isinstance(fig_empty, go.Figure)


def test_create_style_drift_line():
    """Verify create_style_drift_line returns a valid go.Figure."""
    dates = pd.date_range("2026-01-01", periods=10, freq="B").strftime("%Y-%m-%d")
    rolling_df = pd.DataFrame(
        0.2,
        index=dates,
        columns=["large_value", "large_growth", "small_value", "small_growth", "bond_index"],
    )
    fig = create_style_drift_line(rolling_df)
    assert isinstance(fig, go.Figure)

    fig_empty = create_style_drift_line(pd.DataFrame())
    assert isinstance(fig_empty, go.Figure)


def test_create_cvar_stress_bar():
    """Verify create_cvar_stress_bar returns a valid go.Figure."""
    stress_dict = {
        "2015_equity_crash": {
            "scenario_name": "2015年股市踩踏",
            "description": "模拟大跌",
            "loss_pct": 0.28,
            "loss_amount": 28000.0,
        },
        "2022_dual_crash": {
            "scenario_name": "2022年股债双杀",
            "description": "模拟双杀",
            "loss_pct": 0.12,
            "loss_amount": 12000.0,
        },
    }
    fig = create_cvar_stress_bar(stress_dict)
    assert isinstance(fig, go.Figure)

    fig_empty = create_cvar_stress_bar({})
    assert isinstance(fig_empty, go.Figure)


def test_create_prospect_bubble():
    """Verify create_prospect_bubble returns a valid go.Figure."""
    fig = create_prospect_bubble(win_rate=0.62, payoff_ratio=1.45, prospect_utility=0.002, omega_ratio=1.35)
    assert isinstance(fig, go.Figure)


def test_create_rebalance_bar():
    """Verify create_rebalance_bar returns a valid go.Figure."""
    trade_actions = [
        {"action": "BUY", "fund_code": "000001", "amount": 6000.0},
        {"action": "SELL", "fund_code": "000002", "amount": 6000.0},
    ]
    fig = create_rebalance_bar(trade_actions)
    assert isinstance(fig, go.Figure)

    fig_empty = create_rebalance_bar([])
    assert isinstance(fig_empty, go.Figure)


def test_render_risk_profile_card():
    """Verify render_risk_profile_card runs safely for various profile types and edge cases."""
    render_risk_profile_card(risk_profile="保守型", cvar_95=0.04, max_drawdown=0.07)
    render_risk_profile_card(risk_profile="稳健型", cvar_95=0.12, max_drawdown=0.15)
    render_risk_profile_card(risk_profile="积极型", cvar_95=0.22, max_drawdown=0.28)
    render_risk_profile_card(risk_profile=None, cvar_95=None, max_drawdown=None)


def test_render_rmb_loss_simulation():
    """Verify render_rmb_loss_simulation runs safely for valid and edge case inputs."""
    render_rmb_loss_simulation(portfolio_value=100000.0, cvar_95=0.08, cvar_99=0.15)
    render_rmb_loss_simulation(portfolio_value=0.0, cvar_95=0.0, cvar_99=0.0)
    render_rmb_loss_simulation(portfolio_value=None, cvar_95=None, cvar_99=None)


def test_create_risk_gauge_chart():
    """Verify create_risk_gauge_chart returns a valid go.Figure."""
    fig = create_risk_gauge_chart(risk_score=55.0, risk_level="稳健型")
    assert isinstance(fig, go.Figure)

    fig_empty = create_risk_gauge_chart(risk_score=None)
    assert isinstance(fig_empty, go.Figure)


def test_create_alpha_beta_scatter():
    """Verify create_alpha_beta_scatter returns a valid go.Figure."""
    data = [{"market_return": 0.01, "portfolio_return": 0.012}]
    fig = create_alpha_beta_scatter(data, alpha=0.02, beta=1.05)
    assert isinstance(fig, go.Figure)

    fig_empty = create_alpha_beta_scatter([])
    assert isinstance(fig_empty, go.Figure)


# --- Test App Main Integration ---

def test_app_import():
    """Verify app.py loads cleanly without syntax or import errors."""
    assert hasattr(app, "load_and_analyze_data")
    assert hasattr(app, "main")


def test_app_load_and_analyze_data(sample_fundlist_path: str):
    """Verify app.load_and_analyze_data parses sample CSV and computes all engine results including AlphaBetaEngine."""
    res = app.load_and_analyze_data(sample_fundlist_path)

    assert "df_funds" in res
    assert "total_value" in res
    assert "pbsa_res" in res
    assert "rbsa_res" in res
    assert "rolling_res" in res
    assert "cvar_res" in res
    assert "prospect_res" in res
    assert "rebalance_res" in res
    assert "health_res" in res
    assert "alpha_beta_res" in res

    # Verify Health score output
    health_res = res["health_res"]
    assert "total_score" in health_res
    assert 0 <= health_res["total_score"] <= 100
    assert "level" in health_res
    assert "summary_text" in health_res

    # Verify AlphaBetaEngine output and required keys
    ab_res = res["alpha_beta_res"]
    assert "portfolio_alpha" in ab_res
    assert "portfolio_beta" in ab_res
    assert "sharpe_ratio" in ab_res
    assert "scatter_data" in ab_res
    assert isinstance(ab_res["scatter_data"], list)


def test_app_alpha_beta_res_keys(sample_fundlist_path: str):
    """Ensure alpha_beta_res is returned in load_and_analyze_data output with required keys."""
    res = app.load_and_analyze_data(sample_fundlist_path)
    assert "alpha_beta_res" in res
    ab_res = res["alpha_beta_res"]
    for key in ["portfolio_alpha", "portfolio_beta", "sharpe_ratio", "scatter_data"]:
        assert key in ab_res, f"Required key '{key}' missing from alpha_beta_res dict"

