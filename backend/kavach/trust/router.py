"""Risk router (ARCH §8.3, §9.4). Deterministic, so every decision can be explained in one line.

BLOCK    if any required claim is missing or any claim fails.
ESCALATE if a source was unreachable, or any risk flag is up (over the auto-limit, over the hard cap,
         an earlier refund in 30 days, the ML guard score is high, an instruction hidden in a record).
ALLOW    otherwise.
The ML guard can only push ALLOW to ESCALATE. It is never consulted for BLOCK and never lowers anything.
"""
from __future__ import annotations

from kavach.common.contracts import ClaimResult, Risk, Verdict, WriteTool

GUARD_ESCALATE_AT = 0.8


def decide(tool: WriteTool, results: list[ClaimResult], risk: Risk, *, source_unavailable: bool = False) -> tuple[Verdict, list[str]]:
    failed = [r for r in results if not r.ok]
    if failed:
        reasons = sorted({("missing_" + r.kind.value) if r.tier == "REQ" else r.kind.value for r in failed})
        return Verdict.BLOCK, reasons
    if source_unavailable:
        return Verdict.ESCALATE, ["source_unavailable"]
    reasons: list[str] = []
    if risk.over_hard_cap:
        reasons.append("over_hard_cap")
    elif risk.over_auto_limit:
        reasons.append("over_auto_limit")
    if tool is WriteTool.issue_refund and risk.refunds_30d >= 1:
        reasons.append("refund_frequency")
    if risk.guard_score is not None and risk.guard_score >= GUARD_ESCALATE_AT:
        reasons.append("guard_flag")
    reasons += [f for f in risk.flags if f not in reasons]
    return (Verdict.ESCALATE, reasons) if reasons else (Verdict.ALLOW, [])
