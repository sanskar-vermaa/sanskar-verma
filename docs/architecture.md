# Architecture

## Layers

Ledger is organized into five layers that each depend only on the ones
below them:

```
cli        -> argument parsing, orchestrates everything else
storage    -> SQLite schema + repositories (translate rows <-> models)
rules      -> categorization, recurring detection, alerts (pure functions)
importers  -> parse external formats (CSV) into domain models
models     -> Money, Transaction, Account, Budget (no I/O, no dependencies)
```

`models` has zero dependencies on the rest of the codebase, which is what
makes the `rules` layer testable without a database: every function in
`rules/` takes and returns plain domain objects.

## Why money is integer minor units, not float or bare Decimal

Floats lose precision in ways that compound silently across many
transactions. Bare `Decimal` is better but doesn't enforce a currency's
minor-unit precision (you can accidentally end up with `10.567` USD).
`Money` stores an integer count of minor units (cents, paise, fils — see
`_MINOR_UNIT_EXPONENT` in `models/money.py` for currencies with 0 or 3
decimal places) and only exposes `Decimal` at the boundary
(`to_major`/`from_major`). Arithmetic between two `Money` values of
different currencies raises rather than silently producing a nonsense
number — currency conversion is always an explicit, deliberate call.

## Why imports are idempotent by (account_id, external_id)

Bank exports are often re-downloaded (e.g. "download last 90 days"
overlapping a previous export). The repository upserts on the
`(account_id, external_id)` unique constraint, so importing the same
statement twice is a no-op for rows that already exist. Transactions
without a stable external id (many CSV exports don't provide one) are
NOT deduplicated — SQLite treats `NULL` as distinct in a unique
constraint, so repeated imports of external-id-less transactions
correctly create separate rows, since there's no reliable way to tell a
repeated cash withdrawal from a re-imported one.

## Why recurring detection normalizes descriptions the way it does

Bank-generated descriptions embed volatile tokens: store numbers,
authorization codes, dates. A naive exact-match grouping would treat
every occurrence of a subscription as a one-off. `rules/recurring.py`
tokenizes the description and drops any token of length >= 3 that
contains a digit, on the assumption that volatile identifiers are
alphanumeric (`A1B2C3D4`) far more often than purely numeric — pure
words like "NETFLIX" or "COM" survive, codes don't.

## Why budgets use a "rollover chain" instead of a running balance column

Storing a running balance directly would mean every budget mutation has
to correctly update a derived total, which is a common source of drift
bugs when edits happen out of order. Instead, `evaluate_budget` recomputes
the effective limit for a period by walking every prior period in the
chain each time. It's more computation, but it can never drift from the
underlying transaction data, and it's trivial to audit: the rollover
amount for any period is always reproducible from the budgets and
transactions alone.
