"""Adversarial Stress Test Harness for Milestone 2 UI & Chart Components.

This suite stress-tests create_risk_gauge_chart, create_alpha_beta_scatter,
render_risk_profile_card, and render_rmb_loss_simulation with extreme values:
NaN, Inf, negative values, empty lists, giant numbers (e.g. 1e308 RMB),
type mismatches, and boundary edge cases.
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


class TestRiskGaugeChartAdversarial:
    """Stress tests for create_risk_gauge_chart."""

    @pytest.mark.parametrize("score", [
        None,
        float("nan"),
        float("inf"),
        float("-inf"),
        "invalid_string",
        "",
        [],
        {},
        -100.0,
        -0.001,
        0.0,
        30.0,
        30.0001,
        70.0,
        70.0001,
        100.0,
        150.0,
        1e6,
        1e308,
        True,
        False,
    ])
    def test_extreme_risk_scores(self, score):
        """Verify gauge chart handles all extreme/invalid risk scores without throwing exceptions."""
        fig = create_risk_gauge_chart(risk_score=score, risk_level="测试风险")
        assert isinstance(fig, go.Figure)

    @pytest.mark.parametrize("level", [
        None,
        123,
        "",
        "   ",
        "<script>alert('xss')</script>",
        "保守型",
        "稳健型",
        "积极型",
        "超长风险等级描述" * 100,
    ])
    def test_extreme_risk_levels(self, level):
        """Verify gauge chart handles various risk level string inputs."""
        fig = create_risk_gauge_chart(risk_score=50.0, risk_level=level)
        assert isinstance(fig, go.Figure)


class TestAlphaBetaScatterAdversarial:
    """Stress tests for create_alpha_beta_scatter."""

    @pytest.mark.parametrize("scatter_data", [
        None,
        [],
        "not_a_list",
        123,
        [{"wrong_key": 1}],
        [{"market_return": "invalid", "portfolio_return": 0.01}],
        [{"market_return": float("nan"), "portfolio_return": 0.01}],
        [{"market_return": float("inf"), "portfolio_return": 0.01}],
        [{"market_return": 0.01, "portfolio_return": float("-inf")}],
        [{"market_return": None, "portfolio_return": 0.01}],
        # Single point data
        [{"market_return": 0.01, "portfolio_return": 0.02}],
        # Zero variance (all points identical)
        [{"market_return": 0.0, "portfolio_return": 0.0}] * 10,
        # Normal data
        [
            {"market_return": 0.01, "portfolio_return": 0.012},
            {"market_return": -0.02, "portfolio_return": -0.018},
        ],
    ])
    def test_scatter_data_edge_cases(self, scatter_data):
        """Verify alpha/beta scatter plot handles invalid/extreme scatter data gracefully."""
        fig = create_alpha_beta_scatter(scatter_data, alpha=0.05, beta=1.1)
        assert isinstance(fig, go.Figure)

    @pytest.mark.parametrize("alpha_val", [
        None, float("nan"), float("inf"), float("-inf"), "abc", 0.0, -0.1, 0.5, 1e5, 1e300, -1e300
    ])
    @pytest.mark.parametrize("beta_val", [
        None, float("nan"), float("inf"), float("-inf"), "abc", 0.0, -1.5, 1.0, 2.5, 1e5, 1e300, -1e300
    ])
    def test_scatter_metrics_extreme_values(self, alpha_val, beta_val):
        """Verify alpha/beta scatter plot handles extreme alpha and beta parameters."""
        valid_data = [
            {"market_return": 0.01, "portfolio_return": 0.012},
            {"market_return": -0.01, "portfolio_return": -0.008},
        ]
        # Expect figure creation without uncaught OverflowError or TypeError
        try:
            fig = create_alpha_beta_scatter(valid_data, alpha=alpha_val, beta=beta_val)
            assert isinstance(fig, go.Figure)
        except OverflowError:
            pytest.fail(f"create_alpha_beta_scatter raised uncaught OverflowError for alpha={alpha_val}, beta={beta_val}")

    def test_giant_float_overflow_in_scatter_data(self):
        """Verify giant float values in scatter data do not trigger unhandled OverflowError."""
        giant_data = [
            {"market_return": 1e150, "portfolio_return": 1e150},
            {"market_return": 2e150, "portfolio_return": 2e150},
        ]
        try:
            fig = create_alpha_beta_scatter(giant_data, alpha=1e150, beta=1e150)
            assert isinstance(fig, go.Figure)
        except OverflowError:
            pytest.fail("create_alpha_beta_scatter raised uncaught OverflowError on giant float inputs.")


class TestRiskProfileCardAdversarial:
    """Stress tests for render_risk_profile_card."""

    @pytest.mark.parametrize("profile", [
        None,
        "",
        "   ",
        123,
        "保守型",
        "稳健型",
        "积极型",
        "未知自定义类型",
        "🛡️ 保守型 (特殊符号)",
    ])
    @pytest.mark.parametrize("cvar", [
        None, float("nan"), float("inf"), float("-inf"), "invalid", -0.1, 0.0, 0.05, 1.0, 1.000001, 5.0, 100.0, 1e300
    ])
    @pytest.mark.parametrize("mdd", [
        None, float("nan"), float("inf"), float("-inf"), "invalid", -0.2, 0.0, 0.15, 1.0, 15.0, 100.0, 1e300
    ])
    def test_render_risk_profile_card_robustness(self, profile, cvar, mdd):
        """Verify render_risk_profile_card handles all parameter variations without exception."""
        render_risk_profile_card(risk_profile=profile, cvar_95=cvar, max_drawdown=mdd)


class TestRMBLossSimulationAdversarial:
    """Stress tests for render_rmb_loss_simulation."""

    @pytest.mark.parametrize("pval", [
        None, float("nan"), float("inf"), float("-inf"), "invalid", -100000.0, -1.0, 0.0, 1.0, 100000.0, 1e8, 1e15, 1e308
    ])
    @pytest.mark.parametrize("cvar95", [
        None, float("nan"), float("inf"), float("-inf"), "invalid", -0.05, 0.0, 0.05, 1.0, 1.01, 5.0, 100.0, 200.0
    ])
    @pytest.mark.parametrize("cvar99", [
        None, float("nan"), float("inf"), float("-inf"), "invalid", -0.10, 0.0, 0.10, 1.0, 1.01, 10.0, 100.0, 200.0
    ])
    def test_render_rmb_loss_simulation_robustness(self, pval, cvar95, cvar99):
        """Verify render_rmb_loss_simulation handles extreme RMB amounts and CVaR ratios safely."""
        try:
            render_rmb_loss_simulation(portfolio_value=pval, cvar_95=cvar95, cvar_99=cvar99)
        except ValueError as exc:
            pytest.fail(f"render_rmb_loss_simulation raised uncaught ValueError: {exc}")

    def test_rmb_loss_simulation_discontinuity_at_one(self):
        """Inspect decimal vs percentage scale interpretation boundary around 1.0."""
        # 1.0 decimal scale = 100% loss
        # 1.01 percentage scale = 1.01% loss
        # Test that both execute without crashing
        render_rmb_loss_simulation(portfolio_value=100000.0, cvar_95=1.0, cvar_99=1.0)
        render_rmb_loss_simulation(portfolio_value=100000.0, cvar_95=1.01, cvar_99=1.01)
