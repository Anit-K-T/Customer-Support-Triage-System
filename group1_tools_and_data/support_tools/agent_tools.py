"""
agent_tools.py
==============
WHAT THIS FILE DOES
    Packages the tools for the AI agents (the AutoGen team) and controls
    WHICH agent may use WHICH tool.

    Tool permissions (principle of least privilege):

        BillingAgent    -> lookup_order, check_duplicate_payment
        DeliveryAgent   -> lookup_order, check_delivery_issue
        PolicyAgent     -> read_policy,  check_return_eligibility
        ResolutionAgent -> (no tools; it only combines what the others found)

    There is intentionally NO refund, payment, email or account-changing tool
    anywhere in the project. A test checks this.

    Every tool is wrapped so that it can never crash or hang the agent team:
      * an unexpected error  -> returns {"status": "TOOL_ERROR", ...}
      * taking too long      -> returns {"status": "TIMEOUT", ...}
    A failed tool result has complete=False so the caller can mark the case
    incomplete while still keeping the original ticket ID.

    HOW TEAMMATES USE THIS (AutoGen):
        tools = get_tools_for_agent("BillingAgent", store)
        AssistantAgent("BillingAgent", model_client=..., tools=tools)
    Each tool is a normal Python function with type hints and a docstring, which
    is what AutoGen's tool system reads to describe the tool to the model.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Callable, Optional

from . import config
from .data_loader import SupportDataStore, load_all
from .issue_checks import check_delivery_issue as _check_delivery_issue
from .issue_checks import check_duplicate_payment as _check_duplicate_payment
from .order_lookup import lookup_order as _lookup_order
from .policy_tools import check_return_eligibility as _check_return_eligibility
from .policy_tools import read_policy as _read_policy

# Who may use what. Anything not listed here is denied.
AGENT_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "BillingAgent": ("lookup_order", "check_duplicate_payment"),
    "DeliveryAgent": ("lookup_order", "check_delivery_issue"),
    "PolicyAgent": ("read_policy", "check_return_eligibility"),
    "ResolutionAgent": (),
}

_pool = ThreadPoolExecutor(max_workers=4)


def run_tool_safely(func: Callable, *args, timeout: float = config.TOOL_TIMEOUT_SECONDS,
                    **kwargs) -> dict:
    """Run a tool; turn crashes and slow calls into clear, harmless results."""
    future = _pool.submit(func, *args, **kwargs)
    try:
        result = future.result(timeout=timeout)
    except FutureTimeout:
        future.cancel()
        return {"status": "TIMEOUT", "complete": False,
                "message": f"Tool timed out after {timeout}s; result is incomplete."}
    except Exception as exc:  # noqa: BLE001 - a tool must never crash the team
        return {"status": "TOOL_ERROR", "complete": False,
                "message": f"Tool failed: {type(exc).__name__}: {exc}"}
    return result if isinstance(result, dict) else {"status": "OK", "result": result}


def build_all_tools(store: Optional[SupportDataStore] = None) -> dict[str, Callable]:
    """Create every tool (bound to the loaded data). Keys are the tool names."""
    store = store or load_all()

    def lookup_order(order_id: str) -> dict:
        """Look up one order by ID (e.g. 'O1001'). Returns payment, delivery and
        refund status plus the source file/line. Read-only; never invents data."""
        return run_tool_safely(_lookup_order, store, order_id)

    def read_policy(section: str = "") -> dict:
        """Read company support policy. Use section='' for everything, or
        'rules.billing', 'rules.delivery', 'rules.returns', 'rules.account',
        'return_window_days', 'escalation_keywords', 'response_policy'."""
        return run_tool_safely(_read_policy, store, section)

    def check_duplicate_payment(order_id: str) -> dict:
        """Check an order for signs of a duplicate payment. Cannot prove a double
        charge and never allows promising a refund; transaction verification
        is always required."""
        return run_tool_safely(_check_duplicate_payment, store, order_id)

    def check_delivery_issue(order_id: str, customer_message: str = "") -> dict:
        """Compare the customer's delivery claim (never arrived / delayed / arrived)
        with the delivery record for the order."""
        return run_tool_safely(_check_delivery_issue, store, order_id, customer_message)

    def check_return_eligibility(order_id: str, request_date: str) -> dict:
        """Check if the order is inside the 30-day return window. request_date is
        the ticket date as YYYY-MM-DD. Never approves exceptions."""
        return run_tool_safely(_check_return_eligibility, store, order_id, request_date)

    tools = {f.__name__: f for f in (
        lookup_order, read_policy, check_duplicate_payment,
        check_delivery_issue, check_return_eligibility)}

    # Safety net: refuse to build if someone ever adds a forbidden tool.
    banned = set(tools) & set(config.FORBIDDEN_TOOL_NAMES)
    if banned:
        raise RuntimeError(f"Forbidden tool(s) present: {sorted(banned)}")
    return tools


def get_tools_for_agent(agent_name: str,
                        store: Optional[SupportDataStore] = None) -> list[Callable]:
    """Return ONLY the tools this agent is allowed to use."""
    if agent_name not in AGENT_PERMISSIONS:
        raise PermissionError(f"Unknown agent '{agent_name}': no tools granted.")
    all_tools = build_all_tools(store)
    return [all_tools[name] for name in AGENT_PERMISSIONS[agent_name]]


def call_tool_as_agent(agent_name: str, tool_name: str,
                       store: Optional[SupportDataStore] = None, **kwargs) -> dict:
    """
    Call a tool by name on behalf of an agent, enforcing the permission table.
    Useful for tests and for a non-LLM ("fake model") demo mode.
    """
    allowed = AGENT_PERMISSIONS.get(agent_name, ())
    if tool_name not in allowed:
        return {"status": "DENIED", "complete": False,
                "message": f"{agent_name} is not allowed to use '{tool_name}'."}
    tool = build_all_tools(store)[tool_name]
    return tool(**kwargs)


def permissions_report() -> str:
    """Human-readable permission table (good for the demo and the README)."""
    return json.dumps({k: list(v) for k, v in AGENT_PERMISSIONS.items()}, indent=2)
