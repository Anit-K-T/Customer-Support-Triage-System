
from app.langchain_pipeline import ticket_processing_pipeline

ticket = {
    "ticket_id": "T001",
    "customer_id": "U001",
    "message": "I was charged twice for order O1001. Please refund one payment.",
    "created_at": "2026-10-05"
}

result = ticket_processing_pipeline.invoke(ticket)

print("Category:", result.category.value)
print("Urgency:", result.urgency.value)
print("Summary:", result.summary)
print("Status:", result.status)
