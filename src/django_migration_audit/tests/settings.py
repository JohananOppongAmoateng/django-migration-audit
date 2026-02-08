"""
Django settings for django-migration-audit tests.
"""

import os

# Build paths inside the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "test-secret-key-for-django-migration-audit"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django_migration_audit",
    "django_migration_audit.tests",
]

MIDDLEWARE = []

ROOT_URLCONF = None

TEMPLATES = []

# Database
# https://docs.djangoproject.com/en/stable/ref/settings/#databases

# Get database configuration from environment variables
DB_BACKEND = os.environ.get("DB_BACKEND", "sqlite3")
DB_NAME = os.environ.get("DB_NAME", ":memory:")
DB_USER = os.environ.get("DB_USER", "")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_HOST = os.environ.get("DB_HOST", "")
DB_PORT = os.environ.get("DB_PORT", "")

# Map backend names to Django database engines
BACKEND_MAPPING = {
    "sqlite3": "django.db.backends.sqlite3",
    "postgresql": "django.db.backends.postgresql",
    "mysql": "django.db.backends.mysql",
}

DATABASES = {
    "default": {
        "ENGINE": BACKEND_MAPPING.get(DB_BACKEND, "django.db.backends.sqlite3"),
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASSWORD,
        "HOST": DB_HOST,
        "PORT": DB_PORT,
    }
}

# Internationalization
# https://docs.djangoproject.com/en/stable/topics/i18n/
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Default primary key field type
# https://docs.djangoproject.com/en/stable/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Test settings
USE_TZ = True
