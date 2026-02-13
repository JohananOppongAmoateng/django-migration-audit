"""End-to-end integration tests for the audit_migrations command."""

import pytest
from io import StringIO
from unittest.mock import Mock, patch
from django.core.management import call_command
from django.db import connection, models
from django.test import TransactionTestCase, override_settings

from django_migration_audit.core.loader import MigrationNode, MigrationHistory
from django_migration_audit.core.state import SchemaState, TableState, ColumnState


@pytest.mark.django_db
class TestAuditMigrationsCommandIntegration(TransactionTestCase):
    """Integration tests with REAL database and REAL migration files."""

    def setUp(self):
        """Set up test database."""
        # Clean up possible tables from previous runs just in case
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS test_e2e_app_model")
            # Also clean up migration history to ensure migrate command runs
            cursor.execute("DELETE FROM django_migrations WHERE app = 'test_e2e_app'")

    def tearDown(self):
        """Clean up test database."""
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS test_e2e_app_model")
            cursor.execute("DELETE FROM django_migrations WHERE app = 'test_e2e_app'")

    def test_audit_clean_state(self):
        """Test audit command with a clean state (DB matches Disk)."""
        # 1. APPLY MIGRATIONS (Real!)
        call_command("migrate", "test_e2e_app", verbosity=0)

        # 2. RUN AUDIT COMMAND
        out = StringIO()
        call_command("audit_migrations", comparison="b", stdout=out)
        output = out.getvalue()

        # 3. VERIFY
        assert "Comparison B: Reality Check" in output
        assert "✅ No violations found!" in output or "No violations found" in output

    def test_audit_detect_extra_column(self):
        """Test detection of an extra column in the DB (Drift)."""
        # 1. APPLY MIGRATIONS (Real!)
        call_command("migrate", "test_e2e_app", verbosity=0)

        # 2. MANUALLY ADD COLUMN (Drift)
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE test_e2e_app_model ADD COLUMN notes TEXT NULL")

        # 3. RUN AUDIT COMMAND
        out = StringIO()
        call_command("audit_migrations", comparison="b", stdout=out)
        output = out.getvalue()

        # 4. VERIFY
        assert "Violation" in output or "violation" in output.lower()
        assert "notes" in output
        assert "Unexpected column" in output or "unexpected" in output.lower()

    def test_audit_detect_missing_table(self):
        """Test detection of a missing table in the DB."""
        # 1. APPLY MIGRATIONS (Real!)
        call_command("migrate", "test_e2e_app", verbosity=0)

        # 2. MANUALLY DROP TABLE (Drift)
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE test_e2e_app_model")

        # 3. RUN AUDIT COMMAND
        out = StringIO()
        call_command("audit_migrations", comparison="b", stdout=out)
        output = out.getvalue()

        # 4. VERIFY
        assert "test_e2e_app_model" in output
        assert "Missing table" in output or "missing" in output.lower()
