"""Constraint and index-specific invariants."""

from django_migration_audit.invariants.base import (
    ComparisonBInvariant,
    Severity,
    Violation,
)


class ForeignKeyColumnsExist(ComparisonBInvariant):
    """Verify foreign key columns exist for relationship fields.

    Django creates foreign key columns with '_id' suffix. This invariant
    checks that these columns exist when expected.
    """

    @property
    def name(self):
        return "Foreign Key Columns Exist"

    @property
    def description(self):
        return "Foreign key columns (ending in _id) should exist for relationship fields"

    def check(self, expected_schema, actual_schema):
        violations = []

        for table_name in expected_schema.tables:
            if not actual_schema.has_table(table_name):
                continue

            expected_table = expected_schema.table(table_name)
            actual_table = actual_schema.table(table_name)

            # Find expected FK columns (ending in _id)
            for col_name in expected_table.columns:
                if col_name.endswith("_id") and col_name != "id":
                    # This looks like a foreign key column
                    if not actual_table.has_column(col_name):
                        violations.append(
                            Violation(
                                invariant_name=self.name,
                                severity=Severity.ERROR,
                                message=f"Foreign key column '{table_name}.{col_name}' is missing",
                                details={
                                    "table": table_name,
                                    "column": col_name,
                                },
                            )
                        )

        return violations


class NoOrphanedForeignKeys(ComparisonBInvariant):
    """Verify no foreign key columns exist without corresponding tables.

    This checks that tables referenced by foreign keys actually exist.
    Note: This is a heuristic check based on column naming patterns.
    """

    @property
    def name(self):
        return "No Orphaned Foreign Keys"

    @property
    def description(self):
        return "Foreign key columns should reference existing tables"

    def check(self, expected_schema, actual_schema):
        violations = []

        for table in actual_schema.all_tables():
            for col_name, col in table.columns.items():
                # Check if this looks like a foreign key (ends with _id)
                if col_name.endswith("_id") and col_name != "id":
                    # Try to infer the referenced table name
                    # e.g., 'author_id' -> 'app_author'
                    # This is a heuristic and may not always be accurate

                    # Extract the model name (remove _id suffix)
                    model_name = col_name[:-3]  # Remove '_id'

                    # Try to find a table with this model name
                    # Check both with and without app prefix
                    found = False
                    for potential_table in actual_schema.all_tables():
                        if (
                            potential_table.name.endswith(f"_{model_name}")
                            or potential_table.name == model_name
                        ):
                            found = True
                            break

                    if not found:
                        violations.append(
                            Violation(
                                invariant_name=self.name,
                                severity=Severity.WARNING,
                                message=f"Column '{table.name}.{col_name}' appears to be a foreign key "
                                f"but no table for '{model_name}' was found",
                                details={
                                    "table": table.name,
                                    "column": col_name,
                                    "inferred_model": model_name,
                                },
                            )
                        )

        return violations


class PrimaryKeyExists(ComparisonBInvariant):
    """Verify each table has a primary key column.

    This checks that tables have an 'id' column which is typically
    the primary key in Django models.
    """

    @property
    def name(self):
        return "Primary Key Exists"

    @property
    def description(self):
        return "Each table should have a primary key column (usually 'id')"

    def check(self, expected_schema, actual_schema):
        violations = []

        for table in actual_schema.all_tables():
            # Skip Django internal tables
            if table.name.startswith("django_") or table.name.startswith("auth_"):
                continue

            # Check for common primary key columns
            has_pk = table.has_column("id") or table.has_column("pk") or table.has_column("uuid")

            if not has_pk:
                violations.append(
                    Violation(
                        invariant_name=self.name,
                        severity=Severity.WARNING,
                        message=f"Table '{table.name}' may be missing a primary key column",
                        details={
                            "table": table.name,
                            "columns": list(table.columns.keys()),
                        },
                    )
                )

        return violations


class UniqueConstraintHint(ComparisonBInvariant):
    """Provide hints about potential unique constraint issues.

    This is a placeholder for future unique constraint checking.
    Currently, it just checks for common patterns that suggest
    unique constraints should exist.
    """

    @property
    def name(self):
        return "Unique Constraint Hint"

    @property
    def description(self):
        return "Check for columns that commonly have unique constraints"

    def check(self, expected_schema, actual_schema):
        violations = []

        # Common column names that should typically be unique
        unique_candidates = {
            "email",
            "username",
            "slug",
            "uuid",
            "code",
            "token",
        }

        for table in actual_schema.all_tables():
            # Skip Django internal tables
            if table.name.startswith("django_") or table.name.startswith("auth_"):
                continue

            for col_name in table.columns:
                if col_name in unique_candidates:
                    # This is just a hint, not a definitive check
                    violations.append(
                        Violation(
                            invariant_name=self.name,
                            severity=Severity.INFO,
                            message=f"Column '{table.name}.{col_name}' commonly has a unique constraint. "
                            f"Verify this is configured correctly.",
                            details={
                                "table": table.name,
                                "column": col_name,
                                "hint": "This column name typically requires a unique constraint",
                            },
                        )
                    )

        return violations


