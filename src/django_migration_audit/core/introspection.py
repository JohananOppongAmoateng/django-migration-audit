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

from .state import ColumnState, ConstraintState, IndexState, SchemaState, TableState

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
            indexes, constraints = _introspect_indexes_and_constraints(
                cursor, introspection, table_name
            )
            tables[table_name] = TableState(
                name=table_name,
                columns=columns,
                indexes=indexes,
                constraints=constraints,
            )

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

    # Normalise the Django field-type name returned by get_field_type() to
    # the same canonical strings used in state.py's _get_db_type().
    # This lets Comparison B compare apples to apples across all backends.
    #
    # Note: ForeignKey / OneToOneField are NOT listed here because
    # Django introspection returns the storage-level type (IntegerField /
    # BigIntegerField), not the logical relation type.
    type_map = {
        # Auto / integer
        "AutoField": "integer",
        "BigAutoField": "bigint",
        "SmallAutoField": "integer",
        "IntegerField": "integer",
        "BigIntegerField": "bigint",
        "SmallIntegerField": "integer",
        "PositiveIntegerField": "integer",
        "PositiveSmallIntegerField": "integer",
        # Character / text
        "CharField": "varchar",
        "TextField": "text",
        # Boolean
        "BooleanField": "boolean",
        "NullBooleanField": "boolean",
        # Date / time
        "DateField": "date",
        "DateTimeField": "timestamp",
        "TimeField": "time",
        # Numeric
        "DecimalField": "numeric",
        "FloatField": "double precision",
    }

    return type_map.get(data_type, data_type.lower())


def _introspect_indexes_and_constraints(cursor, introspection, table_name: str):
    """
    Introspect indexes and constraints for a specific table.

    Uses Django's get_constraints() which returns a unified dict covering:
    - Primary key constraints (skipped)
    - Foreign key constraints (skipped — column-level checks cover these)
    - Unique constraints  → ConstraintState(type='unique')
    - Check constraints   → ConstraintState(type='check')
    - Plain indexes       → IndexState

    Returns:
        (indexes, constraints) — dicts mapping name → IndexState/ConstraintState
    """
    try:
        raw = introspection.get_constraints(cursor, table_name)
    except Exception:
        return {}, {}

    indexes = {}
    constraints = {}

    for name, info in raw.items():
        if info.get("primary_key"):
            continue
        if info.get("foreign_key") is not None:
            continue

        columns = tuple(info.get("columns") or [])

        if info.get("check"):
            constraints[name] = ConstraintState(
                name=name, constraint_type="check", columns=columns
            )
        elif info.get("unique"):
            constraints[name] = ConstraintState(
                name=name, constraint_type="unique", columns=columns
            )
        elif info.get("index"):
            indexes[name] = IndexState(name=name, columns=columns)

    return indexes, constraints
