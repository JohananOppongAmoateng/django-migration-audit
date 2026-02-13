"""Unit tests for migration extractor functionality."""

import pytest
from unittest.mock import Mock, MagicMock
from django.db import models
from django.db.migrations.operations import models as model_ops
from django.db.migrations.operations import fields as field_ops

from django_migration_audit.core.extractor import MigrationExtractor, SCHEMA_OPS
from django_migration_audit.core.state import ProjectState, SchemaState, TableState, ColumnState


def create_mock_graph(nodes_dict, ordered_nodes):
    """
    Create a mock migration graph that works with the new extractor API.

    Args:
        nodes_dict: Dict mapping node tuples (app, name) to mock migration objects
                   where each value should have a 'migration' attribute
        ordered_nodes: List of node tuples in topological order (dependencies first)

    Returns:
        A mock graph with leaf_nodes() and iterative_dfs() properly configured
    """
    # Create a mock map of keys to Node objects
    mock_node_map = {}
    mock_nodes = {}  # Map keys to migrations

    for key, node in nodes_dict.items():
        # In the test setup, nodes_dict values are treating as 'nodes' wrapping a migration
        # But in reality, graph.nodes[key] is the migration, and graph.node_map[key] is the Node
        # We need to adapt the test data or the mock structure.
        # Let's assume nodes_dict values are the "Migration" objects for simplicity in existing tests
        # And we create fake "Node" objects for node_map.

        # The existing tests create a mock "node" that has a .migration attribute.
        # This matches the OLD buggy code expectation: migration = self.graph.nodes[node].migration
        # BUT the NEW code expects: migration = self.graph.nodes[node_key]
        # So we need to change how the mock graph is constructed to store the migration directly in nodes.

        if hasattr(node, "migration"):
            mock_nodes[key] = node.migration
        else:
            mock_nodes[
                key
            ] = node  # Assume it's already the migration object if no .migration attr

        # Create a dummy Node object for node_map
        mock_graph_node = Mock()
        mock_graph_node.key = key
        mock_node_map[key] = mock_graph_node

    mock_graph = Mock()
    mock_graph.nodes = mock_nodes
    mock_graph.node_map = mock_node_map

    # Find leaf nodes (nodes that are not dependencies of other nodes)
    # For simplicity, assume the last node in ordered_nodes is the leaf
    if ordered_nodes:
        leaf_nodes = [ordered_nodes[-1]]
    else:
        leaf_nodes = []

    mock_graph.leaf_nodes.return_value = leaf_nodes

    # iterative_dfs from a leaf should return KEYS in reversed order
    def iterative_dfs(start_node):
        # start_node is the Node object from node_map
        if start_node.key in ordered_nodes:
            idx = ordered_nodes.index(start_node.key)
            # Return from start_node back to the beginning (reverse order from leaf)
            return reversed(ordered_nodes[: idx + 1])
        return []

    mock_graph.iterative_dfs.side_effect = iterative_dfs

    return mock_graph


