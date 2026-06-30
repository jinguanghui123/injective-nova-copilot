"""Smoke tests: schemas, atomic-unit conversion, agent planner for `send`, InjectiveClient address derivation."""

from decimal import Decimal

import pytest

from copilot.injective_client import INJ_ATOMIC, InjectiveClient, inj_to_atomic
from copilot.schema import Intent, IntentType, Plan, PlanStep


# ─── Schema round-trips ──────────────────────────────────────────────

def test_intent_round_trips() -> None:
    intent = Intent(
        type=IntentType.send,
        raw="send 0.001 INJ to inj1hkhdaj2a2clmq5jq6mspsggqs32vynpk228q3r",
        asset_in="inj",
        amount=Decimal("0.001"),
        recipient="inj1hkhdaj2a2clmq5jq6mspsggqs32vynpk228q3r",
    )
    assert intent.type is IntentType.send
    assert intent.slippage_bps == 100  # default applied


def test_plan_summary_lists_steps() -> None:
    plan = Plan(
        intent=Intent(type=IntentType.send, raw="send 0.001 INJ to inj1..."),
        steps=[
            PlanStep(
                module="bank",
                action="MsgSend",
                args={"to_address": "inj1hkhdaj2a2clmq5jq6mspsggqs32vynpk228q3r", "amount_atomic": 10**15},
                human_readable="Bank-send 0.001 INJ → inj1hkhdaj2a2clmq5jq6mspsggqs32vynpk228q3r",
            ),
        ],
    )
    summary = plan.summary()
    assert "send" in summary
    assert "bank" in summary
    assert "Bank-send" in summary


# ─── Atomic-unit conversion ──────────────────────────────────────────

def test_inj_to_atomic() -> None:
    assert inj_to_atomic(1.0) == 10**18
    assert inj_to_atomic(0.001) == 10**15
    assert inj_to_atomic(2.5) == 25 * 10**17


def test_atomic_constant() -> None:
    assert INJ_ATOMIC == 10**18


# ─── InjectiveClient address derivation (no network) ────────────────

def test_injective_client_derives_address_from_known_key() -> None:
    """A fixed private key must deterministically produce a fixed address."""
    # 64 hex chars, no 0x prefix — the canonical form from pyinjective's to_hex().
    pk = "ab" * 32
    client = InjectiveClient(private_key_hex=pk, network="testnet")
    addr = client.address
    assert addr.startswith("inj1")
    assert len(addr) > 30
    # repr must never leak the private key
    assert "ab" * 32 not in repr(client)


def test_injective_client_strips_0x_prefix() -> None:
    """Users may paste keys with 0x prefix; the wrapper must accept both forms."""
    pk_plain = "cd" * 32
    pk_prefixed = "0x" + pk_plain
    c1 = InjectiveClient(private_key_hex=pk_plain, network="testnet")
    c2 = InjectiveClient(private_key_hex=pk_prefixed, network="testnet")
    assert c1.address == c2.address, "0x-prefixed key should derive the same address"


def test_injective_client_rejects_empty_key() -> None:
    with pytest.raises(ValueError, match="private_key_hex is required"):
        InjectiveClient(private_key_hex="")


# ─── Agent planner for `send` ────────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_plans_send_intent() -> None:
    """The agent should turn a `send` intent into a single bank MsgSend step.

    Uses a fake client — we only exercise the planner, which doesn't need
    network access as long as the client's `.address` property works.
    """
    from copilot.agent import Copilot

    class FakeClient:
        address = "inj1signer000000000000000000000000000000000"

    copilot = Copilot(client=FakeClient())  # type: ignore[arg-type]
    intent = Intent(
        type=IntentType.send,
        raw="send 0.001 INJ to inj1hkhdaj2a2clmq5jq6mspsggqs32vynpk228q3r",
        amount=Decimal("0.001"),
        recipient="inj1hkhdaj2a2clmq5jq6mspsggqs32vynpk228q3r",
    )
    plan = await copilot.plan(intent)
    assert len(plan.steps) == 1
    step = plan.steps[0]
    assert step.module == "bank"
    assert step.action == "MsgSend"
    assert step.args["amount_atomic"] == 10**15
    assert step.args["to_address"] == "inj1hkhdaj2a2clmq5jq6mspsggqs32vynpk228q3r"
    assert "0.001 INJ" in step.human_readable


@pytest.mark.asyncio
async def test_agent_parses_send_utterance() -> None:
    """The regex parser should recognize 'send <amt> INJ to <addr>'."""
    from copilot.agent import Copilot

    class FakeClient:
        address = "inj1signer000000000000000000000000000000000"

    copilot = Copilot(client=FakeClient())  # type: ignore[arg-type]
    intent = await copilot.parse_intent("send 0.001 INJ to inj1hkhdaj2a2clmq5jq6mspsggqs32vynpk228q3r")
    assert intent.type is IntentType.send
    assert intent.amount == Decimal("0.001")
    assert intent.recipient == "inj1hkhdaj2a2clmq5jq6mspsggqs32vynpk228q3r"


@pytest.mark.asyncio
async def test_agent_unknown_utterance_is_typed_unknown() -> None:
    from copilot.agent import Copilot

    class FakeClient:
        address = "inj1signer000000000000000000000000000000000"

    copilot = Copilot(client=FakeClient())  # type: ignore[arg-type]
    intent = await copilot.parse_intent("whats the weather in tokyo")
    assert intent.type is IntentType.unknown
