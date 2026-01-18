"""
Canonical Schema State Representations

This module defines the canonical schema representations used for comparisons
in django-migration-audit.

These data structures are used by:
- **Extractor** (builds expected schema from migration operations)
- **Introspection** (reads actual schema from live database)

By using the same canonical format for both expected and actual schemas,
we enable apples-to-apples comparison in **Comparison B: Reality Check**.

The state classes represent:
- ColumnState: A single database column
- TableState: A database table with its columns
- SchemaState: The entire database schema
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


# ----------------------------
# Column
# ----------------------------

@dataclass(frozen=True)
class ColumnState:
    """
    Canonical representation of a database column.
    """
    name: str
    db_type: str
    null: bool
    default: Optional[str] = None

    def identity(self) -> Tuple[str, str]:
        """
        Identity tuple for comparison across sources.
        """
        return (self.name, self.db_type)


# ----------------------------
# Table
# ----------------------------

@dataclass(frozen=True)
class TableState:
    """
    Canonical representation of a database table.
    """
    name: str
    columns: Dict[str, ColumnState] = field(default_factory=dict)

    def has_column(self, column_name: str) -> bool:
        return column_name in self.columns

    def column(self, column_name: str) -> ColumnState:
        return self.columns[column_name]




@dataclass(frozen=True)
class SchemaState:
    """
    Canonical representation of an entire database schema.
    """
    tables: Dict[str, TableState] = field(default_factory=dict)

    def has_table(self, table_name: str) -> bool:
        return table_name in self.tables

    def table(self, table_name: str) -> TableState:
        return self.tables[table_name]

    def all_tables(self):
        return self.tables.values()


# ----------------------------
# ProjectState (mutable builder)
# ----------------------------

class ProjectState:
    """
    Mutable state builder for constructing expected schema from migration operations.
    
    This is used by the extractor to replay migration operations and build
    the expected schema state.
    """

    def __init__(self):
        self._tables: Dict[str, Dict[str, any]] = {}

    def create_table(self, app_label: str, name: str, fields: list, options: dict):
        """Create a new table from a CreateModel operation."""
        table_name = self._get_table_name(app_label, name, options)
        columns = {}
        
        for field_name, field_obj in fields:
            columns[field_name] = ColumnState(
                name=field_name,
                db_type=self._get_db_type(field_obj),
                null=field_obj.null,
                default=self._get_default(field_obj),
            )
        
        self._tables[table_name] = {
            'name': table_name,
            'columns': columns,
        }

    def drop_table(self, app_label: str, name: str):
        """Drop a table from a DeleteModel operation."""
        # Find and remove the table (need to search by app_label + name)
        table_name = self._find_table(app_label, name)
        if table_name:
            del self._tables[table_name]

    def add_column(self, app_label: str, model_name: str, field: any):
        """Add a column from an AddField operation."""
        table_name = self._find_table(app_label, model_name)
        if table_name:
            field_name = field.name
            self._tables[table_name]['columns'][field_name] = ColumnState(
                name=field_name,
                db_type=self._get_db_type(field),
                null=field.null,
                default=self._get_default(field),
            )

    def remove_column(self, app_label: str, model_name: str, name: str):
        """Remove a column from a RemoveField operation."""
        table_name = self._find_table(app_label, model_name)
        if table_name and name in self._tables[table_name]['columns']:
            del self._tables[table_name]['columns'][name]

    def alter_column(self, app_label: str, model_name: str, field: any):
        """Alter a column from an AlterField operation."""
        table_name = self._find_table(app_label, model_name)
        if table_name:
            field_name = field.name
            self._tables[table_name]['columns'][field_name] = ColumnState(
                name=field_name,
                db_type=self._get_db_type(field),
                null=field.null,
                default=self._get_default(field),
            )

    def add_constraint(self, app_label: str, model_name: str, constraint: any):
        """Add a constraint (placeholder for future implementation)."""
        pass

    def remove_constraint(self, app_label: str, model_name: str, name: str):
        """Remove a constraint (placeholder for future implementation)."""
        pass

    def add_index(self, app_label: str, model_name: str, index: any):
        """Add an index (placeholder for future implementation)."""
        pass

    def remove_index(self, app_label: str, model_name: str, name: str):
        """Remove an index (placeholder for future implementation)."""
        pass

    def to_schema_state(self) -> SchemaState:
        """Convert the mutable ProjectState to an immutable SchemaState."""
        tables = {}
        for table_name, table_data in self._tables.items():
            tables[table_name] = TableState(
                name=table_data['name'],
                columns=table_data['columns'].copy(),
            )
        return SchemaState(tables=tables)

    # Helper methods

    def _get_table_name(self, app_label: str, model_name: str, options: dict) -> str:
        """Get the database table name for a model."""
        db_table = options.get('db_table')
        if db_table:
            return db_table
        return f"{app_label}_{model_name.lower()}"

    def _find_table(self, app_label: str, model_name: str) -> Optional[str]:
        """Find a table by app_label and model_name."""
        # Simple approach: look for app_label_modelname pattern
        expected_name = f"{app_label}_{model_name.lower()}"
        if expected_name in self._tables:
            return expected_name
        # Fallback: search all tables
        for table_name in self._tables:
            if table_name.endswith(f"_{model_name.lower()}"):
                return table_name
        return None

    def _get_db_type(self, field: any) -> str:
        """Get the database type for a field."""
        # Simplified type mapping
        field_type = type(field).__name__
        type_map = {
            'AutoField': 'integer',
            'BigAutoField': 'bigint',
            'IntegerField': 'integer',
            'BigIntegerField': 'bigint',
            'CharField': 'varchar',
            'TextField': 'text',
            'BooleanField': 'boolean',
            'DateField': 'date',
            'DateTimeField': 'timestamp',
            'DecimalField': 'numeric',
            'FloatField': 'double precision',
            'EmailField': 'varchar',
            'URLField': 'varchar',
            'ForeignKey': 'integer',
            'OneToOneField': 'integer',
        }
        return type_map.get(field_type, 'unknown')

    def _get_default(self, field: any) -> Optional[str]:
        """Get the default value for a field."""
        if hasattr(field, 'default') and field.default is not None:
            return str(field.default)
        return None

