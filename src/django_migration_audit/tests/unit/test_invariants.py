import pytest
from django_migration_audit.core.loader import MigrationNode
from django_migration_audit.core.state import (
    ColumnState,
    ConstraintState,
    IndexState,
    SchemaState,
    TableState,
)
from django_migration_audit.invariants.base import (
    Violation,
    Severity,
    NoMissingMigrationFiles,
    SquashMigrationsProperlyReplaced,
    AllExpectedTablesExist,
    NoUnexpectedTables,
    AllExpectedColumnsExist,
)
from django_migration_audit.invariants.columns import (
    NoUnexpectedColumns,
    ColumnNullabilityMatches,
    NoMissingPrimaryKeys,
)
from django_migration_audit.invariants.tables import (
    NoEmptyTables,
    TableNamingConvention,
    NoLegacyTables,
    TableCountReasonable,
)


# ----------------------------
# Comparison A Invariants Tests
# ----------------------------


def test_no_missing_migration_files_pass():
    """Test NoMissingMigrationFiles when all files exist."""
    from django_migration_audit.core.loader import MigrationHistory

    invariant = NoMissingMigrationFiles()

    history = MigrationHistory(
        applied=set(),
        graph_nodes=set(),
        missing_files=set(),  # No missing files
        squashed_replacements=set(),
        plan=[],
    )

    violations = invariant.check(migration_history=history)
    assert len(violations) == 0


def test_no_missing_migration_files_fail():
    """Test NoMissingMigrationFiles when files are missing."""
    from django_migration_audit.core.loader import MigrationHistory

    invariant = NoMissingMigrationFiles()

    missing = MigrationNode(app="myapp", name="0001_initial")
    history = MigrationHistory(
        applied={missing},
        graph_nodes=set(),
        missing_files={missing},
        squashed_replacements=set(),
        plan=[],
    )

    violations = invariant.check(migration_history=history)
    assert len(violations) == 1
    assert violations[0].severity == Severity.ERROR
    assert "myapp.0001_initial" in violations[0].message


def test_squash_migrations_properly_replaced_pass():
    """Test SquashMigrationsProperlyReplaced when squashes are correct."""
    from django_migration_audit.core.loader import MigrationHistory

    invariant = SquashMigrationsProperlyReplaced()

    replaced = MigrationNode(app="myapp", name="0001_initial")
    history = MigrationHistory(
        applied=set(),  # Replaced migration not applied
        graph_nodes=set(),
        missing_files=set(),
        squashed_replacements={replaced},
        plan=[],
    )

    violations = invariant.check(migration_history=history)
    assert len(violations) == 0


def test_squash_migrations_properly_replaced_fail():
    """Test SquashMigrationsProperlyReplaced when replaced migration still applied."""
    from django_migration_audit.core.loader import MigrationHistory

    invariant = SquashMigrationsProperlyReplaced()

    replaced = MigrationNode(app="myapp", name="0001_initial")
    history = MigrationHistory(
        applied={replaced},  # Replaced migration still applied!
        graph_nodes=set(),
        missing_files=set(),
        squashed_replacements={replaced},
        plan=[],
    )

    violations = invariant.check(migration_history=history)
    assert len(violations) == 1
    assert violations[0].severity == Severity.WARNING
    assert "myapp.0001_initial" in violations[0].message


# ----------------------------
# Comparison B Invariants Tests
# ----------------------------


def test_all_expected_tables_exist_pass():
    """Test AllExpectedTablesExist when all tables exist."""
    invariant = AllExpectedTablesExist()

    expected = SchemaState(
        tables={
            "users": TableState(name="users"),
            "posts": TableState(name="posts"),
        }
    )

    actual = SchemaState(
        tables={
            "users": TableState(name="users"),
            "posts": TableState(name="posts"),
        }
    )

    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 0


