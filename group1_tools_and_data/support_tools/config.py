"""
config.py
=========
WHAT THIS FILE DOES
    Holds every setting and constant used by the "Tools & Data Processing"
    part of the project, so nothing is hard-coded in other files:
      * where the data files live
      * extra escalation keywords the team added on top of the policy file
      * patterns that detect prompt-injection text inside customer messages
      * the timeout used when an agent runs a tool

    If the team wants to change a rule (for example, stop escalating
    prompt-injection tickets), this is the first place to look.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# File locations (relative to the project root, so it works on any computer)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TICKETS_FILE = DATA_DIR / "tickets.csv"
ORDERS_FILE = DATA_DIR / "orders.csv"
POLICY_FILE = DATA_DIR / "support_policy.json"

# ---------------------------------------------------------------------------
# Allowed values (the same words the final JSON report must use)
# ---------------------------------------------------------------------------
URGENCY_LEVELS = ("LOW", "MEDIUM", "HIGH")
STATUSES = ("RESOLVED_DRAFT", "NEEDS_INFO", "MANUAL_REVIEW")

# ---------------------------------------------------------------------------
# Escalation settings
# ---------------------------------------------------------------------------
# The official keywords come from data/support_policy.json. These are EXTRA
# words our team added (they are NOT in the policy file). They are kept in a
# separate list so it is always clear which keywords are official.
EXTRA_ESCALATION_KEYWORDS = ("hacked", "account takeover", "compromised")

# Which category a keyword hints at (None = could be several categories).
KEYWORD_CATEGORY_HINT = {
    "charged twice": "BILLING",
    "duplicate payment": "BILLING",
    "someone accessed": "ACCOUNT",
    "unauthorized": None,
    "fraud": None,
    "hacked": "ACCOUNT",
    "account takeover": "ACCOUNT",
    "compromised": "ACCOUNT",
}

# Text patterns that look like a customer trying to "boss" the AI around.
# Customer messages are UNTRUSTED data, never instructions.
PROMPT_INJECTION_PATTERNS = (
    r"ignore\s+(all\s+|your\s+|the\s+|previous\s+)*(polic\w+|instruction\w*|rules?)",
    r"disregard\s+(all\s+|your\s+|the\s+|previous\s+)*(polic\w+|instruction\w*|rules?)",
    r"(immediately|just|now)\s+(send|issue|process)\s+(a\s+|the\s+)?refund",
    r"you\s+are\s+now\s+",
    r"system\s+prompt",
    r"override\s+(the\s+)?(policy|policies|rules?)",
)

# Team decision: should a suspected prompt-injection ticket be escalated to a
# human? True = yes (safer). Change to False to only flag it.
ESCALATE_ON_PROMPT_INJECTION = True

# ---------------------------------------------------------------------------
# Tool safety
# ---------------------------------------------------------------------------
# If a tool takes longer than this many seconds, we stop waiting and report
# "TIMEOUT" instead of hanging the whole agent team.
TOOL_TIMEOUT_SECONDS = 5

# Tool names that must NEVER exist in this project (the assignment says there
# is no refund / payment / email tool). A test checks this list.
FORBIDDEN_TOOL_NAMES = (
    "issue_refund",
    "refund_payment",
    "reverse_charge",
    "send_email",
    "modify_account",
    "update_order",
)
