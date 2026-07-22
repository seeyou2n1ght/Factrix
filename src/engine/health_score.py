"""Health Score & Comprehensive Diagnostic Engine.

Synthesizes results from all 6 analytical engines (PBSA, RBSA, Rolling RBSA,
CVaR Stress, Prospect Theory, Rebalance) into a 0-100 overall score, grade level,
and plain-language diagnostic summary with action points.
"""

from typing import Dict, Any, List


class HealthScoreEngine:
    """Engine for Synthesizing Panorama Health Score & Diagnostic Reports."""

    @staticmethod
    def calculate(
        pbsa_res: Dict[str, Any],
        rbsa_res: Dict[str, Any],
        rolling_res: Dict[str, Any],
        cvar_res: Dict[str, Any],
        prospect_res: Dict[str, Any],
        rebalance_res: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate overall 0-100 health score, rating level, and diagnostic text.

        Args:
            pbsa_res: Output dict from PBSAEngine.
            rbsa_res: Output dict from RBSAEngine.
            rolling_res: Output dict from RollingRBSAEngine.
            cvar_res: Output dict from CVaRStressEngine.
            prospect_res: Output dict from ProspectTheoryEngine.
            rebalance_res: Output dict from RebalanceEngine.

        Returns:
            Dict containing:
                - 'total_score': int (overall score 0-100)
                - 'health_score': int (alias for total_score)
                - 'level': str ('优'/'良'/'中'/'需保养')
                - 'summary_text': str (plain language diagnostic conclusion)
                - 'key_findings': List[str] (key findings and warnings list)
                - 'deductions': List[Dict] (detailed score deduction items)
        """
        score = 100
        key_findings: List[str] = []
        deductions: List[Dict[str, Any]] = []

        # 1. Evaluate PBSA (Holdings & Sector Penetration)
        top_stocks_df = pbsa_res.get('top_stocks')
        if top_stocks_df is not None and not top_stocks_df.empty:
            top_1_wt = float(top_stocks_df.iloc[0].get('amount_per_100', 0.0))
            if top_1_wt > 10.0:
                score -= 6
                msg = f"第一大重仓股权重占比高 ({top_1_wt:.1f}%), 个股风险集中"
                key_findings.append(msg)
                deductions.append({'dimension': '持仓穿透', 'points': -6, 'reason': msg})

            top_3_wt = float(top_stocks_df.iloc[:3]['amount_per_100'].sum())
            if top_3_wt > 25.0:
                score -= 8
                msg = f"前三大重仓股累计占比达 {top_3_wt:.1f}%, 存在抱团持仓倾向"
                key_findings.append(msg)
                deductions.append({'dimension': '持仓穿透', 'points': -8, 'reason': msg})

        sector_weights = pbsa_res.get('sector_weights')
        if sector_weights is not None and not sector_weights.empty:
            max_sector_wt = float(sector_weights.max())
            max_sector_name = str(sector_weights.idxmax())
            if max_sector_wt > 40.0:
                score -= 8
                msg = f"行业配置过度集中于【{max_sector_name}】(占比 {max_sector_wt:.1f}%)"
                key_findings.append(msg)
                deductions.append({'dimension': '行业分布', 'points': -8, 'reason': msg})

        overlap_matrix = pbsa_res.get('overlap_matrix')
        if overlap_matrix is not None and len(overlap_matrix) > 1:
            # Mask diagonal to find off-diagonal maximum overlap
            mat_val = overlap_matrix.values.copy()
            for i in range(len(mat_val)):
                mat_val[i, i] = 0.0
            max_overlap = float(mat_val.max())
            if max_overlap > 0.6:
                score -= 8
                msg = f"部分基金间持仓重合度较高 (最高重合度达 {max_overlap*100:.1f}%), 存在表面分散背地抱团风险"
                key_findings.append(msg)
                deductions.append({'dimension': '持仓重合', 'points': -8, 'reason': msg})

        # 2. Evaluate Rolling RBSA (Style Drift)
        drift_warning = rolling_res.get('drift_warning', False)
        if drift_warning:
            score -= 10
            msg = "检测到基金经理存在显著的【风格漂移】现象, 言行一致性较低"
            key_findings.append(msg)
            deductions.append({'dimension': '风格监测', 'points': -10, 'reason': msg})

        # 3. Evaluate CVaR & Stress Testing
        cvar_95 = cvar_res.get('cvar_95', 0.0)
        if cvar_95 > 0.04:  # > 4% daily CVaR
            score -= 10
            msg = f"95%置信度下极端尾部日风险(CVaR)达 {cvar_95*100:.1f}%, 下行波幅较大"
            key_findings.append(msg)
            deductions.append({'dimension': '尾部风险', 'points': -10, 'reason': msg})

        stress_scenarios = cvar_res.get('stress_results', {})
        max_stress_loss = max((s.get('loss_pct', 0.0) for s in stress_scenarios.values()), default=0.0)
        if max_stress_loss > 0.25:
            score -= 8
            msg = f"黑天鹅压力测试下最大预估亏损达 {max_stress_loss*100:.1f}%, 极端防暴雨能力不足"
            key_findings.append(msg)
            deductions.append({'dimension': '压力测试', 'points': -8, 'reason': msg})

        # 4. Evaluate Prospect Theory & Omega
        win_rate = prospect_res.get('win_rate', 0.5)
        if win_rate < 0.5:
            score -= 8
            msg = f"滚动持有期胜率偏低 ({win_rate*100:.1f}%), 长期正收益概率不足"
            key_findings.append(msg)
            deductions.append({'dimension': '胜率赔率', 'points': -8, 'reason': msg})

        payoff_ratio = prospect_res.get('payoff_ratio', 1.0)
        if payoff_ratio < 1.0:
            score -= 8
            msg = f"持仓赔率(盈亏比)较低 ({payoff_ratio:.2f}), 属于输多赢少的不划算买卖"
            key_findings.append(msg)
            deductions.append({'dimension': '胜率赔率', 'points': -8, 'reason': msg})

        omega_ratio = prospect_res.get('omega_ratio', 1.0)
        if omega_ratio < 1.0:
            score -= 6
            msg = f"Omega比率不足1.0 ({omega_ratio:.2f}), 下行亏损风险高于上行盈利潜能"
            key_findings.append(msg)
            deductions.append({'dimension': '心理效用', 'points': -6, 'reason': msg})

        # 5. Evaluate Rebalance Recommendations
        trade_actions = rebalance_res.get('trade_actions', [])
        if len(trade_actions) > 0:
            score -= 5
            msg = f"组合需要进行保养调仓 (建议执行 {len(trade_actions)} 项买卖操作)"
            key_findings.append(msg)
            deductions.append({'dimension': '配置优化', 'points': -5, 'reason': msg})

        # Final Score Bounding
        final_score = int(max(0, min(100, score)))

        # Determine Level Grade
        if final_score >= 90:
            level = '优'
            level_desc = '持仓结构非常健全，风险分散得当'
        elif final_score >= 75:
            level = '良'
            level_desc = '持仓整体稳健，局部存在小幅优化空间'
        elif final_score >= 60:
            level = '中'
            level_desc = '持仓存在一定风险集中或风格漂移，建议关注'
        else:
            level = '需保养'
            level_desc = '持仓结构风险较高，急需进行针对性调仓与配置保养'

        # Generate Vernacular Summary Text
        summary_text = (
            f"您的公募基金组合全景诊断得分为【{final_score}分】，综合评级为【{level}】（{level_desc}）。\n"
        )
        if key_findings:
            summary_text += "体检诊断发现以下关键注意项：\n"
            for idx, item in enumerate(key_findings, 1):
                summary_text += f"{idx}. {item}\n"
        else:
            summary_text += "组合在持仓穿透、风格稳定性、尾部风险和性价比维度表现均十分优异！"

        return {
            'total_score': final_score,
            'health_score': final_score,
            'level': level,
            'summary_text': summary_text,
            'key_findings': key_findings if key_findings else ["组合各项指标表现均衡"],
            'deductions': deductions
        }
