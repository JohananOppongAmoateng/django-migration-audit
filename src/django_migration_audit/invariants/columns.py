"""Additional column-specific invariants."""

from django_migration_audit.invariants.base import (
    ComparisonBInvariant,
    Violation,
    Severity,
)


class NoUnexpectedColumns(ComparisonBInvariant):
    """Verify no unexpected columns exist in actual schema.
    
    This checks for columns that exist in the database but are not
    defined in the expected schema (from migrations). This can happen
    when columns are manually added to the database.
    """
    
    @property
    def name(self):
        return "No Unexpected Columns"
    
    @property
    def description(self):
        return "No columns should exist in the database that aren't in migrations"
    
    def check(self, expected_schema, actual_schema):
        violations = []
        
        # Check each table that exists in both schemas
        for table_name in expected_schema.tables:
            if not actual_schema.has_table(table_name):
                # Table doesn't exist, skip (handled by other invariant)
                continue
            
            expected_table = expected_schema.table(table_name)
            actual_table = actual_schema.table(table_name)
            
            # Find columns in actual but not in expected
            expected_columns = set(expected_table.columns.keys())
            actual_columns = set(actual_table.columns.keys())
            unexpected = actual_columns - expected_columns
            
            for col_name in unexpected:
                col = actual_table.column(col_name)
                violations.append(Violation(
                    invariant_name=self.name,
                    severity=Severity.WARNING,
                    message=f"Unexpected column '{table_name}.{col_name}' "
                            f"(type: {col.db_type}) exists in database but not in migrations",
                    details={
                        "table": table_name,
                        "column": col_name,
                        "db_type": col.db_type,
                        "nullable": col.null,
                    }
                ))
        
        return violations


class ColumnNullabilityMatches(ComparisonBInvariant):
    """Verify column nullability matches between expected and actual schema.
    
    This checks that columns have the correct NULL/NOT NULL constraint.
    Mismatches can occur when migrations are modified or database is
    manually altered.
    """
    
    @property
    def name(self):
        return "Column Nullability Matches"
    
    @property
    def description(self):
        return "Column nullability should match between migrations and database"
    
    def check(self, expected_schema, actual_schema):
        violations = []
        
        for table_name in expected_schema.tables:
            if not actual_schema.has_table(table_name):
                continue
            
            expected_table = expected_schema.table(table_name)
            actual_table = actual_schema.table(table_name)
            
            # Check columns that exist in both
            for col_name in expected_table.columns:
                if not actual_table.has_column(col_name):
                    continue
                
                expected_col = expected_table.column(col_name)
                actual_col = actual_table.column(col_name)
                
                # Check nullability mismatch
                if expected_col.null != actual_col.null:
                    expected_null = "NULL" if expected_col.null else "NOT NULL"
                    actual_null = "NULL" if actual_col.null else "NOT NULL"
                    
                    violations.append(Violation(
                        invariant_name=self.name,
                        severity=Severity.WARNING,
                        message=f"Column '{table_name}.{col_name}' nullability mismatch: "
                                f"expected {expected_null}, actual {actual_null}",
                        details={
                            "table": table_name,
                            "column": col_name,
                            "expected_null": expected_col.null,
                            "actual_null": actual_col.null,
                        }
                    ))
        
        return violations


class NoMissingPrimaryKeys(ComparisonBInvariant):
    """Verify all tables have a primary key column.
    
    This is a best practice check to ensure all tables have a primary key.
    Most Django models have an 'id' field as primary key.
    """
    
    @property
    def name(self):
        return "No Missing Primary Keys"
    
    @property
    def description(self):
        return "All tables should have a primary key column (usually 'id')"
    
    def check(self, expected_schema, actual_schema):
        violations = []
        
        # Common primary key column names
        pk_names = {'id', 'pk', 'uuid'}
        
        for table in actual_schema.all_tables():
            # Skip Django internal tables
            if table.name.startswith('django_') or table.name.startswith('auth_'):
                continue
            
            # Check if table has any common PK column
            table_columns = set(table.columns.keys())
            has_pk = bool(table_columns & pk_names)
            
            if not has_pk:
                violations.append(Violation(
                    invariant_name=self.name,
                    severity=Severity.WARNING,
                    message=f"Table '{table.name}' appears to be missing a primary key column",
                    details={
                        "table": table.name,
                        "columns": list(table.columns.keys()),
                    }
                ))
        
        return violations
