"""Django migration audit invariants.

This package contains all invariants for verifying migration consistency.

Base invariants (in base.py):
- NoMissingMigrationFiles
- SquashMigrationsProperlyReplaced
- AllExpectedTablesExist
- NoUnexpectedTables
- AllExpectedColumnsExist

Column invariants (in columns.py):
- NoUnexpectedColumns
- ColumnNullabilityMatches
- NoMissingPrimaryKeys

Table invariants (in tables.py):
- NoEmptyTables
- TableNamingConvention
- NoLegacyTables
- TableCountReasonable

Constraint invariants (in constraints.py):
- ForeignKeyColumnsExist
- NoOrphanedForeignKeys
- PrimaryKeyExists
- UniqueConstraintHint
"""

# Base invariants (core functionality)
from django_migration_audit.invariants.base import (
    Invariant,
    ComparisonAInvariant,
    ComparisonBInvariant,
    Violation,
    Severity,
    NoMissingMigrationFiles,
    SquashMigrationsProperlyReplaced,
    AllExpectedTablesExist,
    NoUnexpectedTables,
    AllExpectedColumnsExist,
)

# Column invariants
from django_migration_audit.invariants.columns import (
    NoUnexpectedColumns,
    ColumnNullabilityMatches,
    NoMissingPrimaryKeys,
)

# Table invariants
from django_migration_audit.invariants.tables import (
    NoEmptyTables,
    TableNamingConvention,
    NoLegacyTables,
    TableCountReasonable,
)

# Constraint invariants
from django_migration_audit.invariants.constraints import (
    ForeignKeyColumnsExist,
    NoOrphanedForeignKeys,
    PrimaryKeyExists,
    UniqueConstraintHint,
)

__all__ = [
    # Base classes
    'Invariant',
    'ComparisonAInvariant',
    'ComparisonBInvariant',
    'Violation',
    'Severity',
    # Comparison A invariants
    'NoMissingMigrationFiles',
    'SquashMigrationsProperlyReplaced',
    # Comparison B invariants (base)
    'AllExpectedTablesExist',
    'NoUnexpectedTables',
    'AllExpectedColumnsExist',
    # Column invariants
    'NoUnexpectedColumns',
    'ColumnNullabilityMatches',
    'NoMissingPrimaryKeys',
    # Table invariants
    'NoEmptyTables',
    'TableNamingConvention',
    'NoLegacyTables',
    'TableCountReasonable',
    # Constraint invariants
    'ForeignKeyColumnsExist',
    'NoOrphanedForeignKeys',
    'PrimaryKeyExists',
    'UniqueConstraintHint',
]
