"""Unit tests for AlphaBetaEngine in src/engine/alpha_beta.py."""

import pytest
import pandas as pd
import numpy as np

from src.engine.alpha_beta import AlphaBetaEngine


def make_mock_return_df(daily_returns: np.ndarray, start_date: str = "2025-01-01") -> pd.DataFrame:
    """Helper to construct a mock daily return DataFrame."""
    dates = pd.date_range(start=start_date, periods=len(daily_returns), freq="D").strftime("%Y-%m-%d")
    navs = np.cumprod(1.0 + daily_returns)
    return pd.DataFrame({
        "date": dates,
        "nav": navs,
        "daily_return": daily_returns
    })


def test_alpha_beta_engine_normal_multi_fund():
    """Test AlphaBetaEngine with standard multi-fund portfolio and benchmark."""
    rng = np.random.RandomState(123)
    n = 60
    bm_ret = rng.normal(0.0005, 0.01, size=n)
    f1_ret = 1.1 * bm_ret + rng.normal(0.0002, 0.003, size=n)
    f2_ret = 0.9 * bm_ret + rng.normal(-0.0001, 0.003, size=n)

    bm_df = make_mock_return_df(bm_ret)
    f1_df = make_mock_return_df(f1_ret)
    f2_df = make_mock_return_df(f2_ret)

    nav_dict = {"000001": f1_df, "000002": f2_df}
    market_vals = {"000001": 600000.0, "000002": 400000.0}

    res = AlphaBetaEngine.calculate_metrics(
        nav_df_dict=nav_dict,
        market_benchmark_df=bm_df,
        fund_market_values=market_vals,
        risk_free_rate=0.02
    )

    required_keys = [
        "portfolio_alpha", "portfolio_beta", "portfolio_r2",
        "sharpe_ratio", "treynor_ratio", "information_ratio",
        "tracking_error", "fund_metrics", "scatter_data", "is_synthetic_benchmark"
    ]
    for key in required_keys:
        assert key in res

    assert not res["is_synthetic_benchmark"]
    assert 0.5 <= res["portfolio_beta"] <= 1.5
    assert 0.0 <= res["portfolio_r2"] <= 1.0
    assert len(res["scatter_data"]) == n
    assert "000001" in res["fund_metrics"]
    assert "000002" in res["fund_metrics"]

    fund1_m = res["fund_metrics"]["000001"]
    for f_key in ["alpha", "beta", "r2", "sharpe_ratio", "treynor_ratio", "information_ratio", "tracking_error"]:
        assert f_key in fund1_m

    # Check scatter_data fields
    first_pt = res["scatter_data"][0]
    for pt_key in ["date", "market_return", "portfolio_return", "portfolio_excess_return", "market_excess_return"]:
        assert pt_key in first_pt


def test_alpha_beta_engine_perfect_correlation():
    """Test perfect correlation (y = x) where Beta=1.0, Alpha=0.0, R2=1.0, TE=0.0."""
    n = 50
    ret = np.linspace(-0.02, 0.02, n)
    bm_df = make_mock_return_df(ret)
    f_df = make_mock_return_df(ret)

    res = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": f_df},
        market_benchmark_df=bm_df,
        risk_free_rate=0.02
    )

    assert pytest.approx(res["portfolio_beta"], abs=1e-5) == 1.0
    assert pytest.approx(res["portfolio_alpha"], abs=1e-5) == 0.0
    assert pytest.approx(res["portfolio_r2"], abs=1e-5) == 1.0
    assert pytest.approx(res["tracking_error"], abs=1e-5) == 0.0
    mean_y_ex = np.mean(ret) - (0.02 / 252.0)
    std_y = np.std(ret, ddof=1)
    expected_sharpe = (mean_y_ex / std_y) * np.sqrt(252.0)
    expected_treynor = (mean_y_ex * 252.0) / 1.0

    assert pytest.approx(res["sharpe_ratio"], abs=1e-5) == expected_sharpe
    assert pytest.approx(res["treynor_ratio"], abs=1e-5) == expected_treynor


def test_alpha_beta_engine_known_linear_relation():
    """Test linear relation y = 0.0005 + 1.2 * x with known Beta=1.2 and R2=1.0."""
    n = 100
    rng = np.random.RandomState(42)
    x = rng.normal(0.001, 0.015, size=n)
    y = 0.0005 + 1.2 * x

    bm_df = make_mock_return_df(x)
    f_df = make_mock_return_df(y)

    res = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": f_df},
        market_benchmark_df=bm_df,
        risk_free_rate=0.02
    )

    assert pytest.approx(res["portfolio_beta"], abs=1e-4) == 1.2
    assert pytest.approx(res["portfolio_r2"], abs=1e-4) == 1.0


