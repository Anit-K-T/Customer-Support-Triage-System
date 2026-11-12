"""
escalation.py
=============
WHAT THIS FILE DOES
    The escalation rules engine. For one ticket it decides, using fixed
    deterministic rules (NO AI involved, so the result is always the same):

        * should this be escalated to a human?      -> escalate  (True/False)
        * how urgent is it?                         -> urgency   (LOW/MEDIUM/HIGH)
        * do we need more info from the customer?   -> needs_info
        * what status do we recommend?              -> suggested_status
        * which policy lines justify the decision?  -> policy_references

    The assignment says deterministic rules must win over the AI for explicit
    escalation keywords and for missing customer IDs. That is exactly what this
    file guarantees: the LangChain routing step can call evaluate_escalation()
    FIRST and trust its answer.

    Rules (each decision lists the rule IDs that fired):
      R01_MISSING_CUSTOMER_ID   no customer ID           -> needs more info
      R02_ESCALATION_KEYWORD    fraud / charged twice... -> HIGH, escalate
      R03_PROMPT_INJECTION      "ignore your policies"   -> escalate, manual review
      R04_OWNERSHIP_MISMATCH    order belongs to someone else -> escalate
      R05_UNKNOWN_ORDER         order ID not in records  -> needs more info
      R06_NO_ORDER_REFERENCE    order-related but no order ID -> needs more info
      R07_DELIVERED_NOT_RECEIVED delivered but not received -> escalate (investigation)
      R08_RETURN_WINDOW_EXPIRED  past 30 days            -> escalate (manual approval)
      R09_DELIVERY_STATUS_CONFLICT customer got it, record disagrees -> note only
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from . import config
from .data_loader import SupportDataStore, Ticket, clean_text
from .issue_checks import check_delivery_issue, check_duplicate_payment, classify_delivery_claim
from .order_lookup import OrderResolution, resolve_order_for_ticket
from .policy_tools import check_return_eligibility, policy_reference

_RETURN_WORDS = re.compile(r"\b(return|returning|returned|exchange)\b", re.IGNORECASE)
_BILLING_WORDS = re.compile(
    r"\b(charge[ds]?|refund\w*|payment|paid|receipt|invoice|amount|billing|billed)\b",
    re.IGNORECASE,
)
_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


# ---------------------------------------------------------------------------
# Small detectors
# ---------------------------------------------------------------------------
def find_escalation_keywords(store: SupportDataStore, message: str) -> list[str]:
    """Return the escalation keywords found in the message (official + extra)."""
    text = clean_text(message).lower()
    official = [k.lower() for k in store.policy.get("escalation_keywords", [])]
    extras = [k for k in config.EXTRA_ESCALATION_KEYWORDS if k not in official]
    return [k for k in official + extras if k in text]


def detect_prompt_injection(message: str) -> bool:
    """True if the message tries to give orders to the AI/support system."""
    return any(re.search(p, message or "", re.IGNORECASE)
               for p in config.PROMPT_INJECTION_PATTERNS)


def category_hint_from_keywords(keywords: list[str]) -> Optional[str]:
    """Category suggested by the first keyword that has a clear category."""
    for kw in keywords:
        hint = config.KEYWORD_CATEGORY_HINT.get(kw)
        if hint:
            return hint
    return None


# ---------------------------------------------------------------------------
# The decision object
# ---------------------------------------------------------------------------
@dataclass
class EscalationDecision:
    ticket_id: str
    escalate: bool = False
    urgency: str = "LOW"
    needs_info: bool = False
    suggested_status: str = "RESOLVED_DRAFT"
    category_hint: Optional[str] = None
    matched_keywords: list[str] = field(default_factory=list)
    prompt_injection_suspected: bool = False
    rule_ids: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    policy_references: list[str] = field(default_factory=list)
    evidence_order_ids: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    order_resolution: dict = field(default_factory=dict)
    checks: dict = field(default_factory=dict)  # raw tool outputs, for agents

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def _fire(d: EscalationDecision, rule_id: str, reason: str,
          *, urgency: str = "LOW", escalate: bool = False,
          needs_info: bool = False, policy: Optional[str] = None) -> None:
    """Record that a rule fired and merge its effect into the decision."""
    if rule_id not in d.rule_ids:
        d.rule_ids.append(rule_id)
    d.reasons.append(reason)
    d.escalate = d.escalate or escalate
    d.needs_info = d.needs_info or needs_info
    if _RANK[urgency] > _RANK[d.urgency]:
        d.urgency = urgency
    if policy:
        _cite(d, policy)


def _cite(d: EscalationDecision, section: str) -> None:
    """Add a policy citation once (no duplicates)."""
    ref = policy_reference(section)
    if ref not in d.policy_references:
        d.policy_references.append(ref)


# ---------------------------------------------------------------------------
# The rules engine
# ---------------------------------------------------------------------------
def evaluate_escalation(store: SupportDataStore, ticket: Ticket) -> EscalationDecision:
    """Apply every rule to one ticket and return an EscalationDecision."""
    d = EscalationDecision(ticket_id=ticket.ticket_id)
    message = ticket.message

    resolution: OrderResolution = resolve_order_for_ticket(store, ticket)
    d.order_resolution = resolution.to_dict()
    d.evidence_order_ids = list(resolution.matched_order_ids)
    d.source_refs = [ticket.source_ref] + list(resolution.source_refs)

    claim = classify_delivery_claim(message)
    is_return = bool(_RETURN_WORDS.search(message))
    is_billing = bool(_BILLING_WORDS.search(message))
    is_delivery = claim != "UNKNOWN"
    order_related = is_return or is_billing or is_delivery

    # R01 - missing customer ID (deterministic, always wins)
    if ticket.customer_id is None:
        _fire(d, "R01_MISSING_CUSTOMER_ID",
              "Ticket has no customer ID, so records cannot be matched safely.",
              needs_info=True)

    # R02 - explicit escalation keywords from the policy file
    d.matched_keywords = find_escalation_keywords(store, message)
    d.category_hint = category_hint_from_keywords(d.matched_keywords)
    if d.matched_keywords:
        _fire(d, "R02_ESCALATION_KEYWORD",
              f"Escalation keyword(s) found: {d.matched_keywords}.",
              urgency="HIGH", escalate=True, policy="escalation_keywords")
        if d.category_hint == "ACCOUNT":
            _fire(d, "R02_ESCALATION_KEYWORD",
                  "Suspected account takeover is HIGH urgency and must be escalated.",
                  urgency="HIGH", escalate=True, policy="rules.account")
        if d.category_hint == "BILLING":
            _fire(d, "R02_ESCALATION_KEYWORD",
                  "Billing claim: no refund or reversal without transaction verification.",
                  urgency="HIGH", escalate=True, policy="rules.billing")

    # R03 - prompt injection: customer text is untrusted
    if detect_prompt_injection(message):
        d.prompt_injection_suspected = True
        _fire(d, "R03_PROMPT_INJECTION",
              "Message tries to override policy; treated as untrusted customer text.",
              urgency="MEDIUM", escalate=config.ESCALATE_ON_PROMPT_INJECTION,
              policy="response_policy")

    # R04 / R05 / R06 - order problems
    status = resolution.status
    if status == "OWNERSHIP_MISMATCH":
        _fire(d, "R04_OWNERSHIP_MISMATCH",
              f"Order(s) {resolution.mismatched_order_ids} belong to another customer.",
              urgency="MEDIUM", escalate=True)
    elif status == "UNKNOWN_ORDER":
        _fire(d, "R05_UNKNOWN_ORDER",
              f"Order(s) {resolution.unknown_order_ids} not found; nothing was invented.",
              urgency="MEDIUM" if is_delivery else "LOW", needs_info=True)
    elif status == "NO_ORDER_REFERENCE" and order_related:
        _fire(d, "R06_NO_ORDER_REFERENCE",
              "Order-related request without an order ID; ask which order.",
              needs_info=True)

    # Checks that need a verified, matched order
    for oid in resolution.matched_order_ids:
        if is_billing:
            d.checks["duplicate_payment"] = check_duplicate_payment(store, oid)
            if _RANK[d.urgency] < _RANK["MEDIUM"]:
                d.urgency = "MEDIUM"  # money questions are at least MEDIUM
            _cite(d, "rules.billing")

        if is_delivery:
            delivery = check_delivery_issue(store, oid, message)
            d.checks["delivery_issue"] = delivery
            if delivery["verdict"] == "DELIVERED_NOT_RECEIVED":
                _fire(d, "R07_DELIVERED_NOT_RECEIVED",
                      "Marked delivered but customer did not receive it; "
                      "delivery investigation required.",
                      urgency="MEDIUM", escalate=True, policy="rules.delivery")
            elif delivery["verdict"] in ("IN_PROGRESS_DELAY", "NOT_YET_DELIVERED"):
                _fire(d, "R07_DELIVERY_DELAY",
                      "Order not delivered yet; offer to investigate.",
                      urgency="MEDIUM", policy="rules.delivery")
            elif delivery["verdict"] == "STATUS_CONFLICT":
                _fire(d, "R09_DELIVERY_STATUS_CONFLICT",
                      "Customer says it arrived but the record shows it is not "
                      "delivered; record may be out of date (no change made).",
                      policy="rules.delivery")

        if is_return:
            ret = check_return_eligibility(store, oid, ticket.created_at)
            d.checks["return_eligibility"] = ret
            _cite(d, "rules.returns")
            if ret["verdict"] == "EXPIRED_NEEDS_MANUAL_APPROVAL":
                _fire(d, "R08_RETURN_WINDOW_EXPIRED", ret["message"],
                      urgency="MEDIUM", escalate=True, policy="rules.returns")

    # Always cite the "draft only" policy: no refunds/emails/modifications.
    _cite(d, "response_policy")

    # Recommended status (the final decision belongs to the synthesizer).
    if d.prompt_injection_suspected or status == "OWNERSHIP_MISMATCH":
        d.suggested_status = "MANUAL_REVIEW"
    elif d.needs_info:
        d.suggested_status = "NEEDS_INFO"
    else:
        d.suggested_status = "RESOLVED_DRAFT"
    return d


def evaluate_all(store: SupportDataStore) -> list[EscalationDecision]:
    """Run the rules on every (non-duplicate, valid) ticket in the file."""
    return [evaluate_escalation(store, t) for t in store.tickets.values()]
