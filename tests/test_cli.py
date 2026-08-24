import io
import contextlib

from ledger.cli.main import main


def _run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = main(argv)
    return code, buf.getvalue()


def test_full_workflow(tmp_path):
    db_path = str(tmp_path / "test.db")
    csv_path = tmp_path / "statement.csv"
    csv_path.write_text(
        "Date,Description,Amount,Id\n"
        "2024-03-01,PAYCHECK,3000.00,t1\n"
        "2024-03-05,STARBUCKS #10,-5.50,t2\n"
        "2024-03-06,STARBUCKS #11,-6.00,t3\n"
    )

    code, _ = _run(["--db", db_path, "init-account", "acc1", "Checking", "USD"])
    assert code == 0

    code, out = _run(["--db", db_path, "import", "acc1", str(csv_path)])
    assert code == 0
    assert "Imported 3 transactions" in out

    code, _ = _run(["--db", db_path, "add-rule", "STARBUCKS*", "Coffee"])
    assert code == 0

    code, out = _run(["--db", db_path, "categorize", "acc1"])
    assert code == 0
    assert "Categorized 2 transactions" in out

    code, out = _run(["--db", db_path, "report", "acc1", "2024-03"])
    assert code == 0
    assert "Income:   3000.00 USD" in out
    assert "Coffee" in out


def test_budget_status_workflow(tmp_path):
    db_path = str(tmp_path / "test.db")
    csv_path = tmp_path / "statement.csv"
    csv_path.write_text(
        "Date,Description,Amount,Id\n"
        "2024-03-05,STARBUCKS #10,-50.00,t1\n"
    )

    _run(["--db", db_path, "init-account", "acc1", "Checking", "USD"])
    _run(["--db", db_path, "import", "acc1", str(csv_path)])
    _run(["--db", db_path, "add-rule", "STARBUCKS*", "Coffee"])
    _run(["--db", db_path, "categorize", "acc1"])
    _run(["--db", db_path, "set-budget", "Coffee", "2024-03", "100.00", "USD"])

    code, out = _run(["--db", db_path, "budget-status", "Coffee", "2024-03"])
    assert code == 0
    assert "Remaining:       50.00 USD" in out


def test_import_fails_for_unknown_account(tmp_path):
    db_path = str(tmp_path / "test.db")
    csv_path = tmp_path / "statement.csv"
    csv_path.write_text("Date,Description,Amount\n2024-01-01,X,-1.00\n")

    code, _ = _run(["--db", db_path, "import", "nope", str(csv_path)])
    assert code == 1
