"""
Guardrails — pre-LLM query relevance filter.

Catches obviously irrelevant queries (general knowledge, coding, jokes,
math, entertainment, etc.) BEFORE making an LLM API call, saving cost
and latency.

Usage:
    from guardrails import check_relevance

    rejection = check_relevance("Tell me a joke")
    if rejection:
        return rejection  # "This system is designed to answer ..."
"""

from __future__ import annotations

import re


# ─── Standard rejection message ─────────────────────────────────────────────

REJECTION_MESSAGE = (
    "This system is designed to answer questions related to the "
    "provided dataset only."
)

# ─── Off-topic patterns ─────────────────────────────────────────────────────
# Each regex targets a category of irrelevant queries.  We use word
# boundaries and case-insensitive matching to minimise false positives.

_OFF_TOPIC_PATTERNS: list[re.Pattern] = [
    # ── General knowledge / trivia ───────────────────────────────────
    re.compile(
        r"\b(?:capital|president|population|continent|country|planet|"
        r"language|currency|flag|geography|history|who\s+(?:is|was|were|invented|discovered)|"
        r"when\s+(?:was|did|is)|where\s+(?:is|was|are)|"
        r"what\s+is\s+(?:the\s+)?(?:capital|population|meaning|definition|difference))\b",
        re.IGNORECASE,
    ),
    # ── Coding / programming ─────────────────────────────────────────
    re.compile(
        r"\b(?:write\s+(?:a\s+)?(?:code|program|function|script|class|algorithm)|"
        r"write\s+(?:a\s+)?(?:python|java|javascript|typescript|rust|c\+\+|go)\s+"
        r"(?:code|program|function|script|class|method)|"
        r"(?:code|program|script)\s+(?:to|for|that)|"
        r"how\s+(?:to|do\s+(?:I|you))\s+(?:code|program|implement|debug|compile)|"
        r"(?:python|java|javascript|typescript|rust|golang|c\+\+|html|css|react|"
        r"django|flask|node\.?js|sql\s+tutorial|regex)\s+(?:code|example|tutorial|help)|"
        r"explain\s+(?:this\s+)?(?:code|error|bug|syntax)|"
        r"fix\s+(?:this\s+|my\s+)?(?:code|error|bug)|"
        r"(?:leetcode|hackerrank|codechef|codeforces)|"
        r"data\s+structure|sorting\s+algorithm|binary\s+(?:tree|search))\b",
        re.IGNORECASE,
    ),
    # ── Jokes / entertainment / creative ─────────────────────────────
    re.compile(
        r"\b(?:tell\s+(?:me\s+)?(?:a\s+)?joke|"
        r"make\s+me\s+laugh|"
        r"write\s+(?:a\s+)?(?:poem|story|essay|song|lyrics|haiku)|"
        r"sing\s+(?:a\s+)?song|"
        r"funny|humor|riddle|"
        r"roleplay|pretend\s+(?:to\s+be|you\s+are))\b",
        re.IGNORECASE,
    ),
    # ── Math / science (non-data) ────────────────────────────────────
    re.compile(
        r"\b(?:solve\s+(?:this\s+)?(?:equation|problem|integral|derivative)|"
        r"solve\s+\d+|"
        r"(?:what|how\s+much)\s+is\s+\d+\s*[\+\-\*\/x×÷]\s*\d+|"
        r"^\s*\d+\s*[\+\-\*\/x×÷]\s*\d+\s*[=\?]?\s*$|"
        r"calculate\s+(?:the\s+)?(?:area|volume|circumference|factorial|"
        r"square\s+root|logarithm|probability)|"
        r"(?:newton|einstein|quantum|relativity|thermodynamics|"
        r"photosynthesis|mitosis|chemistry|physics|biology)\b)",
        re.IGNORECASE,
    ),
    # ── Weather / time / personal assistant ──────────────────────────
    re.compile(
        r"\b(?:(?:what(?:'s|\s+is)\s+)?the\s+weather|"
        r"(?:weather|temperature|forecast)\s+(?:in|at|for|today|tomorrow)|"
        r"what\s+(?:time|day|date)\s+is\s+it|"
        r"set\s+(?:a\s+)?(?:timer|alarm|reminder)|"
        r"play\s+(?:music|song|video)|"
        r"open\s+(?:youtube|google|spotify|browser|app)|"
        r"translate\s+.+\s+(?:to|into)|"
        r"send\s+(?:a\s+)?(?:message|email|text))\b",
        re.IGNORECASE,
    ),
    # ── Opinion / philosophical / personal ───────────────────────────
    re.compile(
        r"\b(?:(?:what\s+)?(?:do\s+)?you\s+(?:think|feel|believe|like|prefer|recommend)|"
        r"what\s+is\s+(?:the\s+)?(?:meaning|purpose)\s+of\s+life|"
        r"(?:are\s+you|who\s+are\s+you|what\s+are\s+you)|"
        r"(?:your\s+(?:name|opinion|favourite|favorite))|"
        r"best\s+(?:movie|book|game|anime|show|restaurant|place))\b",
        re.IGNORECASE,
    ),
]


