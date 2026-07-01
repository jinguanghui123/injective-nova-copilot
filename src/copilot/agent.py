"""The copilot agent: intent → plan → simulate → approve → execute.

The agent object is the composition root. It holds references to the LLM
(intent parser), the Injective client (executor), and the approval gate.

Week-2 state: LLM-backed intent parser is wired (Ollama + qwen2.5 by default,
regex fallback when the LLM is unavailable). Planner produces a real Plan for
`send`; other intents return a typed `unknown`-ish Plan with a warning.
Simulator and approval gate land in weeks 2-3.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from rich.console import Console

from .injective_client import INJ_ATOMIC, InjectiveClient, inj_to_atomic
from .llm import LLMError, OllamaClient
from .prompts import INTENT_SYSTEM, INTENT_USER_TEMPLATE
from .schema import Intent, IntentType, Plan, PlanStep

console = Console()


def _llm_dict_to_intent(d: dict[str, Any], *, raw: str) -> Intent:
    """Coerce the LLM's JSON dict into a validated Intent.

    Anything that doesn't fit the schema degrades to IntentType.unknown rather
    than raising — the approval gate can then ask the user to rephrase.
    """
    type_str = str(d.get("type", "unknown")).lower().strip()
    try:
        type_ = IntentType(type_str)
    except ValueError:
        type_ = IntentType.unknown

    def _decimal(v: Any) -> Decimal | None:
        if v is None or v == "":
            return None
        try:
            return Decimal(str(v))
        except Exception:
            return None

    amount = _decimal(d.get("amount"))
    limit_price = _decimal(d.get("limit_price"))
    leverage_raw = d.get("leverage")
    leverage = int(leverage_raw) if leverage_raw not in (None, "") else None

    # Recipient sanity — must be a bech32 inj1 address.
    recipient = d.get("recipient")
    if recipient is not None and not str(recipient).startswith("inj1"):
        recipient = None  # don't trust the LLM here

    notes = d.get("notes")

    # If type is send but recipient is missing, downgrade to unknown.
    if type_ is IntentType.send and recipient is None:
        type_ = IntentType.unknown
        notes = (notes + " | " if notes else "") + "send intent missing valid inj1 recipient"

    return Intent(
        type=type_,
        raw=raw,
        asset_in=_opt_str(d.get("asset_in")),
        asset_out=_opt_str(d.get("asset_out")),
        amount=amount,
        recipient=recipient,
        limit_price=limit_price,
        leverage=leverage,
        notes=notes,
    )


def _opt_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


_SEND_REGEX = re.compile(r"^\s*send\s+([\d.]+)\s+(inj|INJ)\s+to\s+(inj1\w+)\s*$")


class Copilot:
    """Top-level orchestrator. Construct one per process / interactive session."""

    def __init__(
        self,
        *,
        client: InjectiveClient,
        llm: OllamaClient | None = None,
    ) -> None:
        self.client = client
        self.llm = llm

    async def parse_intent(self, utterance: str) -> Intent:
        """Turn NL utterance into a validated Intent.

        Path: LLM (Ollama) first; on any LLM failure, fall back to a tiny regex
        that only understands the `send <amount> INJ to <addr>` shape.
        """
        if self.llm is not None:
            try:
                result = await self.llm.chat_json(
                    system=INTENT_SYSTEM,
                    user=INTENT_USER_TEMPLATE.format(utterance=utterance),
                )
                return _llm_dict_to_intent(result, raw=utterance)
            except LLMError as exc:
                console.print(f"[dim]LLM unavailable ({str(exc)[:80]}); falling back to regex parser.[/dim]")

        # Regex fallback — only the `send` shape.
        m = _SEND_REGEX.match(utterance.strip())
        if m:
            return Intent(
                type=IntentType.send,
                raw=utterance,
                asset_in="inj",
                amount=Decimal(m.group(1)),
                recipient=m.group(3),
            )
        return Intent(
            type=IntentType.unknown,
            raw=utterance,
            notes="no LLM available and utterance did not match the regex fallback",
        )

    async def plan(self, intent: Intent) -> Plan:
        """Map an Intent to a list of Injective module calls."""
        if intent.type is IntentType.send:
            if intent.recipient is None or intent.amount is None:
                return Plan(intent=intent, steps=[], warnings=["send intent needs recipient and amount"])
            amount_atomic = inj_to_atomic(float(intent.amount))
            return Plan(
                intent=intent,
                steps=[
                    PlanStep(
                        module="bank",
                        action="MsgSend",
                        args={
                            "from_address": self.client.address,
                            "to_address": intent.recipient,
                            "amount_atomic": amount_atomic,
                            "denom": "inj",
                        },
                        human_readable=f"Bank-send {intent.amount} INJ → {intent.recipient}",
                    )
                ],
            )
        return Plan(
            intent=intent,
            steps=[],
            warnings=[f"planner for {intent.type.value} not yet implemented (week 2)"],
        )

    async def simulate(self, plan: Plan) -> Plan:
        """Dry-run the plan via Injective RPC; attach gas + price-impact estimates.

        Week-2/3 deliverable. For now we just query the signer balance as a sanity
        check and surface a warning if it's zero.
        """
        try:
            balance_atomic = await self.client.get_bank_balance("inj")
            plan.warnings.append(f"signer balance: {balance_atomic / INJ_ATOMIC:.6f} INJ")
            if balance_atomic == 0:
                plan.warnings.append("signer has 0 INJ — tx will fail. Fund from the testnet faucet.")
        except Exception as exc:
            plan.warnings.append(f"could not query signer balance: {exc!r}")
        return plan

    async def approve(self, plan: Plan) -> bool:
        """Render the plan in plain language and wait for user approval.

        Human-in-the-loop is non-negotiable. The copilot never auto-executes.
        """
        console.print("[bold]Proposed plan:[/bold]")
        console.print(plan.summary())
        # TODO(week 3): real interactive prompt (typer/rich) with explicit y/N.
        return False

    async def execute(self, plan: Plan) -> dict[str, Any]:
        """Send the approved plan to the Injective chain via pyinjective."""
        if not plan.steps:
            raise ValueError("cannot execute a plan with no steps")
        receipts: list[dict[str, Any]] = []
        for step in plan.steps:
            if step.module == "bank" and step.action == "MsgSend":
                receipt = await self.client.bank_send(
                    to_address=str(step.args["to_address"]),
                    amount_atomic=int(step.args["amount_atomic"]),
                    denom=str(step.args.get("denom", "inj")),
                )
                receipts.append(receipt)
            else:
                raise NotImplementedError(
                    f"executor for {step.module}.{step.action} not wired yet (week 2+)"
                )
        return {"receipts": receipts}

    async def handle(self, utterance: str) -> None:
        """End-to-end: parse → plan → simulate → approve → execute."""
        intent = await self.parse_intent(utterance)
        plan = await self.plan(intent)
        plan = await self.simulate(plan)
        if not await self.approve(plan):
            console.print("[yellow]Plan not approved. Aborting.[/yellow]")
            return
        receipt = await self.execute(plan)
        console.print(f"[green]Executed.[/green] {receipt}")
