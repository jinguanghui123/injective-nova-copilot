"""The copilot agent: intent → plan → simulate → approve → execute.

The agent object is the composition root. It holds references to the LLM (intent
parser), the planner, the simulator, the MCP client (executor), and the approval
gate. Each of those is a small, testable unit.

Week-1 scaffold: only the orchestration skeleton is in place. Real implementations
land per the roadmap.
"""

from __future__ import annotations

from rich.console import Console

from .mcp_client import MCPClient
from .schema import Intent, IntentType, Plan

console = Console()


class Copilot:
    """Top-level orchestrator. Construct one per process / interactive session."""

    def __init__(
        self,
        *,
        mcp: MCPClient,
        llm_provider: str = "ollama",
        llm_model: str = "qwen2.5:latest",
    ) -> None:
        self.mcp = mcp
        self.llm_provider = llm_provider
        self.llm_model = llm_model

    async def parse_intent(self, utterance: str) -> Intent:
        """Turn NL utterance into a validated Intent.

        Week-2 deliverable: prompt template → LLM → Pydantic validation.
        For now, returns an `unknown` intent so the pipeline type-checks end-to-end.
        """
        # TODO(week 2): real LLM-backed parse.
        return Intent(type=IntentType.unknown, raw=utterance, notes="parser not yet implemented")

    async def plan(self, intent: Intent) -> Plan:
        """Map an Intent to a list of Injective module calls.

        Week-2 deliverable: deterministic planner per IntentType.
        """
        # TODO(week 2): real planner.
        return Plan(intent=intent, steps=[], warnings=["planner not yet implemented"])

    async def simulate(self, plan: Plan) -> Plan:
        """Dry-run the plan via Injective node RPC; attach gas + price-impact estimates.

        Week-2/3 deliverable.
        """
        # TODO(week 2-3): simulator via INJ_RPC_URL.
        plan.warnings.append("simulator not yet implemented — estimates are null")
        return plan

    async def approve(self, plan: Plan) -> bool:
        """Render the plan in plain language and wait for user approval.

        Human-in-the-loop is non-negotiable. The copilot never auto-executes.
        """
        console.print("[bold]Proposed plan:[/bold]")
        console.print(plan.summary())
        # TODO(week 3): real interactive prompt (typer/rich) with explicit y/N.
        return False

    async def execute(self, plan: Plan) -> dict[str, object]:
        """Send the approved plan to the Injective MCP server for on-chain execution."""
        # TODO(week 3): self.mcp.call(...) per step.
        raise NotImplementedError("executor not yet wired — see docs/roadmap.md")

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
