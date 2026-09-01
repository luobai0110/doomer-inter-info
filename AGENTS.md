# Repository Guidelines

## Project Structure & Module Organization

`inter-info` is a FastAPI service managed with `uv`. Source code lives under `app/`:

- `app/main.py` — FastAPI app entrypoint, route registration, and lifecycle.
- `app/core/` — configuration and infrastructure: `config.py` loads settings from `.env`; `database.py` defines the engine, session factory, `Base`, and `get_db`.
- `app/model/` — SQLAlchemy ORM models, such as `weather.py`.
- `app/service/` — business logic and external integrations, such as `weather.py`.
- `data/` — runtime data.

Configuration examples live in `.env.example`; dependencies and metadata live in `pyproject.toml` with `uv.lock`. No tests or assets directories exist yet.

## Build, Test, and Development Commands

Use `uv` instead of `pip`:

- `uv sync` — install dependencies from `uv.lock`.
- `cp .env.example .env` — create local configuration, then set PostgreSQL values.
- `uv run fastapi dev` — start FastAPI with reload; equivalent to `uv run uvicorn app.main:app --reload`.
- `uv run python app/main.py` — run the app module directly.

No test runner or test suite is configured. When tests are introduced, add `pytest` as a dev dependency and use `uv run pytest`.

## Coding Style & Naming Conventions

- Use Python 3.14, PEP 8, and 4-space indentation.
- Add type hints to public functions and methods.
- Use `snake_case` for modules, functions, and variables; `PascalCase` for classes; `UPPER_SNAKE_CASE` for constants; `snake_case` for routes and table names.
- Match the repository's existing style of Chinese docstrings and comments.
- No formatter or linter is configured yet; keep edits consistent with the surrounding code.

## Testing Guidelines

Tests are not yet configured. When adding them, mirror the package structure under `app/tests/`, name files `test_<module>.py`, and name test functions `test_<behavior>`. Keep each test focused on one behavior.

## Commit & Pull Request Guidelines

Git history uses short, lowercase, imperative subjects such as `init repo` and `add database`. Keep one logical change per commit and regenerate `uv.lock` whenever dependencies change.

For pull requests, describe what changed and why, include test or verification steps, link related issues, and add screenshots for UI or API changes. Never commit `.env` or other secrets.

## Agent-Specific Instructions

Read `README.md` and `.env.example` before touching configuration or infrastructure. Copy `.env.example` to `.env` for local work, but never edit or commit the real `.env`. Run `uv sync` before assuming the environment is ready, use `uv` commands instead of `pip`, and verify the app starts and `/health/db` responds when a database is available.
