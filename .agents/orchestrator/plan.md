# Project Plan — Factrix Extensions

## Objectives
1. R1: Alpha & Beta Performance Attribution engine (`AlphaBetaEngine`) and visualization decomposing returns into market (Beta) vs manager (Alpha) components.
2. R2: Enhanced Risk Factor Exposure dashboard with plain-language risk profiles suitable for retail investors.
3. R3: Integration into `app.py` (`load_and_analyze_data`) and Streamlit UI with dark-mode styling.
4. Quality & Verification: Update `run_debug.py` to pass without exceptions, ensure UI runs error-free, static analysis clean, tests pass.

## Milestones
- **M0: Codebase Exploration & Architecture Design**
  - Dispatch Explorer to analyze existing repository structure, `app.py`, `run_debug.py`, data models, factor engines, and test harness.
  - Create `PROJECT.md` specifying interface contracts, code layout, and milestone details.
- **M1: R1 Alpha & Beta Performance Attribution Engine (`AlphaBetaEngine`)**
  - Dispatch Explorer -> Worker -> Reviewer -> Challenger -> Auditor.
  - Deliver `AlphaBetaEngine` module, attribution logic, visualization components.
- **M2: R2 Enhanced Risk Factor Exposure Dashboard**
  - Dispatch Explorer -> Worker -> Reviewer -> Challenger -> Auditor.
  - Deliver retail investor plain-language risk profiling & dashboard visual components.
- **M3: R3 Integration & E2E Verification**
  - Dispatch Worker to integrate `AlphaBetaEngine` and Risk Exposure components into `app.py` and `run_debug.py`.
  - Dispatch Reviewer, Challenger, and Forensic Auditor for full integration validation.
