"""
Migration 0003: adds a view_count field to Post.

Tracks how many times each post has been viewed. This migration is used by
the demo_fake_migration scenario to show what happens when a migration is
marked as applied (via --fake) without the SQL actually running.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_add_tags"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="view_count",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
