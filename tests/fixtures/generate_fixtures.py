"""
Fixture Data Generator for Factrix Offline Tests.
Generates deterministic, realistic 250-day NAV history, style benchmark indices,
top 10 holdings per fund, and sample CSV files.
"""

import json
import os
import numpy as np
import pandas as pd


def generate_all_fixtures():
    fixtures_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(fixtures_dir, exist_ok=True)

    # 1. Generate sample_fundlist.csv
    sample_csv_path = os.path.join(fixtures_dir, "sample_fundlist.csv")
    csv_content = (
        "序号,基金代码,基金名称,份额类别,基金管理人,销售机构,持有份额,份额日期,基金净值,净值日期,资产情况（结算币种）,结算币种,分红方式\n"
        "1,000001,华夏成长混合,前收费,华夏基金,北京雪球基金销售,10000.00,2026/07/20,1.2500,2026/07/20,12500.00,人民币,红利转投\n"
        "2,014114,广发沪港深医药混合A,前收费,广发基金,北京雪球基金销售,15000.00,2026/07/20,0.9900,2026/07/20,14850.00,人民币,红利转投\n"
        "3,001900,诺安精选价值混合A,前收费,诺安基金,北京雪球基金销售,8000.00,2026/07/20,1.5000,2026/07/20,12000.00,人民币,红利转投\n"
        "4,012094,鹏华创新升级混合C,前收费,鹏华基金,北京雪球基金销售,10000.00,2026/07/20,1.3800,2026/07/20,13800.00,人民币,红利转投\n"
        "5,022502,国泰黄金ETF联接E,前收费,国泰基金,北京雪球基金销售,3000.00,2026/07/20,3.1000,2026/07/20,9300.00,人民币,现金分红\n"
    )
    with open(sample_csv_path, "w", encoding="utf-8") as f:
        f.write(csv_content)

    # 2. Generate invalid_fundlist.csv
    invalid_csv_path = os.path.join(fixtures_dir, "invalid_fundlist.csv")
    invalid_content = "序号,错误代码,基金名称,持有份额\n1,000001,华夏成长,ABC\n"
    with open(invalid_csv_path, "w", encoding="utf-8") as f:
        f.write(invalid_content)

    # 3. Generate mock_holdings.json
    holdings_data = {
        "000001": [
            {"stock_code": "600519", "stock_name": "贵州茅台", "weight": 0.085, "sector": "消费"},
            {"stock_code": "300750", "stock_name": "宁德时代", "weight": 0.072, "sector": "新能源"},
            {"stock_code": "600036", "stock_name": "招商银行", "weight": 0.058, "sector": "金融"},
            {"stock_code": "002475", "stock_name": "立讯精密", "weight": 0.051, "sector": "电子"},
            {"stock_code": "600276", "stock_name": "恒瑞医药", "weight": 0.045, "sector": "医药"},
            {"stock_code": "300760", "stock_name": "迈瑞医疗", "weight": 0.042, "sector": "医药"},
            {"stock_code": "000858", "stock_name": "五粮液", "weight": 0.039, "sector": "消费"},
            {"stock_code": "002594", "stock_name": "比亚迪", "weight": 0.035, "sector": "新能源"},
            {"stock_code": "601318", "stock_name": "中国平安", "weight": 0.031, "sector": "金融"},
            {"stock_code": "00700", "stock_name": "腾讯控股", "weight": 0.028, "sector": "互联网"}
        ],
        "014114": [
            {"stock_code": "603259", "stock_name": "药明康德", "weight": 0.092, "sector": "医药"},
            {"stock_code": "600276", "stock_name": "恒瑞医药", "weight": 0.088, "sector": "医药"},
            {"stock_code": "300760", "stock_name": "迈瑞医疗", "weight": 0.075, "sector": "医药"},
            {"stock_code": "600436", "stock_name": "片仔癀", "weight": 0.061, "sector": "医药"},
            {"stock_code": "300015", "stock_name": "爱尔眼科", "weight": 0.053, "sector": "医药"},
            {"stock_code": "688235", "stock_name": "百济神州", "weight": 0.048, "sector": "医药"},
            {"stock_code": "01801", "stock_name": "信达生物", "weight": 0.042, "sector": "医药"},
            {"stock_code": "09926", "stock_name": "康方生物", "weight": 0.038, "sector": "医药"},
            {"stock_code": "688271", "stock_name": "联影医疗", "weight": 0.031, "sector": "医药"},
            {"stock_code": "000963", "stock_name": "华东医药", "weight": 0.025, "sector": "医药"}
        ],
        "001900": [
            {"stock_code": "688981", "stock_name": "中芯国际", "weight": 0.098, "sector": "半导体"},
            {"stock_code": "300661", "stock_name": "圣邦股份", "weight": 0.085, "sector": "半导体"},
            {"stock_code": "603501", "stock_name": "韦尔股份", "weight": 0.074, "sector": "半导体"},
            {"stock_code": "002371", "stock_name": "北方华创", "weight": 0.068, "sector": "半导体"},
            {"stock_code": "603986", "stock_name": "兆易创新", "weight": 0.059, "sector": "半导体"},
            {"stock_code": "300782", "stock_name": "卓胜微", "weight": 0.052, "sector": "半导体"},
            {"stock_code": "600584", "stock_name": "长电科技", "weight": 0.045, "sector": "半导体"},
            {"stock_code": "002049", "stock_name": "紫光国微", "weight": 0.039, "sector": "半导体"},
            {"stock_code": "688012", "stock_name": "中微公司", "weight": 0.033, "sector": "半导体"},
            {"stock_code": "688041", "stock_name": "海光信息", "weight": 0.029, "sector": "半导体"}
        ],
        "012094": [
            {"stock_code": "300750", "stock_name": "宁德时代", "weight": 0.095, "sector": "新能源"},
            {"stock_code": "300274", "stock_name": "阳光电源", "weight": 0.082, "sector": "新能源"},
            {"stock_code": "601012", "stock_name": "隆基绿能", "weight": 0.069, "sector": "光伏"},
            {"stock_code": "300141", "stock_name": "亿纬锂能", "weight": 0.058, "sector": "新能源"},
            {"stock_code": "600438", "stock_name": "通威股份", "weight": 0.051, "sector": "光伏"},
            {"stock_code": "688223", "stock_name": "晶科能源", "weight": 0.044, "sector": "光伏"},
            {"stock_code": "002594", "stock_name": "比亚迪", "weight": 0.039, "sector": "新能源"},
            {"stock_code": "300124", "stock_name": "汇川技术", "weight": 0.034, "sector": "制造"},
            {"stock_code": "002460", "stock_name": "赣锋锂业", "weight": 0.029, "sector": "资源"},
            {"stock_code": "002466", "stock_name": "天齐锂业", "weight": 0.025, "sector": "资源"}
        ],
        "022502": [
            {"stock_code": "601899", "stock_name": "紫金矿业", "weight": 0.099, "sector": "有色金属"},
            {"stock_code": "600547", "stock_name": "山东黄金", "weight": 0.091, "sector": "黄金"},
            {"stock_code": "600489", "stock_name": "中金黄金", "weight": 0.083, "sector": "黄金"},
            {"stock_code": "600988", "stock_name": "赤峰黄金", "weight": 0.072, "sector": "黄金"},
            {"stock_code": "000975", "stock_name": "银泰黄金", "weight": 0.061, "sector": "黄金"},
            {"stock_code": "002155", "stock_name": "湖南黄金", "weight": 0.052, "sector": "黄金"},
            {"stock_code": "601069", "stock_name": "西部黄金", "weight": 0.044, "sector": "黄金"},
            {"stock_code": "002237", "stock_name": "恒邦股份", "weight": 0.036, "sector": "黄金"},
            {"stock_code": "01818", "stock_name": "招金矿业", "weight": 0.030, "sector": "黄金"},
            {"stock_code": "600916", "stock_name": "中国黄金", "weight": 0.022, "sector": "黄金"}
        ]
    }
    holdings_json_path = os.path.join(fixtures_dir, "mock_holdings.json")
    with open(holdings_json_path, "w", encoding="utf-8") as f:
        json.dump(holdings_data, f, ensure_ascii=False, indent=2)

    # 4. Generate mock_nav_data.json (250 trading days)
    dates = pd.date_range(end="2026-07-20", periods=250, freq="B").strftime("%Y-%m-%d").tolist()

    np.random.seed(42)

    # Define parameters for each fund to simulate distinct styles
    fund_configs = {
        "000001": {"mu": 0.0004, "sigma": 0.012, "base_nav": 1.25},
        "014114": {"mu": -0.0002, "sigma": 0.018, "base_nav": 0.99},
        "001900": {"mu": 0.0006, "sigma": 0.022, "base_nav": 1.50},
        "012094": {"mu": 0.0003, "sigma": 0.016, "base_nav": 1.38},
        "022502": {"mu": 0.0008, "sigma": 0.009, "base_nav": 3.10},
    }

    funds_data = {}
    for code, cfg in fund_configs.items():
        ret_series = np.random.normal(cfg["mu"], cfg["sigma"], 250)
        # Fix first return to 0.0 for initial NAV reference
        ret_series[0] = 0.0
        nav_series = cfg["base_nav"] * np.cumprod(1.0 + ret_series)
        fund_records = []
        for d, nav, r in zip(dates, nav_series, ret_series):
            fund_records.append({
                "date": d,
                "nav": float(round(float(nav), 4)),
                "daily_return": float(round(float(r), 6))
            })
        funds_data[code] = fund_records

    # Generate benchmark & style factor indices
    factor_configs = {
        "hs300": {"mu": 0.0002, "sigma": 0.010},
        "zz500": {"mu": 0.0003, "sigma": 0.014},
        "gz2000": {"mu": 0.0004, "sigma": 0.018},
        "large_cap_value": {"mu": 0.0002, "sigma": 0.009},
        "small_cap_growth": {"mu": 0.0005, "sigma": 0.020},
        "large_cap_growth": {"mu": 0.0003, "sigma": 0.015},
        "small_cap_value": {"mu": 0.0002, "sigma": 0.011},
    }

    factor_series_dict = {}
    for factor, cfg in factor_configs.items():
        ret = np.random.normal(cfg["mu"], cfg["sigma"], 250)
        ret[0] = 0.0
        nav = 1.0 * np.cumprod(1.0 + ret)
        factor_series_dict[factor] = nav

    benchmarks_data = []
    for i, d in enumerate(dates):
        row = {"date": d}
        for factor in factor_configs.keys():
            row[factor] = float(round(float(factor_series_dict[factor][i]), 4))
        benchmarks_data.append(row)


    nav_data = {
        "funds": funds_data,
        "benchmarks": benchmarks_data
    }

    nav_json_path = os.path.join(fixtures_dir, "mock_nav_data.json")
    with open(nav_json_path, "w", encoding="utf-8") as f:
        json.dump(nav_data, f, ensure_ascii=False, indent=2)

    print("Written mock_nav_data.json successfully to:", nav_json_path)


generate_all_fixtures()

