"""Integration tests for legacy schema handling."""

import pytest
from unittest.mock import Mock, patch
from django.test import TestCase

from django_migration_audit.core.loader import (
    MigrationNode,
    MigrationHistory,
    load_migration_history,
)
from django_migration_audit.invariants.base import (
    NoMissingMigrationFiles,
    SquashMigrationsProperlyReplaced,
    Severity,
)


class TestLegacySchema(TestCase):
    """Test cases for handling legacy database schemas."""

    def test_missing_migration_file_detection(self):
        """Test detecting missing migration files."""
        # Create a history with missing files
        missing_node = MigrationNode(app='myapp', name='0001_initial')
        
        history = MigrationHistory(
            applied={missing_node, MigrationNode(app='myapp', name='0002_auto')},
            graph_nodes={MigrationNode(app='myapp', name='0002_auto')},
            missing_files={missing_node},
            squashed_replacements=set(),
            plan=[],
        )
        
        # Run invariant
        invariant = NoMissingMigrationFiles()
        violations = invariant.check(migration_history=history)
        
        # Verify detection
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert 'myapp.0001_initial' in violations[0].message
        assert 'missing' in violations[0].message.lower()

    def test_multiple_missing_migration_files(self):
        """Test detecting multiple missing migration files."""
        missing1 = MigrationNode(app='app1', name='0001_initial')
        missing2 = MigrationNode(app='app1', name='0003_auto')
        missing3 = MigrationNode(app='app2', name='0001_initial')
        
        history = MigrationHistory(
            applied={
                missing1,
                MigrationNode(app='app1', name='0002_auto'),
                missing2,
                missing3,
            },
            graph_nodes={MigrationNode(app='app1', name='0002_auto')},
            missing_files={missing1, missing2, missing3},
            squashed_replacements=set(),
            plan=[],
        )
        
        # Run invariant
        invariant = NoMissingMigrationFiles()
        violations = invariant.check(migration_history=history)
        
        # Verify all missing files are detected
        assert len(violations) == 3
        assert all(v.severity == Severity.ERROR for v in violations)

    def test_no_missing_files_clean_state(self):
        """Test that clean state with no missing files passes."""
        node1 = MigrationNode(app='myapp', name='0001_initial')
        node2 = MigrationNode(app='myapp', name='0002_auto')
        
        history = MigrationHistory(
            applied={node1, node2},
            graph_nodes={node1, node2},
            missing_files=set(),
            squashed_replacements=set(),
            plan=[],
        )
        
        # Run invariant
        invariant = NoMissingMigrationFiles()
        violations = invariant.check(migration_history=history)
        
        # Should pass with no violations
        assert len(violations) == 0

    def test_squashed_migration_properly_replaced(self):
        """Test that properly replaced squashed migrations pass."""
        replaced1 = MigrationNode(app='myapp', name='0001_initial')
        replaced2 = MigrationNode(app='myapp', name='0002_auto')
        squash = MigrationNode(app='myapp', name='0001_squashed')
        
        history = MigrationHistory(
            applied={squash},  # Only squash is applied
            graph_nodes={squash},
            missing_files=set(),
            squashed_replacements={replaced1, replaced2},
            plan=[],
        )
        
        # Run invariant
        invariant = SquashMigrationsProperlyReplaced()
        violations = invariant.check(migration_history=history)
        
        # Should pass - replaced migrations are not applied
        assert len(violations) == 0

    def test_squashed_migration_not_replaced(self):
        """Test detecting when squashed migrations don't properly replace originals."""
        replaced1 = MigrationNode(app='myapp', name='0001_initial')
        replaced2 = MigrationNode(app='myapp', name='0002_auto')
        squash = MigrationNode(app='myapp', name='0001_squashed')
        
        history = MigrationHistory(
            applied={replaced1, replaced2, squash},  # Old migrations still applied!
            graph_nodes={squash},
            missing_files=set(),
            squashed_replacements={replaced1, replaced2},
            plan=[],
        )
        
        # Run invariant
        invariant = SquashMigrationsProperlyReplaced()
        violations = invariant.check(migration_history=history)
        
        # Should detect both improperly replaced migrations
        assert len(violations) == 2
        assert all(v.severity == Severity.WARNING for v in violations)
        assert any('0001_initial' in v.message for v in violations)
        assert any('0002_auto' in v.message for v in violations)

    def test_partial_squash_replacement(self):
        """Test detecting partial squash replacement (some old migrations still applied)."""
        replaced1 = MigrationNode(app='myapp', name='0001_initial')
        replaced2 = MigrationNode(app='myapp', name='0002_auto')
        replaced3 = MigrationNode(app='myapp', name='0003_auto')
        squash = MigrationNode(app='myapp', name='0001_squashed')
        
        history = MigrationHistory(
            applied={replaced1, squash},  # Only one old migration still applied
            graph_nodes={squash},
            missing_files=set(),
            squashed_replacements={replaced1, replaced2, replaced3},
            plan=[],
        )
        
        # Run invariant
        invariant = SquashMigrationsProperlyReplaced()
        violations = invariant.check(migration_history=history)
        
        # Should detect the one improperly replaced migration
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING
        assert '0001_initial' in violations[0].message

    def test_no_squashed_migrations(self):
        """Test that absence of squashed migrations passes."""
        node1 = MigrationNode(app='myapp', name='0001_initial')
        node2 = MigrationNode(app='myapp', name='0002_auto')
        
        history = MigrationHistory(
            applied={node1, node2},
            graph_nodes={node1, node2},
            missing_files=set(),
            squashed_replacements=set(),  # No squashed migrations
            plan=[],
        )
        
        # Run invariant
        invariant = SquashMigrationsProperlyReplaced()
        violations = invariant.check(migration_history=history)
        
        # Should pass with no violations
        assert len(violations) == 0

    def test_fake_applied_migration_scenario(self):
        """Test scenario where migration is fake-applied (in DB but not on disk)."""
        # This is essentially the same as missing files
        fake_applied = MigrationNode(app='myapp', name='0002_fake')
        
        history = MigrationHistory(
            applied={
                MigrationNode(app='myapp', name='0001_initial'),
                fake_applied,
            },
            graph_nodes={MigrationNode(app='myapp', name='0001_initial')},
            missing_files={fake_applied},
            squashed_replacements=set(),
            plan=[],
        )
        
        # Run invariant
        invariant = NoMissingMigrationFiles()
        violations = invariant.check(migration_history=history)
        
        # Should detect the fake-applied migration
        assert len(violations) == 1
        assert 'myapp.0002_fake' in violations[0].message

    def test_database_restore_scenario(self):
        """Test scenario simulating a database restore with outdated migration history."""
        # Scenario: Database was restored from backup, but code has newer migrations
        old_migration = MigrationNode(app='myapp', name='0001_initial')
        new_migration = MigrationNode(app='myapp', name='0002_new_feature')
        
        history = MigrationHistory(
            applied={old_migration},  # Only old migration in DB
            graph_nodes={old_migration, new_migration},  # Both in code
            missing_files=set(),
            squashed_replacements=set(),
            plan=[old_migration, new_migration],
        )
        
        # This scenario would be detected by comparing applied vs plan
        # The new migration is in the plan but not applied
        assert new_migration in history.plan
        assert new_migration not in history.applied
        assert new_migration in history.graph_nodes

    def test_complex_legacy_scenario(self):
        """Test complex scenario with multiple legacy issues."""
        # Missing file
        missing = MigrationNode(app='app1', name='0001_missing')
        
        # Squashed but not replaced
        replaced = MigrationNode(app='app2', name='0001_old')
        squash = MigrationNode(app='app2', name='0001_squashed')
        
        # Normal migrations
        normal1 = MigrationNode(app='app3', name='0001_initial')
        normal2 = MigrationNode(app='app3', name='0002_auto')
        
        history = MigrationHistory(
            applied={missing, replaced, squash, normal1, normal2},
            graph_nodes={squash, normal1, normal2},
            missing_files={missing},
            squashed_replacements={replaced},
            plan=[],
        )
        
        # Check missing files
        invariant = NoMissingMigrationFiles()
        violations = invariant.check(migration_history=history)
        assert len(violations) == 1
        assert 'app1.0001_missing' in violations[0].message
        
        # Check squash replacement
        invariant = SquashMigrationsProperlyReplaced()
        violations = invariant.check(migration_history=history)
        assert len(violations) == 1
        assert 'app2.0001_old' in violations[0].message


