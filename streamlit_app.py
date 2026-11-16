
"""Streamlit UI for the existing Customer Support Triage project.

Run from the repository root:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import streamlit as st

from app.main import process
from group1_tools_and_data.support_tools import load_all


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Customer Support Triage Desk",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM STYLING
# ============================================================

st.markdown(
    """
    <style>
        .stApp {
            background-color: #f5f7fb;
        }

        [data-testid="stSidebar"] {
            background-color: #111827;
        }

        [data-testid="stSidebar"] * {
            color: #f9fafb;
        }

        .hero {
            padding: 1.5rem;
            border-radius: 16px;
            background: linear-gradient(120deg, #172554, #1d4ed8);
            color: white;
            margin-bottom: 1.2rem;
        }

        .hero h1 {
            margin: 0 0 0.35rem 0;
            font-size: 1.8rem;
        }

        .hero p {
            margin: 0;
            color: #dbeafe;
        }

        .panel {
            background: white;
            padding: 1rem 1.1rem;
            border: 1px solid #e5e7eb;
            border-radius: 13px;
            margin-bottom: 0.8rem;
        }

        div[data-testid="stMetric"] {
            background: white;
            border: 1px solid #e5e7eb;
            padding: 14px 16px;
            border-radius: 12px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATA LOADING
# ============================================================

@st.cache_resource(show_spinner="Loading support tickets and policy data...")
def get_store():
    return load_all()


try:
    store = get_store()

except Exception as exc:
    st.error(
        f"Could not load project data: "
        f"{type(exc).__name__}: {exc}"
    )
    st.info(
        "Please check whether the required data files "
        "are available in the project data folder."
    )
    st.stop()


tickets = list(store.tickets.values())
orders = list(store.orders.values())


# ============================================================
# SESSION STATE
# ============================================================

if "history" not in st.session_state:
    st.session_state.history = []

if "batch_results" not in st.session_state:
    st.session_state.batch_results = []

if "latest_result" not in st.session_state:
    st.session_state.latest_result = None


# ============================================================
# PROCESSING FUNCTION
# ============================================================

def run_processing(ticket_id: str | None = None) -> list[dict[str, Any]]:
    """
    Reuse the existing app.main.process() function.

    ticket_id provided: process one ticket.
    ticket_id None: process all tickets.
    """

    args = SimpleNamespace(
        ticket=ticket_id,
        all=ticket_id is None,
    )

    results = asyncio.run(process(args))

    return [
        item.model_dump(mode="json")
        for item in results
    ]


# ============================================================
# ANALYSIS RESULT DISPLAY
# ============================================================

def show_analysis(result: dict[str, Any]) -> None:

    status = str(result.get("status", ""))
    urgency = str(result.get("urgency", ""))

    st.subheader(
        f"Analysis — {result.get('ticket_id', 'Ticket')}"
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Category",
        result.get("category", "—")
    )

    col2.metric(
        "Urgency",
        urgency or "—"
    )

    col3.metric(
        "Status",
        status.replace("_", " ").title() or "—"
    )

    if result.get("escalation"):
        st.warning(
            "This ticket is marked for escalation."
        )

    elif status == "MANUAL_REVIEW":
        st.warning(
            "Automated analysis was incomplete. "
            "Human review is required."
        )

    else:
        st.success("Analysis completed.")

    st.markdown("#### Summary")

    st.write(
        result.get("summary")
        or "No summary available."
    )

    st.markdown("#### Suggested Reply")

    st.text_area(
        "Draft response",
        value=result.get("suggested_reply") or "",
        height=150,
        key=(
            f"reply_{result.get('ticket_id', 'unknown')}_"
            f"{len(st.session_state.history)}"
        ),
    )

    left, right = st.columns(2)

    with left:

        st.markdown("#### Evidence Order IDs")

        evidence = result.get("evidence_order_ids") or []

        if evidence:
            for item in evidence:
                st.write(f"• {item}")
        else:
            st.caption("No evidence order IDs returned.")

    with right:

        st.markdown("#### Policy References")

        references = result.get("policy_references") or []

        if references:
            for item in references:
                st.write(f"• {item}")
        else:
            st.caption("No policy references returned.")


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

st.sidebar.markdown("## 🎧 Support Desk")

st.sidebar.caption(
    "AI-powered ticket triage"
)

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Analyze Ticket",
        "Batch Processing",
        "Ticket History",
    ],
)

