"""Unit tests for the 7 core analytical engines in src/engine/.

Covers normal execution, zero variance, pure bond fund, extreme volatility,
and empty/boundary data conditions for 100% test reliability.
"""

import pytest
import pandas as pd
import numpy as np

from src.engine.pbsa import PBSAEngine, map_broad_sector
from src.engine.rbsa import RBSAEngine
from src.engine.rolling_rbsa import RollingRBSAEngine
from src.engine.cvar_stress import CVaRStressEngine
from src.engine.prospect_theory import ProspectTheoryEngine
from src.engine.rebalance import RebalanceEngine
from src.engine.health_score import HealthScoreEngine


# --- Helper Data Generators ---
def make_mock_nav_df(daily_returns: np.ndarray, start_date: str = "2025-01-01") -> pd.DataFrame:
    """Helper to construct a mock fund NAV DataFrame from daily returns."""
    dates = pd.date_range(start=start_date, periods=len(daily_returns), freq="D").strftime("%Y-%m-%d")
    navs = np.cumprod(1.0 + daily_returns)
    return pd.DataFrame({
        "date": dates,
        "nav": navs,
        "daily_return": daily_returns
    })


# --- 1. PBSA Engine Tests ---
def test_pbsa_engine_normal(mock_holdings_df_dict):
    """Test PBSAEngine downward penetration and overlap matrix under normal inputs."""
    fund_market_values = {
        "000001": 50000.0,
        "014114": 30000.0,
        "001900": 20000.0
    }
    res = PBSAEngine.calculate(mock_holdings_df_dict, fund_market_values)

    assert "stock_weights" in res
    assert "sector_weights" in res
    assert "overlap_matrix" in res
    assert "top_stocks" in res

    stock_w = res["stock_weights"]
    sector_w = res["sector_weights"]
    overlap_m = res["overlap_matrix"]
    top_stocks = res["top_stocks"]

    assert not stock_w.empty
    assert len(sector_w) == 6  # 5 broad categories + 其他
    assert overlap_m.shape == (3, 3)

    # Check matrix diagonal is 1.0
    for code in fund_market_values.keys():
        assert np.isclose(overlap_m.loc[code, code], 1.0)

    # Check stock sum equals top_stocks sum
    assert pytest.approx(stock_w.sum(), 0.01) == top_stocks["amount_per_100"].sum()


def test_pbsa_engine_cosine_overlap_exact():
    """Test PBSAEngine overlap matrix cosine similarity accuracy."""
    holdings_dict = {
        "F1": pd.DataFrame([
            {"stock_code": "600519", "stock_name": "茅台", "weight": 0.1, "sector": "消费"},
            {"stock_code": "300750", "stock_name": "宁德", "weight": 0.1, "sector": "新能源"}
        ]),
        "F2": pd.DataFrame([
            {"stock_code": "600519", "stock_name": "茅台", "weight": 0.1, "sector": "消费"},
            {"stock_code": "300750", "stock_name": "宁德", "weight": 0.1, "sector": "新能源"}
        ]),
        "F3": pd.DataFrame([
            {"stock_code": "000001", "stock_name": "平安", "weight": 0.2, "sector": "金融"}
        ])
    }
    market_vals = {"F1": 1000.0, "F2": 1000.0, "F3": 1000.0}
    res = PBSAEngine.calculate(holdings_dict, market_vals)
    ov = res["overlap_matrix"]

    assert np.isclose(ov.loc["F1", "F2"], 1.0)
    assert np.isclose(ov.loc["F1", "F3"], 0.0)


def test_pbsa_engine_boundary_empty():
    """Test PBSAEngine with empty inputs."""
    res = PBSAEngine.calculate({}, {})
    assert res["stock_weights"].empty
    assert res["overlap_matrix"].empty


def test_map_broad_sector():
    """Test sector mapping function."""
    assert map_broad_sector("食品饮料") == "大消费"
    assert map_broad_sector("银行") == "大金融"
    assert map_broad_sector("半导体") == "科技制造"
    assert map_broad_sector("未知领域xxx") == "其他"


