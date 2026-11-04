"""Deterministic SQL and business-rule tools for the Emporio da Musica AI Agent."""

from __future__ import annotations

import json
import unicodedata
from datetime import date, datetime
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.database.ingest_csv import init_and_seed_database
from src.database.models import (
    Category,
    Customer,
    Order,
    OrderItem,
    Product,
    Promotion,
    get_session_factory,
)
from src.rag.retriever import retrieve_policy_context


def _normalize_text(value: str) -> str:
    """Remove accents and convert text to lowercase for resilient search matching."""
    norm = unicodedata.normalize("NFD", value.lower().strip())
    return "".join(ch for ch in norm if unicodedata.category(ch) != "Mn")


def _get_seeded_session() -> Session:
    """Ensure the SQLite database is initialized and return a new ORM session."""
    init_and_seed_database(force_reseed=False)
    factory = get_session_factory()
    return factory()


def _compute_product_pricing(product: Product) -> dict[str, Any]:
    """Calculate final product pricing enforcing non-cumulative promotion and PIX rules."""
    active_promos = [p for p in product.promotions if p.is_active]
    expired_promos = [p for p in product.promotions if not p.is_active]

    original_price = round(float(product.price_brl), 2)

    if active_promos:
        # Select highest active discount if multiple exist
        best_promo = max(active_promos, key=lambda p: p.discount_percent)
        discount_pct = float(best_promo.discount_percent)
        promotional_price = round(original_price * (1.0 - discount_pct / 100.0), 2)
        # Rule 6.2: PIX 5% discount is NOT cumulative with already promotional prices
        pix_price = promotional_price
        pix_additional_discount_applied = False
        active_promo_info = {
            "promotion_id": best_promo.promotion_id,
            "description": best_promo.description,
            "discount_percent": discount_pct,
            "promotional_price_brl": promotional_price,
        }
        effective_price = promotional_price
    else:
        discount_pct = 0.0
        promotional_price = None
        # Rule 3 & 6.2: 5% PIX discount applies only over standard table price
        pix_price = round(original_price * 0.95, 2)
        pix_additional_discount_applied = True
        active_promo_info = None
        effective_price = original_price

    return {
        "original_price_brl": original_price,
        "effective_base_price_brl": effective_price,
        "has_active_promotion": active_promo_info is not None,
        "active_promotion": active_promo_info,
        "expired_promotions": [
            {
                "promotion_id": ep.promotion_id,
                "description": ep.description,
                "discount_percent": float(ep.discount_percent),
                "status": "expired",
            }
            for ep in expired_promos
        ],
        "pix_price_brl": pix_price,
        "pix_5_percent_applied": pix_additional_discount_applied,
        "pricing_rule_note": (
            "Produto com promoção ativa: o desconto de 5% do PIX não é cumulativo "
            "(Seção 6.2 do Manual de Políticas)."
            if active_promo_info
            else "Preço de tabela: elegível a 5% de desconto à vista no PIX."
        ),
    }


def _find_similar_alternatives(
    session: Session, product: Product, limit: int = 3
) -> list[dict[str, Any]]:
    """Find active, in-stock alternative instruments in the same category."""
    candidates = (
        session.query(Product)
        .filter(
            Product.category_id == product.category_id,
            Product.product_id != product.product_id,
            Product.status == "active",
            Product.stock_quantity > 0,
        )
        .all()
    )
    # Sort by closeness in price to the requested product
    candidates.sort(key=lambda p: abs(float(p.price_brl) - float(product.price_brl)))
    alternatives: list[dict[str, Any]] = []
    for alt in candidates[:limit]:
        pricing = _compute_product_pricing(alt)
        alternatives.append(
            {
                "product_id": alt.product_id,
                "name": alt.name,
                "original_price_brl": pricing["original_price_brl"],
                "effective_price_brl": pricing["effective_base_price_brl"],
                "pix_price_brl": pricing["pix_price_brl"],
                "stock_quantity": alt.stock_quantity,
            }
        )
    return alternatives