def test_all_expected_tables_exist_fail():
    """Test AllExpectedTablesExist when a table is missing."""
    invariant = AllExpectedTablesExist()

    expected = SchemaState(
        tables={
            "users": TableState(name="users"),
            "posts": TableState(name="posts"),
        }
    )

    actual = SchemaState(
        tables={
            "users": TableState(name="users"),
            # 'posts' is missing!
        }
    )

    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 1
    assert violations[0].severity == Severity.ERROR
    assert "posts" in violations[0].message


def test_no_unexpected_tables_pass():
    """Test NoUnexpectedTables when no extra tables exist."""
    invariant = NoUnexpectedTables()

    expected = SchemaState(
        tables={
            "users": TableState(name="users"),
        }
    )

    actual = SchemaState(
        tables={
            "users": TableState(name="users"),
        }
    )

    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 0


def test_no_unexpected_tables_fail():
    """Test NoUnexpectedTables when extra tables exist."""
    invariant = NoUnexpectedTables()

    expected = SchemaState(
        tables={
            "users": TableState(name="users"),
        }
    )

    actual = SchemaState(
        tables={
            "users": TableState(name="users"),
            "manual_table": TableState(name="manual_table"),  # Unexpected!
        }
    )

    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 1
    assert violations[0].severity == Severity.WARNING
    assert "manual_table" in violations[0].message


def test_all_expected_columns_exist_pass():
    """Test AllExpectedColumnsExist when all columns match."""
    invariant = AllExpectedColumnsExist()

    expected = SchemaState(
        tables={
            "users": TableState(
                name="users",
                columns={
                    "id": ColumnState("id", "integer", False),
                    "name": ColumnState("name", "varchar", False),
                },
            ),
        }
    )

    actual = SchemaState(
        tables={
            "users": TableState(
                name="users",
                columns={
                    "id": ColumnState("id", "integer", False),
                    "name": ColumnState("name", "varchar", False),
                },
            ),
        }
    )

    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 0


def test_all_expected_columns_exist_missing_column():
    """Test AllExpectedColumnsExist when a column is missing."""
    invariant = AllExpectedColumnsExist()

    expected = SchemaState(
        tables={
            "users": TableState(
                name="users",
                columns={
                    "id": ColumnState("id", "integer", False),
                    "name": ColumnState("name", "varchar", False),
                },
            ),
        }
    )

    actual = SchemaState(
        tables={
            "users": TableState(
                name="users",
                columns={
                    "id": ColumnState("id", "integer", False),
                    # 'name' is missing!
                },
            ),
        }
    )

    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 1
    assert violations[0].severity == Severity.ERROR
    assert "name" in violations[0].message


def test_all_expected_columns_exist_wrong_type():
    """Test AllExpectedColumnsExist when a column has wrong type."""
    invariant = AllExpectedColumnsExist()

    expected = SchemaState(
        tables={
            "users": TableState(
                name="users",
                columns={
                    "id": ColumnState("id", "integer", False),
                },
            ),
        }
    )

    actual = SchemaState(
        tables={
            "users": TableState(
                name="users",
                columns={
                    "id": ColumnState("id", "bigint", False),  # Wrong type!
                },
            ),
        }
    )

    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 1
    assert violations[0].severity == Severity.ERROR
    assert "wrong type" in violations[0].message.lower()


def test_all_expected_columns_exist_skips_missing_tables():
    """Test AllExpectedColumnsExist skips tables that don't exist."""
    invariant = AllExpectedColumnsExist()

    expected = SchemaState(
        tables={
            "users": TableState(
                name="users",
                columns={
                    "id": ColumnState("id", "integer", False),
                },
            ),
        }
    )

    actual = SchemaState(tables={})  # No tables at all

    # Should not raise errors for columns when table is missing
    # (that's handled by AllExpectedTablesExist)
    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 0


# ----------------------------
# Violation Tests
# ----------------------------


