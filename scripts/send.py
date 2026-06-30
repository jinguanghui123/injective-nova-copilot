"""Send INJ on-chain via a signed bank MsgSend.

Safety:
  - Default mode is DRY-RUN — prints the planned tx without broadcasting.
  - Pass --broadcast to actually sign and submit.
  - Refuses to send > 1.0 INJ without --i-know-this-is-real-money.

Usage:
  uv run python scripts/send.py --to inj1... --amount 0.001
  uv run python scripts/send.py --to inj1... --amount 0.001 --broadcast
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from copilot.injective_client import InjectiveClient, inj_to_atomic, ensure_no_proxy_for_injective


MAX_SAFE_AMOUNT_INJ = 1.0  # without --i-know-this-is-real-money


async def main() -> None:
    parser = argparse.ArgumentParser(description="Sign and broadcast a bank MsgSend on Injective.")
    parser.add_argument("--to", required=True, help="Recipient bech32 address (inj1...)")
    parser.add_argument("--amount", required=True, type=float, help="Amount in INJ (e.g. 0.001)")
    parser.add_argument("--denom", default="inj", help="Asset denom (default: inj)")
    parser.add_argument("--broadcast", action="store_true", help="Actually sign and submit. Default is dry-run.")
    parser.add_argument(
        "--i-know-this-is-real-money",
        action="store_true",
        help=f"Required to send more than {MAX_SAFE_AMOUNT_INJ} INJ.",
    )
    args = parser.parse_args()

    load_dotenv(Path(".env"))
    pk = os.environ.get("INJECTIVE_PRIVATE_KEY")
    network = os.environ.get("INJECTIVE_NETWORK", "testnet")
    if not pk:
        raise SystemExit("INJECTIVE_PRIVATE_KEY not set. Copy .env.example to .env and fill it in.")

    if args.amount > MAX_SAFE_AMOUNT_INJ and not args.i_know_this_is_real_money:
        raise SystemExit(
            f"Refusing to send {args.amount} INJ (> {MAX_SAFE_AMOUNT_INJ}). "
            f"Re-run with --i-know-this-is-real-money if you mean it."
        )

    ensure_no_proxy_for_injective()
    client = InjectiveClient(private_key_hex=pk, network=network)
    amount_atomic = inj_to_atomic(args.amount)
    print(f"{client!r}")
    print(f"Planned tx: send {args.amount} {args.denom} ({amount_atomic} atomic) → {args.to}")
    print(f"Network:    {network}")

    if not args.broadcast:
        print("\n[DRY-RUN] Not broadcasting. Re-run with --broadcast to submit.")
        return

    print("\nBroadcasting...")
    try:
        receipt = await client.bank_send(to_address=args.to, amount_atomic=amount_atomic, denom=args.denom)
        print("\n--- Receipt ---")
        import json
        print(json.dumps(receipt, indent=2, default=str))
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
