# Contributing

## Setup

```bash
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

## Code layout conventions

- `ledger/models/` must stay free of I/O — no database access, no file
  reads. If a model needs persistence, add a repository under
  `ledger/storage/` instead of adding methods to the model itself.
- `ledger/rules/` functions should be pure: given the same input
  transactions, they return the same output every time. This is what
  keeps recurring-detection and categorization testable without a
  database fixture.
- New CLI commands go in `ledger/cli/main.py`: add a `_cmd_*` function
  and register it as a subparser in `build_parser()`.

## Tests

Every new module should ship with a corresponding `tests/test_*.py`.
Prefer testing through the public function/class interface over
reaching into internals. For CLI changes, add or extend a scenario in
`tests/test_cli.py` that exercises the command end-to-end.
