from datetime import date

from mock_core.seed_data import SEED, build_seed, fingerprint, summarize


def test_fixed_seed_reproduces_every_row_and_covers_business_cases() -> None:
    rows = build_seed(SEED)

    assert fingerprint(rows) == fingerprint(build_seed(SEED))
    assert summarize(rows) == {
        "customers": 300,
        "agents": 20,
        "max_installments": 420,
        "pair_loan_customers": 1,
        "delinquent_contracts": 1,
        "paid_contracts": 1,
        "fixed_expiring_within_year": 1,
        "partial_fixed_contracts": 1,
    }
    assert ("A001", "C0001") in rows["agent_customer"]
    assert ("A020", "C0001") in rows["agent_customer"]
    assert ("A002", "C0001") not in rows["agent_customer"]


def test_level_payment_schedule_returns_all_of_the_original_principal() -> None:
    rows = build_seed(SEED)
    contract = next(row for row in rows["loan_contracts"] if row[0] == "L0001")
    schedule = [row for row in rows["repayment_schedule"] if row[0] == "L0001"]

    assert [(row[1], row[2]) for row in schedule[::419]] == [
        (1, date(2024, 2, 15)),
        (420, date(2059, 1, 15)),
    ]
    assert len({row[3] for row in schedule[:-1]}) == 1
    assert all(row[3] == row[4] + row[5] for row in schedule)
    assert sum(row[4] for row in schedule) == contract[3]
