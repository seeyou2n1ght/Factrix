"""Global configuration module for Factrix framework.

Provides configuration constants including paths, benchmark indices,
sector category mappings, prospect theory parameters, and redemption fee tiers.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple

import glob

# Project Directory Paths
BASE_DIR: Path = Path(__file__).resolve().parent.parent

def get_latest_data_file() -> Path:
    """Find the latest Fund E-Account export file in the base directory."""
    pattern = str(BASE_DIR / "基金E账户App投资者公募基金持有信息-*.xlsx")
    files = glob.glob(pattern)
    if not files:
        return BASE_DIR / "基金E账户App投资者公募基金持有信息-2026-07-17.xlsx"
    # Sort files by name (which contains the YYYY-MM-DD date) in descending order
    files.sort(reverse=True)
    return Path(files[0])

DEFAULT_FILE_PATH: Path = get_latest_data_file()
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

# CSRC (China Securities Regulatory Commission) 19 Industry Categories Mapping
CSRC_SECTOR_CATEGORY_MAP: Dict[str, str] = {
    # 农、林、牧、渔业
    '农、林、牧、渔业': '大消费',
    '农林牧渔业': '大消费',
    '农林牧渔': '大消费',
    # 采矿业
    '采矿业': '周期资源',
    # 制造业及具体子类
    '制造业': '科技制造',
    '医药制造业': '医药健康',
    '电子及通信设备制造业': '科技制造',
    '计算机、通信和其他电子设备制造业': '科技制造',
    '计算机通信和其他电子设备制造业': '科技制造',
    '电气机械和器材制造业': '科技制造',
    '汽车制造业': '科技制造',
    '专用设备制造业': '科技制造',
    '通用设备制造业': '科技制造',
    '化学原料和化学制品制造业': '周期资源',
    '黑色金属冶炼和压延加工业': '周期资源',
    '有色金属冶炼和压延加工业': '周期资源',
    '非金属矿物制品业': '周期资源',
    '食品制造业': '大消费',
    '酒、饮料和精制茶制造业': '大消费',
    '酒饮料和精制茶制造业': '大消费',
    '纺织业': '大消费',
    # 电力、热力、燃气及水生产和供应业
    '电力、热力、燃气及水生产和供应业': '周期资源',
    '电力热力燃气及水生产供应业': '周期资源',
    '电力、热力、燃气及水生产与供应业': '周期资源',
    # 建筑业
    '建筑业': '周期资源',
    # 批发和零售业
    '批发和零售业': '大消费',
    '批发与零售业': '大消费',
    # 交通运输、仓储和邮政业
    '交通运输、仓储和邮政业': '周期资源',
    '交通运输仓储和邮政业': '周期资源',
    '交通运输业': '周期资源',
    # 住宿和餐饮业
    '住宿和餐饮业': '大消费',
    # 信息传输、软件和信息技术服务业
    '信息传输、软件和信息技术服务业': '科技制造',
    '信息传输软件和信息技术服务业': '科技制造',
    '信息传输、计算机服务和软件业': '科技制造',
    # 金融业
    '金融业': '大金融',
    # 房地产业
    '房地产业': '大金融',
    # 租赁和商务服务业
    '租赁和商务服务业': '大金融',
    # 科学研究和技术服务业
    '科学研究和技术服务业': '科技制造',
    # 水利、环境和公共设施管理业
    '水利、环境和公共设施管理业': '周期资源',
    '水利环境和公共设施管理业': '周期资源',
    # 居民服务、修理和其他服务业
    '居民服务、修理和其他服务业': '大消费',
    '居民服务和其他服务业': '大消费',
    # 教育
    '教育': '大消费',
    # 卫生和社会工作
    '卫生和社会工作': '医药健康',
    '卫生与社会工作': '医药健康',
    # 文化、体育和娱乐业
    '文化、体育和娱乐业': '大消费',
    '文化体育和娱乐业': '大消费',
    # 综合
    '综合': '大金融',
}

DEFAULT_SECTOR_CATEGORY: str = '其他'

def get_sector_category(sector_name: str) -> str:
    """Get broad sector category for a given detailed sector or CSRC industry name.

    Args:
        sector_name: Name of the detailed sector or CSRC industry.

    Returns:
        Mapped broad category string. Returns '其他' if not mapped.
    """
    if not sector_name or not isinstance(sector_name, str):
        return DEFAULT_SECTOR_CATEGORY
    sector_clean = sector_name.strip()

    # 1. Direct lookup in Shenwan or CSRC map
    if sector_clean in SECTOR_CATEGORY_MAP:
        return SECTOR_CATEGORY_MAP[sector_clean]
    if sector_clean in CSRC_SECTOR_CATEGORY_MAP:
        return CSRC_SECTOR_CATEGORY_MAP[sector_clean]

    # 2. Punctuation stripping match
    no_punct = sector_clean.replace('、', '').replace(' ', '').replace('，', '')
    if no_punct in CSRC_SECTOR_CATEGORY_MAP:
        return CSRC_SECTOR_CATEGORY_MAP[no_punct]
    if no_punct in SECTOR_CATEGORY_MAP:
        return SECTOR_CATEGORY_MAP[no_punct]

    # 3. Substring matching against known keys
    for key, val in CSRC_SECTOR_CATEGORY_MAP.items():
        if len(key) >= 2 and (key in sector_clean or sector_clean in key):
            return val
    for key, val in SECTOR_CATEGORY_MAP.items():
        if len(key) >= 2 and (key in sector_clean or sector_clean in key):
            return val

    return DEFAULT_SECTOR_CATEGORY

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
