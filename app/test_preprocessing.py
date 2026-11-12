
from app.langchain_pipeline import ticket_preprocessor

ticket = {
    "ticket_id": " T001 ",
    "customer_id": " U001 ",
    "message": " I was   charged twice   for order O1001 ",
    "created_at": "2026-10-05"
}

result = ticket_preprocessor.invoke(ticket)

print("Original message:", ticket["message"])
print("Cleaned message:", result["message"])
print("Cleaned ticket ID:", result["ticket_id"])
print("Cleaned customer ID:", result["customer_id"])
