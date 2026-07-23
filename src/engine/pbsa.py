"""PBSA (Portfolio Breakdown & Stock Analysis) Engine.

Calculates downward portfolio stock penetration, 5-broad-sector weight distribution,
and fund-to-fund holdings overlap matrix using matrix cosine similarity.
"""

from typing import Dict, Any, List, Optional
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
    
    if sec in BROAD_SECTORS:
        return sec

    # 1. Direct mapping from config (handles Shenwan + CSRC industries)
    cat = get_sector_category(sec)
    if cat != DEFAULT_SECTOR_CATEGORY:
        return cat
        
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
        fund_market_values: Dict[str, float],
        industry_dict: Optional[Dict[str, pd.DataFrame]] = None,
        fund_types: Optional[Dict[str, str]] = None,
        fund_names: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Perform downward penetration and compute stock/sector weights, macro asset breakdown, and overlap matrix.

        Args:
            holdings_dict: Dictionary mapping fund_code -> holdings DataFrame
                           (columns: ['stock_code', 'stock_name', 'weight', 'sector']).
            fund_market_values: Dictionary mapping fund_code -> market value in RMB.
            industry_dict: Optional dictionary mapping fund_code -> industry allocation DataFrame
                           (columns: ['industry_name', 'weight', 'broad_sector']).
            fund_types: Optional dictionary mapping fund_code -> fund classification string.

        Returns:
            Dict containing:
                - 'stock_weights': pd.Series (indexed by stock_code, values = per 100 RMB amount)
                - 'sector_weights': pd.Series (100% Equity re-normalized broad sector distribution)
                - 'macro_asset_weights': pd.Series (4 macro asset classes: Equity, Fixed Income, Commodity, Cash)
                - 'overlap_matrix': pd.DataFrame (fund x fund cosine overlap ratio matrix in [0, 1])
                - 'top_stocks': pd.DataFrame (summary of top individual stock penetrations)
        """
        # Defensive Input Validation
        if not holdings_dict and not industry_dict:
            return PBSAEngine._empty_result(list(fund_market_values.keys()) if fund_market_values else [])
        if not fund_market_values:
            return PBSAEngine._empty_result([])

        total_market_value = float(sum(v for v in fund_market_values.values() if v > 0))
        if total_market_value <= 0:
            return PBSAEngine._empty_result(list(fund_market_values.keys()))

        fund_codes = [code for code in fund_market_values.keys() if fund_market_values[code] > 0]
        if not fund_codes:
            return PBSAEngine._empty_result([])

        # Fund weights in overall portfolio
        fund_weights = {code: float(fund_market_values[code]) / total_market_value for code in fund_codes}

        # 1. Macro Asset Class Isolation (Equity, Fixed Income, Commodity, Cash)
        macro_equity_total = 0.0
        macro_fixed_total = 0.0
        macro_commodity_total = 0.0
        macro_cash_total = 0.0

        drilldown_data = []

        for fund_code in fund_codes:
            f_weight = fund_weights[fund_code]
            ftype = (fund_types.get(fund_code, '') if fund_types else '') or ''
            fname = (fund_names.get(fund_code, fund_code) if fund_names else fund_code)

            eq_w = 0.0
            fi_w = 0.0
            co_w = 0.0
            
            industry_weights = {}

            if '债' in ftype:
                fi_w = 0.90
                eq_w = 0.0
            elif '货币' in ftype or '理财' in ftype:
                fi_w = 0.0
                eq_w = 0.0
            elif '商品' in ftype or '黄金' in ftype:
                co_w = 0.95
                eq_w = 0.0
            else:
                # Check industry_dict first for full equity allocation
                df_ind = industry_dict.get(fund_code) if industry_dict else None
                if df_ind is not None and not df_ind.empty:
                    w_col = 'weight' if 'weight' in df_ind.columns else df_ind.columns[1]
                    name_col = 'industry_name' if 'industry_name' in df_ind.columns else df_ind.columns[0]
                    raw_eq = pd.to_numeric(df_ind[w_col], errors='coerce').fillna(0.0).sum()
                    if raw_eq > 1.5:
                        raw_eq = raw_eq / 100.0
                    eq_w = min(1.0, float(raw_eq))
                    
                    for _, row in df_ind.iterrows():
                        iname = str(row[name_col])
                        bsec = map_broad_sector(iname)
                        iw = float(row[w_col])
                        if iw > 1.5:
                            iw /= 100.0
                        industry_weights[bsec] = industry_weights.get(bsec, 0.0) + iw
                else:
                    # Fallback to holdings_dict top 10 stocks
                    df_hold = holdings_dict.get(fund_code) if holdings_dict else None
                    if df_hold is not None and not df_hold.empty:
                        w_sum = pd.to_numeric(df_hold['weight'], errors='coerce').fillna(0.0).sum()
                        if w_sum > 1.5:
                            w_sum = w_sum / 100.0
                        eq_w = min(1.0, max(float(w_sum), 0.85))
                        
                        for _, row in df_hold.iterrows():
                            bsec = map_broad_sector(str(row.get('sector', '')))
                            iw = float(row.get('weight', 0.0))
                            if iw > 1.5:
                                iw /= 100.0
                            industry_weights[bsec] = industry_weights.get(bsec, 0.0) + iw
                    else:
                        eq_w = 0.0

            ca_w = max(0.0, 1.0 - eq_w - fi_w - co_w)

            macro_equity_total += f_weight * eq_w * 100.0
            macro_fixed_total += f_weight * fi_w * 100.0
            macro_commodity_total += f_weight * co_w * 100.0
            macro_cash_total += f_weight * ca_w * 100.0
            
            # --- Populate Drilldown Data ---
            if fi_w > 0:
                drilldown_data.append({'macro': '固收资产', 'sector': '固收/债券', 'fund': fname, 'stock': '债券资产', 'weight': f_weight * fi_w * 100.0, 'fund_code': fund_code})
            if ca_w > 0:
                drilldown_data.append({'macro': '现金等价物', 'sector': '货币/现金', 'fund': fname, 'stock': '现金资产', 'weight': f_weight * ca_w * 100.0, 'fund_code': fund_code})
            if co_w > 0:
                drilldown_data.append({'macro': '商品资产', 'sector': '商品/黄金', 'fund': fname, 'stock': '商品资产', 'weight': f_weight * co_w * 100.0, 'fund_code': fund_code})
            if eq_w > 0:
                # Normalize industry weights to match exactly eq_w
                iw_sum = sum(industry_weights.values())
                scale = (eq_w / iw_sum) if iw_sum > 0 else 1.0
                for sec, w in industry_weights.items():
                    drilldown_data.append({'macro': '权益资产', 'sector': sec, 'fund': fname, 'stock': None, 'weight': f_weight * (w * scale) * 100.0, 'fund_code': fund_code})

        macro_asset_weights = pd.Series({
            'Equity': round(macro_equity_total, 4),
            'Fixed Income': round(macro_fixed_total, 4),
            'Commodity': round(macro_commodity_total, 4),
            'Cash': round(macro_cash_total, 4),
        }, name='macro_asset_weights')

        # 2. Individual Stock Downward Penetration
        stock_records: List[Dict[str, Any]] = []
        fund_stock_weights: Dict[str, Dict[str, float]] = {code: {} for code in fund_codes}

        for fund_code in fund_codes:
            df_hold = holdings_dict.get(fund_code) if holdings_dict else None
            if df_hold is None or df_hold.empty:
                continue

            f_weight = fund_weights[fund_code]
            for _, row in df_hold.iterrows():
                scode = str(row.get('stock_code', '')).zfill(6)
                sname = str(row.get('stock_name', scode))
                w_fund = float(row.get('weight', 0.0))
                if w_fund > 1.5:
                    w_fund = w_fund / 100.0

                sec_raw = str(row.get('sector', DEFAULT_SECTOR_CATEGORY))
                broad_sec = map_broad_sector(sec_raw, stock_code=scode)

                if w_fund <= 0:
                    continue

                fund_stock_weights[fund_code][scode] = w_fund
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
                
        # Refine drilldown_data with stock level penetration
        final_drilldown_data = []
        for item in drilldown_data:
            if item['macro'] != '权益资产':
                final_drilldown_data.append(item)
                continue
            
            # For equity, break it down to stocks
            fund_code = item['fund_code']
            sector = item['sector']
            total_sec_weight = item['weight']
            fname = item['fund']
            
            df_hold = holdings_dict.get(fund_code) if holdings_dict else None
            stock_sum = 0.0
            if df_hold is not None and not df_hold.empty:
                for _, row in df_hold.iterrows():
                    bsec = map_broad_sector(str(row.get('sector', '')))
                    if bsec == sector:
                        sname = str(row.get('stock_name', ''))
                        w_fund = float(row.get('weight', 0.0))
                        if w_fund > 1.5:
                            w_fund /= 100.0
                        sw = fund_weights[fund_code] * w_fund * 100.0
                        # Cap stock weight to not exceed the sector's allocated weight
                        # (this handles scaling artifacts)
                        if stock_sum + sw > total_sec_weight:
                            sw = total_sec_weight - stock_sum
                        if sw > 0:
                            final_drilldown_data.append({
                                'macro': '权益资产', 'sector': sector, 'fund': fname, 
                                'stock': sname, 'weight': sw
                            })
                            stock_sum += sw
            
            other_weight = total_sec_weight - stock_sum
            if other_weight > 0.001:
                final_drilldown_data.append({
                    'macro': '权益资产', 'sector': sector, 'fund': fname, 
                    'stock': '隐形重仓及其他 (Others)', 'weight': other_weight
                })

        if stock_records:
            df_all_stocks = pd.DataFrame(stock_records)
            stock_summary = df_all_stocks.groupby('stock_code').agg({
                'stock_name': 'first',
                'sector': 'first',
                'broad_sector': 'first',
                'amount_per_100': 'sum'
            }).reset_index()

            stock_summary['weight_pct'] = stock_summary['amount_per_100']
            stock_summary = stock_summary.sort_values(by='amount_per_100', ascending=False).reset_index(drop=True)

            stock_weights_series = pd.Series(
                data=stock_summary['amount_per_100'].values,
                index=stock_summary['stock_code'].values,
                name='stock_weights_per_100'
            )
        else:
            stock_summary = pd.DataFrame(columns=['stock_code', 'stock_name', 'sector', 'broad_sector', 'amount_per_100', 'weight_pct'])
            stock_weights_series = pd.Series(dtype=float)

        # 3. Industry Sector Weight Allocation & 100% Equity Re-Normalization
        raw_sector_amounts: Dict[str, float] = {sec: 0.0 for sec in BROAD_SECTORS}

        for fund_code in fund_codes:
            f_weight = fund_weights[fund_code]
            df_ind = industry_dict.get(fund_code) if industry_dict else None

            if df_ind is not None and not df_ind.empty:
                ind_col = next((c for c in ['industry_name', '行业类别', '行业名称', '行业'] if c in df_ind.columns), df_ind.columns[0])
                w_col = next((c for c in ['weight', '占净值比例', '持仓比例', '配置比例'] if c in df_ind.columns), df_ind.columns[1])

                for _, r in df_ind.iterrows():
                    iname = str(r.get(ind_col, ''))
                    iw = float(pd.to_numeric(r.get(w_col, 0.0), errors='coerce') or 0.0)
                    if iw > 1.5:
                        iw = iw / 100.0
                    bsec = map_broad_sector(iname)
                    raw_sector_amounts[bsec] += f_weight * iw * 100.0
            else:
                # Fallback to stock_records aggregation for this fund
                df_hold = holdings_dict.get(fund_code) if holdings_dict else None
                if df_hold is not None and not df_hold.empty:
                    for _, row in df_hold.iterrows():
                        scode = str(row.get('stock_code', '')).zfill(6)
                        w_fund = float(row.get('weight', 0.0))
                        if w_fund > 1.5:
                            w_fund = w_fund / 100.0
                        sec_raw = str(row.get('sector', DEFAULT_SECTOR_CATEGORY))
                        broad_sec = map_broad_sector(sec_raw, stock_code=scode)
                        raw_sector_amounts[broad_sec] += f_weight * w_fund * 100.0

        # 100% Equity Industry Re-normalization across all 6 broad sectors (5 broad + 其他)
        total_sector_amount = sum(raw_sector_amounts[s] for s in BROAD_SECTORS)

        sector_weights_dict: Dict[str, float] = {}
        if total_sector_amount > 1e-6:
            for sec in BROAD_SECTORS:
                sector_weights_dict[sec] = float((raw_sector_amounts[sec] / total_sector_amount) * 100.0)
        else:
            for sec in ['大消费', '大金融', '医药健康', '科技制造', '周期资源']:
                sector_weights_dict[sec] = 0.0
            sector_weights_dict['其他'] = 100.0

        sector_weights_series = pd.Series(sector_weights_dict, name='sector_weights_per_100')

        # 4. Compute Fund-to-Fund Cosine Overlap Matrix O_ij
        n_funds = len(fund_codes)
        if stock_records:
            all_unique_stocks = sorted(list(set(r['stock_code'] for r in stock_records)))
            W = np.zeros((n_funds, len(all_unique_stocks)), dtype=float)
            stock_idx_map = {s: idx for idx, s in enumerate(all_unique_stocks)}

            for i, code in enumerate(fund_codes):
                for scode, w in fund_stock_weights[code].items():
                    if scode in stock_idx_map:
                        W[i, stock_idx_map[scode]] = w

            dot_product = np.dot(W, W.T)
            norms = np.linalg.norm(W, axis=1)
            norm_matrix = np.outer(norms, norms)

            with np.errstate(divide='ignore', invalid='ignore'):
                overlap_arr = np.where(norm_matrix > 1e-12, dot_product / norm_matrix, 0.0)

            for i in range(n_funds):
                overlap_arr[i, i] = 1.0 if norms[i] > 1e-12 else 0.0

            overlap_matrix = pd.DataFrame(overlap_arr, index=fund_codes, columns=fund_codes)
        else:
            overlap_matrix = pd.DataFrame(0.0, index=fund_codes, columns=fund_codes)

        return {
            'stock_weights': stock_weights_series,
            'sector_weights': sector_weights_series,
            'macro_asset_weights': macro_asset_weights,
            'overlap_matrix': overlap_matrix,
            'top_stocks': stock_summary.head(30),
            'drilldown_data': final_drilldown_data
        }

    @staticmethod
    def _empty_result(fund_codes: List[str]) -> Dict[str, Any]:
        """Return empty result structures for edge/error cases."""
        sector_series = pd.Series({sec: 0.0 for sec in BROAD_SECTORS}, name='sector_weights_per_100')
        macro_series = pd.Series({'Equity': 0.0, 'Fixed Income': 0.0, 'Commodity': 0.0, 'Cash': 0.0}, name='macro_asset_weights')
        overlap_matrix = pd.DataFrame(0.0, index=fund_codes, columns=fund_codes)
        top_stocks = pd.DataFrame(columns=['stock_code', 'stock_name', 'sector', 'broad_sector', 'amount_per_100', 'weight_pct'])
        return {
            'stock_weights': pd.Series(dtype=float),
            'sector_weights': sector_series,
            'macro_asset_weights': macro_series,
            'overlap_matrix': overlap_matrix,
            'top_stocks': top_stocks
        }