class AllExpectedIndexesExist(ComparisonBInvariant):
    """Verify that all indexes defined in migrations exist in the actual database."""

    @property
    def name(self):
        return "All Expected Indexes Exist"

    @property
    def description(self):
        return "All indexes from AddIndex migration operations must exist in the database"

    def check(self, expected_schema, actual_schema):
        violations = []

        for expected_table in expected_schema.all_tables():
            if not actual_schema.has_table(expected_table.name):
                continue  # Missing table handled by AllExpectedTablesExist

            actual_table = actual_schema.table(expected_table.name)

            for idx_name, expected_idx in expected_table.indexes.items():
                if not actual_table.has_index(idx_name):
                    violations.append(
                        Violation(
                            invariant_name=self.name,
                            severity=Severity.ERROR,
                            message=f"Expected index '{idx_name}' on table '{expected_table.name}' does not exist",
                            details={
                                "table": expected_table.name,
                                "index": idx_name,
                                "columns": list(expected_idx.columns),
                            },
                        )
                    )

        return violations


class AllExpectedConstraintsExist(ComparisonBInvariant):
    """Verify that all constraints defined in migrations exist in the actual database."""

    @property
    def name(self):
        return "All Expected Constraints Exist"

    @property
    def description(self):
        return "All constraints from AddConstraint migration operations must exist in the database"

    def check(self, expected_schema, actual_schema):
        violations = []

        for expected_table in expected_schema.all_tables():
            if not actual_schema.has_table(expected_table.name):
                continue  # Missing table handled by AllExpectedTablesExist

            actual_table = actual_schema.table(expected_table.name)

            for con_name, expected_con in expected_table.constraints.items():
                if not actual_table.has_constraint(con_name):
                    violations.append(
                        Violation(
                            invariant_name=self.name,
                            severity=Severity.ERROR,
                            message=f"Expected {expected_con.constraint_type} constraint '{con_name}' "
                            f"on table '{expected_table.name}' does not exist",
                            details={
                                "table": expected_table.name,
                                "constraint": con_name,
                                "type": expected_con.constraint_type,
                                "columns": list(expected_con.columns),
                            },
                        )
                    )

        return violations


class NoUnexpectedIndexes(ComparisonBInvariant):
    """Verify no indexes exist in the database that aren't defined in migrations.

    Reports WARNING because Django also creates implicit indexes (e.g. for
    ForeignKey columns) that are not tracked via AddIndex operations. Users
    should review violations rather than treating them all as hard errors.
    """

    @property
    def name(self):
        return "No Unexpected Indexes"

    @property
    def description(self):
        return (
            "No indexes should exist in the database that aren't defined via AddIndex migrations"
        )

    def check(self, expected_schema, actual_schema):
        violations = []

        for actual_table in actual_schema.all_tables():
            if not expected_schema.has_table(actual_table.name):
                continue  # Unexpected table handled by NoUnexpectedTables

            expected_table = expected_schema.table(actual_table.name)

            for idx_name, actual_idx in actual_table.indexes.items():
                if not expected_table.has_index(idx_name):
                    violations.append(
                        Violation(
                            invariant_name=self.name,
                            severity=Severity.WARNING,
                            message=f"Unexpected index '{idx_name}' on table '{actual_table.name}' "
                            f"is not defined in migrations",
                            details={
                                "table": actual_table.name,
                                "index": idx_name,
                                "columns": list(actual_idx.columns),
                            },
                        )
                    )

        return violations


class NoUnexpectedConstraints(ComparisonBInvariant):
    """Verify no constraints exist in the database that aren't defined in migrations.

    Reports WARNING because Django creates implicit unique constraints for
    fields with unique=True and unique_together, which are not tracked via
    AddConstraint operations. Users should review violations rather than
    treating them all as hard errors.
    """

    @property
    def name(self):
        return "No Unexpected Constraints"

    @property
    def description(self):
        return "No constraints should exist in the database that aren't defined via AddConstraint migrations"

    def check(self, expected_schema, actual_schema):
        violations = []

        for actual_table in actual_schema.all_tables():
            if not expected_schema.has_table(actual_table.name):
                continue  # Unexpected table handled by NoUnexpectedTables

            expected_table = expected_schema.table(actual_table.name)

            for con_name, actual_con in actual_table.constraints.items():
                if not expected_table.has_constraint(con_name):
                    violations.append(
                        Violation(
                            invariant_name=self.name,
                            severity=Severity.WARNING,
                            message=f"Unexpected {actual_con.constraint_type} constraint '{con_name}' "
                            f"on table '{actual_table.name}' is not defined in migrations",
                            details={
                                "table": actual_table.name,
                                "constraint": con_name,
                                "type": actual_con.constraint_type,
                                "columns": list(actual_con.columns),
                            },
                        )
                    )

        return violations
