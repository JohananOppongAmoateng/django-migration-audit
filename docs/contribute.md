# Contributing

Contributions are welcome! This page covers the development setup, running tests, and
code quality tools.

## Setup

```bash
git clone https://github.com/JohananOppongAmoateng/django-migration-audit.git
cd django-migration-audit

# Install uv (if not already installed)
# Linux/macOS:
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Create venv and install all dev dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

## Running tests

```bash
# All tests (SQLite, the default)
uv run pytest

# With coverage report
uv run pytest --cov=django_migration_audit --cov-report=html

# A specific test file
uv run pytest src/django_migration_audit/tests/unit/test_loader.py
```

### Test against other databases

Set environment variables to point at a running Postgres or MySQL instance:

```bash
# PostgreSQL
DB_BACKEND=postgresql DB_NAME=django_migration_audit \
DB_USER=postgres DB_PASSWORD=postgres \
uv run pytest

# MySQL / MariaDB
DB_BACKEND=mysql DB_NAME=django_migration_audit \
DB_USER=root DB_PASSWORD='' \
uv run pytest
```

Or use tox to run the full matrix:

```bash
uv run tox -e py312-django52-postgres
```

## Code quality

```bash
# Format
uv run ruff format

# Lint
uv run ruff check

# Lint + auto-fix
uv run ruff check --fix
```

Pre-commit also runs these automatically on every `git commit`.

## Building the docs

```bash
uv run mkdocs serve        # live-reload preview at http://127.0.0.1:8000
uv run mkdocs build        # one-off build into site/
```

## Submitting a pull request

1. Fork the repository and create a feature branch.
2. Make your changes — add tests for any new behaviour.
3. Run the test suite and linting.
4. Open a pull request against `main` with a clear description.
