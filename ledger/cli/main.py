"""Command-line entry point for ledger."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ledger.importers.csv_importer import ImportError_, parse_statement
from ledger.models.budget import Budget, evaluate_budget
from ledger.models.transaction import Account
from ledger.models.money import Money
from ledger.reports.export import to_csv
from ledger.reports.summary import summarize_month
from ledger.rules.alerts import evaluate_alert
from ledger.rules.engine import CategoryRule, RuleEngine
from ledger.storage.budget_repository import BudgetRepository, RuleRepository
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


def _cmd_add_rule(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    repo = RuleRepository(conn)
    repo.add_rule(CategoryRule(args.priority, "description", args.pattern, args.category))
    print(f"Rule added: priority={args.priority} {args.pattern!r} -> {args.category!r}")
    return 0


def _cmd_categorize(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    txn_repo = TransactionRepository(conn)
    rule_repo = RuleRepository(conn)
    account = txn_repo.get_account(args.account_id)
    if account is None:
        print(f"error: unknown account {args.account_id!r}", file=sys.stderr)
        return 1

    transactions = txn_repo.list_transactions(account_id=args.account_id)
    engine = RuleEngine(rule_repo.list_rules())
    updated = engine.apply(transactions)
    for txn in transactions:
        if txn.category is not None and txn.transaction_id is not None:
            txn_repo.set_category(txn.transaction_id, txn.category)
    print(f"Categorized {updated} transactions.")
    return 0


def _cmd_set_budget(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    repo = BudgetRepository(conn)
    repo.upsert_budget(
        Budget(
            category=args.category,
            period=args.period,
            limit=Money.from_major(args.limit, args.currency),
            rollover=args.rollover,
        )
    )
    print(f"Budget set: {args.category} / {args.period} = {args.limit} {args.currency}")
    return 0


def _cmd_budget_status(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    txn_repo = TransactionRepository(conn)
    budget_repo = BudgetRepository(conn)

    budget = budget_repo.get_budget(args.category, args.period)
    if budget is None:
        print(f"error: no budget set for {args.category!r} in {args.period!r}", file=sys.stderr)
        return 1

    prior_periods = budget_repo.list_budget_periods(args.category, before_period=args.period)
    all_periods = prior_periods + [args.period]

    transactions = [
        t for t in txn_repo.list_transactions() if t.category == args.category
    ]
    spent_by_period: dict[str, Money] = {}
    for period in all_periods:
        total = Money.zero(budget.limit.currency)
        for txn in transactions:
            if txn.posted_on.strftime("%Y-%m") == period and txn.amount.is_negative():
                total = total - txn.amount
        spent_by_period[period] = total

    status = evaluate_budget(budget, spent_by_period, prior_periods)
    alert = evaluate_alert(status)

    print(f"Budget status for {args.category} / {args.period}")
    print(f"  Effective limit: {status.effective_limit}")
    print(f"  Spent:           {status.spent}")
    print(f"  Remaining:       {status.remaining}")
    print(f"  Alert:           {alert or 'none'}")
    return 0


def _cmd_tag(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    repo = TransactionRepository(conn)
    try:
        repo.add_tag(args.transaction_id, args.tag)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Tagged transaction {args.transaction_id} with {args.tag!r}.")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    repo = TransactionRepository(conn)
    account = repo.get_account(args.account_id)
    if account is None:
        print(f"error: unknown account {args.account_id!r}", file=sys.stderr)
        return 1

    transactions = repo.list_transactions(account_id=args.account_id)
    csv_text = to_csv(transactions)
    if args.out:
        Path(args.out).write_text(csv_text, encoding="utf-8")
        print(f"Exported {len(transactions)} transactions to {args.out}")
    else:
        print(csv_text, end="")
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

    p_add_rule = subparsers.add_parser("add-rule", help="add a categorization rule")
    p_add_rule.add_argument("pattern", help="glob pattern matched against description, e.g. 'AMAZON*'")
    p_add_rule.add_argument("category")
    p_add_rule.add_argument("--priority", type=int, default=100)
    p_add_rule.set_defaults(func=_cmd_add_rule)

    p_categorize = subparsers.add_parser("categorize", help="apply rules to uncategorized transactions")
    p_categorize.add_argument("account_id")
    p_categorize.set_defaults(func=_cmd_categorize)

    p_set_budget = subparsers.add_parser("set-budget", help="create or update a budget")
    p_set_budget.add_argument("category")
    p_set_budget.add_argument("period", help="YYYY-MM")
    p_set_budget.add_argument("limit")
    p_set_budget.add_argument("currency")
    p_set_budget.add_argument("--rollover", action="store_true")
    p_set_budget.set_defaults(func=_cmd_set_budget)

    p_budget_status = subparsers.add_parser("budget-status", help="show spend against a budget")
    p_budget_status.add_argument("category")
    p_budget_status.add_argument("period", help="YYYY-MM")
    p_budget_status.set_defaults(func=_cmd_budget_status)

    p_tag = subparsers.add_parser("tag", help="add a tag to a transaction")
    p_tag.add_argument("transaction_id", type=int)
    p_tag.add_argument("tag")
    p_tag.set_defaults(func=_cmd_tag)

    p_export = subparsers.add_parser("export", help="export an account's transactions to CSV")
    p_export.add_argument("account_id")
    p_export.add_argument("--out", help="output file path (defaults to stdout)")
    p_export.set_defaults(func=_cmd_export)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
