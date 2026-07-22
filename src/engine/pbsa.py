"""PBSA (Portfolio Breakdown & Stock Analysis) Engine.

Calculates downward portfolio stock penetration, 5-broad-sector weight distribution,
and fund-to-fund holdings overlap matrix using matrix cosine similarity.
"""

from typing import Dict, Any, List
import pandas as pd
import numpy as np

from src.config import SECTOR_CATEGORY_MAP, DEFAULT_SECTOR_CATEGORY, get_sector_category

# 5 broad sector categories + 其他
BROAD_SECTORS: List[str] = ['大消费', '大金融', '医药健康', '科技制造', '周期资源', '其他']

# Hardcoded stock code -> broad sector lookup for common A/HK shares
# Used as last-resort fallback when sector name column is missing or unmapped
STOCK_CODE_SECTOR_MAP: Dict[str, str] = {
    # 大消费
    '600519': '大消费', '000858': '大消费', '603288': '大消费', '002304': '大消费',
    '000568': '大消费', '600809': '大消费', '601888': '大消费', '600887': '大消费',
    '601336': '大消费', '002273': '大消费', '603012': '大消费',
    # 科技制造
    '300750': '科技制造', '002594': '科技制造', '601127': '科技制造', '300014': '科技制造',
    '002230': '科技制造', '600703': '科技制造', '688981': '科技制造', '002371': '科技制造',
    '002475': '科技制造', '300015': '医药健康',  # 爱尔眼科 → 医药
    '002027': '科技制造', '000725': '科技制造', '601012': '科技制造',
    # 大金融
    '600036': '大金融', '601318': '大金融', '600016': '大金融', '601166': '大金融',
    '600030': '大金融', '601601': '大金融', '601668': '大金融', '601328': '大金融',
    '600000': '大金融', '601998': '大金融', '601688': '大金融', '601211': '大金融',
    '600837': '大金融', '000001': '大金融', '002142': '大金融',
    # 医药健康
    '600276': '医药健康', '603259': '医药健康', '300122': '医药健康', '002415': '医药健康',
    '300760': '医药健康', '688506': '医药健康', '600867': '医药健康', '000538': '医药健康',
    '600763': '医药健康', '300347': '医药健康',
    # 周期资源
    '600900': '周期资源', '601857': '周期资源', '600309': '周期资源', '601899': '周期资源',
    '002460': '周期资源', '600585': '周期资源', '601225': '周期资源', '000002': '大金融',
    '601390': '周期资源', '601800': '周期资源', '600011': '周期资源',
    # 港股常见（以5/6/9开头，保留前4位匹配思路)
    '000700': '科技制造',  # 腾讯控股 0700.HK → pad to 6
    '009988': '大消费',    # 阿里巴巴
}

def map_broad_sector(sector_name: str, stock_code: str = '') -> str:
    """Map a detailed sector or industry name to one of 5 broad categories or '其他'.

    Args:
        sector_name: Name of sector/industry string.
        stock_code: Optional 6-digit stock code for code-based fallback lookup.

    Returns:
        Mapped broad sector string.
    """
    if not sector_name or not isinstance(sector_name, str):
        # Try stock_code lookup first
        if stock_code and stock_code in STOCK_CODE_SECTOR_MAP:
            return STOCK_CODE_SECTOR_MAP[stock_code]
        return DEFAULT_SECTOR_CATEGORY
    sec = sector_name.strip()
    
    # 1. Direct mapping from config
    if sec in SECTOR_CATEGORY_MAP:
        return SECTOR_CATEGORY_MAP[sec]
    if sec in BROAD_SECTORS:
        return sec
        
    # 2. Keyword fallback mapping for coarse sector names
    if any(k in sec for k in ['消费', '白酒', '家电', '餐饮', '零售', '服饰']):
        return '大消费'
    if any(k in sec for k in ['金融', '银行', '保险', '证券', '信托', '地产', '房地产']):
        return '大金融'
    if any(k in sec for k in ['医药', '医疗', '生物', '药', '医', '健康']):
        return '医药健康'
    if any(k in sec for k in ['科技', '新能源', '半导体', '电子', '芯片', '软件',
                                '光伏', '制造', '通信', '计算机', '互联网', '人工智能',
                                '汽车', '电力设备', '电气']):
        return '科技制造'
    if any(k in sec for k in ['资源', '黄金', '有色', '周期', '煤炭', '石油',
                                '化工', '钢铁', '建材', '建筑', '交通', '电力', '公用']):
        return '周期资源'
    
    # 3. Stock code lookup as final fallback
    if stock_code and stock_code in STOCK_CODE_SECTOR_MAP:
        return STOCK_CODE_SECTOR_MAP[stock_code]
        
    return DEFAULT_SECTOR_CATEGORY



