"""Live LLM parser regression tests.

These hit a running Ollama server, so they're skipped automatically if Ollama
isn't available (CI, fresh checkout, etc.). Run locally with `uv run pytest`.

The point: lock in the parser's behavior on the 5 reference intents plus two
known-unknown shapes. If a prompt or model change silently degrades parsing,
these fail and tell you which intent broke.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

import pytest
from dotenv import load_dotenv

from copilot.agent import Copilot

load_dotenv(Path(".env"))


def _ollama_up(host: str = "http://localhost:11434", timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


# Skip the whole module if Ollama isn't running.
pytestmark = pytest.mark.skipif(not _ollama_up(), reason="Ollama not running at localhost:11434")


class _FakeClient:
    address = "inj1signer000000000000000000000000000000000"


@pytest.fixture(scope="module")
def copilot() -> Copilot:
    from copilot.llm import OllamaClient

    return Copilot(client=_FakeClient(), llm=OllamaClient())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_parses_send(copilot: Copilot) -> None:
    i = await copilot.parse_intent("send 5 INJ to inj1hkhdaj2a2clmq5jq6mspsggqs32vynpk228q3r")
    from copilot.schema import IntentType

    assert i.type is IntentType.send
    assert i.amount == 5
    assert i.recipient == "inj1hkhdaj2a2clmq5jq6mspsggqs32vynpk228q3r"


@pytest.mark.asyncio
async def test_parses_swap(copilot: Copilot) -> None:
    from copilot.schema import IntentType

    i = await copilot.parse_intent("swap 100 USDT to INJ at best price")
    assert i.type is IntentType.swap
    assert i.asset_in == "USDT"
    assert i.asset_out == "INJ"
    assert i.amount == 100


@pytest.mark.asyncio
async def test_parses_perp_open(copilot: Copilot) -> None:
    from copilot.schema import IntentType

    i = await copilot.parse_intent("open a 2x long on INJ perp with 1000 USDT margin")
    assert i.type is IntentType.perp_open
    assert i.amount == 1000
    assert i.leverage == 2


@pytest.mark.asyncio
async def test_parses_perp_close(copilot: Copilot) -> None:
    from copilot.schema import IntentType

    i = await copilot.parse_intent("close my INJ perp position")
    assert i.type is IntentType.perp_close


@pytest.mark.asyncio
async def test_parses_limit_order(copilot: Copilot) -> None:
    from copilot.schema import IntentType

    i = await copilot.parse_intent("limit buy 50 INJ at 24 USDT")
    assert i.type is IntentType.limit_order
    assert i.amount == 50


@pytest.mark.asyncio
async def test_conditional_utterance_is_unknown(copilot: Copilot) -> None:
    """Chinese conditional trigger — out of scope, should classify as unknown."""
    from copilot.schema import IntentType

    i = await copilot.parse_intent("如果 INJ 跌破 25 就做空")
    assert i.type is IntentType.unknown


@pytest.mark.asyncio
async def test_off_topic_is_unknown(copilot: Copilot) -> None:
    from copilot.schema import IntentType

    i = await copilot.parse_intent("whats the weather in tokyo")
    assert i.type is IntentType.unknown


@pytest.mark.asyncio
async def test_send_with_bad_recipient_downgrades_to_unknown(copilot: Copilot) -> None:
    """A recipient that isn't inj1... should not produce a valid send intent."""
    from copilot.schema import IntentType

    i = await copilot.parse_intent("send 5 INJ to 0xdeadbeef")
    # Either the LLM already returns unknown, or our validator downgrades it.
    assert i.type is not IntentType.send
