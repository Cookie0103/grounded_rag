from datetime import date

from sqlalchemy import and_

from app.db.policy_filter import MetaFilter


def test_filter_compiles_product_type_tier_and_exclusive_expiry_for_both_stores() -> None:
    filters = MetaFilter(
        product_line="home_loan",
        policy_type="repayment",
        as_of=date(2026, 11, 18),
        corpus_tier="S",
    )
    predicate = and_(*filters.sql_conditions())
    compiled = predicate.compile()
    sql = str(compiled)
    keyword = filters.elasticsearch_filters()

    assert "chunks.product_line =" in sql
    assert "chunks.policy_type =" in sql
    assert "chunks.corpus_tier =" in sql
    assert "chunks.effective_to >" in sql
    assert compiled.params["effective_to_1"] == filters.as_of
    assert {"term": {"product_line": "home_loan"}} in keyword
    assert {"term": {"policy_type": "repayment"}} in keyword
    assert {"term": {"corpus_tier": "S"}} in keyword
    assert {"range": {"effective_from": {"lte": "2026-11-18"}}} in keyword
