"""CSV Parser module for Factrix.

Parses and normalizes public fund portfolio CSV files exported from Fund E Account App
or standard template format. Handles header newline issues, 6-digit fund code zero-padding,
trailing empty/disclaimer rows, and optional aggregation of duplicate fund entries.
"""

import os
import re
from typing import Tuple, List, Optional
import pandas as pd
import numpy as np


REQUIRED_COLUMNS: List[str] = ['fund_code', 'fund_name', 'share', 'nav', 'market_value']
ALL_COLUMNS: List[str] = ['fund_code', 'fund_name', 'share', 'nav', 'market_value', 'nav_date', 'channel']


def parse_fundlist_csv(csv_path: str, aggregate: bool = True) -> pd.DataFrame:
    """Parse and clean public fund position CSV file.

    Args:
        csv_path: Absolute or relative path to the fund list CSV file.
        aggregate: If True, aggregate positions with identical fund codes by summing shares
            and market values. Defaults to True.

    Returns:
        Normalized pd.DataFrame with columns:
        ['fund_code', 'fund_name', 'share', 'nav', 'market_value', 'nav_date', 'channel']

    Raises:
        FileNotFoundError: If the specified csv_path does not exist.
        ValueError: If parsing fails to yield any valid data or required columns.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Specified CSV file does not exist: {csv_path}")

    # 1. Read raw CSV with string dtype to preserve leading zeroes
    df_raw: Optional[pd.DataFrame] = None
    encodings_to_try = ['utf-8', 'utf-8-sig', 'gbk', 'gb18030']
    
    for encoding in encodings_to_try:
        try:
            df_raw = pd.read_csv(csv_path, dtype=str, encoding=encoding)
            break
        except (UnicodeDecodeError, Exception):
            continue

    if df_raw is None or df_raw.empty:
        raise ValueError(f"Failed to read CSV file or file is empty: {csv_path}")

    # 2. Clean column names (strip newlines, carriage returns, and spaces)
    df_raw.columns = [
        str(col).replace('\n', '').replace('\r', '').strip()
        for col in df_raw.columns
    ]

    # 3. Map original column names to normalized standard names
    col_map = {
        '基金代码': 'fund_code',
        '基金名称': 'fund_name',
        '持有份额': 'share',
        '基金净值': 'nav',
        '净值日期': 'nav_date',
        '销售机构': 'channel',
    }

    # Dynamically match '资产情况' column (e.g., '资产情况（结算币种）')
    for col in df_raw.columns:
        if '资产情况' in col:
            col_map[col] = 'market_value'
            break

    df = df_raw.rename(columns=col_map)

    # 4. Filter out non-data tail rows (e.g. empty comma lines, disclaimers, summary notes)
    if '序号' in df.columns:
        valid_mask = pd.to_numeric(df['序号'], errors='coerce').notna()
        df = df[valid_mask].copy()

    if 'fund_code' not in df.columns:
        raise ValueError("CSV missing required column '基金代码' (fund_code)")

    # Filter out rows where fund_code is not numeric (disclaimers, notes, header artifacts)
    df = df[df['fund_code'].notna() & df['fund_code'].str.strip().str.contains(r'^\d+$', regex=True)].copy()

    if df.empty:
        raise ValueError("No valid fund data rows found in CSV after filtering")

    # 5. Clean data types and normalize formatting
    df['fund_code'] = df['fund_code'].str.strip().str.zfill(6)
    df['fund_name'] = df['fund_name'].fillna('').str.strip()

    df['share'] = pd.to_numeric(df['share'], errors='coerce').fillna(0.0)
    df['nav'] = pd.to_numeric(df['nav'], errors='coerce').fillna(0.0)

    if 'market_value' in df.columns:
        df['market_value'] = pd.to_numeric(df['market_value'], errors='coerce')
        # Auto-compute market_value if missing or non-positive
        df['market_value'] = np.where(
            (df['market_value'].isna()) | (df['market_value'] <= 0),
            df['share'] * df['nav'],
            df['market_value']
        )
    else:
        df['market_value'] = df['share'] * df['nav']

    # Date normalization YYYY-MM-DD
    if 'nav_date' in df.columns:
        df['nav_date'] = df['nav_date'].astype(str).str.replace('/', '-', regex=False).str.strip()
    else:
        df['nav_date'] = ''

    if 'channel' not in df.columns:
        df['channel'] = ''

    # Filter out invalid or zero positions (share > 0)
    df = df[df['share'] > 0].copy()

    if df.empty:
        raise ValueError("No positive share fund entries remaining after cleaning")

    # 6. Aggregate duplicate fund entries if aggregate=True
    if aggregate:
        df = df.groupby('fund_code', as_index=False).agg({
            'fund_name': 'first',
            'share': 'sum',
            'market_value': 'sum',
            'nav': 'last',
            'nav_date': 'last',
            'channel': lambda x: ','.join(sorted(set(str(v) for v in x if pd.notna(v) and str(v).strip())))
        })

    # Return standardized columns order
    output_cols = [c for c in ALL_COLUMNS if c in df.columns]
    return df[output_cols].reset_index(drop=True)


def validate_parsed_data(df: pd.DataFrame) -> Tuple[bool, str]:
    """Validate completeness and correctness of parsed fund DataFrame.

    Args:
        df: Parsed pandas DataFrame.

    Returns:
        Tuple of (is_valid: bool, message: str).
    """
    if df is None or not isinstance(df, pd.DataFrame):
        return False, "Input is not a pandas DataFrame"

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            return False, f"Missing required column: {col}"

    if df.empty:
        return False, "Parsed DataFrame is empty"

    if (df['share'] <= 0).any():
        return False, "DataFrame contains non-positive share values"

    if (df['fund_code'].str.len() != 6).any():
        return False, "DataFrame contains fund codes that are not 6 digits"

    return True, "Valid"
