"""
Django management command to audit migrations.

This command performs both Comparison A (trust verification) and
Comparison B (reality check) to verify migration consistency.
"""

from django.core.management.base import BaseCommand
from django.db import connections

from django_migration_audit.core.loader import load_migration_history
from django_migration_audit.core.extractor import MigrationExtractor
from django_migration_audit.core.introspection import introspect_schema
from django_migration_audit.invariants.base import (
    NoMissingMigrationFiles,
    SquashMigrationsProperlyReplaced,
    AllExpectedTablesExist,
    NoUnexpectedTables,
    AllExpectedColumnsExist,
)


class Command(BaseCommand):
    help = "Audit Django migrations for consistency between history, code, and database schema"

    def add_arguments(self, parser):
        parser.add_argument(
            '--database',
            default='default',
            help='Database to audit (default: default)',
        )
        parser.add_argument(
            '--comparison',
            choices=['a', 'b', 'all'],
            default='all',
            help='Which comparison to run: a (trust), b (reality), or all (default: all)',
        )

    def handle(self, *args, **options):
        database = options['database']
        comparison = options['comparison']

        self.stdout.write(self.style.SUCCESS(f'\n=== Django Migration Audit ==='))
        self.stdout.write(f'Database: {database}\n')

        # Load migration history and code (Inputs 1 & 2)
        self.stdout.write('Loading migration history and code...')
        history = load_migration_history(using=database)
        
        self.stdout.write(f'  Applied migrations: {len(history.applied)}')
        self.stdout.write(f'  Migration files on disk: {len(history.graph_nodes)}')
        self.stdout.write(f'  Missing files: {len(history.missing_files)}')
        self.stdout.write(f'  Squashed replacements: {len(history.squashed_replacements)}\n')

        violations = []

        # Comparison A: Trust Verification
        if comparison in ['a', 'all']:
            self.stdout.write(self.style.WARNING('🔍 Comparison A: Trust Verification'))
            self.stdout.write('   (Migration history ↔ Migration code)\n')
            
            violations.extend(self._run_comparison_a(history))

        # Comparison B: Reality Check
        if comparison in ['b', 'all']:
            self.stdout.write(self.style.WARNING('🔍 Comparison B: Reality Check'))
            self.stdout.write('   (Expected schema ↔ Actual schema)\n')
            
            violations.extend(self._run_comparison_b(history, database))

        # Summary
        self.stdout.write('\n=== Summary ===')
        if not violations:
            self.stdout.write(self.style.SUCCESS('No violations found! Migration state is consistent.'))
        else:
            error_count = sum(1 for v in violations if v.severity.value == 'error')
            warning_count = sum(1 for v in violations if v.severity.value == 'warning')
            
            self.stdout.write(self.style.ERROR(f'Found {len(violations)} violation(s):'))
            self.stdout.write(f'   Errors: {error_count}')
            self.stdout.write(f'   Warnings: {warning_count}\n')
            
            for violation in violations:
                if violation.severity.value == 'error':
                    self.stdout.write(self.style.ERROR(f'  {violation}'))
                else:
                    self.stdout.write(self.style.WARNING(f'  {violation}'))

    def _run_comparison_a(self, history):
        """Run Comparison A invariants (trust verification)."""
        invariants = [
            NoMissingMigrationFiles(),
            SquashMigrationsProperlyReplaced(),
        ]
        
        violations = []
        for invariant in invariants:
            self.stdout.write(f'  Checking: {invariant.name}...')
            inv_violations = invariant.check(migration_history=history)
            violations.extend(inv_violations)
            
            if inv_violations:
                self.stdout.write(self.style.ERROR(f'    ❌ {len(inv_violations)} violation(s)'))
            else:
                self.stdout.write(self.style.SUCCESS(f'    ✅ Pass'))
        
        self.stdout.write('')
        return violations

    def _run_comparison_b(self, history, database):
        """Run Comparison B invariants (reality check)."""
        # Build expected schema from migrations
        self.stdout.write('  Building expected schema from migrations...')
        connection = connections[database]
        loader = connection.loader if hasattr(connection, 'loader') else None
        
        if not loader:
            from django.db.migrations.loader import MigrationLoader
            loader = MigrationLoader(connection)
        
        extractor = MigrationExtractor(
            migration_graph=loader.graph,
            applied_nodes={(m.app, m.name) for m in history.applied}
        )
        expected_schema = extractor.build_state()
        
        # Introspect actual schema
        self.stdout.write('  Introspecting actual database schema...')
        actual_schema = introspect_schema(using=database)
        
        self.stdout.write(f'    Expected tables: {len(expected_schema.tables)}')
        self.stdout.write(f'    Actual tables: {len(actual_schema.tables)}\n')
        
        # Run invariants
        invariants = [
            AllExpectedTablesExist(),
            NoUnexpectedTables(),
            AllExpectedColumnsExist(),
        ]
        
        violations = []
        for invariant in invariants:
            self.stdout.write(f'  Checking: {invariant.name}...')
            inv_violations = invariant.check(
                expected_schema=expected_schema,
                actual_schema=actual_schema
            )
            violations.extend(inv_violations)
            
            if inv_violations:
                self.stdout.write(self.style.ERROR(f'    ❌ {len(inv_violations)} violation(s)'))
            else:
                self.stdout.write(self.style.SUCCESS(f'    ✅ Pass'))
        
        self.stdout.write('')
        return violations
