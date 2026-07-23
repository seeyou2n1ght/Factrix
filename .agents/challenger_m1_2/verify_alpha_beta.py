import numpy as np
import pandas as pd
from scipy import stats
from src.engine.alpha_beta import AlphaBetaEngine

def make_df(returns, start_date="2025-01-01"):
    dates = pd.date_range(start=start_date, periods=len(returns), freq="D").strftime("%Y-%m-%d")
    navs = np.cumprod(1.0 + returns)
    return pd.DataFrame({"date": dates, "nav": navs, "daily_return": returns})

def run_deep_verification():
    print("=== DEEP EDGE CASE & MULTI-FUND NUMERICAL VERIFICATION ===")
    rf = 0.02
    rf_daily = rf / 252.0

    # 1. Multi-fund Portfolio Verification
    n = 100
    rng = np.random.RandomState(777)
    x = rng.normal(0.0008, 0.012, size=n)
    f1_ret = 1.2 * x + rng.normal(0.0001, 0.002, size=n)
    f2_ret = 0.8 * x + rng.normal(-0.0001, 0.002, size=n)

    bm_df = make_df(x)
    f1_df = make_df(f1_ret)
    f2_df = make_df(f2_ret)

    nav_dict = {"F1": f1_df, "F2": f2_df}
    market_vals = {"F1": 600000.0, "F2": 400000.0} # 60% F1, 40% F2

    res = AlphaBetaEngine.calculate_metrics(
        nav_df_dict=nav_dict,
        market_benchmark_df=bm_df,
        fund_market_values=market_vals,
        risk_free_rate=rf
    )

    p_ret = 0.6 * f1_ret + 0.4 * f2_ret
    cov_p = np.cov(x - rf_daily, p_ret - rf_daily, ddof=1)
    ref_p_beta = cov_p[0, 1] / np.var(x - rf_daily, ddof=1)
    ref_p_alpha = (np.mean(p_ret - rf_daily) - ref_p_beta * np.mean(x - rf_daily)) * 252.0

    print("\n--- Multi-fund Weighted Portfolio ---")
    print(f"Portfolio Beta:  Engine={res['portfolio_beta']:.8f}, Ref={ref_p_beta:.8f}, Diff={abs(res['portfolio_beta'] - ref_p_beta):.2e}")
    print(f"Portfolio Alpha: Engine={res['portfolio_alpha']:.8f}, Ref={ref_p_alpha:.8f}, Diff={abs(res['portfolio_alpha'] - ref_p_alpha):.2e}")

    # Verify Fund Level Metrics
    f1_m = res["fund_metrics"]["F1"]
    cov_f1 = np.cov(x - rf_daily, f1_ret - rf_daily, ddof=1)
    ref_f1_beta = cov_f1[0, 1] / np.var(x - rf_daily, ddof=1)
    ref_f1_alpha = (np.mean(f1_ret - rf_daily) - ref_f1_beta * np.mean(x - rf_daily)) * 252.0
    print(f"Fund F1 Beta:    Engine={f1_m['beta']:.8f}, Ref={ref_f1_beta:.8f}, Diff={abs(f1_m['beta'] - ref_f1_beta):.2e}")
    print(f"Fund F1 Alpha:   Engine={f1_m['alpha']:.8f}, Ref={ref_f1_alpha:.8f}, Diff={abs(f1_m['alpha'] - ref_f1_alpha):.2e}")

    # 2. Negative Beta Case
    y_neg = -1.5 * x
    f_neg_df = make_df(y_neg)
    res_neg = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F_NEG": f_neg_df},
        market_benchmark_df=bm_df,
        risk_free_rate=rf
    )
    cov_neg = np.cov(x - rf_daily, y_neg - rf_daily, ddof=1)
    ref_neg_beta = cov_neg[0, 0] # wait, cov_neg[0,1]
    ref_neg_beta = cov_neg[0, 1] / np.var(x - rf_daily, ddof=1)
    print("\n--- Negative Beta Case ---")
    print(f"Negative Beta:   Engine={res_neg['portfolio_beta']:.8f}, Ref={ref_neg_beta:.8f}, Diff={abs(res_neg['portfolio_beta'] - ref_neg_beta):.2e}")
    print(f"Treynor Ratio:   Engine={res_neg['treynor_ratio']:.8f}")

    # 3. High Floating-Point Scale Precision Test (100,000 points)
    n_huge = 100000
    x_huge = rng.normal(0.0001, 0.01, size=n_huge)
    y_huge = 1.05 * x_huge + 0.00005
    bm_huge = make_df(x_huge)
    f_huge = make_df(y_huge)

    res_huge = AlphaBetaEngine.calculate_metrics(
        nav_df_dict={"F_HUGE": f_huge},
        market_benchmark_df=bm_huge,
        risk_free_rate=rf
    )
    print("\n--- High Volume Precision Test (N=100,000) ---")
    print(f"Portfolio Beta:  Engine={res_huge['portfolio_beta']:.8f}")
    print(f"Portfolio R2:    Engine={res_huge['portfolio_r2']:.8f}")

if __name__ == "__main__":
    run_deep_verification()
