# Run in CI

Running `audit_migrations` in CI catches problems before they reach production — edited
migrations, schema drift introduced during development, missing files after a branch
merge.

## GitHub Actions example

```yaml
- name: Run migration audit
  run: python manage.py audit_migrations
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

The command exits with a non-zero status code when any `ERROR`-level violations are
found, which causes the CI step to fail.

## Run only specific comparisons

```bash
# Only trust verification (fast, no DB connection needed beyond django_migrations)
python manage.py audit_migrations --comparison=a

# Only reality check (requires a real DB)
python manage.py audit_migrations --comparison=b
```

## Skip invariants that don't apply to your CI database

CI databases are typically created fresh, so invariants that detect legacy drift (like
`No Unexpected Tables`) may not be useful there:

```bash
python manage.py audit_migrations \
    --skip-invariants "No Unexpected Tables" "No Unexpected Columns"
```

Or set them in a CI-specific settings file:

```python
# settings_ci.py
MIGRATION_AUDIT = {
    "SKIP_INVARIANTS": ["No Unexpected Tables", "No Unexpected Columns"],
}
```

## Audit a specific database

```bash
python manage.py audit_migrations --database=replica
```
