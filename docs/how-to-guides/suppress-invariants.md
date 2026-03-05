# Suppress Invariants

By default every invariant runs. If your project has known drift you accept (legacy tables,
implicit unique constraints created outside migrations, etc.) you can suppress specific
invariants by name so they don't clutter the output.

Invariant names are **case-sensitive** and match the `name` property on each invariant class.

## Via the CLI (one-off runs)

```bash
# Skip a single invariant
python manage.py audit_migrations --skip-invariants "No Unexpected Tables"

# Skip multiple invariants
python manage.py audit_migrations \
    --skip-invariants "No Unexpected Tables" "Column Nullability Matches"
```

## Via Django settings (persistent baseline)

```python
# settings.py
MIGRATION_AUDIT = {
    "SKIP_INVARIANTS": [
        "No Unexpected Tables",
        "Column Nullability Matches",
    ],
}
```

CLI `--skip-invariants` and `SKIP_INVARIANTS` from settings are **merged** — both apply at
the same time.

## Available invariant names

### Comparison A — Trust Verification

| Name | What it checks |
|---|---|
| `No Missing Migration Files` | Every applied migration still has a file on disk |
| `Squash Migrations Properly Replaced` | Squashed migrations correctly replace their originals |

### Comparison B — Reality Check

| Name | What it checks |
|---|---|
| `All Expected Tables Exist` | Every table from migrations exists in the DB |
| `No Unexpected Tables` | No tables in the DB that aren't in migrations |
| `All Expected Columns Exist` | Every column from migrations exists with the correct type |
| `No Unexpected Columns` | No columns in the DB that aren't in migrations |
| `Column Nullability Matches` | Column NULL/NOT NULL matches between migrations and DB |
| `All Expected Indexes Exist` | Every index from `AddIndex` exists in the DB |
| `No Unexpected Indexes` | No indexes in the DB not defined via `AddIndex` |
| `All Expected Constraints Exist` | Every constraint from `AddConstraint` exists in the DB |
| `No Unexpected Constraints` | No constraints in the DB not defined via `AddConstraint` |

!!! note
    `No Unexpected Indexes` and `No Unexpected Constraints` are `WARNING`-level because
    Django silently creates implicit indexes (e.g. for ForeignKey columns) and unique
    constraints (e.g. for `unique=True` fields) that are never expressed via
    `AddIndex`/`AddConstraint`. These will appear as "unexpected" even though they are
    normal. Review violations rather than treating them all as failures.
