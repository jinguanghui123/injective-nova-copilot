# Architecture

## Component map

```
┌──────────────────────────────────────────────────────────────────┐
│                          Nova Copilot                            │
│                                                                  │
│   CLI (typer) ──▶ Copilot (orchestrator)                         │
│                       │                                          │
│       ┌───────────────┼───────────────┬─────────────┐            │
│       ▼               ▼               ▼             ▼            │
│  Intent Parser    Planner        Simulator      Approval Gate    │
│  (LLM, Ollama)   (deterministic) (RPC dry-run) (human-in-loop)   │
│                       │                                          │
│                       ▼                                          │
│                   Executor                                       │
│                       │                                          │
│                       ▼                                          │
│           ┌────────────────────────┐                             │
│           │  InjectiveClient       │  ← only module that         │
│           │  (pyinjective wrapper) │     knows about pyinjective │
│           └───────────┬────────────┘                             │
└───────────────────────┼──────────────────────────────────────────┘
                        │ grpc (Cosmos SDK tx)
                        ▼
               ┌───────────────────┐
               │  Injective chain  │
               │ (testnet/mainnet) │
               └───────────────────┘

                 ─── sidecar (one-shot, week 3) ───
                ┌─────────────────────────────────┐
                │  injective-agent-sdk (TS CLI)   │ ──▶ ERC-8004
                │  PinataStorage → IPFS agent card│     registration
                └─────────────────────────────────┘
```

## Decision: native `injective-py` (chosen) vs MCP server vs TS agent-sdk

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **`injective-py`** (InjectiveLabs/sdk-python) | Official, native Python, v1.16 released 2026-06-29 (active), full module coverage (bank/exchange/perp/futures/wasm), no subprocess | Heavy proto-based deps (grpcio, protobuf, web3) | **Primary path.** Verified installable and importable on this box. |
| `InjectiveLabs/mcp-server` | Language-agnostic | Adds a Node subprocess hop; partial feature parity | **Dropped** for trading. Could be revisited if the copilot ever needs to expose its own tools to other agents. |
| `@injective/agent-sdk` (TypeScript) | First-class ERC-8004 identity support | TypeScript-only; identity-only (no trading) | **Identity sidecar only.** One-shot CLI call in week 3. |

The boundary that makes this swappable: the planner and intent layers speak `Intent` / `Plan` / `PlanStep` (Pydantic), not pyinjective types. `InjectiveClient` is the only module that knows about pyinjective; replacing it with another implementation of the same surface is a one-module change.

## Decision: human-in-the-loop is non-negotiable

The copilot **never** auto-executes a plan. Every plan goes through:

1. Simulation (dry-run against RPC — week 2).
2. Plain-language summary in the user's language.
3. Explicit `y/N` prompt.
4. Only then: execution.

There is no `--yes` flag on the agent and no auto-approval path. The standalone `scripts/send.py` does have `--broadcast` (because it's a developer-facing escape hatch), but it still refuses amounts > 1 INJ without an additional `--i-know-this-is-real-money` flag. This is the product's core trust promise.

## Decision: local LLM by default

Default `LLM_PROVIDER=ollama` with `qwen2.5:latest`:

- Free, private, offline-capable.
- Sufficient quality for the 5 reference intents.
- Cloud (OpenAI / Anthropic) is an optional extra — opt-in via env, never mandatory.

## Trust boundaries

- **Secrets** (`INJECTIVE_PRIVATE_KEY`, API JWTs) live only in `.env`, loaded via `python-dotenv`, never logged, never serialized into plans or receipts. `InjectiveClient.__repr__` redacts the key — it only prints the public address.
- **LLM output** is validated at the boundary by Pydantic — an LLM cannot produce a plan that bypasses the schema.
- **Execution** goes through the approval gate — no code path exists from intent to on-chain tx without a human `y`.
- **`InjectiveClient`** is the only thing that signs — the Python orchestration layer never sees the key bytes outside the client wrapper, which limits the blast radius of any bug elsewhere.

## Network notes (this box)

This Mac runs a global HTTP proxy at `127.0.0.1:5780` which intercepts httpx calls. To keep Injective grpc traffic out of the proxy, `ensure_no_proxy_for_injective()` sets `NO_PROXY` for `*.injective.network` and friends at startup. The CLI and scripts call it before connecting. If you see weird 502s from `localhost`-style URLs, that's the proxy — set `NO_PROXY` manually.
