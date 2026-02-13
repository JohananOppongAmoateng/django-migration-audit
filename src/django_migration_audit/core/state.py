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

from django.db.models.fields import NOT_PROVIDED
from django.db.models.fields.related import ForeignKey, OneToOneField

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
        self._model_to_table: Dict[tuple, str] = {}  # (app_label, model_name_lower) -> table_name

    def create_table(self, app_label: str, name: str, fields: list, options: dict):
        """Create a new table from a CreateModel operation."""
        table_name = self._get_table_name(app_label, name, options)
        columns = {}

        for field_name, field_obj in fields:
            col_name = self._get_column_name(field_name, field_obj)
            columns[col_name] = ColumnState(
                name=col_name,
                db_type=self._get_db_type(field_obj),
                null=field_obj.null,
                default=self._get_default(field_obj),
            )

        self._tables[table_name] = {
            "name": table_name,
            "columns": columns,
        }
        self._model_to_table[(app_label, name.lower())] = table_name

    def drop_table(self, app_label: str, name: str):
        """Drop a table from a DeleteModel operation."""
        table_name = self._find_table(app_label, name)
        if table_name:
            del self._tables[table_name]
            self._model_to_table.pop((app_label, name.lower()), None)

    def add_column(self, app_label: str, model_name: str, field: any):
        """Add a column from an AddField operation."""
        table_name = self._find_table(app_label, model_name)
        if table_name:
            col_name = self._get_column_name(field.name, field)
            self._tables[table_name]["columns"][col_name] = ColumnState(
                name=col_name,
                db_type=self._get_db_type(field),
                null=field.null,
                default=self._get_default(field),
            )

    def remove_column(self, app_label: str, model_name: str, name: str):
        """Remove a column from a RemoveField operation."""
        table_name = self._find_table(app_label, model_name)
        if table_name:
            columns = self._tables[table_name]["columns"]
            # RemoveField provides the field name, but the column may have _id suffix (FK/O2O)
            if name in columns:
                del columns[name]
            elif f"{name}_id" in columns:
                del columns[f"{name}_id"]

    def alter_column(self, app_label: str, model_name: str, field: any):
        """Alter a column from an AlterField operation."""
        table_name = self._find_table(app_label, model_name)
        if table_name:
            col_name = self._get_column_name(field.name, field)
            self._tables[table_name]["columns"][col_name] = ColumnState(
                name=col_name,
                db_type=self._get_db_type(field),
                null=field.null,
                default=self._get_default(field),
            )

    def rename_table(self, app_label: str, model_name: str, new_table_name: str):
        """Rename a table from an AlterModelTable operation."""
        old_table_name = self._find_table(app_label, model_name)
        if old_table_name and new_table_name:
            table_data = self._tables.pop(old_table_name)
            table_data["name"] = new_table_name
            self._tables[new_table_name] = table_data
            self._model_to_table[(app_label, model_name.lower())] = new_table_name

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
                name=table_data["name"],
                columns=table_data["columns"].copy(),
            )
        return SchemaState(tables=tables)

    # Helper methods

    def _get_table_name(self, app_label: str, model_name: str, options: dict) -> str:
        """Get the database table name for a model."""
        db_table = options.get("db_table")
        if db_table:
            return db_table
        return f"{app_label}_{model_name.lower()}"

    def _find_table(self, app_label: str, model_name: str) -> Optional[str]:
        """Find a table by app_label and model_name."""
        table_name = self._model_to_table.get((app_label, model_name.lower()))
        if table_name and table_name in self._tables:
            return table_name
        return None

    def _get_column_name(self, field_name: str, field_obj: any) -> str:
        """Get the actual DB column name for a field.

        ForeignKey and OneToOneField create columns with an '_id' suffix
        unless db_column is explicitly set.
        """
        if isinstance(field_obj, (ForeignKey, OneToOneField)):
            db_column = getattr(field_obj, "db_column", None)
            if db_column:
                return db_column
            return f"{field_name}_id"
        return field_name

    def _get_db_type(self, field: any) -> str:
        """Get the database type for a field."""
        # Simplified type mapping
        field_type = type(field).__name__
        type_map = {
            "AutoField": "integer",
            "BigAutoField": "bigint",
            "IntegerField": "integer",
            "BigIntegerField": "bigint",
            "CharField": "varchar",
            "TextField": "text",
            "BooleanField": "boolean",
            "DateField": "date",
            "DateTimeField": "timestamp",
            "DecimalField": "numeric",
            "FloatField": "double precision",
            "EmailField": "varchar",
            "URLField": "varchar",
            "ForeignKey": "integer",
            "OneToOneField": "integer",
        }
        return type_map.get(field_type, "unknown")

    def _get_default(self, field: any) -> Optional[str]:
        """Get the default value for a field."""
        if (
            hasattr(field, "default")
            and field.default is not NOT_PROVIDED
            and field.default is not None
        ):
            return str(field.default)
        return None
