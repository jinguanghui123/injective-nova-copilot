"""Smoke test: schemas import and behave, summary renders."""

from decimal import Decimal

from copilot.schema import Intent, IntentType, Plan, PlanStep


def test_intent_round_trips() -> None:
    intent = Intent(
        type=IntentType.swap,
        raw="Swap 100 USDT to INJ",
        asset_in="USDT",
        asset_out="INJ",
        amount=Decimal("100"),
    )
    assert intent.type is IntentType.swap
    assert intent.slippage_bps == 100  # default applied


def test_plan_summary_lists_steps() -> None:
    plan = Plan(
        intent=Intent(type=IntentType.swap, raw="Swap 100 USDT to INJ"),
        steps=[
            PlanStep(
                module="exchange",
                action="market_buy",
                args={"market_id": "inj-usdt", "quantity": "100"},
                human_readable="Market-buy 100 USDT worth of INJ on the inj-usdt order book",
            ),
        ],
        estimated_gas_inj=Decimal("0.0021"),
    )
    summary = plan.summary()
    assert "Swap" in summary
    assert "exchange" in summary
    assert "Market-buy" in summary
