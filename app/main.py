"""CLI entry point for the Customer Support Triage & Escalation Desk.

Run from the repository root with:
    python -m app.main --ticket T001
    python -m app.main --all
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from dotenv import load_dotenv

from app.langchain_pipeline import category_router, ticket_processing_pipeline
from app.schemas import TicketAnalysis, TicketStatus
from app.team import create_model_client, get_resolution_text, investigate_ticket
from group1_tools_and_data.support_tools import evaluate_escalation, load_all


def _ticket_dict(ticket: Any) -> dict[str, Any]:
    """Convert the loaded ticket record to the application's input shape."""
    return {
        "ticket_id": ticket.ticket_id,
        "customer_id": ticket.customer_id,
        "message": ticket.message,
        "created_at": ticket.created_at.isoformat(),
    }


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _extract_json(text: str) -> dict[str, Any]:
    """Read the JSON object from ResolutionAgent's response."""
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("ResolutionAgent did not return a JSON object")
    value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("ResolutionAgent JSON must be an object")
    return value


def _safe_fallback(
    ticket: dict[str, Any],
    category: str = "OTHER",
    urgency: str = "MEDIUM",
    summary: str = "Automated analysis was incomplete; human review is required.",
    *,
    escalation: bool = False,
    evidence_order_ids: list[str] | None = None,
    policy_references: list[str] | None = None,
) -> TicketAnalysis:
    """Create a valid conservative result when classification/team work fails."""
    return TicketAnalysis(
        ticket_id=ticket["ticket_id"],
        category=category,
        urgency=urgency,
        summary=summary,
        evidence_order_ids=evidence_order_ids or [],
        escalation=escalation,
        status=TicketStatus.MANUAL_REVIEW,
        suggested_reply=(
            "Thanks for contacting us. We need a support specialist to review "
            "your case before we can confirm the next steps."
        ),
        policy_references=policy_references or [],
    )


async def analyze_one(ticket_record: Any, store: Any, model_client: Any) -> TicketAnalysis:
    """Run LangChain triage, deterministic checks, then AutoGen investigation."""
    ticket = _ticket_dict(ticket_record)

    try:
        classification_result = ticket_processing_pipeline.invoke(ticket)
        classification = classification_result.model_dump(mode="json")

        # Routing is explicit and based on the validated LangChain category.
        route = category_router.invoke(classification_result)

        # This deterministic rules engine runs before the LLM team and wins
        # over any conflicting agent suggestion.
        decision_object = evaluate_escalation(store, ticket_record)
        decision = decision_object.to_dict()

        category = decision.get("category_hint") or classification["category"]
        urgency = max(
            [classification["urgency"], decision.get("urgency", "LOW")],
            key={"LOW": 0, "MEDIUM": 1, "HIGH": 2}.get,
        )
        evidence_ids = decision.get("evidence_order_ids", [])
        policy_refs = decision.get("policy_references", [])

        team_result = await investigate_ticket(
            ticket=ticket,
            classification={**classification, "route": route},
            decision=decision,
            store=store,
            model_client=model_client,
        )
        agent_result = _extract_json(get_resolution_text(team_result))

        # The team can add references discovered in tools, while the known
        # deterministic references are retained.
        evidence_ids = list(dict.fromkeys(
            evidence_ids + agent_result.get("evidence_order_ids", [])
        ))
        policy_refs = list(dict.fromkeys(
            policy_refs + agent_result.get("policy_references", [])
        ))

        status = decision.get("suggested_status", "RESOLVED_DRAFT")
        if classification.get("status") == "MANUAL_REVIEW":
            status = "MANUAL_REVIEW"

        reply = agent_result.get("suggested_reply")
        if not isinstance(reply, str) or not reply.strip():
            raise ValueError("ResolutionAgent did not provide a suggested reply")

        # Never publish model wording that claims a refund was completed.
        refund_claims = (
            "refund has been issued",
            "refund was issued",
            "we have refunded",
            "refund is completed",
            "refund has been processed",
        )
        if any(phrase in reply.lower() for phrase in refund_claims):
            raise ValueError("ResolutionAgent made an unsupported refund claim")

        return TicketAnalysis(
            ticket_id=ticket["ticket_id"],
            category=category,
            urgency=urgency,
            summary=agent_result.get("summary") or classification["summary"],
            evidence_order_ids=evidence_ids,
            escalation=bool(decision.get("escalate", False)),
            status=status,
            suggested_reply=reply.strip(),
            policy_references=policy_refs,
        )
    except Exception as exc:
        # Preserve the original ticket ID and report a safe result instead of
        # dropping a ticket when classification, tools, or the model fails.
        print(
            f"Warning: {ticket['ticket_id']} needs manual review "
            f"({type(exc).__name__}: {exc})",
            file=sys.stderr,
        )
        return _safe_fallback(ticket)


async def process(args: argparse.Namespace) -> list[TicketAnalysis]:
    load_dotenv()
    store = load_all()

    if args.ticket:
        ticket_record = store.get_ticket(args.ticket)
        if ticket_record is None:
            raise ValueError(f"Unknown ticket ID: {args.ticket}")
        tickets = [ticket_record]
    else:
        tickets = list(store.tickets.values())

    model_client = None
    results: list[TicketAnalysis] = []
    try:
        # Construct once and share the client across the selected ticket batch.
        model_client = create_model_client()
        for ticket_record in tickets:
            results.append(await analyze_one(ticket_record, store, model_client))
    except Exception as exc:
        # If the model client cannot be created (for example, no API key),
        # produce explicit manual-review results for every selected ticket.
        print(
            f"Warning: AutoGen is unavailable ({type(exc).__name__}: {exc})",
            file=sys.stderr,
        )
        results = [_safe_fallback(_ticket_dict(t)) for t in tickets]
    finally:
        if model_client is not None:
            await model_client.close()

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify, investigate, and draft replies for support tickets."
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--ticket", help="Process one ticket, for example T001")
    selection.add_argument("--all", action="store_true", help="Process every loaded ticket")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        reports = asyncio.run(process(args))
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Error: could not load project data ({exc})", file=sys.stderr)
        return 1

    report_json = [item.model_dump(mode="json") for item in reports]
    print(json.dumps(report_json, ensure_ascii=False, indent=2))
    print(
        f"Processed {len(reports)} ticket(s). Status counts: "
        + json.dumps(
            {
                status.value: sum(item.status == status for item in reports)
                for status in TicketStatus
            }
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
