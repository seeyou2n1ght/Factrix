"""Alpha & Beta Performance Attribution Engine.

Calculates CAPM Alpha, Beta, R^2, Sharpe ratio, Treynor ratio,
Information ratio, and Tracking Error for both individual funds
and the overall weighted portfolio.
"""

from typing import Dict, Any, List, Optional, Union
import numpy as np
import pandas as pd

from src.engine.rbsa import prepare_portfolio_returns


class AlphaBetaEngine:
    """Engine for CAPM Alpha/Beta performance attribution and risk-adjusted metrics."""

    @staticmethod
    def calculate_metrics(
        nav_df_dict: Union[Dict[str, pd.DataFrame], pd.DataFrame, pd.Series],
        market_benchmark_df: Optional[pd.DataFrame] = None,
        fund_market_values: Optional[Dict[str, float]] = None,
        risk_free_rate: float = 0.02,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Calculate annualized Alpha, Beta, R2, Sharpe, Treynor, IR, TE, and scatter data.

        Args:
            nav_df_dict: Dict mapping fund code to NAV DataFrame, or single NAV DataFrame/Series.
            market_benchmark_df: Benchmark index DataFrame (e.g. 000300.SH).
            fund_market_values: Dict mapping fund code to market value (RMB).
            risk_free_rate: Annualized risk-free rate (default 0.02, i.e. 2%).
            **kwargs: Extra parameters (e.g. rf_rate alias).

        Returns:
            Dict containing portfolio metrics, fund metrics, scatter dataset, and synthetic benchmark flag.
        """
        # Handle rf_rate kwarg alias if provided
        if "rf_rate" in kwargs and kwargs["rf_rate"] is not None:
            try:
                risk_free_rate = float(kwargs["rf_rate"])
            except (ValueError, TypeError):
                pass

        # 1. Prepare portfolio daily return series
        y_portfolio = prepare_portfolio_returns(nav_df_dict, fund_market_values)
        if y_portfolio.empty or len(y_portfolio) < 3:
            return AlphaBetaEngine._default_result()

        # 2. Extract benchmark daily return series
        bm_series = AlphaBetaEngine._extract_benchmark_series(market_benchmark_df)

        # 3. Check for benchmark validity or fallback to synthetic benchmark
        is_synthetic = False
        if bm_series is None or bm_series.empty:
            bm_series = AlphaBetaEngine._generate_synthetic_benchmark(y_portfolio)
            is_synthetic = True
        else:
            # Align dates to test overlap
            aligned_test = pd.concat([y_portfolio, bm_series], axis=1, join="inner").dropna()
            if len(aligned_test) < 3:
                bm_series = AlphaBetaEngine._generate_synthetic_benchmark(y_portfolio)
                is_synthetic = True

        # 4. Align portfolio and benchmark daily returns
        df_aligned = pd.concat([y_portfolio, bm_series], axis=1, join="inner").dropna()
        # Ensure finite values only
        df_aligned = df_aligned[np.isfinite(df_aligned.iloc[:, 0]) & np.isfinite(df_aligned.iloc[:, 1])]

        if len(df_aligned) < 3:
            return AlphaBetaEngine._default_result()

        y_ret = df_aligned.iloc[:, 0].values.astype(float)
        x_ret = df_aligned.iloc[:, 1].values.astype(float)
        aligned_dates = df_aligned.index.astype(str).tolist()

        # 5. Compute portfolio metrics
        p_metrics = AlphaBetaEngine._compute_metrics_from_aligned_series(
            y_ret=y_ret,
            x_ret=x_ret,
            risk_free_rate=risk_free_rate
        )

        # 6. Build regression scatter plot dataset
        rf_daily = risk_free_rate / 252.0
        scatter_data: List[Dict[str, Any]] = []
        for d, p_r, m_r in zip(aligned_dates, y_ret, x_ret):
            scatter_data.append({
                "date": str(d),
                "market_return": round(float(m_r), 6),
                "portfolio_return": round(float(p_r), 6),
                "portfolio_excess_return": round(float(p_r - rf_daily), 6),
                "market_excess_return": round(float(m_r - rf_daily), 6)
            })

        # 7. Compute single fund metrics (fund_metrics)
        fund_metrics: Dict[str, Dict[str, float]] = {}
        if isinstance(nav_df_dict, dict):
            for code, df_fund in nav_df_dict.items():
                if df_fund is None or (isinstance(df_fund, pd.DataFrame) and df_fund.empty):
                    continue
                s_fund = prepare_portfolio_returns({code: df_fund}, {code: 1.0})
                if s_fund.empty:
                    continue

                df_f_aligned = pd.concat([s_fund, bm_series], axis=1, join="inner").dropna()
                df_f_aligned = df_f_aligned[
                    np.isfinite(df_f_aligned.iloc[:, 0]) & np.isfinite(df_f_aligned.iloc[:, 1])
                ]

                if len(df_f_aligned) < 3:
                    fund_metrics[str(code)] = {
                        "alpha": 0.0,
                        "beta": 0.0,
                        "r2": 0.0,
                        "sharpe_ratio": 0.0,
                        "treynor_ratio": 0.0,
                        "information_ratio": 0.0,
                        "tracking_error": 0.0
                    }
                else:
                    fy_ret = df_f_aligned.iloc[:, 0].values.astype(float)
                    fx_ret = df_f_aligned.iloc[:, 1].values.astype(float)
                    f_m = AlphaBetaEngine._compute_metrics_from_aligned_series(
                        y_ret=fy_ret,
                        x_ret=fx_ret,
                        risk_free_rate=risk_free_rate
                    )
                    fund_metrics[str(code)] = {
                        "alpha": f_m["portfolio_alpha"],
                        "beta": f_m["portfolio_beta"],
                        "r2": f_m["portfolio_r2"],
                        "sharpe_ratio": f_m["sharpe_ratio"],
                        "treynor_ratio": f_m["treynor_ratio"],
                        "information_ratio": f_m["information_ratio"],
                        "tracking_error": f_m["tracking_error"]
                    }

        return {
            "portfolio_alpha": p_metrics["portfolio_alpha"],
            "portfolio_beta": p_metrics["portfolio_beta"],
            "portfolio_r2": p_metrics["portfolio_r2"],
            "sharpe_ratio": p_metrics["sharpe_ratio"],
            "treynor_ratio": p_metrics["treynor_ratio"],
            "information_ratio": p_metrics["information_ratio"],
            "tracking_error": p_metrics["tracking_error"],
            "fund_metrics": fund_metrics,
            "scatter_data": scatter_data,
            "is_synthetic_benchmark": is_synthetic
        }

    @staticmethod
    def calculate(
        nav_df_dict: Union[Dict[str, pd.DataFrame], pd.DataFrame, pd.Series],
        market_benchmark_df: Optional[pd.DataFrame] = None,
        fund_market_values: Optional[Dict[str, float]] = None,
        risk_free_rate: float = 0.02,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Alias for calculate_metrics to ensure API interface compatibility."""
        return AlphaBetaEngine.calculate_metrics(
            nav_df_dict=nav_df_dict,
            market_benchmark_df=market_benchmark_df,
            fund_market_values=fund_market_values,
            risk_free_rate=risk_free_rate,
            **kwargs
        )

    @staticmethod
    def _extract_benchmark_series(benchmark_df: Optional[pd.DataFrame]) -> Optional[pd.Series]:
        """Extract benchmark daily return series indexed by date string.

        Args:
            benchmark_df: Optional benchmark DataFrame.

        Returns:
            Optional[pd.Series] of daily returns indexed by YYYY-MM-DD.
        """
        if benchmark_df is None or not isinstance(benchmark_df, pd.DataFrame) or benchmark_df.empty:
            return None

        df = benchmark_df.copy()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            df = df.set_index("date")
        else:
            try:
                df.index = pd.to_datetime(df.index).strftime("%Y-%m-%d")
            except (ValueError, TypeError, AttributeError):
                return None

        for col in ["daily_return", "pct_change", "return", "change", "000300.SH", "000300"]:
            if col in df.columns:
                s = df[col].dropna().astype(float)
                s.name = "market_return"
                return s

        if "nav" in df.columns:
            s = df["nav"].astype(float).pct_change().dropna()
            s.name = "market_return"
            return s
        elif "close" in df.columns:
            s = df["close"].astype(float).pct_change().dropna()
            s.name = "market_return"
            return s

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            s = df[numeric_cols[0]].dropna().astype(float)
            s.name = "market_return"
            return s

        return None

    @staticmethod
    def _generate_synthetic_benchmark(y_portfolio: pd.Series) -> pd.Series:
        """Generate a synthetic market benchmark series when market benchmark is missing or invalid.

        Args:
            y_portfolio: Portfolio daily return series.

        Returns:
            pd.Series of synthetic market returns.
        """
        rng = np.random.RandomState(42)
        n = len(y_portfolio)
        noise = rng.normal(loc=0.0001, scale=0.005, size=n)
        synthetic_ret = 0.6 * y_portfolio.values + noise
        s = pd.Series(synthetic_ret, index=y_portfolio.index, name="market_return")
        return s

    @staticmethod
    def _compute_metrics_from_aligned_series(
        y_ret: np.ndarray,
        x_ret: np.ndarray,
        risk_free_rate: float
    ) -> Dict[str, float]:
        """Compute CAPM and risk-adjusted attribution metrics from aligned daily return arrays.

        Args:
            y_ret: Array of portfolio/fund daily returns.
            x_ret: Array of market benchmark daily returns.
            risk_free_rate: Annualized risk-free rate.

        Returns:
            Dict containing computed metrics.
        """
        n = len(y_ret)
        if n < 3:
            return {
                "portfolio_alpha": 0.0,
                "portfolio_beta": 0.0,
                "portfolio_r2": 0.0,
                "sharpe_ratio": 0.0,
                "treynor_ratio": 0.0,
                "information_ratio": 0.0,
                "tracking_error": 0.0
            }

        rf_daily = risk_free_rate / 252.0
        y_ex = y_ret - rf_daily
        x_ex = x_ret - rf_daily

        mean_y_ex = float(np.mean(y_ex))
        mean_x_ex = float(np.mean(x_ex))

        var_x = float(np.var(x_ex, ddof=1))
        var_y = float(np.var(y_ex, ddof=1))
        cov_matrix = np.cov(x_ex, y_ex, ddof=1)
        cov_xy = float(cov_matrix[0, 1])

        # 1. Beta
        if var_x > 1e-12:
            beta = cov_xy / var_x
        else:
            beta = 0.0

        # 2. Annualized Alpha
        alpha_daily = mean_y_ex - beta * mean_x_ex
        alpha_annual = alpha_daily * 252.0

        # 3. R2 (Coefficient of determination)
        if var_x > 1e-12 and var_y > 1e-12:
            r2 = (cov_xy ** 2) / (var_x * var_y)
            r2 = float(np.clip(r2, 0.0, 1.0))
        else:
            r2 = 0.0

        # 4. Annualized Sharpe Ratio
        std_y = float(np.std(y_ret, ddof=1))
        if std_y > 1e-12:
            sharpe = (mean_y_ex / std_y) * np.sqrt(252.0)
        else:
            sharpe = 0.0

        # 5. Annualized Treynor Ratio
        if abs(beta) > 1e-8:
            treynor = (mean_y_ex * 252.0) / beta
        else:
            treynor = 0.0

        # 6. Annualized Tracking Error
        active_ret = y_ret - x_ret
        std_active = float(np.std(active_ret, ddof=1))
        tracking_error = std_active * np.sqrt(252.0)

        # 7. Annualized Information Ratio
        mean_active = float(np.mean(active_ret))
        if tracking_error > 1e-12:
            information_ratio = (mean_active * 252.0) / tracking_error
        else:
            information_ratio = 0.0

        return {
            "portfolio_alpha": float(alpha_annual),
            "portfolio_beta": float(beta),
            "portfolio_r2": float(r2),
            "sharpe_ratio": float(sharpe),
            "treynor_ratio": float(treynor),
            "information_ratio": float(information_ratio),
            "tracking_error": float(tracking_error)
        }

    @staticmethod
    def _default_result() -> Dict[str, Any]:
        """Return default zeroed dictionary structure for empty/invalid inputs."""
        return {
            "portfolio_alpha": 0.0,
            "portfolio_beta": 0.0,
            "portfolio_r2": 0.0,
            "sharpe_ratio": 0.0,
            "treynor_ratio": 0.0,
            "information_ratio": 0.0,
            "tracking_error": 0.0,
            "fund_metrics": {},
            "scatter_data": [],
            "is_synthetic_benchmark": False
        }
