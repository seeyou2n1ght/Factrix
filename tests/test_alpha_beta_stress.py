"""Empirical stress test suite for AlphaBetaEngine in src/engine/alpha_beta.py.

Designed by challenger_m1_1 to test edge cases, boundary conditions,
and failure modes.
"""

import pytest
import pandas as pd
import numpy as np

from src.engine.alpha_beta import AlphaBetaEngine


def make_return_df(dates: list, returns: list, col_name: str = "daily_return") -> pd.DataFrame:
    """Helper to create test DataFrame from dates and returns list."""
    return pd.DataFrame({
        "date": dates,
        col_name: returns
    })


def test_stress_zero_variance_benchmark():
    """Stress test: Market benchmark has zero variance (constant returns)."""
    dates = pd.date_range("2025-01-01", periods=10).strftime("%Y-%m-%d").tolist()
    bm_ret = [0.0] * 10
    f_ret = [0.01 * (i % 2) for i in range(10)]

    bm_df = make_return_df(dates, bm_ret)
    f_df = make_return_df(dates, f_ret)

    res = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": f_df},
        market_benchmark_df=bm_df,
        risk_free_rate=0.02
    )

    # Should trigger synthetic benchmark fallback due to bm_var < 1e-12
    assert res["is_synthetic_benchmark"] is True
    assert isinstance(res["portfolio_alpha"], float)
    assert isinstance(res["portfolio_beta"], float)
    assert len(res["scatter_data"]) == 10


def test_stress_zero_variance_portfolio():
    """Stress test: Portfolio returns are zero variance (all zeros)."""
    dates = pd.date_range("2025-01-01", periods=10).strftime("%Y-%m-%d").tolist()
    bm_ret = [0.01, -0.01, 0.02, -0.02, 0.005, -0.005, 0.01, -0.01, 0.02, -0.02]
    f_ret = [0.0] * 10

    bm_df = make_return_df(dates, bm_ret)
    f_df = make_return_df(dates, f_ret)

    res = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": f_df},
        market_benchmark_df=bm_df,
        risk_free_rate=0.02
    )

    assert not res["is_synthetic_benchmark"]
    # Beta should be 0.0 since portfolio returns have 0 covariance with market
    assert res["portfolio_beta"] == 0.0
    # R2 should be 0.0
    assert res["portfolio_r2"] == 0.0
    # Sharpe ratio should be 0.0 since std_y is 0
    assert res["sharpe_ratio"] == 0.0
    # Alpha = mean(y_ex) - beta * mean(x_ex) = (-0.02/252) * 252 = -0.02
    assert pytest.approx(res["portfolio_alpha"], abs=1e-5) == -0.02


def test_stress_empty_inputs():
    """Stress test: Empty dictionary, empty DataFrames, None values."""
    # 1. Empty dict
    res1 = AlphaBetaEngine.calculate_metrics(nav_df_dict={}, market_benchmark_df=None)
    assert res1["portfolio_alpha"] == 0.0
    assert res1["fund_metrics"] == {}
    assert res1["scatter_data"] == []

    # 2. Dict with empty DataFrame
    res2 = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": pd.DataFrame()},
        market_benchmark_df=pd.DataFrame()
    )
    assert res2["portfolio_alpha"] == 0.0
    assert res2["scatter_data"] == []

    # 3. Dict with None value
    res3 = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": None},
        market_benchmark_df=None
    )
    assert res3["portfolio_alpha"] == 0.0


