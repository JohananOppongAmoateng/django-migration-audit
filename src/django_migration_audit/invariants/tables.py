"""Table-specific invariants."""

from django_migration_audit.invariants.base import (
    ComparisonBInvariant,
    Violation,
    Severity,
)


class NoEmptyTables(ComparisonBInvariant):
    """Verify no tables exist without any columns.
    
    This is a sanity check to detect corrupted or improperly created tables.
    """
    
    @property
    def name(self):
        return "No Empty Tables"
    
    @property
    def description(self):
        return "All tables should have at least one column"
    
    def check(self, expected_schema, actual_schema):
        violations = []
        
        for table in actual_schema.all_tables():
            if len(table.columns) == 0:
                violations.append(Violation(
                    invariant_name=self.name,
                    severity=Severity.ERROR,
                    message=f"Table '{table.name}' has no columns",
                    details={"table": table.name}
                ))
        
        return violations


class TableNamingConvention(ComparisonBInvariant):
    """Verify tables follow Django's naming convention.
    
    Django typically names tables as 'app_modelname'. This invariant
    checks that all non-Django tables follow this pattern.
    """
    
    @property
    def name(self):
        return "Table Naming Convention"
    
    @property
    def description(self):
        return "Tables should follow Django naming convention (app_modelname)"
    
    def check(self, expected_schema, actual_schema):
        violations = []
        
        for table in actual_schema.all_tables():
            # Skip Django internal tables
            if table.name.startswith('django_') or table.name.startswith('auth_'):
                continue
            
            # Check if table name contains underscore (app_model pattern)
            if '_' not in table.name:
                violations.append(Violation(
                    invariant_name=self.name,
                    severity=Severity.INFO,
                    message=f"Table '{table.name}' doesn't follow Django naming convention",
                    details={
                        "table": table.name,
                        "expected_pattern": "app_modelname",
                    }
                ))
        
        return violations


class NoLegacyTables(ComparisonBInvariant):
    """Verify no tables with legacy/deprecated prefixes exist.
    
    This helps identify old tables that should have been removed.
    Customize the LEGACY_PREFIXES set for your project.
    """
    
    # Customize these for your project
    LEGACY_PREFIXES = {
        'old_',
        'legacy_',
        'temp_',
        'tmp_',
        'backup_',
        'deprecated_',
    }
    
    @property
    def name(self):
        return "No Legacy Tables"
    
    @property
    def description(self):
        return f"No tables with legacy prefixes ({', '.join(self.LEGACY_PREFIXES)}) should exist"
    
    def check(self, expected_schema, actual_schema):
        violations = []
        
        for table in actual_schema.all_tables():
            # Check if table starts with any legacy prefix
            for prefix in self.LEGACY_PREFIXES:
                if table.name.startswith(prefix):
                    violations.append(Violation(
                        invariant_name=self.name,
                        severity=Severity.WARNING,
                        message=f"Legacy table '{table.name}' still exists (prefix: {prefix})",
                        details={
                            "table": table.name,
                            "prefix": prefix,
                        }
                    ))
                    break  # Only report once per table
        
        return violations


class TableCountReasonable(ComparisonBInvariant):
    """Verify the number of tables is reasonable.
    
    This is a sanity check to detect issues like:
    - Too many tables (possible test pollution)
    - Too few tables (possible data loss)
    """
    
    # Customize these thresholds for your project
    MIN_TABLES = 1
    MAX_TABLES = 500
    
    @property
    def name(self):
        return "Table Count Reasonable"
    
    @property
    def description(self):
        return f"Number of tables should be between {self.MIN_TABLES} and {self.MAX_TABLES}"
    
    def check(self, expected_schema, actual_schema):
        violations = []
        
        # Count non-Django tables
        user_tables = [
            t for t in actual_schema.all_tables()
            if not t.name.startswith('django_') and not t.name.startswith('auth_')
        ]
        
        count = len(user_tables)
        
        if count < self.MIN_TABLES:
            violations.append(Violation(
                invariant_name=self.name,
                severity=Severity.ERROR,
                message=f"Too few tables: {count} (minimum: {self.MIN_TABLES})",
                details={"count": count, "min": self.MIN_TABLES}
            ))
        elif count > self.MAX_TABLES:
            violations.append(Violation(
                invariant_name=self.name,
                severity=Severity.WARNING,
                message=f"Too many tables: {count} (maximum: {self.MAX_TABLES})",
                details={"count": count, "max": self.MAX_TABLES}
            ))
        
        return violations
