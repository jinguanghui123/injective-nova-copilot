# Nova Copilot

> Natural-language DeFi copilot for the Injective chain. Describe what you want in plain language; the copilot plans, simulates, and executes on-chain transactions — you stay in control of the keys.

Built for the **Injective Nova Program** (Injective × Microsoft × Web3Labs) — Direction: *AI × Real Application Scenarios*.

---

## The problem

Injective's module ecosystem (spot, perpetuals, futures, insurance, CosmWasm) is powerful but accessible only to users who already understand wallets, gas, order books, market IDs, and denomination strings. For everyone else, the learning curve *is* the moat. Real users don't want to learn any of it — they want to say "swap 100 USDT to INJ at the best price" and have it happen safely.

## The solution

Nova Copilot turns natural-language intent into a **planned, simulated, then executed** transaction bundle on Injective. The user reviews the plan in plain language before any signature happens. The copilot never holds keys.

```
"如果 INJ 跌破 25 就帮我做空 100 INJ 的永续"
        │
        ▼
  Intent Parser (LLM)
        │
        ▼
   Plan Graph          ── dry-run ──▶  Simulator (gas / slippage / price impact)
        │
        ▼
  Approval Gate (human-in-the-loop, plain-language review)
        │
        ▼
   Executor  ──▶  Injective MCP Server  ──▶  Injective chain
        │
        ▼
   On-chain receipt + ERC-8004 agent identity
```

Five reference intents the copilot will support by demo day:

| Intent | Example utterance |
|---|---|
| Spot swap | "Swap 100 USDT to INJ at the best price" |
| Send | "Send 5 INJ to vitalik.eth" |
| Perp open | "Open a 2x long on INJ perp, $1,000 margin" |
| Perp close | "Close my INJ perp position" |
| Limit order | "Limit-buy 50 INJ at 24 USDT, good-til-cancelled" |

## Why Injective

- **Fully on-chain order book** (not AMM) → execution is predictable, which makes plans sim-able.
- **Sub-second finality** → plans don't go stale between simulation and execution.
- **Rich module surface** (spot / perp / futures / wasm / insurance / bank) → real value to surface in natural language.
- **ERC-8004 agent identity** → first-class on-chain agent primitives; the copilot registers itself as a discoverable, verifiable agent.

## Architecture decisions

The original plan was to use `@injective/agent-sdk` for everything. Reading the actual SDK revealed it is **TypeScript-only** and is for **agent identity registration** (ERC-8004), *not* trading. So:

- **Execution path**: official [`InjectiveLabs/mcp-server`](https://github.com/InjectiveLabs/mcp-server) — language-agnostic, callable from Python over the MCP protocol. This is the recommended path in Injective's own docs.
- **Identity path** (optional, week 3): a one-shot TypeScript CLI call to register the copilot as an ERC-8004 agent. Output: on-chain agent ID + IPFS-pinned agent card.
- **Python integration**: see [`docs/architecture.md`](docs/architecture.md). If a native Python SDK (`pyinjective`) is verified on PyPI during week 1, it can replace the MCP server hop with no change to the planner/intent layers.

## Roadmap

4-week plan aligned to the Nova program timeline. See [`docs/roadmap.md`](docs/roadmap.md).

| Week | Focus | Deliverable |
|---|---|---|
| 1 (6/30–7/6) | Foundation | MCP server reachable from Python; first signed testnet tx; intent schema |
| 2 (7/7–7/13) | Planner | NL → structured intent; plan graph for 5 intents; simulator |
| 3 (7/14–7/20) | Execution + Identity | Approval-gate CLI; executor; ERC-8004 registration |
| 4 (7/21–7/27) | Polish + Demo | E2E flows; demo recording; docs |

## Setup

```bash
git clone https://github.com/jinguanghui123/injective-nova-copilot.git
cd injective-nova-copilot
uv sync
cp .env.example .env
# edit .env — fill in wallet mnemonic, network, optional API keys
uv run copilot --help
```

Requirements: Python ≥ 3.11, [uv](https://docs.astral.sh/uv/), an Injective-compatible wallet mnemonic (testnet funds from the [Injective faucet](https://testnet) for development).

## Status

Pre-alpha. Scaffolding committed; planner and execution layers land in weeks 1–3 per the roadmap.

## Evaluation alignment

Nova Copilot is designed against the Nova Program's evaluation criteria:

- **Innovation** — NL copilot on a fully on-chain order book chain, with ERC-8004 identity for on-chain agent discovery.
- **Technical Execution** — integrates Injective testnet (week 1) and mainnet (week 3+) via the official MCP server.
- **Use Case & Impact** — opens DeFi to non-technical users; same UX in English and Chinese.
- **Product & UX** — human-in-the-loop approval gate, plain-language plan review, never holds keys.
- **Ecosystem Fit** — uses Injective's modules (spot/perp/futures), order book (not AMM), and agent-identity standard.

## License

MIT. See [`LICENSE`](LICENSE).
