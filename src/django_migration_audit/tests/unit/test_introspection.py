"""Unit tests for database introspection functionality."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from collections import namedtuple

from django_migration_audit.core.introspection import (
    introspect_schema,
    _introspect_table_columns,
    _normalize_db_type,
)
from django_migration_audit.core.state import SchemaState, TableState, ColumnState


# Mock FieldInfo namedtuple (used by Django's introspection)
FieldInfo = namedtuple('FieldInfo', ['name', 'type_code', 'display_size', 'internal_size', 'precision', 'scale', 'null_ok', 'default'])


class TestIntrospectSchema:
    """Test cases for introspect_schema function."""

    @patch('django_migration_audit.core.introspection.connections')
    def test_introspect_schema_empty_database(self, mock_connections):
        """Test introspecting an empty database."""
        # Setup mocks
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_introspection = Mock()
        mock_introspection.table_names.return_value = []
        mock_connection.introspection = mock_introspection
        
        mock_connections.__getitem__.return_value = mock_connection
        
        # Execute
        schema = introspect_schema(using='default')
        
        # Verify
        assert isinstance(schema, SchemaState)
        assert len(schema.tables) == 0

    @patch('django_migration_audit.core.introspection.connections')
    def test_introspect_schema_single_table(self, mock_connections):
        """Test introspecting a database with a single table."""
        # Setup mocks
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_introspection = Mock()
        mock_introspection.table_names.return_value = ['myapp_person']
        mock_introspection.get_table_description.return_value = [
            FieldInfo('id', 1, None, None, None, None, False, None),
            FieldInfo('name', 2, None, None, None, None, False, None),
        ]
        mock_introspection.get_field_type.side_effect = lambda code, _: {
            1: 'AutoField',
            2: 'CharField',
        }.get(code, 'unknown')
        
        mock_connection.introspection = mock_introspection
        mock_connections.__getitem__.return_value = mock_connection
        
        # Execute
        schema = introspect_schema(using='default')
        
        # Verify
        assert schema.has_table('myapp_person')
        table = schema.table('myapp_person')
        assert table.has_column('id')
        assert table.has_column('name')
        assert table.column('id').db_type == 'integer'
        assert table.column('name').db_type == 'varchar'

    @patch('django_migration_audit.core.introspection.connections')
    def test_introspect_schema_multiple_tables(self, mock_connections):
        """Test introspecting a database with multiple tables."""
        # Setup mocks
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_introspection = Mock()
        mock_introspection.table_names.return_value = ['myapp_author', 'myapp_post']
        
        def get_table_description(cursor, table_name):
            if table_name == 'myapp_author':
                return [
                    FieldInfo('id', 1, None, None, None, None, False, None),
                    FieldInfo('name', 2, None, None, None, None, False, None),
                ]
            elif table_name == 'myapp_post':
                return [
                    FieldInfo('id', 1, None, None, None, None, False, None),
                    FieldInfo('title', 2, None, None, None, None, False, None),
                ]
            return []
        
        mock_introspection.get_table_description.side_effect = get_table_description
        mock_introspection.get_field_type.side_effect = lambda code, _: {
            1: 'AutoField',
            2: 'CharField',
        }.get(code, 'unknown')
        
        mock_connection.introspection = mock_introspection
        mock_connections.__getitem__.return_value = mock_connection
        
        # Execute
        schema = introspect_schema(using='default')
        
        # Verify
        assert len(schema.tables) == 2
        assert schema.has_table('myapp_author')
        assert schema.has_table('myapp_post')

    @patch('django_migration_audit.core.introspection.connections')
    def test_introspect_schema_filters_django_tables(self, mock_connections):
        """Test that Django internal tables are filtered out."""
        # Setup mocks
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_introspection = Mock()
        mock_introspection.table_names.return_value = [
            'myapp_person',
            'django_migrations',
            'django_content_type',
            'django_session',
            'auth_permission',
            'auth_group',
            'auth_group_permissions',
            'auth_user_groups',
            'auth_user_user_permissions',
        ]
        
        def get_table_description(cursor, table_name):
            if table_name == 'myapp_person':
                return [FieldInfo('id', 1, None, None, None, None, False, None)]
            return []
        
        mock_introspection.get_table_description.side_effect = get_table_description
        mock_introspection.get_field_type.return_value = 'AutoField'
        
        mock_connection.introspection = mock_introspection
        mock_connections.__getitem__.return_value = mock_connection
        
        # Execute
        schema = introspect_schema(using='default')
        
        # Verify - only user table should be included
        assert len(schema.tables) == 1
        assert schema.has_table('myapp_person')
        assert not schema.has_table('django_migrations')
        assert not schema.has_table('auth_permission')

    @patch('django_migration_audit.core.introspection.connections')
    def test_introspect_schema_custom_database(self, mock_connections):
        """Test introspecting a custom database."""
        # Setup mocks
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_introspection = Mock()
        mock_introspection.table_names.return_value = []
        mock_connection.introspection = mock_introspection
        
        mock_connections.__getitem__.return_value = mock_connection
        
        # Execute
        introspect_schema(using='secondary')
        
        # Verify correct database was used
        mock_connections.__getitem__.assert_called_once_with('secondary')


class TestIntrospectTableColumns:
    """Test cases for _introspect_table_columns function."""

    def test_introspect_table_columns_basic(self):
        """Test introspecting basic table columns."""
        mock_cursor = Mock()
        mock_introspection = Mock()
        
        table_description = [
            FieldInfo('id', 1, None, None, None, None, False, None),
            FieldInfo('name', 2, None, None, None, None, False, None),
            FieldInfo('email', 3, None, None, None, None, True, None),
        ]
        
        mock_introspection.get_table_description.return_value = table_description
        mock_introspection.get_field_type.side_effect = lambda code, _: {
            1: 'AutoField',
            2: 'CharField',
            3: 'EmailField',
        }.get(code, 'unknown')
        
        # Execute
        columns = _introspect_table_columns(mock_cursor, mock_introspection, 'test_table')
        
        # Verify
        assert 'id' in columns
        assert 'name' in columns
        assert 'email' in columns
        
        assert columns['id'].name == 'id'
        assert columns['id'].db_type == 'integer'
        assert columns['id'].null is False
        
        assert columns['name'].name == 'name'
        assert columns['name'].db_type == 'varchar'
        assert columns['name'].null is False
        
        assert columns['email'].name == 'email'
        assert columns['email'].db_type == 'varchar'
        assert columns['email'].null is True

    def test_introspect_table_columns_with_defaults(self):
        """Test introspecting columns with default values."""
        mock_cursor = Mock()
        mock_introspection = Mock()
        
        table_description = [
            FieldInfo('id', 1, None, None, None, None, False, None),
            FieldInfo('status', 2, None, None, None, None, False, 'active'),
            FieldInfo('count', 3, None, None, None, None, False, 0),
        ]
        
        mock_introspection.get_table_description.return_value = table_description
        mock_introspection.get_field_type.side_effect = lambda code, _: {
            1: 'AutoField',
            2: 'CharField',
            3: 'IntegerField',
        }.get(code, 'unknown')
        
        # Execute
        columns = _introspect_table_columns(mock_cursor, mock_introspection, 'test_table')
        
        # Verify
        assert columns['id'].default is None
        assert columns['status'].default == 'active'
        assert columns['count'].default == '0'

    def test_introspect_table_columns_various_types(self):
        """Test introspecting columns with various field types."""
        mock_cursor = Mock()
        mock_introspection = Mock()
        
        table_description = [
            FieldInfo('auto_field', 1, None, None, None, None, False, None),
            FieldInfo('big_int', 2, None, None, None, None, False, None),
            FieldInfo('text_field', 3, None, None, None, None, False, None),
            FieldInfo('bool_field', 4, None, None, None, None, False, None),
            FieldInfo('date_field', 5, None, None, None, None, False, None),
            FieldInfo('datetime_field', 6, None, None, None, None, False, None),
        ]
        
        mock_introspection.get_table_description.return_value = table_description
        mock_introspection.get_field_type.side_effect = lambda code, _: {
            1: 'AutoField',
            2: 'BigIntegerField',
            3: 'TextField',
            4: 'BooleanField',
            5: 'DateField',
            6: 'DateTimeField',
        }.get(code, 'unknown')
        
        # Execute
        columns = _introspect_table_columns(mock_cursor, mock_introspection, 'test_table')
        
        # Verify types are normalized
        assert columns['auto_field'].db_type == 'integer'
        assert columns['big_int'].db_type == 'bigint'
        assert columns['text_field'].db_type == 'text'
        assert columns['bool_field'].db_type == 'boolean'
        assert columns['date_field'].db_type == 'date'
        assert columns['datetime_field'].db_type == 'timestamp'


class TestNormalizeDbType:
    """Test cases for _normalize_db_type function."""

    def test_normalize_db_type_auto_field(self):
        """Test normalizing AutoField type."""
        mock_introspection = Mock()
        mock_introspection.get_field_type.return_value = 'AutoField'
        
        result = _normalize_db_type(1, mock_introspection)
        
        assert result == 'integer'

    def test_normalize_db_type_big_auto_field(self):
        """Test normalizing BigAutoField type."""
        mock_introspection = Mock()
        mock_introspection.get_field_type.return_value = 'BigAutoField'
        
        result = _normalize_db_type(1, mock_introspection)
        
        assert result == 'bigint'

    def test_normalize_db_type_integer_field(self):
        """Test normalizing IntegerField type."""
        mock_introspection = Mock()
        mock_introspection.get_field_type.return_value = 'IntegerField'
        
        result = _normalize_db_type(1, mock_introspection)
        
        assert result == 'integer'

    def test_normalize_db_type_big_integer_field(self):
        """Test normalizing BigIntegerField type."""
        mock_introspection = Mock()
        mock_introspection.get_field_type.return_value = 'BigIntegerField'
        
        result = _normalize_db_type(1, mock_introspection)
        
        assert result == 'bigint'

    def test_normalize_db_type_char_field(self):
        """Test normalizing CharField type."""
        mock_introspection = Mock()
        mock_introspection.get_field_type.return_value = 'CharField'
        
        result = _normalize_db_type(1, mock_introspection)
        
        assert result == 'varchar'

    def test_normalize_db_type_text_field(self):
        """Test normalizing TextField type."""
        mock_introspection = Mock()
        mock_introspection.get_field_type.return_value = 'TextField'
        
        result = _normalize_db_type(1, mock_introspection)
        
        assert result == 'text'

    def test_normalize_db_type_boolean_field(self):
        """Test normalizing BooleanField type."""
        mock_introspection = Mock()
        mock_introspection.get_field_type.return_value = 'BooleanField'
        
        result = _normalize_db_type(1, mock_introspection)
        
        assert result == 'boolean'

    def test_normalize_db_type_date_field(self):
        """Test normalizing DateField type."""
        mock_introspection = Mock()
        mock_introspection.get_field_type.return_value = 'DateField'
        
        result = _normalize_db_type(1, mock_introspection)
        
        assert result == 'date'

    def test_normalize_db_type_datetime_field(self):
        """Test normalizing DateTimeField type."""
        mock_introspection = Mock()
        mock_introspection.get_field_type.return_value = 'DateTimeField'
        
        result = _normalize_db_type(1, mock_introspection)
        
        assert result == 'timestamp'

    def test_normalize_db_type_decimal_field(self):
        """Test normalizing DecimalField type."""
        mock_introspection = Mock()
        mock_introspection.get_field_type.return_value = 'DecimalField'
        
        result = _normalize_db_type(1, mock_introspection)
        
        assert result == 'numeric'

    def test_normalize_db_type_float_field(self):
        """Test normalizing FloatField type."""
        mock_introspection = Mock()
        mock_introspection.get_field_type.return_value = 'FloatField'
        
        result = _normalize_db_type(1, mock_introspection)
        
        assert result == 'double precision'

    def test_normalize_db_type_email_field(self):
        """Test normalizing EmailField type."""
        mock_introspection = Mock()
        mock_introspection.get_field_type.return_value = 'EmailField'
        
        result = _normalize_db_type(1, mock_introspection)
        
        assert result == 'varchar'

    def test_normalize_db_type_url_field(self):
        """Test normalizing URLField type."""
        mock_introspection = Mock()
        mock_introspection.get_field_type.return_value = 'URLField'
        
        result = _normalize_db_type(1, mock_introspection)
        
        assert result == 'varchar'

    def test_normalize_db_type_foreign_key(self):
        """Test normalizing ForeignKey type."""
        mock_introspection = Mock()
        mock_introspection.get_field_type.return_value = 'ForeignKey'
        
        result = _normalize_db_type(1, mock_introspection)
        
        assert result == 'integer'

    def test_normalize_db_type_one_to_one_field(self):
        """Test normalizing OneToOneField type."""
        mock_introspection = Mock()
        mock_introspection.get_field_type.return_value = 'OneToOneField'
        
        result = _normalize_db_type(1, mock_introspection)
        
        assert result == 'integer'

    def test_normalize_db_type_unknown_type(self):
        """Test normalizing unknown type."""
        mock_introspection = Mock()
        mock_introspection.get_field_type.return_value = 'CustomField'
        
        result = _normalize_db_type(1, mock_introspection)
        
        assert result == 'customfield'

    def test_normalize_db_type_exception_handling(self):
        """Test handling exceptions during type normalization."""
        mock_introspection = Mock()
        mock_introspection.get_field_type.side_effect = KeyError('Unknown type')
        
        result = _normalize_db_type(999, mock_introspection)
        
        assert result == 'unknown'

    def test_normalize_db_type_attribute_error(self):
        """Test handling AttributeError during type normalization."""
        mock_introspection = Mock()
        mock_introspection.get_field_type.side_effect = AttributeError('No such attribute')
        
        result = _normalize_db_type(999, mock_introspection)
        
        assert result == 'unknown'
