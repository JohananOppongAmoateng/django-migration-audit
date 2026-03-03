# Auto-Run After Deployments

By default `audit_migrations` is a command you run manually or in CI. You can also have
it run **automatically** at the end of every `manage.py migrate` call — no extra step
required.

## Enable AUTO_RUN

```python
# settings.py
MIGRATION_AUDIT = {
    "AUTO_RUN": True,
}
```

When enabled, the tool hooks into Django's `post_migrate` signal. After all migrations
finish, the audit runs and any violations are emitted as `WARNING` log records via the
`django_migration_audit` logger.

## Example log output

```
WARNING django_migration_audit Migration audit found 1 violation(s) (1 error(s), 0 warning(s)).
WARNING django_migration_audit   [ERROR] All Expected Tables Exist: Expected table 'myapp_profile' does not exist in database
```

A clean run produces an `INFO` record (only visible when verbosity ≥ 1):

```
INFO django_migration_audit Migration audit passed — no violations found.
```

## Combining with SKIP_INVARIANTS

```python
MIGRATION_AUDIT = {
    "AUTO_RUN": True,
    "SKIP_INVARIANTS": ["No Unexpected Tables"],
}
```

## Capturing violations in Sentry / logging

Because violations are standard Python log records, they flow into whatever logging
backend your project already uses:

```python
# settings.py
LOGGING = {
    "version": 1,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "django_migration_audit": {
            "handlers": ["console"],
            "level": "WARNING",
        },
    },
}
```

## Why this matters for production

Running the audit after every deployment catches drift that CI cannot see. CI databases
are created fresh — they never accumulate the manual changes, emergency hotfixes, or
Django version upgrade effects that a long-lived production database does. Catching a
mismatch immediately after `migrate` runs is the highest-signal moment to surface it.
