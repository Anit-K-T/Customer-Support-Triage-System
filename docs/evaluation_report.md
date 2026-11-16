# Evaluation Report
## Customer Support Triage & Escalation System

### 1. Introduction

This report documents the final testing and evaluation of the Customer Support Triage & Escalation System.

The system combines LangChain preprocessing and classification, Pydantic validation, deterministic escalation rules, local order and policy tools, and an AutoGen multi-agent workflow to analyse customer support tickets and generate structured resolution recommendations.

Testing covered individual components, safety and edge cases, integration behaviour, and end-to-end ticket processing.

---

### 2. Evaluation Objectives

The evaluation was conducted to verify:

- Customer support ticket data loading.
- LangChain preprocessing and classification.
- Category, urgency and summary generation.
- Pydantic schema validation.
- Category-based routing.
- Deterministic escalation decisions.
- Order lookup and policy retrieval.
- AutoGen multi-agent investigation.
- Edge-case and safety handling.
- Structured JSON output.
- Single-ticket processing.
- Batch processing of all available tickets.
- Fallback and manual-review behaviour.

---

### 3. Dataset

The project uses a local dataset containing 12 customer support tickets together with order information and support policy data.

The dataset contains billing, delivery, return, account and general support scenarios.

It also includes safety and edge cases such as duplicate payments, missing customer information, unknown order IDs, prompt injection and conflicting delivery information.

---

### 4. Automated Test Results

The core automated test suite was executed using:

`python -m pytest -v --ignore=customer`

Final result:

- Tests collected: 55
- Tests passed: 55
- Tests failed: 0
- Errors: 0
- Pass rate: 100% for the automated core test suite
- Execution time: 0.88 seconds

The automated tests covered data loading, order lookup, policy retrieval, deterministic escalation, delivery verification, billing safety, prompt-injection detection, agent tool permissions and tool failure handling.

---

### 5. Component Testing Results

| Test Area | Result | Notes |
|---|---|---|
| Data loading | PASS | All 12 supplied tickets loaded and processed |
| LangChain preprocessing | PASS | Ticket preprocessing completed successfully |
| Parallel classification | PASS | Category, urgency and summary generated |
| Pydantic validation | PASS | Valid output accepted |
| Invalid Pydantic input | PASS | Invalid category value was rejected with ValidationError |
| Category routing | PASS | Tickets routed to appropriate department |
| Deterministic escalation | PASS | Escalation rules behaved as expected |
| Order lookup | PASS | Known and unknown order scenarios handled correctly |
| Policy retrieval | PASS | Relevant policy sections retrieved |
| AutoGen multi-agent workflow | PASS | Multi-agent investigation completed successfully |
| Structured output | PASS | Required output fields were generated |
| Safe fallback | PASS | Failures safely resulted in manual-review behaviour |

---

### 6. Edge-Case Testing

The required edge cases were verified.

| Edge Case | Result | Observed Behaviour |
|---|---|---|
| Duplicate payment | PASS | High urgency and escalation triggered without falsely claiming that a refund was completed |
| Delivered but not received | PASS | Delivery dispute identified and escalated |
| Missing customer ID | PASS | System returned NEEDS_INFO |
| Prompt injection | PASS | Untrusted instructions did not override system behaviour; case directed to MANUAL_REVIEW |
| Unknown order ID | PASS | No order information was fabricated; system returned NEEDS_INFO |
| Expired return window | PASS | Return-window violation identified and escalation triggered |
| Conflicting delivery status | PASS | Conflict between customer statement and order data was detected |

Edge-case result: **7/7 PASS**

---

### 7. End-to-End Testing

#### Single-Ticket Test

Ticket T001 was processed using:

`python -m app.main --ticket T001`

The system successfully produced structured output containing:

- ticket_id
- category
- urgency
- summary
- evidence_order_ids
- escalation
- status
- suggested_reply
- policy_references

The ticket was classified as a billing issue with HIGH urgency and escalation enabled. Order O1001 was correctly identified as supporting evidence.

Result: **PASS**

#### Full Dataset Test

All tickets were processed using:

`python -m app.main --all`

Result:

- Tickets processed: 12
- Successful processing: 12
- Runtime failures: 0

Final status distribution:

| Status | Count |
|---|---:|
| RESOLVED_DRAFT | 9 |
| NEEDS_INFO | 2 |
| MANUAL_REVIEW | 1 |
| **Total** | **12** |

Result: **12/12 PASS**

