# django-migration-audit

**A forensic Django tool that verifies whether a live database schema is historically consistent with its applied migrations.**

[![License](https://img.shields.io/badge/license-BSD--3--Clause-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/django-4.2+-green.svg)](https://www.djangoproject.com/)
[![Latest on Django Packages](https://img.shields.io/badge/PyPI--django--migration--audit--tags--8c3c26.svg)](https://djangopackages.org/packages/p/django-migration-audit/)

> **⚠️ Work in Progress**
>
> This project is under active development. The API may change and some features are still being refined.

Django assumes: **if a migration is recorded as applied, the schema must match.**

Reality: **that assumption can be false.** Edited migration files, `--fake` applies,
manual `ALTER TABLE`, database restores, Django version upgrades — all of these can
silently break that assumption.

`django-migration-audit` verifies both:

- **Trust** — are the migration files consistent with what was applied?
- **Reality** — does the actual database schema match what the migrations say it should be?

## Install

```bash
pip install django-migration-audit
```

Add `"django_migration_audit"` to `INSTALLED_APPS`, then:

```bash
python manage.py audit_migrations
```

## Documentation

**[django-migration-audit.readthedocs.io →](https://django-migration-audit.readthedocs.io/)**

- [Installation](https://django-migration-audit.readthedocs.io/installation/)
- [How detection works](https://django-migration-audit.readthedocs.io/explanation/how-detection-works/)
- [Auto-run after deployments](https://django-migration-audit.readthedocs.io/how-to-guides/auto-run-after-deploy/)
- [Suppress invariants](https://django-migration-audit.readthedocs.io/how-to-guides/suppress-invariants/)

## License

BSD-3-Clause — see [LICENSE](LICENSE).
