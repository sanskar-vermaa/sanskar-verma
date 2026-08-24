# Changelog

## Unreleased

### Added
- Money type with integer minor-unit arithmetic and explicit currency conversion.
- Transaction and Account domain models.
- SQLite-backed storage layer with idempotent transaction imports.
- CSV statement importer handling mixed date formats, encodings, and debit/credit columns.
- Priority-based categorization rule engine.
- Recurring-transaction detection with interval and amount tolerance.
- Envelope-style budget tracking with rollover.
- Budget alert thresholds (on_track / warning / over_budget).
- Monthly summary and CSV export reports.
- Account balance and multi-currency net worth calculation.
- Tagging support for transactions.
- CLI covering account setup, import, categorization, budgeting, tagging, and export.
- GitHub Actions CI running the test suite on Python 3.10-3.12.

### Fixed
- Recurring-detection description normalization now strips alphanumeric
  store/reference codes (e.g. `A1B2C3D4`), not just purely numeric tokens.
