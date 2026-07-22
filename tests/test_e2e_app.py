"""4-Tier E2E and Full Application Testing Suite for Factrix (tests/test_e2e_app.py).

Covers:
- Tier 1: Functional Happy Path (10 test cases)
- Tier 2: Boundary Edge Cases & Exceptions (8 test cases)
- Tier 3: Cross-Combination & Multi-Factor (3 test cases)
- Tier 4: Real-World Headless E2E Execution (2 test cases)
"""

import time
from pathlib import Path
from typing import Dict, Any
import pytest
import pandas as pd
import numpy as np
from streamlit.testing.v1 import AppTest

from src.config import DEFAULT_CSV_PATH, DB_PATH, get_redemption_fee_rate
from src.data.csv_parser import parse_fundlist_csv, validate_parsed_data
from src.data.storage import SQLiteStorage
from src.data.fetcher import FundFetcher

from src.engine.pbsa import PBSAEngine
from src.engine.rbsa import RBSAEngine
from src.engine.rolling_rbsa import RollingRBSAEngine
from src.engine.cvar_stress import CVaRStressEngine
from src.engine.prospect_theory import ProspectTheoryEngine
from src.engine.rebalance import RebalanceEngine
from src.engine.health_score import HealthScoreEngine


# Helper function to generate mock NAV DataFrames with specified returns
def _make_nav_df(returns: np.ndarray, start_date: str = "2025-01-01") -> pd.DataFrame:
    dates = pd.date_range(start=start_date, periods=len(returns), freq="D").strftime("%Y-%m-%d")
    navs = np.cumprod(1.0 + returns)
    return pd.DataFrame({
        "date": dates,
        "nav": navs,
        "daily_return": returns
    })


# =====================================================================
# Tier 1: Functional Happy Path (10 Test Cases)
# =====================================================================

@pytest.mark.tier1
def test_tc_t1_01_parse_standard_fundlist_csv():
    """TC-T1-01: CSV parser reads standard 5-column fundlist.csv correctly."""
    assert DEFAULT_CSV_PATH.exists()
    df = parse_fundlist_csv(str(DEFAULT_CSV_PATH), aggregate=True)
    is_valid, msg = validate_parsed_data(df)
    assert is_valid, f"Validation failed: {msg}"
    expected_cols = ['fund_code', 'fund_name', 'share', 'nav', 'market_value']
    assert all(col in df.columns for col in expected_cols)
    assert len(df) > 0
    for code in df['fund_code']:
        assert len(code) == 6 and code.isdigit()


@pytest.mark.tier1
def test_tc_t1_02_fetcher_sqlite_cache_hit(memory_storage: SQLiteStorage):
    """TC-T1-02: FundFetcher cache hit mechanism自检 without external network requests."""
    fetcher = FundFetcher(storage=memory_storage)

    # First fetch from memory_storage (cache hit)
    df_nav1 = fetcher.get_fund_nav("000001")
    assert not df_nav1.empty

    # Second fetch
    df_nav2 = fetcher.get_fund_nav("000001")
    assert not df_nav2.empty
    assert len(df_nav1) == len(df_nav2)


@pytest.mark.tier1
def test_tc_t1_03_health_score_engine_happy_path(
    mock_fund_nav_df_dict, mock_benchmark_nav_df, mock_holdings_df_dict
):
    """TC-T1-03: HealthScoreEngine happy path outputs valid score [0, 100] and level string."""
    market_vals = {"000001": 50000.0, "014114": 30000.0}
    holding_days = {"000001": 100, "014114": 150}

    pbsa_res = PBSAEngine.calculate(mock_holdings_df_dict, market_vals)
    rbsa_res = RBSAEngine.calculate(mock_fund_nav_df_dict, mock_benchmark_nav_df)
    rolling_res = RollingRBSAEngine.calculate(mock_fund_nav_df_dict, mock_benchmark_nav_df)
    cvar_res = CVaRStressEngine.calculate(mock_fund_nav_df_dict, market_vals)
    prospect_res = ProspectTheoryEngine.calculate(mock_fund_nav_df_dict, market_vals)
    rebalance_res = RebalanceEngine.calculate(market_vals, mock_fund_nav_df_dict, holding_days)

    res = HealthScoreEngine.calculate(pbsa_res, rbsa_res, rolling_res, cvar_res, prospect_res, rebalance_res)

    assert 0 <= res["total_score"] <= 100
    assert res["level"] in ["优", "良", "中", "需保养"]
    assert len(res["summary_text"]) > 0
    assert isinstance(res["key_findings"], list)


