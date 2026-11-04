"""Integration tests validating RAG policy retrieval and customer order lookup scenarios."""

from __future__ import annotations

import json

from src.agent.tools import consult_store_policies, lookup_customer_order


def test_order_lookup_and_regret_window_evaluation() -> None:
    """Verify order #7 lookup and 7-day regret return window calculation (Section 4.1)."""
    # Order 7 was delivered on 2026-02-17
    raw_within = lookup_customer_order.invoke(
        {"order_id": 7, "reference_date": "2026-02-20"}
    )
    data_within = json.loads(raw_within)
    assert data_within["found"] is True
    order_info = data_within["orders"][0]
    assert order_info["customer"]["name"] == "Letícia Gonçalves Rocha"
    assert order_info["policy_windows"]["days_since_estimated_delivery"] == 3
    assert order_info["policy_windows"]["within_7_day_regret_window"] is True

    # 15 days after delivery -> outside 7-day regret window, inside 90-day legal warranty
    raw_expired = lookup_customer_order.invoke(
        {"order_id": 7, "reference_date": "2026-03-04"}
    )
    data_expired = json.loads(raw_expired)
    windows_expired = data_expired["orders"][0]["policy_windows"]
    assert windows_expired["within_7_day_regret_window"] is False
    assert windows_expired["within_90_day_legal_warranty"] is True


def test_rag_policy_retrieval_for_accessories_and_scope() -> None:
    """Verify RAG retrieves Section 1 / 7.1 when asked about musical accessories."""
    context = consult_store_policies.invoke(
        {"question": "Vocês vendem encordoamento, palhetas, cabos, pedais ou amplificadores?"}
    )
    assert "exclusivamente com instrumentos musicais" in context.lower()
    assert "acessórios" in context.lower()


def test_rag_policy_retrieval_for_store_hours_and_address() -> None:
    """Verify RAG retrieves store address and operating hours (Sections 1.2 and 2)."""
    context = consult_store_policies.invoke(
        {"question": "Qual o endereço da loja e o horário de funcionamento aos sábados?"}
    )
    assert "14 de maio" in context.lower()
    assert "09:00" in context.lower()
