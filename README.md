# django-migration-audit

**A forensic Django tool that verifies whether a live database schema is historically consistent with its applied migrations.**

[![License](https://img.shields.io/badge/license-BSD--3--Clause-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/django-4.2+-green.svg)](https://www.djangoproject.com/)
[![Latest on Django Packages](https://img.shields.io/badge/PyPI--django--migration--audit--tags--8c3c26.svg)](https://djangopackages.org/packages/p/django-migration-audit/)


> **⚠️ Work in Progress**
>
> This project is under active development and not yet ready for production use. The core functionality is being implemented and tested, but the API may change and some features are still being refined. Use at your own risk and expect breaking changes.


## Why This Tool Exists

Django assumes: **if a migration is recorded as applied, the schema must match.**

Reality: **That assumption can be false.**

Common scenarios where this breaks:
- Modified migration files after application
- Manual database schema changes
- Fake-applied migrations (`--fake`)
- Squashed migrations with mismatches
- Database restores from backups
- Schema drift over time

This tool verifies both assumptions:
- **Reachability**: Can we trust the migration history?
- **Consistency**: Does the actual schema match what the history claims?

## Installation

```bash
pip install django-migration-audit
```

Or install from source:

```bash
git clone https://github.com/yourusername/django-migration-audit.git
cd django-migration-audit
pip install -e .
```

Add to your Django project's `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ... other apps
    'django_migration_audit',
]
```

## Quick Start

### Basic Usage

```bash
# Run full audit (both comparisons)
python manage.py audit_migrations

# Audit specific database
python manage.py audit_migrations --database=replica

# Run only trust verification (Comparison A)
python manage.py audit_migrations --comparison=a

# Run only reality check (Comparison B)
python manage.py audit_migrations --comparison=b
```

### Example Output (Clean State)

```
=== Django Migration Audit ===
Database: default

Loading migration history and code...
  Applied migrations: 15
  Migration files on disk: 15
  Missing files: 0
  Squashed replacements: 0

🔍 Comparison A: Trust Verification
   (Migration history ↔ Migration code)

  Checking: No Missing Migration Files...
    ✅ Pass
  Checking: Squash Migrations Properly Replaced...
    ✅ Pass

🔍 Comparison B: Reality Check
   (Expected schema ↔ Actual schema)

  Building expected schema from migrations...
  Introspecting actual database schema...
    Expected tables: 8
    Actual tables: 8

  Checking: All Expected Tables Exist...
    ✅ Pass
  Checking: No Unexpected Tables...
    ✅ Pass
  Checking: All Expected Columns Exist...
    ✅ Pass

=== Summary ===
✅ No violations found! Migration state is consistent.
```

### Example Output (Issues Detected)

```
=== Django Migration Audit ===
Database: default

🔍 Comparison A: Trust Verification
  Checking: No Missing Migration Files...
    ❌ 1 violation(s)

🔍 Comparison B: Reality Check
  Checking: All Expected Tables Exist...
    ❌ 2 violation(s)
  Checking: No Unexpected Tables...
    ❌ 1 violation(s)

=== Summary ===
❌ Found 4 violation(s):
   Errors: 3
   Warnings: 1

  [ERROR] No Missing Migration Files: Migration myapp.0003_add_email is recorded as applied but file is missing
  [ERROR] All Expected Tables Exist: Expected table 'myapp_profile' does not exist in database
  [ERROR] All Expected Columns Exist: Expected column 'myapp_user.email' does not exist
  [WARNING] No Unexpected Tables: Unexpected table 'legacy_data' exists in database
```

## Suppressing Invariants

By default all invariants run. You can suppress specific ones via a CLI flag, Django settings, or programmatically — they are silently skipped and do not appear in output.

### CLI flag (one-off runs)

```bash
# Skip a single invariant by name (case-sensitive)
python manage.py audit_migrations --skip-invariants "No Unexpected Tables"

# Skip multiple
python manage.py audit_migrations --skip-invariants "No Unexpected Tables" "Column Nullability Matches"
```

### Django settings (persistent per-project baseline)

```python
# settings.py
MIGRATION_AUDIT = {
    "SKIP_INVARIANTS": [
        "No Unexpected Tables",
        "Column Nullability Matches",
    ],
}
```

CLI `--skip-invariants` merges with `SKIP_INVARIANTS` from settings — both apply.

## Architecture Overview

### The Three Inputs

1. **Migration History** (`django_migrations` table)
   - What Django thinks happened
   - Which migrations are recorded as applied, and in what order
   - No schema details—just names and app labels

2. **Migration Code** (migration files on disk: `migrations/*.py`)
   - What the project currently says should happen
   - The operations that were supposed to run
   - Detects: edited migrations, squashed migrations, rewritten history

3. **Live Database Schema** (database introspection)
   - What actually exists right now
   - Ground truth: tables, columns, indexes, constraints
   - The reality that everything else must match

### The Two Comparisons

```
(1) Migration history
        │
        │  🔍 Comparison A: Trust Verification
        ▼
(2) Migration code
        │
        │  produces expected schema
        ▼
    Expected schema
        │
        │  🔍 Comparison B: Reality Check
        ▼
(3) Live database schema
```

#### 🔍 Comparison A: Trust Verification
**Migration history ↔ Migration code**

**Detects:**
- Modified migration files
- Missing migration files
- Fake-applied migrations
- Squash mismatches

**Answers:** *"Can we trust the migration history at all?"*

#### 🔍 Comparison B: Reality Check
**Expected schema ↔ Actual schema**

**Detects:**
- Schema drift
- Manual database edits
- Broken legacy assumptions
- Missing/extra tables
- Column type mismatches


## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/django-migration-audit.git
cd django-migration-audit

# Install uv (if not already installed)
# Linux/Mac:
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Setup development environment
uv venv
uv sync
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=django_migration_audit --cov-report=html

# Run specific test file
uv run pytest src/django_migration_audit/tests/unit/test_loader.py
```

### Code Quality

```bash
# Format code
uv run ruff format

# Lint code
uv run ruff check

# Fix linting issues
uv run ruff check --fix
```

### Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to automatically check code quality before commits.

To set up the hooks:

```bash
# Install the hooks
uv run pre-commit install
```

Now, `pre-commit` will run automatically on `git commit`. You can also run it manually against all files:

```bash
uv run pre-commit run --all-files
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

BSD-3-Clause - see [LICENSE](LICENSE) file for details.

## Credits

Created by Johanan Oppong Amoateng

## Support

- **Issues**: [GitHub Issues](https://github.com/JohananOppongAmoateng/django-migration-audit/issues)
- **Discussions**: [GitHub Discussions](https://github.com/JohananOppongAmoateng/django-migration-audit/discussions)
