"""CVaR & Black Swan Stress Testing Engine.

Calculates 95% and 99% Cornish-Fisher modified Expected Shortfall (CVaR)
and simulates portfolio loss under historical Black Swan stress scenarios.
"""

from typing import Dict, Any, Union, Optional
import pandas as pd
import numpy as np
from scipy.stats import norm, skew, kurtosis

from src.engine.rbsa import prepare_portfolio_returns


class CVaRStressEngine:
    """Engine for CVaR and Historical Black Swan Stress Testing."""

    @staticmethod
    def calculate(
        nav_df_dict: Union[Dict[str, pd.DataFrame], pd.DataFrame],
        fund_market_values: Dict[str, float],
        rbsa_res: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculate Cornish-Fisher 95%/99% CVaR and simulate stress scenarios.

        Args:
            nav_df_dict: Dict of fund NAV DataFrames or single NAV DataFrame.
            fund_market_values: Dict of fund market values in RMB.
            rbsa_res: Optional RBSA engine result dict. When provided, uses precise
                      style factor weights for equity/bond exposure estimation instead
                      of the crude volatility proxy.

        Returns:
            Dict containing:
                - 'cvar_95': float (95% confidence CVaR loss percentage)
                - 'cvar_99': float (99% confidence CVaR loss percentage)
                - 'stress_results': Dict[str, Dict] (stress scenario results)
                - 'stress_scenarios': Dict[str, Dict] (alias for stress_results)
        """
        # 1. Prepare Portfolio Returns
        y_series = prepare_portfolio_returns(nav_df_dict, fund_market_values)
        total_market_value = float(sum(v for v in fund_market_values.values() if v > 0)) if fund_market_values else 100000.0

        if y_series.empty or len(y_series) < 5:
            return CVaRStressEngine._default_result(total_market_value)

        returns = y_series.values.astype(float)

        # 2. Compute Cornish-Fisher CVaR at 95% and 99% Confidence
        cvar_95 = CVaRStressEngine._calc_cornish_fisher_cvar(returns, alpha=0.95)
        cvar_99 = CVaRStressEngine._calc_cornish_fisher_cvar(returns, alpha=0.99)

        # 3. Estimate Equity vs Bond Exposure
        # Prefer RBSA style weights when available (more accurate than volatility proxy)
        equity_weight, bond_weight = CVaRStressEngine._estimate_equity_bond_weights(
            returns, rbsa_res
        )

        # Historical Stress Test Scenarios Definition
        # (Equity shock %, Bond shock %)
        scenarios_def = {
            '2015_equity_crash': {
                'name': '2015年股市踩踏',
                'desc': '模拟2015年股市千股跌停极值踩踏场景 (股票-35%, 债券+2%)',
                'eq_shock': -0.35,
                'bond_shock': 0.02,
            },
            '2022_dual_crash': {
                'name': '2022年股债双杀',
                'desc': '模拟2022年底市场流动性冲击股债同跌场景 (股票-15%, 债券-5%)',
                'eq_shock': -0.15,
                'bond_shock': -0.05,
            },
            '2020_covid_shock': {
                'name': '2020年全球疫情暴跌',
                'desc': '模拟2020年初全球疫情黑天鹅市场大跌场景 (股票-20%, 债券+1%)',
                'eq_shock': -0.20,
                'bond_shock': 0.01,
            }
        }

        stress_results: Dict[str, Dict[str, Any]] = {}

        for key, sc in scenarios_def.items():
            # Projected return under scenario
            proj_return = equity_weight * sc['eq_shock'] + bond_weight * sc['bond_shock']
            loss_pct = float(round(-min(0.0, proj_return), 4))
            loss_amount = float(round(loss_pct * total_market_value, 2))

            stress_results[key] = {
                'scenario_name': sc['name'],
                'description': sc['desc'],
                'loss_pct': loss_pct,
                'loss_amount': loss_amount,
                'projected_return': float(round(proj_return, 4))
            }

        return {
            'cvar_95': float(round(cvar_95, 4)),
            'cvar_99': float(round(cvar_99, 4)),
            'stress_results': stress_results,
            'stress_scenarios': stress_results
        }

    @staticmethod
    def _calc_cornish_fisher_cvar(returns: np.ndarray, alpha: float) -> float:
        """Calculate Cornish-Fisher modified CVaR (Expected Shortfall).

        Args:
            returns: Array of daily returns.
            alpha: Confidence level (0.95 or 0.99).

        Returns:
            CVaR loss fraction as positive float (e.g. 0.045 for 4.5% loss).
        """
        n = len(returns)
        if n < 5:
            return 0.0

        mu = float(np.mean(returns))
        sigma = float(np.std(returns, ddof=1))

        if sigma < 1e-12:
            return float(max(0.0, -mu))

        # Skewness and excess kurtosis
        s = float(skew(returns))
        k = float(kurtosis(returns, fisher=True))

        p = 1.0 - alpha  # tail probability (0.05 or 0.01)
        z_p = norm.ppf(p)  # standard normal quantile (negative)

        # Cornish-Fisher Expansion Quantile Adjustment
        z_cf = (
            z_p
            + (s / 6.0) * (z_p**2 - 1.0)
            + (k / 24.0) * (z_p**3 - 3.0 * z_p)
            - (s**2 / 36.0) * (2.0 * z_p**3 - 5.0 * z_p)
        )

        var_threshold = mu + z_cf * sigma

        # Empirical tail loss below Cornish-Fisher VaR threshold
        tail_returns = returns[returns <= var_threshold]
        if len(tail_returns) > 0:
            cvar_val = -float(np.mean(tail_returns))
        else:
            # Fallback to parametric formula
            cvar_val = -var_threshold

        return float(max(0.0, cvar_val))

    @staticmethod
    def _estimate_equity_bond_weights(
        returns: np.ndarray, rbsa_res: Optional[Dict[str, Any]] = None
    ) -> tuple:
        """Estimate portfolio equity and bond exposure weights.

        Uses RBSA style factor weights when available for precise attribution.
        Falls back to a daily volatility proxy when RBSA data is missing.

        Args:
            returns: Array of daily portfolio returns.
            rbsa_res: Optional RBSA engine result dict.

        Returns:
            Tuple of (equity_weight, bond_weight) summing to 1.0.
        """
        # Try RBSA style weights first
        if rbsa_res and isinstance(rbsa_res, dict):
            style_w = rbsa_res.get('style_weights', {})
            if style_w and isinstance(style_w, dict):
                equity_factors = ['large_value', 'large_growth', 'small_value', 'small_growth']
                equity_weight = sum(float(style_w.get(f, 0.0)) for f in equity_factors)
                bond_weight = float(style_w.get('bond_index', 0.0))
                total = equity_weight + bond_weight
                if total > 1e-6:
                    return (equity_weight / total, bond_weight / total)

        # Fallback: volatility-based proxy
        daily_std = float(np.std(returns))
        if daily_std < 0.001:
            return (0.1, 0.9)
        elif daily_std > 0.015:
            return (0.9, 0.1)
        else:
            equity_weight = min(0.95, max(0.05, daily_std / 0.015))
            return (equity_weight, 1.0 - equity_weight)

    @staticmethod
    def _default_result(total_market_value: float) -> Dict[str, Any]:
        """Return zero risk default structure."""
        empty_stress = {
            '2015_equity_crash': {'scenario_name': '2015年股市踩踏', 'loss_pct': 0.0, 'loss_amount': 0.0},
            '2022_dual_crash': {'scenario_name': '2022年股债双杀', 'loss_pct': 0.0, 'loss_amount': 0.0},
            '2020_covid_shock': {'scenario_name': '2020年全球疫情暴跌', 'loss_pct': 0.0, 'loss_amount': 0.0}
        }
        return {
            'cvar_95': 0.0,
            'cvar_99': 0.0,
            'stress_results': empty_stress,
            'stress_scenarios': empty_stress
        }
