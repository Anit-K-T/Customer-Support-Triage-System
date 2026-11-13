
from app.langchain_pipeline import (
    ticket_preprocessor,
    ticket_analyzer
)

ticket = {
    "ticket_id": "T001",
    "customer_id": "U001",
    "message": "I was charged twice for order O1001. Please refund one payment.",
    "created_at": "2026-10-05"
}

# First clean the ticket
cleaned_ticket = ticket_preprocessor.invoke(ticket)

# Then run all three tasks in parallel
result = ticket_analyzer.invoke(cleaned_ticket)

print("Ticket ID:", cleaned_ticket["ticket_id"])
print("Category:", result["category"])
print("Urgency:", result["urgency"])
print("Summary:", result["summary"])

