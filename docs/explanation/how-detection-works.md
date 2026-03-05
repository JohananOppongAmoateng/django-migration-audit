# How Detection Works

A common question is: **"How does the tool know if a migration file was edited?"**

## The short answer

Django only records *that* a migration ran — not *what was in it*. There is no hash or
checksum in the `django_migrations` table. The tool detects modifications **indirectly**
by comparing what the migrations *say should exist* against what *actually exists*.

## The mechanism

1. **Read migration files on disk** — the operations currently defined for every applied migration.
2. **Replay those operations** — execute them in dependency order to build an *expected schema*: the tables, columns, indexes, and constraints that *should* exist if those exact files were applied unchanged.
3. **Introspect the live database** — read the actual schema directly from the database.
4. **Compare** — any mismatch between expected and actual is a violation.

```
Migration files on disk
        │
        │  replay operations in dependency order
        ▼
  Expected schema  ──── Comparison B ────  Actual database schema
                                                (ground truth)
```

## Why this catches more than just edited files

Because the comparison is schema-level rather than file-level, it catches *all* forms of
drift, regardless of cause:

| Root cause | Schema effect | Detected? |
|---|---|---|
| Migration file edited after apply | Expected ≠ actual | ✅ |
| `--fake` apply (schema never ran) | Expected columns missing from DB | ✅ |
| Manual `ALTER TABLE` | Unexpected column / changed type | ✅ |
| Migration file deleted | Missing file detected in Comparison A | ✅ |
| Database restored from old backup | Tables / columns missing | ✅ |
| Django version upgrade (e.g. serial → identity in 4.1) | Type mismatch | ✅ |

## What the `django_migrations` table is used for

The `django_migrations` table is only used for **Comparison A** (trust verification):

- Is every migration recorded as applied still present as a file on disk?
- Are squash migrations properly configured?

It is **not** used to verify schema correctness — that is entirely Comparison B's job.

## A note on false positives

Certain things exist in the database that are never expressed via migration operations:

- Unique constraints created implicitly by `unique=True` field options
- Indexes created implicitly for `ForeignKey` columns
- Anything created outside Django's migration system

The `No Unexpected Indexes` and `No Unexpected Constraints` invariants report these as
`WARNING` (not `ERROR`) so you can review rather than treat them as definitive failures.
The other invariants (`All Expected Tables Exist`, `All Expected Columns Exist`, etc.)
only report things that *should* be there but *aren't* — those are always `ERROR`.