def test_stress_nans_and_infs():
    """Stress test: DataFrames containing NaNs, Infs, and -Infs."""
    dates = pd.date_range("2025-01-01", periods=10).strftime("%Y-%m-%d").tolist()
    
    # Portfolio returns with NaNs and Infs
    f_ret = [0.01, np.nan, 0.02, np.inf, -np.inf, 0.005, np.nan, -0.01, 0.02, -0.02]
    bm_ret = [0.01, -0.01, 0.02, -0.02, 0.005, -0.005, 0.01, -0.01, 0.02, np.nan]

    bm_df = make_return_df(dates, bm_ret)
    f_df = make_return_df(dates, f_ret)

    res = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": f_df},
        market_benchmark_df=bm_df,
        risk_free_rate=0.02
    )

    # Valid non-NaN non-Inf aligned points: indices 0, 2, 5, 7, 8 (5 valid points)
    # len(df_aligned) = 5 >= 3, so metrics should compute without crashing
    assert isinstance(res["portfolio_alpha"], float)
    assert not np.isnan(res["portfolio_alpha"])
    assert not np.isinf(res["portfolio_alpha"])
    assert len(res["scatter_data"]) == 5


def test_stress_insufficient_valid_points_with_nans():
    """Stress test: Inputs where NaNs leave fewer than 3 valid data points."""
    dates = pd.date_range("2025-01-01", periods=5).strftime("%Y-%m-%d").tolist()
    f_ret = [0.01, np.nan, np.nan, np.nan, 0.02] # Only 2 valid points
    bm_ret = [0.01, 0.02, 0.03, 0.04, 0.05]

    bm_df = make_return_df(dates, bm_ret)
    f_df = make_return_df(dates, f_ret)

    res = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": f_df},
        market_benchmark_df=bm_df
    )

    assert res["portfolio_alpha"] == 0.0
    assert res["scatter_data"] == []


def test_stress_single_and_two_data_points():
    """Stress test: 1 or 2 data points."""
    dates_1 = ["2025-01-01"]
    dates_2 = ["2025-01-01", "2025-01-02"]

    # 1 point
    f_df1 = make_return_df(dates_1, [0.01])
    bm_df1 = make_return_df(dates_1, [0.01])
    res1 = AlphaBetaEngine.calculate_metrics(nav_df_dict={"F1": f_df1}, market_benchmark_df=bm_df1)
    assert res1["portfolio_alpha"] == 0.0

    # 2 points
    f_df2 = make_return_df(dates_2, [0.01, 0.02])
    bm_df2 = make_return_df(dates_2, [0.01, 0.02])
    res2 = AlphaBetaEngine.calculate_metrics(nav_df_dict={"F1": f_df2}, market_benchmark_df=bm_df2)
    assert res2["portfolio_alpha"] == 0.0


def test_stress_disjoint_dates():
    """Stress test: Non-matching dates between fund and market benchmark."""
    dates_f = pd.date_range("2025-01-01", periods=10).strftime("%Y-%m-%d").tolist()
    dates_bm = pd.date_range("2025-06-01", periods=10).strftime("%Y-%m-%d").tolist()

    f_ret = [0.01 * i for i in range(10)]
    bm_ret = [0.005 * i for i in range(10)]

    f_df = make_return_df(dates_f, f_ret)
    bm_df = make_return_df(dates_bm, bm_ret)

    res = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": f_df},
        market_benchmark_df=bm_df
    )

    # Disjoint dates cause aligned_test to have 0 points, triggering synthetic benchmark
    assert res["is_synthetic_benchmark"] is True
    assert len(res["scatter_data"]) == 10


def test_stress_partial_date_overlap():
    """Stress test: Only 2 overlapping dates between fund and benchmark."""
    dates_f = ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"]
    dates_bm = ["2025-01-03", "2025-01-04", "2025-01-05", "2025-01-06"]

    f_df = make_return_df(dates_f, [0.01, 0.02, 0.03, 0.04])
    bm_df = make_return_df(dates_bm, [0.01, 0.02, 0.03, 0.04])

    res = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": f_df},
        market_benchmark_df=bm_df
    )

    # Only 2 overlapping points ("2025-01-03", "2025-01-04"), which is < 3 points
    # Should trigger synthetic benchmark fallback!
    assert res["is_synthetic_benchmark"] is True


