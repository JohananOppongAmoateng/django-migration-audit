"""
Migration 0002: adds Tag and PostTag models.

Tag categorises posts. PostTag is the explicit many-to-many join table.
Using an explicit model (instead of Django's implicit M2M join table) means
every table appears as a CreateModel operation in migrations — making the
expected schema fully auditable without special M2M handling.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Tag",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="PostTag",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="post_tags",
                        to="core.post",
                    ),
                ),
                (
                    "tag",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="post_tags",
                        to="core.tag",
                    ),
                ),
            ],
        ),
        migrations.AlterUniqueTogether(
            name="posttag",
            unique_together={("post", "tag")},
        ),
    ]
