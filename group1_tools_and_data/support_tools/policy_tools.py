"""
policy_tools.py
===============
WHAT THIS FILE DOES
    Retrieves the company policies from data/support_policy.json.

      * read_policy()              - returns the whole policy or one section
                                     (e.g. "rules.billing"), with a reference
                                     the final report can cite as evidence.
      * check_return_eligibility() - applies the "30 days after confirmed
                                     delivery" return rule to a specific order.

    The return check never approves an exception. If the window has passed it
    says "needs manual approval" and leaves the decision to a human.
"""

from __future__ import annotations

from datetime import date
from typing import Optional, Union

from .data_loader import SupportDataStore, clean_id, clean_text

POLICY_FILE_NAME = "data/support_policy.json"


def policy_reference(section: str) -> str:
    """Build a citation like 'data/support_policy.json#rules.billing'."""
    return f"{POLICY_FILE_NAME}#{section}"


def list_policy_sections(store: SupportDataStore) -> list[str]:
    """Every section name that read_policy() understands."""
    sections = [k for k in store.policy if k != "rules"]
    sections += ["rules"] + [f"rules.{name}" for name in store.policy.get("rules", {})]
    return sections


def read_policy(store: SupportDataStore, section: str = "") -> dict:
    """
    Read company policy.

    section = ""             -> the whole policy
    section = "rules"        -> all four rules
    section = "rules.billing"-> one rule (billing / delivery / returns / account)
    section = "return_window_days", "escalation_keywords", "response_policy"
    """
    section = clean_text(section)
    if not store.policy:
        return {"found": False, "reason": "POLICY_NOT_LOADED"}

    if not section:
        return {
            "found": True,
            "section": "all",
            "content": store.policy,
            "policy_reference": POLICY_FILE_NAME,
        }

    node = store.policy
    for part in section.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return {
                "found": False,
                "section": section,
                "reason": "UNKNOWN_POLICY_SECTION",
                "available_sections": list_policy_sections(store),
            }
    return {
        "found": True,
        "section": section,
        "content": node,
        "policy_reference": policy_reference(section),
    }


def _to_date(value: Union[date, str, None]) -> Optional[date]:
    if isinstance(value, date):
        return value
    text = clean_text(value)
    return date.fromisoformat(text) if text else None


def check_return_eligibility(
    store: SupportDataStore,
    order_id: str,
    request_date: Union[date, str, None] = None,
) -> dict:
    """
    Is the order still inside the return window on `request_date`?

    The window is counted from the CONFIRMED delivery date. Verdicts:
      ELIGIBLE_WITHIN_WINDOW        - request is within the allowed days
      EXPIRED_NEEDS_MANUAL_APPROVAL - too late; only a human may allow it
      NOT_DELIVERED_YET             - no delivery date, so nothing to return yet
      ORDER_NOT_FOUND / INVALID_DATE / DATA_INCONSISTENT - could not check safely
    """
    oid = clean_id(order_id)
    order = store.get_order(oid)
    if order is None:
        return {"verdict": "ORDER_NOT_FOUND", "order_id": oid}

    try:
        asked_on = _to_date(request_date)
    except ValueError:
        return {"verdict": "INVALID_DATE", "order_id": oid,
                "message": "request_date must look like 2026-10-31."}
    if asked_on is None:
        return {"verdict": "INVALID_DATE", "order_id": oid,
                "message": "A request date is required (use the ticket's created_at)."}

    window = store.policy["return_window_days"]
    base = {
        "order_id": oid,
        "window_days": window,
        "request_date": asked_on.isoformat(),
        "source_refs": [order.source_ref, policy_reference("return_window_days"),
                        policy_reference("rules.returns")],
        "policy_reference": policy_reference("rules.returns"),
    }

    if order.delivery_status != "DELIVERED" or order.delivered_at is None:
        return {**base, "verdict": "NOT_DELIVERED_YET",
                "delivery_status": order.delivery_status,
                "message": "No confirmed delivery date, so the return window has not started."}

    days = (asked_on - order.delivered_at).days
    if days < 0:
        return {**base, "verdict": "DATA_INCONSISTENT",
                "message": "Request date is before the delivery date; needs a human check."}

    base.update(delivered_at=order.delivered_at.isoformat(), days_since_delivery=days)
    if days <= window:
        return {**base, "verdict": "ELIGIBLE_WITHIN_WINDOW",
                "message": f"{days} day(s) after delivery; window is {window} days."}
    return {**base, "verdict": "EXPIRED_NEEDS_MANUAL_APPROVAL",
            "message": (f"{days} day(s) after delivery; window is {window} days. "
                        "Exceptions require manual approval.")}