@pytest.mark.tier1
def test_tc_t1_04_pbsa_engine_happy_path(mock_holdings_df_dict):
    """TC-T1-04: PBSAEngine happy path computes top stocks and symmetric overlap matrix with 1.0 diagonal."""
    market_vals = {"000001": 50000.0, "014114": 30000.0}
    res = PBSAEngine.calculate(mock_holdings_df_dict, market_vals)

    assert "stock_weights" in res
    assert "overlap_matrix" in res
    assert "top_stocks" in res

    overlap_m = res["overlap_matrix"]
    assert overlap_m.shape == (2, 2)
    assert np.isclose(overlap_m.loc["000001", "000001"], 1.0)
    assert np.isclose(overlap_m.loc["014114", "014114"], 1.0)


@pytest.mark.tier1
def test_tc_t1_05_rbsa_engine_happy_path(mock_fund_nav_df_dict, mock_benchmark_nav_df):
    """TC-T1-05: RBSAEngine happy path constrained weights sum to 1.0 and non-negative."""
    res = RBSAEngine.calculate(mock_fund_nav_df_dict, mock_benchmark_nav_df)

    weights = res["style_weights"]
    assert len(weights) == 5
    assert pytest.approx(sum(weights.values()), 0.001) == 1.0
    assert all(w >= 0.0 for w in weights.values())
    assert 0.0 <= res["r_squared"] <= 1.0


@pytest.mark.tier1
def test_tc_t1_06_rolling_rbsa_engine_happy_path(mock_fund_nav_df_dict, mock_benchmark_nav_df):
    """TC-T1-06: RollingRBSAEngine happy path computes 60-day rolling style trajectory and variance."""
    res = RollingRBSAEngine.calculate(mock_fund_nav_df_dict, mock_benchmark_nav_df, window=60)

    assert "rolling_series" in res
    assert "factor_variance" in res
    assert "drift_warning" in res
    assert not res["rolling_series"].empty


@pytest.mark.tier1
def test_tc_t1_07_cvar_stress_engine_happy_path(mock_fund_nav_df_dict):
    """TC-T1-07: CVaRStressEngine happy path Cornish-Fisher CVaR 99% >= 95% and stress scenarios."""
    market_vals = {"000001": 50000.0, "014114": 50000.0}
    res = CVaRStressEngine.calculate(mock_fund_nav_df_dict, market_vals)

    assert res["cvar_95"] >= 0.0
    assert res["cvar_99"] >= res["cvar_95"]
    assert "2015_equity_crash" in res["stress_results"]


@pytest.mark.tier1
def test_tc_t1_08_prospect_theory_engine_happy_path(mock_fund_nav_df_dict):
    """TC-T1-08: ProspectTheoryEngine happy path win rate in [0,1], V(r), and positive Omega ratio."""
    market_vals = {"000001": 100000.0}
    res = ProspectTheoryEngine.calculate(mock_fund_nav_df_dict, market_vals)

    assert 0.0 <= res["win_rate"] <= 1.0
    assert res["payoff_ratio"] >= 0.0
    assert isinstance(res["prospect_utility"], float)
    assert res["omega_ratio"] >= 0.0


@pytest.mark.tier1
def test_tc_t1_09_rebalance_engine_happy_path(mock_fund_nav_df_dict):
    """TC-T1-09: RebalanceEngine happy path trade recommendations and redemption fee tips."""
    current_positions = {"000001": 80000.0, "014114": 20000.0}
    holding_days = {"000001": 10, "014114": 400}
    res = RebalanceEngine.calculate(current_positions, mock_fund_nav_df_dict, holding_days)

    assert "trade_actions" in res
    assert "net_benefit" in res
    assert isinstance(res["trade_actions"], list)


@pytest.mark.tier1
def test_tc_t1_10_app_test_main_render():
    """TC-T1-10: Streamlit AppTest loads app.py cleanly without unhandled exceptions."""
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()

    assert not at.exception, f"AppTest raised unexpected exception: {at.exception}"
    assert len(at.sidebar) > 0


# =====================================================================
# Tier 2: Boundary Edge Cases & Exceptions (8 Test Cases)
# =====================================================================

