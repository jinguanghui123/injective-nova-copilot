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
│               ┌───────────────┐                                  │
│               │  MCP Client   │                                  │
│               └───────┬───────┘                                  │
└───────────────────────┼──────────────────────────────────────────┘
                        │ MCP protocol (stdio / HTTP)
                        ▼
               ┌───────────────────┐
               │ InjectiveLabs/    │
               │ mcp-server (Node) │
               └────────┬──────────┘
                        │ Cosmos SDK tx
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

## Decision: MCP server vs native Python SDK

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **MCP server** (chosen) | Official, language-agnostic, supports both trading + identity tools, documented in Injective's AI dev docs | Adds a Node subprocess hop; one more process to manage | **Primary path.** Proven, low-risk for a 4-week hackathon. |
| `pyinjective` (native Python) | No subprocess, idiomatic Python | Existence on PyPI not verified at time of writing; if real, maturity unknown | **Fallback.** Verify in week 1; if usable, can replace MCP hop with zero changes to planner/intent layers. |
| `injective-agent-sdk` (TypeScript) | First-class ERC-8004 identity support | TypeScript-only; identity-only (no trading) | **Identity sidecar only.** One-shot CLI call in week 3. |

The boundary that makes this swappable: the planner and intent layers speak `Intent` / `Plan` / `PlanStep` (Pydantic), not MCP types. The `MCPClient` is the only module that knows about MCP; replacing it with a `PyInjectiveClient` of the same shape is a one-module change.

## Decision: human-in-the-loop is non-negotiable

The copilot **never** auto-executes a plan. Every plan goes through:

1. Simulation (dry-run against RPC).
2. Plain-language summary in the user's language.
3. Explicit `y/N` prompt.
4. Only then: execution.

There is no `--yes` flag and no auto-approval path. This is the product's core trust promise and the main reason a user would pick it over a raw wallet.

## Decision: local LLM by default

Default `LLM_PROVIDER=ollama` with `qwen2.5:latest`:

- Free, private, offline-capable.
- Sufficient quality for the 5 reference intents.
- Cloud (OpenAI / Anthropic) is an optional extra — opt-in via env, never mandatory.

This keeps the copilot runnable by anyone, on a laptop, without an API key — a real UX win for the demo.

## Trust boundaries

- **Secrets** (mnemonic, private keys, API JWTs) live only in `.env`, loaded via `python-dotenv`, never logged, never serialized into plans or receipts.
- **LLM output** is validated at the boundary by Pydantic — an LLM cannot produce a plan that bypasses the schema.
- **Execution** goes through the approval gate — no code path exists from intent to on-chain tx without a human `y`.
- **MCP server** is the only thing that talks to the chain — Python never signs directly, which limits the blast radius of any bug in the Python layer.
