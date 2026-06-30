"""Native Python client for the Injective chain.

This replaces the earlier MCP-server wrapper. With `injective-py` (InjectiveLabs'
official Python SDK, v1.16) we can sign and broadcast directly — no Node subprocess,
no extra hop. The boundary stays clean: this is the only module that knows about
pyinjective, so swapping implementations later would only touch this file.

Security: the private key is held in memory only, never logged, never serialized
into a Plan or receipt. `__repr__` redacts it.
"""

from __future__ import annotations

import os
from typing import Any

from pyinjective.async_client_v2 import AsyncClient
from pyinjective.core.broadcaster import MsgBroadcasterWithPk
from pyinjective.core.network import Network
from pyinjective.wallet import PrivateKey

# 1 INJ = 1e18 atomic units (atoshi-style, like wei for ETH).
INJ_ATOMIC = 10**18


def inj_to_atomic(amount_inj: float) -> int:
    """Convert human-readable INJ (e.g. 1.5) to atomic units (1500000000000000000)."""
    return int(amount_inj * INJ_ATOMIC)


class InjectiveClient:
    """Thin async wrapper around pyinjective's V2 AsyncClient + MsgBroadcaster.

    Usage:
        client = InjectiveClient(private_key_hex=os.environ["INJECTIVE_PRIVATE_KEY"])
        await client.connect()
        print(await client.get_bank_balance("inj"))
        receipt = await client.bank_send(to_address="inj...", amount_atomic=inj_to_atomic(1))
        await client.close()
    """

    def __init__(self, *, private_key_hex: str, network: str = "testnet") -> None:
        if not private_key_hex:
            raise ValueError("private_key_hex is required — never log this value")
        # pyinjective's from_hex rejects the 0x prefix; be tolerant so users
        # can paste either form into .env.
        key = private_key_hex.strip()
        if key.startswith(("0x", "0X")):
            key = key[2:]
        self._private_key_hex = key
        self.network = Network.testnet() if network == "testnet" else Network.mainnet()
        self._client: AsyncClient | None = None
        self._composer: Any = None
        self._broadcaster: MsgBroadcasterWithPk | None = None

    @property
    def address(self) -> str:
        """The signer's bech32 address (inj1...), derived from the private key."""
        priv_key = PrivateKey.from_hex(self._private_key_hex)
        return priv_key.to_public_key().to_address().to_acc_bech32()

    def __repr__(self) -> str:
        # Never include the key. Address is fine — it's public on-chain anyway.
        return f"InjectiveClient(address={self.address!r}, network={self.network!r})"

    async def connect(self) -> None:
        """Initialize the grpc client, composer, and broadcaster."""
        self._client = AsyncClient(self.network)
        self._composer = await self._client.composer()
        gas_price = await self._client.current_chain_gas_price()
        # 1.1x buffer so the tx stays valid even if gas ticks up between
        # query and broadcast (per sdk-python/examples/chain_client/bank/1_MsgSend.py).
        gas_price = int(gas_price * 1.1)
        self._broadcaster = MsgBroadcasterWithPk.new_using_gas_heuristics(
            network=self.network,
            private_key=self._private_key_hex,
            gas_price=gas_price,
            client=self._client,
            composer=self._composer,
        )

    async def bank_send(self, *, to_address: str, amount_atomic: int, denom: str = "inj") -> dict[str, Any]:
        """Broadcast a Cosmos-SDK bank MsgSend.

        Args:
            to_address: bech32 recipient (inj1...)
            amount_atomic: amount in atomic units. Use `inj_to_atomic(1.5)` for 1.5 INJ.
            denom: asset denom, defaults to "inj".

        Returns:
            The broadcaster's raw result dict (contains tx hash, gas used, etc.).
        """
        if self._composer is None or self._broadcaster is None:
            await self.connect()
        assert self._composer is not None and self._broadcaster is not None  # for mypy
        msg = self._composer.msg_send(
            from_address=self.address,
            to_address=to_address,
            amount=amount_atomic,
            denom=denom,
        )
        return await self._broadcaster.broadcast([msg])

    async def get_bank_balance(self, denom: str = "inj") -> int:
        """Return the signer's atomic balance for `denom`."""
        if self._client is None:
            await self.connect()
        assert self._client is not None
        result = await self._client.fetch_bank_balance(address=self.address, denom=denom)
        # pyinjective returns balance in atomic units; shape varies by version — handle both.
        if isinstance(result, dict):
            return int(result.get("amount", 0))
        return int(getattr(result, "amount", 0))

    async def close(self) -> None:
        """Release the underlying grpc channel."""
        if self._client is not None:
            try:
                await self._client.close()
            except AttributeError:
                pass  # older versions may not expose close()
            self._client = None


def ensure_no_proxy_for_injective() -> None:
    """Set NO_PROXY so Injective RPC hosts don't go through the local system proxy.

    This box runs a global HTTP proxy at 127.0.0.1:5780 which intercepts httpx
    calls and breaks grpc. Call this once at startup before connecting the client.
    Idempotent — preserves any user-set NO_PROXY.
    """
    existing = os.environ.get("NO_PROXY", "")
    hosts = "*.injective.network,*.injective.dev,*.injective.com,sentry*.injective.network"
    if "injective" not in existing.lower():
        os.environ["NO_PROXY"] = f"{existing},{hosts}".lstrip(",") if existing else hosts
