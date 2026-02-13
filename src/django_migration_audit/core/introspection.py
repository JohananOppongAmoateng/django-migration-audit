"""
Live Database Schema Introspection

This module handles **Input 3** of the django-migration-audit architecture:
the live database schema (ground truth).

It introspects the actual database state via Django's connection introspection API,
providing the "actual" side for **Comparison B: Reality Check** (expected ↔ actual).

The core question this module helps answer:
"What actually exists in the database right now?"

This is the ground truth that both migration history and migration code must
ultimately match.
"""

from django.db import connections

from .state import ColumnState, SchemaState, TableState

DJANGO_INTERNAL_TABLE_PREFIXES = ("django_", "auth_", "sqlite_")


def is_internal_table(table_name: str) -> bool:
    """Check if a table is a Django internal table."""
    return table_name.startswith(DJANGO_INTERNAL_TABLE_PREFIXES)


def introspect_schema(using: str = "default") -> SchemaState:
    """
    Introspect the live database schema and return a SchemaState.

    Args:
        using: Database alias to introspect

    Returns:
        SchemaState representing the actual database schema
    """
    connection = connections[using]

    with connection.cursor() as cursor:
        introspection = connection.introspection
        table_names = introspection.table_names(cursor)

        tables = {}
        for table_name in table_names:
            if is_internal_table(table_name):
                continue

            columns = _introspect_table_columns(cursor, introspection, table_name)
            tables[table_name] = TableState(name=table_name, columns=columns)

    return SchemaState(tables=tables)


def _introspect_table_columns(cursor, introspection, table_name: str) -> dict:
    """
    Introspect columns for a specific table.

    Returns:
        Dictionary mapping column names to ColumnState objects
    """
    table_description = introspection.get_table_description(cursor, table_name)

    columns = {}
    for row in table_description:
        col_name = row.name
        col_type = _normalize_db_type(row.type_code, introspection, row)
        col_null = row.null_ok
        col_default = row.default

        columns[col_name] = ColumnState(
            name=col_name,
            db_type=col_type,
            null=col_null,
            default=str(col_default) if col_default is not None else None,
        )

    return columns


def _normalize_db_type(type_code, introspection, description=None) -> str:
    """
    Normalize database type codes to consistent string representations.

    Different databases use different type codes, so we normalize them
    to a consistent format for comparison.
    """
    # Get the data type name from the introspection
    # Pass the full FieldInfo row as description so backends (e.g. SQLite)
    # can inspect attributes like pk to distinguish AutoField vs IntegerField.
    try:
        data_type = introspection.get_field_type(type_code, description)
    except (KeyError, AttributeError):
        data_type = "unknown"

    # Normalize common variations
    # Note: ForeignKey, OneToOneField, EmailField, URLField are not included
    # because Django's introspection returns storage-level types (IntegerField,
    # CharField), not logical types.
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
    }

    return type_map.get(data_type, data_type.lower())
