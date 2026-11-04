"""Unit tests verifying deterministic SQL queries, pricing, installments, and shipping rules."""

from __future__ import annotations

import json

from src.agent.tools import (
    calculate_payment_and_shipping,
    lookup_customer_order,
    search_products_catalog,
)


def test_catalog_search_acoustic_guitars_under_1000() -> None:
    """Verify catalog search returns available acoustic guitars under R$ 1,000.00."""
    raw = search_products_catalog.invoke(
        {
            "query": "violão",
            "category_name": "Violões",
            "max_price_brl": 1000.0,
            "only_available": True,
        }
    )
    data = json.loads(raw)
    assert data["total_matches"] > 0
    for product in data["products"]:
        assert product["availability"] == "available"
        assert product["stock_quantity"] > 0
        assert product["pricing"]["effective_base_price_brl"] <= 1000.0


def test_non_cumulative_pix_discount_on_active_promotion() -> None:
    """Verify Rule 6.2: active promotional items do NOT receive an additional 5% PIX discount."""
    # Product 94 (Taylor 110e) has active promotion_id 24 (8% off)
    raw = search_products_catalog.invoke({"query": "Taylor 110e"})
    data = json.loads(raw)
    assert data["total_matches"] >= 1
    taylor = data["products"][0]
    pricing = taylor["pricing"]

    assert pricing["original_price_brl"] == 5999.0
    assert pricing["has_active_promotion"] is True
    assert pricing["active_promotion"]["discount_percent"] == 8.0
    # 5999 * 0.92 = 5519.08
    assert pricing["effective_base_price_brl"] == 5519.08
    # PIX price must equal promotional price (no extra 5% discount)
    assert pricing["pix_price_brl"] == 5519.08
    assert pricing["pix_5_percent_applied"] is False


def test_standard_pix_discount_on_non_promotional_product() -> None:
    """Verify Rule 3: products without active promotion get 5% off on PIX."""
    # Product 95 (Takamine GD20) has only an expired promotion (is_active=0)
    raw = search_products_catalog.invoke({"query": "Takamine GD20"})
    data = json.loads(raw)
    assert data["total_matches"] == 1
    takamine = data["products"][0]
    pricing = takamine["pricing"]

    assert pricing["original_price_brl"] == 2199.0
    assert pricing["has_active_promotion"] is False
    assert len(pricing["expired_promotions"]) >= 1
    # 2199 * 0.95 = 2089.05
    assert pricing["pix_price_brl"] == 2089.05
    assert pricing["pix_5_percent_applied"] is True


def test_installment_tiers_and_shipping_rules() -> None:
    """Verify Section 3.1 installment minimums (R$50/R$80/R$100) and Section 5.1 shipping."""
    # R$ 450.00 purchase:
    # - Up to 3x: min R$ 50 -> 3x of R$ 150.00 (allowed)
    # - 4x to 6x: min R$ 80 -> 5x of R$ 90.00 (allowed), 6x of R$ 75.00 (disallowed < 80)
    # - 7x to 12x: min R$ 100 -> all disallowed (< 100)
    raw = calculate_payment_and_shipping.invoke(
        {
            "amount_brl": 450.0,
            "has_active_promotion": False,
            "desired_installments": 6,
            "city": "Campo Grande",
        }
    )
    sim = json.loads(raw)
    assert sim["pix_option"]["final_amount_brl"] == 427.50
    assert sim["credit_card_summary"]["max_allowed_installments"] == 5
    assert sim["credit_card_summary"]["requested_installment_evaluation"]["allowed"] is False
    assert sim["combined_payment_eligible"] is False
    # Below R$ 500 in Campo Grande -> R$ 35.00 fixed motoboy fee
    assert sim["shipping"]["campo_grande_metropolitan"]["shipping_cost_brl"] == 35.0


def test_out_of_stock_and_discontinued_suggest_alternatives() -> None:
    """Verify Section 7.3: out-of-stock (ID 96) and discontinued (ID 113) return alternatives."""
    raw_oos = search_products_catalog.invoke({"query": "Giannini GF-3D"})
    oos_product = json.loads(raw_oos)["products"][0]
    assert oos_product["availability"] == "out_of_stock"
    assert len(oos_product["suggested_alternatives"]) > 0

    raw_disc = search_products_catalog.invoke({"query": "Shelby SN-7C"})
    disc_product = json.loads(raw_disc)["products"][0]
    assert disc_product["availability"] == "discontinued"
    assert len(disc_product["suggested_alternatives"]) > 0
