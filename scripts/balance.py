"""Query the testnet/mainnet balance of the configured wallet.

Usage: uv run python scripts/balance.py
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from copilot.injective_client import InjectiveClient, INJ_ATOMIC, ensure_no_proxy_for_injective


async def main() -> None:
    load_dotenv(Path(".env"))
    pk = os.environ.get("INJECTIVE_PRIVATE_KEY")
    network = os.environ.get("INJECTIVE_NETWORK", "testnet")
    if not pk:
        raise SystemExit("INJECTIVE_PRIVATE_KEY not set. Copy .env.example to .env and fill it in.")

    ensure_no_proxy_for_injective()
    client = InjectiveClient(private_key_hex=pk, network=network)
    print(f"{client!r}")
    try:
        atomic = await client.get_bank_balance("inj")
        print(f"Balance: {atomic / INJ_ATOMIC:.6f} INJ  ({atomic} atomic)")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
