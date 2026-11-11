"""What each write action must prove (ARCH §9.4). Defined by the verifier, never by the agent.

A proposal that omits any required claim is BLOCKED (`missing_claim`), which closes the round-1 hole
where only the claims the agent chose to list were checked.
"""
from __future__ import annotations

import re

from kavach.common.contracts import ClaimKind as K
from kavach.common.contracts import WriteTool as T

REQUIRED: dict[T, set[K]] = {
    T.issue_refund: {K.ownership, K.state, K.temporal, K.monetary, K.duplicate, K.eligibility, K.policy, K.frequency},
    T.create_return_pickup: {K.ownership, K.state, K.temporal, K.eligibility, K.duplicate, K.policy},
    T.update_address: {K.ownership, K.state, K.channel_identity},
    T.cancel_order: {K.ownership, K.state},
}

DAMAGE_REASONS = {"damaged", "wrong_item"}

# which policy clauses can justify which action (seed.py clause ids)
RELEVANT_CLAUSES: dict[T, set[int]] = {
    T.issue_refund: {1, 2},
    T.create_return_pickup: {1, 2},
    T.update_address: {7},
    T.cancel_order: {8},
}

EXPECTED_STATE: dict[T, str] = {
    T.issue_refund: "delivered",
    T.create_return_pickup: "delivered",
    T.update_address: "not_dispatched",
    T.cancel_order: "not_dispatched",
}


def required_for(tool: T, args: dict) -> set[K]:
    req = set(REQUIRED[tool])
    if tool in (T.issue_refund, T.create_return_pickup) and args.get("reason") in DAMAGE_REASONS:
        req.add(K.evidence)
    return req


# Imperative instructions hidden in data (order notes, return notes). A signal only: the defence is
# "no verdict, no write"; this just makes the attempt visible and forces a human look.
_INJECTION = re.compile(
    r"(ignore|disregard|forget)\b[^.\n]{0,40}\b(rules?|instructions?|polic(y|ies)|previous)"
    r"|^\s*(system|assistant)\s*:|\bsystem\s*:"
    r"|\brefund\s+(rs\.?|inr|₹)?\s*\d{4,}",
    re.IGNORECASE | re.MULTILINE,
)


def injection_flags(text: str) -> list[str]:
    return ["instruction_in_record"] if text and _INJECTION.search(text) else []
