"""Prospect Theory & Omega Ratio Engine.

Calculates rolling 20d/60d win rate (W), payoff ratio (O),
Kahneman-Tversky prospect theory utility V(r), and the Omega ratio.
"""

from typing import Dict, Any, Union, Optional
import pandas as pd
import numpy as np

from src.config import PROSPECT_LAMBDA, PROSPECT_ALPHA, PROSPECT_BETA
from src.engine.rbsa import prepare_portfolio_returns


class ProspectTheoryEngine:
    """Engine for Kahneman-Tversky Prospect Utility, Win/Loss Matrix, and Omega Ratio."""

    @staticmethod
    def calculate(
        nav_df_dict: Union[Dict[str, pd.DataFrame], pd.DataFrame],
        fund_market_values: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Calculate win rate, payoff ratio, prospect utility, and Omega ratio.

        Args:
            nav_df_dict: Dict of fund NAV DataFrames or single NAV DataFrame.
            fund_market_values: Optional fund market value weights.

        Returns:
            Dict containing:
                - 'win_rate': float (proportion of positive holding periods, in [0, 1])
                - 'payoff_ratio': float (average gain magnitude / average loss magnitude)
                - 'prospect_utility': float (Kahneman-Tversky utility score)
                - 'omega_ratio': float (Omega ratio with zero threshold)
        """
        # 1. Prepare Daily Portfolio Return Series
        daily_returns_s = prepare_portfolio_returns(nav_df_dict, fund_market_values)
        if daily_returns_s.empty or len(daily_returns_s) < 5:
            return ProspectTheoryEngine._default_result()

        daily_returns = daily_returns_s.values.astype(float)

        # Reconstruct portfolio cumulative NAV curve to compute rolling 20d and 60d holding returns
        cum_nav = np.cumprod(1.0 + daily_returns)
        
        rolling_returns_list = []
        for hold_window in [20, 60]:
            if len(cum_nav) > hold_window:
                r_h = (cum_nav[hold_window:] / cum_nav[:-hold_window]) - 1.0
                rolling_returns_list.extend(r_h.tolist())

        if not rolling_returns_list:
            # Fall back to daily returns if data points < 20
            eval_returns = daily_returns
        else:
            eval_returns = np.array(rolling_returns_list, dtype=float)

        # 2. Win Rate (W) and Payoff Ratio (O)
        gains = eval_returns[eval_returns > 1e-8]
        losses = eval_returns[eval_returns < -1e-8]
        n_total = len(eval_returns)

        win_rate = float(len(gains) / n_total) if n_total > 0 else 0.0

        avg_gain = float(np.mean(gains)) if len(gains) > 0 else 0.0
        avg_loss = float(np.abs(np.mean(losses))) if len(losses) > 0 else 0.0

        if avg_loss > 1e-8:
            payoff_ratio = float(round(avg_gain / avg_loss, 4))
        elif avg_gain > 1e-8:
            payoff_ratio = 10.0  # Cap when no losses occur
        else:
            payoff_ratio = 1.0

        # 3. Kahneman-Tversky Prospect Utility V(r)
        # v(x) = x^alpha if x >= 0 else -lambda * (-x)^beta
        pos_part = np.where(eval_returns >= 0, np.power(np.maximum(0.0, eval_returns), PROSPECT_ALPHA), 0.0)
        neg_part = np.where(eval_returns < 0, -PROSPECT_LAMBDA * np.power(np.maximum(0.0, -eval_returns), PROSPECT_BETA), 0.0)
        v_values = pos_part + neg_part
        prospect_utility = float(round(np.mean(v_values), 6))

        # 4. Omega Ratio Omega(L) with Threshold L = 0.0
        upside = np.maximum(0.0, eval_returns)
        downside = np.maximum(0.0, -eval_returns)

        sum_downside = np.sum(downside)
        sum_upside = np.sum(upside)

        if sum_downside > 1e-12:
            omega_ratio = float(round(sum_upside / sum_downside, 4))
        elif sum_upside > 1e-12:
            omega_ratio = 99.0  # High cap when no downside risk
        else:
            omega_ratio = 1.0

        return {
            'win_rate': float(round(win_rate, 4)),
            'payoff_ratio': payoff_ratio,
            'prospect_utility': prospect_utility,
            'omega_ratio': omega_ratio
        }

    @staticmethod
    def _default_result() -> Dict[str, Any]:
        """Return default zero result for invalid/insufficient data."""
        return {
            'win_rate': 0.0,
            'payoff_ratio': 1.0,
            'prospect_utility': 0.0,
            'omega_ratio': 1.0
        }