def test_violation_str():
    """Test Violation string representation."""
    violation = Violation(
        invariant_name="Test Invariant",
        severity=Severity.ERROR,
        message="Something went wrong",
        details={"key": "value"},
    )

    result = str(violation)
    assert "ERROR" in result
    assert "Test Invariant" in result
    assert "Something went wrong" in result


def test_violation_severity_enum():
    """Test Severity enum values."""
    assert Severity.ERROR.value == "error"
    assert Severity.WARNING.value == "warning"
    assert Severity.INFO.value == "info"


# ----------------------------
# NoUnexpectedColumns Tests
# ----------------------------


def test_no_unexpected_columns_pass():
    """Test NoUnexpectedColumns when columns match."""
    invariant = NoUnexpectedColumns()

    schema = SchemaState(
        tables={
            "users": TableState(
                name="users",
                columns={
                    "id": ColumnState("id", "integer", False),
                    "name": ColumnState("name", "varchar", False),
                },
            ),
        }
    )

    violations = invariant.check(expected_schema=schema, actual_schema=schema)
    assert len(violations) == 0


def test_no_unexpected_columns_fail():
    """Test NoUnexpectedColumns when extra column exists."""
    invariant = NoUnexpectedColumns()

    expected = SchemaState(
        tables={
            "users": TableState(
                name="users",
                columns={
                    "id": ColumnState("id", "integer", False),
                },
            ),
        }
    )

    actual = SchemaState(
        tables={
            "users": TableState(
                name="users",
                columns={
                    "id": ColumnState("id", "integer", False),
                    "extra": ColumnState("extra", "text", True),
                },
            ),
        }
    )

    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 1
    assert "extra" in violations[0].message


# ----------------------------
# ColumnNullabilityMatches Tests
# ----------------------------


def test_column_nullability_matches_pass():
    """Test ColumnNullabilityMatches when nullability matches."""
    invariant = ColumnNullabilityMatches()

    schema = SchemaState(
        tables={
            "users": TableState(
                name="users",
                columns={
                    "id": ColumnState("id", "integer", False),
                    "bio": ColumnState("bio", "text", True),
                },
            ),
        }
    )

    violations = invariant.check(expected_schema=schema, actual_schema=schema)
    assert len(violations) == 0


def test_column_nullability_matches_fail():
    """Test ColumnNullabilityMatches when nullability differs."""
    invariant = ColumnNullabilityMatches()

    expected = SchemaState(
        tables={
            "users": TableState(
                name="users",
                columns={
                    "name": ColumnState("name", "varchar", False),
                },
            ),
        }
    )

    actual = SchemaState(
        tables={
            "users": TableState(
                name="users",
                columns={
                    "name": ColumnState("name", "varchar", True),  # Mismatch!
                },
            ),
        }
    )

    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 1
    assert "nullability" in violations[0].message.lower()


# ----------------------------
# NoMissingPrimaryKeys Tests
# ----------------------------


def test_no_missing_primary_keys_pass():
    """Test NoMissingPrimaryKeys when all tables have id."""
    invariant = NoMissingPrimaryKeys()

    actual = SchemaState(
        tables={
            "myapp_user": TableState(
                name="myapp_user",
                columns={
                    "id": ColumnState("id", "integer", False),
                    "name": ColumnState("name", "varchar", False),
                },
            ),
        }
    )

    violations = invariant.check(expected_schema=actual, actual_schema=actual)
    assert len(violations) == 0


def test_no_missing_primary_keys_fail():
    """Test NoMissingPrimaryKeys when a table has no pk."""
    invariant = NoMissingPrimaryKeys()

    actual = SchemaState(
        tables={
            "myapp_params": TableState(
                name="myapp_params",
                columns={
                    "key": ColumnState("key", "varchar", False),
                    "value": ColumnState("value", "text", True),
                },
            ),
        }
    )

    violations = invariant.check(expected_schema=actual, actual_schema=actual)
    assert len(violations) == 1
    assert "missing a primary key" in violations[0].message


# ----------------------------
# NoEmptyTables Tests
# ----------------------------


