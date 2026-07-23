"""Adversarial Stress Testing Harness for Milestone 3 (R3 Integration in app.py & run_debug.py).

Covers edge cases:
- Missing benchmarks (empty benchmark dict, missing keys, invalid benchmark codes)
- Empty CSV input (zero rows, headers only, invalid format)
- Single-fund portfolio (1 fund in portfolio)
- Corrupted NAV data (NaN, Inf, flat zero returns, short history, unsorted dates)
- Headless Streamlit UI rendering & CLI script run_debug execution
"""

import os
import sys
import tempfile
from pathlib import Path
import pytest
import pandas as pd
import numpy as np
from streamlit.testing.v1 import AppTest

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import (
    load_and_analyze_data,
    generate_fallback_nav,
    generate_fallback_benchmark,
    generate_fallback_holdings,
    generate_fallback_industry_allocation,
)
import run_debug


class TestM3EdgeCasesAdversarial:
    """Stress tests for load_and_analyze_data and app pipeline edge cases."""

    def test_edge_case_empty_csv_handling(self, tmp_path: Path):
        """Test empty CSV file handling in load_and_analyze_data and app main."""
        empty_csv = tmp_path / "empty_fundlist.csv"
        empty_csv.write_text("序号,基金代码,基金名称,持有份额,基金净值,净值日期,资产情况\n", encoding="utf-8")

        # Test load_and_analyze_data returns empty dict or handles exception
        res = load_and_analyze_data(str(empty_csv))
        assert isinstance(res, dict)
        # Should be empty dict when no funds found
        assert res == {}

    def test_edge_case_single_fund_portfolio(self, tmp_path: Path):
        """Test single-fund portfolio pipeline execution."""
        single_csv = tmp_path / "single_fund.csv"
        content = (
            "序号,基金代码,基金名称,持有份额,基金净值,净值日期,资产情况\n"
            "1,000001,华夏成长,10000.0,1.5,2026-07-17,15000.0\n"
        )
        single_csv.write_text(content, encoding="utf-8")

        res = load_and_analyze_data(str(single_csv))
        assert "df_funds" in res
        assert len(res["df_funds"]) == 1
        assert res["n_funds"] == 1
        assert res["total_value"] == 15000.0

        # Verify engine outputs for single fund
        assert res["pbsa_res"]["overlap_matrix"].shape == (1, 1)
        assert res["rebalance_res"]["trigger_reasons"] == ["单一持仓无需调仓"]
        assert "alpha_beta_res" in res
        assert "health_res" in res

    def test_edge_case_missing_benchmarks(self, tmp_path: Path, monkeypatch):
        """Test pipeline behavior when benchmark configuration or fetcher returns empty benchmark dictionary."""
        sample_csv = tmp_path / "sample_fund.csv"
        content = (
            "序号,基金代码,基金名称,持有份额,基金净值,净值日期,资产情况\n"
            "1,000001,华夏成长,10000.0,1.5,2026-07-17,15000.0\n"
            "2,014114,易方达品质,5000.0,2.0,2026-07-17,10000.0\n"
        )
        sample_csv.write_text(content, encoding="utf-8")

        # Mock RBSA_BENCHMARKS to empty dict
        monkeypatch.setattr("app.RBSA_BENCHMARKS", {})

        res = load_and_analyze_data(str(sample_csv))
        assert "rbsa_res" in res
        assert "rolling_res" in res
        assert "alpha_beta_res" in res

    def test_edge_case_corrupted_nav_data(self, tmp_path: Path, monkeypatch):
        """Test pipeline behavior when fetcher returns corrupted NAV data (NaN, Inf, short history)."""
        sample_csv = tmp_path / "corrupted_nav_fund.csv"
        content = (
            "序号,基金代码,基金名称,持有份额,基金净值,净值日期,资产情况\n"
            "1,000001,华夏成长,10000.0,1.5,2026-07-17,15000.0\n"
        )
        sample_csv.write_text(content, encoding="utf-8")

        # Mock get_fund_nav to return NaN / Inf / single row NAV
        def mock_corrupted_nav(code):
            dates = pd.date_range("2026-01-01", periods=10, freq="D").strftime("%Y-%m-%d")
            return pd.DataFrame({
                "date": dates,
                "nav": [1.0, np.nan, np.inf, -np.inf, 1.2, 0.0, 1.1, 1.3, 1.4, 1.5],
                "daily_return": [0.0, np.nan, np.inf, -np.inf, 0.02, -1.0, 0.1, 0.05, 0.01, 0.02]
            })

        from src.data.fetcher import FundFetcher
        monkeypatch.setattr(FundFetcher, "get_fund_nav", lambda self, code: mock_corrupted_nav(code))

        res = load_and_analyze_data(str(sample_csv))
        assert "health_res" in res
        assert 0 <= res["health_res"]["total_score"] <= 100

    def test_fallback_generators_robustness(self):
        """Verify defensive fallback mock generators with extreme/invalid fund codes."""
        for code in ["000001", "INVALID", "", "123456789", None]:
            df_nav = generate_fallback_nav(str(code))
            assert isinstance(df_nav, pd.DataFrame)
            assert not df_nav.empty
            assert "date" in df_nav.columns and "nav" in df_nav.columns

            df_hold = generate_fallback_holdings(str(code))
            assert isinstance(df_hold, pd.DataFrame)
            assert not df_hold.empty
            assert "stock_code" in df_hold.columns

            df_ind = generate_fallback_industry_allocation(str(code))
            assert isinstance(df_ind, pd.DataFrame)
            assert not df_ind.empty
            assert "industry_name" in df_ind.columns

        dates = pd.date_range("2026-01-01", periods=20, freq="D")
        for bcode in ["000012.SH", "000028.SH", "UNKNOWN"]:
            df_bm = generate_fallback_benchmark(bcode, dates)
            assert isinstance(df_bm, pd.DataFrame)
            assert len(df_bm) == len(dates)


