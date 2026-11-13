
from enum import Enum
from pydantic import BaseModel, Field


# Allowed ticket categories
class Category(str, Enum):
    BILLING = "BILLING"
    DELIVERY = "DELIVERY"
    RETURN = "RETURN"
    ACCOUNT = "ACCOUNT"
    OTHER = "OTHER"


# Allowed urgency levels
class Urgency(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# Allowed processing statuses
class TicketStatus(str, Enum):
    RESOLVED_DRAFT = "RESOLVED_DRAFT"
    NEEDS_INFO = "NEEDS_INFO"
    MANUAL_REVIEW = "MANUAL_REVIEW"

class ClassificationResult(BaseModel):
    category: Category
    urgency: Urgency
    summary: str
    status: TicketStatus | None = None
# Incoming ticket structure
class TicketInput(BaseModel):
    ticket_id: str
    customer_id: str | None = None
    message: str
    created_at: str


# Final ticket analysis structure
class TicketAnalysis(BaseModel):
    ticket_id: str
    category: Category
    urgency: Urgency
    summary: str
    evidence_order_ids: list[str] = Field(default_factory=list)
    escalation: bool
    status: TicketStatus
    suggested_reply: str
    policy_references: list[str] = Field(default_factory=list)
