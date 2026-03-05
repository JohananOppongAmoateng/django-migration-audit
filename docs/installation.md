# Installation

## Requirements

| Dependency | Version |
|---|---|
| Python | 3.11+ |
| Django | 4.2, 5.2, 6.0 |

All three major databases are supported and tested in CI:

| Database | Notes |
|---|---|
| PostgreSQL | Full support — recommended for production |
| MySQL / MariaDB | Full support |
| SQLite | Full support — used in development and tests |

## Install the package

```bash
pip install django-migration-audit
```

## Add to INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "django_migration_audit",
]
```

That's it. You can now run:

```bash
python manage.py audit_migrations
```

## Optional: enable auto-run after migrations

To have the audit run automatically every time `manage.py migrate` completes, add `AUTO_RUN` to your settings:

```python
# settings.py
MIGRATION_AUDIT = {
    "AUTO_RUN": True,
}
```

See [Auto-Run After Deployments](how-to-guides/auto-run-after-deploy.md) for details.
