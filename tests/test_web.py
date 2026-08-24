import pytest

from ledger.cli.main import main as cli_main
from ledger.web.app import create_app


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "web.db")
    csv_path = tmp_path / "statement.csv"
    csv_path.write_text(
        "Date,Description,Amount,Id\n"
        "2024-03-01,PAYCHECK,2000.00,t1\n"
        "2024-03-05,STARBUCKS #10,-6.00,t2\n"
    )
    cli_main(["--db", db_path, "init-account", "acc1", "Checking", "USD"])
    cli_main(["--db", db_path, "import", "acc1", str(csv_path)])

    app = create_app(db_path)
    app.config["TESTING"] = True
    return app.test_client()


def test_index_lists_accounts(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"acc1" in resp.data


def test_account_detail_shows_transactions(client):
    resp = client.get("/accounts/acc1")
    assert resp.status_code == 200
    assert b"PAYCHECK" in resp.data
    assert b"STARBUCKS" in resp.data


def test_account_detail_unknown_account_404s(client):
    resp = client.get("/accounts/nope")
    assert resp.status_code == 404


def test_categorize_applies_rules(client):
    client.post("/rules/new", data={"pattern": "STARBUCKS*", "category": "Coffee", "priority": "1"})
    resp = client.post("/accounts/acc1/categorize", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Coffee" in resp.data


def test_budget_creation_and_listing(client):
    resp = client.post(
        "/budgets/new",
        data={"category": "Coffee", "period": "2024-03", "limit": "50.00", "currency": "USD"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Coffee" in resp.data
    assert b"2024-03" in resp.data


def test_rule_creation_and_listing(client):
    resp = client.post(
        "/rules/new",
        data={"pattern": "AMAZON*", "category": "Shopping", "priority": "5"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"AMAZON*" in resp.data
    assert b"Shopping" in resp.data
