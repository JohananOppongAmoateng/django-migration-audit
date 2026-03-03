# Architecture

## The three inputs

```
(1) django_migrations table     (2) Migration files on disk     (3) Live database
  "what Django recorded"          "what should happen"            "what actually exists"
```

### 1. Migration history (`django_migrations` table)

- Which migrations are recorded as applied, and in what order
- No schema details — just app labels and migration names
- Can be wrong (fake applies, manual insertions, deleted rows)

### 2. Migration code (files on disk)

- The Python operations that define schema changes
- Can be wrong (edited after apply, deleted, rewritten)
- The tool reads these to construct the *expected* schema

### 3. Live database schema

- Tables, columns, indexes, and constraints that currently exist
- Ground truth — the reality everything else must be compared against
- Read via Django's `connection.introspection` API

## The two comparisons

```
(1) Migration history
        │
        │  Comparison A: Trust Verification
        │  "Can we trust the migration history?"
        ▼
(2) Migration code ──── produces ────► Expected schema
                                              │
                                              │  Comparison B: Reality Check
                                              │  "Does the DB match the migrations?"
                                              ▼
                                       (3) Live database schema
```

### Comparison A — Trust Verification

Checks that the migration history and migration files are consistent with each other.

**Invariants:**

- `No Missing Migration Files` — every applied migration still has a file on disk
- `Squash Migrations Properly Replaced` — squash migrations correctly replace originals

**Answers:** *"Can we trust the migration history at all?"*

### Comparison B — Reality Check

Replays all applied migration files to build an expected schema, then compares it against
the live database.

**Invariants:**

- `All Expected Tables Exist` / `No Unexpected Tables`
- `All Expected Columns Exist` / `No Unexpected Columns`
- `Column Nullability Matches`
- `All Expected Indexes Exist` / `No Unexpected Indexes`
- `All Expected Constraints Exist` / `No Unexpected Constraints`

**Answers:** *"Does the actual database match what the migrations say it should be?"*

## Canonical schema representation

Both the extractor (from migrations) and the introspection module (from the live DB)
produce the same data structures, enabling direct comparison:

- `ColumnState` — name, type, nullability, default
- `IndexState` — name, columns
- `ConstraintState` — name, type (`unique` / `check`), columns
- `TableState` — name + dicts of the above
- `SchemaState` — dict of `TableState`

The type system normalises database-specific type names (`AutoField`, `CharField`, etc.)
to canonical strings (`integer`, `varchar`, etc.) so comparisons work across SQLite,
PostgreSQL, and MySQL without backend-specific logic in the invariants.
