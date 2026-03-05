# audit_migrations

Management command that audits your Django project's migration consistency.

```
python manage.py audit_migrations [--database ALIAS] [--comparison {a,b,all}] [--skip-invariants NAME ...]
```

---

## What it checks

The command runs two independent comparisons:

**Comparison A — Trust verification** (`--comparison a`)

Checks that the migration files on disk match what the `django_migrations` table says was applied.

| Invariant | What it catches |
|---|---|
| `NoMissingMigrationFiles` | A migration is recorded as applied but its `.py` file is gone from disk |
| `SquashMigrationsProperlyReplaced` | A squash migration is applied but its replaced originals are still marked applied |

**Comparison B — Reality check** (`--comparison b`)

Replays all applied migration files to build an *expected* schema, then compares it against the *actual* live database.

| Invariant | What it catches |
|---|---|
| `AllExpectedTablesExist` | A table that migrations say should exist is missing from the DB |
| `NoUnexpectedTables` | A table exists in the DB that no migration accounts for |
| `AllExpectedColumnsExist` | A column is missing — e.g. a migration was `--fake`d |
| `NoUnexpectedColumns` | A column was added directly via raw SQL |
| `ColumnNullabilityMatches` | A column's `NOT NULL` constraint differs from what the migration defined |

---

## Options

### `--database ALIAS`

The database connection to audit. Defaults to `default`.

```bash
python manage.py audit_migrations --database secondary
```

### `--comparison {a,b,all}`

Which comparison to run. Defaults to `all`.

```bash
# Trust verification only
python manage.py audit_migrations --comparison a

# Reality check only
python manage.py audit_migrations --comparison b
```

### `--skip-invariants NAME [NAME ...]`

Skip one or more invariants by name for this run. Names are case-sensitive and match the class names listed above.

```bash
python manage.py audit_migrations --skip-invariants NoUnexpectedTables ColumnNullabilityMatches
```

This is merged with `MIGRATION_AUDIT["SKIP_INVARIANTS"]` from your Django settings. See [Suppress Invariants](../../../../how-to-guides/suppress-invariants.md) for persistent suppression.

---

## Exit behaviour

The command exits with status **0** when no violations are found, and prints a green success message.

When violations are found it prints each one to stdout (errors in red, warnings in yellow) with a summary count, but **does not exit non-zero by default**. To treat violations as a CI failure, pipe through a grep or wrap the command — see [Run in CI](../../../../how-to-guides/run-in-ci.md).