def test_stress_extreme_values():
    """Stress test: Extremely large values and extreme risk-free rate."""
    dates = pd.date_range("2025-01-01", periods=10).strftime("%Y-%m-%d").tolist()
    f_ret = [1e5, -1e5, 2e5, -2e5, 1e5, -1e5, 2e5, -2e5, 1e5, -1e5]
    bm_ret = [1e4, -1e4, 2e4, -2e4, 1e4, -1e4, 2e4, -2e4, 1e4, -1e4]

    f_df = make_return_df(dates, f_ret)
    bm_df = make_return_df(dates, bm_ret)

    res = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": f_df},
        market_benchmark_df=bm_df,
        risk_free_rate=0.0
    )

    assert not np.isnan(res["portfolio_beta"])
    assert not np.isinf(res["portfolio_beta"])
    assert pytest.approx(res["portfolio_beta"], abs=1e-3) == 10.0


def test_stress_near_zero_beta_treynor_behavior():
    """Stress test: Near-zero beta behavior with Treynor ratio."""
    dates = pd.date_range("2025-01-01", periods=20).strftime("%Y-%m-%d").tolist()
    rng = np.random.RandomState(42)
    bm_ret = rng.normal(0.001, 0.01, size=20)
    # y orthogonal to x so beta is ~ 0
    f_ret = rng.normal(0.005, 0.01, size=20)

    f_df = make_return_df(dates, f_ret)
    bm_df = make_return_df(dates, bm_ret)

    res = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": f_df},
        market_benchmark_df=bm_df,
        risk_free_rate=0.02
    )

    # Beta should be near zero, Treynor ratio should be finite (not NaN or Inf)
    assert not np.isnan(res["treynor_ratio"])
    assert not np.isinf(res["treynor_ratio"])


def test_stress_unusual_benchmark_columns():
    """Stress test: Benchmark DataFrame with alternative column names ('close', '000300.SH', etc.)."""
    dates = pd.date_range("2025-01-01", periods=10).strftime("%Y-%m-%d").tolist()
    nav_values = np.linspace(1.0, 1.1, 10)

    # Column 'close'
    bm_df_close = pd.DataFrame({"date": dates, "close": nav_values})
    f_df = make_return_df(dates, [0.01] * 10)

    res = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": f_df},
        market_benchmark_df=bm_df_close
    )

    assert len(res["scatter_data"]) == 9  # pct_change reduces 10 NAV points to 9 return points


def test_stress_zero_sum_market_values():
    """Stress test: Zero sum or negative fund_market_values dict."""
    dates = pd.date_range("2025-01-01", periods=10).strftime("%Y-%m-%d").tolist()
    f1_df = make_return_df(dates, [0.01] * 10)
    f2_df = make_return_df(dates, [-0.01] * 10)
    bm_df = make_return_df(dates, [0.005] * 10)

    # Net zero sum market values
    res = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": f1_df, "F2": f2_df},
        market_benchmark_df=bm_df,
        fund_market_values={"F1": 100.0, "F2": -100.0}
    )

    assert isinstance(res["portfolio_beta"], float)
    assert not np.isnan(res["portfolio_beta"])


def test_stress_fund_dict_schema_inconsistency():
    """Stress test: Fund DataFrame using column 'close' instead of 'nav' or 'daily_return'."""
    dates = pd.date_range("2025-01-01", periods=10).strftime("%Y-%m-%d").tolist()
    bm_df = make_return_df(dates, [0.01] * 10)
    # Fund DataFrame with column 'close'
    f_df_close = pd.DataFrame({"date": dates, "close": np.linspace(1.0, 1.1, 10)})

    res = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F1": f_df_close},
        market_benchmark_df=bm_df
    )

    # Note: prepare_portfolio_returns ignores 'close' inside a dict!
    # So y_portfolio becomes empty, returning _default_result()
    assert res["portfolio_alpha"] == 0.0
    assert res["scatter_data"] == []
