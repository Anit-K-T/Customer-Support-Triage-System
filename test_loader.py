from app.data_loader import load_tickets
from app.langchain_pipeline import ticket_processing_pipeline

tickets = load_tickets()

for ticket in tickets:
    result = ticket_processing_pipeline.invoke(ticket)

    print("\nTicket ID:", ticket["ticket_id"])
    print("Category:", result.category.value)
    print("Urgency:", result.urgency.value)
    print("Summary:", result.summary)