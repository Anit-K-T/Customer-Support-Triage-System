"""
run_tools_demo.py
=================
WHAT THIS FILE DOES
    A command-line demo that proves the tools & data layer works on the real
    supplied files. It needs no AI model and no internet.

    Usage:
        python run_tools_demo.py               # table of all tickets
        python run_tools_demo.py --ticket T001 # full JSON detail for one ticket
        python run_tools_demo.py --json        # all tickets as JSON
        python run_tools_demo.py --permissions # which agent gets which tool

    For each ticket it shows what the escalation rules decided, which order was
    matched, and the source file/line behind each fact. Unknown ticket IDs are
    rejected clearly instead of crashing.
"""

from __future__ import annotations

import argparse
import json
import sys

from support_tools import DataLoadError, evaluate_escalation, load_all
from support_tools.agent_tools import permissions_report
from support_tools.data_loader import clean_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Tools & data processing demo")
    parser.add_argument("--ticket", help="process one ticket ID, e.g. T001")
    parser.add_argument("--json", action="store_true", help="print JSON for all tickets")
    parser.add_argument("--permissions", action="store_true",
                        help="show the agent tool-permission table")
    args = parser.parse_args()

    if args.permissions:
        print(permissions_report())
        return 0

    try:
        store = load_all()
    except DataLoadError as exc:
        print(f"ERROR: cannot load data: {exc}", file=sys.stderr)
        return 2

    for warning in store.warnings:
        print(f"WARNING: {warning}", file=sys.stderr)

    if args.ticket:
        tid = clean_id(args.ticket)
        ticket = store.get_ticket(tid)
        if ticket is None:
            reason = store.rejected_tickets.get(tid, "no such ticket ID in data/tickets.csv")
            print(f"ERROR: ticket {tid} cannot be processed: {reason}", file=sys.stderr)
            return 1
        decision = evaluate_escalation(store, ticket)
        print(json.dumps({"ticket": ticket.message, "customer_id": ticket.customer_id,
                          **decision.to_dict()}, indent=2, default=str))
        return 0

    decisions = [evaluate_escalation(store, t) for t in store.tickets.values()]
    if args.json:
        print(json.dumps([d.to_dict() for d in decisions], indent=2, default=str))
        return 0

    print(f"{'TICKET':<6} {'URGENCY':<7} {'ESCALATE':<8} {'STATUS':<15} "
          f"{'ORDERS':<8} RULES")
    print("-" * 90)
    for d in decisions:
        print(f"{d.ticket_id:<6} {d.urgency:<7} {str(d.escalate):<8} "
              f"{d.suggested_status:<15} {','.join(d.evidence_order_ids) or '-':<8} "
              f"{','.join(dict.fromkeys(d.rule_ids)) or '-'}")
    print(f"\n{len(decisions)} tickets processed; {len(store.warnings)} data warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
