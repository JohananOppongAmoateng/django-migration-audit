# Django Migration Audit

**A forensic Django tool that verifies whether a live database schema is historically consistent with its applied migrations.**

Django assumes: *if a migration is recorded as applied, the schema must match.* Reality: that assumption can be false.

`django-migration-audit` verifies both:

- **Trust** — are the migration files on disk consistent with what was applied?
- **Reality** — does the actual database schema match what the migrations say it should be?

---

## Get started

- New here? Start with **[Installation](installation.md)**.
- Want to see it in action first? Try **[Running the Example App](tutorials/run-the-example.md)**.
- Already installed? Jump to the **[management command reference](reference/django_migration_audit/management/commands/audit_migrations.md)**.

## What it detects

| Scenario | Detected? |
|---|---|
| Migration file edited after being applied | ✅ |
| Migration marked applied with `--fake` | ✅ |
| Manual `ALTER TABLE` / column added by hand | ✅ |
| Migration file deleted after being applied | ✅ |
| Schema drift from a Django version upgrade | ✅ |
| Database restored from an older backup | ✅ |
| Squash migration not properly replacing originals | ✅ |

## How it works (short version)

The tool replays your migration files to build an *expected* schema, then compares it to the *actual* live database. Any mismatch — regardless of cause — is reported as a violation.

For the full explanation see **[How Detection Works](explanation/how-detection-works.md)**.
