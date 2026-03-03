"""Unit tests for the audit_migrations management command."""

from django_migration_audit.invariants.base import (
    AllExpectedTablesExist,
    NoUnexpectedTables,
    SquashMigrationsProperlyReplaced,
)
from django_migration_audit.management.commands.audit_migrations import Command


def _make_command(skip):
    cmd = Command()
    cmd.skip_invariants = set(skip)
    return cmd


def test_active_invariants_filters_by_name():
    cmd = _make_command(["No Unexpected Tables"])
    result = cmd._active_invariants([NoUnexpectedTables(), AllExpectedTablesExist()])
    assert len(result) == 1
    assert result[0].name == "All Expected Tables Exist"


def test_active_invariants_empty_skip_returns_all():
    cmd = _make_command([])
    invariants = [NoUnexpectedTables(), AllExpectedTablesExist()]
    assert cmd._active_invariants(invariants) == invariants


def test_active_invariants_skip_all():
    cmd = _make_command(["No Unexpected Tables", "All Expected Tables Exist"])
    result = cmd._active_invariants([NoUnexpectedTables(), AllExpectedTablesExist()])
    assert result == []


def test_active_invariants_unknown_name_is_ignored():
    cmd = _make_command(["Nonexistent Invariant"])
    invariants = [NoUnexpectedTables(), AllExpectedTablesExist()]
    assert cmd._active_invariants(invariants) == invariants


def test_active_invariants_multiple_skips():
    cmd = _make_command(["No Unexpected Tables", "Squash Migrations Properly Replaced"])
    invariants = [
        NoUnexpectedTables(),
        AllExpectedTablesExist(),
        SquashMigrationsProperlyReplaced(),
    ]
    result = cmd._active_invariants(invariants)
    assert len(result) == 1
    assert result[0].name == "All Expected Tables Exist"
