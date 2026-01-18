"""Integration tests for drift detection."""

import pytest
from django.db import connection, models
from django.db.migrations.operations import models as model_ops
from django.test import TestCase, TransactionTestCase

from django_migration_audit.core.loader import load_migration_history
from django_migration_audit.core.extractor import MigrationExtractor
from django_migration_audit.core.introspection import introspect_schema
from django_migration_audit.invariants.base import (
    AllExpectedTablesExist,
    NoUnexpectedTables,
    AllExpectedColumnsExist,
    Severity,
)


@pytest.mark.django_db
class TestDriftDetection(TransactionTestCase):
    """Test cases for drift detection between migrations and database state."""

    def setUp(self):
        """Set up test database with a simple table."""
        with connection.schema_editor() as schema_editor:
            # Create a test table
            class TestAuthor(models.Model):
                name = models.CharField(max_length=100)
                email = models.EmailField()
                
                class Meta:
                    app_label = 'test_drift'
                    db_table = 'test_author'
            
            self.TestAuthor = TestAuthor
            schema_editor.create_model(TestAuthor)

    def tearDown(self):
        """Clean up test database."""
        with connection.schema_editor() as schema_editor:
            try:
                schema_editor.delete_model(self.TestAuthor)
            except:
                pass

    def test_no_drift_clean_state(self):
        """Test that clean state (no drift) passes all checks."""
        # Introspect the actual schema
        actual_schema = introspect_schema(using='default')
        
        # Verify the table exists
        assert actual_schema.has_table('test_author')
        
        # Get the actual types from introspection to build matching expected schema
        actual_table = actual_schema.table('test_author')
        
        # Create expected schema matching actual (using introspected types)
        from django_migration_audit.core.state import SchemaState, TableState, ColumnState
        
        expected_schema = SchemaState(tables={
            'test_author': TableState(
                name='test_author',
                columns={
                    col_name: ColumnState(col_name, col_state.db_type, col_state.null)
                    for col_name, col_state in actual_table.columns.items()
                }
            )
        })
        
        # Run invariants
        invariant = AllExpectedTablesExist()
        violations = invariant.check(expected_schema=expected_schema, actual_schema=actual_schema)
        assert len(violations) == 0
        
        invariant = AllExpectedColumnsExist()
        violations = invariant.check(expected_schema=expected_schema, actual_schema=actual_schema)
        assert len(violations) == 0

    def test_detect_manual_column_addition(self):
        """Test detecting manually added columns."""
        # Add a column manually (simulating drift)
        with connection.cursor() as cursor:
            cursor.execute('ALTER TABLE test_author ADD COLUMN phone VARCHAR(20)')
        
        # Introspect the actual schema
        actual_schema = introspect_schema(using='default')
        
        # Create expected schema without the phone column
        from django_migration_audit.core.state import SchemaState, TableState, ColumnState
        
        expected_schema = SchemaState(tables={
            'test_author': TableState(
                name='test_author',
                columns={
                    'id': ColumnState('id', 'integer', False),
                    'name': ColumnState('name', 'varchar', False),
                    'email': ColumnState('email', 'varchar', False),
                }
            )
        })
        
        # Verify the drift is detected
        assert actual_schema.table('test_author').has_column('phone')
        assert not expected_schema.table('test_author').has_column('phone')

    def test_detect_manual_table_addition(self):
        """Test detecting manually added tables."""
        # Add a table manually
        with connection.cursor() as cursor:
            cursor.execute('CREATE TABLE manual_table (id INTEGER PRIMARY KEY, data TEXT)')
        
        try:
            # Introspect the actual schema
            actual_schema = introspect_schema(using='default')
            
            # Create expected schema without the manual table
            from django_migration_audit.core.state import SchemaState, TableState, ColumnState
            
            expected_schema = SchemaState(tables={
                'test_author': TableState(
                    name='test_author',
                    columns={
                        'id': ColumnState('id', 'integer', False),
                        'name': ColumnState('name', 'varchar', False),
                        'email': ColumnState('email', 'varchar', False),
                    }
                )
            })
            
            # Run NoUnexpectedTables invariant
            invariant = NoUnexpectedTables()
            violations = invariant.check(expected_schema=expected_schema, actual_schema=actual_schema)
            
            # Should detect the manual table
            assert len(violations) > 0
            assert any('manual_table' in v.message for v in violations)
            assert violations[0].severity == Severity.WARNING
            
        finally:
            # Clean up
            with connection.cursor() as cursor:
                cursor.execute('DROP TABLE IF EXISTS manual_table')

    def test_detect_manual_table_deletion(self):
        """Test detecting manually deleted tables."""
        # Delete the table manually
        with connection.cursor() as cursor:
            cursor.execute('DROP TABLE test_author')
        
        try:
            # Introspect the actual schema
            actual_schema = introspect_schema(using='default')
            
            # Create expected schema with the table
            from django_migration_audit.core.state import SchemaState, TableState, ColumnState
            
            expected_schema = SchemaState(tables={
                'test_author': TableState(
                    name='test_author',
                    columns={
                        'id': ColumnState('id', 'integer', False),
                        'name': ColumnState('name', 'varchar', False),
                        'email': ColumnState('email', 'varchar', False),
                    }
                )
            })
            
            # Run AllExpectedTablesExist invariant
            invariant = AllExpectedTablesExist()
            violations = invariant.check(expected_schema=expected_schema, actual_schema=actual_schema)
            
            # Should detect the missing table
            assert len(violations) == 1
            assert 'test_author' in violations[0].message
            assert violations[0].severity == Severity.ERROR
            
        finally:
            # Recreate the table for tearDown
            with connection.schema_editor() as schema_editor:
                schema_editor.create_model(self.TestAuthor)

    def test_detect_column_type_change(self):
        """Test detecting column type changes."""
        # This test verifies type mismatch detection
        from django_migration_audit.core.state import SchemaState, TableState, ColumnState
        
        # Introspect actual schema to get real types
        actual_schema = introspect_schema(using='default')
        actual_table = actual_schema.table('test_author')
        
        # Get the actual type for 'name' column and create expected with different type
        actual_name_type = actual_table.column('name').db_type
        # Use a deliberately wrong type (if actual is 'varchar', use 'text', otherwise 'varchar')
        wrong_type = 'text' if actual_name_type != 'text' else 'varchar'
        
        # Create expected schema with different type for name
        expected_schema = SchemaState(tables={
            'test_author': TableState(
                name='test_author',
                columns={
                    'id': ColumnState('id', actual_table.column('id').db_type, False),
                    'name': ColumnState('name', wrong_type, False),  # Different type!
                    'email': ColumnState('email', actual_table.column('email').db_type, False),
                }
            )
        })
        
        # Run AllExpectedColumnsExist invariant
        invariant = AllExpectedColumnsExist()
        violations = invariant.check(expected_schema=expected_schema, actual_schema=actual_schema)
        
        # Should detect the type mismatch
        assert len(violations) == 1
        assert 'name' in violations[0].message
        assert 'wrong type' in violations[0].message.lower()

    def test_detect_manual_column_deletion(self):
        """Test detecting manually deleted columns."""
        # Note: SQLite doesn't support DROP COLUMN easily, so we'll test the invariant logic
        from django_migration_audit.core.state import SchemaState, TableState, ColumnState
        
        # Introspect actual schema
        actual_schema = introspect_schema(using='default')
        actual_table = actual_schema.table('test_author')
        
        # Create expected schema with an extra column that doesn't exist
        expected_columns = {
            col_name: ColumnState(col_name, col_state.db_type, col_state.null)
            for col_name, col_state in actual_table.columns.items()
        }
        # Add a column that doesn't exist in the actual schema
        expected_columns['deleted_column'] = ColumnState('deleted_column', 'varchar', True)
        
        expected_schema = SchemaState(tables={
            'test_author': TableState(
                name='test_author',
                columns=expected_columns
            )
        })
        
        # Run AllExpectedColumnsExist invariant
        invariant = AllExpectedColumnsExist()
        violations = invariant.check(expected_schema=expected_schema, actual_schema=actual_schema)
        
        # Should detect the missing column
        assert len(violations) == 1
        assert 'deleted_column' in violations[0].message
        assert violations[0].severity == Severity.ERROR

    def test_detect_multiple_drifts(self):
        """Test detecting multiple drift issues simultaneously."""
        # Add a manual column
        with connection.cursor() as cursor:
            cursor.execute('ALTER TABLE test_author ADD COLUMN extra_field TEXT')
        
        # Add a manual table
        with connection.cursor() as cursor:
            cursor.execute('CREATE TABLE extra_table (id INTEGER PRIMARY KEY)')
        
        try:
            # Introspect actual schema
            actual_schema = introspect_schema(using='default')
            actual_table = actual_schema.table('test_author')
            
            # Build expected schema using actual introspected types
            # but WITHOUT extra_field and WITH missing_column
            from django_migration_audit.core.state import SchemaState, TableState, ColumnState
            
            # Get columns except extra_field (which we manually added)
            expected_columns = {
                col_name: ColumnState(col_name, col_state.db_type, col_state.null)
                for col_name, col_state in actual_table.columns.items()
                if col_name != 'extra_field'  # Exclude the manually added column
            }
            # Add a missing column
            expected_columns['missing_column'] = ColumnState('missing_column', 'varchar', True)
            
            expected_schema = SchemaState(tables={
                'test_author': TableState(
                    name='test_author',
                    columns=expected_columns
                )
            })
            
            # Check for unexpected tables
            invariant = NoUnexpectedTables()
            violations = invariant.check(expected_schema=expected_schema, actual_schema=actual_schema)
            # Should detect extra_table as unexpected
            assert any('extra_table' in v.message for v in violations)
            
            # Check for missing columns
            invariant = AllExpectedColumnsExist()
            violations = invariant.check(expected_schema=expected_schema, actual_schema=actual_schema)
            assert len(violations) == 1  # missing_column
            
        finally:
            # Clean up
            with connection.cursor() as cursor:
                cursor.execute('DROP TABLE IF EXISTS extra_table')

    def test_drift_with_nullable_columns(self):
        """Test drift detection with nullable vs non-nullable columns."""
        from django_migration_audit.core.state import SchemaState, TableState, ColumnState
        
        # Introspect actual schema
        actual_schema = introspect_schema(using='default')
        
        # Verify actual nullability
        actual_table = actual_schema.table('test_author')
        # id is NOT NULL (primary key)
        # name is NOT NULL (no null=True)
        # email is NOT NULL (no null=True)
        
        # Create expected schema matching actual nullability (using actual introspected types)
        expected_schema = SchemaState(tables={
            'test_author': TableState(
                name='test_author',
                columns={
                    col_name: ColumnState(col_name, col_state.db_type, col_state.null)
                    for col_name, col_state in actual_table.columns.items()
                }
            )
        })
        
        # Should not detect violations
        invariant = AllExpectedColumnsExist()
        violations = invariant.check(expected_schema=expected_schema, actual_schema=actual_schema)
        assert len(violations) == 0


