"""Structured schemas for natural-language intent and execution plans.

The flow is: NL utterance → Intent → Plan (list of PlanStep) → simulated → approved → executed.

Keeping these as Pydantic models means the LLM's output is validated at the boundary,
the simulator can branch on `IntentType`, and the approval gate can render a plan
in plain language without leaking raw transaction bytes.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """The set of intents the copilot can plan for.

    `unknown` is intentional: an unparseable utterance should produce a typed
    `unknown` intent rather than raise — the approval gate can then ask for
    clarification.
    """

    swap = "swap"
    send = "send"
    perp_open = "perp_open"
    perp_close = "perp_close"
    limit_order = "limit_order"
    unknown = "unknown"


InjectiveModule = Literal["bank", "exchange", "perpetuals", "futures", "wasm", "insurance"]


class Intent(BaseModel):
    """A parsed natural-language intent.

    `raw` is preserved so the approval gate can echo what the user said back at them,
    in their own words, before they sign anything.
    """

    type: IntentType
    raw: str
    asset_in: str | None = None
    asset_out: str | None = None
    amount: Decimal | None = None
    recipient: str | None = None
    limit_price: Decimal | None = None
    leverage: int | None = None
    slippage_bps: int = Field(default=100, ge=0, le=10_000)  # 1% default
    notes: str | None = None


class PlanStep(BaseModel):
    """A single Injective module call inside a plan."""

    module: InjectiveModule
    action: str
    args: dict[str, object] = Field(default_factory=dict)
    human_readable: str  # shown in the approval gate


class Plan(BaseModel):
    """A fully-formed execution plan ready for simulation and approval."""

    intent: Intent
    steps: list[PlanStep]
    estimated_gas_inj: Decimal | None = None
    estimated_price_impact_bps: int | None = None
    warnings: list[str] = Field(default_factory=list)

    def summary(self) -> str:
        """Plain-language summary for the approval gate."""
        lines = [f"Intent: {self.intent.type.value} — \"{self.intent.raw}\""]
        for i, step in enumerate(self.steps, 1):
            lines.append(f"  {i}. [{step.module}] {step.human_readable}")
        if self.warnings:
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  ! {w}")
        return "\n".join(lines)
