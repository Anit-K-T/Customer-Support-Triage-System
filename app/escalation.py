
HIGH_PRIORITY_KEYWORDS = [
    "charged twice",
    "duplicate payment",
    "fraud",
    "unauthorized",
    "someone accessed"
]


def evaluate_escalation(ticket: dict) -> dict:

    message = ticket.get("message", "").lower()
    customer_id = ticket.get("customer_id")

    # Rule 1: High-priority issues
    if any(word in message for word in HIGH_PRIORITY_KEYWORDS):
        return {
            "escalation": True,
            "urgency": "HIGH",
            "status": "MANUAL_REVIEW",
            "reason": "High-priority issue detected"
        }

    # Rule 2: Missing customer ID
    if not customer_id or not customer_id.strip():
        return {
            "escalation": False,
            "urgency": "MEDIUM",
            "status": "NEEDS_INFO",
            "reason": "Customer ID is missing"
        }

    # Rule 3: Vague message
    if len(message.split()) < 4:
        return {
            "escalation": False,
            "urgency": "LOW",
            "status": "NEEDS_INFO",
            "reason": "Insufficient information in ticket"
        }

    # Rule 4: Medium-priority issues
    medium_keywords = [
        "delayed",
        "damaged",
        "not received",
        "not arrived",
        "did not receive",
        "return"
    ]

    if any(word in message for word in medium_keywords):
        return {
            "escalation": False,
            "urgency": "MEDIUM",
            "status": "RESOLVED_DRAFT",
            "reason": "Medium-priority issue detected"
        }

    # Rule 5: Normal issues
    return {
        "escalation": False,
        "urgency": "LOW",
        "status": "RESOLVED_DRAFT",
        "reason": "No deterministic escalation condition"
    }