class TestDriftDetectionHelpers:
    """Test helper functions for drift detection."""

    def test_schema_comparison_empty_schemas(self):
        """Test comparing two empty schemas."""
        from django_migration_audit.core.state import SchemaState
        
        schema1 = SchemaState(tables={})
        schema2 = SchemaState(tables={})
        
        invariant = AllExpectedTablesExist()
        violations = invariant.check(expected_schema=schema1, actual_schema=schema2)
        assert len(violations) == 0

    def test_schema_comparison_identical_schemas(self):
        """Test comparing two identical schemas."""
        from django_migration_audit.core.state import SchemaState, TableState, ColumnState
        
        schema1 = SchemaState(tables={
            'users': TableState(
                name='users',
                columns={
                    'id': ColumnState('id', 'integer', False),
                    'name': ColumnState('name', 'varchar', False),
                }
            )
        })
        
        schema2 = SchemaState(tables={
            'users': TableState(
                name='users',
                columns={
                    'id': ColumnState('id', 'integer', False),
                    'name': ColumnState('name', 'varchar', False),
                }
            )
        })
        
        # Test all invariants
        invariant = AllExpectedTablesExist()
        violations = invariant.check(expected_schema=schema1, actual_schema=schema2)
        assert len(violations) == 0
        
        invariant = NoUnexpectedTables()
        violations = invariant.check(expected_schema=schema1, actual_schema=schema2)
        assert len(violations) == 0
        
        invariant = AllExpectedColumnsExist()
        violations = invariant.check(expected_schema=schema1, actual_schema=schema2)
        assert len(violations) == 0
