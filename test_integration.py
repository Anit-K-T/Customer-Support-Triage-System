
from support_tools import load_all, evaluate_escalation

# Load ticket, order and policy data
store = load_all()

# Get ticket T001
ticket = store.get_ticket("T001")

# Evaluate escalation
decision = evaluate_escalation(store, ticket)

# Display result
print("Ticket ID:", ticket["ticket_id"])
print("Escalation:", decision["escalate"])
print("Urgency:", decision["urgency"])
print("Status:", decision["suggested_status"])
print("Evidence:", decision["evidence_order_ids"])
print("Policy references:", decision["policy_references"])