def test_no_empty_tables_pass():
    """Test NoEmptyTables when all tables have columns."""
    invariant = NoEmptyTables()

    actual = SchemaState(
        tables={
            "myapp_user": TableState(
                name="myapp_user",
                columns={"id": ColumnState("id", "integer", False)},
            ),
        }
    )

    violations = invariant.check(expected_schema=actual, actual_schema=actual)
    assert len(violations) == 0


def test_no_empty_tables_fail():
    """Test NoEmptyTables when a table has no columns."""
    invariant = NoEmptyTables()

    actual = SchemaState(
        tables={
            "myapp_empty": TableState(name="myapp_empty", columns={}),
        }
    )

    violations = invariant.check(expected_schema=actual, actual_schema=actual)
    assert len(violations) == 1
    assert "no columns" in violations[0].message


# ----------------------------
# TableNamingConvention Tests
# ----------------------------


def test_table_naming_convention_pass():
    """Test TableNamingConvention with proper app_model naming."""
    invariant = TableNamingConvention()

    actual = SchemaState(
        tables={
            "myapp_user": TableState(name="myapp_user"),
        }
    )

    violations = invariant.check(expected_schema=actual, actual_schema=actual)
    assert len(violations) == 0


def test_table_naming_convention_fail():
    """Test TableNamingConvention with non-standard naming."""
    invariant = TableNamingConvention()

    actual = SchemaState(
        tables={
            "users": TableState(name="users"),  # No underscore
        }
    )

    violations = invariant.check(expected_schema=actual, actual_schema=actual)
    assert len(violations) == 1
    assert "naming convention" in violations[0].message.lower()


# ----------------------------
# NoLegacyTables Tests
# ----------------------------


def test_no_legacy_tables_pass():
    """Test NoLegacyTables when no legacy tables exist."""
    invariant = NoLegacyTables()

    actual = SchemaState(
        tables={
            "myapp_user": TableState(name="myapp_user"),
        }
    )

    violations = invariant.check(expected_schema=actual, actual_schema=actual)
    assert len(violations) == 0


def test_no_legacy_tables_fail():
    """Test NoLegacyTables when legacy tables exist."""
    invariant = NoLegacyTables()

    actual = SchemaState(
        tables={
            "old_users": TableState(name="old_users"),
            "temp_data": TableState(name="temp_data"),
        }
    )

    violations = invariant.check(expected_schema=actual, actual_schema=actual)
    assert len(violations) == 2


# ----------------------------
# TableCountReasonable Tests
# ----------------------------


def test_table_count_reasonable_pass():
    """Test TableCountReasonable with reasonable count."""
    invariant = TableCountReasonable()

    actual = SchemaState(
        tables={
            "myapp_user": TableState(name="myapp_user"),
        }
    )

    violations = invariant.check(expected_schema=actual, actual_schema=actual)
    assert len(violations) == 0


def test_table_count_reasonable_too_few():
    """Test TableCountReasonable with zero user tables."""
    invariant = TableCountReasonable()

    actual = SchemaState(tables={})

    violations = invariant.check(expected_schema=actual, actual_schema=actual)
    assert len(violations) == 1
    assert "too few" in violations[0].message.lower()


# ----------------------------
# AllExpectedIndexesExist Tests
# ----------------------------


def test_all_expected_indexes_exist_pass():
    """Test AllExpectedIndexesExist when all indexes are present."""
    from django_migration_audit.invariants.constraints import AllExpectedIndexesExist

    invariant = AllExpectedIndexesExist()

    idx = IndexState(name="post_title_idx", columns=("title",))
    table = TableState(name="myapp_post", indexes={"post_title_idx": idx})
    schema = SchemaState(tables={"myapp_post": table})

    violations = invariant.check(expected_schema=schema, actual_schema=schema)
    assert len(violations) == 0


