import os
import sys
from pprint import pprint
import pandas as pd
import numpy as np

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import load_and_analyze_data

# Force UTF-8 encoding for Windows terminal
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def check_dict(d, prefix=""):
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, pd.DataFrame):
                print(f"{prefix}{k}: DataFrame shape {v.shape}")
                print(f"{prefix}  Null values:\n{v.isnull().sum()}")
            elif isinstance(v, pd.Series):
                print(f"{prefix}{k}: Series shape {v.shape}")
            elif isinstance(v, (int, float, str, bool)):
                print(f"{prefix}{k}: {v}")
            elif isinstance(v, list):
                print(f"{prefix}{k}: List length {len(v)}")
            elif isinstance(v, dict):
                print(f"{prefix}{k}: Dict")
                check_dict(v, prefix + "  ")
            else:
                print(f"{prefix}{k}: {type(v)}")

def main():
    print("Running data pipeline...")
    try:
        from src.config import DEFAULT_FILE_PATH
        data = load_and_analyze_data(str(DEFAULT_FILE_PATH))
        print("Pipeline finished successfully. Result summary:")
        check_dict(data)

        print("\n--- Key Engine Outputs Inspection ---")
        required_engines = [
            'alpha_beta_res',
            'pbsa_res',
            'rbsa_res',
            'cvar_res',
            'rebalance_res',
            'health_res',
        ]
        for engine_key in required_engines:
            if engine_key in data:
                val = data[engine_key]
                size_desc = len(val) if isinstance(val, (dict, list, pd.DataFrame)) else "N/A"
                print(f"  [OK] {engine_key}: present (type: {type(val).__name__}, entries: {size_desc})")
            else:
                print(f"  [ERROR] {engine_key}: MISSING from pipeline output!")

        ab = data.get('alpha_beta_res', {})
        print("\n--- Alpha & Beta Key CAPM Metrics ---")
        print(f"  Portfolio Alpha (Annualized): {ab.get('portfolio_alpha', 0.0):.4f}")
        print(f"  Portfolio Beta:               {ab.get('portfolio_beta', 0.0):.4f}")
        print(f"  Sharpe Ratio:                 {ab.get('sharpe_ratio', 0.0):.4f}")
        print(f"  Treynor Ratio:                {ab.get('treynor_ratio', 0.0):.4f}")
        print(f"  Information Ratio:            {ab.get('information_ratio', 0.0):.4f}")
        print(f"  Tracking Error:               {ab.get('tracking_error', 0.0):.4f}")
        print(f"  Regression Scatter Points:    {len(ab.get('scatter_data', []))}")

        health = data.get('health_res', {})
        print("\n--- Health Score Summary ---")
        print(f"  Total Health Score:           {health.get('total_score', 0)}")
        print(f"  Health Level:                 {health.get('level', 'N/A')}")

    except Exception as e:
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