class TestMigrationExtractor:
    """Test cases for MigrationExtractor."""

    def test_build_state_empty_migrations(self):
        """Test building state with no migrations."""
        mock_graph = create_mock_graph({}, [])

        extractor = MigrationExtractor(migration_graph=mock_graph, applied_nodes=set())

        schema = extractor.build_state()

        assert isinstance(schema, SchemaState)
        assert len(schema.tables) == 0

    def test_build_state_single_create_model(self):
        """Test building state with a single CreateModel operation."""
        # Create mock migration
        mock_migration = Mock()
        mock_migration.app_label = "myapp"
        mock_migration.operations = [
            model_ops.CreateModel(
                name="Author",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                    ("name", models.CharField(max_length=100)),
                    ("email", models.EmailField()),
                ],
                options={},
            )
        ]

        # Create mock graph
        mock_node = Mock()
        mock_node.migration = mock_migration

        nodes_dict = {("myapp", "0001_initial"): mock_node}
        ordered_nodes = [("myapp", "0001_initial")]
        mock_graph = create_mock_graph(nodes_dict, ordered_nodes)

        extractor = MigrationExtractor(
            migration_graph=mock_graph, applied_nodes={("myapp", "0001_initial")}
        )

        schema = extractor.build_state()

        assert schema.has_table("myapp_author")
        table = schema.table("myapp_author")
        assert table.has_column("id")
        assert table.has_column("name")
        assert table.has_column("email")
        assert table.column("name").db_type == "varchar"
        assert table.column("email").db_type == "varchar"

    def test_build_state_multiple_models(self):
        """Test building state with multiple CreateModel operations."""
        # Create mock migration
        mock_migration = Mock()
        mock_migration.app_label = "blog"
        mock_migration.operations = [
            model_ops.CreateModel(
                name="Author",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                    ("name", models.CharField(max_length=100)),
                ],
                options={},
            ),
            model_ops.CreateModel(
                name="Post",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                    ("title", models.CharField(max_length=200)),
                    ("content", models.TextField()),
                ],
                options={},
            ),
        ]

        # Create mock graph
        mock_node = Mock()
        mock_node.migration = mock_migration

        nodes_dict = {("blog", "0001_initial"): mock_node}
        ordered_nodes = [("blog", "0001_initial")]
        mock_graph = create_mock_graph(nodes_dict, ordered_nodes)

        extractor = MigrationExtractor(
            migration_graph=mock_graph, applied_nodes={("blog", "0001_initial")}
        )

        schema = extractor.build_state()

        assert schema.has_table("blog_author")
        assert schema.has_table("blog_post")
        assert len(schema.tables) == 2

    def test_build_state_add_field(self):
        """Test building state with AddField operation."""
        # Create initial migration
        mock_migration1 = Mock()
        mock_migration1.app_label = "myapp"
        mock_migration1.operations = [
            model_ops.CreateModel(
                name="Person",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                    ("name", models.CharField(max_length=100)),
                ],
                options={},
            )
        ]

        # Create migration that adds field
        email_field = models.EmailField()
        email_field.name = "email"

        mock_migration2 = Mock()
        mock_migration2.app_label = "myapp"
        mock_migration2.operations = [
            field_ops.AddField(
                model_name="Person",
                name="email",
                field=email_field,
            )
        ]

        # Create mock graph
        mock_node1 = Mock()
        mock_node1.migration = mock_migration1
        mock_node2 = Mock()
        mock_node2.migration = mock_migration2

        nodes_dict = {
            ("myapp", "0001_initial"): mock_node1,
            ("myapp", "0002_add_email"): mock_node2,
        }
        ordered_nodes = [
            ("myapp", "0001_initial"),
            ("myapp", "0002_add_email"),
        ]
        mock_graph = create_mock_graph(nodes_dict, ordered_nodes)

        extractor = MigrationExtractor(
            migration_graph=mock_graph,
            applied_nodes={("myapp", "0001_initial"), ("myapp", "0002_add_email")},
        )

        schema = extractor.build_state()

        table = schema.table("myapp_person")
        assert table.has_column("id")
        assert table.has_column("name")
        assert table.has_column("email")

    def test_build_state_remove_field(self):
        """Test building state with RemoveField operation."""
        # Create initial migration
        mock_migration1 = Mock()
        mock_migration1.app_label = "myapp"
        mock_migration1.operations = [
            model_ops.CreateModel(
                name="Person",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                    ("name", models.CharField(max_length=100)),
                    ("temp_field", models.CharField(max_length=50)),
                ],
                options={},
            )
        ]

        # Create migration that removes field
        mock_migration2 = Mock()
        mock_migration2.app_label = "myapp"
        mock_migration2.operations = [
            field_ops.RemoveField(
                model_name="Person",
                name="temp_field",
            )
        ]

        # Create mock graph
        mock_node1 = Mock()
        mock_node1.migration = mock_migration1
        mock_node2 = Mock()
        mock_node2.migration = mock_migration2

        nodes_dict = {
            ("myapp", "0001_initial"): mock_node1,
            ("myapp", "0002_remove_temp"): mock_node2,
        }
        ordered_nodes = [
            ("myapp", "0001_initial"),
            ("myapp", "0002_remove_temp"),
        ]
        mock_graph = create_mock_graph(nodes_dict, ordered_nodes)

        extractor = MigrationExtractor(
            migration_graph=mock_graph,
            applied_nodes={("myapp", "0001_initial"), ("myapp", "0002_remove_temp")},
        )

        schema = extractor.build_state()

        table = schema.table("myapp_person")
        assert table.has_column("id")
        assert table.has_column("name")
        assert not table.has_column("temp_field")

    def test_build_state_alter_field(self):
        """Test building state with AlterField operation."""
        # Create initial migration
        mock_migration1 = Mock()
        mock_migration1.app_label = "myapp"
        mock_migration1.operations = [
            model_ops.CreateModel(
                name="Person",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                    ("age", models.IntegerField()),
                ],
                options={},
            )
        ]

        # Create migration that alters field
        new_age_field = models.BigIntegerField()
        new_age_field.name = "age"

        mock_migration2 = Mock()
        mock_migration2.app_label = "myapp"
        mock_migration2.operations = [
            field_ops.AlterField(
                model_name="Person",
                name="age",
                field=new_age_field,
            )
        ]

        # Create mock graph
        mock_node1 = Mock()
        mock_node1.migration = mock_migration1
        mock_node2 = Mock()
        mock_node2.migration = mock_migration2

        nodes_dict = {
            ("myapp", "0001_initial"): mock_node1,
            ("myapp", "0002_alter_age"): mock_node2,
        }
        ordered_nodes = [
            ("myapp", "0001_initial"),
            ("myapp", "0002_alter_age"),
        ]
        mock_graph = create_mock_graph(nodes_dict, ordered_nodes)

        extractor = MigrationExtractor(
            migration_graph=mock_graph,
            applied_nodes={("myapp", "0001_initial"), ("myapp", "0002_alter_age")},
        )

        schema = extractor.build_state()

        table = schema.table("myapp_person")
        assert table.column("age").db_type == "bigint"

    def test_build_state_delete_model(self):
        """Test building state with DeleteModel operation."""
        # Create initial migration
        mock_migration1 = Mock()
        mock_migration1.app_label = "myapp"
        mock_migration1.operations = [
            model_ops.CreateModel(
                name="TempModel",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                ],
                options={},
            ),
            model_ops.CreateModel(
                name="Person",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                ],
                options={},
            ),
        ]

        # Create migration that deletes model
        mock_migration2 = Mock()
        mock_migration2.app_label = "myapp"
        mock_migration2.operations = [
            model_ops.DeleteModel(
                name="TempModel",
            )
        ]

        # Create mock graph
        mock_node1 = Mock()
        mock_node1.migration = mock_migration1
        mock_node2 = Mock()
        mock_node2.migration = mock_migration2

        nodes_dict = {
            ("myapp", "0001_initial"): mock_node1,
            ("myapp", "0002_delete_temp"): mock_node2,
        }
        ordered_nodes = [
            ("myapp", "0001_initial"),
            ("myapp", "0002_delete_temp"),
        ]
        mock_graph = create_mock_graph(nodes_dict, ordered_nodes)

        extractor = MigrationExtractor(
            migration_graph=mock_graph,
            applied_nodes={("myapp", "0001_initial"), ("myapp", "0002_delete_temp")},
        )

        schema = extractor.build_state()

        assert not schema.has_table("myapp_tempmodel")
        assert schema.has_table("myapp_person")

    def test_build_state_complex_sequence(self):
        """Test building state with a realistic migration sequence."""
        # Migration 1: Create Author
        mock_migration1 = Mock()
        mock_migration1.app_label = "blog"
        mock_migration1.operations = [
            model_ops.CreateModel(
                name="Author",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                    ("name", models.CharField(max_length=100)),
                ],
                options={},
            )
        ]

        # Migration 2: Create Post
        mock_migration2 = Mock()
        mock_migration2.app_label = "blog"
        mock_migration2.operations = [
            model_ops.CreateModel(
                name="Post",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                    ("title", models.CharField(max_length=200)),
                ],
                options={},
            )
        ]

        # Migration 3: Add email to Author
        email_field = models.EmailField()
        email_field.name = "email"

        mock_migration3 = Mock()
        mock_migration3.app_label = "blog"
        mock_migration3.operations = [
            field_ops.AddField(
                model_name="Author",
                name="email",
                field=email_field,
            )
        ]

        # Migration 4: Add content to Post
        content_field = models.TextField()
        content_field.name = "content"

        mock_migration4 = Mock()
        mock_migration4.app_label = "blog"
        mock_migration4.operations = [
            field_ops.AddField(
                model_name="Post",
                name="content",
                field=content_field,
            )
        ]

        # Create mock graph
        mock_node1 = Mock()
        mock_node1.migration = mock_migration1
        mock_node2 = Mock()
        mock_node2.migration = mock_migration2
        mock_node3 = Mock()
        mock_node3.migration = mock_migration3
        mock_node4 = Mock()
        mock_node4.migration = mock_migration4

        nodes_dict = {
            ("blog", "0001_initial"): mock_node1,
            ("blog", "0002_create_post"): mock_node2,
            ("blog", "0003_add_email"): mock_node3,
            ("blog", "0004_add_content"): mock_node4,
        }
        ordered_nodes = [
            ("blog", "0001_initial"),
            ("blog", "0002_create_post"),
            ("blog", "0003_add_email"),
            ("blog", "0004_add_content"),
        ]
        mock_graph = create_mock_graph(nodes_dict, ordered_nodes)

        extractor = MigrationExtractor(
            migration_graph=mock_graph,
            applied_nodes={
                ("blog", "0001_initial"),
                ("blog", "0002_create_post"),
                ("blog", "0003_add_email"),
                ("blog", "0004_add_content"),
            },
        )

        schema = extractor.build_state()

        # Verify Author table
        assert schema.has_table("blog_author")
        author_table = schema.table("blog_author")
        assert author_table.has_column("id")
        assert author_table.has_column("name")
        assert author_table.has_column("email")

        # Verify Post table
        assert schema.has_table("blog_post")
        post_table = schema.table("blog_post")
        assert post_table.has_column("id")
        assert post_table.has_column("title")
        assert post_table.has_column("content")

    def test_ordered_applied_nodes(self):
        """Test that applied nodes are returned in topological order."""
        # Each applied node should be returned in proper order
        ordered_nodes = [
            ("app1", "0001_initial"),
            ("app2", "0001_initial"),
            ("app1", "0002_auto"),
            ("app2", "0002_auto"),
        ]

        # We need to provide nodes_dict for create_mock_graph to populate node_map
        nodes_dict = {
            ("app1", "0001_initial"): Mock(),
            ("app2", "0001_initial"): Mock(),
            ("app1", "0002_auto"): Mock(),
            ("app2", "0002_auto"): Mock(),
        }

        mock_graph = create_mock_graph(nodes_dict, ordered_nodes)

        extractor = MigrationExtractor(
            migration_graph=mock_graph,
            applied_nodes={
                ("app1", "0002_auto"),
                ("app2", "0001_initial"),
            },
        )

        ordered = extractor._ordered_applied_nodes()

        # Should only include applied nodes
        assert len(ordered) == 2
        assert ("app2", "0001_initial") in ordered
        assert ("app1", "0002_auto") in ordered
        # Verify topological ordering: app2.0001 comes before app1.0002
        assert ordered.index(("app2", "0001_initial")) < ordered.index(("app1", "0002_auto"))

    def test_apply_operation_sets_app_label(self):
        """Test that app_label is set on operations that don't have it."""
        mock_migration = Mock()
        mock_migration.app_label = "testapp"

        # Create operation without app_label
        operation = model_ops.CreateModel(
            name="TestModel",
            fields=[("id", models.AutoField(primary_key=True))],
            options={},
        )

        mock_migration.operations = [operation]

        # Create mock graph
        mock_node = Mock()
        mock_node.migration = mock_migration

        nodes_dict = {("testapp", "0001_initial"): mock_node}
        ordered_nodes = [("testapp", "0001_initial")]
        mock_graph = create_mock_graph(nodes_dict, ordered_nodes)

        extractor = MigrationExtractor(
            migration_graph=mock_graph, applied_nodes={("testapp", "0001_initial")}
        )

        schema = extractor.build_state()

        # Verify the operation was applied (table exists)
        assert schema.has_table("testapp_testmodel")

    def test_build_state_with_custom_db_table(self):
        """Test building state with custom db_table option."""
        mock_migration = Mock()
        mock_migration.app_label = "myapp"
        mock_migration.operations = [
            model_ops.CreateModel(
                name="Person",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                    ("name", models.CharField(max_length=100)),
                ],
                options={"db_table": "custom_people"},
            )
        ]

        # Create mock graph
        mock_node = Mock()
        mock_node.migration = mock_migration

        nodes_dict = {("myapp", "0001_initial"): mock_node}
        ordered_nodes = [("myapp", "0001_initial")]
        mock_graph = create_mock_graph(nodes_dict, ordered_nodes)

        extractor = MigrationExtractor(
            migration_graph=mock_graph, applied_nodes={("myapp", "0001_initial")}
        )

        schema = extractor.build_state()

        assert schema.has_table("custom_people")
        assert not schema.has_table("myapp_person")

    def test_build_state_create_model_with_foreign_key(self):
        """Test that FK fields get _id suffix on column names."""
        mock_migration = Mock()
        mock_migration.app_label = "shop"
        mock_migration.operations = [
            model_ops.CreateModel(
                name="Category",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                    ("name", models.CharField(max_length=100)),
                ],
                options={},
            ),
            model_ops.CreateModel(
                name="Product",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                    ("title", models.CharField(max_length=200)),
                    ("category", models.ForeignKey("Category", on_delete=models.CASCADE)),
                ],
                options={},
            ),
        ]

        mock_node = Mock()
        mock_node.migration = mock_migration

        nodes_dict = {("shop", "0001_initial"): mock_node}
        ordered_nodes = [("shop", "0001_initial")]
        mock_graph = create_mock_graph(nodes_dict, ordered_nodes)

        extractor = MigrationExtractor(
            migration_graph=mock_graph, applied_nodes={("shop", "0001_initial")}
        )

        schema = extractor.build_state()

        product_table = schema.table("shop_product")
        # FK field "category" should be stored as column "category_id"
        assert product_table.has_column("category_id")
        assert not product_table.has_column("category")
        assert product_table.column("category_id").db_type == "integer"

    def test_build_state_only_applied_migrations(self):
        """Test that only applied migrations are included in state."""
        # Create two migrations
        mock_migration1 = Mock()
        mock_migration1.app_label = "myapp"
        mock_migration1.operations = [
            model_ops.CreateModel(
                name="AppliedModel",
                fields=[("id", models.AutoField(primary_key=True))],
                options={},
            )
        ]

        mock_migration2 = Mock()
        mock_migration2.app_label = "myapp"
        mock_migration2.operations = [
            model_ops.CreateModel(
                name="UnappliedModel",
                fields=[("id", models.AutoField(primary_key=True))],
                options={},
            )
        ]

        # Create mock graph
        mock_node1 = Mock()
        mock_node1.migration = mock_migration1
        mock_node2 = Mock()
        mock_node2.migration = mock_migration2

        nodes_dict = {
            ("myapp", "0001_initial"): mock_node1,
            ("myapp", "0002_unapplied"): mock_node2,
        }
        ordered_nodes = [
            ("myapp", "0001_initial"),
            ("myapp", "0002_unapplied"),
        ]
        mock_graph = create_mock_graph(nodes_dict, ordered_nodes)

        # Only mark first migration as applied
        extractor = MigrationExtractor(
            migration_graph=mock_graph, applied_nodes={("myapp", "0001_initial")}
        )

        schema = extractor.build_state()

        assert schema.has_table("myapp_appliedmodel")
        assert not schema.has_table("myapp_unappliedmodel")


class TestSchemaOperations:
    """Test SCHEMA_OPS constant."""

    def test_schema_ops_includes_expected_operations(self):
        """Test that SCHEMA_OPS includes all expected operation types."""
        assert model_ops.CreateModel in SCHEMA_OPS
        assert model_ops.DeleteModel in SCHEMA_OPS
        assert field_ops.AddField in SCHEMA_OPS
        assert field_ops.RemoveField in SCHEMA_OPS
        assert field_ops.AlterField in SCHEMA_OPS
        assert model_ops.AlterModelTable in SCHEMA_OPS
        assert model_ops.AddIndex in SCHEMA_OPS
        assert model_ops.RemoveIndex in SCHEMA_OPS
        assert model_ops.AddConstraint in SCHEMA_OPS
        assert model_ops.RemoveConstraint in SCHEMA_OPS

    def test_schema_ops_excludes_non_column_operations(self):
        """AlterUniqueTogether/AlterIndexTogether don't affect column-level schema."""
        assert model_ops.AlterUniqueTogether not in SCHEMA_OPS
        assert model_ops.AlterIndexTogether not in SCHEMA_OPS
