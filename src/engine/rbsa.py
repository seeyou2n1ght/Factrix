"""RBSA (Returns-Based Style Analysis) Engine.

Performs constrained quadratic programming regression of portfolio daily returns
against benchmark factor indices (large_value, large_growth, small_value, small_growth, bond_index).
"""

from typing import Dict, Any, Union, List, Optional
import pandas as pd
import numpy as np
from scipy.optimize import minimize, nnls

FACTOR_KEYS: List[str] = ['large_value', 'large_growth', 'small_value', 'small_growth', 'bond_index']
FACTOR_LABELS: Dict[str, str] = {
    'large_value': '大盘价值',
    'large_growth': '大盘成长',
    'small_value': '小盘价值',
    'small_growth': '小盘成长',
    'bond_index': '国债指数'
}

# Alias mapping for factor indices column matching
FACTOR_ALIASES: Dict[str, List[str]] = {
    'large_value': ['large_value', '000029.SH', 'large_cap_value', '000029'],
    'large_growth': ['large_growth', '000028.SH', 'large_cap_growth', '000028'],
    'small_value': ['small_value', '000031.SH', 'small_cap_value', '000031'],
    'small_growth': ['small_growth', '000030.SH', 'small_cap_growth', '000030'],
    'bond_index': ['bond_index', '000012.SH', 'bond', '国债指数', '000012']
}


def prepare_portfolio_returns(
    nav_df_dict: Union[Dict[str, pd.DataFrame], pd.DataFrame, pd.Series],
    fund_market_values: Optional[Dict[str, float]] = None
) -> pd.Series:
    """Extract and aggregate daily returns series for the fund portfolio.

    Args:
        nav_df_dict: Dict mapping fund_code -> NAV DataFrame, or a single NAV DataFrame/Series.
        fund_market_values: Optional dict mapping fund_code -> market value amount.

    Returns:
        pd.Series of daily returns indexed by date string ('YYYY-MM-DD').
    """
    if isinstance(nav_df_dict, pd.Series):
        s = nav_df_dict.copy()
        s.index = pd.to_datetime(s.index).strftime('%Y-%m-%d')
        s.name = 'portfolio_return'
        return s.astype(float)

    if isinstance(nav_df_dict, pd.DataFrame):
        df = nav_df_dict.copy()
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            df = df.set_index('date')
        else:
            df.index = pd.to_datetime(df.index).strftime('%Y-%m-%d')

        if 'daily_return' in df.columns:
            return df['daily_return'].astype(float)
        elif 'nav' in df.columns:
            ret = df['nav'].pct_change().dropna()
            return ret.astype(float)
        elif len(df.columns) == 1:
            return df.iloc[:, 0].astype(float)

    if not isinstance(nav_df_dict, dict) or not nav_df_dict:
        return pd.Series(dtype=float)

    # Dictionary of fund DataFrames
    fund_series_list = []
    weights_list = []

    total_val = sum(fund_market_values.values()) if fund_market_values else 0.0

    for code, df_fund in nav_df_dict.items():
        if df_fund is None or df_fund.empty:
            continue
        df_c = df_fund.copy()
        if 'date' in df_c.columns:
            df_c['date'] = pd.to_datetime(df_c['date']).dt.strftime('%Y-%m-%d')
            df_c = df_c.set_index('date')
        else:
            df_c.index = pd.to_datetime(df_c.index).strftime('%Y-%m-%d')
        
        if 'daily_return' in df_c.columns:
            s_ret = df_c['daily_return'].astype(float)
        elif 'nav' in df_c.columns:
            s_ret = df_c['nav'].astype(float).pct_change().dropna()
        else:
            continue

        w = (fund_market_values.get(code, 1.0) / total_val) if (total_val > 0 and fund_market_values) else 1.0
        fund_series_list.append(s_ret)
        weights_list.append(w)

    if not fund_series_list:
        return pd.Series(dtype=float)

    # Normalize weights sum to 1
    w_sum = sum(weights_list)
    norm_weights = [w / w_sum for w in weights_list]

    # Combine into DataFrame aligned on date
    df_combined = pd.concat(fund_series_list, axis=1, keys=range(len(fund_series_list))).dropna()
    if df_combined.empty:
        return pd.Series(dtype=float)

    portfolio_returns = df_combined.dot(norm_weights)
    portfolio_returns.name = 'portfolio_return'
    return portfolio_returns