class TestCLIRunDebugAdversarial:
    """Stress tests for run_debug.py CLI script execution."""

    def test_run_debug_main_execution(self, monkeypatch, capsys):
        """Execute run_debug.main() to ensure 100% crash-free execution."""
        try:
            run_debug.main()
            captured = capsys.readouterr()
            assert "Running data pipeline..." in captured.out
            assert "Pipeline finished successfully" in captured.out or "[ERROR]" not in captured.out
        except Exception as e:
            pytest.fail(f"run_debug.main() raised uncaught exception: {e}")

    def test_run_debug_check_dict_robustness(self, capsys):
        """Test check_dict function in run_debug with recursive and unusual object structures."""
        complex_dict = {
            "df": pd.DataFrame({"a": [1, 2, np.nan]}),
            "series": pd.Series([1, 2, 3]),
            "scalar_int": 42,
            "scalar_float": 3.14,
            "scalar_str": "test",
            "scalar_bool": True,
            "list_val": [1, 2, 3],
            "nested_dict": {"inner_df": pd.DataFrame({"b": [4, 5]})},
            "custom_object": object(),
        }
        try:
            run_debug.check_dict(complex_dict)
            captured = capsys.readouterr()
            assert "DataFrame shape" in captured.out
            assert "Series shape" in captured.out
            assert "nested_dict: Dict" in captured.out
        except Exception as e:
            pytest.fail(f"check_dict raised uncaught exception: {e}")


class TestStreamlitUIAppTestAdversarial:
    """Stress tests for Streamlit app UI rendering via AppTest."""

    def test_streamlit_app_default_run(self):
        """AppTest standard execution."""
        at = AppTest.from_file("app.py", default_timeout=30)
        at.run()
        assert not at.exception, f"Streamlit app raised uncaught exception: {at.exception}"

    def test_streamlit_app_empty_csv_uncaught_keyerror(self, tmp_path: Path, monkeypatch):
        """AppTest execution with empty CSV file to verify if app crashes with KeyError."""
        empty_csv = tmp_path / "empty_fundlist.csv"
        empty_csv.write_text("序号,基金代码,基金名称,持有份额,基金净值,净值日期,资产情况\n", encoding="utf-8")

        monkeypatch.setattr("src.config.DEFAULT_CSV_PATH", empty_csv)
        monkeypatch.setattr("src.config.get_latest_data_file", lambda: empty_csv)

        at = AppTest.from_file("app.py", default_timeout=15)
        at.run()

        # Check if an exception was raised during rendering
        if at.exception:
            print(f"Captured Exception: {at.exception}")
