"""
Invariant Base Classes

Invariants are the **verification rules** for the two comparisons in
django-migration-audit.

## Comparison A Invariants: Trust Verification
These invariants verify migration history ↔ migration code consistency:
- No modified migration files
- No missing migration files
- No fake-applied migrations
- Squash migrations properly replaced

## Comparison B Invariants: Reality Check
These invariants verify expected schema ↔ actual schema consistency:
- No schema drift
- All expected tables exist
- All expected columns exist with correct types
- All expected constraints and indexes exist

## Custom Invariants
Extend the base classes in this module to implement custom verification rules
for your specific use cases.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List
from enum import Enum


class Severity(Enum):
    """Severity levels for invariant violations."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Violation:
    """Represents a single invariant violation."""
    invariant_name: str
    severity: Severity
    message: str
    details: dict = None

    def __str__(self):
        return f"[{self.severity.value.upper()}] {self.invariant_name}: {self.message}"


class Invariant(ABC):
    """
    Base class for all invariants.
    
    Invariants are verification rules that check for consistency
    between different inputs in the django-migration-audit system.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this invariant."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this invariant checks."""
        pass

    @abstractmethod
    def check(self, **kwargs) -> List[Violation]:
        """
        Check the invariant and return any violations.
        
        Returns:
            List of Violation objects (empty list if no violations)
        """
        pass


class ComparisonAInvariant(Invariant):
    """
    Base class for Comparison A invariants (Trust Verification).
    
    These invariants verify migration history ↔ migration code consistency.
    """
    pass


class ComparisonBInvariant(Invariant):
    """
    Base class for Comparison B invariants (Reality Check).
    
    These invariants verify expected schema ↔ actual schema consistency.
    """
    pass


# ----------------------------
# Comparison A Invariants
# ----------------------------

class NoMissingMigrationFiles(ComparisonAInvariant):
    """Verify that all applied migrations have corresponding files on disk."""

    @property
    def name(self) -> str:
        return "No Missing Migration Files"

    @property
    def description(self) -> str:
        return "All migrations recorded as applied must have corresponding files on disk"

    def check(self, migration_history) -> List[Violation]:
        violations = []
        
        if migration_history.missing_files:
            for missing in migration_history.missing_files:
                violations.append(Violation(
                    invariant_name=self.name,
                    severity=Severity.ERROR,
                    message=f"Migration {missing.app}.{missing.name} is recorded as applied but file is missing",
                    details={"app": missing.app, "name": missing.name}
                ))
        
        return violations


class SquashMigrationsProperlyReplaced(ComparisonAInvariant):
    """Verify that squashed migrations properly replace their originals."""

    @property
    def name(self) -> str:
        return "Squash Migrations Properly Replaced"

    @property
    def description(self) -> str:
        return "Squashed migrations must properly replace their original migrations"

    def check(self, migration_history) -> List[Violation]:
        violations = []
        
        # Check if any replaced migrations are still applied
        for replaced in migration_history.squashed_replacements:
            if replaced in migration_history.applied:
                violations.append(Violation(
                    invariant_name=self.name,
                    severity=Severity.WARNING,
                    message=f"Migration {replaced.app}.{replaced.name} is replaced by a squash but still marked as applied",
                    details={"app": replaced.app, "name": replaced.name}
                ))
        
        return violations


# ----------------------------
# Comparison B Invariants
# ----------------------------

class AllExpectedTablesExist(ComparisonBInvariant):
    """Verify that all expected tables exist in the actual database."""

    @property
    def name(self) -> str:
        return "All Expected Tables Exist"

    @property
    def description(self) -> str:
        return "All tables from migration operations must exist in the actual database"

    def check(self, expected_schema, actual_schema) -> List[Violation]:
        violations = []
        
        for expected_table in expected_schema.all_tables():
            if not actual_schema.has_table(expected_table.name):
                violations.append(Violation(
                    invariant_name=self.name,
                    severity=Severity.ERROR,
                    message=f"Expected table '{expected_table.name}' does not exist in database",
                    details={"table_name": expected_table.name}
                ))
        
        return violations


class NoUnexpectedTables(ComparisonBInvariant):
    """Verify that no unexpected tables exist in the actual database."""

    @property
    def name(self) -> str:
        return "No Unexpected Tables"

    @property
    def description(self) -> str:
        return "No tables should exist in the database that aren't defined in migrations"

    def check(self, expected_schema, actual_schema) -> List[Violation]:
        violations = []
        
        for actual_table in actual_schema.all_tables():
            if not expected_schema.has_table(actual_table.name):
                violations.append(Violation(
                    invariant_name=self.name,
                    severity=Severity.WARNING,
                    message=f"Unexpected table '{actual_table.name}' exists in database",
                    details={"table_name": actual_table.name}
                ))
        
        return violations


class AllExpectedColumnsExist(ComparisonBInvariant):
    """Verify that all expected columns exist with correct types."""

    @property
    def name(self) -> str:
        return "All Expected Columns Exist"

    @property
    def description(self) -> str:
        return "All columns from migration operations must exist with correct types"

    def check(self, expected_schema, actual_schema) -> List[Violation]:
        violations = []
        
        for expected_table in expected_schema.all_tables():
            if not actual_schema.has_table(expected_table.name):
                continue  # Table-level check handles this
            
            actual_table = actual_schema.table(expected_table.name)
            
            for col_name, expected_col in expected_table.columns.items():
                if not actual_table.has_column(col_name):
                    violations.append(Violation(
                        invariant_name=self.name,
                        severity=Severity.ERROR,
                        message=f"Expected column '{expected_table.name}.{col_name}' does not exist",
                        details={
                            "table_name": expected_table.name,
                            "column_name": col_name,
                            "expected_type": expected_col.db_type
                        }
                    ))
                else:
                    actual_col = actual_table.column(col_name)
                    if expected_col.db_type != actual_col.db_type:
                        violations.append(Violation(
                            invariant_name=self.name,
                            severity=Severity.ERROR,
                            message=f"Column '{expected_table.name}.{col_name}' has wrong type",
                            details={
                                "table_name": expected_table.name,
                                "column_name": col_name,
                                "expected_type": expected_col.db_type,
                                "actual_type": actual_col.db_type
                            }
                        ))
        
        return violations
