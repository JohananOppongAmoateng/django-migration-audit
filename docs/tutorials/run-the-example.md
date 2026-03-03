# Running the Example App

The repository ships with a self-contained example app that lets you trigger real schema
violations and watch `audit_migrations` detect them. This is the fastest way to understand
what the tool does.

## Setup

```bash
git clone https://github.com/JohananOppongAmoateng/django-migration-audit.git
cd django-migration-audit

# Install with dev dependencies
uv sync

# Move into the example project
cd example

# Apply all migrations (creates a clean SQLite database)
../venv/bin/python manage.py migrate
```

## List available scenarios

```bash
python manage.py audit_demo list
```

```
Available scenarios:

  drift_add       Column added directly via raw SQL (no migration)
  drift_remove    Column dropped directly via raw SQL
  missing_file    Migration recorded as applied but file is gone from disk
  fake_migration  Migration marked applied via --fake; schema is behind
```

## Run a scenario

Each scenario is a three-step cycle: **setup → audit → teardown**.

### Schema drift: column added by hand

```bash
# 1. Put the DB into a broken state
python manage.py audit_demo setup drift_add

# 2. Run the audit — you should see a violation
python manage.py audit_migrations

# 3. Restore the clean state
python manage.py audit_demo teardown drift_add
```

The audit will report a `No Unexpected Columns` warning for the manually added column.

### Missing migration file

```bash
python manage.py audit_demo setup missing_file
python manage.py audit_migrations
python manage.py audit_demo teardown missing_file
```

Reports a `No Missing Migration Files` error — the migration is recorded as applied but
the file no longer exists on disk.

### Fake-applied migration

```bash
python manage.py audit_demo setup fake_migration
python manage.py audit_migrations
python manage.py audit_demo teardown fake_migration
```

The migration was marked as applied with `--fake` so the schema is behind. Reports
`All Expected Columns Exist` errors for the columns that were never actually created.

### Column removed by hand

```bash
python manage.py audit_demo setup drift_remove
python manage.py audit_migrations
python manage.py audit_demo teardown drift_remove
```

Reports `All Expected Columns Exist` errors for the column that was dropped directly.

## Next steps

- See the [management command reference](../reference/django_migration_audit/management/commands/audit_migrations.md) for all available flags.
- Learn [how the detection works](../explanation/how-detection-works.md) under the hood.
