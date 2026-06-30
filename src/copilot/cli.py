"""Command-line entry point. `copilot` on the terminal."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console

from .agent import Copilot
from .injective_client import INJ_ATOMIC, InjectiveClient, ensure_no_proxy_for_injective

app = typer.Typer(
    name="copilot",
    help="Nova Copilot — natural-language DeFi on the Injective chain.",
    no_args_is_help=True,
)
console = Console()


def _load_client() -> InjectiveClient:
    load_dotenv(Path(".env"))
    pk = os.environ.get("INJECTIVE_PRIVATE_KEY")
    network = os.environ.get("INJECTIVE_NETWORK", "testnet")
    if not pk:
        raise typer.BadParameter(
            "INJECTIVE_PRIVATE_KEY not set. Copy .env.example to .env and fill it in."
        )
    ensure_no_proxy_for_injective()
    return InjectiveClient(private_key_hex=pk, network=network)


@app.command()
def chat() -> None:
    """Start an interactive chat session (week 3)."""
    console.print("[bold green]Nova Copilot[/bold green] [dim]v0.0.1 — pre-alpha[/dim]")
    console.print("Interactive chat lands in week 3. See docs/roadmap.md.")
    raise typer.Exit(code=0)


@app.command()
def plan(
    intent: str = typer.Argument(..., help='Natural-language intent, e.g. "send 0.001 INJ to inj1..."'),
) -> None:
    """Plan (but do not execute) a transaction from a natural-language intent."""
    client = _load_client()
    copilot = Copilot(client=client)

    async def run() -> None:
        try:
            i = await copilot.parse_intent(intent)
            p = await copilot.plan(i)
            p = await copilot.simulate(p)
            console.print(p.summary())
        finally:
            await client.close()

    asyncio.run(run())


@app.command()
def balance() -> None:
    """Print the configured wallet's INJ balance."""

    async def run() -> None:
        client = _load_client()
        console.print(f"{client!r}")
        try:
            atomic = await client.get_bank_balance("inj")
            console.print(f"Balance: {atomic / INJ_ATOMIC:.6f} INJ  [dim]({atomic} atomic)[/dim]")
        finally:
            await client.close()

    asyncio.run(run())


if __name__ == "__main__":
    app()
