"""
support_tools package
=====================
WHAT THIS FILE DOES
    Makes the folder importable as a Python package and lists the main
    functions teammates will use, so they can write for example:

        from support_tools import load_all, evaluate_escalation, get_tools_for_agent
"""

from .agent_tools import (AGENT_PERMISSIONS, build_all_tools, call_tool_as_agent,
                          get_tools_for_agent, run_tool_safely)
from .data_loader import DataLoadError, SupportDataStore, load_all
from .escalation import EscalationDecision, evaluate_all, evaluate_escalation
from .issue_checks import check_delivery_issue, check_duplicate_payment
from .order_lookup import extract_order_ids, lookup_order, resolve_order_for_ticket
from .policy_tools import check_return_eligibility, read_policy

__all__ = [
    "AGENT_PERMISSIONS", "build_all_tools", "call_tool_as_agent",
    "get_tools_for_agent", "run_tool_safely", "DataLoadError", "SupportDataStore",
    "load_all", "EscalationDecision", "evaluate_all", "evaluate_escalation",
    "check_delivery_issue", "check_duplicate_payment", "extract_order_ids",
    "lookup_order", "resolve_order_for_ticket", "check_return_eligibility",
    "read_policy",
]
