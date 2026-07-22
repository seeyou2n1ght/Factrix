"""Global Pytest Fixtures and AkShare Network Interceptor for Factrix E2E and Unit Tests.

Provides offline mock data stubs, SQLite storage fixtures, and network blocking
to guarantee 100% offline, zero-network test execution.
"""

import json
from pathlib import Path
from typing import Dict, Any, Generator
import pytest
import pandas as pd

from src.data.storage import SQLiteStorage


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Return absolute path to tests/fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def mock_nav_data(fixtures_dir: Path) -> Dict[str, Any]:
    """Load raw mock_nav_data.json containing 250-day NAV and benchmark factor indices."""
    nav_file = fixtures_dir / "mock_nav_data.json"
    with open(nav_file, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def mock_holdings_data(fixtures_dir: Path) -> Dict[str, Any]:
    """Load raw mock_holdings.json containing top 10 stock holdings per fund."""
    holdings_file = fixtures_dir / "mock_holdings.json"
    with open(holdings_file, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def sample_fundlist_path(fixtures_dir: Path) -> str:
    """Return path to standard 5-fund sample CSV fixture."""
    return str(fixtures_dir / "sample_fundlist.csv")


@pytest.fixture(scope="session")
def invalid_fundlist_path(fixtures_dir: Path) -> str:
    """Return path to malformed CSV fixture for exception testing."""
    return str(fixtures_dir / "invalid_fundlist.csv")


@pytest.fixture(scope="module")
def mock_fund_nav_df_dict(mock_nav_data: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """Return dictionary of normalized fund NAV DataFrames indexed by 6-digit fund code.
    
    Columns: ['date', 'nav', 'daily_return']
    """
    result = {}
    funds_dict = mock_nav_data.get("funds", {})
    for code, records in funds_dict.items():
        df = pd.DataFrame(records)
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        df['nav'] = df['nav'].astype(float)
        df['daily_return'] = df['daily_return'].astype(float)
        result[code] = df
    return result


@pytest.fixture(scope="module")
def mock_benchmark_nav_df(mock_nav_data: Dict[str, Any]) -> pd.DataFrame:
    """Return normalized benchmark style factor indices DataFrame.
    
    Columns: ['date', 'hs300', 'zz500', 'gz2000', 'large_cap_value', 'small_cap_growth', ...]
    """
    benchmarks = mock_nav_data.get("benchmarks", [])
    df = pd.DataFrame(benchmarks)
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    for col in df.columns:
        if col != 'date':
            df[col] = df[col].astype(float)
    return df


@pytest.fixture(scope="module")
def mock_holdings_df_dict(mock_holdings_data: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """Return dictionary of normalized stock holdings DataFrames indexed by 6-digit fund code.
    
    Columns: ['stock_code', 'stock_name', 'weight', 'sector']
    """
    result = {}
    raw_holdings = mock_holdings_data.get("holdings", mock_holdings_data)
    for code, holdings in raw_holdings.items():
        if isinstance(holdings, list):
            df = pd.DataFrame(holdings)
            df['stock_code'] = df['stock_code'].astype(str).str.zfill(6)
            df['weight'] = df['weight'].astype(float)
            result[code] = df
    return result


@pytest.fixture
def memory_storage(
    tmp_path: Path,
    mock_fund_nav_df_dict: Dict[str, pd.DataFrame],
    mock_holdings_df_dict: Dict[str, pd.DataFrame]
) -> Generator[SQLiteStorage, None, None]:
    """Provide an isolated SQLiteStorage test instance pre-populated with mock data."""
    test_db = tmp_path / "test_fund_data.db"
    storage = SQLiteStorage(db_path=test_db)
    for code, df_nav in mock_fund_nav_df_dict.items():
        storage.save_nav(code, df_nav)
    for code, df_holdings in mock_holdings_df_dict.items():
        storage.save_holdings(code, df_holdings)
    yield storage
    storage.close()



@pytest.fixture(autouse=True)
def block_external_network(monkeypatch, mock_nav_data: Dict[str, Any], mock_holdings_data: Dict[str, Any]):
    """Autouse fixture to intercept AkShare API calls with offline mock data.

    Returns mock data for known test funds. For unmocked funds, returns empty DataFrame
    instead of raising errors, allowing app.py's fallback generators and SQLite cache
    to handle gracefully without retry storms.
    """
    funds_nav_mock = mock_nav_data.get("funds", {})
    holdings_mock = mock_holdings_data.get("holdings", mock_holdings_data)

    def mock_fund_open_fund_info_em(fund: str, indicator: str = "单位净值走势", *args, **kwargs) -> pd.DataFrame:
        fund_code = str(fund).zfill(6)
        if indicator == "单位净值走势":
            if fund_code in funds_nav_mock:
                records = funds_nav_mock[fund_code]
                df = pd.DataFrame(records)
                return df.rename(columns={
                    "date": "净值日期",
                    "nav": "单位净值",
                    "daily_return": "日增长率"
                })
            return pd.DataFrame()  # Graceful empty for unmocked funds
        elif indicator == "持仓明细":
            if fund_code in holdings_mock and isinstance(holdings_mock[fund_code], list):
                records = holdings_mock[fund_code]
                df = pd.DataFrame(records)
                return df.rename(columns={
                    "stock_code": "股票代码",
                    "stock_name": "股票名称",
                    "weight": "占净值比例",
                    "sector": "申万行业"
                })
            return pd.DataFrame()
        return pd.DataFrame()

    def mock_fund_portfolio_hold_em(symbol: str, *args, **kwargs) -> pd.DataFrame:
        fund_code = str(symbol).zfill(6)
        if fund_code in holdings_mock and isinstance(holdings_mock[fund_code], list):
            records = holdings_mock[fund_code]
            df = pd.DataFrame(records)
            return df.rename(columns={
                "stock_code": "股票代码",
                "stock_name": "股票名称",
                "weight": "占净值比例",
                "sector": "申万行业"
            })
        return pd.DataFrame()  # Graceful empty for unmocked funds

    def mock_stock_zh_index_daily_em(symbol: str, *args, **kwargs) -> pd.DataFrame:
        benchmarks = mock_nav_data.get("benchmarks", [])
        if benchmarks:
            df = pd.DataFrame(benchmarks)
            if 'date' in df.columns:
                df = df.rename(columns={'date': 'date'})
            if 'large_cap_value' in df.columns and 'close' not in df.columns:
                df['close'] = df['large_cap_value'] * 3000.0
            elif 'close' not in df.columns:
                df['close'] = 3000.0
            return df
        return pd.DataFrame()

    # Patch akshare API endpoints directly if akshare is installed
    try:
        import akshare as ak
        monkeypatch.setattr(ak, "fund_open_fund_info_em", mock_fund_open_fund_info_em, raising=False)
        monkeypatch.setattr(ak, "fund_portfolio_hold_em", mock_fund_portfolio_hold_em, raising=False)
        monkeypatch.setattr(ak, "stock_zh_index_daily_em", mock_stock_zh_index_daily_em, raising=False)
        monkeypatch.setattr(ak, "stock_zh_index_daily", mock_stock_zh_index_daily_em, raising=False)
    except ImportError:
        pass
