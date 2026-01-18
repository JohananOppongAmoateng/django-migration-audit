"""End-to-end integration tests for the audit_migrations command."""

import pytest
from io import StringIO
from unittest.mock import Mock, patch
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase
from django.db import connection, models

from django_migration_audit.core.loader import MigrationNode, MigrationHistory
from django_migration_audit.core.state import SchemaState, TableState, ColumnState


class TestAuditMigrationsCommand(TestCase):
    """Test cases for the audit_migrations management command."""

    @patch('django_migration_audit.management.commands.audit_migrations.load_migration_history')
    @patch('django_migration_audit.management.commands.audit_migrations.introspect_schema')
    @patch('django_migration_audit.management.commands.audit_migrations.MigrationExtractor')
    def test_audit_command_clean_state(self, mock_extractor_class, mock_introspect, mock_load_history):
        """Test audit command with clean state (no violations)."""
        # Setup mocks for clean state
        history = MigrationHistory(
            applied={MigrationNode(app='myapp', name='0001_initial')},
            graph_nodes={MigrationNode(app='myapp', name='0001_initial')},
            missing_files=set(),
            squashed_replacements=set(),
            plan=[MigrationNode(app='myapp', name='0001_initial')],
        )
        mock_load_history.return_value = history
        
        # Mock schema (matching expected and actual)
        schema = SchemaState(tables={
            'myapp_person': TableState(
                name='myapp_person',
                columns={
                    'id': ColumnState('id', 'integer', False),
                    'name': ColumnState('name', 'varchar', False),
                }
            )
        })
        
        mock_extractor = Mock()
        mock_extractor.build_state.return_value = schema
        mock_extractor_class.return_value = mock_extractor
        mock_introspect.return_value = schema
        
        # Run command
        out = StringIO()
        call_command('audit_migrations', stdout=out)
        output = out.getvalue()
        
        # Verify output
        assert 'Django Migration Audit' in output
        assert 'Comparison A: Trust Verification' in output
        assert 'Comparison B: Reality Check' in output
        assert '✅ No violations found!' in output or 'No violations found' in output
        assert 'Pass' in output

    @patch('django_migration_audit.management.commands.audit_migrations.load_migration_history')
    def test_audit_command_with_violations(self, mock_load_history):
        """Test audit command with violations."""
        # Setup mocks with violations
        missing_node = MigrationNode(app='myapp', name='0001_missing')
        
        history = MigrationHistory(
            applied={missing_node},
            graph_nodes=set(),
            missing_files={missing_node},
            squashed_replacements=set(),
            plan=[],
        )
        mock_load_history.return_value = history
        
        # Run command with comparison=a to skip Comparison B (which would use real MigrationGraph)
        out = StringIO()
        call_command('audit_migrations', comparison='a', stdout=out)
        output = out.getvalue()
        
        # Verify violations are reported
        assert 'violation' in output.lower()
        assert 'myapp.0001_missing' in output or 'missing' in output.lower()

    @patch('django_migration_audit.management.commands.audit_migrations.load_migration_history')
    def test_audit_command_comparison_a_only(self, mock_load_history):
        """Test audit command with --comparison=a flag."""
        # Setup mocks
        history = MigrationHistory(
            applied=set(),
            graph_nodes=set(),
            missing_files=set(),
            squashed_replacements=set(),
            plan=[],
        )
        mock_load_history.return_value = history
        
        # Run command with comparison=a
        out = StringIO()
        call_command('audit_migrations', comparison='a', stdout=out)
        output = out.getvalue()
        
        # Verify only Comparison A is run
        assert 'Comparison A: Trust Verification' in output
        assert 'Comparison B: Reality Check' not in output

    @patch('django_migration_audit.management.commands.audit_migrations.load_migration_history')
    @patch('django_migration_audit.management.commands.audit_migrations.introspect_schema')
    @patch('django_migration_audit.management.commands.audit_migrations.MigrationExtractor')
    def test_audit_command_comparison_b_only(self, mock_extractor_class, mock_introspect, mock_load_history):
        """Test audit command with --comparison=b flag."""
        # Setup mocks
        history = MigrationHistory(
            applied=set(),
            graph_nodes=set(),
            missing_files=set(),
            squashed_replacements=set(),
            plan=[],
        )
        mock_load_history.return_value = history
        
        schema = SchemaState(tables={})
        mock_extractor = Mock()
        mock_extractor.build_state.return_value = schema
        mock_extractor_class.return_value = mock_extractor
        mock_introspect.return_value = schema
        
        # Run command with comparison=b
        out = StringIO()
        call_command('audit_migrations', comparison='b', stdout=out)
        output = out.getvalue()
        
        # Verify only Comparison B is run
        assert 'Comparison B: Reality Check' in output
        assert 'Comparison A: Trust Verification' not in output

    @patch('django_migration_audit.management.commands.audit_migrations.connections')
    @patch('django_migration_audit.management.commands.audit_migrations.load_migration_history')
    @patch('django_migration_audit.management.commands.audit_migrations.introspect_schema')
    @patch('django_migration_audit.management.commands.audit_migrations.MigrationExtractor')
    def test_audit_command_custom_database(self, mock_extractor_class, mock_introspect, mock_load_history, mock_connections):
        """Test audit command with --database flag."""
        # Setup mocks
        history = MigrationHistory(
            applied=set(),
            graph_nodes=set(),
            missing_files=set(),
            squashed_replacements=set(),
            plan=[],
        )
        mock_load_history.return_value = history
        
        schema = SchemaState(tables={})
        mock_extractor = Mock()
        mock_extractor.build_state.return_value = schema
        mock_extractor_class.return_value = mock_extractor
        mock_introspect.return_value = schema
        
        # Mock connection
        mock_connection = Mock()
        mock_connection.introspection = Mock()
        mock_connections.__getitem__.return_value = mock_connection
        
        # Run command with custom database
        out = StringIO()
        call_command('audit_migrations', database='secondary', stdout=out)
        output = out.getvalue()
        
        # Verify custom database is used
        assert 'Database: secondary' in output
        mock_load_history.assert_called_once_with(using='secondary')
        mock_introspect.assert_called_once_with(using='secondary')

    @patch('django_migration_audit.management.commands.audit_migrations.load_migration_history')
    @patch('django_migration_audit.management.commands.audit_migrations.introspect_schema')
    @patch('django_migration_audit.management.commands.audit_migrations.MigrationExtractor')
    def test_audit_command_output_format(self, mock_extractor_class, mock_introspect, mock_load_history):
        """Test that audit command output is properly formatted."""
        # Setup mocks
        history = MigrationHistory(
            applied={MigrationNode(app='app1', name='0001_initial')},
            graph_nodes={MigrationNode(app='app1', name='0001_initial')},
            missing_files=set(),
            squashed_replacements=set(),
            plan=[],
        )
        mock_load_history.return_value = history
        
        schema = SchemaState(tables={
            'app1_model': TableState(name='app1_model', columns={})
        })
        mock_extractor = Mock()
        mock_extractor.build_state.return_value = schema
        mock_extractor_class.return_value = mock_extractor
        mock_introspect.return_value = schema
        
        # Run command
        out = StringIO()
        call_command('audit_migrations', stdout=out)
        output = out.getvalue()
        
        # Verify output structure
        assert '===' in output  # Section headers
        assert 'Loading migration history' in output
        assert 'Applied migrations:' in output
        assert 'Migration files on disk:' in output
        assert 'Expected tables:' in output
        assert 'Actual tables:' in output
        assert 'Summary' in output

    @patch('django_migration_audit.management.commands.audit_migrations.load_migration_history')
    def test_audit_command_multiple_violations(self, mock_load_history):
        """Test audit command with multiple violations."""
        # Setup mocks with multiple violations
        missing1 = MigrationNode(app='app1', name='0001_missing')
        missing2 = MigrationNode(app='app2', name='0001_missing')
        replaced = MigrationNode(app='app3', name='0001_old')
        
        history = MigrationHistory(
            applied={missing1, missing2, replaced},
            graph_nodes=set(),
            missing_files={missing1, missing2},
            squashed_replacements={replaced},
            plan=[],
        )
        mock_load_history.return_value = history
        
        # Run command with comparison=a to skip Comparison B (which would use real MigrationGraph)
        out = StringIO()
        call_command('audit_migrations', comparison='a', stdout=out)
        output = out.getvalue()
        
        # Verify multiple violations are reported
        assert 'violation' in output.lower()
        # Should show count of violations
        assert any(char.isdigit() for char in output)

    @patch('django_migration_audit.management.commands.audit_migrations.load_migration_history')
    @patch('django_migration_audit.management.commands.audit_migrations.introspect_schema')
    @patch('django_migration_audit.management.commands.audit_migrations.MigrationExtractor')
    def test_audit_command_error_and_warning_counts(self, mock_extractor_class, mock_introspect, mock_load_history):
        """Test that errors and warnings are counted separately."""
        # Setup mocks with both errors and warnings
        missing = MigrationNode(app='app1', name='0001_missing')  # ERROR
        replaced = MigrationNode(app='app2', name='0001_old')  # WARNING
        
        history = MigrationHistory(
            applied={missing, replaced},
            graph_nodes=set(),
            missing_files={missing},
            squashed_replacements={replaced},
            plan=[],
        )
        mock_load_history.return_value = history
        
        # Mock schemas with table mismatch (WARNING)
        expected_schema = SchemaState(tables={
            'expected_table': TableState(name='expected_table', columns={})
        })
        actual_schema = SchemaState(tables={
            'unexpected_table': TableState(name='unexpected_table', columns={})
        })
        
        mock_extractor = Mock()
        mock_extractor.build_state.return_value = expected_schema
        mock_extractor_class.return_value = mock_extractor
        mock_introspect.return_value = actual_schema
        
        # Run command
        out = StringIO()
        call_command('audit_migrations', stdout=out)
        output = out.getvalue()
        
        # Verify error and warning counts
        assert 'Errors:' in output
        assert 'Warnings:' in output


