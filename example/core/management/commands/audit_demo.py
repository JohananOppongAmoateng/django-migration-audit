"""
audit_demo — interactive scenario runner for django-migration-audit examples.

Each scenario puts the database into a broken state so you can run
audit_migrations yourself and see the violation appear as it would in
a real project.

Usage
-----
  # List all available scenarios
  python manage.py audit_demo list

  # Put the database into a broken state
  python manage.py audit_demo setup <scenario>

  # Discover the problem yourself
  python manage.py audit_migrations

  # Restore the database to a clean state
  python manage.py audit_demo teardown <scenario>

Scenarios
---------
  drift_add       Column added directly via raw SQL (no migration)
  drift_remove    Column dropped directly via raw SQL
  missing_file    Migration recorded as applied but file is gone from disk
  fake_migration  Migration marked applied via --fake; schema is behind
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

# ---------------------------------------------------------------------------
# Scenario registry
# ---------------------------------------------------------------------------

SCENARIOS = {
    "drift_add": {
        "name": "Schema Drift — Unexpected Column",
        "problem": (
            "A 'notes' TEXT column has been added directly to core_post via raw SQL.\n"
            "Django has no record of this column — it doesn't exist in any migration.\n"
            "\n"
            "Real-world causes:\n"
            "  • DBA applied a hotfix directly on the production database\n"
            "  • A data-import script added an extra column as a side-effect\n"
            "  • A developer added a column for debugging and forgot to clean up"
        ),
        "fix_hint": (
            "Create a migration that adds the column (making it official), or\n"
            "drop the column from the database if it is no longer needed."
        ),
        "invariant": "No Unexpected Columns → WARNING",
    },
    "drift_remove": {
        "name": "Schema Drift — Missing Column",
        "problem": (
            "The 'published_at' column has been dropped from core_post via raw SQL.\n"
            "Migration 0001 says the column must exist, but it is gone from the DB.\n"
            "\n"
            "Real-world causes:\n"
            "  • DBA 'cleaned up' a column thought to be unused\n"
            "  • Column dropped from the wrong table during maintenance\n"
            "  • Database restore landed in an older backup state"
        ),
        "fix_hint": (
            "Re-add the column (manually or via a new migration), or restore\n"
            "the database from a backup that includes the column."
        ),
        "invariant": "All Expected Columns Exist → ERROR",
    },
    "missing_file": {
        "name": "Missing Migration File",
        "problem": (
            "The django_migrations table records 'core.0099_nonexistent_migration'\n"
            "as applied, but no such file exists under core/migrations/.\n"
            "\n"
            "Real-world causes:\n"
            "  • Migration file was deleted during a failed squash attempt\n"
            "  • Migrations were applied from a branch that was later abandoned\n"
            "  • History was rewritten after migrations were already applied"
        ),
        "fix_hint": (
            "Restore the missing migration file from version control, or\n"
            "manually remove the phantom record from django_migrations if the\n"
            "migration was never needed."
        ),
        "invariant": "No Missing Migration Files → ERROR",
    },
    "fake_migration": {
        "name": "Fake-Applied Migration",
        "problem": (
            "Migration '0003_post_view_count' is recorded in django_migrations\n"
            "as applied, but the 'view_count' column does not exist in core_post.\n"
            "The migration was recorded with '--fake' — the SQL never ran.\n"
            "\n"
            "Real-world causes:\n"
            "  • Developer used: python manage.py migrate --fake core 0003\n"
            "  • Emergency recovery where the migration could not be reversed\n"
            "  • Cross-environment sync where migration was assumed to be applied"
        ),
        "fix_hint": (
            "Run the migration properly (without --fake) to apply the missing\n"
            "schema changes, or create a new migration that adds the column."
        ),
        "invariant": "All Expected Columns Exist → ERROR",
    },
}

SCENARIO_KEYS = list(SCENARIOS.keys())


# ---------------------------------------------------------------------------
# Management command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = "Set up and tear down demo scenarios for django-migration-audit"

    def add_arguments(self, parser):
        parser.add_argument(
            "action",
            choices=["list", "setup", "teardown"],
            help="'list' shows all scenarios. 'setup'/'teardown' default to all scenarios.",
        )
        parser.add_argument(
            "scenario",
            nargs="?",
            choices=SCENARIO_KEYS,
            metavar=f"{{{','.join(SCENARIO_KEYS)}}}",
            help="Scenario to set up or tear down. Omit to run all scenarios.",
        )

    def handle(self, *args, **options):
        action = options["action"]
        scenario = options.get("scenario")

        if action == "list":
            self._list()
            return

        targets = [scenario] if scenario else SCENARIO_KEYS

        if action == "setup":
            for key in targets:
                self._setup(key)
        elif action == "teardown":
            for key in reversed(targets):
                self._teardown(key)

    # ── list ─────────────────────────────────────────────────────────────────

    def _list(self):
        self.stdout.write("\nAvailable demo scenarios\n" + "─" * 50)
        for key, info in SCENARIOS.items():
            self.stdout.write(f"\n  {self.style.SUCCESS(key)}")
            self.stdout.write(f"    {info['name']}")
            self.stdout.write(f"    Fires: {info['invariant']}")
        self.stdout.write(
            "\n"
            "Usage:\n"
            "  python manage.py audit_demo setup   <scenario>   # break the DB\n"
            "  python manage.py audit_migrations                # find the problem\n"
            "  python manage.py audit_demo teardown <scenario>  # restore clean state\n"
        )

    # ── setup dispatcher ─────────────────────────────────────────────────────

    def _setup(self, scenario):
        info = SCENARIOS[scenario]
        self._header(f"SETUP: {info['name']}")
        self.stdout.write(f"  Database backend : {connection.vendor}\n")

        getattr(self, f"_setup_{scenario}")()

        self._what_happened(info)

    # ── teardown dispatcher ──────────────────────────────────────────────────

    def _teardown(self, scenario):
        info = SCENARIOS[scenario]
        self._header(f"TEARDOWN: {info['name']}")

        getattr(self, f"_teardown_{scenario}")()

        self.stdout.write(self.style.SUCCESS("\n  ✓ Database restored to a clean state."))
        self.stdout.write("  Run 'python manage.py audit_migrations' to confirm.\n")

    # =========================================================================
    # Scenario: drift_add
    # =========================================================================

    def _setup_drift_add(self):
        self._ensure_migrated()

        if self._column_exists("core_post", "notes"):
            self.stdout.write(
                self.style.WARNING(
                    "  'core_post.notes' already exists — scenario already set up.\n"
                    "  Run 'audit_demo teardown drift_add' to reset, then set up again.\n"
                )
            )
            return

        self.stdout.write("  Executing raw SQL (outside of any migration):")
        self.stdout.write("  > ALTER TABLE core_post ADD COLUMN notes TEXT;\n")
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE core_post ADD COLUMN notes TEXT;")
        self.stdout.write("  Column 'notes' added. No migration was created.\n")

    def _teardown_drift_add(self):
        if not self._column_exists("core_post", "notes"):
            self.stdout.write("  'notes' column is not present — nothing to do.")
            return

        vendor = connection.vendor
        if vendor == "sqlite":
            sqlite_ver = self._sqlite_version()
            major, minor = sqlite_ver
            if major > 3 or (major == 3 and minor >= 35):
                with connection.cursor() as cursor:
                    cursor.execute("ALTER TABLE core_post DROP COLUMN notes;")
                self.stdout.write(f"  Dropped 'core_post.notes' (SQLite {major}.{minor})")
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"  SQLite {major}.{minor} does not support DROP COLUMN (requires 3.35+).\n"
                        "  Delete db.sqlite3 and re-run 'migrate' to reset to a clean state."
                    )
                )
        else:
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE core_post DROP COLUMN notes;")
            self.stdout.write("  Dropped 'core_post.notes'")

    # =========================================================================
    # Scenario: drift_remove
    # =========================================================================

    def _setup_drift_remove(self):
        vendor = connection.vendor

        if vendor == "sqlite":
            major, minor = self._sqlite_version()
            if not (major > 3 or (major == 3 and minor >= 35)):
                self.stdout.write(
                    self.style.WARNING(
                        f"  SQLite {major}.{minor} does not support DROP COLUMN (requires 3.35+).\n"
                        "  This scenario requires SQLite 3.35+, MySQL, or PostgreSQL.\n"
                        "  Skipping setup."
                    )
                )
                return

        self._ensure_migrated()

        if not self._column_exists("core_post", "published_at"):
            self.stdout.write(
                self.style.WARNING(
                    "  'core_post.published_at' is already absent — scenario already set up.\n"
                    "  Run 'audit_demo teardown drift_remove' to reset, then set up again.\n"
                )
            )
            return

        self.stdout.write("  Executing raw SQL (outside of any migration):")
        self.stdout.write("  > ALTER TABLE core_post DROP COLUMN published_at;\n")
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE core_post DROP COLUMN published_at;")
        self.stdout.write("  Column 'published_at' dropped. Migration 0001 still expects it.\n")

    def _teardown_drift_remove(self):
        if self._column_exists("core_post", "published_at"):
            self.stdout.write("  'published_at' column is already present — nothing to do.")
            return

        vendor = connection.vendor
        if vendor == "mysql":
            sql = "ALTER TABLE core_post ADD COLUMN published_at DATETIME(6) NULL;"
        else:
            # SQLite and PostgreSQL both accept this form
            sql = "ALTER TABLE core_post ADD COLUMN published_at DATETIME NULL;"

        self.stdout.write(f"  Re-adding column:\n  > {sql}")
        with connection.cursor() as cursor:
            cursor.execute(sql)
        self.stdout.write("  Column 'published_at' restored.")

    # =========================================================================
    # Scenario: missing_file
    # =========================================================================

    _PHANTOM_APP = "core"
    _PHANTOM_NAME = "0099_nonexistent_migration"

    def _setup_missing_file(self):
        self._ensure_migrated()

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM django_migrations WHERE app=%s AND name=%s",
                [self._PHANTOM_APP, self._PHANTOM_NAME],
            )
            if cursor.fetchone()[0] > 0:
                self.stdout.write(
                    self.style.WARNING(
                        "  Phantom record already present — scenario already set up.\n"
                        "  Run 'audit_demo teardown missing_file' to reset, then set up again.\n"
                    )
                )
                return

            cursor.execute(
                "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                [self._PHANTOM_APP, self._PHANTOM_NAME, timezone.now()],
            )

        self.stdout.write(
            f"  Inserted into django_migrations:\n"
            f"    app='{self._PHANTOM_APP}', name='{self._PHANTOM_NAME}'\n"
            f"  No file 'core/migrations/{self._PHANTOM_NAME}.py' exists on disk.\n"
        )

    def _teardown_missing_file(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM django_migrations WHERE app=%s AND name=%s",
                [self._PHANTOM_APP, self._PHANTOM_NAME],
            )
            deleted = cursor.rowcount

        if deleted:
            self.stdout.write(
                f"  Removed phantom record '{self._PHANTOM_APP}.{self._PHANTOM_NAME}'"
            )
        else:
            self.stdout.write("  Phantom record not found — scenario was already clean.")

    # =========================================================================
    # Scenario: fake_migration
    # =========================================================================

    _FAKE_APP = "core"
    _FAKE_NAME = "0003_post_view_count"
    _ROLLBACK_TARGET = "0002_add_tags"

    def _setup_fake_migration(self):
        self._ensure_migrated()

        # 1. Reverse migration 0003 so view_count column is removed from the schema
        self.stdout.write("  Reversing migration 0003 (removes 'view_count' from core_post)...")
        call_command(
            "migrate", self._FAKE_APP, self._ROLLBACK_TARGET, verbosity=1, stdout=self.stdout
        )

        # 2. Insert a fake django_migrations record for 0003
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM django_migrations WHERE app=%s AND name=%s",
                [self._FAKE_APP, self._FAKE_NAME],
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                    [self._FAKE_APP, self._FAKE_NAME, timezone.now()],
                )

        col_present = self._column_exists("core_post", "view_count")
        self.stdout.write(
            f"\n  State after setup:\n"
            f"    django_migrations says '0003' applied : YES\n"
            f"    'core_post.view_count' exists in DB   : "
            f"{'YES (unexpected — check your DB)' if col_present else 'NO  ← the gap'}\n"
        )

    def _teardown_fake_migration(self):
        # Remove the fake record so Django can apply 0003 properly
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM django_migrations WHERE app=%s AND name=%s",
                [self._FAKE_APP, self._FAKE_NAME],
            )
        self.stdout.write("  Removed fake django_migrations record.")

        self.stdout.write("  Re-applying migration 0003 properly...")
        call_command("migrate", verbosity=1, stdout=self.stdout)

    # =========================================================================
    # Helpers
    # =========================================================================

    def _ensure_migrated(self):
        self.stdout.write("  Ensuring all migrations are applied...")
        call_command("migrate", verbosity=0)
        self.stdout.write("  ✓ Baseline ready.\n")

    def _column_exists(self, table, column):
        try:
            with connection.cursor() as cursor:
                cols = [
                    c.name for c in connection.introspection.get_table_description(cursor, table)
                ]
                return column in cols
        except Exception:
            return False

    def _sqlite_version(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT sqlite_version()")
            ver = cursor.fetchone()[0]
        parts = ver.split(".")
        return int(parts[0]), int(parts[1])

    def _what_happened(self, info):
        bar = "─" * 65
        self.stdout.write(f"\n{bar}")
        self.stdout.write(self.style.WARNING("  WHAT HAPPENED"))
        for line in info["problem"].splitlines():
            self.stdout.write(f"  {line}")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("  WHAT TO DO NEXT"))
        self.stdout.write(
            "  Run: python manage.py audit_migrations\n"
            f"  Look for: {info['invariant']}\n"
            "\n"
            "  When you're ready to restore the clean state:\n"
            f"  Run: python manage.py audit_demo teardown "
            f"{next(k for k, v in SCENARIOS.items() if v is info)}"
        )
        self.stdout.write(f"{bar}\n")

    def _header(self, title):
        bar = "=" * 65
        self.stdout.write(f"\n{bar}")
        self.stdout.write(f"  {title}")
        self.stdout.write(f"{bar}\n")
