"""
Expected Schema Extractor

This module builds the **expected schema** from migration operations without touching
the database. It serves as the bridge between migration code (Input 2) and the
expected database state.

This expected schema is used in **Comparison B: Reality Check** (expected ↔ actual)
to detect:
- Schema drift
- Manual database edits
- Broken legacy assumptions

The extractor replays migration operations to construct what the database *should*
look like based on the recorded migration history.
"""

from django.db.migrations.operations import fields, models
from django.db.migrations.operations.base import Operation

from .state import ProjectState

SCHEMA_OPS = (
    models.CreateModel,
    models.DeleteModel,
    fields.AddField,
    fields.RemoveField,
    fields.AlterField,
    models.AlterModelTable,
    models.AddIndex,
    models.RemoveIndex,
    models.AddConstraint,
    models.RemoveConstraint,
)


class MigrationExtractor:
    """
    Projects a schema state purely from migration operations,
    without touching the database.
    """

    def __init__(self, migration_graph, applied_nodes):
        self.graph = migration_graph
        self.applied_nodes = applied_nodes

    def build_state(self):
        """Build the expected schema state from applied migrations."""
        state = ProjectState()

        for node_key in self._ordered_applied_nodes():
            migration = self.graph.nodes[node_key]
            self._apply_migration(migration, state)

        return state.to_schema_state()

    def _ordered_applied_nodes(self):
        """
        Return applied migrations in topological order (dependencies first).

        Django's iterative_dfs traverses from a leaf node back through its
        ancestor chain, visiting parents before the leaf. Starting from the
        leaf and collecting all ancestors therefore naturally produces nodes
        in dependency order (root first, leaf last) — no reversal needed.
        """
        # Get all leaf nodes (migrations with no dependents)
        leaf_nodes = self.graph.leaf_nodes()

        all_nodes = []
        for leaf in leaf_nodes:
            leaf_node = self.graph.node_map[leaf]
            for node in self.graph.iterative_dfs(leaf_node):
                if node not in all_nodes:
                    all_nodes.append(node)

        # Filter to only applied nodes, preserving topological order
        return [node for node in all_nodes if node in self.applied_nodes]

    def _apply_migration(self, migration, state):
        """Apply a migration's operations to the state."""
        for operation in migration.operations:
            if isinstance(operation, SCHEMA_OPS):
                # Set app_label on operation if not already set
                if not hasattr(operation, "app_label") or operation.app_label is None:
                    operation.app_label = migration.app_label
                self._apply_operation(operation, state)

    def _apply_operation(self, operation: Operation, state: ProjectState):
        """
        Map Django migration ops → state mutations.
        """
        if isinstance(operation, models.CreateModel):
            state.create_table(
                app_label=operation.app_label,
                name=operation.name,
                fields=operation.fields,
                options=operation.options,
            )

        elif isinstance(operation, models.DeleteModel):
            state.drop_table(
                app_label=operation.app_label,
                name=operation.name,
            )

        elif isinstance(operation, fields.AddField):
            # Ensure field.name is set — Django migration operations store the
            # field name in operation.name, but the field object itself is not
            # always contributed to a model class, so field.name may be None.
            field = operation.field
            if not field.name:
                field.name = operation.name
            state.add_column(
                app_label=operation.app_label,
                model_name=operation.model_name,
                field=field,
            )

        elif isinstance(operation, fields.RemoveField):
            state.remove_column(
                app_label=operation.app_label,
                model_name=operation.model_name,
                name=operation.name,
            )

        elif isinstance(operation, fields.AlterField):
            # Same field.name fix as AddField above.
            field = operation.field
            if not field.name:
                field.name = operation.name
            state.alter_column(
                app_label=operation.app_label,
                model_name=operation.model_name,
                field=field,
            )

        elif isinstance(operation, models.AlterModelTable):
            state.rename_table(
                app_label=operation.app_label,
                model_name=operation.name,
                new_table_name=operation.table,
            )

        elif isinstance(operation, models.AddConstraint):
            state.add_constraint(
                app_label=operation.app_label,
                model_name=operation.model_name,
                constraint=operation.constraint,
            )

        elif isinstance(operation, models.RemoveConstraint):
            state.remove_constraint(
                app_label=operation.app_label,
                model_name=operation.model_name,
                name=operation.name,
            )

        elif isinstance(operation, models.AddIndex):
            state.add_index(
                app_label=operation.app_label,
                model_name=operation.model_name,
                index=operation.index,
            )

        elif isinstance(operation, models.RemoveIndex):
            state.remove_index(
                app_label=operation.app_label,
                model_name=operation.model_name,
                name=operation.name,
            )