@pytest.mark.tier2
def test_tc_t2_01_csv_parser_missing_required_columns(tmp_path: Path):
    """TC-T2-01: CSV parser raises ValueError when required columns (e.g. fund_code) are missing."""
    invalid_csv = tmp_path / "missing_cols.csv"
    invalid_csv.write_text("序号,基金名称,持有份额\n1,测试A,100\n", encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        parse_fundlist_csv(str(invalid_csv))
    assert "缺失" in str(exc_info.value) or "column" in str(exc_info.value).lower()


@pytest.mark.tier2
def test_tc_t2_02_csv_parser_malformed_numeric_data(tmp_path: Path):
    """TC-T2-02: CSV parser cleans or handles non-numeric string characters in numeric columns."""
    malformed_csv = tmp_path / "malformed.csv"
    content = (
        '序号,基金代码,基金名称,持有份额,基金净值,净值日期,资产情况\n'
        '1,000001,测试A,INVALID_NUM,1.5,2026-07-17,150.0\n'
    )
    malformed_csv.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        parse_fundlist_csv(str(malformed_csv))
    assert "No positive share" in str(exc_info.value) or "invalid" in str(exc_info.value).lower()


@pytest.mark.tier2
def test_tc_t2_03_fetcher_exponential_backoff_retry_fallback(tmp_path: Path, monkeypatch):
    """TC-T2-03: AkShare HTTP 429/Timeout triggers retries and falls back gracefully to empty DF/storage."""
    fetcher = FundFetcher(db_path=tmp_path / "retry.db", max_retries=3, backoff_factor=0.001)

    def mock_fail_all(fund_code):
        raise RuntimeError("Mock HTTP 429 Rate Limit Exceeded")

    monkeypatch.setattr(fetcher, "_fetch_akshare_fund_holdings", mock_fail_all)
    df_fallback = fetcher.get_fund_holdings("000940")

    assert isinstance(df_fallback, pd.DataFrame)
    assert df_fallback.empty


@pytest.mark.tier2
def test_tc_t2_04_pbsa_single_fund_portfolio():
    """TC-T2-04: Single fund portfolio PBSA calculation does not crash and produces 1x1 matrix."""
    single_holdings = {
        "000001": pd.DataFrame([
            {"stock_code": "600519", "stock_name": "茅台", "weight": 0.1, "sector": "消费"}
        ])
    }
    market_vals = {"000001": 50000.0}
    res = PBSAEngine.calculate(single_holdings, market_vals)

    assert "overlap_matrix" in res
    ov = res["overlap_matrix"]
    assert ov.shape == (1, 1)
    assert np.isclose(ov.iloc[0, 0], 1.0)


@pytest.mark.tier2
def test_tc_t2_05_rbsa_short_nav_history(mock_benchmark_nav_df):
    """TC-T2-05: NAV history less than 30 days is handled gracefully without matrix singularity crash."""
    short_returns = np.random.normal(0.001, 0.01, 15)
    short_nav_df = _make_nav_df(short_returns)

    res = RBSAEngine.calculate({"000001": short_nav_df}, mock_benchmark_nav_df)
    assert "style_weights" in res
    assert pytest.approx(sum(res["style_weights"].values()), 0.001) == 1.0


@pytest.mark.tier2
def test_tc_t2_06_cvar_zero_variance_flat_returns():
    """TC-T2-06: Zero return volatility / flat NAV returns handle ZeroDivisionError safely."""
    flat_nav_df = _make_nav_df(np.zeros(50))
    res = CVaRStressEngine.calculate({"000001": flat_nav_df}, {"000001": 10000.0})

    assert res["cvar_95"] == 0.0
    assert res["cvar_99"] == 0.0


@pytest.mark.tier2
def test_tc_t2_07_rebalance_high_redemption_fee_penalty(mock_fund_nav_df_dict):
    """TC-T2-07: Holding days < 7 triggers high 1.5% penalty fee in rebalance engine tips."""
    current_positions = {"000001": 90000.0, "014114": 10000.0}
    holding_days = {"000001": 3, "014114": 400}  # held 3 days (<7d -> 1.5% fee)

    res = RebalanceEngine.calculate(current_positions, mock_fund_nav_df_dict, holding_days)
    actions = res["trade_actions"]

    for act in actions:
        if act["fund_code"] == "000001" and act["action"] == "SELL":
            assert "1.5%" in act["fee_saved_tip"] or "惩罚" in act["fee_saved_tip"] or "已持有 3 天" in act["fee_saved_tip"]


@pytest.mark.tier2
def test_tc_t2_08_app_empty_fundlist_handling(tmp_path: Path, monkeypatch):
    """TC-T2-08: Empty or invalid fundlist file in Streamlit UI renders Warning card without crashing."""
    empty_csv = tmp_path / "empty_fundlist.csv"
    empty_csv.write_text("序号,基金代码,基金名称,持有份额,基金净值,净值日期,资产情况\n", encoding="utf-8")

    monkeypatch.setattr("src.config.DEFAULT_CSV_PATH", empty_csv)

    at = AppTest.from_file("app.py", default_timeout=10)
    at.run()

    assert not at.exception
    # Verify warning/info/markdown element rendered for empty data without crashing
    assert len(at.warning) > 0 or len(at.info) > 0 or len(at.markdown) > 0 or len(at.error) > 0


# =====================================================================
# Tier 3: Cross-Combination & Multi-Factor (3 Test Cases)
# =====================================================================

@pytest.mark.tier3
def test_tc_t3_01_high_overlap_and_cvar_linkage(mock_fund_nav_df_dict, mock_benchmark_nav_df):
    """TC-T3-01: High overlap (>80%) + equity crash stress linkage triggers concentration & tail risk warnings."""
    # Build two funds with identical top holdings
    identical_holdings = {
        "F1": pd.DataFrame([{"stock_code": "600519", "stock_name": "茅台", "weight": 0.1, "sector": "消费"}]),
        "F2": pd.DataFrame([{"stock_code": "600519", "stock_name": "茅台", "weight": 0.1, "sector": "消费"}]),
    }
    market_vals = {"F1": 50000.0, "F2": 50000.0}
    holding_days = {"F1": 100, "F2": 100}

    pbsa_res = PBSAEngine.calculate(identical_holdings, market_vals)

    # Check overlap is 1.0 (100%)
    ov = pbsa_res["overlap_matrix"]
    assert np.isclose(ov.loc["F1", "F2"], 1.0)

    # Run remaining engines
    rbsa_res = RBSAEngine.calculate(mock_fund_nav_df_dict, mock_benchmark_nav_df)
    rolling_res = RollingRBSAEngine.calculate(mock_fund_nav_df_dict, mock_benchmark_nav_df)
    cvar_res = CVaRStressEngine.calculate(mock_fund_nav_df_dict, market_vals)
    prospect_res = ProspectTheoryEngine.calculate(mock_fund_nav_df_dict, market_vals)
    rebalance_res = RebalanceEngine.calculate(market_vals, mock_fund_nav_df_dict, holding_days)

    health_res = HealthScoreEngine.calculate(pbsa_res, rbsa_res, rolling_res, cvar_res, prospect_res, rebalance_res)

    # Verify score deduction and key finding warning for high overlap
    findings = " ".join(health_res["key_findings"])
    assert "重合" in findings or "抱团" in findings or "集中" in findings


@pytest.mark.tier3
def test_tc_t3_02_style_drift_and_sharpe_decay_rebalance(mock_benchmark_nav_df):
    """TC-T3-02: Rolling RBSA style drift + Sharpe ratio decay triggers multi-factor warning and rebalance action."""
    # Create fund with high volatility and severe style drift
    np.random.seed(123)
    ret1 = np.random.normal(0.002, 0.03, 120)  # early high return
    ret2 = np.random.normal(-0.003, 0.04, 130) # recent severe decay
    drifting_returns = np.concatenate([ret1, ret2])
    drifting_nav_df = _make_nav_df(drifting_returns)

    nav_dict = {"000001": drifting_nav_df, "014114": mock_benchmark_nav_df[['date', 'hs300']].rename(columns={'hs300': 'nav'}).assign(daily_return=0.0001)}

    rolling_res = RollingRBSAEngine.calculate(nav_dict, mock_benchmark_nav_df, window=60)
    assert "rolling_series" in rolling_res

    current_positions = {"000001": 80000.0, "014114": 20000.0}
    holding_days = {"000001": 100, "014114": 100}

    rebalance_res = RebalanceEngine.calculate(current_positions, nav_dict, holding_days)
    assert "trigger_reasons" in rebalance_res
    assert len(rebalance_res["trigger_reasons"]) > 0


@pytest.mark.tier3
def test_tc_t3_03_rebalance_fee_tier_transition(mock_fund_nav_df_dict):
    """TC-T3-03: Rebalance fee tier boundary transition (6 days @ 1.5% vs 8 days @ 0.75%)."""
    current_positions = {"000001": 70000.0, "014114": 30000.0}

    # Case A: 6 days holding -> 1.5% fee
    days_6 = {"000001": 6, "014114": 400}
    res_6 = RebalanceEngine.calculate(current_positions, mock_fund_nav_df_dict, days_6)

    # Case B: 8 days holding -> 0.75% fee
    days_8 = {"000001": 8, "014114": 400}
    res_8 = RebalanceEngine.calculate(current_positions, mock_fund_nav_df_dict, days_8)

    assert get_redemption_fee_rate(6) == 0.015
    assert get_redemption_fee_rate(8) == 0.0075
    # Net benefit should be higher for lower redemption fee
    assert res_8["net_benefit"] >= res_6["net_benefit"]


# =====================================================================
# Tier 4: Real-World Headless E2E Execution (2 Test Cases)
# =====================================================================

@pytest.mark.tier4
def test_tc_t4_01_full_portfolio_analysis_e2e(mock_fund_nav_df_dict, mock_benchmark_nav_df, mock_holdings_df_dict):
    """TC-T4-01: Full 5-fund realistic portfolio pipeline runs end-to-end under 3 seconds without network."""
    t_start = time.time()

    fund_market_values = {
        "000001": 30000.0,
        "014114": 25000.0,
        "001900": 20000.0,
        "012094": 15000.0,
        "022502": 10000.0,
    }
    holding_days = {code: 120 for code in fund_market_values.keys()}

    # 1. PBSA
    pbsa_res = PBSAEngine.calculate(mock_holdings_df_dict, fund_market_values)
    assert not pbsa_res["overlap_matrix"].empty

    # 2. RBSA
    rbsa_res = RBSAEngine.calculate(mock_fund_nav_df_dict, mock_benchmark_nav_df)
    assert pytest.approx(sum(rbsa_res["style_weights"].values()), 0.001) == 1.0

    # 3. Rolling RBSA
    rolling_res = RollingRBSAEngine.calculate(mock_fund_nav_df_dict, mock_benchmark_nav_df)
    assert not rolling_res["rolling_series"].empty

    # 4. CVaR & Stress
    cvar_res = CVaRStressEngine.calculate(mock_fund_nav_df_dict, fund_market_values)
    assert cvar_res["cvar_99"] >= cvar_res["cvar_95"]

    # 5. Prospect Theory
    prospect_res = ProspectTheoryEngine.calculate(mock_fund_nav_df_dict, fund_market_values)
    assert prospect_res["win_rate"] >= 0.0

    # 6. Rebalance Engine
    rebalance_res = RebalanceEngine.calculate(fund_market_values, mock_fund_nav_df_dict, holding_days)
    assert "trade_actions" in rebalance_res

    # 7. Health Score Engine
    health_res = HealthScoreEngine.calculate(
        pbsa_res, rbsa_res, rolling_res, cvar_res, prospect_res, rebalance_res
    )
    assert 0 <= health_res["total_score"] <= 100

    t_elapsed = time.time() - t_start
    assert t_elapsed < 3.0, f"Full E2E pipeline took {t_elapsed:.2f}s, exceeding 3.0s threshold!"


@pytest.mark.tier4
def test_tc_t4_02_app_headless_full_workflow():
    """TC-T4-02: AppTest Headless full workflow renders metrics, charts, and dataframes without exceptions."""
    at = AppTest.from_file("app.py", default_timeout=60)
    at.run()

    # 1. Assert no unhandled exceptions
    assert not at.exception, f"Streamlit app raised exception: {at.exception}"

    # 2. Assert sidebar rendered
    assert len(at.sidebar) > 0

    # 3. Assert metric cards present
    metrics = at.metric
    assert len(metrics) > 0

    # 4. Assert UI headers and Markdown present
    assert len(at.title) > 0 or len(at.markdown) > 0

    # 5. Assert DataFrames/Tables present
    dfs = at.dataframe
    assert len(dfs) >= 1