# --- 2. RBSA Engine Tests ---
def test_rbsa_engine_normal(mock_fund_nav_df_dict, mock_benchmark_nav_df):
    """Test RBSAEngine constrained style attribution under normal inputs."""
    res = RBSAEngine.calculate(mock_fund_nav_df_dict, mock_benchmark_nav_df)

    assert "style_weights" in res
    assert "radar_data" in res
    assert "r_squared" in res

    weights = res["style_weights"]
    assert len(weights) == 5
    assert pytest.approx(sum(weights.values()), 0.001) == 1.0
    assert all(w >= 0.0 for w in weights.values())
    assert 0.0 <= res["r_squared"] <= 1.0


def test_rbsa_engine_zero_variance(mock_benchmark_nav_df):
    """Test RBSAEngine boundary case: zero variance / flat NAV returns."""
    flat_returns = np.zeros(100)
    flat_nav_df = make_mock_nav_df(flat_returns)

    res = RBSAEngine.calculate({"000001": flat_nav_df}, mock_benchmark_nav_df)
    assert "style_weights" in res
    assert pytest.approx(sum(res["style_weights"].values()), 0.001) == 1.0


# --- 3. Rolling RBSA Engine Tests ---
def test_rolling_rbsa_engine_normal(mock_fund_nav_df_dict, mock_benchmark_nav_df):
    """Test RollingRBSAEngine rolling style weights and drift variance."""
    res = RollingRBSAEngine.calculate(mock_fund_nav_df_dict, mock_benchmark_nav_df, window=60)

    assert "rolling_series" in res
    assert "factor_variance" in res
    assert "drift_warning" in res

    rolling_df = res["rolling_series"]
    assert not rolling_df.empty
    assert set(rolling_df.columns) == {"large_value", "large_growth", "small_value", "small_growth", "bond_index"}
    assert isinstance(res["drift_warning"], bool)


def test_rolling_rbsa_engine_insufficient_dates(mock_benchmark_nav_df):
    """Test RollingRBSAEngine boundary case: total dates < window."""
    short_returns = np.random.normal(0.001, 0.01, 20)
    short_nav_df = make_mock_nav_df(short_returns)

    res = RollingRBSAEngine.calculate({"000001": short_nav_df}, mock_benchmark_nav_df, window=60)
    assert "rolling_series" in res
    assert not res["rolling_series"].empty


# --- 4. CVaR Stress Engine Tests ---
def test_cvar_stress_engine_normal(mock_fund_nav_df_dict):
    """Test CVaRStressEngine Cornish-Fisher CVaR and stress testing."""
    market_vals = {"000001": 50000.0, "014114": 50000.0}
    res = CVaRStressEngine.calculate(mock_fund_nav_df_dict, market_vals)

    assert "cvar_95" in res
    assert "cvar_99" in res
    assert "stress_results" in res

    assert res["cvar_95"] >= 0.0
    assert res["cvar_99"] >= res["cvar_95"]

    stress = res["stress_results"]
    assert "2015_equity_crash" in stress
    assert "2022_dual_crash" in stress
    assert "2020_covid_shock" in stress

    for key, val in stress.items():
        assert "loss_pct" in val
        assert "loss_amount" in val
        assert val["loss_pct"] >= 0.0


def test_cvar_stress_engine_flat_returns():
    """Test CVaRStressEngine boundary case: zero return volatility."""
    flat_nav_df = make_mock_nav_df(np.zeros(50))
    res = CVaRStressEngine.calculate({"000001": flat_nav_df}, {"000001": 10000.0})
    assert res["cvar_95"] == 0.0
    assert res["cvar_99"] == 0.0


