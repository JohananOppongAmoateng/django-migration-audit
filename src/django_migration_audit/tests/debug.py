"""
Django debug settings for django-migration-audit development.
Extends the base test settings with additional debugging features.
"""

import os

from .settings import *  # noqa: F401, F403

# Enable debug mode
DEBUG = True

# Parse SQLITE_DATABASES environment variable for multiple databases
sqlite_dbs = os.environ.get("SQLITE_DATABASES", "").split(",")
if sqlite_dbs and sqlite_dbs[0]:
    # Override DATABASES with multiple SQLite databases for testing
    DATABASES = {  # noqa: F405
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": sqlite_dbs[0].strip(),
        }
    }
    
    # Add additional databases if specified
    for idx, db_name in enumerate(sqlite_dbs[1:], start=1):
        if db_name.strip():
            DATABASES[f"test{idx}"] = {  # noqa: F405
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": db_name.strip(),
            }

# Show SQL queries in console
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
        },
    },
}