---

### 8. Multi-Agent Workflow Evaluation

The AutoGen workflow uses specialised agents for billing, delivery, policy and resolution tasks.

The agents operate within a bounded RoundRobinGroupChat with a termination condition and maximum-turn limit.

The deterministic escalation result is calculated before the AutoGen investigation and is treated as authoritative when agent reasoning conflicts with deterministic safety rules.

The workflow successfully generated resolution recommendations during end-to-end testing.

Result: **PASS**

---

### 9. Safety Evaluation

Safety controls were successfully verified.

The system:

- Does not provide tools that directly execute refunds or payments.
- Does not automatically send customer emails.
- Does not modify customer accounts.
- Detects prompt-injection attempts.
- Avoids inventing unknown order information.
- Handles tool errors and timeouts safely.
- Prevents unsupported claims that a refund has already been executed.
- Uses deterministic escalation rules for critical conditions.
- Supports NEEDS_INFO and MANUAL_REVIEW when reliable automated resolution is not appropriate.

Result: **PASS**

---

### 10. Integration Test Correction

During initial testing, `test_integration.py` prevented the complete pytest suite from being collected successfully.

Two issues were identified in the integration script:

1. The script imported `support_tools` without the correct package path.
2. The script treated `Ticket` and `EscalationDecision` objects as dictionaries instead of accessing their object attributes.

The integration script was corrected to use the production support-tools package and object attribute access.

After the correction:

- `python test_integration.py` completed successfully.
- The complete automated test suite was rerun.
- All 55 automated tests passed.

Status: **RESOLVED**

---

### 11. Evaluation Finding

#### Duplicate Escalation Implementations

Two escalation implementations were identified:

- `app/escalation.py`
- `group1_tools_and_data/support_tools/escalation.py`

The production application uses the escalation implementation under `group1_tools_and_data/support_tools`, while the standalone `test_escalation.py` script tests the simpler implementation under `app/escalation.py`.

This does not currently prevent the application from functioning correctly, and the production deterministic escalation engine is covered by the automated core tests.

However, maintaining two implementations can create future test and maintenance inconsistencies.

**Severity:** Medium  
**Type:** Maintainability / Test Consistency

**Recommendation:** Future development should consolidate escalation behaviour or ensure tests directly exercise the same implementation used by the production application.

---

### 12. Documentation Verification

Project documentation was reviewed against the tested implementation.

| Document | Result |
|---|---|
| README.md | PASS |
| architecture.md | PASS |
| API_Documentation.md | PASS |
| evaluation_report.md | Updated with final verification results |

The architecture correctly represents the overall processing flow from data loading through LangChain, deterministic escalation, support tools, AutoGen investigation and structured output.

The architecture diagram provides a simplified representation of the AutoGen interaction; the implementation uses a bounded RoundRobinGroupChat for agent coordination.

---

### 13. Final Evaluation Summary

| Evaluation Area | Final Result |
|---|---|
| Core automated tests | 55/55 PASS |
| Ticket dataset processing | 12/12 PASS |
| Required edge cases | 7/7 PASS |
| LangChain pipeline | PASS |
| Pydantic validation | PASS |
| Deterministic escalation | PASS |
| Order and policy tools | PASS |
| AutoGen workflow | PASS |
| Structured JSON output | PASS |
| Safety controls | PASS |
| Single-ticket E2E | PASS |
| Full-dataset E2E | PASS |
| Documentation verification | PASS |

---

### 14. Conclusion

The Customer Support Triage & Escalation System successfully completed component, automated, edge-case and end-to-end testing.

The core automated test suite achieved **55/55 passing tests**, all **12 customer support tickets** were successfully processed end-to-end, and all **7 required edge cases** demonstrated the expected safety or escalation behaviour.

An integration-script issue identified during testing was corrected and verified through a complete regression test run.

One maintainability observation remains regarding duplicate escalation implementations. This does not currently prevent successful operation but should be considered for future code consolidation.

Based on the completed testing, the system is considered **functionally ready for project submission**, subject to normal final repository and submission checks.

---

### 15. Future Improvements

- Consolidate duplicate escalation implementations.
- Expand the customer support ticket dataset.
- Introduce quantitative classification accuracy metrics using labelled ground-truth data.
- Add additional adversarial and prompt-injection test cases.
- Expand automated integration and end-to-end testing.
- Improve multi-agent observability and tracing.
- Add a web-based monitoring dashboard.