st.sidebar.divider()

st.sidebar.caption(
    "Customer Support Triage & Escalation System"
)


# ============================================================
# MAIN HEADER
# ============================================================

st.markdown(
    """
    <div class="hero">
        <h1>Customer Support Triage Desk</h1>
        <p>
            Classify support requests, review evidence
            and prepare consistent responses.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 1. DASHBOARD
# ============================================================

if page == "Dashboard":

    st.subheader("Dashboard Overview")

    total_tickets = len(tickets)
    total_orders = len(orders)

    missing_customer = sum(
        1 for ticket in tickets
        if not ticket.customer_id
    )

    escalated_history = sum(
        1 for item in st.session_state.history
        if item.get("escalation")
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Tickets",
        total_tickets
    )

    col2.metric(
        "Total Orders",
        total_orders
    )

    col3.metric(
        "Missing Customer IDs",
        missing_customer
    )

    col4.metric(
        "Escalated This Session",
        escalated_history
    )

    st.markdown("### Ticket Records")

    if tickets:

        ticket_table = [
            {
                "Ticket ID": ticket.ticket_id,
                "Customer ID": ticket.customer_id or "Missing",
                "Created": ticket.created_at.isoformat(),
                "Message": ticket.message,
            }
            for ticket in tickets
        ]

        st.dataframe(
            ticket_table,
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info("No valid tickets were loaded.")

    with st.expander("Data Quality and Loader Warnings"):

        if store.warnings:

            for warning in store.warnings:
                st.warning(warning)

        else:
            st.success("No data-loading warnings.")

        st.write(
            {
                "Rejected tickets": len(store.rejected_tickets),
                "Rejected orders": len(store.rejected_orders),
                "Duplicate ticket IDs": store.duplicate_ticket_ids,
                "Duplicate order IDs": store.duplicate_order_ids,
            }
        )


# ============================================================
# 2. SINGLE TICKET ANALYSIS
# ============================================================

elif page == "Analyze Ticket":

    st.subheader("Analyze a Single Ticket")

    if not tickets:

        st.info("There are no valid tickets to analyze.")

    else:

        ticket_ids = [
            ticket.ticket_id
            for ticket in tickets
        ]

        selected_id = st.selectbox(
            "Select Ticket",
            ticket_ids,
        )

        selected_ticket = store.get_ticket(selected_id)

        st.markdown("#### Customer Message")

        st.markdown(
            f'<div class="panel">{selected_ticket.message}</div>',
            unsafe_allow_html=True,
        )

        info1, info2 = st.columns(2)

        info1.write(
            f"**Customer ID:** "
            f"{selected_ticket.customer_id or 'Missing'}"
        )

        info2.write(
            f"**Created:** "
            f"{selected_ticket.created_at.isoformat()}"
        )

        related_orders = (
            store.orders_for_customer(
                selected_ticket.customer_id
            )
            if selected_ticket.customer_id
            else []
        )

        with st.expander(
            f"Related Customer Orders ({len(related_orders)})"
        ):

            if related_orders:

                order_table = [
                    {
                        "Order ID": order.order_id,
                        "Total (INR)": order.total_inr,
                        "Payment": order.payment_status,
                        "Delivery": order.delivery_status,
                        "Refund": order.refund_status,
                        "Source": order.source_ref,
                    }
                    for order in related_orders
                ]

                st.dataframe(
                    order_table,
                    use_container_width=True,
                    hide_index=True,
                )

            else:
                st.caption(
                    "No related orders found for this customer."
                )

        if st.button(
            "Run AI Ticket Analysis",
            type="primary",
            use_container_width=True,
        ):

            try:

                with st.spinner(
                    "Running the existing triage and investigation pipeline..."
                ):

                    result = run_processing(selected_id)[0]

                st.session_state.history.insert(
                    0,
                    result
                )

                st.session_state.latest_result = result

            except Exception as exc:

                st.error(
                    f"Ticket processing failed: "
                    f"{type(exc).__name__}: {exc}"
                )

        latest = st.session_state.latest_result

        if (
            latest is not None
            and latest.get("ticket_id") == selected_id
        ):

            show_analysis(latest)


# ============================================================
# 3. BATCH PROCESSING
# ============================================================

elif page == "Batch Processing":

    st.subheader("Batch Ticket Processing")

    st.write(
        f"There are **{len(tickets)} valid tickets** available."
    )

    st.caption(
        "This runs the existing project pipeline "
        "for every loaded ticket."
    )

    if st.button(
        "Process All Tickets",
        type="primary",
        use_container_width=True,
        disabled=not tickets,
    ):

        try:

            with st.spinner(
                f"Processing {len(tickets)} tickets. "
                "This may take a little while..."
            ):

                results = run_processing()

            st.session_state.batch_results = results

            st.session_state.history = (
                results + st.session_state.history
            )

            st.success(
                f"Finished processing {len(results)} tickets."
            )

        except Exception as exc:

            st.error(
                f"Batch processing failed: "
                f"{type(exc).__name__}: {exc}"
            )

    results = st.session_state.batch_results

    if results:

        st.markdown("### Batch Summary")

        counts = {}

        for item in results:

            key = item.get("status", "UNKNOWN")

            counts[key] = counts.get(key, 0) + 1

        cols = st.columns(max(1, len(counts)))

        for col, (status, count) in zip(
            cols,
            counts.items()
        ):

            col.metric(
                status.replace("_", " ").title(),
                count
            )

        st.markdown("### Processed Tickets")

        batch_table = [
            {
                "Ticket ID": item.get("ticket_id"),
                "Category": item.get("category"),
                "Urgency": item.get("urgency"),
                "Escalation": (
                    "Yes"
                    if item.get("escalation")
                    else "No"
                ),
                "Status": item.get("status"),
                "Summary": item.get("summary"),
            }
            for item in results
        ]

        st.dataframe(
            batch_table,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### View Detailed Result")

        selected_result_id = st.selectbox(
            "Select Ticket",
            [
                item.get("ticket_id")
                for item in results
            ],
            key="batch_result_choice",
        )

        selected_result = next(
            item
            for item in results
            if item.get("ticket_id") == selected_result_id
        )

        show_analysis(selected_result)


# ============================================================
# 4. TICKET HISTORY
# ============================================================

elif page == "Ticket History":

    st.subheader("Analysis History")

    history = st.session_state.history

    if not history:

        st.info(
            "No tickets have been analyzed "
            "in this Streamlit session yet."
        )

    else:

        st.caption(
            "History is kept for the current Streamlit session."
        )

        history_table = [
            {
                "Ticket ID": item.get("ticket_id"),
                "Category": item.get("category"),
                "Urgency": item.get("urgency"),
                "Escalation": (
                    "Yes"
                    if item.get("escalation")
                    else "No"
                ),
                "Status": item.get("status"),
                "Summary": item.get("summary"),
            }
            for item in history
        ]

        st.dataframe(
            history_table,
            use_container_width=True,
            hide_index=True,
        )

        history_ids = [
            item.get("ticket_id")
            for item in history
        ]

        chosen_id = st.selectbox(
            "Open an Analysis",
            history_ids,
            key="history_choice",
        )

        chosen = next(
            item
            for item in history
            if item.get("ticket_id") == chosen_id
        )

        show_analysis(chosen)
