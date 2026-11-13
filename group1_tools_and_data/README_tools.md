# Group 1 – Tools & Data Processing (our part)

Offline, deterministic layer that the LangChain and AutoGen parts plug into.
Standard library only (pytest needed for tests). Python 3.11 / 3.12.

## Run
    python run_tools_demo.py                 # all 12 tickets
    python run_tools_demo.py --ticket T001   # full detail for one ticket
    python run_tools_demo.py --permissions   # who gets which tool
    python -m pytest -v                      # 55 tests

## Files
| File | Purpose |
|---|---|
| support_tools/config.py | settings, extra keywords, injection patterns, timeout |
| support_tools/data_loader.py | read + validate tickets/orders/policy, duplicates, source lines |
| support_tools/order_lookup.py | find/lookup orders, match ticket to order safely |
| support_tools/policy_tools.py | read_policy, 30-day return check |
| support_tools/issue_checks.py | duplicate-payment and delivery-issue checks |
| support_tools/escalation.py | deterministic escalation rules engine |
| support_tools/agent_tools.py | tools for agents + per-agent permissions + safe execution |
| run_tools_demo.py | command-line demo |
| tests/test_tools_and_data.py | pytest tests |

## For teammates
    from support_tools import load_all, evaluate_escalation, get_tools_for_agent
    store = load_all()
    decision = evaluate_escalation(store, store.get_ticket("T001"))   # LangChain branch step
    tools = get_tools_for_agent("BillingAgent", store)                # AutoGen AssistantAgent(tools=...)

`decision` gives: escalate, urgency, needs_info, suggested_status, evidence_order_ids,
policy_references, source_refs and the raw tool outputs (`checks`).
