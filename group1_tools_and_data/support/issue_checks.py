"""
issue_checks.py
===============
WHAT THIS FILE DOES
    Two investigation helpers used by the BillingAgent and DeliveryAgent.

    1. check_duplicate_payment()
         Looks for evidence of a double charge for an order.
         IMPORTANT HONESTY NOTE: orders.csv stores only ONE payment status per
         order and there is no transaction ledger. So this tool can find
         *signs* of duplication (the same order listed twice, or two orders for
         the same customer with the same amount) but it can NEVER prove a
         customer was charged twice. It therefore always says that transaction
         verification is required and that a refund must NOT be promised
         (policy rule: rules.billing).

    2. check_delivery_issue()
         Compares what the customer claims ("never arrived", "delayed",
         "it arrived") with what the delivery record says, and returns a
         verdict such as DELIVERED_NOT_RECEIVED or STATUS_CONFLICT.

    Both return plain dictionaries with a list of VERIFIED FACTS (each tied to
    a source file/line) so the final report can separate facts from guesses.
"""

from __future__ import annotations

import re

from .data_loader import SupportDataStore, clean_id
from .policy_tools import policy_reference

NOT_DELIVERED_STATES = {"PROCESSING", "NOT_SHIPPED", "IN_TRANSIT"}

# Phrases are checked in this order: "never arrived" must win over "arrived".
_NOT_RECEIVED = re.compile(
    r"never\s+(arrived|came|received)|not\s+(received|arrived)|"
    r"(did\s*n['o]?t|did\s+not|haven['’]?t|have\s+not|hasn['’]?t|has\s+not)\s+"
    r"(receive|received|arrive|arrived|get|got)|missing|lost",
    re.IGNORECASE,
)
_DELAYED = re.compile(r"delay|late\b|still\s+waiting|not\s+yet|where\s+is\s+my", re.IGNORECASE)
_RECEIVED = re.compile(r"\b(arrived|received|got\s+it|came)\b", re.IGNORECASE)


def classify_delivery_claim(message: str) -> str:
    """Read the customer's words: NOT_RECEIVED, DELAYED, RECEIVED or UNKNOWN."""
    text = message or ""
    if _NOT_RECEIVED.search(text):
        return "NOT_RECEIVED"
    if _DELAYED.search(text):
        return "DELAYED"
    if _RECEIVED.search(text):
        return "RECEIVED"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Duplicate payment check
# ---------------------------------------------------------------------------
def check_duplicate_payment(store: SupportDataStore, order_id: str) -> dict:
    """
    Look for evidence of a duplicate payment on an order.

    Verdicts:
      ORDER_NOT_FOUND          - no such order
      DUPLICATE_ORDER_RECORDS  - the same order ID is listed more than once
      POSSIBLE_DUPLICATE_ORDER - same customer has another order, same amount
      NOT_CONFIRMED            - records show nothing that proves a double charge
    In every case: requires_transaction_verification=True and
    refund_can_be_promised=False.
    """
    oid = clean_id(order_id)
    order = store.get_order(oid)
    if order is None:
        return {"verdict": "ORDER_NOT_FOUND", "order_id": oid,
                "requires_transaction_verification": True,
                "refund_can_be_promised": False}

    refs = store.order_refs.get(oid, [order.source_ref])
    same_amount = [
        o for o in store.orders_for_customer(order.customer_id)
        if o.order_id != oid and o.total_inr == order.total_inr
    ]

    facts = [
        {"fact": f"Order {oid} payment_status is {order.payment_status} "
                 f"for INR {order.total_inr}.", "source": order.source_ref},
        {"fact": f"Order {oid} refund_status is {order.refund_status}.",
         "source": order.source_ref},
    ]
    limits = [
        "orders.csv has one payment status per order and no transaction ledger, "
        "so a second charge cannot be proven or disproven from these files."
    ]

    if len(refs) > 1:
        verdict = "DUPLICATE_ORDER_RECORDS"
        facts.append({"fact": f"Order {oid} is listed {len(refs)} times.",
                      "source": ", ".join(refs)})
    elif same_amount:
        verdict = "POSSIBLE_DUPLICATE_ORDER"
        for o in same_amount:
            facts.append({"fact": f"Order {o.order_id} has the same customer and "
                                  f"amount (INR {o.total_inr}).", "source": o.source_ref})
    else:
        verdict = "NOT_CONFIRMED"

    if order.refund_status != "NONE":
        facts.append({"fact": f"A refund is already recorded: {order.refund_status}.",
                      "source": order.source_ref})

    return {
        "verdict": verdict,
        "order_id": oid,
        "verified_facts": facts,
        "limitations": limits,
        "requires_transaction_verification": True,   # policy: rules.billing
        "refund_can_be_promised": False,             # we never confirm refunds
        "policy_reference": policy_reference("rules.billing"),
    }


# ---------------------------------------------------------------------------
# Delivery issue check
# ---------------------------------------------------------------------------
def check_delivery_issue(
    store: SupportDataStore, order_id: str, customer_message: str = ""
) -> dict:
    """
    Compare the customer's delivery claim with the delivery record.

    Verdicts:
      ORDER_NOT_FOUND
      DELIVERED_NOT_RECEIVED  - record says delivered, customer says no
                                (policy requires a delivery investigation)
      NOT_YET_DELIVERED       - customer has nothing, record agrees
      IN_PROGRESS_DELAY       - customer says delayed, record shows not delivered
                                (no promised date exists, so lateness is unverified)
      ALREADY_DELIVERED       - customer says delayed but record says delivered
      CONSISTENT_RECEIVED     - customer got it and record says delivered
      STATUS_CONFLICT         - customer got it but record says NOT delivered
      NO_DELIVERY_CLAIM       - message is not about delivery; status only
    """
    oid = clean_id(order_id)
    order = store.get_order(oid)
    if order is None:
        return {"verdict": "ORDER_NOT_FOUND", "order_id": oid,
                "needs_investigation": False}

    claim = classify_delivery_claim(customer_message)
    delivered = order.delivery_status == "DELIVERED"
    not_delivered = order.delivery_status in NOT_DELIVERED_STATES

    if claim == "NOT_RECEIVED" and delivered:
        verdict, investigate = "DELIVERED_NOT_RECEIVED", True
    elif claim == "NOT_RECEIVED" and not_delivered:
        verdict, investigate = "NOT_YET_DELIVERED", False
    elif claim == "DELAYED" and not_delivered:
        verdict, investigate = "IN_PROGRESS_DELAY", False
    elif claim == "DELAYED" and delivered:
        verdict, investigate = "ALREADY_DELIVERED", False
    elif claim == "RECEIVED" and delivered:
        verdict, investigate = "CONSISTENT_RECEIVED", False
    elif claim == "RECEIVED" and not_delivered:
        verdict, investigate = "STATUS_CONFLICT", False
    else:
        verdict, investigate = "NO_DELIVERY_CLAIM", False

    facts = [{
        "fact": f"Order {oid} delivery_status is {order.delivery_status}"
                + (f", delivered_at {order.delivered_at.isoformat()}."
                   if order.delivered_at else " (no delivery date recorded)."),
        "source": order.source_ref,
    }]
    return {
        "verdict": verdict,
        "order_id": oid,
        "customer_claim": claim,
        "delivery_status": order.delivery_status,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        "needs_investigation": investigate,
        "verified_facts": facts,
        "policy_reference": policy_reference("rules.delivery"),
    }
