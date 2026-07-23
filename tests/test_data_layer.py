"""Unit tests for data layer and configuration module.

Tests parse_fundlist_csv, validate_parsed_data, config helpers,
SQLiteStorage local cache, and FundFetcher with exponential backoff retries.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock
import pytest
import pandas as pd
import numpy as np

from src.config import (
    DEFAULT_CSV_PATH,
    PROSPECT_LAMBDA,
    get_sector_category,
    get_redemption_fee_rate,
)
from src.data.csv_parser import parse_fundlist_csv, validate_parsed_data
from src.data.storage import SQLiteStorage
from src.data.fetcher import FundFetcher


def test_config_defaults_and_helpers():
    """Test config default constants and helper functions."""
    assert PROSPECT_LAMBDA == 2.25
    assert get_sector_category("电子") == "科技制造"
    assert get_sector_category("食品饮料") == "大消费"
    assert get_sector_category("医药生物") == "医药健康"
    assert get_sector_category("未知行业") == "其他"

    # Test fee rate tiers
    assert get_redemption_fee_rate(0) == 0.015
    assert get_redemption_fee_rate(6) == 0.015
    assert get_redemption_fee_rate(7) == 0.0075
    assert get_redemption_fee_rate(29) == 0.0075
    assert get_redemption_fee_rate(30) == 0.0050
    assert get_redemption_fee_rate(364) == 0.0050
    assert get_redemption_fee_rate(365) == 0.0

    with pytest.raises(ValueError):
        get_redemption_fee_rate(-1)


def test_parse_real_fundlist_csv():
    """Test parsing the actual fundlist.csv file in project root."""
    assert DEFAULT_CSV_PATH.exists(), f"fundlist.csv not found at {DEFAULT_CSV_PATH}"

    # Test aggregated mode (default)
    df_agg = parse_fundlist_csv(str(DEFAULT_CSV_PATH), aggregate=True)

    is_valid, msg = validate_parsed_data(df_agg)
    assert is_valid, f"Validation failed: {msg}"

    # Check 6-digit zero padding
    for code in df_agg['fund_code']:
        assert len(code) == 6, f"Fund code {code} is not 6 digits"
        assert code.isdigit(), f"Fund code {code} is not purely numeric"

    # Verify specific zero-padded funds exist
    codes = set(df_agg['fund_code'])
    assert '000198' in codes
    assert '000940' in codes

    # Check aggregated unique constraint
    assert df_agg['fund_code'].is_unique, "Aggregated fund_code column contains duplicates"

    # Test unaggregated mode
    df_raw = parse_fundlist_csv(str(DEFAULT_CSV_PATH), aggregate=False)
    assert len(df_raw) > len(df_agg), "Unaggregated row count should be greater than aggregated count"
    assert len(df_raw) == 122, f"Expected 122 valid data rows, got {len(df_raw)}"

    # Check duplicate fund code 014114 aggregation behavior
    raw_014114 = df_raw[df_raw['fund_code'] == '014114']
    agg_014114 = df_agg[df_agg['fund_code'] == '014114']

    assert len(raw_014114) > 1, "Fund 014114 should have multiple raw position entries"
    assert len(agg_014114) == 1, "Fund 014114 should be aggregated to 1 row"
    assert pytest.approx(agg_014114['share'].iloc[0], 0.01) == raw_014114['share'].sum()
    assert pytest.approx(agg_014114['market_value'].iloc[0], 0.01) == raw_014114['market_value'].sum()


def test_parse_csv_file_not_found():
    """Test exception raised when CSV file path does not exist."""
    with pytest.raises(FileNotFoundError):
        parse_fundlist_csv("non_existent_file_path_12345.csv")


def test_parse_csv_custom_synthetic(tmp_path: Path):
    """Test CSV parser with synthetic CSV containing edge cases (newlines in header, trailing empty lines)."""
    csv_file = tmp_path / "test_funds.csv"
    csv_content = (
        '序号,基金代码,基金名称,持有份额,基金净值,净值日期,"资产情况\n（结算币种）",销售机构\n'
        '1,198,测试基金A,100.0,1.5,2026-07-17,150.0,雪球\n'
        '2,014114,测试基金B,200.0,2.0,2026-07-17,400.0,雪球\n'
        '3,014114,测试基金B,300.0,2.0,2026-07-17,600.0,雪球\n'
        ',,,,,,\n'
        '免责声明：本数据仅供参考,,,,,,,\n'
    )
    csv_file.write_text(csv_content, encoding='utf-8')

    # Test aggregate parsing
    df = parse_fundlist_csv(str(csv_file), aggregate=True)
    assert len(df) == 2

    row_198 = df[df['fund_code'] == '000198'].iloc[0]
    assert row_198['fund_name'] == '测试基金A'
    assert pytest.approx(row_198['share']) == 100.0
    assert pytest.approx(row_198['market_value']) == 150.0

    row_014114 = df[df['fund_code'] == '014114'].iloc[0]
    assert pytest.approx(row_014114['share']) == 500.0
    assert pytest.approx(row_014114['market_value']) == 1000.0


def test_validate_parsed_data_edge_cases():
    """Test validate_parsed_data with invalid input dataframes."""
    is_valid, msg = validate_parsed_data(None)
    assert not is_valid
    assert "not a pandas DataFrame" in msg

    df_missing = pd.DataFrame({'fund_code': ['000001']})
    is_valid, msg = validate_parsed_data(df_missing)
    assert not is_valid
    assert "Missing required column" in msg

    df_bad_code = pd.DataFrame({
        'fund_code': ['198'],
        'fund_name': ['A'],
        'share': [10.0],
        'nav': [1.0],
        'market_value': [10.0]
    })
    is_valid, msg = validate_parsed_data(df_bad_code)
    assert not is_valid
    assert "not 6 digits" in msg


# --- SQLiteStorage Tests ---

def test_sqlite_storage_crud_and_cache(tmp_path: Path):
    """Test SQLiteStorage table initialization, CRUD operations, and cache hitting."""
    db_file = tmp_path / "test_fund_data.db"
    
    with SQLiteStorage(db_path=db_file) as storage:
        # 1. Test NAV Save and Get
        sample_nav = pd.DataFrame({
            'date': ['2026-07-01', '2026-07-02', '2026-07-03'],
            'nav': [1.0, 1.05, 1.02],
        })
        storage.save_nav('000198', sample_nav)

        cached_nav = storage.get_nav('000198')
        assert len(cached_nav) == 3
        assert list(cached_nav.columns) == ['date', 'nav', 'daily_return']
        assert pytest.approx(cached_nav['daily_return'].iloc[1]) == 0.05

        # Test date filtering
        filtered_nav = storage.get_nav('000198', start_date='2026-07-02', end_date='2026-07-02')
        assert len(filtered_nav) == 1
        assert filtered_nav['date'].iloc[0] == '2026-07-02'

        # Test Primary Key overwrite
        overwrite_nav = pd.DataFrame({
            'date': ['2026-07-02'],
            'nav': [1.10],
            'daily_return': [0.10],
        })
        storage.save_nav('000198', overwrite_nav)
        updated_nav = storage.get_nav('000198')
        assert len(updated_nav) == 3
        assert updated_nav[updated_nav['date'] == '2026-07-02']['nav'].iloc[0] == 1.10

        # 2. Test Holdings Save and Get
        sample_holdings = pd.DataFrame({
            'stock_code': ['600519', '000858'],
            'stock_name': ['贵州茅台', '五粮液'],
            'weight': [8.5, 6.2],
            'sector': ['大消费', '大消费'],
        })
        storage.save_holdings('000198', sample_holdings, report_date='2026-06-30')

        cached_holdings = storage.get_holdings('000198')
        assert len(cached_holdings) == 2
        assert cached_holdings['stock_code'].iloc[0] == '600519'
        assert cached_holdings['weight'].iloc[0] == 8.5

        # 3. Test Benchmark Save and Get
        sample_benchmark = pd.DataFrame({
            'date': ['2026-07-01', '2026-07-02'],
            'close': [3000.0, 3030.0],
        })
        storage.save_benchmark('000029.SH', sample_benchmark)

        cached_benchmark = storage.get_benchmark('000029.SH')
        assert len(cached_benchmark) == 2
        assert pytest.approx(cached_benchmark['daily_return'].iloc[1]) == 0.01

        # 4. Test clear_cache
        storage.clear_cache('fund_nav')
        assert storage.get_nav('000198').empty
        assert not storage.get_holdings('000198').empty

        storage.clear_cache()
        assert storage.get_holdings('000198').empty
        assert storage.get_benchmark('000029.SH').empty


# --- FundFetcher Tests ---

def test_fund_fetcher_cache_hit_and_miss(tmp_path: Path, monkeypatch):
    """Test FundFetcher cache priority (hit vs miss behavior)."""
    db_file = tmp_path / "test_fetcher.db"
    fetcher = FundFetcher(db_path=db_file, max_retries=2, backoff_factor=0.001)

    api_call_count = {'nav': 0, 'holdings': 0, 'benchmark': 0}

    def mock_fetch_nav(fund_code):
        api_call_count['nav'] += 1
        return pd.DataFrame({
            '净值日期': ['2026-07-10', '2026-07-11'],
            '单位净值': [1.20, 1.25],
        })

    def mock_fetch_holdings(fund_code):
        api_call_count['holdings'] += 1
        return pd.DataFrame({
            '股票代码': ['600519'],
            '股票名称': ['贵州茅台'],
            '占净值比例': ['9.8%'],
            '行业': ['食品饮料'],
        })

    def mock_fetch_benchmark(code):
        api_call_count['benchmark'] += 1
        return pd.DataFrame({
            '日期': ['2026-07-10', '2026-07-11'],
            '收盘': [4000.0, 4040.0],
        })

    monkeypatch.setattr(fetcher, '_fetch_akshare_fund_nav', mock_fetch_nav)
    monkeypatch.setattr(fetcher, '_fetch_akshare_fund_holdings', mock_fetch_holdings)
    monkeypatch.setattr(fetcher, '_fetch_akshare_benchmark', mock_fetch_benchmark)

    # 1. First call: Cache miss -> triggers API call
    df_nav_1 = fetcher.get_fund_nav('000198')
    assert len(df_nav_1) == 2
    assert api_call_count['nav'] == 1

    # 2. Second call: Cache hit -> does NOT trigger API call
    df_nav_2 = fetcher.get_fund_nav('000198')
    assert len(df_nav_2) == 2
    assert api_call_count['nav'] == 1  # Unchanged

    # Holdings cache hit/miss
    df_h1 = fetcher.get_fund_holdings('000198')
    assert len(df_h1) == 1
    assert api_call_count['holdings'] == 1
    assert df_h1['sector'].iloc[0] == '大消费'  # Verified sector mapping

    df_h2 = fetcher.get_fund_holdings('000198')
    assert len(df_h2) == 1
    assert api_call_count['holdings'] == 1  # Unchanged

    # Benchmark cache hit/miss
    df_b1 = fetcher.get_benchmark_nav('000029.SH')
    assert len(df_b1) == 2
    assert api_call_count['benchmark'] == 1

    df_b2 = fetcher.get_benchmark_nav('000029.SH')
    assert len(df_b2) == 2
    assert api_call_count['benchmark'] == 1  # Unchanged


def test_fund_fetcher_exponential_backoff_retry_and_fallback(tmp_path: Path, monkeypatch):
    """Test FundFetcher retry logic on transient errors and graceful fallback on total failure."""
    db_file = tmp_path / "test_retry.db"
    fetcher = FundFetcher(db_path=db_file, max_retries=3, backoff_factor=0.001)

    attempts = {'count': 0}

    # Scenario A: Fail 2 times with Exception/Timeout, succeed on 3rd attempt
    def mock_flaky_nav(fund_code):
        attempts['count'] += 1
        if attempts['count'] < 3:
            raise TimeoutError("Connection timed out (mock HTTP 429/Timeout)")
        return pd.DataFrame({
            '净值日期': ['2026-07-15'],
            '单位净值': [2.00],
        })

    monkeypatch.setattr(fetcher, '_fetch_akshare_fund_nav', mock_flaky_nav)
    df_res = fetcher.get_fund_nav('000940')
    assert len(df_res) == 1
    assert attempts['count'] == 3

    # Scenario B: Always fail on all retries -> Graceful fallback without crashing
    def mock_always_fail_holdings(fund_code):
        raise RuntimeError("AkShare API rate limit exceeded 429")

    monkeypatch.setattr(fetcher, '_fetch_akshare_fund_holdings', mock_always_fail_holdings)
    df_fallback = fetcher.get_fund_holdings('000940')
    assert isinstance(df_fallback, pd.DataFrame)
    assert df_fallback.empty
    assert list(df_fallback.columns) == ['stock_code', 'stock_name', 'weight', 'sector', 'report_date']


def test_fund_fetcher_imputation_and_missing_data(tmp_path: Path):
    """Test NAV imputation smoothing logic for missing/NaN values in NAV series."""
    fetcher = FundFetcher(db_path=tmp_path / "test_impute.db")

    raw_df = pd.DataFrame({
        '净值日期': ['2026-07-01', '2026-07-02', '2026-07-03', '2026-07-04'],
        '单位净值': [1.0, np.nan, 1.1, np.nan],
    })

    cleaned = fetcher._clean_and_impute_nav(raw_df)
    assert len(cleaned) == 4
    # Check forward fill / backward fill
    assert cleaned['nav'].tolist() == [1.0, 1.0, 1.1, 1.1]
    assert not cleaned['daily_return'].isna().any()
    assert pytest.approx(cleaned['daily_return'].iloc[2]) == (1.1 - 1.0) / 1.0


def test_csrc_sector_category_mapping():
    """Test CSRC 19 industry category mapping in config."""
    assert get_sector_category("制造业") == "科技制造"
    assert get_sector_category("金融业") == "大金融"
    assert get_sector_category("卫生和社会工作") == "医药健康"
    assert get_sector_category("农林牧渔业") == "大消费"
    assert get_sector_category("采矿业") == "周期资源"
    assert get_sector_category("信息传输、软件和信息技术服务业") == "科技制造"


def test_sqlite_storage_industry_allocation(tmp_path: Path):
    """Test SQLiteStorage industry allocation table saving, getting, and clearing."""
    db_file = tmp_path / "test_ind_storage.db"
    with SQLiteStorage(db_path=db_file) as storage:
        df_ind = pd.DataFrame({
            'industry_name': ['制造业', '金融业'],
            'weight': [0.60, 0.20],
            'market_value': [6000.0, 2000.0],
            'broad_sector': ['科技制造', '大金融']
        })
        storage.save_industry_allocation('000198', df_ind, report_date='2026-06-30')

        cached = storage.get_industry_allocation('000198')
        assert len(cached) == 2
        assert cached['industry_name'].iloc[0] == '制造业'
        assert cached['broad_sector'].iloc[0] == '科技制造'

        storage.clear_cache('fund_industry_allocation')
        assert storage.get_industry_allocation('000198').empty


def test_fund_fetcher_industry_allocation(tmp_path: Path, monkeypatch):
    """Test FundFetcher industry allocation fetching with cache hit and miss."""
    db_file = tmp_path / "test_ind_fetcher.db"
    fetcher = FundFetcher(db_path=db_file)

    calls = {'count': 0}

    def mock_fetch_ind(fund_code):
        calls['count'] += 1
        return pd.DataFrame({
            '行业类别': ['制造业', '金融业'],
            '占净值比例': ['55.0%', '15.0%'],
            '市值': [5500.0, 1500.0]
        })

    monkeypatch.setattr(fetcher, '_fetch_akshare_industry_allocation', mock_fetch_ind)

    # First call: Cache miss
    df1 = fetcher.get_fund_industry_allocation('000198')
    assert len(df1) == 2
    assert calls['count'] == 1
    assert df1['broad_sector'].iloc[0] == '科技制造'

    # Second call: Cache hit
    df2 = fetcher.get_fund_industry_allocation('000198')
    assert len(df2) == 2
    assert calls['count'] == 1

