"""
Migration History and Code Loader

This module handles **Inputs 1 & 2** of the django-migration-audit architecture:
1. Migration history from the `django_migrations` table
2. Migration code from disk (migrations/*.py files)

It enables **Comparison A: Trust Verification** (history ↔ code) by detecting:
- Modified migration files
- Missing migration files
- Fake-applied migrations
- Squash mismatches

The core question this module helps answer:
"Can we trust the migration history at all?"
"""
from dataclasses import dataclass
from typing import Set, List, Tuple

from django.db import connections
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.executor import MigrationExecutor


@dataclass(frozen=True)
class MigrationNode:
    app: str
    name: str


@dataclass
class MigrationHistory:
    applied: Set[MigrationNode]
    graph_nodes: Set[MigrationNode]
    missing_files: Set[MigrationNode]
    squashed_replacements: Set[MigrationNode]
    plan: List[MigrationNode]


def _node(key: Tuple[str, str]) -> MigrationNode:
    return MigrationNode(app=key[0], name=key[1])


def _load_loader(using: str) -> MigrationLoader:
    connection = connections[using]
    return MigrationLoader(connection, ignore_no_migrations=True)


def _load_applied(loader: MigrationLoader) -> Set[MigrationNode]:
    return {_node(key) for key in loader.applied_migrations.keys()}


def _load_graph_nodes(loader: MigrationLoader) -> Set[MigrationNode]:
    return {_node(key) for key in loader.disk_migrations.keys()}


def _load_squashed_replacements(loader: MigrationLoader) -> Set[MigrationNode]:
    """
    Returns migrations that are replaced by squash migrations.
    """
    replaced: Set[MigrationNode] = set()

    for migration in loader.disk_migrations.values():
        if migration.replaces:
            for repl in migration.replaces:
                replaced.add(_node(repl))

    return replaced


def _build_forward_plan(using: str) -> List[MigrationNode]:
    """
    Build a deterministic forward migration plan to current leaf nodes.
    """
    connection = connections[using]
    executor = MigrationExecutor(connection)

    targets = executor.loader.graph.leaf_nodes()
    plan = executor.migration_plan(targets)

    forward_plan: List[MigrationNode] = []

    for migration_key, backwards in plan:
        if not backwards:
            forward_plan.append(_node(migration_key))

    return forward_plan


def load_migration_history(using: str = "default") -> MigrationHistory:
    """
    Load Django's migration history as factual data:
    - what is applied
    - what exists on disk
    - what is missing
    - what has been squashed
    - the resolved forward migration plan
    """
    loader = _load_loader(using)

    applied = _load_applied(loader)
    graph_nodes = _load_graph_nodes(loader)

    missing_files = applied - graph_nodes
    squashed_replacements = _load_squashed_replacements(loader)
    plan = _build_forward_plan(using)

    return MigrationHistory(
        applied=applied,
        graph_nodes=graph_nodes,
        missing_files=missing_files,
        squashed_replacements=squashed_replacements,
        plan=plan,
    )
