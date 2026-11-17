# Customer Support Triage & Escalation System

## 1. Project Overview

The Customer Support Triage & Escalation System is an AI-powered application designed to automate the analysis and handling of customer support tickets.

The system combines LangChain, AutoGen, Pydantic validation, local support tools and deterministic escalation rules to classify customer issues, identify urgency, retrieve relevant order and policy information, and generate structured resolution recommendations.

It supports processing individual customer tickets as well as multiple tickets through a command-line interface.

## 2. Problem Statement

Customer support teams handle large volumes of customer queries related to billing, payments, delivery, returns and account issues. Manually classifying tickets, checking order information, identifying relevant policies and deciding when to escalate can be time-consuming.

This project aims to simplify the support workflow through automated ticket classification, evidence retrieval, rule-based escalation and multi-agent investigation.

## 3. Project Objectives

- Automate customer support ticket classification.
- Identify the urgency of customer issues.
- Generate concise ticket summaries.
- Retrieve relevant order and policy information.
- Apply deterministic escalation rules.
- Use specialized AI agents for ticket investigation.
- Generate structured resolution recommendations.
- Provide manual review for uncertain or sensitive cases.

## 4. Key Features

- **Ticket Preprocessing:** Normalizes incoming ticket messages.
- **Parallel Classification:** Uses LangChain RunnableParallel to classify category, urgency and summary.
- **Data Validation:** Uses Pydantic schemas to validate structured outputs.
- **Category Routing:** Routes tickets based on their issue category.
- **Order Lookup:** Retrieves order details from local datasets.
- **Policy Retrieval:** Provides relevant customer support policy information.
- **Deterministic Escalation:** Applies predefined business rules to identify cases requiring escalation.
- **Multi-Agent Investigation:** Uses specialized AutoGen agents.
- **Fallback Handling:** Supports manual review when reliable automated processing is not possible.
- **Batch Processing:** Processes all available tickets through the CLI.

## 5. Technologies Used

| Technology | Purpose |
|---|---|
| Python | Core development |
| LangChain Core | Workflow orchestration and classification |
| AutoGen | Multi-agent collaboration |
| Pydantic | Data validation |
| Pandas | Data processing |
| CSV and JSON | Local data storage |
| Pytest | Testing |
| OpenAI API | Language model integration |

## 6. System Modules

### LangChain Processing Module

Responsible for:
- Ticket preprocessing and normalization.
- Parallel classification of category, urgency and summary.
- Pydantic validation.
- Category-based routing.

### Deterministic Escalation Module

Evaluates predefined support conditions and determines whether a ticket requires escalation, additional information or manual review.

### Support Tools Module

Provides:
- Order lookup.
- Policy retrieval.
- Issue checks.
- Evidence identification.
- Agent-specific tool access.

### AutoGen Multi-Agent Module

The system uses four specialized agents:

| Agent | Responsibility |
|---|---|
| BillingAgent | Investigates billing and payment issues |
| DeliveryAgent | Investigates delivery-related issues |
| PolicyAgent | Retrieves and interprets relevant policies |
| ResolutionAgent | Prepares the final resolution recommendation |

The agents collaborate using a RoundRobinGroupChat workflow with a termination condition and maximum-turn limit.

## 7. Project Structure

```text
Customer-Support-Triage-System/
│
├── app/
│   ├── main.py
│   ├── agents.py
│   ├── team.py
│   ├── schemas.py
│   ├── langchain_pipeline.py
│   ├── data_loader.py
│   └── escalation.py
│
├── group1_tools_and_data/
│   ├── data/
│   ├── support_tools/
│   │   ├── agent_tools.py
│   │   ├── config.py
│   │   ├── data_loader.py
│   │   ├── escalation.py
│   │   ├── issue_checks.py
│   │   ├── order_lookup.py
│   │   └── policy_tools.py
│   └── tests/
│
├── data/
├── requirements.txt
├── .env.example
├── README.md
├── test_escalation.py
├── test_integration.py
├── test_loader.py
├── test_parallel.py
├── test_routing.py
└── test_validation.py
```

## 8. Installation and Setup

### Prerequisites

- Python 3.12
- pip
- OpenAI API key

### Step 1: Clone the repository

```bash
git clone https://github.com/Anit-K-T/Customer-Support-Triage-System.git
cd Customer-Support-Triage-System
```

### Step 2: Create a virtual environment

```bash
python -m venv customer
```

Activate it on Windows:

```powershell
.\customer\Scripts\Activate.ps1
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure environment variables

Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
```

Replace the placeholder with your own API key. Never upload your actual `.env` file to GitHub.

## 9. Running the Application

### Process a single ticket

```bash
python -m app.main --ticket T001
```

Replace `T001` with the required ticket ID.

### Process all tickets

```bash
python -m app.main --all
```
### Run the Streamlit UI

```powershell
streamlit run streamlit_app.py

The application processes the available tickets and displays structured JSON results and status counts.

## 10. Output Structure

Each processed ticket produces a structured result containing:

| Field | Description |
|---|---|
| ticket_id | Unique ticket identifier |
| category | BILLING, DELIVERY, RETURN, ACCOUNT or OTHER |
| urgency | LOW, MEDIUM or HIGH |
| summary | Summary of the customer issue |
| evidence_order_ids | Relevant order identifiers |
| escalation | Indicates whether escalation is recommended |
| status | RESOLVED_DRAFT, NEEDS_INFO or MANUAL_REVIEW |
| suggested_reply | Recommended customer response |
| policy_references | Relevant policy references |

## 11. Safety and Escalation

The system uses deterministic rules to identify conditions that require special handling, including missing customer information, duplicate payments, delivery disputes, expired return windows and suspicious instructions.

The system generates recommendations and draft responses. It does not automatically send customer emails, issue refunds or modify customer accounts.

Cases that cannot be reliably resolved are directed for manual review.

## 12. Testing

The project includes test modules covering:

- Data loading.
- Parallel classification.
- Category routing.
- Pydantic validation.
- Escalation decisions.
- Integration behaviour.

Run the test suite using:

```bash
python -m pytest -v --ignore=customer
```

Refer to the final verified test results and evaluation report for testing outcomes.

## 13. Expected Outcomes

The system aims to:
- Reduce manual ticket classification effort.
- Improve consistency in escalation decisions.
- Provide relevant order and policy evidence.
- Support structured and explainable resolution recommendations.
- Identify cases that require human intervention.

## 14. Future Enhancements

- Web-based customer support dashboard.
- REST API integration.
- Persistent ticket history.
- Advanced analytics and reporting.
- Expanded policy knowledge base.
- Improved classification and evaluation using larger datasets.

## 15. Repository

**GitHub:** https://github.com/Anit-K-T/Customer-Support-Triage-System

**Project:** Customer Support Triage & Escalation System