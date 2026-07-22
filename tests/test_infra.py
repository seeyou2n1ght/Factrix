"""Test Infrastructure Verification Suite for Factrix.

Verifies that offline Mock Fixtures, SQLite memory storage, data schemas,
and AkShare zero-network interceptors are working as expected.
"""

from pathlib import Path
from typing import Dict, Any
import pytest
import pandas as pd

from src.data.storage import SQLiteStorage
from src.data.fetcher import FundFetcher


def test_fixtures_dir_exists(fixtures_dir: Path) -> None:
    """Verify fixture directory and required offline files exist."""
    assert fixtures_dir.exists()
    assert fixtures_dir.is_dir()
    required_files = [
        "sample_fundlist.csv",
        "invalid_fundlist.csv",
        "mock_holdings.json",
        "mock_nav_data.json",
    ]
    for fname in required_files:
        fpath = fixtures_dir / fname
        assert fpath.exists(), f"Missing required fixture file: {fname}"


def test_mock_nav_data_fixture(mock_nav_data: Dict[str, Any]) -> None:
    """Verify mock_nav_data structure and 250-day series length."""
    assert "funds" in mock_nav_data
    assert "benchmarks" in mock_nav_data

    funds = mock_nav_data["funds"]
    expected_codes = ["000001", "014114", "001900", "012094", "022502"]
    for code in expected_codes:
        assert code in funds, f"Fund code {code} missing in mock_nav_data"
        nav_records = funds[code]
        assert len(nav_records) >= 250, f"Fund {code} has less than 250 days of NAV data"
        assert "date" in nav_records[0]
        assert "nav" in nav_records[0]
        assert "daily_return" in nav_records[0]

    benchmarks = mock_nav_data["benchmarks"]
    assert len(benchmarks) >= 250
    assert "hs300" in benchmarks[0]
    assert "zz500" in benchmarks[0]


def test_mock_holdings_data_fixture(mock_holdings_data: Dict[str, Any]) -> None:
    """Verify mock_holdings_data contains top 10 stocks per fund with valid weights."""
    expected_codes = ["000001", "014114", "001900", "012094", "022502"]
    for code in expected_codes:
        assert code in mock_holdings_data, f"Fund code {code} missing in mock_holdings_data"
        holdings = mock_holdings_data[code]
        assert len(holdings) == 10, f"Fund {code} should have 10 stock holdings"
        for item in holdings:
            assert "stock_code" in item
            assert "stock_name" in item
            assert "weight" in item
            assert "sector" in item
            assert 0.0 < item["weight"] < 1.0


def test_mock_fund_nav_df_dict_schema(mock_fund_nav_df_dict: Dict[str, pd.DataFrame]) -> None:
    """Verify DataFrame schema for mock_fund_nav_df_dict."""
    expected_cols = ["date", "nav", "daily_return"]
    for code, df in mock_fund_nav_df_dict.items():
        assert list(df.columns) == expected_cols
        assert not df.empty
        assert pd.api.types.is_numeric_dtype(df["nav"])
        assert pd.api.types.is_numeric_dtype(df["daily_return"])


def test_mock_benchmark_nav_df_schema(mock_benchmark_nav_df: pd.DataFrame) -> None:
    """Verify DataFrame schema and columns for mock_benchmark_nav_df."""
    assert "date" in mock_benchmark_nav_df.columns
    expected_factors = [
        "hs300",
        "zz500",
        "gz2000",
        "large_cap_value",
        "small_cap_growth",
        "large_cap_growth",
        "small_cap_value",
    ]
    for factor in expected_factors:
        assert factor in mock_benchmark_nav_df.columns
        assert pd.api.types.is_numeric_dtype(mock_benchmark_nav_df[factor])


def test_mock_holdings_df_dict_schema(mock_holdings_df_dict: Dict[str, pd.DataFrame]) -> None:
    """Verify DataFrame schema for mock_holdings_df_dict."""
    expected_cols = ["stock_code", "stock_name", "weight", "sector"]
    for code, df in mock_holdings_df_dict.items():
        assert list(df.columns) == expected_cols
        assert len(df) == 10


def test_memory_storage_fixture(memory_storage: SQLiteStorage) -> None:
    """Verify in-memory SQLite storage returns cached NAV and holdings."""
    df_nav = memory_storage.get_nav("000001")
    assert not df_nav.empty
    assert len(df_nav) >= 250

    df_holdings = memory_storage.get_holdings("000001")
    assert not df_holdings.empty
    assert len(df_holdings) == 10


def test_akshare_interceptor_offline(memory_storage: SQLiteStorage) -> None:
    """Verify fetcher reads from storage/mock without making network requests."""
    fetcher = FundFetcher(storage=memory_storage)
    df_nav = fetcher.get_fund_nav("000001")
    assert not df_nav.empty
    assert "nav" in df_nav.columns

    df_holdings = fetcher.get_fund_holdings("000001")
    assert not df_holdings.empty
    assert "stock_code" in df_holdings.columns
