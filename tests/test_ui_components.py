"""Unit Test Suite for Milestone 2 UI Components and Plotly Chart Extensions.

Tests:
1. create_risk_gauge_chart (normal inputs, color bands, None, NaN, out-of-bound scores).
2. create_alpha_beta_scatter (normal returns pairs, regression line, empty, invalid dicts, NaN/None metrics).
3. render_risk_profile_card (conservative/balanced/aggressive profiles, fallback, None/NaN inputs).
4. render_rmb_loss_simulation (RMB conversion, percentage vs decimal inputs, zero/negative portfolio values, None/NaN inputs).
"""

import pytest
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.ui.charts import (
    create_risk_gauge_chart,
    create_alpha_beta_scatter,
)
from src.ui.components import (
    render_risk_profile_card,
    render_rmb_loss_simulation,
)


# --- Tests for create_risk_gauge_chart ---

def test_create_risk_gauge_chart_normal():
    """Verify create_risk_gauge_chart with valid normal inputs."""
    fig = create_risk_gauge_chart(risk_score=45.0, risk_level="中风险")
    assert isinstance(fig, go.Figure)
    assert "组合风险综合评估仪表盘" in fig.layout.title.text
    assert "中风险" in fig.layout.title.text


def test_create_risk_gauge_chart_risk_bands():
    """Verify gauge chart handles low (conservative), medium (balanced), and high (aggressive) risk scores."""
    fig_low = create_risk_gauge_chart(risk_score=15.0, risk_level="保守型")
    assert isinstance(fig_low, go.Figure)

    fig_mid = create_risk_gauge_chart(risk_score=50.0, risk_level="稳健型")
    assert isinstance(fig_mid, go.Figure)

    fig_high = create_risk_gauge_chart(risk_score=85.0, risk_level="高风险")
    assert isinstance(fig_high, go.Figure)


def test_create_risk_gauge_chart_edge_cases():
    """Verify create_risk_gauge_chart handles None, NaN, string, and out-of-bound values safely."""
    # None input
    fig_none = create_risk_gauge_chart(risk_score=None)
    assert isinstance(fig_none, go.Figure)

    # NaN input
    fig_nan = create_risk_gauge_chart(risk_score=float('nan'))
    assert isinstance(fig_nan, go.Figure)

    # Invalid non-numeric string input
    fig_str = create_risk_gauge_chart(risk_score="invalid_score")
    assert isinstance(fig_str, go.Figure)

    # Out of bounds scores (<0 and >100)
    fig_neg = create_risk_gauge_chart(risk_score=-20.0)
    assert isinstance(fig_neg, go.Figure)

    fig_over = create_risk_gauge_chart(risk_score=150.0)
    assert isinstance(fig_over, go.Figure)


# --- Tests for create_alpha_beta_scatter ---

def test_create_alpha_beta_scatter_normal():
    """Verify create_alpha_beta_scatter with valid scatter data list."""
    scatter_data = [
        {"market_return": 0.01, "portfolio_return": 0.012},
        {"market_return": -0.005, "portfolio_return": -0.006},
        {"market_return": 0.02, "portfolio_return": 0.022},
        {"market_return": -0.01, "portfolio_return": -0.008},
    ]
    fig = create_alpha_beta_scatter(scatter_data, alpha=0.04, beta=1.15)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2  # Scatter markers + Regression line trace


def test_create_alpha_beta_scatter_edge_cases():
    """Verify create_alpha_beta_scatter handles empty lists, invalid dict keys, NaN/None parameters gracefully."""
    # Empty scatter data
    fig_empty = create_alpha_beta_scatter([], alpha=0.0, beta=1.0)
    assert isinstance(fig_empty, go.Figure)

    # None scatter data
    fig_none = create_alpha_beta_scatter(None, alpha=0.0, beta=1.0)
    assert isinstance(fig_none, go.Figure)

    # Malformed scatter data list
    bad_data = [
        {"wrong_key": 123},
        {"market_return": "invalid"},
        {"market_return": float('nan'), "portfolio_return": 0.01},
    ]
    fig_bad = create_alpha_beta_scatter(bad_data, alpha=0.0, beta=1.0)
    assert isinstance(fig_bad, go.Figure)

    # Valid data with None / NaN alpha/beta
    valid_data = [{"market_return": 0.01, "portfolio_return": 0.015}]
    fig_nan_metrics = create_alpha_beta_scatter(valid_data, alpha=None, beta=float('nan'))
    assert isinstance(fig_nan_metrics, go.Figure)


