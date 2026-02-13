"""Integration tests for constraint invariants."""

import pytest
from unittest.mock import Mock, patch
from django.db import connection, models
from django.test import TransactionTestCase

from django_migration_audit.core.loader import MigrationHistory
from django_migration_audit.core.state import SchemaState, TableState, ColumnState
from django_migration_audit.invariants.constraints import (
    ForeignKeyColumnsExist,
    NoOrphanedForeignKeys,
    PrimaryKeyExists,
    UniqueConstraintHint,
)


@pytest.mark.django_db
class TestConstraintInvariants(TransactionTestCase):
    """Integration tests for constraint-related invariants."""

    def setUp(self):
        """Set up test database."""
        # Ensure clean state
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS test_constraints_book")
            cursor.execute("DROP TABLE IF EXISTS test_constraints_author")

    def tearDown(self):
        """Clean up test database."""
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS test_constraints_book")
            cursor.execute("DROP TABLE IF EXISTS test_constraints_author")

    def test_foreign_key_columns_exist(self):
        """Test detection of missing foreign key columns using schema objects."""
        invariant = ForeignKeyColumnsExist()

        # Case: Expected has author_id, Actual also has it (pass)
        expected_with_fk = SchemaState(
            tables={
                "test_constraints_book": TableState(
                    name="test_constraints_book",
                    columns={
                        "id": ColumnState("id", "integer", False),
                        "author_id": ColumnState("author_id", "integer", False),
                    },
                )
            }
        )

        violations = invariant.check(expected_with_fk, expected_with_fk)
        assert len(violations) == 0

        # Case: Expected has author_id, Actual does not (fail)
        actual_without_fk = SchemaState(
            tables={
                "test_constraints_book": TableState(
                    name="test_constraints_book",
                    columns={
                        "id": ColumnState("id", "integer", False),
                    },
                )
            }
        )

        violations = invariant.check(expected_with_fk, actual_without_fk)
        assert len(violations) == 1
        assert "author_id" in violations[0].message
        assert "missing" in violations[0].message

    def test_no_orphaned_foreign_keys(self):
        """Test detection of orphaned foreign keys (table missing)."""
        # Logic test
        invariant = NoOrphanedForeignKeys()

        # Case: table has 'author_id' but 'author' table does not exist
        actual_schema = SchemaState(
            tables={
                "test_constraints_book": TableState(
                    name="test_constraints_book",
                    columns={
                        "id": ColumnState("id", "integer", False),
                        "author_id": ColumnState("author_id", "integer", False),
                    },
                )
                # No 'test_constraints_author' table!
            }
        )

        expected_schema = actual_schema  # Doesn't matter for this invariant usually

        violations = invariant.check(expected_schema, actual_schema)
        # Should detect orphan
        assert len(violations) == 1
        assert "author_id" in violations[0].message
        assert (
            "no table for 'author'" in violations[0].message
            or "author" in violations[0].details["inferred_model"]
        )

    def test_primary_key_exists(self):
        """Test detection of missing primary keys."""
        invariant = PrimaryKeyExists()

        # Case: Table without 'id' or 'pk'
        actual_schema = SchemaState(
            tables={
                "test_params": TableState(
                    name="test_params",
                    columns={
                        "key": ColumnState("key", "varchar", False),
                        "value": ColumnState("value", "varchar", False),
                    },
                )
            }
        )

        violations = invariant.check(None, actual_schema)
        assert len(violations) == 1
        assert "missing a primary key" in violations[0].message

    def test_unique_constraint_hint(self):
        """Test hints for potential unique constraints."""
        invariant = UniqueConstraintHint()

        actual_schema = SchemaState(
            tables={
                "test_users": TableState(
                    name="test_users",
                    columns={
                        "id": ColumnState("id", "integer", False),
                        "email": ColumnState("email", "varchar", False),  # Candidate
                        "username": ColumnState("username", "varchar", False),  # Candidate
                        "bio": ColumnState("bio", "text", True),
                    },
                )
            }
        )

        violations = invariant.check(None, actual_schema)
        assert len(violations) == 2
        messages = [v.message for v in violations]
        assert any("email" in m for m in messages)
        assert any("username" in m for m in messages)