@pytest.mark.django_db
class TestAuditMigrationsCommandIntegration(TransactionTestCase):
    """Integration tests with real database."""

    def setUp(self):
        """Set up test database."""
        with connection.schema_editor() as schema_editor:
            class TestModel(models.Model):
                name = models.CharField(max_length=100)
                
                class Meta:
                    app_label = 'test_e2e'
                    db_table = 'test_e2e_model'
            
            self.TestModel = TestModel
            schema_editor.create_model(TestModel)

    def tearDown(self):
        """Clean up test database."""
        with connection.schema_editor() as schema_editor:
            try:
                schema_editor.delete_model(self.TestModel)
            except:
                pass

    @patch('django_migration_audit.management.commands.audit_migrations.load_migration_history')
    @patch('django_migration_audit.management.commands.audit_migrations.MigrationExtractor')
    def test_audit_with_real_database(self, mock_extractor_class, mock_load_history):
        """Test audit command with real database introspection."""
        # Setup mocks
        history = MigrationHistory(
            applied=set(),
            graph_nodes=set(),
            missing_files=set(),
            squashed_replacements=set(),
            plan=[],
        )
        mock_load_history.return_value = history
        
        # Mock expected schema to match actual
        expected_schema = SchemaState(tables={
            'test_e2e_model': TableState(
                name='test_e2e_model',
                columns={
                    'id': ColumnState('id', 'integer', False),
                    'name': ColumnState('name', 'varchar', False),
                }
            )
        })
        
        mock_extractor = Mock()
        mock_extractor.build_state.return_value = expected_schema
        mock_extractor_class.return_value = mock_extractor
        
        # Run command (will use real introspection)
        out = StringIO()
        call_command('audit_migrations', comparison='b', stdout=out)
        output = out.getvalue()
        
        # Verify command ran successfully
        assert 'Comparison B: Reality Check' in output
        assert 'Introspecting actual database schema' in output


class TestAuditMigrationsCommandHelpers:
    """Test helper methods in the audit command."""

    def test_command_help_text(self):
        """Test that command has proper help text."""
        from django_migration_audit.management.commands.audit_migrations import Command
        
        cmd = Command()
        assert cmd.help
        assert 'audit' in cmd.help.lower()
        assert 'migration' in cmd.help.lower()

    def test_command_arguments(self):
        """Test that command accepts expected arguments."""
        from django_migration_audit.management.commands.audit_migrations import Command
        from argparse import ArgumentParser
        
        cmd = Command()
        parser = ArgumentParser()
        cmd.add_arguments(parser)
        
        # Parse with default arguments
        args = parser.parse_args([])
        assert args.database == 'default'
        assert args.comparison == 'all'
        
        # Parse with custom arguments
        args = parser.parse_args(['--database', 'secondary', '--comparison', 'a'])
        assert args.database == 'secondary'
        assert args.comparison == 'a'
