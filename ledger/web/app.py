"""Web dashboard for Ledger.

A thin Flask layer over the same repository and report functions the CLI
uses -- no business logic lives here, it's purely presentation and
request handling. Every route reads from the same SQLite database the
CLI writes to, so `ledger import ...` on the command line and the
dashboard always agree.
"""

from __future__ import annotations

from datetime import date

from flask import Flask, abort, redirect, render_template, request, url_for

from ledger.models.budget import Budget, evaluate_budget
from ledger.models.money import Money
from ledger.reports.balance import current_balance
from ledger.reports.summary import summarize_month
from ledger.rules.alerts import evaluate_alert
from ledger.rules.engine import CategoryRule, RuleEngine
from ledger.storage.budget_repository import BudgetRepository, RuleRepository
from ledger.storage.db import connect
from ledger.storage.repository import TransactionRepository


def create_app(db_path: str = "ledger.db") -> Flask:
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path

    def _repos():
        conn = connect(app.config["DB_PATH"])
        return (
            TransactionRepository(conn),
            BudgetRepository(conn),
            RuleRepository(conn),
        )

    @app.route("/")
    def index():
        txn_repo, _, _ = _repos()
        conn = connect(app.config["DB_PATH"])
        rows = conn.execute("SELECT account_id FROM accounts ORDER BY account_id").fetchall()
        accounts = []
        for row in rows:
            account = txn_repo.get_account(row["account_id"])
            balance = current_balance(account, txn_repo.list_transactions(account_id=account.account_id))
            accounts.append((account, balance))
        return render_template("index.html", accounts=accounts)

    @app.route("/accounts/<account_id>")
    def account_detail(account_id: str):
        txn_repo, _, _ = _repos()
        account = txn_repo.get_account(account_id)
        if account is None:
            abort(404)
        transactions = txn_repo.list_transactions(account_id=account_id)
        balance = current_balance(account, transactions)
        period = request.args.get("period", date.today().strftime("%Y-%m"))
        summary = None
        if any(t.posted_on.strftime("%Y-%m") == period for t in transactions):
            summary = summarize_month(transactions, period, account.currency)
        return render_template(
            "account.html",
            account=account,
            transactions=list(reversed(transactions)),
            balance=balance,
            period=period,
            summary=summary,
        )

    @app.route("/accounts/<account_id>/categorize", methods=["POST"])
    def categorize(account_id: str):
        txn_repo, _, rule_repo = _repos()
        account = txn_repo.get_account(account_id)
        if account is None:
            abort(404)
        transactions = txn_repo.list_transactions(account_id=account_id)
        engine = RuleEngine(rule_repo.list_rules())
        engine.apply(transactions)
        for txn in transactions:
            if txn.category is not None and txn.transaction_id is not None:
                txn_repo.set_category(txn.transaction_id, txn.category)
        return redirect(url_for("account_detail", account_id=account_id))

    @app.route("/budgets")
    def budgets():
        _, budget_repo, _ = _repos()
        conn = connect(app.config["DB_PATH"])
        rows = conn.execute("SELECT category, period FROM budgets ORDER BY period DESC").fetchall()
        statuses = []
        txn_repo = TransactionRepository(conn)
        all_txns = txn_repo.list_transactions()
        for row in rows:
            budget = budget_repo.get_budget(row["category"], row["period"])
            prior_periods = budget_repo.list_budget_periods(budget.category, before_period=budget.period)
            spent_by_period: dict[str, Money] = {}
            for period in prior_periods + [budget.period]:
                total = Money.zero(budget.limit.currency)
                for txn in all_txns:
                    if (
                        txn.category == budget.category
                        and txn.posted_on.strftime("%Y-%m") == period
                        and txn.amount.is_negative()
                    ):
                        total = total - txn.amount
                spent_by_period[period] = total
            status = evaluate_budget(budget, spent_by_period, prior_periods)
            statuses.append((status, evaluate_alert(status)))
        return render_template("budgets.html", statuses=statuses)

    @app.route("/budgets/new", methods=["POST"])
    def new_budget():
        _, budget_repo, _ = _repos()
        budget_repo.upsert_budget(
            Budget(
                category=request.form["category"],
                period=request.form["period"],
                limit=Money.from_major(request.form["limit"], request.form["currency"]),
                rollover=bool(request.form.get("rollover")),
            )
        )
        return redirect(url_for("budgets"))

    @app.route("/rules")
    def rules():
        _, _, rule_repo = _repos()
        return render_template("rules.html", rules=rule_repo.list_rules())

    @app.route("/rules/new", methods=["POST"])
    def new_rule():
        _, _, rule_repo = _repos()
        rule_repo.add_rule(
            CategoryRule(
                priority=int(request.form["priority"]),
                field="description",
                pattern=request.form["pattern"],
                category=request.form["category"],
            )
        )
        return redirect(url_for("rules"))

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
