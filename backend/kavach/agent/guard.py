"""Manipulation guard (ARCH §11). v0 = transparent rules; Phase 5 swaps in the trained model behind the
same `score()` interface (done: guard_model.py, distilled from MuRIL, see ml/train.py). The score can only add caution: it is sent to the trust service, which may turn
ALLOW into ESCALATE but never the reverse.

Tags: AUTHORITY ("owner ne bola"), POLICY_CLAIM ("30 din ka return"), INJECTION ("ignore rules"),
PRESSURE (threats, urgency), IMPERSONATION ("main seller hoon").
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from kavach.agent import guard_model

_RULES: list[tuple[str, float, re.Pattern]] = [
    ("AUTHORITY", 0.85, re.compile(
        r"\b(owner|malik|maalik|manager|seller|boss|admin|support team|ceo)\b[^.?!\n]{0,40}\b(bola|boli|kaha|said|told|promised|approved?|allowed?|manzoor|confirm(ed)?)\b"
        r"|\b(approved?|manzoor|allowed)\b[^.?!\n]{0,30}\b(owner|malik|manager|seller)\b", re.I)),
    ("POLICY_CLAIM", 0.7, re.compile(
        r"\b(\d{2,3})\s*(din|days?|day)\b[^.?!\n]{0,25}\b(return|refund|replacement|policy)\b"
        r"|\b(return|refund|policy)\b[^.?!\n]{0,25}\b(\d{2,3})\s*(din|days?)\b"
        r"|\bpolicy\s+(says|kehti|me likha|mein likha)\b", re.I)),
    ("INJECTION", 0.95, re.compile(
        r"\b(ignore|disregard|forget|bhool\s*jao)\b[^.\n]{0,40}\b(rules?|instructions?|polic(y|ies)|previous|niyam)\b"
        r"|^\s*(system|assistant)\s*:|\byou (are|must) now\b|\bdeveloper mode\b|\bjailbreak\b", re.I | re.M)),
    ("PRESSURE", 0.55, re.compile(
        r"\b(consumer court|police|fir|lawyer|legal action|case kar(unga|ungi|enge)|viral|1 star|one star|bad review"
        r"|review (dunga|dungi|likh)|abhi ke abhi|turant|immediately or)\b", re.I)),
    ("IMPERSONATION", 0.85, re.compile(
        r"\b(main|mai|i am|i'm|this is)\s+(the\s+)?(seller|owner|malik|admin|manager|delivery boy|courier)\b"
        r"|\b(seller|owner)\s+(ka|ki)\s+(bhai|cousin|dost|friend|relative)\b", re.I)),
]


@dataclass
class GuardResult:
    score: float
    tags: list[str] = field(default_factory=list)
    model: str = "rules-v0"


def score(text: str) -> GuardResult:
    tags, s = [], 0.0
    for tag, weight, rx in _RULES:
        if rx.search(text or ""):
            tags.append(tag)
            s = max(s, weight)
    if len(tags) >= 2:
        s = min(0.99, s + 0.05)
    model = "rules-v0"
    p = guard_model.probability(text)
    if p is not None:                         # Phase 5: the trained student can only ADD caution
        model = "rules-v0+student-v1"
        thr = guard_model.threshold()
        # map onto the router's line (0.8 = escalate): below the model's threshold stays below 0.8
        ms = 0.8 + 0.19 * (p - thr) / max(1e-6, 1 - thr) if p >= thr else 0.79 * p / max(1e-6, thr)
        if p >= thr and "MANIPULATION" not in tags:
            tags.append("MANIPULATION")
        s = max(s, ms)
    return GuardResult(score=round(s, 2), tags=tags, model=model)
