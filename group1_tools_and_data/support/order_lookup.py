"""
order_lookup.py
===============
WHAT THIS FILE DOES
    Order lookup functionality. It answers: "Which order is this ticket about,
    and what do our records say about it?"

    Main pieces:
      * extract_order_ids()      - finds order IDs like O1001 inside a message
      * lookup_order()           - looks up ONE order and returns its facts
                                   together with the file/line they came from
      * resolve_order_for_ticket() - decides which order(s) a ticket refers to

    Safety rules built in (from the assignment's edge cases):
      * Unknown order ID      -> reported as not found; nothing is invented.
      * Order owned by someone else -> flagged (OWNERSHIP_MISMATCH).
      * Customer has several orders -> we NEVER pick one at random; we only
        use an order the customer actually wrote in the message.
      * Missing customer ID   -> reported, ownership cannot be verified.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .data_loader import Order, SupportDataStore, Ticket, clean_id

# An order ID looks like the letter O followed by digits (O1001).
ORDER_ID_PATTERN = re.compile(r"\bO\d{3,}\b", re.IGNORECASE)
_VALID_ORDER_ID = re.compile(r"^O\d{3,}$")


def extract_order_ids(text: str) -> list[str]:
    """Return every order ID mentioned in the text (upper-case, no repeats)."""
    found: list[str] = []
    for match in ORDER_ID_PATTERN.findall(text or ""):
        oid = match.upper()
        if oid not in found:
            found.append(oid)
    return found


def order_to_dict(order: Order) -> dict:
    """Convert an Order to a plain dictionary (JSON friendly)."""
    return {
        "order_id": order.order_id,
        "customer_id": order.customer_id,
        "total_inr": order.total_inr,
        "payment_status": order.payment_status,
        "delivery_status": order.delivery_status,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        "refund_status": order.refund_status,
    }


def lookup_order(store: SupportDataStore, order_id: str) -> dict:
    """
    Look up one order by ID.

    Returns a dictionary. When found:
        {"found": True, "order": {...}, "source_ref": "data/orders.csv:line 2"}
    When not found (we never invent data):
        {"found": False, "reason": "UNKNOWN_ORDER_ID" | "INVALID_ORDER_ID_FORMAT", ...}
    """
    oid = clean_id(order_id)
    if not _VALID_ORDER_ID.match(oid):
        return {
            "found": False,
            "order_id": oid,
            "reason": "INVALID_ORDER_ID_FORMAT",
            "message": "Order IDs look like 'O1001'. No lookup was done.",
        }

    order = store.get_order(oid)
    if order is None:
        return {
            "found": False,
            "order_id": oid,
            "reason": "UNKNOWN_ORDER_ID",
            "message": f"No order {oid} exists in data/orders.csv.",
        }

    result = {
        "found": True,
        "order_id": oid,
        "order": order_to_dict(order),
        "source_ref": order.source_ref,
    }
    refs = store.order_refs.get(oid, [])
    if len(refs) > 1:
        result["warning"] = f"Order ID appears more than once in the data: {refs}"
    return result


@dataclass
class OrderResolution:
    """The answer to 'which order is this ticket about?'"""

    status: str  # see the list below
    referenced_order_ids: list[str] = field(default_factory=list)
    matched_order_ids: list[str] = field(default_factory=list)
    unknown_order_ids: list[str] = field(default_factory=list)
    mismatched_order_ids: list[str] = field(default_factory=list)
    # Orders the customer owns but did NOT mention (shown only as hints).
    candidate_order_ids: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()


# Possible status values:
#   MATCHED            - every mentioned order exists and belongs to the customer
#   PARTIAL_MATCH      - some mentioned orders exist, some do not
#   UNKNOWN_ORDER      - the mentioned order(s) do not exist
#   OWNERSHIP_MISMATCH - an order exists but belongs to a different customer
#   NO_CUSTOMER_ID     - ticket has no customer ID, ownership cannot be checked
#   NO_ORDER_REFERENCE - customer known but no order ID in the message
def resolve_order_for_ticket(store: SupportDataStore, ticket: Ticket) -> OrderResolution:
    """Work out which order a ticket is about. Never guesses."""
    referenced = extract_order_ids(ticket.message)
    res = OrderResolution(status="NO_ORDER_REFERENCE", referenced_order_ids=referenced)

    # Hints only: orders this customer owns (never auto-selected).
    if ticket.customer_id:
        res.candidate_order_ids = [
            o.order_id for o in store.orders_for_customer(ticket.customer_id)
        ]

    if not referenced:
        if ticket.customer_id is None:
            res.status = "NO_CUSTOMER_ID"
            res.note = "No customer ID and no order ID in the message."
        else:
            res.note = (
                "No order ID in the message. The customer's orders are listed as "
                "candidates only; none was chosen automatically."
            )
        return res

    for oid in referenced:
        order = store.get_order(oid)
        if order is None:
            res.unknown_order_ids.append(oid)
        elif ticket.customer_id is not None and order.customer_id != ticket.customer_id:
            res.mismatched_order_ids.append(oid)
        else:
            res.matched_order_ids.append(oid)
            res.source_refs.append(order.source_ref)

    if ticket.customer_id is None:
        # Orders exist, but we cannot prove they belong to this person.
        res.status = "NO_CUSTOMER_ID"
        res.note = "Order IDs were mentioned but the ticket has no customer ID."
    elif res.mismatched_order_ids:
        res.status = "OWNERSHIP_MISMATCH"
        res.matched_order_ids = []  # do not expose someone else's order
        res.source_refs = []
        res.note = "A mentioned order belongs to a different customer."
    elif res.matched_order_ids and res.unknown_order_ids:
        res.status = "PARTIAL_MATCH"
    elif res.matched_order_ids:
        res.status = "MATCHED"
    else:
        res.status = "UNKNOWN_ORDER"
        res.note = "The mentioned order ID(s) were not found in the records."
    return res
