"""The copilot agent: intent → plan → simulate → approve → execute.

The agent object is the composition root. It holds references to the LLM (intent
parser, week 2) and the Injective client (executor). Each of those is small and
testable on its own.

Week-1 state: schemas are frozen, the executor is wired for `send` (bank MsgSend),
the planner produces a real Plan for `send` intents, and other intents are stubbed.
LLM-backed parsing and the simulator land in week 2.
"""

from __future__ import annotations

from typing import Any

from rich.console import Console

from .injective_client import INJ_ATOMIC, InjectiveClient, inj_to_atomic
from .schema import Intent, IntentType, Plan, PlanStep

console = Console()


class Copilot:
    """Top-level orchestrator. Construct one per process / interactive session."""

    def __init__(self, *, client: InjectiveClient) -> None:
        self.client = client

    async def parse_intent(self, utterance: str) -> Intent:
        """Turn NL utterance into a validated Intent.

        Week-2 deliverable: prompt template → LLM → Pydantic validation.
        For now, a tiny regex recognizes `send <amount> INJ to <addr>` so the
        end-to-end pipeline is exercisable without an LLM.
        """
        import re

        m = re.match(
            r"^\s*send\s+([\d.]+)\s+(inj|INJ)\s+to\s+(inj1\w+)\s*$",
            utterance.strip(),
        )
        if m:
            from decimal import Decimal

            return Intent(
                type=IntentType.send,
                raw=utterance,
                asset_in="inj",
                amount=Decimal(m.group(1)),
                recipient=m.group(3),
            )
        return Intent(type=IntentType.unknown, raw=utterance, notes="parser could not match any known intent shape")

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