class CatalogSearchInput(BaseModel):
    """Input schema for searching the musical instrument catalog."""

    query: str | None = Field(
        default=None,
        description="Keyword, brand, model, or instrument type (e.g., 'Takamine GD20', 'violão nylon', 'ukulele', 'guitarra').",
    )
    category_name: str | None = Field(
        default=None,
        description="Optional category filter (e.g., 'Violões', 'Guitarras', 'Baixos', 'Baterias', 'Teclados', 'Ukuleles').",
    )
    max_price_brl: float | None = Field(
        default=None,
        description="Maximum price in BRL (checks both table price and active promotional price).",
    )
    min_price_brl: float | None = Field(
        default=None,
        description="Minimum price in BRL.",
    )
    only_available: bool = Field(
        default=False,
        description="If True, returns only active products with stock_quantity > 0. Keep False when looking up a specific model so out-of-stock or discontinued status can be explained with alternatives.",
    )


@tool("search_products_catalog", args_schema=CatalogSearchInput)
def search_products_catalog(
    query: str | None = None,
    category_name: str | None = None,
    max_price_brl: float | None = None,
    min_price_brl: float | None = None,
    only_available: bool = False,
) -> str:
    """Search the Emporio da Musica catalog for musical instruments, prices, stock, promotions, and technical specs."""
    with _get_seeded_session() as session:
        all_products = session.query(Product).join(Category).all()
        categories = session.query(Category).all()

        norm_query = _normalize_text(query) if query else ""
        norm_cat = _normalize_text(category_name) if category_name else ""

        # Check if user asked for an existing category that has 0 registered products (e.g. Sopros / Cordas Orquestrais)
        matched_empty_categories: list[str] = []
        for cat in categories:
            cat_norm_name = _normalize_text(cat.name)
            cat_norm_desc = _normalize_text(cat.description or "")
            if (norm_cat and norm_cat in cat_norm_name) or (
                norm_query and (norm_query in cat_norm_name or norm_query in cat_norm_desc)
            ):
                if not cat.products:
                    matched_empty_categories.append(f"{cat.name} ({cat.description})")

        results: list[dict[str, Any]] = []
        query_tokens = [
            tok
            for tok in norm_query.split()
            if len(tok) >= 2 and tok not in {"de", "da", "do", "com", "para", "ate", "um", "uma"}
        ]

        # Common singular/plural stem normalizations in Portuguese
        normalized_tokens: list[str] = []
        for tok in query_tokens:
            if tok in {"violoes", "violao"}:
                normalized_tokens.append("viol")
            elif tok in {"guitarras", "guitarra"}:
                normalized_tokens.append("guitarr")
            elif tok in {"ukuleles", "ukulele"}:
                normalized_tokens.append("ukulele")
            elif tok in {"baixos", "baixo", "contrabaixo", "contrabaixos"}:
                normalized_tokens.append("baix")
            elif tok in {"baterias", "bateria"}:
                normalized_tokens.append("bateri")
            elif tok in {"teclados", "teclado", "pianos", "piano", "sintetizador"}:
                normalized_tokens.append("teclad")
            else:
                normalized_tokens.append(tok)

        for prod in all_products:
            if only_available and not prod.is_available:
                continue

            if norm_cat:
                prod_cat_norm = _normalize_text(prod.category.name)
                if norm_cat not in prod_cat_norm and prod_cat_norm[:5] not in norm_cat:
                    continue

            pricing = _compute_product_pricing(prod)
            effective_price = pricing["effective_base_price_brl"]

            if max_price_brl is not None and effective_price > max_price_brl and prod.price_brl > max_price_brl:
                continue
            if min_price_brl is not None and effective_price < min_price_brl and prod.price_brl < min_price_brl:
                continue

            searchable_blob = _normalize_text(
                f"{prod.name} {prod.description} {prod.category.name} {prod.specs_json}"
            )

            if normalized_tokens:
                token_hits = sum(1 for tok in normalized_tokens if tok in searchable_blob)
                if token_hits == 0:
                    continue
                match_ratio = token_hits / len(normalized_tokens)
                # Require all tokens if short query, or majority match
                if len(normalized_tokens) <= 2 and token_hits < len(normalized_tokens):
                    continue
            else:
                match_ratio = 1.0

            availability_label = (
                "available"
                if prod.is_available
                else (
                    "discontinued"
                    if prod.status == "discontinued"
                    else ("coming_soon" if prod.status == "coming_soon" else "out_of_stock")
                )
            )

            item_payload: dict[str, Any] = {
                "product_id": prod.product_id,
                "name": prod.name,
                "category": prod.category.name,
                "status": prod.status,
                "availability": availability_label,
                "stock_quantity": prod.stock_quantity,
                "description": prod.description,
                "specs": prod.specs,
                "pricing": pricing,
                "_match_score": match_ratio,
            }

            if not prod.is_available:
                item_payload["suggested_alternatives"] = _find_similar_alternatives(
                    session, prod, limit=3
                )

            results.append(item_payload)

        results.sort(
            key=lambda r: (
                -r["_match_score"],
                0 if r["availability"] == "available" else 1,
                r["pricing"]["effective_base_price_brl"],
            )
        )

        for r in results:
            r.pop("_match_score", None)

        response_payload = {
            "total_matches": len(results),
            "empty_registered_categories_matched": matched_empty_categories,
            "products": results[:15],
        }
        return json.dumps(response_payload, ensure_ascii=False, indent=2)


