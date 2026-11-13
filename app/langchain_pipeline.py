
from langchain_core.runnables import RunnableLambda,RunnableParallel,RunnableBranch
from pydantic import ValidationError
from app.schemas import ClassificationResult, TicketStatus,Category

# Step 1: Clean and normalize incoming ticket data
def normalize_ticket(ticket: dict) -> dict:
    """
    Clean ticket text and prepare it for processing.
    """

    cleaned_ticket = ticket.copy()

    # Remove extra spaces from the message
    cleaned_ticket["message"] = " ".join(
        cleaned_ticket["message"].split()
    )

    # Remove spaces around ticket ID
    cleaned_ticket["ticket_id"] = (
        cleaned_ticket["ticket_id"].strip()
    )

    # Clean customer ID if available
    if cleaned_ticket.get("customer_id"):
        cleaned_ticket["customer_id"] = (
            cleaned_ticket["customer_id"].strip()
        )

    return cleaned_ticket


# Step 2: Convert the Python function into a LangChain Runnable
ticket_preprocessor = RunnableLambda(normalize_ticket)

# Step 1: Identify the ticket category
def classify_category(ticket: dict) -> str:

    message = ticket["message"].lower()

    if any(word in message for word in [
        "password", "account", "accessed", "login",
        "hacked", "unauthorized"
    ]):
        return "ACCOUNT"

    elif any(word in message for word in [
        "return", "refund for return", "damaged"
    ]):
        return "RETURN"

    elif any(word in message for word in [
        "charged", "payment", "billing", "receipt",
        "refund", "amount"
    ]):
        return "BILLING"

    elif any(word in message for word in [
        "delivery", "delayed", "delivered", "package",
        "parcel", "arrived", "shipped", "order"
    ]):
        return "DELIVERY"

    return "OTHER"


# Step 2: Determine ticket urgency
def detect_urgency(ticket: dict) -> str:

    message = ticket["message"].lower()

    high_keywords = [
        "charged twice", "duplicate payment",
        "fraud", "unauthorized", "someone accessed",
        "urgent"
    ]

    medium_keywords = [
        "delayed", "damaged", "not received",
        "not arrived", "return"
    ]

    if any(word in message for word in high_keywords):
        return "HIGH"

    elif any(word in message for word in medium_keywords):
        return "MEDIUM"

    return "LOW"


# Step 3: Generate a short mock summary
def summarize_ticket(ticket: dict) -> str:

    message = ticket["message"]

    if len(message) > 100:
        message = message[:97] + "..."

    return f"Customer issue: {message}"


# Step 4: Create independent LangChain tasks
ticket_analyzer = RunnableParallel(
    category=RunnableLambda(classify_category),
    urgency=RunnableLambda(detect_urgency),
    summary=RunnableLambda(summarize_ticket)
)
# Step 5: Validate classification output using Pydantic
def validate_classification(result: dict):

    try:
        return ClassificationResult.model_validate(result)

    except ValidationError:
        return ClassificationResult(
            category="OTHER",
            urgency="MEDIUM",
            summary="Classification failed. Manual review required.",
            status=TicketStatus.MANUAL_REVIEW
        )


# Step 6: Connect all steps into one pipeline
ticket_processing_pipeline = (
    ticket_preprocessor
    | ticket_analyzer
    | RunnableLambda(validate_classification)
)
# Step 7: Define department routing functions

def billing_branch(result):
    return {
        "category": result.category.value,
        "department": "Billing Team",
        "summary": result.summary
    }


def delivery_branch(result):
    return {
        "category": result.category.value,
        "department": "Delivery Team",
        "summary": result.summary
    }


def return_branch(result):
    return {
        "category": result.category.value,
        "department": "Returns Team",
        "summary": result.summary
    }


def general_branch(result):
    return {
        "category": result.category.value,
        "department": "General Support Team",
        "summary": result.summary
    }
# Step 8: Create conditional routing

category_router = RunnableBranch(
    (
        lambda result: result.category == Category.BILLING,
        RunnableLambda(billing_branch)
    ),
    (
        lambda result: result.category == Category.DELIVERY,
        RunnableLambda(delivery_branch)
    ),
    (
        lambda result: result.category == Category.RETURN,
        RunnableLambda(return_branch)
    ),
    RunnableLambda(general_branch)
)
# Step 9: Connect classification and routing pipelines

routed_ticket_pipeline = (
    ticket_processing_pipeline
    | category_router
)