def extract_benchmark_factor_matrix(
    benchmark_nav_input: Union[Dict[str, pd.DataFrame], pd.DataFrame],
    dates_index: pd.Index
) -> pd.DataFrame:
    """Extract benchmark factor daily returns matrix aligned with target dates.

    Args:
        benchmark_nav_input: Dict of factor DataFrames or a single combined DataFrame.
        dates_index: Index of dates to align against.

    Returns:
        pd.DataFrame of shape (N, 5) with columns FACTOR_KEYS aligned on dates.
    """
    matrix_df = pd.DataFrame(index=dates_index)

    if isinstance(benchmark_nav_input, pd.DataFrame):
        df_bm = benchmark_nav_input.copy()
        if 'date' in df_bm.columns:
            df_bm['date'] = pd.to_datetime(df_bm['date']).dt.strftime('%Y-%m-%d')
            df_bm = df_bm.drop_duplicates(subset='date').set_index('date')
        else:
            df_bm.index = pd.to_datetime(df_bm.index).strftime('%Y-%m-%d')

        for factor_key in FACTOR_KEYS:
            matched_col = None
            aliases = FACTOR_ALIASES.get(factor_key, [factor_key])
            for col in df_bm.columns:
                if col in aliases or str(col).lower() in aliases:
                    matched_col = col
                    break
            
            if matched_col is not None:
                series = df_bm[matched_col].astype(float)
                # Check if values look like NAV rather than daily returns (mean > 0.5)
                if series.mean() > 0.5 and series.min() >= 0:
                    series = series.pct_change().fillna(0.0)
                matrix_df[factor_key] = series
            else:
                # Fallback: if factor column not found, check partial match or generate zero
                matrix_df[factor_key] = 0.0

    elif isinstance(benchmark_nav_input, dict):
        for factor_key in FACTOR_KEYS:
            matched_df = None
            aliases = FACTOR_ALIASES.get(factor_key, [factor_key])
            for name, df_sub in benchmark_nav_input.items():
                if name in aliases or any(a in name for a in aliases):
                    matched_df = df_sub
                    break

            if matched_df is not None and not matched_df.empty:
                df_c = matched_df.copy()
                if 'date' in df_c.columns:
                    df_c['date'] = pd.to_datetime(df_c['date']).dt.strftime('%Y-%m-%d')
                    df_c = df_c.drop_duplicates(subset='date').set_index('date')
                else:
                    df_c.index = pd.to_datetime(df_c.index).strftime('%Y-%m-%d')

                if 'daily_return' in df_c.columns:
                    s_ret = df_c['daily_return'].astype(float)
                elif 'nav' in df_c.columns:
                    s_ret = df_c['nav'].astype(float).pct_change().fillna(0.0)
                else:
                    s_ret = pd.Series(0.0, index=df_c.index)
                matrix_df[factor_key] = s_ret
            else:
                matrix_df[factor_key] = 0.0

    # Align with target dates and fill missing with 0.0
    matrix_df = matrix_df.reindex(dates_index).fillna(0.0)
    return matrix_df


