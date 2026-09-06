# Repository Guidelines

## Project Structure & Module Organization

- `app/main.py` defines the FastAPI application, lifecycle startup/shutdown, and root and database health endpoints.
- `app/core/` contains configuration (`config.py`) and SQLAlchemy infrastructure (`database.py`).
- `app/model/` contains SQLAlchemy ORM models, such as `app/model/weather.py`.
- `data/` stores project data files; do not treat it as application source.
- `pyproject.toml` and `uv.lock` define dependencies and the pinned environment. The project targets Python 3.14.

## Build, Test, and Development Commands

- `uv sync`: install dependencies from the lockfile.
- `uv run fastapi dev`: start the development API with reload.
- `uv run uvicorn app.main:app --reload`: equivalent Uvicorn command.
- `uv run pytest`: run tests when a test suite is present.

Startup creates missing database tables and disposes the connection pool on shutdown. A reachable PostgreSQL instance configured through `.env` is required for database health checks.

## External Service Constraints

- The snowflake ID service (`app/service/snowflake.py`, URL configured via `snowflake_id_url`) accepts at most **512 IDs per request**: `?n=512` succeeds, `n=513` returns HTTP 400. When more IDs are needed, request them in batches of 512 or fewer — the limit is defined as `MAX_CODES_PER_REQUEST` in `app/service/snowflake.py`, and `_backfill_missing_map_codes` (`app/service/station.py`) and `_backfill_missing_stat_codes` (`app/service/metro_stat.py`) implement the batching pattern.

## Coding Style & Naming Conventions

- Use Python type hints for function signatures and public data models.
- Follow PEP 8; default to 4-space indentation and snake_case for modules, functions, and variables.
- Use PascalCase for classes and UPPERCASE or descriptive snake_case for settings where the existing code does so.
- Keep API and database logic separated: routes in `app/main.py` (or new route modules), configuration in `app/core`, models in `app/model`.
- Keep existing Chinese docstrings and comments when editing nearby code; write new explanatory text consistently.

## Testing Guidelines

No test suite is currently configured. Add tests under `tests/` using `tests/test_*.py`, with focused fixtures for FastAPI dependency overrides and PostgreSQL-backed behavior. Prefer tests that can run without mutating real production data. Update or add coverage for database models and route behavior when changing them.

## Commit & Pull Request Guidelines

Recent history uses short, imperative messages, often with Conventional Commit prefixes such as `feat:天地图` or `feat: add vscode config`. Continue with concise conventional prefixes (`feat:`, `fix:`, `docs:`, `chore:`) and a specific subject.

Pull requests should describe the motivation, behavioral changes, database/model impact, and verification steps. Include linked issues when applicable, and add screenshots or request examples for API changes. Do not commit `.env`, virtual environments, build output, or IDE-specific files.

## Security & Configuration Tips

Copy `.env.example` to `.env` and adjust database credentials locally. Never expose real credentials in source, logs, or PR descriptions. Use `pydantic-settings` fields in `app/core/config.py` rather than reading environment variables ad hoc.
