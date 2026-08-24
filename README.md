# Ledger

**Ledger** is a personal finance and envelope-budgeting toolkit for people who
want their bank statements turned into real insight without handing their
data to a SaaS product. It's a Python library and CLI, backed by a local
SQLite database.

Import a CSV export from your bank, let a rule engine auto-categorize the
noise, catch subscriptions and recurring payments automatically, and track
spend against envelope-style budgets that roll unspent (or overspent)
balance forward month to month.

## Features

- **CSV statement import** — handles inconsistent bank export formats:
  multiple date formats, single signed-amount columns *or* separate
  debit/credit columns, and both UTF-8 and Windows-1252 encoded files.
- **Idempotent imports** — re-importing the same statement twice never
  duplicates transactions.
- **Rule-based categorization** — glob-pattern rules with explicit
  priority and specificity-based tie-breaking, so overlapping rules
  resolve predictably.
- **Recurring transaction detection** — groups transactions by normalized
  description and flags series with consistent intervals and amounts
  (within tolerance), even when descriptions embed volatile store or
  reference codes.
- **Envelope budgeting** — budgets can roll unspent balance forward, or
  carry an overspend forward as a penalty against the next period.
- **Exact currency math** — money is stored as integer minor units, never
  floats, with explicit, auditable currency conversion.
- **A real CLI** — `init-account`, `import`, `add-rule`, `categorize`,
  `set-budget`, `budget-status`, `balance`, `tag`, `report`, `export`.
- **A web dashboard** — a small Flask app (`ledger serve`) over the same
  database: browse accounts and transactions, manage budgets and
  categorization rules, and trigger categorization from the browser. Dark,
  glassmorphic UI with gradient stat cards and a mouse-tracked tilt effect.

## Quick start

```bash
pip install -e .

ledger --db my.db init-account checking "Everyday Checking" USD
ledger --db my.db import checking examples/sample_statement.csv
ledger --db my.db add-rule "STARBUCKS*" Coffee
ledger --db my.db categorize checking
ledger --db my.db set-budget Coffee 2024-03 100.00 USD
ledger --db my.db budget-status Coffee 2024-03
ledger --db my.db report checking 2024-03

# or browse it in the web dashboard instead
ledger --db my.db serve
```

## Project layout

```
ledger/
├── models/       Money, Transaction, Account, Budget domain types
├── storage/      SQLite schema and repositories
├── importers/    CSV statement parsing
├── rules/        categorization engine, recurring detection, alerts
├── reports/      monthly summaries, balance, net worth, CSV export
├── web/          Flask dashboard (dark glassmorphic templates + static assets)
└── cli/          command-line entry point
tests/            unit and end-to-end tests (pytest)
```

See [docs/architecture.md](docs/architecture.md) for more on how the
pieces fit together and the design decisions behind them.

## Running tests

```bash
pip install pytest
pytest
```

## License

MIT — see [LICENSE](LICENSE).

## Author

Sanskar Verma