class RBSAEngine:
    """Engine for Returns-Based Style Analysis via Constrained Optimization."""

    @staticmethod
    def calculate(
        nav_df_dict: Union[Dict[str, pd.DataFrame], pd.DataFrame],
        benchmark_nav_dict: Union[Dict[str, pd.DataFrame], pd.DataFrame],
        fund_market_values: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Run constrained RBSA regression on portfolio daily returns.

        Args:
            nav_df_dict: Dict of fund NAV DataFrames or single NAV DataFrame.
            benchmark_nav_dict: Dict or DataFrame of benchmark style factor indices.
            fund_market_values: Optional fund market value weights.

        Returns:
            Dict containing:
                - 'style_weights': Dict[str, float] (factor weights summing to 1.0)
                - 'radar_data': Dict (formatted for radar visualization)
                - 'style_radar_data': Dict (alias for radar_data)
                - 'r_squared': float (goodness-of-fit coefficient R^2)
        """
        # 1. Prepare Portfolio Returns
        y_series = prepare_portfolio_returns(nav_df_dict, fund_market_values)
        if y_series.empty or len(y_series) < 3:
            return RBSAEngine._default_result()

        # 2. Extract Aligned Factor Matrix
        X_df = extract_benchmark_factor_matrix(benchmark_nav_dict, y_series.index)
        
        # Combine y and X to drop rows with missing values
        combined = pd.concat([y_series, X_df], axis=1).dropna()
        if len(combined) < 3:
            return RBSAEngine._default_result()

        y = combined.iloc[:, 0].values.astype(float)
        X = combined.iloc[:, 1:].values.astype(float)
        n_factors = X.shape[1]

        # Check for zero variance in y
        var_y = np.var(y)
        if var_y < 1e-12:
            weights = np.ones(n_factors) / n_factors
            return RBSAEngine._format_result(weights, 1.0)

        # 3. Constrained Optimization: min ||y - X w||^2 s.t. sum(w) = 1, w >= 0
        def objective(w):
            pred = X @ w
            return 0.5 * np.sum((y - pred) ** 2)

        def constraint_sum_one(w):
            return np.sum(w) - 1.0

        init_w = np.ones(n_factors) / n_factors
        bounds = [(0.0, 1.0) for _ in range(n_factors)]
        constraints = [{'type': 'eq', 'fun': constraint_sum_one}]

        res = minimize(objective, init_w, method='SLSQP', bounds=bounds, constraints=constraints)

        if res.success and np.all(res.x >= -1e-5):
            weights = np.maximum(res.x, 0.0)
            w_sum = np.sum(weights)
            if w_sum > 1e-8:
                weights = weights / w_sum
            else:
                weights = init_w
        else:
            # Fallback to NNLS + Normalization
            nnls_w, _ = nnls(X, y)
            w_sum = np.sum(nnls_w)
            if w_sum > 1e-8:
                weights = nnls_w / w_sum
            else:
                weights = init_w

        # 4. Compute Goodness-of-Fit R^2
        y_pred = X @ weights
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        
        if ss_tot > 1e-12:
            r_squared = float(max(0.0, min(1.0, 1.0 - (ss_res / ss_tot))))
        else:
            r_squared = 1.0

        return RBSAEngine._format_result(weights, r_squared)

    @staticmethod
    def _format_result(weights: np.ndarray, r_squared: float) -> Dict[str, Any]:
        """Package optimization weights into standard output format."""
        weights_dict = {factor: float(round(weights[i], 4)) for i, factor in enumerate(FACTOR_KEYS)}
        
        # Ensure exact sum = 1.0 due to float rounding
        total_w = sum(weights_dict.values())
        if total_w > 0:
            weights_dict = {k: float(round(v / total_w, 4)) for k, v in weights_dict.items()}

        radar_data = {
            'labels': [FACTOR_LABELS[k] for k in FACTOR_KEYS],
            'values': [weights_dict[k] for k in FACTOR_KEYS],
            'factor_keys': FACTOR_KEYS
        }

        return {
            'style_weights': weights_dict,
            'radar_data': radar_data,
            'style_radar_data': radar_data,
            'r_squared': float(round(r_squared, 4))
        }

    @staticmethod
    def _default_result() -> Dict[str, Any]:
        """Return equal weights default result when data is insufficient."""
        default_w = np.ones(len(FACTOR_KEYS)) / len(FACTOR_KEYS)
        return RBSAEngine._format_result(default_w, 0.0)
