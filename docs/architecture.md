
# System Architecture

```mermaid
flowchart TD
    A[Customer Support Tickets] --> B[Data Loader]
    B --> C[LangChain Preprocessing]
    C --> D[RunnableParallel Classification]
    D --> E[Category]
    D --> F[Urgency]
    D --> G[Summary]
    E --> H[Pydantic Validation]
    F --> H
    G --> H
    H --> I[Category Routing]
    I --> J[Deterministic Escalation]
    J --> K[Order Lookup and Policy Tools]
    K --> L[AutoGen Multi-Agent Team]
    L --> M[BillingAgent]
    L --> N[DeliveryAgent]
    L --> O[PolicyAgent]
    M --> P[ResolutionAgent]
    N --> P
    O --> P
    P --> Q[Final Structured JSON]
    Q --> R[RESOLVED_DRAFT]
    Q --> S[NEEDS_INFO]
    Q --> T[MANUAL_REVIEW]
```

## Architecture Description

The system accepts customer support tickets from local datasets and processes them through LangChain classification, Pydantic validation, category routing and deterministic escalation rules.

Local support tools provide order and policy information. AutoGen agents investigate the issues and prepare resolution recommendations. The application combines these results into a structured JSON response with an appropriate status.
```
