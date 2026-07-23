"""Markdown Report Generator Engine.

Exports the synthesized analysis results into a structured Markdown document.
"""

from typing import Dict, Any
import pandas as pd

class ReportGeneratorEngine:
    @staticmethod
    def generate_markdown(data: Dict[str, Any], filepath: str = 'Factrix_Report.md') -> None:
        """Generate and save a markdown report from the pipeline results."""
        if not data:
            return

        report_lines = []
        report_lines.append("# Factrix 投资组合深度分析报告\n")
        
        # 1. Overview
        report_lines.append("## 1. 资产总览")
        report_lines.append(f"- **总资产**: ¥ {data.get('total_value', 0):,.2f}")
        report_lines.append(f"- **持仓基金数量**: {data.get('n_funds', 0)} 只\n")
        
        # 2. Macro Asset Allocation
        report_lines.append("## 2. 宏观资产配置")
        pbsa_res = data.get('pbsa_res', {})
        macro_weights = pbsa_res.get('macro_asset_weights', pd.Series())
        for asset, weight in macro_weights.items():
            report_lines.append(f"- **{asset}**: {weight:.2f}%")
        report_lines.append("\n")
        
        # 3. Sector Penetration
        report_lines.append("## 3. 股票行业穿透 (前五大)")
        sector_weights = pbsa_res.get('sector_weights', pd.Series()).sort_values(ascending=False)
        for sector, weight in list(sector_weights.items())[:5]:
            report_lines.append(f"- **{sector}**: {weight:.2f}%")
        report_lines.append("\n")
        
        # 4. Style Regression (RBSA)
        report_lines.append("## 4. 风格归因 (RBSA)")
        rbsa_res = data.get('rbsa_res', {})
        r2_val = rbsa_res.get('r_squared', 0.0)
        report_lines.append(f"- **拟合优度 (R²)**: {r2_val:.4f}")
        style_w = rbsa_res.get('style_weights', {})
        for style, weight in style_w.items():
            report_lines.append(f"- **{style}**: {weight * 100:.2f}%")
        report_lines.append("\n")
        
        # 5. Tail Risk (CVaR & Stress)
        report_lines.append("## 5. 尾部风险与极端压力测试")
        cvar_res = data.get('cvar_res', {})
        cvar_95 = cvar_res.get('cvar_95', 0.0)
        report_lines.append(f"- **95% 极端损失 (CVaR)**: {cvar_95 * 100:.2f}%")
        
        stress_results = cvar_res.get('stress_results', {})
        for k, v in stress_results.items():
            report_lines.append(f"  - {v['scenario_name']}: 预计损失 **{v['loss_pct'] * 100:.2f}%** (¥ {v['loss_amount']:,.2f})")
        report_lines.append("\n")
        
        # 6. Health Score
        report_lines.append("## 6. 组合健康度体检")
        health_res = data.get('health_res', {})
        report_lines.append(f"- **综合健康得分**: {health_res.get('health_score', 0)}")
        report_lines.append(f"- **健康评级**: {health_res.get('level', '未知')}")
        report_lines.append(f"- **核心评价**: {health_res.get('summary_text', '')}\n")
        
        deductions = health_res.get('deductions', [])
        if deductions:
            report_lines.append("### 扣分项详细诊断:")
            for deduct in deductions:
                dim = deduct.get('dimension', '')
                pts = deduct.get('points', 0)
                rsn = deduct.get('reason', '')
                report_lines.append(f"- 📉 **{dim} ({pts} 分)**: {rsn}")
            
        report_text = "\n".join(report_lines)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_text)
        except Exception as e:
            print(f"Warning: Failed to write report to {filepath}: {e}")
