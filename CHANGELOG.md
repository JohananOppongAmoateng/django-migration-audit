# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added `CHANGELOG.md` and integrated into documentation.

### Changed
- Improved CI workflow configuration.




## [0.1.0]
### Added
- Core audit functionality comparing Migration History, Migration Code, and Live Database Schema.
- "Trust Verification" (Comparison A): Verifies consistency between migration history and migration code.
  - Detects missing migration files.
  - Detects modified migration files.
  - Detects fake-applied migrations.
  - Verifies squash replacements.
- "Reality Check" (Comparison B): Verifies consistency between expected schema (from code) and actual database schema.
  - Detects missing or extra tables.
  - Detects missing or extra columns.
  - Detects column type mismatches.
- `audit_migrations` management command.
  - Support for targeting specific databases (`--database`).
  - Support for running specific comparisons (`--comparison=a` or `--comparison=b`).
- Integration with `pre-commit` for automated checks.
- Comprehensive test suite including unit and integration tests.