class PBSAEngine:
    """Engine for PBSA Penetration & Holding Overlap Analysis."""

    @staticmethod
    def calculate(
        holdings_dict: Dict[str, pd.DataFrame],
        fund_market_values: Dict[str, float]
    ) -> Dict[str, Any]:
        """Perform downward penetration and compute stock/sector weights and overlap matrix.

        Args:
            holdings_dict: Dictionary mapping fund_code -> holdings DataFrame
                           (columns: ['stock_code', 'stock_name', 'weight', 'sector']).
            fund_market_values: Dictionary mapping fund_code -> market value in RMB.

        Returns:
            Dict containing:
                - 'stock_weights': pd.Series (indexed by stock_code, values = per 100 RMB amount)
                - 'sector_weights': pd.Series (indexed by 5 broad sectors + 其他, values = per 100 RMB amount)
                - 'overlap_matrix': pd.DataFrame (fund x fund cosine overlap ratio matrix in [0, 1])
                - 'top_stocks': pd.DataFrame (summary of top individual stock penetrations)
        """
        # Defensive Input Validation
        if not holdings_dict or not fund_market_values:
            return PBSAEngine._empty_result(list(fund_market_values.keys()) if fund_market_values else [])

        total_market_value = float(sum(v for v in fund_market_values.values() if v > 0))
        if total_market_value <= 0:
            return PBSAEngine._empty_result(list(fund_market_values.keys()))

        fund_codes = [code for code in fund_market_values.keys() if fund_market_values[code] > 0]
        if not fund_codes:
            return PBSAEngine._empty_result([])

        # Fund weights in overall portfolio
        fund_weights = {code: float(fund_market_values[code]) / total_market_value for code in fund_codes}

        # 1. Accumulate Penetrated Stock Amounts and Sector Amounts
        stock_records: List[Dict[str, Any]] = []
        fund_stock_weights: Dict[str, Dict[str, float]] = {code: {} for code in fund_codes}

        for fund_code in fund_codes:
            df_hold = holdings_dict.get(fund_code)
            if df_hold is None or df_hold.empty:
                continue

            f_weight = fund_weights[fund_code]
            for _, row in df_hold.iterrows():
                scode = str(row.get('stock_code', '')).zfill(6)
                sname = str(row.get('stock_name', scode))
                w_fund = float(row.get('weight', 0.0))  # weight within fund portfolio (e.g. 0.085)
                sec_raw = str(row.get('sector', DEFAULT_SECTOR_CATEGORY))
                broad_sec = map_broad_sector(sec_raw, stock_code=scode)

                if w_fund <= 0:
                    continue

                # Stock weight within this fund (capped at 1.0 if entered as fraction)
                fund_stock_weights[fund_code][scode] = w_fund

                # Contribution to overall portfolio per 100 RMB
                port_stock_weight_100 = f_weight * w_fund * 100.0

                stock_records.append({
                    'fund_code': fund_code,
                    'stock_code': scode,
                    'stock_name': sname,
                    'sector': sec_raw,
                    'broad_sector': broad_sec,
                    'fund_weight': w_fund,
                    'amount_per_100': port_stock_weight_100,
                })

        if not stock_records:
            return PBSAEngine._empty_result(fund_codes)

        df_all_stocks = pd.DataFrame(stock_records)

        # Aggregate stock totals
        stock_summary = df_all_stocks.groupby('stock_code').agg({
            'stock_name': 'first',
            'sector': 'first',
            'broad_sector': 'first',
            'amount_per_100': 'sum'
        }).reset_index()

        stock_summary['weight_pct'] = stock_summary['amount_per_100']  # % of total portfolio
        stock_summary = stock_summary.sort_values(by='amount_per_100', ascending=False).reset_index(drop=True)

        stock_weights_series = pd.Series(
            data=stock_summary['amount_per_100'].values,
            index=stock_summary['stock_code'].values,
            name='stock_weights_per_100'
        )

        # Aggregate sector totals (guarantee all 6 broad sector categories are present)
        sector_agg = stock_summary.groupby('broad_sector')['amount_per_100'].sum().to_dict()
        sector_weights_dict = {sec: float(sector_agg.get(sec, 0.0)) for sec in BROAD_SECTORS}
        sector_weights_series = pd.Series(sector_weights_dict, name='sector_weights_per_100')

        # 2. Compute Fund-to-Fund Cosine Overlap Matrix O_ij = (w_i . w_j) / (||w_i|| * ||w_j||)
        all_unique_stocks = sorted(list(set(df_all_stocks['stock_code'].unique())))
        n_funds = len(fund_codes)

        # Build weight matrix W (shape: n_funds x n_stocks)
        W = np.zeros((n_funds, len(all_unique_stocks)), dtype=float)
        stock_idx_map = {s: idx for idx, s in enumerate(all_unique_stocks)}

        for i, code in enumerate(fund_codes):
            for scode, w in fund_stock_weights[code].items():
                if scode in stock_idx_map:
                    W[i, stock_idx_map[scode]] = w

        # Dot products and norms
        dot_product = np.dot(W, W.T)
        norms = np.linalg.norm(W, axis=1)
        norm_matrix = np.outer(norms, norms)

        # Avoid division by zero
        with np.errstate(divide='ignore', invalid='ignore'):
            overlap_arr = np.where(norm_matrix > 1e-12, dot_product / norm_matrix, 0.0)

        # Ensure diagonal is 1.0 if fund has non-zero holdings
        for i in range(n_funds):
            if norms[i] > 1e-12:
                overlap_arr[i, i] = 1.0
            else:
                overlap_arr[i, i] = 0.0

        overlap_matrix = pd.DataFrame(overlap_arr, index=fund_codes, columns=fund_codes)

        return {
            'stock_weights': stock_weights_series,
            'sector_weights': sector_weights_series,
            'overlap_matrix': overlap_matrix,
            'top_stocks': stock_summary
        }

    @staticmethod
    def _empty_result(fund_codes: List[str]) -> Dict[str, Any]:
        """Return empty result structures for edge/error cases."""
        sector_series = pd.Series({sec: 0.0 for sec in BROAD_SECTORS}, name='sector_weights_per_100')
        overlap_matrix = pd.DataFrame(0.0, index=fund_codes, columns=fund_codes)
        top_stocks = pd.DataFrame(columns=['stock_code', 'stock_name', 'sector', 'broad_sector', 'amount_per_100', 'weight_pct'])
        return {
            'stock_weights': pd.Series(dtype=float),
            'sector_weights': sector_series,
            'overlap_matrix': overlap_matrix,
            'top_stocks': top_stocks
        }
