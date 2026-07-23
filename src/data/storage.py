"""SQLite local cache storage module for Factrix.

Provides persistent caching for fund NAVs, fund top holdings,
and benchmark index daily data to reduce external API requests.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Union
import pandas as pd

from src.config import DB_PATH


class SQLiteStorage:
    """SQLite local cache storage manager for fund and benchmark data."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """Initialize SQLiteStorage with database file path.

        Args:
            db_path: Path to SQLite database file. Defaults to DB_PATH in config.
        """
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Get or create SQLite connection.

        Returns:
            Active sqlite3.Connection instance.
        """
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """Close SQLite connection if currently open."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "SQLiteStorage":
        """Context manager entry."""
        self.get_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    def _init_db(self) -> None:
        """Create database tables and indices if they do not exist."""
        conn = self.get_connection()
        cursor = conn.cursor()
        # 1. fund_nav
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fund_nav (
                fund_code TEXT NOT NULL,
                date TEXT NOT NULL,
                nav REAL NOT NULL,
                daily_return REAL NOT NULL DEFAULT 0.0,
                PRIMARY KEY (fund_code, date)
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fund_nav_code_date ON fund_nav(fund_code, date);")

        # 2. fund_holdings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fund_holdings (
                fund_code TEXT NOT NULL,
                report_date TEXT NOT NULL DEFAULT '',
                stock_code TEXT NOT NULL,
                stock_name TEXT NOT NULL DEFAULT '',
                weight REAL NOT NULL DEFAULT 0.0,
                sector TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (fund_code, report_date, stock_code)
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fund_holdings_code ON fund_holdings(fund_code);")

        # 3. benchmark_nav
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_nav (
                code TEXT NOT NULL,
                date TEXT NOT NULL,
                close REAL NOT NULL,
                daily_return REAL NOT NULL DEFAULT 0.0,
                PRIMARY KEY (code, date)
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_benchmark_nav_code_date ON benchmark_nav(code, date);")

        # 4. fund_industry_allocation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fund_industry_allocation (
                fund_code TEXT NOT NULL,
                report_date TEXT NOT NULL DEFAULT '',
                industry_name TEXT NOT NULL,
                weight REAL NOT NULL DEFAULT 0.0,
                market_value REAL NOT NULL DEFAULT 0.0,
                broad_sector TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (fund_code, report_date, industry_name)
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fund_industry_code ON fund_industry_allocation(fund_code);")

        conn.commit()


    # --- NAV Operations ---

    def save_nav(self, fund_code: str, df: pd.DataFrame) -> None:
        """Save fund NAV data into SQLite database.

        Args:
            fund_code: 6-digit fund code string.
            df: DataFrame containing at least ['date', 'nav'].
                May optionally contain 'daily_return'.
        """
        if df is None or df.empty:
            return
        fund_code_clean = str(fund_code).zfill(6)
        df_to_save = df.copy()
        df_to_save['fund_code'] = fund_code_clean

        if 'daily_return' not in df_to_save.columns:
            df_to_save['nav'] = pd.to_numeric(df_to_save['nav'], errors='coerce')
            df_to_save['daily_return'] = df_to_save['nav'].pct_change().fillna(0.0)

        df_to_save = df_to_save[['fund_code', 'date', 'nav', 'daily_return']].dropna(subset=['date', 'nav'])

        conn = self.get_connection()
        cursor = conn.cursor()
        records = [
            (row['fund_code'], str(row['date']), float(row['nav']), float(row['daily_return']))
            for _, row in df_to_save.iterrows()
        ]
        cursor.executemany("""
            INSERT OR REPLACE INTO fund_nav (fund_code, date, nav, daily_return)
            VALUES (?, ?, ?, ?)
        """, records)
        conn.commit()

    def get_nav(self, fund_code: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """Query cached fund NAV data from database.

        Args:
            fund_code: 6-digit fund code.
            start_date: Optional start date string 'YYYY-MM-DD'.
            end_date: Optional end date string 'YYYY-MM-DD'.

        Returns:
            DataFrame with columns ['date', 'nav', 'daily_return'] sorted by date.
        """
        fund_code_clean = str(fund_code).zfill(6)
        conn = self.get_connection()
        query = "SELECT date, nav, daily_return FROM fund_nav WHERE fund_code = ?"
        params = [fund_code_clean]

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date ASC"

        df = pd.read_sql_query(query, conn, params=params)
        return df

    # --- Holdings Operations ---

    def save_holdings(self, fund_code: str, df: pd.DataFrame, report_date: str = "") -> None:
        """Save fund holdings data into SQLite database.

        Args:
            fund_code: 6-digit fund code.
            df: DataFrame with columns ['stock_code', 'stock_name', 'weight', 'sector'].
                May optionally contain 'report_date'.
            report_date: Optional report date override string.
        """
        if df is None or df.empty:
            return
        fund_code_clean = str(fund_code).zfill(6)
        df_to_save = df.copy()
        df_to_save['fund_code'] = fund_code_clean
        if 'report_date' not in df_to_save.columns or not df_to_save['report_date'].any():
            df_to_save['report_date'] = report_date or ''

        for col in ['stock_name', 'sector']:
            if col not in df_to_save.columns:
                df_to_save[col] = ''
        if 'weight' not in df_to_save.columns:
            df_to_save['weight'] = 0.0

        df_to_save = df_to_save[['fund_code', 'report_date', 'stock_code', 'stock_name', 'weight', 'sector']]

        conn = self.get_connection()
        cursor = conn.cursor()
        records = [
            (
                str(row['fund_code']),
                str(row['report_date']),
                str(row['stock_code']),
                str(row['stock_name']),
                float(row['weight']),
                str(row['sector'])
            )
            for _, row in df_to_save.iterrows()
        ]
        cursor.executemany("""
            INSERT OR REPLACE INTO fund_holdings (fund_code, report_date, stock_code, stock_name, weight, sector)
            VALUES (?, ?, ?, ?, ?, ?)
        """, records)
        conn.commit()

    def get_holdings(self, fund_code: str, report_date: Optional[str] = None) -> pd.DataFrame:
        """Query cached fund holdings data from database.

        Args:
            fund_code: 6-digit fund code.
            report_date: Optional specific report date.

        Returns:
            DataFrame with columns ['stock_code', 'stock_name', 'weight', 'sector', 'report_date'].
        """
        fund_code_clean = str(fund_code).zfill(6)
        conn = self.get_connection()
        query = "SELECT stock_code, stock_name, weight, sector, report_date FROM fund_holdings WHERE fund_code = ?"
        params = [fund_code_clean]

        if report_date:
            query += " AND report_date = ?"
            params.append(report_date)

        query += " ORDER BY weight DESC"

        df = pd.read_sql_query(query, conn, params=params)
        return df

    # --- Benchmark Operations ---

    def save_benchmark(self, code: str, df: pd.DataFrame) -> None:
        """Save benchmark index daily NAV/close data into database.

        Args:
            code: Index symbol/code (e.g., '000029.SH').
            df: DataFrame containing at least ['date', 'close'].
                May optionally contain 'daily_return'.
        """
        if df is None or df.empty:
            return
        df_to_save = df.copy()
        df_to_save['code'] = str(code)

        if 'daily_return' not in df_to_save.columns:
            df_to_save['close'] = pd.to_numeric(df_to_save['close'], errors='coerce')
            df_to_save['daily_return'] = df_to_save['close'].pct_change().fillna(0.0)

        df_to_save = df_to_save[['code', 'date', 'close', 'daily_return']].dropna(subset=['date', 'close'])

        conn = self.get_connection()
        cursor = conn.cursor()
        records = [
            (str(row['code']), str(row['date']), float(row['close']), float(row['daily_return']))
            for _, row in df_to_save.iterrows()
        ]
        cursor.executemany("""
            INSERT OR REPLACE INTO benchmark_nav (code, date, close, daily_return)
            VALUES (?, ?, ?, ?)
        """, records)
        conn.commit()

    def get_benchmark(self, code: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """Query cached benchmark index data from database.

        Args:
            code: Index symbol.
            start_date: Optional start date 'YYYY-MM-DD'.
            end_date: Optional end date 'YYYY-MM-DD'.

        Returns:
            DataFrame with columns ['date', 'close', 'daily_return'] sorted by date.
        """
        conn = self.get_connection()
        query = "SELECT date, close, daily_return FROM benchmark_nav WHERE code = ?"
        params = [str(code)]

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date ASC"

        df = pd.read_sql_query(query, conn, params=params)
        return df

    # --- Industry Allocation Operations ---

    def save_industry_allocation(self, fund_code: str, df: pd.DataFrame, report_date: str = "") -> None:
        """Save fund industry allocation data into SQLite database.

        Args:
            fund_code: 6-digit fund code.
            df: DataFrame with columns ['industry_name', 'weight'].
                May optionally contain ['market_value', 'broad_sector', 'report_date'].
            report_date: Optional report date override string.
        """
        if df is None or df.empty:
            return
        fund_code_clean = str(fund_code).zfill(6)
        df_to_save = df.copy()
        df_to_save['fund_code'] = fund_code_clean
        if 'report_date' not in df_to_save.columns or not df_to_save['report_date'].any():
            df_to_save['report_date'] = report_date or ''

        for col in ['market_value', 'weight']:
            if col not in df_to_save.columns:
                df_to_save[col] = 0.0
        for col in ['broad_sector', 'industry_name']:
            if col not in df_to_save.columns:
                df_to_save[col] = ''

        df_to_save = df_to_save[['fund_code', 'report_date', 'industry_name', 'weight', 'market_value', 'broad_sector']]

        conn = self.get_connection()
        cursor = conn.cursor()
        records = [
            (
                str(row['fund_code']),
                str(row['report_date']),
                str(row['industry_name']),
                float(row['weight']),
                float(row['market_value']),
                str(row['broad_sector'])
            )
            for _, row in df_to_save.iterrows()
        ]
        cursor.executemany("""
            INSERT OR REPLACE INTO fund_industry_allocation
            (fund_code, report_date, industry_name, weight, market_value, broad_sector)
            VALUES (?, ?, ?, ?, ?, ?)
        """, records)
        conn.commit()

    def get_industry_allocation(self, fund_code: str, report_date: Optional[str] = None) -> pd.DataFrame:
        """Query cached fund industry allocation data from database.

        Args:
            fund_code: 6-digit fund code.
            report_date: Optional specific report date.

        Returns:
            DataFrame with columns ['industry_name', 'weight', 'market_value', 'broad_sector', 'report_date'].
        """
        fund_code_clean = str(fund_code).zfill(6)
        conn = self.get_connection()
        query = "SELECT industry_name, weight, market_value, broad_sector, report_date FROM fund_industry_allocation WHERE fund_code = ?"
        params = [fund_code_clean]

        if report_date:
            query += " AND report_date = ?"
            params.append(report_date)

        query += " ORDER BY weight DESC"

        df = pd.read_sql_query(query, conn, params=params)
        return df

    # --- Cache Management ---

    def clear_cache(self, table_name: Optional[str] = None) -> None:
        """Clear cached data from database tables.

        Args:
            table_name: Table to clear ('fund_nav', 'fund_holdings', 'benchmark_nav', 'fund_industry_allocation').
                If None, clears all tables.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        tables = [table_name] if table_name else ['fund_nav', 'fund_holdings', 'benchmark_nav', 'fund_industry_allocation']
        for tbl in tables:
            cursor.execute(f"DELETE FROM {tbl};")
        conn.commit()

    # Aliases for PROJECT.md contract compliance
    save_nav_cache = save_nav
    get_nav_cache = get_nav
    save_holdings_cache = save_holdings
    get_holdings_cache = get_holdings
    save_industry_allocation_cache = save_industry_allocation
    get_industry_allocation_cache = get_industry_allocation
