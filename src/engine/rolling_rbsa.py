"""Rolling RBSA Engine.

Performs 60-day (configurable) rolling window style attribution over time to detect
style drift, factor variance, and emit drift warning signals.
"""

from typing import Dict, Any, Union, Optional
import pandas as pd
import numpy as np
from scipy.optimize import minimize, nnls

from src.engine.rbsa import (
    prepare_portfolio_returns, extract_benchmark_factor_matrix,
    FACTOR_KEYS, FACTOR_LABELS,
)


def _solve_window_rbsa(y: np.ndarray, X: np.ndarray) -> Dict[str, float]:
    """Run constrained RBSA regression on a single window slice.

    Directly solves the quadratic program without re-parsing NAV/benchmark data.
    Falls back to NNLS + normalization on optimizer failure.

    Args:
        y: Portfolio daily returns array (N,).
        X: Factor matrix (N, 5).

    Returns:
        Dict mapping factor_key -> weight float.
    """
    n_factors = X.shape[1]
    init_w = np.ones(n_factors) / n_factors

    var_y = np.var(y)
    if var_y < 1e-12:
        return {FACTOR_KEYS[i]: float(init_w[i]) for i in range(n_factors)}

    def objective(w):
        return 0.5 * np.sum((y - X @ w) ** 2)

    bounds = [(0.0, 1.0)] * n_factors
    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]

    res = minimize(objective, init_w, method='SLSQP', bounds=bounds, constraints=constraints)

    if res.success and np.all(res.x >= -1e-5):
        weights = np.maximum(res.x, 0.0)
        w_sum = np.sum(weights)
        if w_sum > 1e-8:
            weights = weights / w_sum
        else:
            weights = init_w
    else:
        nnls_w, _ = nnls(X, y)
        w_sum = np.sum(nnls_w)
        if w_sum > 1e-8:
            weights = nnls_w / w_sum
        else:
            weights = init_w

    # Normalize to exact sum=1 and round
    total = float(np.sum(weights))
    if total > 1e-8:
        weights = weights / total

    return {FACTOR_KEYS[i]: float(round(weights[i], 4)) for i in range(n_factors)}


class RollingRBSAEngine:
    """Engine for Rolling RBSA Style Drift & Variance Analysis."""

    @staticmethod
    def calculate(
        nav_df_dict: Union[Dict[str, pd.DataFrame], pd.DataFrame],
        benchmark_nav_dict: Union[Dict[str, pd.DataFrame], pd.DataFrame],
        window: int = 60,
        fund_market_values: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Calculate rolling window style weights, factor variance, and drift warning.

        Pre-computes the aligned portfolio returns and factor matrix once, then
        slices each rolling window for direct optimization without redundant parsing.

        Args:
            nav_df_dict: Dict of fund NAV DataFrames or single NAV DataFrame.
            benchmark_nav_dict: Dict or DataFrame of benchmark style factor indices.
            window: Rolling window size in trading days (default: 60).
            fund_market_values: Optional fund market value weights.

        Returns:
            Dict containing:
                - 'rolling_series': pd.DataFrame (index: date, columns: FACTOR_KEYS)
                - 'rolling_weights': pd.DataFrame (alias for rolling_series)
                - 'factor_variance': Dict[str, float] (variance of each factor weight over time)
                - 'drift_variance': Dict[str, float] (alias for factor_variance)
                - 'drift_warning': bool (True if style drift exceeds risk threshold)
        """
        # 1. Pre-compute aligned portfolio returns and factor matrix (once)
        y_series = prepare_portfolio_returns(nav_df_dict, fund_market_values)
        if y_series.empty:
            return RollingRBSAEngine._empty_result()

        X_df = extract_benchmark_factor_matrix(benchmark_nav_dict, y_series.index)
        combined = pd.concat([y_series, X_df], axis=1).dropna()

        n_rows = len(combined)
        if n_rows < 10:
            return RollingRBSAEngine._empty_result()

        effective_window = min(window, n_rows)
        dates = combined.index

        # Pre-extract numpy arrays for fast slicing
        y_all = combined.iloc[:, 0].values.astype(float)
        X_all = combined.iloc[:, 1:].values.astype(float)

        records = []
        recorded_dates = []

        # 2. Rolling Window — slice arrays directly, no re-parsing
        for i in range(effective_window, n_rows + 1):
            y_sub = y_all[i - effective_window:i]
            X_sub = X_all[i - effective_window:i, :]
            window_date = dates[i - 1]

            weights = _solve_window_rbsa(y_sub, X_sub)
            records.append(weights)
            recorded_dates.append(window_date)

        if not records:
            return RollingRBSAEngine._empty_result()

        rolling_df = pd.DataFrame(records, index=recorded_dates)
        for factor in FACTOR_KEYS:
            if factor not in rolling_df.columns:
                rolling_df[factor] = 0.2
        rolling_df = rolling_df[FACTOR_KEYS]

        # 3. Compute Factor Variances across time
        factor_variance: Dict[str, float] = {}
        for factor in FACTOR_KEYS:
            var_val = float(rolling_df[factor].var(ddof=1)) if len(rolling_df) > 1 else 0.0
            factor_variance[factor] = float(round(var_val, 6))

        # 4. Determine Drift Warning
        equity_factors = ['large_value', 'large_growth', 'small_value', 'small_growth']
        max_equity_var = max(factor_variance.get(f, 0.0) for f in equity_factors)

        if len(rolling_df) >= 2:
            first_w = rolling_df.iloc[0][equity_factors].values
            last_w = rolling_df.iloc[-1][equity_factors].values
            max_drift = float(np.max(np.abs(first_w - last_w)))
        else:
            max_drift = 0.0

        drift_warning = bool(max_equity_var > 0.015 or max_drift > 0.30)

        return {
            'rolling_series': rolling_df,
            'rolling_weights': rolling_df,
            'factor_variance': factor_variance,
            'drift_variance': factor_variance,
            'drift_warning': drift_warning
        }

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        """Return default empty structure."""
        df_empty = pd.DataFrame(columns=FACTOR_KEYS)
        var_empty = {f: 0.0 for f in FACTOR_KEYS}
        return {
            'rolling_series': df_empty,
            'rolling_weights': df_empty,
            'factor_variance': var_empty,
            'drift_variance': var_empty,
            'drift_warning': False
        }
