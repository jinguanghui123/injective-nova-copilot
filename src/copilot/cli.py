"""Command-line entry point. `copilot` on the terminal."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console

from .agent import Copilot
from .mcp_client import MCPClient

app = typer.Typer(
    name="copilot",
    help="Nova Copilot — natural-language DeFi on the Injective chain.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def chat() -> None:
    """Start an interactive chat session (week 3)."""
    console.print("[bold green]Nova Copilot[/bold green] [dim]v0.0.1 — pre-alpha[/dim]")
    console.print("Interactive chat lands in week 3. See docs/roadmap.md.")
    raise typer.Exit(code=0)


@app.command()
def plan(
    intent: str = typer.Argument(..., help="Natural-language intent, e.g. \"Swap 100 USDT to INJ\""),
) -> None:
    """Plan (but do not execute) a transaction from a natural-language intent."""
    load_dotenv(Path(".env"))
    copilot = Copilot(mcp=MCPClient(network="testnet"))
    result = asyncio.run(_plan(copilot, intent))
    console.print(result.summary())


async def _plan(copilot: Copilot, utterance: str):
    intent = await copilot.parse_intent(utterance)
    plan_obj = await copilot.plan(intent)
    return await copilot.simulate(plan_obj)


if __name__ == "__main__":
    app()
