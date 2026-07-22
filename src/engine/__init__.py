"""Calculations Engine Package for Factrix.

Contains core algorithm engines for the 7 analysis dimensions:
1. PBSAEngine: Stock penetration & holdings overlap matrix
2. RBSAEngine: Returns-based style attribution via constrained QP
3. RollingRBSAEngine: Rolling style drift monitoring & factor variance
4. CVaRStressEngine: Cornish-Fisher CVaR & Black Swan stress testing
5. ProspectTheoryEngine: Win/Loss matrix, Prospect utility, Omega ratio
6. RebalanceEngine: Quad-programming rebalance with transaction friction
7. HealthScoreEngine: 0-100 panorama health score & diagnostic report
"""

from src.engine.pbsa import PBSAEngine
from src.engine.rbsa import RBSAEngine
from src.engine.rolling_rbsa import RollingRBSAEngine
from src.engine.cvar_stress import CVaRStressEngine
from src.engine.prospect_theory import ProspectTheoryEngine
from src.engine.rebalance import RebalanceEngine
from src.engine.health_score import HealthScoreEngine

__all__ = [
    'PBSAEngine',
    'RBSAEngine',
    'RollingRBSAEngine',
    'CVaRStressEngine',
    'ProspectTheoryEngine',
    'RebalanceEngine',
    'HealthScoreEngine',
]