def test_all_expected_indexes_exist_fail():
    """Test AllExpectedIndexesExist when an expected index is missing from the DB."""
    from django_migration_audit.invariants.constraints import AllExpectedIndexesExist

    invariant = AllExpectedIndexesExist()

    idx = IndexState(name="post_title_idx", columns=("title",))
    expected = SchemaState(
        tables={"myapp_post": TableState(name="myapp_post", indexes={"post_title_idx": idx})}
    )
    actual = SchemaState(
        tables={"myapp_post": TableState(name="myapp_post")}  # no indexes
    )

    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 1
    assert violations[0].severity == Severity.ERROR
    assert "post_title_idx" in violations[0].message


def test_all_expected_indexes_exist_skips_missing_tables():
    """Test AllExpectedIndexesExist skips tables that don't exist in actual."""
    from django_migration_audit.invariants.constraints import AllExpectedIndexesExist

    invariant = AllExpectedIndexesExist()

    idx = IndexState(name="post_title_idx", columns=("title",))
    expected = SchemaState(
        tables={"myapp_post": TableState(name="myapp_post", indexes={"post_title_idx": idx})}
    )
    actual = SchemaState(tables={})  # table is missing entirely

    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 0  # AllExpectedTablesExist handles this


# ----------------------------
# AllExpectedConstraintsExist Tests
# ----------------------------


def test_all_expected_constraints_exist_pass():
    """Test AllExpectedConstraintsExist when all constraints are present."""
    from django_migration_audit.invariants.constraints import AllExpectedConstraintsExist

    invariant = AllExpectedConstraintsExist()

    con = ConstraintState(name="post_slug_uniq", constraint_type="unique", columns=("slug",))
    table = TableState(name="myapp_post", constraints={"post_slug_uniq": con})
    schema = SchemaState(tables={"myapp_post": table})

    violations = invariant.check(expected_schema=schema, actual_schema=schema)
    assert len(violations) == 0


def test_all_expected_constraints_exist_fail():
    """Test AllExpectedConstraintsExist when an expected constraint is missing."""
    from django_migration_audit.invariants.constraints import AllExpectedConstraintsExist

    invariant = AllExpectedConstraintsExist()

    con = ConstraintState(name="post_slug_uniq", constraint_type="unique", columns=("slug",))
    expected = SchemaState(
        tables={"myapp_post": TableState(name="myapp_post", constraints={"post_slug_uniq": con})}
    )
    actual = SchemaState(
        tables={"myapp_post": TableState(name="myapp_post")}  # no constraints
    )

    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 1
    assert violations[0].severity == Severity.ERROR
    assert "post_slug_uniq" in violations[0].message
    assert "unique" in violations[0].message


def test_all_expected_constraints_check_type():
    """Test AllExpectedConstraintsExist reports the constraint type in the message."""
    from django_migration_audit.invariants.constraints import AllExpectedConstraintsExist

    invariant = AllExpectedConstraintsExist()

    con = ConstraintState(name="rating_range", constraint_type="check", columns=())
    expected = SchemaState(
        tables={"myapp_review": TableState(name="myapp_review", constraints={"rating_range": con})}
    )
    actual = SchemaState(tables={"myapp_review": TableState(name="myapp_review")})

    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 1
    assert "check" in violations[0].message


def test_all_expected_constraints_exist_skips_missing_tables():
    """Test AllExpectedConstraintsExist skips tables missing from actual."""
    from django_migration_audit.invariants.constraints import AllExpectedConstraintsExist

    invariant = AllExpectedConstraintsExist()

    con = ConstraintState(name="post_slug_uniq", constraint_type="unique", columns=("slug",))
    expected = SchemaState(
        tables={"myapp_post": TableState(name="myapp_post", constraints={"post_slug_uniq": con})}
    )
    actual = SchemaState(tables={})

    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 0


# ----------------------------
# NoUnexpectedIndexes Tests
# ----------------------------


