"""Client wrapper around the official Injective MCP server.

The Injective agent-sdk is TypeScript-only and is for *identity registration*, not
trading. For trading we call the official `InjectiveLabs/mcp-server` over the MCP
protocol — language-agnostic, recommended in Injective's own docs.

This module is intentionally a thin wrapper: it owns the connection lifecycle and
exposes a small set of typed helpers. The planner and executor build on top of it.
"""

from __future__ import annotations

from typing import Any

from rich.console import Console

console = Console()


class MCPClient:
    """Thin async wrapper over the Injective MCP server.

    Connection strategy (in priority order):
      1. If `INJ_MCP_SERVER_URL` is set, connect over HTTP/SSE transport.
      2. Otherwise, spawn the local `mcp-server` binary as a subprocess (stdio transport).

    Real transport wiring lands in week 1 — see docs/roadmap.md. For now this is a
    typed placeholder so the planner can be built against a stable interface.
    """

    def __init__(self, *, server_url: str | None = None, network: str = "testnet") -> None:
        self.server_url = server_url
        self.network = network
        self._connected = False

    async def connect(self) -> None:
        # TODO(week 1): real transport — httpx-based MCP client or stdio subprocess.
        console.print(f"[dim]MCPClient.connect → {self.server_url or 'local subprocess'} ({self.network})[/dim]")
        self._connected = True

    async def list_tools(self) -> list[dict[str, Any]]:
        """Return the MCP server's declared tool surface."""
        # TODO(week 1): call `tools/list` on the MCP server.
        return []

    async def call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke a named MCP tool with structured arguments."""
        if not self._connected:
            await self.connect()
        # TODO(week 1): `tools/call` → real server.
        raise NotImplementedError(f"MCP tool call '{tool}' not wired yet — see docs/roadmap.md")

    async def close(self) -> None:
        self._connected = False
