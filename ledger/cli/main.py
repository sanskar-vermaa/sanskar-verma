"""Command-line entry point for ledger."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ledger.importers.csv_importer import ImportError_, parse_statement
from ledger.models.transaction import Account
from ledger.models.money import Money
from ledger.reports.summary import summarize_month
from ledger.rules.engine import RuleEngine
from ledger.storage.db import connect
from ledger.storage.repository import TransactionRepository


def _cmd_init_account(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    repo = TransactionRepository(conn)
    repo.upsert_account(
        Account(
            account_id=args.account_id,
            name=args.name,
            currency=args.currency,
            opening_balance=Money.from_major(args.opening_balance, args.currency),
        )
    )
    print(f"Account {args.account_id!r} ready ({args.currency}).")
    return 0


def _cmd_import(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    repo = TransactionRepository(conn)
    account = repo.get_account(args.account_id)
    if account is None:
        print(f"error: unknown account {args.account_id!r}, run init-account first", file=sys.stderr)
        return 1

    raw = Path(args.csv_path).read_bytes()
    try:
        transactions = list(parse_statement(raw, args.account_id, account.currency))
    except ImportError_ as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    imported = 0
    for txn in transactions:
        repo.add_transaction(txn)
        imported += 1
    print(f"Imported {imported} transactions into {args.account_id!r}.")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    repo = TransactionRepository(conn)
    account = repo.get_account(args.account_id)
    if account is None:
        print(f"error: unknown account {args.account_id!r}", file=sys.stderr)
        return 1

    transactions = repo.list_transactions(account_id=args.account_id)
    summary = summarize_month(transactions, args.period, account.currency)

    print(f"Summary for {args.account_id} / {summary.period}")
    print(f"  Income:   {summary.income}")
    print(f"  Expenses: {summary.expenses}")
    print(f"  Net:      {summary.net}")
    print("  By category:")
    for cat in summary.by_category:
        print(f"    {cat.category:<20} {cat.total} ({cat.count} txns)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ledger")
    parser.add_argument("--db", default="ledger.db", help="path to the SQLite database file")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_init = subparsers.add_parser("init-account", help="create or update an account")
    p_init.add_argument("account_id")
    p_init.add_argument("name")
    p_init.add_argument("currency")
    p_init.add_argument("--opening-balance", dest="opening_balance", default="0")
    p_init.set_defaults(func=_cmd_init_account)

    p_import = subparsers.add_parser("import", help="import a CSV statement")
    p_import.add_argument("account_id")
    p_import.add_argument("csv_path")
    p_import.set_defaults(func=_cmd_import)

    p_report = subparsers.add_parser("report", help="print a monthly summary")
    p_report.add_argument("account_id")
    p_report.add_argument("period", help="YYYY-MM")
    p_report.set_defaults(func=_cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
