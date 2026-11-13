from app.escalation import evaluate_escalation

test_tickets = [
    {
        "ticket_id": "T001",
        "customer_id": "U001",
        "message": "I was charged twice for order O1001."
    },
    {
        "ticket_id": "T005",
        "customer_id": "U005",
        "message": "Someone accessed my account without permission."
    },
    {
        "ticket_id": "T006",
        "customer_id": "",
        "message": "Please help me with this issue."
    },
    {
        "ticket_id": "T003",
        "customer_id": "U003",
        "message": "My order is delayed by three days."
    }
]

for ticket in test_tickets:
    result = evaluate_escalation(ticket)

    print("\nTicket:", ticket["ticket_id"])
    print("Result:", result)