# --- Tests for render_risk_profile_card ---

def test_render_risk_profile_card_normal():
    """Verify render_risk_profile_card executes without exception for conservative, balanced, aggressive profiles."""
    for profile in ["保守型", "稳健型", "积极型"]:
        render_risk_profile_card(risk_profile=profile, cvar_95=0.12, max_drawdown=0.18)


def test_render_risk_profile_card_edge_cases():
    """Verify render_risk_profile_card handles unknown profile strings, empty strings, None, and NaN parameters."""
    # Unknown or empty profile strings
    render_risk_profile_card(risk_profile="", cvar_95=0.10, max_drawdown=0.15)
    render_risk_profile_card(risk_profile="自定义超高风险", cvar_95=0.25, max_drawdown=0.30)

    # None and NaN numerical inputs
    render_risk_profile_card(risk_profile="稳健型", cvar_95=None, max_drawdown=None)
    render_risk_profile_card(risk_profile="保守型", cvar_95=float('nan'), max_drawdown=float('nan'))

    # Percentage scale inputs (e.g. 12.5 instead of 0.125)
    render_risk_profile_card(risk_profile="稳健型", cvar_95=12.5, max_drawdown=18.0)


# --- Tests for render_rmb_loss_simulation ---

def test_render_rmb_loss_simulation_normal():
    """Verify render_rmb_loss_simulation executes cleanly for typical RMB portfolio values."""
    render_rmb_loss_simulation(portfolio_value=100000.0, cvar_95=0.08, cvar_99=0.15)
    render_rmb_loss_simulation(portfolio_value=500000.0, cvar_95=8.0, cvar_99=15.0)


def test_render_rmb_loss_simulation_edge_cases():
    """Verify render_rmb_loss_simulation handles zero, negative, None, and NaN inputs safely."""
    # Zero and negative portfolio values
    render_rmb_loss_simulation(portfolio_value=0.0, cvar_95=0.05, cvar_99=0.10)
    render_rmb_loss_simulation(portfolio_value=-10000.0, cvar_95=0.05, cvar_99=0.10)

    # None and NaN parameters
    render_rmb_loss_simulation(portfolio_value=None, cvar_95=None, cvar_99=None)
    render_rmb_loss_simulation(portfolio_value=100000.0, cvar_95=float('nan'), cvar_99=float('nan'))


def test_adversarial_extreme_values():
    """Adversarial stress-testing for Inf, -Inf, giant RMB amounts, single-element scatter, and invalid types."""
    # 1. Giant RMB amounts (e.g. 1 Trillion / 1 Quadrillion RMB) and Inf values
    render_rmb_loss_simulation(portfolio_value=1e15, cvar_95=0.15, cvar_99=0.30)
    render_rmb_loss_simulation(portfolio_value=float('inf'), cvar_95=float('inf'), cvar_99=-float('inf'))

    # 2. Risk gauge chart Inf / -Inf and extreme out-of-bounds
    fig_inf = create_risk_gauge_chart(risk_score=float('inf'))
    assert isinstance(fig_inf, go.Figure)
    fig_neginf = create_risk_gauge_chart(risk_score=-float('inf'))
    assert isinstance(fig_neginf, go.Figure)

    # 3. Single-item scatter data and Inf/NaN alpha/beta
    scatter_single = [{"market_return": 0.05, "portfolio_return": 0.08}]
    fig_single = create_alpha_beta_scatter(scatter_single, alpha=float('inf'), beta=-float('inf'))
    assert isinstance(fig_single, go.Figure)

    # 4. Risk profile card with Inf / -Inf and unexpected profile types
    render_risk_profile_card(risk_profile=None, cvar_95=float('inf'), max_drawdown=-float('inf'))
    render_risk_profile_card(risk_profile=12345, cvar_95=-0.50, max_drawdown=-0.80)

