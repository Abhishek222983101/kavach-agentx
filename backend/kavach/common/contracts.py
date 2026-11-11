"""Shared data contracts (ARCH §9). Every process speaks these shapes; change them only together with the docs.

Money is integer paise. Free text from customers is untrusted and is never used as evidence on its own.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class WriteTool(StrEnum):
    issue_refund = "issue_refund"
    create_return_pickup = "create_return_pickup"
    update_address = "update_address"
    cancel_order = "cancel_order"


class ClaimKind(StrEnum):
    ownership = "ownership"
    state = "state"
    temporal = "temporal"
    monetary = "monetary"
    duplicate = "duplicate"
    eligibility = "eligibility"
    evidence = "evidence"
    frequency = "frequency"
    channel_identity = "channel_identity"
    policy = "policy"
    authority = "authority"


class Source(StrEnum):
    tool = "tool"        # the agent read it from a tool
    policy = "policy"    # the agent quotes the written policy
    customer = "customer"  # the customer said it (never trusted alone)


class Verdict(StrEnum):
    ALLOW = "ALLOW"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"


class Claim(Strict):
    kind: ClaimKind
    source: Source = Source.tool
    statement: str = Field(default="", max_length=500)
    expect: Literal["delivered", "not_dispatched"] | None = None
    clause_id: int | None = None
    quote: str | None = Field(default=None, max_length=600)


class RefundArgs(Strict):
    order_id: int = Field(gt=0)
    amount_paise: int = Field(gt=0, le=10_000_000)
    reason: Literal["damaged", "wrong_item", "not_delivered", "changed_mind", "other"] = "other"


class ReturnArgs(Strict):
    order_id: int = Field(gt=0)
    reason: Literal["damaged", "wrong_item", "changed_mind", "other"] = "other"


class AddressArgs(Strict):
    order_id: int = Field(gt=0)
    new_address: str = Field(min_length=6, max_length=300)


class CancelArgs(Strict):
    order_id: int = Field(gt=0)


ARGS_MODEL: dict[WriteTool, type[Strict]] = {
    WriteTool.issue_refund: RefundArgs,
    WriteTool.create_return_pickup: ReturnArgs,
    WriteTool.update_address: AddressArgs,
    WriteTool.cancel_order: CancelArgs,
}


class Caller(Strict):
    customer_id: str = Field(min_length=1, max_length=64)
    channel: Literal["whatsapp", "telegram", "web", "test"]
    channel_user_id: str = Field(min_length=1, max_length=128)


class ProposalIn(Strict):
    """What the agent process sends to the trust service."""
    trace_id: str = Field(min_length=1, max_length=64)
    tool: WriteTool
    args: dict[str, Any]
    claims: list[Claim] = Field(default_factory=list, max_length=20)
    caller: Caller
    guard_score: float | None = Field(default=None, ge=0, le=1)   # ML guard: may only add caution
    flags: list[str] = Field(default_factory=list, max_length=10)

    def typed_args(self) -> Strict:
        return ARGS_MODEL[self.tool].model_validate(self.args)


class ClaimResult(Strict):
    kind: ClaimKind
    ok: bool
    why: str
    tier: Literal["T0", "T1", "REQ"]
    source: Source = Source.tool


class Risk(Strict):
    amount_paise: int | None = None
    auto_limit_paise: int | None = None
    over_auto_limit: bool = False
    over_hard_cap: bool = False
    refunds_30d: int = 0
    guard_score: float | None = None
    flags: list[str] = Field(default_factory=list)


class VerdictOut(Strict):
    proposal_id: str
    verdict: Verdict
    reasons: list[str]
    results: list[ClaimResult]
    risk: Risk
    token: str | None = None          # only for ALLOW / APPROVED
    approval_id: int | None = None    # only for ESCALATE


class ExecuteIn(Strict):
    proposal_id: str
    tool: WriteTool
    args: dict[str, Any]
    token: str


class ExecuteOut(Strict):
    proposal_id: str
    status: Literal["executed", "already_executed", "refused"]
    reason: str | None = None
    result: dict[str, Any] | None = None


class Decision(Strict):
    decision: Literal["approve", "reject"]
    decided_via: Literal["console", "whatsapp", "telegram", "phone", "test"]
    edited_amount_paise: int | None = Field(default=None, gt=0, le=10_000_000)
    note: str = Field(default="", max_length=300)
