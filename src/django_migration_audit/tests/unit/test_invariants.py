import pytest
from django_migration_audit.core.loader import MigrationNode
from django_migration_audit.core.state import SchemaState, TableState, ColumnState
from django_migration_audit.invariants.base import (
    Violation,
    Severity,
    NoMissingMigrationFiles,
    SquashMigrationsProperlyReplaced,
    AllExpectedTablesExist,
    NoUnexpectedTables,
    AllExpectedColumnsExist,
)


# ----------------------------
# Comparison A Invariants Tests
# ----------------------------

def test_no_missing_migration_files_pass():
    """Test NoMissingMigrationFiles when all files exist."""
    from django_migration_audit.core.loader import MigrationHistory
    
    invariant = NoMissingMigrationFiles()
    
    history = MigrationHistory(
        applied=set(),
        graph_nodes=set(),
        missing_files=set(),  # No missing files
        squashed_replacements=set(),
        plan=[],
    )
    
    violations = invariant.check(migration_history=history)
    assert len(violations) == 0


def test_no_missing_migration_files_fail():
    """Test NoMissingMigrationFiles when files are missing."""
    from django_migration_audit.core.loader import MigrationHistory
    
    invariant = NoMissingMigrationFiles()
    
    missing = MigrationNode(app='myapp', name='0001_initial')
    history = MigrationHistory(
        applied={missing},
        graph_nodes=set(),
        missing_files={missing},
        squashed_replacements=set(),
        plan=[],
    )
    
    violations = invariant.check(migration_history=history)
    assert len(violations) == 1
    assert violations[0].severity == Severity.ERROR
    assert 'myapp.0001_initial' in violations[0].message


def test_squash_migrations_properly_replaced_pass():
    """Test SquashMigrationsProperlyReplaced when squashes are correct."""
    from django_migration_audit.core.loader import MigrationHistory
    
    invariant = SquashMigrationsProperlyReplaced()
    
    replaced = MigrationNode(app='myapp', name='0001_initial')
    history = MigrationHistory(
        applied=set(),  # Replaced migration not applied
        graph_nodes=set(),
        missing_files=set(),
        squashed_replacements={replaced},
        plan=[],
    )
    
    violations = invariant.check(migration_history=history)
    assert len(violations) == 0


def test_squash_migrations_properly_replaced_fail():
    """Test SquashMigrationsProperlyReplaced when replaced migration still applied."""
    from django_migration_audit.core.loader import MigrationHistory
    
    invariant = SquashMigrationsProperlyReplaced()
    
    replaced = MigrationNode(app='myapp', name='0001_initial')
    history = MigrationHistory(
        applied={replaced},  # Replaced migration still applied!
        graph_nodes=set(),
        missing_files=set(),
        squashed_replacements={replaced},
        plan=[],
    )
    
    violations = invariant.check(migration_history=history)
    assert len(violations) == 1
    assert violations[0].severity == Severity.WARNING
    assert 'myapp.0001_initial' in violations[0].message


# ----------------------------
# Comparison B Invariants Tests
# ----------------------------

def test_all_expected_tables_exist_pass():
    """Test AllExpectedTablesExist when all tables exist."""
    invariant = AllExpectedTablesExist()
    
    expected = SchemaState(tables={
        'users': TableState(name='users'),
        'posts': TableState(name='posts'),
    })
    
    actual = SchemaState(tables={
        'users': TableState(name='users'),
        'posts': TableState(name='posts'),
    })
    
    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 0


def test_all_expected_tables_exist_fail():
    """Test AllExpectedTablesExist when a table is missing."""
    invariant = AllExpectedTablesExist()
    
    expected = SchemaState(tables={
        'users': TableState(name='users'),
        'posts': TableState(name='posts'),
    })
    
    actual = SchemaState(tables={
        'users': TableState(name='users'),
        # 'posts' is missing!
    })
    
    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 1
    assert violations[0].severity == Severity.ERROR
    assert 'posts' in violations[0].message


