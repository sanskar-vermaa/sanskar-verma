"""SQLite schema management."""

from __future__ import annotations

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    currency TEXT NOT NULL,
    opening_balance_minor INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    posted_on TEXT NOT NULL,
    amount_minor INTEGER NOT NULL,
    currency TEXT NOT NULL,
    description TEXT NOT NULL,
    external_id TEXT,
    category TEXT,
    tags TEXT NOT NULL DEFAULT '',
    UNIQUE(account_id, external_id)
);

CREATE INDEX IF NOT EXISTS idx_transactions_account_date
    ON transactions(account_id, posted_on);

CREATE TABLE IF NOT EXISTS budgets (
    budget_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    period TEXT NOT NULL,
    limit_minor INTEGER NOT NULL,
    currency TEXT NOT NULL,
    rollover INTEGER NOT NULL DEFAULT 0,
    UNIQUE(category, period)
);

CREATE TABLE IF NOT EXISTS category_rules (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    priority INTEGER NOT NULL,
    field TEXT NOT NULL,
    pattern TEXT NOT NULL,
    category TEXT NOT NULL
);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn
