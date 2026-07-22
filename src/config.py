"""Global configuration module for Factrix framework.

Provides configuration constants including paths, benchmark indices,
sector category mappings, prospect theory parameters, and redemption fee tiers.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple

# Project Directory Paths
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DEFAULT_CSV_PATH: Path = BASE_DIR / "fundlist.csv"
DB_PATH: Path = BASE_DIR / "fund_data.db"

# AkShare Data Fetching Settings
AKSHARE_MAX_RETRIES: int = 3
AKSHARE_BACKOFF_FACTOR: float = 2.0  # Retry wait backoff multiplier in seconds
AKSHARE_REQUEST_TIMEOUT: int = 10     # Request timeout in seconds

# RBSA Benchmark Style Indices Mapping
RBSA_BENCHMARKS: Dict[str, str] = {
    'large_value': '000029.SH',    # 中证大盘价值指数
    'large_growth': '000028.SH',   # 中证大盘成长指数
    'small_value': '000031.SH',    # 中证小盘价值指数
    'small_growth': '000030.SH',   # 中证小盘成长指数
    'bond_index': '000012.SH',     # 国债指数
}

# Sector Mapping: Shenwan Primary Sectors -> 5 Broad Categories
SECTOR_CATEGORY_MAP: Dict[str, str] = {
    # 科技制造
    '电子': '科技制造',
    '计算机': '科技制造',
    '通信': '科技制造',
    '国防军工': '科技制造',
    '机械设备': '科技制造',
    '电力设备': '科技制造',
    '汽车': '科技制造',
    '半导体': '科技制造',
    # 大消费
    '食品饮料': '大消费',
    '家用电器': '大消费',
    '农林牧渔': '大消费',
    '商贸零售': '大消费',
    '社会服务': '大消费',
    '轻工制造': '大消费',
    '纺织服饰': '大消费',
    '美容护理': '大消费',
    # 医药健康
    '医药生物': '医药健康',
    '医疗器械': '医药健康',
    '创新药': '医药健康',
    # 大金融
    '银行': '大金融',
    '非银金融': '大金融',
    '房地产': '大金融',
    '综合': '大金融',
    # 周期资源
    '煤炭': '周期资源',
    '石油石化': '周期资源',
    '基础化工': '周期资源',
    '钢铁': '周期资源',
    '有色金属': '周期资源',
    '建筑材料': '周期资源',
    '建筑装饰': '周期资源',
    '交通运输': '周期资源',
    '公用事业': '周期资源',
    '环保': '周期资源',
}

DEFAULT_SECTOR_CATEGORY: str = '其他'

def get_sector_category(sector_name: str) -> str:
    """Get broad sector category for a given detailed sector name.

    Args:
        sector_name: Name of the detailed sector or industry.

    Returns:
        Mapped broad category string. Returns '其他' if not mapped.
    """
    if not sector_name or not isinstance(sector_name, str):
        return DEFAULT_SECTOR_CATEGORY
    sector_clean = sector_name.strip()
    return SECTOR_CATEGORY_MAP.get(sector_clean, DEFAULT_SECTOR_CATEGORY)

# Prospect Theory Parameters (Kahneman & Tversky, 1992)
PROSPECT_LAMBDA: float = 2.25  # Loss aversion coefficient lambda
PROSPECT_ALPHA: float = 0.88   # Value function power parameter for gains
PROSPECT_BETA: float = 0.88    # Value function power parameter for losses

# Universal Redemption Fee Rate Tiers (Holding days upper bound, Fee rate)
REDEMPTION_FEE_TIERS: List[Tuple[int, float]] = [
    (7, 0.015),      # Holding days < 7: 1.50% penalty fee
    (30, 0.0075),    # Holding days < 30: 0.75%
    (365, 0.0050),   # Holding days < 365: 0.50%
    (99999, 0.0000), # Holding days >= 365: 0.00%
]

def get_redemption_fee_rate(holding_days: int) -> float:
    """Calculate redemption fee rate based on holding days.

    Args:
        holding_days: Number of days the fund position has been held.

    Returns:
        Fee rate as a decimal float (e.g. 0.015 for 1.5%).
    """
    if holding_days < 0:
        raise ValueError(f"Holding days must be non-negative, got {holding_days}")
    for days_limit, fee_rate in REDEMPTION_FEE_TIERS:
        if holding_days < days_limit:
            return fee_rate
    return 0.0
