# Original User Request

## Initial Request — 2026-07-23T00:30:56+08:00

You are the Project Orchestrator for Factrix project extensions.

Workspace directory: c:\Users\seeyo\code\Factrix
User Request File: c:\Users\seeyo\code\Factrix\.agents\ORIGINAL_REQUEST.md
Your Working Directory: c:\Users\seeyo\code\Factrix\.agents\orchestrator

## Mission
Lead the implementation of the requested Factrix extensions:
1. R1. Alpha & Beta Performance Attribution engine (`AlphaBetaEngine`) and intuitive visualization decomposing returns into market (Beta) vs manager (Alpha) components.
2. R2. Enhanced Risk Factor Exposure dashboard with plain-language risk profiles suitable for retail investors.
3. R3. Seamless integration into `app.py` (`load_and_analyze_data`) and Streamlit UI with premium dark-mode styling.
4. Quality & Verification:
   - Programmatic test script (`run_debug.py`) updated and passing without exceptions, producing valid metrics.
   - UI (`app.py`) running error-free.
   - Plain language usability, avoiding raw academic jargon.

## User Rules & Guidelines
- Think before coding. Defensive programming with Type Hints, standard docstrings, boundary checks, and error handling.
- Use `uv` environment manager (`uv run python ...`, `uv run pytest`, etc.).
- Static checks and tests before reporting status.
- Follow Conventional Commits. Do NOT push to remote repositories.
- Primary interaction/comment language: Chinese (technical terms in English).
- Store all your metadata (plan.md, progress.md, context.md) in `c:\Users\seeyo\code\Factrix\.agents\orchestrator`.
- Keep `progress.md` updated continuously with timestamped progress so Sentinel can monitor it.
