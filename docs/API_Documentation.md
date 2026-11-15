# API and CLI Documentation

## 1. Overview

The Customer Support Triage & Escalation System provides a command-line interface for processing customer support tickets.

The application supports individual ticket processing and batch processing.

## 2. Requirements

- Python 3.12
- Required project dependencies
- OpenAI API key configured in the `.env` file

## 3. Application Commands

### Process a single ticket

```bash
python -m app.main --ticket T001
```

This command processes the specified ticket ID.

### Process all tickets

```bash
python -m app.main --all
```

This command processes all available tickets in the dataset.

## 4. Input Data

The application uses locally stored customer support ticket data.

Each ticket contains information such as:
- Ticket ID
- Customer ID
- Customer message
- Creation timestamp

Order and support policy information are retrieved using the local support tools.

## 5. Processing Workflow

1. Load the customer support ticket.
2. Normalize the ticket message.
3. Classify category, urgency and summary.
4. Validate classification results.
5. Route the ticket according to its category.
6. Evaluate deterministic escalation rules.
7. Retrieve relevant order and policy evidence.
8. Investigate the issue using AutoGen agents.
9. Generate a structured resolution recommendation.

## 6. Output Schema

The application generates structured JSON containing:

| Field | Description |
|---|---|
| ticket_id | Unique ticket identifier |
| category | Customer issue category |
| urgency | Ticket urgency |
| summary | Short issue summary |
| evidence_order_ids | Related order identifiers |
| escalation | Escalation recommendation |
| status | Final processing status |
| suggested_reply | Draft response |
| policy_references | Relevant policy references |

### Supported Categories

- BILLING
- DELIVERY
- RETURN
- ACCOUNT
- OTHER

### Supported Urgency Levels

- LOW
- MEDIUM
- HIGH

### Supported Status Values

- RESOLVED_DRAFT
- NEEDS_INFO
- MANUAL_REVIEW

## 7. Error Handling and Safety

The system supports fallback handling when processing fails or reliable results cannot be produced.

Sensitive or unresolved cases can be directed for manual review.

The application generates draft recommendations and does not automatically send emails, issue refunds or modify customer accounts.

## 8. Important Note

This project currently exposes a command-line interface. REST API endpoints are not part of the documented application interface.