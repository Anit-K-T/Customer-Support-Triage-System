from app.langchain_pipeline import routed_ticket_pipeline

sample_ticket = {
    "ticket_id": "T001",
    "customer_id": "U001",
    "message": "I was charged twice for order O1001.",
    "created_at": "2026-10-05"
}

result = routed_ticket_pipeline.invoke(sample_ticket)

print("Category:", result["category"])
print("Assigned Department:", result["department"])
print("Summary:", result["summary"])