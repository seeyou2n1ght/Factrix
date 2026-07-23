"""AkShare data fetcher with exponential backoff and SQLite caching.

Provides FundFetcher class to query fund NAV, portfolio holdings, and benchmark indices.
Implements cache priority, exponential backoff retries, and data imputation/smoothing fallback.
"""

import logging
import time
from typing import Optional, Union, Callable
import pandas as pd
import numpy as np

from src.config import (
    AKSHARE_MAX_RETRIES,
    AKSHARE_BACKOFF_FACTOR,
    AKSHARE_REQUEST_TIMEOUT,
    get_sector_category,
)
from src.data.storage import SQLiteStorage

logger = logging.getLogger(__name__)


class FundFetcher:
    """AkShare API data fetcher with local SQLite cache and exponential backoff retries."""

    def __init__(
        self,
        storage: Optional[SQLiteStorage] = None,
        db_path: Optional[Union[str, pd.Timestamp]] = None,
        max_retries: int = AKSHARE_MAX_RETRIES,
        backoff_factor: float = AKSHARE_BACKOFF_FACTOR,
        timeout: int = AKSHARE_REQUEST_TIMEOUT,
    ):
        """Initialize FundFetcher.

        Args:
            storage: Optional SQLiteStorage instance.
            db_path: Optional custom path to SQLite database file.
            max_retries: Maximum number of retry attempts for AkShare API calls.
            backoff_factor: Exponential backoff factor (in seconds).
            timeout: Request timeout limit (in seconds).
        """
        if storage is not None:
            self.storage = storage
        else:
            self.storage = SQLiteStorage(db_path=db_path)

        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout

    def _execute_with_retry(self, func: Callable, *args, **kwargs) -> pd.DataFrame:
        """Execute an API function with exponential backoff retries.

        Args:
            func: API callable to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            pd.DataFrame result from successful execution.

        Raises:
            Exception: Last caught exception if max_retries is reached.
        """
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                if isinstance(result, pd.DataFrame) and not result.empty:
                    return result
                elif isinstance(result, pd.DataFrame) and result.empty:
                    # Empty DataFrame returned (valid for non-equity funds or empty holdings)
                    logger.debug(f"Attempt {attempt + 1}/{self.max_retries}: Empty DataFrame returned")
                    return result
                return pd.DataFrame()
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Attempt {attempt + 1}/{self.max_retries} failed for {func.__name__}: {e}. Retrying..."
                )
                if attempt < self.max_retries - 1:
                    sleep_time = self.backoff_factor * (1.5 ** attempt)
                    time.sleep(sleep_time)

        if last_exception:
            raise last_exception
        return pd.DataFrame()

    # --- Fund NAV Fetching ---

    def get_fund_nav(
        self,
        fund_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch fund historical daily NAV data with cache priority and smoothing.

        Args:
            fund_code: 6-digit fund code string.
            start_date: Optional start date 'YYYY-MM-DD'.
            end_date: Optional end date 'YYYY-MM-DD'.

        Returns:
            DataFrame with normalized columns ['date', 'nav', 'daily_return'].
        """
        fund_code_clean = str(fund_code).zfill(6)

        # 1. Check SQLite Cache
        df_cached = self.storage.get_nav(fund_code_clean, start_date=start_date, end_date=end_date)
        if not df_cached.empty:
            logger.info(f"Cache hit for fund_nav {fund_code_clean} ({len(df_cached)} records)")
            return self._smooth_nav_dataframe(df_cached)

        # 2. Cache Miss - Fetch from AkShare API
        logger.info(f"Cache miss for fund_nav {fund_code_clean}, fetching from AkShare...")
        try:
            df_api = self._execute_with_retry(self._fetch_akshare_fund_nav, fund_code_clean)
            if not df_api.empty:
                df_clean = self._clean_and_impute_nav(df_api)
                if not df_clean.empty:
                    # Save full fetched history to SQLite cache
                    self.storage.save_nav(fund_code_clean, df_clean)
                    # Filter by requested date range
                    return self._filter_by_date(df_clean, start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to fetch NAV for fund {fund_code_clean} after {self.max_retries} retries: {e}")

        # 3. Fallback: Check if partial cache exists without date bounds
        df_all_cached = self.storage.get_nav(fund_code_clean)
        if not df_all_cached.empty:
            logger.warning(f"Using fallback partial cache for fund_nav {fund_code_clean}")
            return self._filter_by_date(self._smooth_nav_dataframe(df_all_cached), start_date, end_date)

        # 4. Ultimate Fallback: Return empty DataFrame with expected schema
        logger.error(f"Returning empty DataFrame fallback for fund_nav {fund_code_clean}")
        return pd.DataFrame(columns=['date', 'nav', 'daily_return'])

    def _fetch_akshare_fund_nav(self, fund_code: str) -> pd.DataFrame:
        """Raw AkShare API call for fund NAV."""
        import akshare as ak
        import warnings
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # Try primary fund info indicator
            try:
                df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
                if df is not None and df.empty:
                    # Might be a money market fund
                    try:
                        df_mm = ak.fund_money_fund_info_em(symbol=fund_code)
                        if df_mm is not None and not df_mm.empty:
                            return df_mm
                    except Exception:
                        pass
                    return ak.fund_etf_fund_info_em(fund=fund_code)
                return df
            except Exception:
                try:
                    df_mm = ak.fund_money_fund_info_em(symbol=fund_code)
                    if df_mm is not None and not df_mm.empty:
                        return df_mm
                except Exception:
                    pass
                return ak.fund_etf_fund_info_em(fund=fund_code)

    def _clean_and_impute_nav(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean raw AkShare NAV DataFrame and apply imputation smoothing."""
        df_clean = df.copy()

        # Find date column
        date_col = None
        for col in ['净值日期', '日期', 'date', 'NAV_date']:
            if col in df_clean.columns:
                date_col = col
                break

        # Handle Money Market Funds (货币基金)
        if '每万份收益' in df_clean.columns:
            if not date_col:
                logger.warning("Date column not found in Money Market Fund DataFrame")
                return pd.DataFrame(columns=['date', 'nav', 'daily_return'])
            
            df_clean['date'] = pd.to_datetime(df_clean[date_col], errors='coerce').dt.strftime('%Y-%m-%d')
            df_clean['daily_return'] = pd.to_numeric(df_clean['每万份收益'], errors='coerce').fillna(0.0) / 10000.0
            
            df_clean = df_clean.dropna(subset=['date']).sort_values('date').reset_index(drop=True)
            # Reconstruct synthetic NAV (starting at 1.0)
            df_clean['nav'] = (1.0 + df_clean['daily_return']).cumprod()
            return df_clean[['date', 'nav', 'daily_return']]

        # Find nav column
        nav_col = None
        for col in ['单位净值', 'nav', 'NAV', 'DWJZ', '收盘']:
            if col in df_clean.columns:
                nav_col = col
                break

        if not date_col or not nav_col:
            logger.warning("Required columns not found in raw NAV DataFrame")
            return pd.DataFrame(columns=['date', 'nav', 'daily_return'])

        df_clean['date'] = pd.to_datetime(df_clean[date_col], errors='coerce').dt.strftime('%Y-%m-%d')
        df_clean['nav'] = pd.to_numeric(df_clean[nav_col], errors='coerce')

        df_clean = df_clean.dropna(subset=['date']).sort_values('date').reset_index(drop=True)

        # Imputation logic: ffill().bfill().fillna(0.0)
        df_clean['nav'] = df_clean['nav'].ffill().bfill().fillna(0.0)

        # Compute daily_return
        df_clean['daily_return'] = df_clean['nav'].pct_change().fillna(0.0)

        return df_clean[['date', 'nav', 'daily_return']]

    def _smooth_nav_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure NAV DataFrame has no NaN values and valid daily_return."""
        if df.empty:
            return pd.DataFrame(columns=['date', 'nav', 'daily_return'])
        df_out = df.copy()
        df_out['nav'] = pd.to_numeric(df_out['nav'], errors='coerce').ffill().bfill().fillna(0.0)
        if 'daily_return' not in df_out.columns or df_out['daily_return'].isna().any():
            df_out['daily_return'] = df_out['nav'].pct_change().fillna(0.0)
        df_out['daily_return'] = df_out['daily_return'].fillna(0.0)
        return df_out[['date', 'nav', 'daily_return']]

    # --- Fund Holdings Fetching ---

    def get_fund_holdings(self, fund_code: str, report_date: Optional[str] = None) -> pd.DataFrame:
        """Fetch top holdings details for a fund with cache priority.

        Args:
            fund_code: 6-digit fund code string.
            report_date: Optional report date string.

        Returns:
            DataFrame with columns ['stock_code', 'stock_name', 'weight', 'sector', 'report_date'].
        """
        fund_code_clean = str(fund_code).zfill(6)

        # 1. Check SQLite Cache
        df_cached = self.storage.get_holdings(fund_code_clean, report_date=report_date)
        if not df_cached.empty:
            logger.info(f"Cache hit for fund_holdings {fund_code_clean} ({len(df_cached)} holdings)")
            return df_cached

        # 2. Cache Miss - Fetch from AkShare API
        logger.info(f"Cache miss for fund_holdings {fund_code_clean}, fetching from AkShare...")
        try:
            df_api = self._execute_with_retry(self._fetch_akshare_fund_holdings, fund_code_clean)
            if not df_api.empty:
                df_clean = self._clean_holdings_data(df_api, fund_code_clean)
                if not df_clean.empty:
                    # Determine report date from clean data if present
                    r_date = report_date or (df_clean['report_date'].iloc[0] if 'report_date' in df_clean.columns else '')
                    self.storage.save_holdings(fund_code_clean, df_clean, report_date=r_date)
                    return df_clean
        except Exception as e:
            logger.error(f"Failed to fetch holdings for fund {fund_code_clean} after {self.max_retries} retries: {e}")

        # 3. Fallback: Check for any cached holdings without report_date filter
        df_all_cached = self.storage.get_holdings(fund_code_clean)
        if not df_all_cached.empty:
            logger.warning(f"Using fallback partial cached holdings for fund {fund_code_clean}")
            return df_all_cached

        # 4. Ultimate Fallback: Empty DataFrame
        logger.error(f"Returning empty DataFrame fallback for fund_holdings {fund_code_clean}")
        return pd.DataFrame(columns=['stock_code', 'stock_name', 'weight', 'sector', 'report_date'])

    def _fetch_akshare_fund_holdings(self, fund_code: str) -> pd.DataFrame:
        """Raw AkShare API call for fund holdings."""
        import akshare as ak
        try:
            return ak.fund_portfolio_hold_em(symbol=fund_code)
        except Exception:
            return ak.fund_open_fund_info_em(symbol=fund_code, indicator="持仓明细")

    def _clean_holdings_data(self, df: pd.DataFrame, fund_code: str) -> pd.DataFrame:
        """Normalize raw AkShare holdings DataFrame and map sector categories."""
        df_clean = df.copy()

        # Find columns
        stock_code_col = next((c for c in ['股票代码', 'stock_code', 'code'] if c in df_clean.columns), None)
        stock_name_col = next((c for c in ['股票名称', 'stock_name', 'name'] if c in df_clean.columns), None)
        weight_col = next((c for c in ['占净值比例', '持仓比例', 'weight', '持股比例'] if c in df_clean.columns), None)
        sector_col = next((c for c in ['行业', '申万行业', 'sector', '所属行业'] if c in df_clean.columns), None)
        report_date_col = next((c for c in ['季度', '报告期', 'report_date', '截止时间'] if c in df_clean.columns), None)

        if not stock_code_col:
            logger.debug("Stock code column not found in holdings data")
            return pd.DataFrame(columns=['stock_code', 'stock_name', 'weight', 'sector', 'report_date'])

        # Stock code cleaning (6 digits zero padded)
        df_clean['stock_code'] = df_clean[stock_code_col].astype(str).str.strip().str.zfill(6)
        df_clean['stock_name'] = df_clean[stock_name_col].astype(str).str.strip() if stock_name_col else ''

        # Weight parsing (handle string percentages like "5.12%" or numeric 5.12)
        if weight_col:
            weight_series = df_clean[weight_col].astype(str).str.replace('%', '', regex=False)
            raw_weight = pd.to_numeric(weight_series, errors='coerce').fillna(0.0)
            # AkShare returns percentage values (e.g., 5.12 = 5.12%), convert to decimal fraction
            # Heuristic: if max weight > 1.5, assume percentage format and divide by 100
            if raw_weight.max() > 1.5:
                raw_weight = raw_weight / 100.0
            df_clean['weight'] = raw_weight
        else:
            df_clean['weight'] = 0.0

        # Sector categorization using config mapping
        if sector_col:
            df_clean['sector'] = df_clean[sector_col].astype(str).apply(get_sector_category)
        else:
            # No sector column available: default to '其他' rather than incorrectly using stock_name
            df_clean['sector'] = '其他'

        # Report date handling
        if report_date_col:
            df_clean['report_date'] = df_clean[report_date_col].astype(str).str.strip()
        else:
            df_clean['report_date'] = ''

        # Deduplicate and sort by weight descending
        output_cols = ['stock_code', 'stock_name', 'weight', 'sector', 'report_date']
        df_out = df_clean[output_cols].sort_values('weight', ascending=False).reset_index(drop=True)
        return df_out

    # --- Fund Industry Allocation Fetching ---

    def get_fund_industry_allocation(
        self,
        fund_code: str,
        report_date: Optional[str] = None
    ) -> pd.DataFrame:
        """Fetch fund full portfolio industry allocation data with cache priority.

        Args:
            fund_code: 6-digit fund code string.
            report_date: Optional report date string.

        Returns:
            DataFrame with columns ['industry_name', 'weight', 'market_value', 'broad_sector', 'report_date'].
        """
        fund_code_clean = str(fund_code).zfill(6)

        # 1. Check SQLite Cache
        df_cached = self.storage.get_industry_allocation(fund_code_clean, report_date=report_date)
        if not df_cached.empty:
            logger.info(f"Cache hit for fund_industry_allocation {fund_code_clean} ({len(df_cached)} records)")
            return df_cached

        # 2. Cache Miss - Fetch from AkShare API
        logger.info(f"Cache miss for fund_industry_allocation {fund_code_clean}, fetching from AkShare...")
        try:
            df_api = self._execute_with_retry(self._fetch_akshare_industry_allocation, fund_code_clean)
            if not df_api.empty:
                df_clean = self._clean_industry_allocation_data(df_api, fund_code_clean)
                if not df_clean.empty:
                    r_date = report_date or (df_clean['report_date'].iloc[0] if 'report_date' in df_clean.columns else '')
                    self.storage.save_industry_allocation(fund_code_clean, df_clean, report_date=r_date)
                    return df_clean
        except Exception as e:
            logger.info(f"Industry allocation unavailable for fund {fund_code_clean}: {e}")

        # 3. Fallback: Check for any cached industry allocation without report_date filter
        df_all_cached = self.storage.get_industry_allocation(fund_code_clean)
        if not df_all_cached.empty:
            logger.info(f"Using fallback cached industry allocation for fund {fund_code_clean}")
            return df_all_cached

        # 4. Ultimate Fallback: Empty DataFrame
        logger.info(f"Returning empty DataFrame fallback for fund_industry_allocation {fund_code_clean}")
        return pd.DataFrame(columns=['industry_name', 'weight', 'market_value', 'broad_sector', 'report_date'])

    def _fetch_akshare_industry_allocation(self, fund_code: str) -> pd.DataFrame:
        """Raw AkShare API call for fund industry allocation."""
        import akshare as ak
        try:
            return ak.fund_portfolio_industry_allocation_cninfo(symbol=fund_code)
        except Exception:
            try:
                return ak.fund_portfolio_industry_allocation_em(symbol=fund_code)
            except Exception:
                return ak.fund_open_fund_info_em(symbol=fund_code, indicator="行业配置")

    def _clean_industry_allocation_data(self, df: pd.DataFrame, fund_code: str) -> pd.DataFrame:
        """Normalize raw AkShare industry allocation DataFrame."""
        df_clean = df.copy()

        ind_col = next((c for c in ['行业类别', '行业名称', 'industry_name', '行业', 'CSRC行业', '申万行业'] if c in df_clean.columns), None)
        weight_col = next((c for c in ['占净值比例', '持仓比例', 'weight', '配置比例', '占净值比', '占净值比例(%)'] if c in df_clean.columns), None)
        val_col = next((c for c in ['市值', '持股市值', 'market_value', '市值(万元)'] if c in df_clean.columns), None)
        report_date_col = next((c for c in ['截止时间', '报告期', 'report_date', '季度'] if c in df_clean.columns), None)

        if not ind_col:
            logger.warning("Industry column not found in industry allocation data")
            return pd.DataFrame(columns=['industry_name', 'weight', 'market_value', 'broad_sector', 'report_date'])

        df_clean['industry_name'] = df_clean[ind_col].astype(str).str.strip()

        if weight_col:
            w_series = df_clean[weight_col].astype(str).str.replace('%', '', regex=False)
            raw_w = pd.to_numeric(w_series, errors='coerce').fillna(0.0)
            if raw_w.max() > 1.5:
                raw_w = raw_w / 100.0
            df_clean['weight'] = raw_w
        else:
            df_clean['weight'] = 0.0

        if val_col:
            df_clean['market_value'] = pd.to_numeric(df_clean[val_col], errors='coerce').fillna(0.0)
        else:
            df_clean['market_value'] = 0.0

        df_clean['broad_sector'] = df_clean['industry_name'].apply(get_sector_category)

        if report_date_col:
            df_clean['report_date'] = df_clean[report_date_col].astype(str).str.strip()
        else:
            df_clean['report_date'] = ''

        output_cols = ['industry_name', 'weight', 'market_value', 'broad_sector', 'report_date']
        return df_clean[output_cols].sort_values('weight', ascending=False).reset_index(drop=True)

    # --- Benchmark Fetching ---

    def get_benchmark_nav(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch benchmark index daily price and return series.

        Args:
            code: Benchmark index code (e.g., '000029.SH').
            start_date: Optional start date 'YYYY-MM-DD'.
            end_date: Optional end date 'YYYY-MM-DD'.

        Returns:
            DataFrame with columns ['date', 'close', 'daily_return'].
        """
        code_clean = str(code).strip()

        # 1. Check SQLite Cache
        df_cached = self.storage.get_benchmark(code_clean, start_date=start_date, end_date=end_date)
        if not df_cached.empty:
            logger.info(f"Cache hit for benchmark_nav {code_clean} ({len(df_cached)} records)")
            return df_cached

        # 2. Cache Miss - Fetch from AkShare API
        logger.info(f"Cache miss for benchmark_nav {code_clean}, fetching from AkShare...")
        try:
            df_api = self._execute_with_retry(self._fetch_akshare_benchmark, code_clean)
            if not df_api.empty:
                df_clean = self._clean_and_impute_benchmark(df_api)
                if not df_clean.empty:
                    self.storage.save_benchmark(code_clean, df_clean)
                    return self._filter_by_date(df_clean, start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to fetch benchmark {code_clean} after {self.max_retries} retries: {e}")

        # 3. Fallback: Return partial cached data or empty DataFrame
        df_all_cached = self.storage.get_benchmark(code_clean)
        if not df_all_cached.empty:
            logger.warning(f"Using fallback partial cache for benchmark {code_clean}")
            return self._filter_by_date(df_all_cached, start_date, end_date)

        logger.error(f"Returning empty DataFrame fallback for benchmark {code_clean}")
        return pd.DataFrame(columns=['date', 'close', 'daily_return'])

    def _fetch_akshare_benchmark(self, code: str) -> pd.DataFrame:
        """Raw AkShare API call for benchmark index."""
        import akshare as ak
        # Extract numeric code for AkShare index_zh_a_hist (e.g., '000029' from '000029.SH')
        numeric_code = code.split('.')[0]
        try:
            return ak.index_zh_a_hist(symbol=numeric_code, period="daily")
        except Exception:
            return ak.stock_zh_index_daily_em(symbol=f"sh{numeric_code}")

    def _clean_and_impute_benchmark(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean raw benchmark index DataFrame and calculate daily return."""
        df_clean = df.copy()

        date_col = next((c for c in ['日期', 'date', 'trade_date'] if c in df_clean.columns), None)
        close_col = next((c for c in ['收盘', 'close', '收盘价'] if c in df_clean.columns), None)

        if not date_col or not close_col:
            logger.warning("Required columns not found in raw benchmark DataFrame")
            return pd.DataFrame(columns=['date', 'close', 'daily_return'])

        df_clean['date'] = pd.to_datetime(df_clean[date_col], errors='coerce').dt.strftime('%Y-%m-%d')
        df_clean['close'] = pd.to_numeric(df_clean[close_col], errors='coerce')

        df_clean = df_clean.dropna(subset=['date']).sort_values('date').reset_index(drop=True)

        # Imputation: ffill().bfill().fillna(0.0)
        df_clean['close'] = df_clean['close'].ffill().bfill().fillna(0.0)
        df_clean['daily_return'] = df_clean['close'].pct_change().fillna(0.0)

        return df_clean[['date', 'close', 'daily_return']]

    # --- Utility Helpers ---

    @staticmethod
    def _filter_by_date(df: pd.DataFrame, start_date: Optional[str], end_date: Optional[str]) -> pd.DataFrame:
        """Filter DataFrame by optional start_date and end_date."""
        if df.empty or ('date' not in df.columns):
            return df
        df_filtered = df.copy()
        if start_date:
            df_filtered = df_filtered[df_filtered['date'] >= start_date]
        if end_date:
            df_filtered = df_filtered[df_filtered['date'] <= end_date]
        return df_filtered.reset_index(drop=True)
