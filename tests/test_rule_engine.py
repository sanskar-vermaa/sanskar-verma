from datetime import date

from ledger.models.money import Money
from ledger.models.transaction import Transaction
from ledger.rules.engine import CategoryRule, RuleEngine


def _txn(description: str) -> Transaction:
    return Transaction(
        account_id="acc1",
        posted_on=date(2024, 1, 1),
        amount=Money.from_major("-10.00", "USD"),
        description=description,
    )


def test_single_match():
    engine = RuleEngine([CategoryRule(1, "description", "STARBUCKS*", "Coffee")])
    assert engine.categorize(_txn("STARBUCKS #4021")) == "Coffee"


def test_no_match_returns_none():
    engine = RuleEngine([CategoryRule(1, "description", "STARBUCKS*", "Coffee")])
    assert engine.categorize(_txn("UBER TRIP")) is None


def test_lower_priority_number_wins():
    engine = RuleEngine(
        [
            CategoryRule(10, "description", "AMAZON*", "Shopping"),
            CategoryRule(1, "description", "AMAZON*", "Business Expense"),
        ]
    )
    assert engine.categorize(_txn("AMAZON MKTPLACE")) == "Business Expense"


def test_more_specific_pattern_wins_at_same_priority():
    engine = RuleEngine(
        [
            CategoryRule(1, "description", "AMAZON*", "Shopping"),
            CategoryRule(1, "description", "AMAZON MKTPLACE*", "Business Expense"),
        ]
    )
    assert engine.categorize(_txn("AMAZON MKTPLACE US")) == "Business Expense"


def test_apply_does_not_overwrite_manual_category():
    txn = _txn("STARBUCKS #4021")
    txn.category = "Manual Override"
    engine = RuleEngine([CategoryRule(1, "description", "STARBUCKS*", "Coffee")])
    updated = engine.apply([txn])
    assert updated == 0
    assert txn.category == "Manual Override"


def test_apply_categorizes_and_counts_updates():
    txns = [_txn("STARBUCKS #1"), _txn("STARBUCKS #2"), _txn("UNKNOWN VENDOR")]
    engine = RuleEngine([CategoryRule(1, "description", "STARBUCKS*", "Coffee")])
    updated = engine.apply(txns)
    assert updated == 2
    assert txns[2].category is None
