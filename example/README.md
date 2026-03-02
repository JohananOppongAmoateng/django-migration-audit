# django-migration-audit — Example Project

This project demonstrates the real-world problems that `django-migration-audit` detects,
using a blog-style Django application.  Each scenario puts the database into a **broken
state** so you can run `audit_migrations` yourself and see the violation appear as it would
in a production incident.

## App structure

```
core/
├── models.py
└── migrations/
    ├── 0001_initial.py          creates Author + Post
    ├── 0002_add_tags.py         adds Tag + PostTag join table
    └── 0003_post_view_count.py  adds Post.view_count
```

---

## Choosing a database backend

Edit `example/settings.py` to switch between backends.  Only one `DATABASES` block should
be active at a time.

### SQLite (default — zero setup)

```bash
python manage.py migrate
python manage.py audit_migrations   # should show "No violations found"
```

### MySQL

```bash
pip install mysqlclient
mysql -u root -e "CREATE DATABASE migration_audit_demo CHARACTER SET utf8mb4;"
```

Comment out the SQLite block in `settings.py` and uncomment the MySQL block.

```bash
python manage.py migrate
```

### PostgreSQL

```bash
pip install psycopg2-binary
createdb migration_audit_demo
```

Comment out the SQLite block in `settings.py` and uncomment the PostgreSQL block.

```bash
python manage.py migrate
```

---

## Running demo scenarios

### The workflow

Omit the scenario name to set up (or tear down) **all problems at once**:

```bash
# Set up all scenarios in one go
python manage.py audit_demo setup

# Discover all the problems yourself
python manage.py audit_migrations

# Restore the database to a clean state
python manage.py audit_demo teardown

# Confirm the fix
python manage.py audit_migrations   # clean again
```

Or target a single scenario:

```bash
# 1. See all available scenarios
python manage.py audit_demo list

# 2. Set up one scenario (puts the database into a broken state)
python manage.py audit_demo setup <scenario>

# 3. Discover the problem yourself
python manage.py audit_migrations

# 4. Restore the database to a clean state
python manage.py audit_demo teardown <scenario>

# 5. Confirm the fix
python manage.py audit_migrations   # clean again
```

---

### Scenario 1 — `drift_add`: Schema Drift, Unexpected Column

**The problem:**  A column is added directly to the database with raw SQL, bypassing
Django's migration system entirely.

```bash
python manage.py audit_demo setup drift_add
```

Now run the audit:

```bash
python manage.py audit_migrations
```

Expected violation:

```
[WARNING] No Unexpected Columns: Unexpected column 'core_post.notes'
(type: text) exists in database but not in migrations
```

Django's own `showmigrations` command shows everything as applied — the problem is invisible
without cross-referencing the live schema.

**Fix:**

```bash
python manage.py audit_demo teardown drift_add
```

---

### Scenario 2 — `drift_remove`: Schema Drift, Missing Column

**The problem:**  A column is dropped from the database with raw SQL.  Migrations say it
must exist, but it is gone.

> **SQLite note:** Requires SQLite 3.35+.  Use MySQL or PostgreSQL for older SQLite.

```bash
python manage.py audit_demo setup drift_remove
```

Run the audit:

```bash
python manage.py audit_migrations
```

Expected violation:

```
[ERROR] All Expected Columns Exist: Expected column 'core_post.published_at'
does not exist in the actual database
```

This is the kind of error that causes `column "published_at" does not exist` crashes at
runtime — after deployment, not during CI.

**Fix:**

```bash
python manage.py audit_demo teardown drift_remove
```

---

### Scenario 3 — `missing_file`: Missing Migration File

**The problem:**  The `django_migrations` table records a migration as applied, but no
corresponding file exists on disk.

```bash
python manage.py audit_demo setup missing_file
```

Run the audit:

```bash
python manage.py audit_migrations
```

Expected violation:

```
[ERROR] No Missing Migration Files: Migration core.0099_nonexistent_migration
is recorded as applied but file is missing
```

`showmigrations` only shows files present on disk — a phantom record is completely invisible
to Django's own tooling.

**Fix:**

```bash
python manage.py audit_demo teardown missing_file
```

---

### Scenario 4 — `fake_migration`: Fake-Applied Migration

**The problem:**  A developer used `migrate --fake` to mark migration 0003 as applied
without running the SQL.  The `view_count` column is absent from the actual schema even
though Django's records say it was added.

```bash
python manage.py audit_demo setup fake_migration
```

Run the audit:

```bash
python manage.py audit_migrations
```

Expected violation:

```
[ERROR] All Expected Columns Exist: Expected column 'core_post.view_count'
does not exist in the actual database
```

This is the exact class of bug that produces `column "view_count" does not exist` errors in
production — after the code that references the column has already been deployed.

**Fix:**

```bash
python manage.py audit_demo teardown fake_migration
```

---

## Database-specific behaviours

| Feature | SQLite | MySQL | PostgreSQL |
|---|---|---|---|
| `DROP COLUMN` | 3.35+ only | Yes | Yes |
| Transactional DDL | No | No | **Yes** — failed migrations roll back |
| Boolean storage | `0` / `1` | `TINYINT(1)` | `BOOLEAN` |
| FK enforcement | Off by default | Depends on engine | Always enforced |
| Type strictness | Loose (affinity) | Strict | Strict |

### SQLite

Limited `ALTER TABLE` support makes schema drift hard to reverse manually.  You cannot drop
columns (before 3.35) or rename columns (before 3.25), which means accidental manual changes
can be difficult to undo — making automatic detection especially valuable.

The `drift_remove` scenario requires SQLite 3.35+ because it drops a column.  All other
scenarios work on any SQLite version.

### MySQL

MySQL stores booleans as `TINYINT(1)`, applies character-set constraints, and locks tables
during some `ALTER TABLE` operations.  Schema drift here can silently affect both correctness
and query performance.

### PostgreSQL

PostgreSQL is the most standards-compliant option.  DDL statements are transactional, which
means a failed migration rolls back atomically — reducing (but not eliminating) the risk of
partial schema states.  The audit tool relies on Django's introspection API, which works
identically across all three backends.