def test_no_unexpected_indexes_pass():
    """Test NoUnexpectedIndexes when DB indexes match migrations exactly."""
    from django_migration_audit.invariants.constraints import NoUnexpectedIndexes

    invariant = NoUnexpectedIndexes()

    idx = IndexState(name="post_title_idx", columns=("title",))
    table = TableState(name="myapp_post", indexes={"post_title_idx": idx})
    schema = SchemaState(tables={"myapp_post": table})

    violations = invariant.check(expected_schema=schema, actual_schema=schema)
    assert len(violations) == 0


def test_no_unexpected_indexes_fail():
    """Test NoUnexpectedIndexes when DB has an index not in migrations."""
    from django_migration_audit.invariants.constraints import NoUnexpectedIndexes

    invariant = NoUnexpectedIndexes()

    expected = SchemaState(
        tables={"myapp_post": TableState(name="myapp_post")}  # no indexes in migrations
    )
    extra_idx = IndexState(name="manual_idx", columns=("title",))
    actual = SchemaState(
        tables={"myapp_post": TableState(name="myapp_post", indexes={"manual_idx": extra_idx})}
    )

    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 1
    assert violations[0].severity == Severity.WARNING
    assert "manual_idx" in violations[0].message
    assert "not defined in migrations" in violations[0].message


def test_no_unexpected_indexes_skips_unknown_tables():
    """Test NoUnexpectedIndexes skips tables not in expected schema."""
    from django_migration_audit.invariants.constraints import NoUnexpectedIndexes

    invariant = NoUnexpectedIndexes()

    expected = SchemaState(tables={})
    extra_idx = IndexState(name="manual_idx", columns=("col",))
    actual = SchemaState(
        tables={"myapp_post": TableState(name="myapp_post", indexes={"manual_idx": extra_idx})}
    )

    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 0  # NoUnexpectedTables handles the missing table


# ----------------------------
# NoUnexpectedConstraints Tests
# ----------------------------


def test_no_unexpected_constraints_pass():
    """Test NoUnexpectedConstraints when DB constraints match migrations exactly."""
    from django_migration_audit.invariants.constraints import NoUnexpectedConstraints

    invariant = NoUnexpectedConstraints()

    con = ConstraintState(name="post_slug_uniq", constraint_type="unique", columns=("slug",))
    table = TableState(name="myapp_post", constraints={"post_slug_uniq": con})
    schema = SchemaState(tables={"myapp_post": table})

    violations = invariant.check(expected_schema=schema, actual_schema=schema)
    assert len(violations) == 0


def test_no_unexpected_constraints_fail():
    """Test NoUnexpectedConstraints when DB has a constraint not in migrations."""
    from django_migration_audit.invariants.constraints import NoUnexpectedConstraints

    invariant = NoUnexpectedConstraints()

    expected = SchemaState(
        tables={"myapp_post": TableState(name="myapp_post")}  # no constraints in migrations
    )
    extra_con = ConstraintState(name="manual_uniq", constraint_type="unique", columns=("slug",))
    actual = SchemaState(
        tables={
            "myapp_post": TableState(name="myapp_post", constraints={"manual_uniq": extra_con})
        }
    )

    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 1
    assert violations[0].severity == Severity.WARNING
    assert "manual_uniq" in violations[0].message
    assert "unique" in violations[0].message
    assert "not defined in migrations" in violations[0].message


def test_no_unexpected_constraints_skips_unknown_tables():
    """Test NoUnexpectedConstraints skips tables not in expected schema."""
    from django_migration_audit.invariants.constraints import NoUnexpectedConstraints

    invariant = NoUnexpectedConstraints()

    expected = SchemaState(tables={})
    extra_con = ConstraintState(name="manual_uniq", constraint_type="unique", columns=("slug",))
    actual = SchemaState(
        tables={
            "myapp_post": TableState(name="myapp_post", constraints={"manual_uniq": extra_con})
        }
    )

    violations = invariant.check(expected_schema=expected, actual_schema=actual)
    assert len(violations) == 0  # NoUnexpectedTables handles the missing table