class TestLegacySchemaHelpers:
    """Test helper functions for legacy schema handling."""

    def test_migration_node_in_set(self):
        """Test that MigrationNode works correctly in sets."""
        node1 = MigrationNode(app='myapp', name='0001_initial')
        node2 = MigrationNode(app='myapp', name='0001_initial')
        node3 = MigrationNode(app='myapp', name='0002_auto')
        
        nodes = {node1, node2, node3}
        
        # node1 and node2 are the same, so set should have 2 items
        assert len(nodes) == 2

    def test_migration_history_immutability(self):
        """Test that MigrationHistory fields are properly set."""
        applied = {MigrationNode(app='app1', name='0001_initial')}
        graph_nodes = {MigrationNode(app='app1', name='0001_initial')}
        missing = set()
        squashed = set()
        plan = []
        
        history = MigrationHistory(
            applied=applied,
            graph_nodes=graph_nodes,
            missing_files=missing,
            squashed_replacements=squashed,
            plan=plan,
        )
        
        assert history.applied == applied
        assert history.graph_nodes == graph_nodes
        assert history.missing_files == missing
        assert history.squashed_replacements == squashed
        assert history.plan == plan

    def test_empty_migration_history(self):
        """Test empty migration history."""
        history = MigrationHistory(
            applied=set(),
            graph_nodes=set(),
            missing_files=set(),
            squashed_replacements=set(),
            plan=[],
        )
        
        # Run all invariants - should pass
        invariant = NoMissingMigrationFiles()
        violations = invariant.check(migration_history=history)
        assert len(violations) == 0
        
        invariant = SquashMigrationsProperlyReplaced()
        violations = invariant.check(migration_history=history)
        assert len(violations) == 0