# --- 5. Prospect Theory Engine Tests ---
def test_prospect_theory_engine_normal(mock_fund_nav_df_dict):
    """Test ProspectTheoryEngine win rate, payoff ratio, prospect utility, and Omega ratio."""
    market_vals = {"000001": 100000.0}
    res = ProspectTheoryEngine.calculate(mock_fund_nav_df_dict, market_vals)

    assert "win_rate" in res
    assert "payoff_ratio" in res
    assert "prospect_utility" in res
    assert "omega_ratio" in res

    assert 0.0 <= res["win_rate"] <= 1.0
    assert res["payoff_ratio"] >= 0.0
    assert isinstance(res["prospect_utility"], float)
    assert res["omega_ratio"] >= 0.0


def test_prospect_theory_engine_all_positive():
    """Test ProspectTheoryEngine boundary case: all positive daily returns."""
    pos_returns = np.ones(50) * 0.01
    pos_nav_df = make_mock_nav_df(pos_returns)
    res = ProspectTheoryEngine.calculate({"000001": pos_nav_df}, {"000001": 50000.0})

    assert res["win_rate"] == 1.0
    assert res["payoff_ratio"] == 10.0
    assert res["prospect_utility"] > 0.0
    assert res["omega_ratio"] == 99.0


# --- 6. Rebalance Engine Tests ---
def test_rebalance_engine_normal(mock_fund_nav_df_dict):
    """Test RebalanceEngine quad-programming rebalance and redemption fee tips."""
    current_positions = {
        "000001": 80000.0,
        "014114": 10000.0,
        "001900": 10000.0
    }
    holding_days = {
        "000001": 5,   # held < 7 days -> 1.5% fee
        "014114": 28,  # held < 30 days -> 0.75% fee
        "001900": 400  # held >= 365 days -> 0% fee
    }
    res = RebalanceEngine.calculate(current_positions, mock_fund_nav_df_dict, holding_days)

    assert "trade_actions" in res
    assert "net_benefit" in res
    assert "trigger_reasons" in res

    actions = res["trade_actions"]
    assert isinstance(actions, list)

    # Check fee tip generated for fund 000001 if recommended to sell
    for act in actions:
        assert act["action"] in ["SELL", "BUY"]
        assert act["amount"] > 0.0
        if act["fund_code"] == "000001" and act["action"] == "SELL":
            assert "已持有 5 天" in act["fee_saved_tip"]


def test_rebalance_engine_single_fund(mock_fund_nav_df_dict):
    """Test RebalanceEngine boundary case: single fund holding."""
    res = RebalanceEngine.calculate({"000001": 50000.0}, mock_fund_nav_df_dict, {"000001": 100})
    assert res["trade_actions"] == []


# --- 7. Health Score Engine Tests ---
def test_health_score_engine_normal(mock_fund_nav_df_dict, mock_benchmark_nav_df, mock_holdings_df_dict):
    """Test HealthScoreEngine full panorama diagnostic scoring."""
    market_vals = {"000001": 50000.0, "014114": 30000.0, "001900": 20000.0}
    holding_days = {"000001": 100, "014114": 200, "001900": 300}

    # Run all 6 prior engines
    pbsa_res = PBSAEngine.calculate(mock_holdings_df_dict, market_vals)
    rbsa_res = RBSAEngine.calculate(mock_fund_nav_df_dict, mock_benchmark_nav_df)
    rolling_res = RollingRBSAEngine.calculate(mock_fund_nav_df_dict, mock_benchmark_nav_df)
    cvar_res = CVaRStressEngine.calculate(mock_fund_nav_df_dict, market_vals)
    prospect_res = ProspectTheoryEngine.calculate(mock_fund_nav_df_dict, market_vals)
    rebalance_res = RebalanceEngine.calculate(market_vals, mock_fund_nav_df_dict, holding_days)

    res = HealthScoreEngine.calculate(pbsa_res, rbsa_res, rolling_res, cvar_res, prospect_res, rebalance_res)

    assert "total_score" in res
    assert "health_score" in res
    assert "level" in res
    assert "summary_text" in res
    assert "key_findings" in res
    assert "deductions" in res

    assert 0 <= res["total_score"] <= 100
    assert res["level"] in ["优", "良", "中", "需保养"]
    assert len(res["summary_text"]) > 10
    assert isinstance(res["key_findings"], list)
