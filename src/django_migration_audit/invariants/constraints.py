"""Constraint and index-specific invariants.

Note: Full constraint and index checking requires additional implementation
in the state.py module. These invariants provide basic checks that can be
implemented with the current schema introspection capabilities.
"""

from django_migration_audit.invariants.base import (
    ComparisonBInvariant,
    Violation,
    Severity,
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
                if col_name.endswith('_id') and col_name != 'id':
                    # This looks like a foreign key column
                    if not actual_table.has_column(col_name):
                        violations.append(Violation(
                            invariant_name=self.name,
                            severity=Severity.ERROR,
                            message=f"Foreign key column '{table_name}.{col_name}' is missing",
                            details={
                                "table": table_name,
                                "column": col_name,
                            }
                        ))
        
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
                if col_name.endswith('_id') and col_name != 'id':
                    # Try to infer the referenced table name
                    # e.g., 'author_id' -> 'app_author'
                    # This is a heuristic and may not always be accurate
                    
                    # Extract the model name (remove _id suffix)
                    model_name = col_name[:-3]  # Remove '_id'
                    
                    # Try to find a table with this model name
                    # Check both with and without app prefix
                    found = False
                    for potential_table in actual_schema.all_tables():
                        if (potential_table.name.endswith(f'_{model_name}') or
                            potential_table.name == model_name):
                            found = True
                            break
                    
                    if not found:
                        violations.append(Violation(
                            invariant_name=self.name,
                            severity=Severity.WARNING,
                            message=f"Column '{table.name}.{col_name}' appears to be a foreign key "
                                    f"but no table for '{model_name}' was found",
                            details={
                                "table": table.name,
                                "column": col_name,
                                "inferred_model": model_name,
                            }
                        ))
        
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
            if table.name.startswith('django_') or table.name.startswith('auth_'):
                continue
            
            # Check for common primary key columns
            has_pk = (
                table.has_column('id') or
                table.has_column('pk') or
                table.has_column('uuid')
            )
            
            if not has_pk:
                violations.append(Violation(
                    invariant_name=self.name,
                    severity=Severity.WARNING,
                    message=f"Table '{table.name}' may be missing a primary key column",
                    details={
                        "table": table.name,
                        "columns": list(table.columns.keys()),
                    }
                ))
        
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
            'email',
            'username',
            'slug',
            'uuid',
            'code',
            'token',
        }
        
        for table in actual_schema.all_tables():
            # Skip Django internal tables
            if table.name.startswith('django_') or table.name.startswith('auth_'):
                continue
            
            for col_name in table.columns:
                if col_name in unique_candidates:
                    # This is just a hint, not a definitive check
                    violations.append(Violation(
                        invariant_name=self.name,
                        severity=Severity.INFO,
                        message=f"Column '{table.name}.{col_name}' commonly has a unique constraint. "
                                f"Verify this is configured correctly.",
                        details={
                            "table": table.name,
                            "column": col_name,
                            "hint": "This column name typically requires a unique constraint",
                        }
                    ))
        
        return violations