def test_no_unexpected_tables_pass():
    """Test NoUnexpectedTables when no extra tables exist."""
    invariant = NoUnexpectedTables()
    
    expected = SchemaState(tables={
        'users': TableState(name='users'),
    })
    
    actual = SchemaState(tables={
        'users': TableState(name='users'),
    })
    
    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 0


def test_no_unexpected_tables_fail():
    """Test NoUnexpectedTables when extra tables exist."""
    invariant = NoUnexpectedTables()
    
    expected = SchemaState(tables={
        'users': TableState(name='users'),
    })
    
    actual = SchemaState(tables={
        'users': TableState(name='users'),
        'manual_table': TableState(name='manual_table'),  # Unexpected!
    })
    
    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 1
    assert violations[0].severity == Severity.WARNING
    assert 'manual_table' in violations[0].message


def test_all_expected_columns_exist_pass():
    """Test AllExpectedColumnsExist when all columns match."""
    invariant = AllExpectedColumnsExist()
    
    expected = SchemaState(tables={
        'users': TableState(
            name='users',
            columns={
                'id': ColumnState('id', 'integer', False),
                'name': ColumnState('name', 'varchar', False),
            }
        ),
    })
    
    actual = SchemaState(tables={
        'users': TableState(
            name='users',
            columns={
                'id': ColumnState('id', 'integer', False),
                'name': ColumnState('name', 'varchar', False),
            }
        ),
    })
    
    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 0


def test_all_expected_columns_exist_missing_column():
    """Test AllExpectedColumnsExist when a column is missing."""
    invariant = AllExpectedColumnsExist()
    
    expected = SchemaState(tables={
        'users': TableState(
            name='users',
            columns={
                'id': ColumnState('id', 'integer', False),
                'name': ColumnState('name', 'varchar', False),
            }
        ),
    })
    
    actual = SchemaState(tables={
        'users': TableState(
            name='users',
            columns={
                'id': ColumnState('id', 'integer', False),
                # 'name' is missing!
            }
        ),
    })
    
    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 1
    assert violations[0].severity == Severity.ERROR
    assert 'name' in violations[0].message


def test_all_expected_columns_exist_wrong_type():
    """Test AllExpectedColumnsExist when a column has wrong type."""
    invariant = AllExpectedColumnsExist()
    
    expected = SchemaState(tables={
        'users': TableState(
            name='users',
            columns={
                'id': ColumnState('id', 'integer', False),
            }
        ),
    })
    
    actual = SchemaState(tables={
        'users': TableState(
            name='users',
            columns={
                'id': ColumnState('id', 'bigint', False),  # Wrong type!
            }
        ),
    })
    
    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 1
    assert violations[0].severity == Severity.ERROR
    assert 'wrong type' in violations[0].message.lower()


def test_all_expected_columns_exist_skips_missing_tables():
    """Test AllExpectedColumnsExist skips tables that don't exist."""
    invariant = AllExpectedColumnsExist()
    
    expected = SchemaState(tables={
        'users': TableState(
            name='users',
            columns={
                'id': ColumnState('id', 'integer', False),
            }
        ),
    })
    
    actual = SchemaState(tables={})  # No tables at all
    
    # Should not raise errors for columns when table is missing
    # (that's handled by AllExpectedTablesExist)
    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 0


# ----------------------------
# Violation Tests
# ----------------------------

def test_violation_str():
    """Test Violation string representation."""
    violation = Violation(
        invariant_name="Test Invariant",
        severity=Severity.ERROR,
        message="Something went wrong",
        details={'key': 'value'}
    )
    
    result = str(violation)
    assert 'ERROR' in result
    assert 'Test Invariant' in result
    assert 'Something went wrong' in result


def test_violation_severity_enum():
    """Test Severity enum values."""
    assert Severity.ERROR.value == 'error'
    assert Severity.WARNING.value == 'warning'
    assert Severity.INFO.value == 'info'


class TestMigrationInvariants:
    """Placeholder test class (kept for compatibility)."""
    
    def test_placeholder(self):
        """Placeholder test."""
        assert True
