"""
data_loader.py
==============
WHAT THIS FILE DOES
    Reads the three supplied data files and turns them into clean Python
    objects that the rest of the project can trust:
      * data/tickets.csv         -> Ticket objects
      * data/orders.csv          -> Order objects
      * data/support_policy.json -> a validated dictionary

    While reading it also:
      * cleans messy text (extra spaces, blank values)
      * REJECTS malformed rows (and remembers why) instead of crashing
      * detects DUPLICATE ticket IDs and duplicate order IDs
      * remembers the exact file + line number of every record, so every
        business fact can later point to its source ("data/orders.csv:line 2")

    Everything is bundled in one object, SupportDataStore, which the other
    files receive as input. If a file is missing or unreadable the loader
    raises a clear DataLoadError (fail safely, never guess).

    Uses only the Python standard library (csv, json, dataclasses).
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from .config import ORDERS_FILE, POLICY_FILE, PROJECT_ROOT, TICKETS_FILE


class DataLoadError(Exception):
    """Raised when a data file is missing, unreadable or has wrong columns."""


# ---------------------------------------------------------------------------
# Record types (frozen = they cannot be changed after loading)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Ticket:
    ticket_id: str
    customer_id: Optional[str]  # None when the customer ID is missing
    message: str  # cleaned text; still UNTRUSTED customer content
    created_at: date
    source_ref: str  # e.g. "data/tickets.csv:line 2"


@dataclass(frozen=True)
class Order:
    order_id: str
    customer_id: str
    total_inr: int
    payment_status: str
    delivery_status: str
    delivered_at: Optional[date]  # None if not delivered yet
    refund_status: str
    source_ref: str  # e.g. "data/orders.csv:line 2"


@dataclass
class SupportDataStore:
    """Everything loaded from disk, plus a record of what went wrong."""

    tickets: dict[str, Ticket] = field(default_factory=dict)
    orders: dict[str, Order] = field(default_factory=dict)
    policy: dict = field(default_factory=dict)

    # ticket_id / order_id -> every "file:line" where it appears
    ticket_refs: dict[str, list[str]] = field(default_factory=dict)
    order_refs: dict[str, list[str]] = field(default_factory=dict)

    # Rows we refused to load: {"T0xx or line N": "reason"}
    rejected_tickets: dict[str, str] = field(default_factory=dict)
    rejected_orders: dict[str, str] = field(default_factory=dict)

    duplicate_ticket_ids: list[str] = field(default_factory=list)
    duplicate_order_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # --- simple lookups -----------------------------------------------------
    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        return self.tickets.get(clean_id(ticket_id))

    def get_order(self, order_id: str) -> Optional[Order]:
        return self.orders.get(clean_id(order_id))

    def orders_for_customer(self, customer_id: str) -> list[Order]:
        cid = clean_id(customer_id)
        return [o for o in self.orders.values() if o.customer_id == cid]


# ---------------------------------------------------------------------------
# Small cleaning helpers
# ---------------------------------------------------------------------------
def clean_text(value: Optional[str]) -> str:
    """Trim the text and squeeze repeated spaces/newlines into one space."""
    return re.sub(r"\s+", " ", value or "").strip()


def clean_id(value: Optional[str]) -> str:
    """IDs are compared in UPPER case with no spaces (' o1001 ' -> 'O1001')."""
    return clean_text(value).upper()


def _parse_date(value: str) -> Optional[date]:
    """Turn '2026-10-05' into a date. Blank -> None. Bad format -> ValueError."""
    value = clean_text(value)
    if not value:
        return None
    return date.fromisoformat(value)


def _ref(path: Path, line: int) -> str:
    """Build a readable source reference such as 'data/orders.csv:line 3'."""
    try:
        shown = path.relative_to(PROJECT_ROOT)
    except ValueError:
        shown = path
    return f"{shown.as_posix()}:line {line}"


def _open_csv(path: Path, required: set[str]) -> tuple[csv.DictReader, object]:
    """Open a CSV and check it has the columns we need."""
    if not path.exists():
        raise DataLoadError(f"Required data file not found: {path}")
    try:
        handle = open(path, newline="", encoding="utf-8-sig")
        reader = csv.DictReader(handle)
        headers = {clean_text(h) for h in (reader.fieldnames or [])}
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise DataLoadError(f"Could not read {path}: {exc}") from exc
    missing = required - headers
    if missing:
        handle.close()
        raise DataLoadError(f"{path.name} is missing column(s): {sorted(missing)}")
    return reader, handle


# ---------------------------------------------------------------------------
# Loaders for each file
# ---------------------------------------------------------------------------
def load_tickets(store: SupportDataStore, path: Path = TICKETS_FILE) -> None:
    reader, handle = _open_csv(
        path, {"ticket_id", "customer_id", "message", "created_at"}
    )
    with handle:
        for row in reader:
            ref = _ref(path, reader.line_num)
            ticket_id = clean_id(row.get("ticket_id"))
            label = ticket_id or f"line {reader.line_num}"
            try:
                if not ticket_id:
                    raise ValueError("ticket_id is empty")
                message = clean_text(row.get("message"))
                if not message:
                    raise ValueError("message is empty")
                created = _parse_date(row.get("created_at", ""))
                if created is None:
                    raise ValueError("created_at is empty")
            except ValueError as exc:
                store.rejected_tickets[label] = f"{ref}: {exc}"
                continue

            store.ticket_refs.setdefault(ticket_id, []).append(ref)
            if ticket_id in store.tickets:
                # Duplicate ID: keep the FIRST one only, so no action is repeated.
                if ticket_id not in store.duplicate_ticket_ids:
                    store.duplicate_ticket_ids.append(ticket_id)
                continue

            customer = clean_id(row.get("customer_id")) or None
            store.tickets[ticket_id] = Ticket(
                ticket_id=ticket_id,
                customer_id=customer,
                message=message,
                created_at=created,
                source_ref=ref,
            )


def load_orders(store: SupportDataStore, path: Path = ORDERS_FILE) -> None:
    reader, handle = _open_csv(
        path,
        {
            "order_id", "customer_id", "total_inr", "payment_status",
            "delivery_status", "delivered_at", "refund_status",
        },
    )
    with handle:
        for row in reader:
            ref = _ref(path, reader.line_num)
            order_id = clean_id(row.get("order_id"))
            label = order_id or f"line {reader.line_num}"
            try:
                if not order_id:
                    raise ValueError("order_id is empty")
                customer = clean_id(row.get("customer_id"))
                if not customer:
                    raise ValueError("customer_id is empty")
                total = int(clean_text(row.get("total_inr")))
                if total < 0:
                    raise ValueError("total_inr is negative")
                payment = clean_id(row.get("payment_status"))
                delivery = clean_id(row.get("delivery_status"))
                refund = clean_id(row.get("refund_status"))
                if not (payment and delivery and refund):
                    raise ValueError("a status column is empty")
                delivered = _parse_date(row.get("delivered_at", ""))
            except ValueError as exc:
                store.rejected_orders[label] = f"{ref}: {exc}"
                continue

            store.order_refs.setdefault(order_id, []).append(ref)
            if order_id in store.orders:
                if order_id not in store.duplicate_order_ids:
                    store.duplicate_order_ids.append(order_id)
                continue

            store.orders[order_id] = Order(
                order_id=order_id,
                customer_id=customer,
                total_inr=total,
                payment_status=payment,
                delivery_status=delivery,
                delivered_at=delivered,
                refund_status=refund,
                source_ref=ref,
            )


def load_policy(store: SupportDataStore, path: Path = POLICY_FILE) -> None:
    if not path.exists():
        raise DataLoadError(f"Required data file not found: {path}")
    try:
        policy = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataLoadError(f"Could not read policy file {path}: {exc}") from exc

    if not isinstance(policy, dict):
        raise DataLoadError("support_policy.json must contain a JSON object")
    for key in ("return_window_days", "escalation_keywords", "rules", "response_policy"):
        if key not in policy:
            raise DataLoadError(f"support_policy.json is missing key '{key}'")
    window = policy["return_window_days"]
    if not isinstance(window, int) or isinstance(window, bool) or window <= 0:
        raise DataLoadError("return_window_days must be a positive whole number")
    if not isinstance(policy["escalation_keywords"], list) or not all(
        isinstance(k, str) for k in policy["escalation_keywords"]
    ):
        raise DataLoadError("escalation_keywords must be a list of text values")
    if not isinstance(policy["rules"], dict):
        raise DataLoadError("rules must be a JSON object")
    store.policy = policy


# ---------------------------------------------------------------------------
# One-call entry point
# ---------------------------------------------------------------------------
def load_all(
    tickets_path: Path = TICKETS_FILE,
    orders_path: Path = ORDERS_FILE,
    policy_path: Path = POLICY_FILE,
) -> SupportDataStore:
    """Load all three files and return a ready-to-use SupportDataStore."""
    store = SupportDataStore()
    load_policy(store, policy_path)
    load_orders(store, orders_path)
    load_tickets(store, tickets_path)

    # Turn problems into readable warnings the demo/logs can show.
    for tid in store.duplicate_ticket_ids:
        store.warnings.append(
            f"Duplicate ticket ID {tid} at {store.ticket_refs[tid]}; only the first is used."
        )
    for oid in store.duplicate_order_ids:
        store.warnings.append(
            f"Duplicate order ID {oid} at {store.order_refs[oid]}; only the first is used."
        )
    for key, why in {**store.rejected_tickets, **store.rejected_orders}.items():
        store.warnings.append(f"Rejected record {key}: {why}")
    return store