# ─── Domain-relevant keywords ───────────────────────────────────────────────
# If a query contains at least one of these, we consider it *potentially*
# relevant and let it through to the LLM.  This acts as a safety valve so
# that the blocklist patterns don't accidentally filter real questions
# like "What is the total order amount?".

_DOMAIN_KEYWORDS = re.compile(
    r"\b(?:order|orders|customer|customers|product|products|"
    r"delivery|deliveries|shipment|shipments|"
    r"invoice|invoices|bill|bills|"
    r"payment|payments|"
    r"address|addresses|"
    r"revenue|sales|amount|price|quantity|stock|sku|"
    r"shipped|delivered|pending|confirmed|cancelled|paid|unpaid|overdue|"
    r"tracking|carrier|refund|refunded|"
    r"total|count|sum|average|max|min|top|"
    r"item|items|order_item|"
    r"trace|flow|track|chain|journey)\b",
    re.IGNORECASE,
)


# ─── Public API ──────────────────────────────────────────────────────────────


def check_relevance(query: str) -> str | None:
    """
    Check whether a user query is relevant to the dataset.

    Parameters
    ----------
    query : str
        The raw user query.

    Returns
    -------
    str | None
        ``None`` if the query is allowed (relevant).
        The rejection message string if the query is irrelevant.
    """
    text = query.strip()

    if not text:
        return REJECTION_MESSAGE

    # If the query references a domain keyword, allow it through even if
    # an off-topic pattern also matches (e.g. "what is the total order amount")
    if _DOMAIN_KEYWORDS.search(text):
        return None

    # Check against off-topic patterns
    for pattern in _OFF_TOPIC_PATTERNS:
        if pattern.search(text):
            return REJECTION_MESSAGE

    # No blocklist match → allow through to the LLM
    return None


# ─── CLI test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        # Should be BLOCKED (irrelevant)
        ("What is the capital of France?", True),
        ("Tell me a joke", True),
        ("Write a Python function to sort a list", True),
        ("What is the meaning of life?", True),
        ("Solve 2 + 2", True),
        ("What's the weather in Delhi?", True),
        ("Who is the president of India?", True),
        ("Write a poem about love", True),
        ("Explain this code for me", True),
        ("What is quantum physics?", True),
        ("Translate hello to French", True),
        ("What do you think about AI?", True),
        ("Best movie of 2024?", True),
        # Should be ALLOWED (dataset-relevant)
        ("Show all customers", False),
        ("How many orders are pending?", False),
        ("Total revenue by customer", False),
        ("trace order 1", False),
        ("What is the total order amount?", False),
        ("Top 5 products by price", False),
        ("Show delivered shipments", False),
        ("Unpaid invoices", False),
        ("Payment status for invoice 3", False),
    ]

    print("Guardrail Tests")
    print("=" * 65)
    passed = 0
    for query, should_block in test_cases:
        result = check_relevance(query)
        is_blocked = result is not None
        ok = is_blocked == should_block
        passed += ok
        status = "✅" if ok else "❌"
        tag = "BLOCK" if is_blocked else "ALLOW"
        expected = "BLOCK" if should_block else "ALLOW"
        suffix = "" if ok else f"  (expected {expected})"
        print(f"  {status} [{tag:5s}] {query}{suffix}")

    print(f"\n  {passed}/{len(test_cases)} passed")
