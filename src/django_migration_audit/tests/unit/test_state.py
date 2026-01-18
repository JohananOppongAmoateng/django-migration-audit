import pytest

from django_migration_audit.core.state import (
    ColumnState,
    TableState,
    SchemaState,
)


# ----------------------------
# ColumnState tests
# ----------------------------

def test_column_state_equality():
    c1 = ColumnState(name="age", db_type="integer", null=False)
    c2 = ColumnState(name="age", db_type="integer", null=False)

    assert c1 == c2


def test_column_state_inequality_on_type():
    c1 = ColumnState(name="age", db_type="integer", null=False)
    c2 = ColumnState(name="age", db_type="bigint", null=False)

    assert c1 != c2


def test_column_identity_is_stable():
    c = ColumnState(name="age", db_type="integer", null=True)

    assert c.identity() == ("age", "integer")


def test_column_is_immutable():
    c = ColumnState(name="age", db_type="integer", null=False)

    with pytest.raises(Exception):
        c.name = "years"


# ----------------------------
# TableState tests
# ----------------------------

def test_table_has_column():
    table = TableState(
        name="person",
        columns={
            "age": ColumnState("age", "integer", False),
        },
    )

    assert table.has_column("age") is True
    assert table.has_column("name") is False


def test_table_column_lookup():
    col = ColumnState("age", "integer", False)
    table = TableState(name="person", columns={"age": col})

    assert table.column("age") == col


def test_table_column_lookup_raises_keyerror():
    table = TableState(name="person", columns={})

    with pytest.raises(KeyError):
        table.column("missing")


def test_table_is_immutable():
    table = TableState(name="person", columns={})

    with pytest.raises(Exception):
        table.name = "people"


# ----------------------------
# SchemaState tests
# ----------------------------

def test_schema_has_table():
    schema = SchemaState(
        tables={
            "person": TableState(name="person"),
        }
    )

    assert schema.has_table("person") is True
    assert schema.has_table("order") is False


def test_schema_table_lookup():
    table = TableState(name="person")
    schema = SchemaState(tables={"person": table})

    assert schema.table("person") == table


def test_schema_table_lookup_raises_keyerror():
    schema = SchemaState(tables={})

    with pytest.raises(KeyError):
        schema.table("missing")


def test_schema_equality():
    schema1 = SchemaState(
        tables={
            "person": TableState(
                name="person",
                columns={
                    "age": ColumnState("age", "integer", False),
                },
            )
        }
    )

    schema2 = SchemaState(
        tables={
            "person": TableState(
                name="person",
                columns={
                    "age": ColumnState("age", "integer", False),
                },
            )
        }
    )

    assert schema1 == schema2


def test_schema_inequality_on_column():
    schema1 = SchemaState(
        tables={
            "person": TableState(
                name="person",
                columns={
                    "age": ColumnState("age", "integer", False),
                },
            )
        }
    )

    schema2 = SchemaState(
        tables={
            "person": TableState(
                name="person",
                columns={
                    "age": ColumnState("age", "bigint", False),
                },
            )
        }
    )

    assert schema1 != schema2


# ----------------------------
# ProjectState tests
# ----------------------------

def test_project_state_create_table():
    from django_migration_audit.core.state import ProjectState
    from django.db import models
    
    state = ProjectState()
    
    # Create a simple model
    fields = [
        ('id', models.AutoField(primary_key=True)),
        ('name', models.CharField(max_length=100)),
    ]
    
    state.create_table('myapp', 'Person', fields, {})
    
    schema = state.to_schema_state()
    assert schema.has_table('myapp_person')
    
    table = schema.table('myapp_person')
    assert table.has_column('id')
    assert table.has_column('name')


def test_project_state_create_table_with_custom_db_table():
    from django_migration_audit.core.state import ProjectState
    from django.db import models
    
    state = ProjectState()
    
    fields = [('id', models.AutoField(primary_key=True))]
    state.create_table('myapp', 'Person', fields, {'db_table': 'custom_people'})
    
    schema = state.to_schema_state()
    assert schema.has_table('custom_people')
    assert not schema.has_table('myapp_person')


def test_project_state_drop_table():
    from django_migration_audit.core.state import ProjectState
    from django.db import models
    
    state = ProjectState()
    
    # Create then drop
    fields = [('id', models.AutoField(primary_key=True))]
    state.create_table('myapp', 'Person', fields, {})
    state.drop_table('myapp', 'Person')
    
    schema = state.to_schema_state()
    assert not schema.has_table('myapp_person')


def test_project_state_add_column():
    from django_migration_audit.core.state import ProjectState
    from django.db import models
    
    state = ProjectState()
    
    # Create table
    fields = [('id', models.AutoField(primary_key=True))]
    state.create_table('myapp', 'Person', fields, {})
    
    # Add column
    email_field = models.EmailField(max_length=254)
    email_field.name = 'email'
    state.add_column('myapp', 'Person', email_field)
    
    schema = state.to_schema_state()
    table = schema.table('myapp_person')
    assert table.has_column('email')
    assert table.column('email').db_type == 'varchar'


def test_project_state_remove_column():
    from django_migration_audit.core.state import ProjectState
    from django.db import models
    
    state = ProjectState()
    
    # Create table with columns
    fields = [
        ('id', models.AutoField(primary_key=True)),
        ('name', models.CharField(max_length=100)),
    ]
    state.create_table('myapp', 'Person', fields, {})
    
    # Remove column
    state.remove_column('myapp', 'Person', 'name')
    
    schema = state.to_schema_state()
    table = schema.table('myapp_person')
    assert table.has_column('id')
    assert not table.has_column('name')


def test_project_state_alter_column():
    from django_migration_audit.core.state import ProjectState
    from django.db import models
    
    state = ProjectState()
    
    # Create table
    fields = [
        ('id', models.AutoField(primary_key=True)),
        ('age', models.IntegerField()),
    ]
    state.create_table('myapp', 'Person', fields, {})
    
    # Alter column type
    new_age_field = models.BigIntegerField()
    new_age_field.name = 'age'
    state.alter_column('myapp', 'Person', new_age_field)
    
    schema = state.to_schema_state()
    table = schema.table('myapp_person')
    assert table.column('age').db_type == 'bigint'


def test_project_state_field_type_mapping():
    from django_migration_audit.core.state import ProjectState
    from django.db import models
    
    state = ProjectState()
    
    # Test various field types
    fields = [
        ('auto_field', models.AutoField(primary_key=True)),
        ('big_auto', models.BigAutoField()),
        ('integer', models.IntegerField()),
        ('big_int', models.BigIntegerField()),
        ('char', models.CharField(max_length=50)),
        ('text', models.TextField()),
        ('boolean', models.BooleanField()),
        ('date', models.DateField()),
        ('datetime', models.DateTimeField()),
        ('decimal', models.DecimalField(max_digits=10, decimal_places=2)),
        ('float', models.FloatField()),
    ]
    
    state.create_table('myapp', 'AllTypes', fields, {})
    schema = state.to_schema_state()
    table = schema.table('myapp_alltypes')
    
    assert table.column('auto_field').db_type == 'integer'
    assert table.column('big_auto').db_type == 'bigint'
    assert table.column('integer').db_type == 'integer'
    assert table.column('big_int').db_type == 'bigint'
    assert table.column('char').db_type == 'varchar'
    assert table.column('text').db_type == 'text'
    assert table.column('boolean').db_type == 'boolean'
    assert table.column('date').db_type == 'date'
    assert table.column('datetime').db_type == 'timestamp'
    assert table.column('decimal').db_type == 'numeric'
    assert table.column('float').db_type == 'double precision'


