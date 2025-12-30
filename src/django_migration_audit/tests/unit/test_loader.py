"""Unit tests for migration loader functionality."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import FrozenInstanceError

from django_migration_audit.core.loader import (
    MigrationNode,
    MigrationHistory,
    _node,
    _load_loader,
    _load_applied,
    _load_graph_nodes,
    _load_squashed_replacements,
    _build_forward_plan,
    load_migration_history,
)


class TestMigrationNode(unittest.TestCase):
    """Test cases for MigrationNode dataclass."""

    def test_migration_node_creation(self):
        """Test creating a MigrationNode."""
        node = MigrationNode(app="myapp", name="0001_initial")
        self.assertEqual(node.app, "myapp")
        self.assertEqual(node.name, "0001_initial")

    def test_migration_node_frozen(self):
        """Test that MigrationNode is frozen (immutable)."""
        node = MigrationNode(app="myapp", name="0001_initial")
        with self.assertRaises(FrozenInstanceError):
            node.app = "otherapp"

    def test_migration_node_equality(self):
        """Test MigrationNode equality."""
        node1 = MigrationNode(app="myapp", name="0001_initial")
        node2 = MigrationNode(app="myapp", name="0001_initial")
        node3 = MigrationNode(app="myapp", name="0002_auto")
        
        self.assertEqual(node1, node2)
        self.assertNotEqual(node1, node3)

    def test_migration_node_hashable(self):
        """Test that MigrationNode can be used in sets and dicts."""
        node1 = MigrationNode(app="myapp", name="0001_initial")
        node2 = MigrationNode(app="myapp", name="0001_initial")
        node3 = MigrationNode(app="myapp", name="0002_auto")
        
        node_set = {node1, node2, node3}
        self.assertEqual(len(node_set), 2)  # node1 and node2 are the same


class TestMigrationHistory(unittest.TestCase):
    """Test cases for MigrationHistory dataclass."""

    def test_migration_history_creation(self):
        """Test creating a MigrationHistory."""
        applied = {MigrationNode(app="app1", name="0001_initial")}
        graph_nodes = {MigrationNode(app="app1", name="0001_initial")}
        missing_files = set()
        squashed_replacements = set()
        plan = [MigrationNode(app="app1", name="0001_initial")]
        
        history = MigrationHistory(
            applied=applied,
            graph_nodes=graph_nodes,
            missing_files=missing_files,
            squashed_replacements=squashed_replacements,
            plan=plan,
        )
        
        self.assertEqual(history.applied, applied)
        self.assertEqual(history.graph_nodes, graph_nodes)
        self.assertEqual(history.missing_files, missing_files)
        self.assertEqual(history.squashed_replacements, squashed_replacements)
        self.assertEqual(history.plan, plan)


class TestNodeHelper(unittest.TestCase):
    """Test cases for _node helper function."""

    def test_node_conversion(self):
        """Test converting tuple to MigrationNode."""
        key = ("myapp", "0001_initial")
        node = _node(key)
        
        self.assertIsInstance(node, MigrationNode)
        self.assertEqual(node.app, "myapp")
        self.assertEqual(node.name, "0001_initial")


class TestLoadLoader(unittest.TestCase):
    """Test cases for _load_loader function."""

    @patch("django_migration_audit.core.loader.connections")
    @patch("django_migration_audit.core.loader.MigrationLoader")
    def test_load_loader_default(self, mock_loader_class, mock_connections):
        """Test loading the migration loader with default database."""
        mock_connection = Mock()
        mock_connections.__getitem__.return_value = mock_connection
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader
        
        result = _load_loader("default")
        
        mock_connections.__getitem__.assert_called_once_with("default")
        mock_loader_class.assert_called_once_with(mock_connection, ignore_no_migrations=True)
        self.assertEqual(result, mock_loader)

    @patch("django_migration_audit.core.loader.connections")
    @patch("django_migration_audit.core.loader.MigrationLoader")
    def test_load_loader_custom_db(self, mock_loader_class, mock_connections):
        """Test loading the migration loader with custom database."""
        mock_connection = Mock()
        mock_connections.__getitem__.return_value = mock_connection
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader
        
        result = _load_loader("secondary")
        
        mock_connections.__getitem__.assert_called_once_with("secondary")
        mock_loader_class.assert_called_once_with(mock_connection, ignore_no_migrations=True)
        self.assertEqual(result, mock_loader)


class TestLoadApplied(unittest.TestCase):
    """Test cases for _load_applied function."""

    def test_load_applied_empty(self):
        """Test loading applied migrations when none exist."""
        mock_loader = Mock()
        mock_loader.applied_migrations = {}
        
        result = _load_applied(mock_loader)
        
        self.assertEqual(result, set())

    def test_load_applied_with_migrations(self):
        """Test loading applied migrations."""
        mock_loader = Mock()
        mock_loader.applied_migrations = {
            ("app1", "0001_initial"): Mock(),
            ("app1", "0002_auto"): Mock(),
            ("app2", "0001_initial"): Mock(),
        }
        
        result = _load_applied(mock_loader)
        
        expected = {
            MigrationNode(app="app1", name="0001_initial"),
            MigrationNode(app="app1", name="0002_auto"),
            MigrationNode(app="app2", name="0001_initial"),
        }
        self.assertEqual(result, expected)


class TestLoadGraphNodes(unittest.TestCase):
    """Test cases for _load_graph_nodes function."""

    def test_load_graph_nodes_empty(self):
        """Test loading graph nodes when none exist."""
        mock_loader = Mock()
        mock_loader.disk_migrations = {}
        
        result = _load_graph_nodes(mock_loader)
        
        self.assertEqual(result, set())

    def test_load_graph_nodes_with_migrations(self):
        """Test loading graph nodes."""
        mock_loader = Mock()
        mock_loader.disk_migrations = {
            ("app1", "0001_initial"): Mock(),
            ("app1", "0002_auto"): Mock(),
            ("app2", "0001_initial"): Mock(),
        }
        
        result = _load_graph_nodes(mock_loader)
        
        expected = {
            MigrationNode(app="app1", name="0001_initial"),
            MigrationNode(app="app1", name="0002_auto"),
            MigrationNode(app="app2", name="0001_initial"),
        }
        self.assertEqual(result, expected)


class TestLoadSquashedReplacements(unittest.TestCase):
    """Test cases for _load_squashed_replacements function."""

    def test_load_squashed_replacements_none(self):
        """Test when there are no squashed migrations."""
        mock_loader = Mock()
        mock_migration = Mock()
        mock_migration.replaces = None
        mock_loader.disk_migrations = {
            ("app1", "0001_initial"): mock_migration,
        }
        
        result = _load_squashed_replacements(mock_loader)
        
        self.assertEqual(result, set())

    def test_load_squashed_replacements_empty(self):
        """Test when squashed migrations have empty replaces list."""
        mock_loader = Mock()
        mock_migration = Mock()
        mock_migration.replaces = []
        mock_loader.disk_migrations = {
            ("app1", "0001_squashed"): mock_migration,
        }
        
        result = _load_squashed_replacements(mock_loader)
        
        self.assertEqual(result, set())

    def test_load_squashed_replacements_single(self):
        """Test loading squashed replacements from a single squashed migration."""
        mock_loader = Mock()
        mock_migration = Mock()
        mock_migration.replaces = [
            ("app1", "0001_initial"),
            ("app1", "0002_auto"),
            ("app1", "0003_auto"),
        ]
        mock_loader.disk_migrations = {
            ("app1", "0001_squashed"): mock_migration,
        }
        
        result = _load_squashed_replacements(mock_loader)
        
        expected = {
            MigrationNode(app="app1", name="0001_initial"),
            MigrationNode(app="app1", name="0002_auto"),
            MigrationNode(app="app1", name="0003_auto"),
        }
        self.assertEqual(result, expected)

    def test_load_squashed_replacements_multiple(self):
        """Test loading squashed replacements from multiple squashed migrations."""
        mock_loader = Mock()
        
        mock_migration1 = Mock()
        mock_migration1.replaces = [
            ("app1", "0001_initial"),
            ("app1", "0002_auto"),
        ]
        
        mock_migration2 = Mock()
        mock_migration2.replaces = [
            ("app2", "0001_initial"),
        ]
        
        mock_migration3 = Mock()
        mock_migration3.replaces = None
        
        mock_loader.disk_migrations = {
            ("app1", "0001_squashed"): mock_migration1,
            ("app2", "0001_squashed"): mock_migration2,
            ("app3", "0001_initial"): mock_migration3,
        }
        
        result = _load_squashed_replacements(mock_loader)
        
        expected = {
            MigrationNode(app="app1", name="0001_initial"),
            MigrationNode(app="app1", name="0002_auto"),
            MigrationNode(app="app2", name="0001_initial"),
        }
        self.assertEqual(result, expected)


class TestBuildForwardPlan(unittest.TestCase):
    """Test cases for _build_forward_plan function."""

    @patch("django_migration_audit.core.loader.connections")
    @patch("django_migration_audit.core.loader.MigrationExecutor")
    def test_build_forward_plan_empty(self, mock_executor_class, mock_connections):
        """Test building forward plan when no migrations exist."""
        mock_connection = Mock()
        mock_connections.__getitem__.return_value = mock_connection
        
        mock_executor = Mock()
        mock_executor.loader.graph.leaf_nodes.return_value = []
        mock_executor.migration_plan.return_value = []
        mock_executor_class.return_value = mock_executor
        
        result = _build_forward_plan("default")
        
        self.assertEqual(result, [])

    @patch("django_migration_audit.core.loader.connections")
    @patch("django_migration_audit.core.loader.MigrationExecutor")
    def test_build_forward_plan_forward_only(self, mock_executor_class, mock_connections):
        """Test building forward plan with only forward migrations."""
        mock_connection = Mock()
        mock_connections.__getitem__.return_value = mock_connection
        
        mock_executor = Mock()
        mock_executor.loader.graph.leaf_nodes.return_value = [
            ("app1", "0002_auto"),
        ]
        mock_executor.migration_plan.return_value = [
            (("app1", "0001_initial"), False),  # Forward
            (("app1", "0002_auto"), False),     # Forward
        ]
        mock_executor_class.return_value = mock_executor
        
        result = _build_forward_plan("default")
        
        expected = [
            MigrationNode(app="app1", name="0001_initial"),
            MigrationNode(app="app1", name="0002_auto"),
        ]
        self.assertEqual(result, expected)

    @patch("django_migration_audit.core.loader.connections")
    @patch("django_migration_audit.core.loader.MigrationExecutor")
    def test_build_forward_plan_mixed(self, mock_executor_class, mock_connections):
        """Test building forward plan with mixed forward and backward migrations."""
        mock_connection = Mock()
        mock_connections.__getitem__.return_value = mock_connection
        
        mock_executor = Mock()
        mock_executor.loader.graph.leaf_nodes.return_value = [
            ("app1", "0002_auto"),
        ]
        mock_executor.migration_plan.return_value = [
            (("app1", "0003_auto"), True),      # Backward (should be excluded)
            (("app1", "0001_initial"), False),  # Forward
            (("app1", "0002_auto"), False),     # Forward
        ]
        mock_executor_class.return_value = mock_executor
        
        result = _build_forward_plan("default")
        
        expected = [
            MigrationNode(app="app1", name="0001_initial"),
            MigrationNode(app="app1", name="0002_auto"),
        ]
        self.assertEqual(result, expected)


class TestLoadMigrationHistory(unittest.TestCase):
    """Test cases for load_migration_history function."""

    @patch("django_migration_audit.core.loader._build_forward_plan")
    @patch("django_migration_audit.core.loader._load_squashed_replacements")
    @patch("django_migration_audit.core.loader._load_graph_nodes")
    @patch("django_migration_audit.core.loader._load_applied")
    @patch("django_migration_audit.core.loader._load_loader")
    def test_load_migration_history_empty(
        self,
        mock_load_loader,
        mock_load_applied,
        mock_load_graph_nodes,
        mock_load_squashed,
        mock_build_plan,
    ):
        """Test loading migration history when no migrations exist."""
        mock_loader = Mock()
        mock_load_loader.return_value = mock_loader
        mock_load_applied.return_value = set()
        mock_load_graph_nodes.return_value = set()
        mock_load_squashed.return_value = set()
        mock_build_plan.return_value = []
        
        result = load_migration_history("default")
        
        self.assertIsInstance(result, MigrationHistory)
        self.assertEqual(result.applied, set())
        self.assertEqual(result.graph_nodes, set())
        self.assertEqual(result.missing_files, set())
        self.assertEqual(result.squashed_replacements, set())
        self.assertEqual(result.plan, [])

    @patch("django_migration_audit.core.loader._build_forward_plan")
    @patch("django_migration_audit.core.loader._load_squashed_replacements")
    @patch("django_migration_audit.core.loader._load_graph_nodes")
    @patch("django_migration_audit.core.loader._load_applied")
    @patch("django_migration_audit.core.loader._load_loader")
    def test_load_migration_history_with_data(
        self,
        mock_load_loader,
        mock_load_applied,
        mock_load_graph_nodes,
        mock_load_squashed,
        mock_build_plan,
    ):
        """Test loading migration history with migrations."""
        mock_loader = Mock()
        mock_load_loader.return_value = mock_loader
        
        applied = {
            MigrationNode(app="app1", name="0001_initial"),
            MigrationNode(app="app1", name="0002_auto"),
        }
        graph_nodes = {
            MigrationNode(app="app1", name="0001_initial"),
            MigrationNode(app="app1", name="0002_auto"),
        }
        squashed = {
            MigrationNode(app="app1", name="0001_old"),
        }
        plan = [
            MigrationNode(app="app1", name="0001_initial"),
            MigrationNode(app="app1", name="0002_auto"),
        ]
        
        mock_load_applied.return_value = applied
        mock_load_graph_nodes.return_value = graph_nodes
        mock_load_squashed.return_value = squashed
        mock_build_plan.return_value = plan
        
        result = load_migration_history("default")
        
        self.assertIsInstance(result, MigrationHistory)
        self.assertEqual(result.applied, applied)
        self.assertEqual(result.graph_nodes, graph_nodes)
        self.assertEqual(result.missing_files, set())  # applied - graph_nodes
        self.assertEqual(result.squashed_replacements, squashed)
        self.assertEqual(result.plan, plan)

    @patch("django_migration_audit.core.loader._build_forward_plan")
    @patch("django_migration_audit.core.loader._load_squashed_replacements")
    @patch("django_migration_audit.core.loader._load_graph_nodes")
    @patch("django_migration_audit.core.loader._load_applied")
    @patch("django_migration_audit.core.loader._load_loader")
    def test_load_migration_history_missing_files(
        self,
        mock_load_loader,
        mock_load_applied,
        mock_load_graph_nodes,
        mock_load_squashed,
        mock_build_plan,
    ):
        """Test detecting missing migration files."""
        mock_loader = Mock()
        mock_load_loader.return_value = mock_loader
        
        applied = {
            MigrationNode(app="app1", name="0001_initial"),
            MigrationNode(app="app1", name="0002_auto"),
            MigrationNode(app="app1", name="0003_missing"),  # Applied but not on disk
        }
        graph_nodes = {
            MigrationNode(app="app1", name="0001_initial"),
            MigrationNode(app="app1", name="0002_auto"),
        }
        
        mock_load_applied.return_value = applied
        mock_load_graph_nodes.return_value = graph_nodes
        mock_load_squashed.return_value = set()
        mock_build_plan.return_value = []
        
        result = load_migration_history("default")
        
        expected_missing = {
            MigrationNode(app="app1", name="0003_missing"),
        }
        self.assertEqual(result.missing_files, expected_missing)

    @patch("django_migration_audit.core.loader._build_forward_plan")
    @patch("django_migration_audit.core.loader._load_squashed_replacements")
    @patch("django_migration_audit.core.loader._load_graph_nodes")
    @patch("django_migration_audit.core.loader._load_applied")
    @patch("django_migration_audit.core.loader._load_loader")
    def test_load_migration_history_custom_database(
        self,
        mock_load_loader,
        mock_load_applied,
        mock_load_graph_nodes,
        mock_load_squashed,
        mock_build_plan,
    ):
        """Test loading migration history for a custom database."""
        mock_loader = Mock()
        mock_load_loader.return_value = mock_loader
        mock_load_applied.return_value = set()
        mock_load_graph_nodes.return_value = set()
        mock_load_squashed.return_value = set()
        mock_build_plan.return_value = []
        
        load_migration_history("secondary")
        
        mock_load_loader.assert_called_once_with("secondary")
        mock_build_plan.assert_called_once_with("secondary")