def test_alpha_beta_engine_synthetic_fallback():
    """Test fallback to synthetic benchmark when benchmark DataFrame is None or empty."""
    rng = np.random.RandomState(99)
    f_ret = rng.normal(0.001, 0.01, size=30)
    f_df = make_mock_return_df(f_ret)

    # None benchmark
    res_none = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": f_df},
        market_benchmark_df=None
    )
    assert res_none["is_synthetic_benchmark"] is True
    assert len(res_none["scatter_data"]) == 30

    # Empty DataFrame benchmark
    res_empty = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": f_df},
        market_benchmark_df=pd.DataFrame()
    )
    assert res_empty["is_synthetic_benchmark"] is True
    assert len(res_empty["scatter_data"]) == 30


def test_alpha_beta_engine_zero_variance():
    """Test zero variance protection when net asset value or returns are constant."""
    n = 20
    flat_ret = np.zeros(n)
    bm_df = make_mock_return_df(flat_ret)
    f_df = make_mock_return_df(flat_ret)

    res = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": f_df},
        market_benchmark_df=bm_df,
        risk_free_rate=0.02
    )

    assert res["is_synthetic_benchmark"] is False
    assert res["portfolio_beta"] == 0.0
    assert pytest.approx(res["portfolio_alpha"], abs=1e-5) == -0.02
    assert res["portfolio_r2"] == 0.0
    assert res["sharpe_ratio"] == 0.0
    assert res["treynor_ratio"] == 0.0


def test_alpha_beta_engine_empty_or_short_input():
    """Test empty dictionary or short time series (< 3 trading days)."""
    # Empty input dict
    res_empty = AlphaBetaEngine.calculate_metrics(nav_df_dict={}, market_benchmark_df=None)
    assert res_empty["portfolio_alpha"] == 0.0
    assert res_empty["fund_metrics"] == {}
    assert res_empty["scatter_data"] == []

    # Short time series (2 days)
    short_df = make_mock_return_df(np.array([0.01, 0.02]))
    res_short = AlphaBetaEngine.calculate_metrics(nav_df_dict={"F1": short_df}, market_benchmark_df=short_df)
    assert res_short["portfolio_alpha"] == 0.0
    assert res_short["scatter_data"] == []


def test_alpha_beta_engine_kwarg_rf_rate_alias():
    """Test passing rf_rate kwarg alias."""
    rng = np.random.RandomState(7)
    x = rng.normal(0.001, 0.01, size=40)
    y = rng.normal(0.001, 0.01, size=40)

    bm_df = make_mock_return_df(x)
    f_df = make_mock_return_df(y)

    res_rf1 = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": f_df},
        market_benchmark_df=bm_df,
        rf_rate=0.01
    )
    res_rf2 = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": f_df},
        market_benchmark_df=bm_df,
        rf_rate=0.05
    )

    # Different risk free rates should produce different Sharpe ratios
    assert res_rf1["sharpe_ratio"] != res_rf2["sharpe_ratio"]


def test_alpha_beta_engine_single_fund_dataframe_input():
    """Test passing a single pd.DataFrame directly as nav_df_dict."""
    n = 30
    rng = np.random.RandomState(42)
    bm_ret = rng.normal(0.0005, 0.01, size=n)
    f_ret = 1.1 * bm_ret + 0.0001

    bm_df = make_mock_return_df(bm_ret)
    f_df = make_mock_return_df(f_ret)

    res = AlphaBetaEngine.calculate_metrics(
        nav_df_dict=f_df,
        market_benchmark_df=bm_df
    )

    assert "portfolio_alpha" in res
    assert len(res["scatter_data"]) == n


def test_alpha_beta_engine_negative_beta():
    """Test negative beta handling in Treynor ratio and metrics."""
    n = 50
    x = np.linspace(-0.02, 0.02, n)
    y = -1.5 * x

    bm_df = make_mock_return_df(x)
    f_df = make_mock_return_df(y)

    res = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": f_df},
        market_benchmark_df=bm_df,
        risk_free_rate=0.02
    )

    assert pytest.approx(res["portfolio_beta"], abs=1e-4) == -1.5
    assert np.isfinite(res["treynor_ratio"])


def test_alpha_beta_calculate_alias():
    """Test calculate staticmethod alias."""
    n = 20
    x = np.linspace(-0.01, 0.01, n)
    bm_df = make_mock_return_df(x)
    f_df = make_mock_return_df(x)

    res1 = AlphaBetaEngine.calculate_metrics(nav_df_dict={"F1": f_df}, market_benchmark_df=bm_df)
    res2 = AlphaBetaEngine.calculate(nav_df_dict={"F1": f_df}, market_benchmark_df=bm_df)

    assert res1 == res2
