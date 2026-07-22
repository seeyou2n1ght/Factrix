"""Rebalance Engine with Transaction Friction & Dual Triggers.

Determines optimal rebalancing actions subject to redemption fee tiers
and dual triggers (Sharpe decay & allocation weight drift).
"""

from typing import Dict, Any, List, Union, Optional
import pandas as pd
import numpy as np
from scipy.optimize import minimize

from src.config import get_redemption_fee_rate


class RebalanceEngine:
    """Engine for Quad-Programming Rebalance with Transaction Friction."""

    @staticmethod
    def calculate(
        current_positions: Dict[str, float],
        nav_df_dict: Dict[str, pd.DataFrame],
        holding_days: Dict[str, int]
    ) -> Dict[str, Any]:
        """Calculate optimal rebalancing trade actions and fee-saving tips.

        Args:
            current_positions: Dict mapping fund_code -> current market value in RMB.
            nav_df_dict: Dict mapping fund_code -> NAV DataFrame.
            holding_days: Dict mapping fund_code -> holding days integer.

        Returns:
            Dict containing:
                - 'trade_actions': List of trade action dicts:
                                  [{'action': 'SELL'/'BUY', 'fund_code': str, 'amount': float, 'fee_saved_tip': str}]
                - 'net_benefit': float (expected net gain after fees in RMB)
                - 'trigger_reasons': List[str] (reasons triggering rebalance)
        """
        # 1. Validation and Setup
        valid_funds = [code for code, val in current_positions.items() if val > 0 and code in nav_df_dict]
        total_market_value = float(sum(current_positions[code] for code in valid_funds))

        if not valid_funds or total_market_value <= 0:
            return RebalanceEngine._default_result()

        n_funds = len(valid_funds)
        if n_funds == 1:
            return {
                'trade_actions': [],
                'net_benefit': 0.0,
                'trigger_reasons': ['单一持仓无需调仓']
            }

        # Current portfolio weight vector w0
        w0 = np.array([current_positions[code] / total_market_value for code in valid_funds], dtype=float)

        # 2. Extract Returns, Sharpe Ratios, Covariance
        fund_return_series: Dict[str, pd.Series] = {}
        sharpe_ratios = {}

        for code in valid_funds:
            df_nav = nav_df_dict[code]
            # Build a date-indexed Series for proper alignment later
            if 'date' in df_nav.columns and 'daily_return' in df_nav.columns:
                s = pd.Series(
                    df_nav['daily_return'].astype(float).values,
                    index=pd.to_datetime(df_nav['date'], errors='coerce'),
                    name=code
                ).dropna()
            elif 'date' in df_nav.columns and 'nav' in df_nav.columns:
                prices = pd.Series(
                    df_nav['nav'].astype(float).values,
                    index=pd.to_datetime(df_nav['date'], errors='coerce'),
                    name=code
                )
                s = prices.pct_change().dropna()
            elif 'daily_return' in df_nav.columns:
                s = pd.Series(
                    df_nav['daily_return'].astype(float).values,
                    name=code
                ).dropna()
            else:
                s = pd.Series(np.zeros(20), name=code)

            if len(s) < 5:
                s = pd.Series(np.zeros(20), name=code)

            fund_return_series[code] = s
            ret = s.values
            mean_ret = float(np.mean(ret))
            std_ret = float(np.std(ret, ddof=1)) if len(ret) > 1 else 1e-4

            # Annualized Sharpe (assuming risk free rate = 1.5% p.a. = 0.00006 daily)
            rf_daily = 0.015 / 252.0
            sharpe = ((mean_ret - rf_daily) / std_ret * np.sqrt(252.0)) if std_ret > 1e-6 else 0.0
            sharpe_ratios[code] = sharpe

        # Align daily returns into matrix via pd.concat (handles different-length series by date)
        df_ret_matrix = pd.concat(fund_return_series.values(), axis=1, join='inner')
        df_ret_matrix.columns = list(fund_return_series.keys())
        df_ret_matrix = df_ret_matrix.dropna()
        if len(df_ret_matrix) >= 5:
            mu = df_ret_matrix.mean().values * 252.0  # Annualized expected return
            cov = df_ret_matrix.cov().values * 252.0   # Annualized covariance matrix
        else:
            mu = np.ones(n_funds) * 0.05
            cov = np.eye(n_funds) * 0.02

        # 3. Dual Triggers Evaluation
        trigger_reasons = []

        # Trigger 1: Sharpe ratio decay / divergence
        sharpes = list(sharpe_ratios.values())
        max_sharpe, min_sharpe = max(sharpes), min(sharpes)
        if (max_sharpe - min_sharpe) > 0.8 or min_sharpe < -0.2:
            trigger_reasons.append(
                f"夏普比率显著衰减: 最佳基金夏普({max_sharpe:.2f}) 与 最差基金夏普({min_sharpe:.2f}) 差距拉大"
            )

        # Trigger 2: Allocation weight drift
        target_equal_w = 1.0 / n_funds
        max_weight_drift = max(abs(w - target_equal_w) for w in w0)
        if max_weight_drift > 0.15:
            trigger_reasons.append(
                f"持仓比例发生显著偏离: 最大的偏离度达到 {max_weight_drift*100:.1f}%"
            )

        # 4. Redemption Fee Tiers Vector
        fee_rates = np.array([get_redemption_fee_rate(holding_days.get(code, 365)) for code in valid_funds], dtype=float)

        # 5. Quad-Programming Optimizer with Friction Penalty
        # Maximize: w^T mu - (gamma / 2) w^T Sigma w - sum( fee_i * max(0, w0_i - w_i) )
        gamma = 1.5  # Risk aversion coefficient

        def objective(w):
            ret_term = np.dot(w, mu)
            risk_term = 0.5 * gamma * np.dot(w, np.dot(cov, w))
            # Sell friction cost (only on reduced weight w0_i - w_i)
            sell_amounts = np.maximum(0.0, w0 - w)
            friction_cost = np.sum(fee_rates * sell_amounts)
            return -(ret_term - risk_term - friction_cost)

        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
        bounds = [(0.0, 1.0) for _ in range(n_funds)]

        res = minimize(objective, w0, method='SLSQP', bounds=bounds, constraints=constraints)

        if res.success:
            w_opt = np.maximum(0.0, res.x)
            w_opt = w_opt / np.sum(w_opt)
        else:
            # Equal weight fallback
            w_opt = np.ones(n_funds) / n_funds

        # 6. Generate Trade Actions and Fee Saving Tips
        trade_actions: List[Dict[str, Any]] = []
        total_sell_fees = 0.0

        for i, code in enumerate(valid_funds):
            dw = w_opt[i] - w0[i]
            trade_amount = abs(dw) * total_market_value

            # Ignore tiny rebalances (< 100 RMB or < 0.5% weight change)
            if trade_amount < 100.0 or abs(dw) < 0.005:
                continue

            h_days = holding_days.get(code, 365)
            fee_rate = fee_rates[i]
            fee_tip = ""

            if dw < 0:  # SELL Action
                action_type = 'SELL'
                total_sell_fees += trade_amount * fee_rate

                # Check if holding days is close to fee tier boundary
                if h_days < 7:
                    days_left = 7 - h_days
                    saving_rate = 0.015 - 0.0075
                    est_saved = trade_amount * saving_rate
                    fee_tip = f"已持有 {h_days} 天，建议再持有 {days_left} 天避开 1.5% 惩罚费率 (预计可省 {est_saved:.1f} 元)"
                elif h_days < 30 and h_days >= 23:
                    days_left = 30 - h_days
                    saving_rate = 0.0075 - 0.0050
                    est_saved = trade_amount * saving_rate
                    fee_tip = f"已持有 {h_days} 天，建议再持有 {days_left} 天降低赎回费率 (预计可省 {est_saved:.1f} 元)"

            else:  # BUY Action
                action_type = 'BUY'

            trade_actions.append({
                'action': action_type,
                'fund_code': code,
                'amount': float(round(trade_amount, 2)),
                'fee_saved_tip': fee_tip
            })

        # Calculate estimated Net Benefit in RMB
        # Net Benefit = (Expected return improvement over 1 year) * Total Value - Total Fees
        curr_exp_ret = float(np.dot(w0, mu))
        opt_exp_ret = float(np.dot(w_opt, mu))
        gross_benefit = (opt_exp_ret - curr_exp_ret) * total_market_value
        net_benefit = float(round(gross_benefit - total_sell_fees, 2))

        if not trigger_reasons:
            if abs(net_benefit) < 50.0:
                trigger_reasons.append("当前组合配置相对均衡，暂未触发调仓预警门槛")
            else:
                trigger_reasons.append("优化模型检测到调仓能有效提升收益风险比")

        return {
            'trade_actions': trade_actions,
            'net_benefit': net_benefit,
            'trigger_reasons': trigger_reasons
        }

    @staticmethod
    def _default_result() -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            'trade_actions': [],
            'net_benefit': 0.0,
            'trigger_reasons': ['暂无有效持仓数据']
        }