class PaymentSimulationInput(BaseModel):
    """Input schema for calculating payment methods, installments, and shipping."""

    amount_brl: float = Field(
        ...,
        description="Base purchase amount in BRL (use effective_base_price_brl from product pricing).",
    )
    has_active_promotion: bool = Field(
        default=False,
        description="True if the product already has an active promotion (prevents cumulative 5% PIX discount).",
    )
    desired_installments: int | None = Field(
        default=None,
        description="Optional specific number of credit card installments requested by the customer (1 to 12).",
    )
    city: str | None = Field(
        default=None,
        description="Customer city for shipping calculation (e.g., 'Campo Grande', 'Dourados').",
    )


@tool("calculate_payment_and_shipping", args_schema=PaymentSimulationInput)
def calculate_payment_and_shipping(
    amount_brl: float,
    has_active_promotion: bool = False,
    desired_installments: int | None = None,
    city: str | None = None,
) -> str:
    """Calculate exact PIX discount, credit card installment tiers (Section 3.1), payment combination, and shipping rules (Section 5)."""
    base_amount = round(float(amount_brl), 2)

    # Rule 3 & 6.2: PIX 5% discount only when no active promotion is applied
    if has_active_promotion:
        pix_amount = base_amount
        pix_discount_brl = 0.0
        pix_explanation = (
            "Desconto de 5% no PIX não aplicável pois o produto já está com preço promocional "
            "(promoções não são cumulativas conforme Seção 6.2)."
        )
    else:
        pix_discount_brl = round(base_amount * 0.05, 2)
        pix_amount = round(base_amount - pix_discount_brl, 2)
        pix_explanation = "5% de desconto à vista sobre o preço de tabela."

    # Rule 3.1: Installment rules
    # - 1x to 3x: interest-free, minimum installment R$ 50.00
    # - 4x to 6x: interest-free, minimum installment R$ 80.00
    # - 7x to 12x: interest-free, minimum installment R$ 100.00
    valid_installment_options: list[dict[str, Any]] = []
    for n in range(1, 13):
        installment_value = round(base_amount / n, 2)
        if n <= 3:
            min_required = 50.0
        elif n <= 6:
            min_required = 80.0
        else:
            min_required = 100.0

        is_allowed = n == 1 or installment_value >= min_required
        valid_installment_options.append(
            {
                "installments": n,
                "installment_value_brl": installment_value,
                "min_required_brl": min_required if n > 1 else 0.0,
                "allowed": is_allowed,
            }
        )

    allowed_only = [opt for opt in valid_installment_options if opt["allowed"]]
    max_installments = allowed_only[-1]["installments"] if allowed_only else 1

    requested_check: dict[str, Any] | None = None
    if desired_installments is not None:
        if 1 <= desired_installments <= 12:
            requested_check = valid_installment_options[desired_installments - 1]
        else:
            requested_check = {
                "installments": desired_installments,
                "allowed": False,
                "reason": "O parcelamento máximo na loja é em até 12x sem juros.",
            }

    # Rule 5: Shipping calculation
    shipping_info: dict[str, Any] = {
        "campo_grande_metropolitan": {
            "shipping_cost_brl": 0.0 if base_amount >= 500.0 else 35.0,
            "is_free_shipping": base_amount >= 500.0,
            "delivery_time_business_days": "1 a 3 dias úteis",
            "carrier": "Motoboy próprio (contato telefônico prévio antes da entrega)",
        },
        "other_cities_options": [
            {"modality": "SEDEX (Correios)", "delivery_time": "2 a 5 dias úteis", "insurance": "Incluído"},
            {"modality": "Jadlog (Package)", "delivery_time": "3 a 8 dias úteis", "insurance": "Incluído"},
            {"modality": "PAC (Correios)", "delivery_time": "5 a 12 dias úteis", "insurance": "Incluído"},
        ],
    }

    if city:
        norm_city = _normalize_text(city)
        shipping_info["evaluated_city"] = city
        shipping_info["is_campo_grande"] = "campo grande" in norm_city

    payload = {
        "base_amount_brl": base_amount,
        "pix_option": {
            "final_amount_brl": pix_amount,
            "discount_brl": pix_discount_brl,
            "rule": pix_explanation,
        },
        "credit_card_summary": {
            "max_allowed_installments": max_installments,
            "max_installment_plan": allowed_only[-1] if allowed_only else None,
            "all_allowed_tiers": allowed_only,
            "requested_installment_evaluation": requested_check,
        },
        "combined_payment_eligible": base_amount > 2000.0,
        "combined_payment_rule": (
            "Permitida combinação de formas de pagamento (ex.: PIX + cartão) pois a compra supera R$ 2.000,00."
            if base_amount > 2000.0
            else "Combinação de formas de pagamento (PIX + cartão) permitida apenas para compras acima de R$ 2.000,00."
        ),
        "shipping": shipping_info,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


class OrderLookupInput(BaseModel):
    """Input schema for looking up customer orders and evaluating return/exchange eligibility."""

    order_id: int | None = Field(
        default=None,
        description="Numeric order ID (e.g., 1, 8, 17).",
    )
    tracking_code: str | None = Field(
        default=None,
        description="Tracking code (e.g., 'BRJL5544332BR').",
    )
    customer_identifier: str | None = Field(
        default=None,
        description="Customer name, email, or phone number (e.g., 'Pedro Henrique', 'lucas.mendes@jmail.com').",
    )
    reference_date: str | None = Field(
        default=None,
        description="Optional ISO reference date (YYYY-MM-DD) to evaluate 7-day and 30-day return windows.",
    )


@tool("lookup_customer_order", args_schema=OrderLookupInput)
def lookup_customer_order(
    order_id: int | None = None,
    tracking_code: str | None = None,
    customer_identifier: str | None = None,
    reference_date: str | None = None,
) -> str:
    """Look up order status, items, tracking codes, and return/exchange policy eligibility by order_id, tracking_code, or customer name/email/phone."""
    with _get_seeded_session() as session:
        orders: list[Order] = []

        if order_id is not None:
            found = session.query(Order).filter(Order.order_id == order_id).first()
            if found:
                orders.append(found)

        if not orders and tracking_code:
            clean_track = tracking_code.strip().upper()
            found = (
                session.query(Order)
                .filter(Order.tracking_code.ilike(f"%{clean_track}%"))
                .all()
            )
            orders.extend(found)

        if not orders and customer_identifier:
            norm_ident = _normalize_text(customer_identifier)
            all_customers = session.query(Customer).all()
            matched_cust_ids = [
                c.customer_id
                for c in all_customers
                if norm_ident in _normalize_text(c.name)
                or norm_ident in _normalize_text(c.email)
                or norm_ident in _normalize_text(c.phone)
            ]
            if matched_cust_ids:
                orders = (
                    session.query(Order)
                    .filter(Order.customer_id.in_(matched_cust_ids))
                    .order_by(Order.order_date.desc())
                    .all()
                )

        if not orders:
            return json.dumps(
                {
                    "found": False,
                    "message": "Nenhum pedido encontrado para os critérios informados.",
                },
                ensure_ascii=False,
            )

        ref_dt: date | None = None
        if reference_date:
            try:
                ref_dt = datetime.strptime(reference_date.strip(), "%Y-%m-%d").date()
            except ValueError:
                ref_dt = None

        serialized_orders: list[dict[str, Any]] = []
        for ord_obj in orders:
            items_detail = [
                {
                    "product_id": item.product_id,
                    "product_name": item.product.name if item.product else "Unknown",
                    "quantity": item.quantity,
                    "unit_table_price_brl": item.product.price_brl if item.product else None,
                    "product_current_status": item.product.status if item.product else None,
                }
                for item in ord_obj.items
            ]

            eligibility_notes: dict[str, Any] = {
                "regret_return_rule": "Até 7 dias corridos após o recebimento (frete de devolução por conta da loja, reembolso em até 10 dias úteis).",
                "preference_exchange_rule": "Até 7 dias corridos na embalagem original sem uso.",
                "defect_exchange_rule": "Até 30 dias corridos após a compra diretamente na loja; após 30 dias, acionar garantia do fabricante (garantia legal de 90 dias a partir do recebimento).",
            }

            if ref_dt and ord_obj.estimated_delivery and ord_obj.status == "delivered":
                try:
                    deliv_dt = datetime.strptime(ord_obj.estimated_delivery, "%Y-%m-%d").date()
                    days_since_delivery = (ref_dt - deliv_dt).days
                    eligibility_notes["days_since_estimated_delivery"] = days_since_delivery
                    eligibility_notes["within_7_day_regret_window"] = 0 <= days_since_delivery <= 7
                    eligibility_notes["within_90_day_legal_warranty"] = 0 <= days_since_delivery <= 90
                except ValueError:
                    pass

            serialized_orders.append(
                {
                    "order_id": ord_obj.order_id,
                    "order_date": ord_obj.order_date,
                    "status": ord_obj.status,
                    "total_brl": ord_obj.total_brl,
                    "payment_method": ord_obj.payment_method,
                    "tracking_code": ord_obj.tracking_code,
                    "estimated_delivery": ord_obj.estimated_delivery,
                    "notes": ord_obj.notes,
                    "customer": {
                        "customer_id": ord_obj.customer.customer_id,
                        "name": ord_obj.customer.name,
                        "email": ord_obj.customer.email,
                        "phone": ord_obj.customer.phone,
                        "city": ord_obj.customer.city,
                    },
                    "items": items_detail,
                    "policy_windows": eligibility_notes,
                }
            )

        return json.dumps(
            {"found": True, "total_orders": len(serialized_orders), "orders": serialized_orders},
            ensure_ascii=False,
            indent=2,
        )


class PolicyLookupInput(BaseModel):
    """Input schema for querying the Emporio da Musica policy manual via RAG."""

    question: str = Field(
        ...,
        description="Natural language question or topic to search in the store policy manual (e.g., 'horário de funcionamento', 'direito de arrependimento devolução', 'garantia', 'acessórios cordas cabos').",
    )
    top_k: int = Field(
        default=4,
        ge=1,
        le=8,
        description="Number of relevant policy sections to retrieve.",
    )


@tool("consult_store_policies", args_schema=PolicyLookupInput)
def consult_store_policies(question: str, top_k: int = 4) -> str:
    """Search the official Emporio da Musica Policy and Procedures Manual (PDF) for store hours, address, returns, exchanges, shipping, warranties, LGPD, and scope rules."""
    return retrieve_policy_context(query=question, top_k=top_k)


AGENT_TOOLS = [
    search_products_catalog,
    calculate_payment_and_shipping,
    lookup_customer_order,
    consult_store_policies,
]
