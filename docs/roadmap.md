# Roadmap

Nova Program timeline: registration 2026-06-30 → demo day mid/late July 2026.
This file is the source of truth for what "done" means each week.

## Week 1 — Foundation (6/30 – 7/6)

**Goal:** the copilot can sign and broadcast one transaction on Injective testnet.

- [x] Verify `pyinjective` existence on PyPI. ✅ Confirmed: real package, v1.16.0 released 2026-06-29. Native Python path it is.
- [x] `injective-py` installed and importable. ✅ `pyinjective.async_client_v2.AsyncClient` + `MsgBroadcasterWithPk` work.
- [ ] Wallet on testnet, funded from the Injective faucet.
- [ ] First signed testnet tx — minimum-viable: bank `send` of 0.001 test-INJ.
- [x] `Intent` / `Plan` / `PlanStep` schemas frozen (Pydantic) — week-2 planner depends on these.
- [x] `.env` flow works: `uv run copilot plan "send 0.001 INJ to inj1..."` parses, plans, and prints the summary.
- [x] `scripts/send.py` provides a developer-facing escape hatch with dry-run-by-default and a `--broadcast` flag.

**Exit criterion:** a green test that builds an Intent, runs it through `plan()` → `simulate()`, and prints the summary. Plus: a real testnet bank-send tx hash captured from a funded wallet.

## Week 2 — Planner (7/7 – 7/13)

**Goal:** NL utterances for the five reference intents produce valid plans.

- [x] Prompt template (`src/copilot/prompts.py`) for intent parsing.
- [x] LLM integration (Ollama local by default via `src/copilot/llm.py`); `qwen2.5:latest` parses all 5 reference intents correctly.
- [x] LLM-first parser with regex fallback (`agent.parse_intent`); 7 live regression tests in `tests/test_parser_live.py`.
- [ ] Deterministic planner per IntentType: swap, send (✅), perp_open, perp_close, limit_order.
- [ ] Simulator: dry-run each PlanStep against Injective RPC, populate `estimated_gas_inj` and `estimated_price_impact_bps`.

**Exit criterion:** the five reference utterances produce five plans with non-null gas estimates.

## Week 3 — Execution + Identity (7/14 – 7/20)

**Goal:** approved plans execute on-chain; the copilot is a registered ERC-8004 agent.

- [ ] Approval gate: rich-based interactive prompt showing `plan.summary()`, explicit y/N, no auto-execute path.
- [ ] Executor: send each PlanStep to the MCP server, collect receipts, surface failures.
- [ ] Idempotency: re-running an approved plan is a no-op once the tx hash is known.
- [ ] ERC-8004 registration: one-shot TypeScript CLI call (agent-sdk) — pin agent card to IPFS via Pinata, mint soulbound NFT on IdentityRegistry.
- [ ] Move from testnet to mainnet behind a feature flag.

**Exit criterion:** end-to-end swap on testnet, signed off by the approval gate, with an on-chain tx hash.

## Week 4 — Polish + Demo (7/21 – 7/27)

**Goal:** demo-ready, English + Chinese UX, recorded walkthrough.

- [ ] Bilingual intent parsing (zh / en).
- [ ] Hardening: private keys never logged; `--dry-run` is the default.
- [ ] Demo script: 5 intents, 5 plans, 5 on-chain txs, recorded.
- [ ] README + architecture docs finalized.
- [ ] Submission package ready.

**Exit criterion:** a 3-minute demo video plus a clean repo a judge can `git clone && uv sync && uv run copilot plan ...` against.

---

## Stretch (post-demo)

- Voice intent (Whisper → intent parser).
- Multi-step strategies ("rebalance my portfolio weekly").
- Cross-chain intent via Injective's IBC paths.
- Published as a discoverable A2A agent on the Injective agent network.
