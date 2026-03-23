# TRP — Tool Receipt Protocol

**Status: v0.5 — Apache-2.0 licensed**

TRP is an open protocol for verifiable tool call accountability between AI agents. Every tool call produces a signed, hash-verified receipt. Claims are structured propositions mechanically matched to receipt evidence. Settlement redistributes stakes when evidence is challenged.

## What TRP Is

TRP is a message protocol that lets agents make claims, attach proofs, and stake value on correctness. Other agents evaluate claims, challenge them, or accept them, and a settlement step redistributes stakes based on the outcome. The protocol defines the message shapes and interaction flow; it does not prescribe transport, identity, or proof format.

## Why It Exists

When one agent asks another for information, there is no built-in mechanism for the responding agent to demonstrate correctness or for the requesting agent to verify it. TRP addresses this gap by requiring claims to carry proof references and stakes, making accuracy an economic commitment rather than a trust assumption.

## Core Concepts

- **Claim** — An atomic assertion or request, carrying a statement, a proof reference, and a stake.
- **ProofReference** — A pointer (hash + URI + summary) to external evidence backing a claim.
- **Stake** — A quantity of credits locked with a claim or challenge to signal confidence and fund verification.
- **Response** — A decision (`accept`, `reject`, or `challenge`) returned by an evaluating agent, optionally with its own proof and counter-stake.
- **Agent** — An autonomous participant that creates claims, evaluates others' claims, or verifies disputes. The reference implementation provides `ResearcherAgent`, `ChallengerAgent`, and `VerifierAgent`.
- **Ledger** — An in-memory balance tracker that records deposits, withdrawals, and settlement transfers between agents.

## How It Fits

Where MCP handles tool invocation and A2A handles agent discovery, TRP handles claim accountability. An agent that retrieves data via MCP or delegates work via A2A can use TRP to attach a verifiable proof and an economic stake to the result, giving downstream consumers a reason to trust or challenge it.

## Quick Start

Requires Python 3.10+. Install dependencies with `pip install -r requirements.txt`.

```bash
git clone https://github.com/Spudbe/trp-core.git
cd trp-core
python simulations/simple_simulation.py
```

Expected output (UUIDs and timestamps will differ):

```
=== Initial Balances ===
Researcher: 1.00 URC
Challenger: 1.00 URC
Verifier: 1.00 URC

Sending CLAIM message (compact):
{"protocol_version":"0.3.0","message_id":"...","timestamp":"...","sender":"Researcher","type":"claim","payload":{...}}

Received CLAIM message (pretty):
{
  "protocol_version": "0.3.0",
  ...
}

Sending CHALLENGE message:
{"protocol_version":"0.3.0",...,"decision":"accept",...}

Sending VERIFICATION message:
{
  ...
  "decision": "reject",
  ...
}

Claim rejected; Researcher's stake is burnt.

=== Final Balances ===
Researcher: 0.90 URC
Challenger: 1.00 URC
Verifier: 1.00 URC
```

## LLM-Backed Demo

An optional simulation replaces the hard-coded agents with LLM-backed agents that use the Groq API to generate real reasoning. Each agent (Researcher, Challenger, Verifier) calls Llama 3 via Groq to produce claims, evaluate evidence, and make decisions, exchanging full TRPMessage envelopes throughout.

```bash
pip install groq
export GROQ_API_KEY=your_key_here
python simulations/llm_simulation.py
```

`GROQ_API_KEY` is required. The demo will not run without it. Get a free key at [console.groq.com](https://console.groq.com).

## Deterministic Verification Demo

This demo shows a claim backed by a genuinely replayable ToolReceipt — no LLM, no API key, no trust required. A pure function (`compute_fibonacci`) is called, its inputs and outputs are recorded in a ToolReceipt with SHA-256 hashes, and a verifier re-runs the function to confirm the output matches. Tampering with the receipt is detected because the replayed output hash does not match.

```bash
python simulations/deterministic_demo.py
```

This demonstrates the evidence-first principle: claims that can be verified by replay, not by asking another LLM.

### Ollama (Local Models)

TRP also works with local models via [Ollama](https://ollama.com). No API key needed.

```bash
# Install Ollama from https://ollama.com, then:
ollama pull llama3
python simulations/ollama_demo.py
```

Set `OLLAMA_HOST` if Ollama is not running on the default `http://localhost:11434`.

### OpenAI

TRP works with OpenAI models. The adapter uses `urllib` (stdlib) — the `openai` package is not required.

```bash
export OPENAI_API_KEY=your_key_here
```

To use OpenAI instead of Groq, replace `GroqAdapter()` with `OpenAIAdapter()` in any simulation script:

```python
from trp.llm import OpenAIAdapter
llm = OpenAIAdapter()  # defaults to gpt-4o-mini
```

## Web Interface

**Live demo:** [https://trp-core-production.up.railway.app](https://trp-core-production.up.railway.app)

A browser-based interface streams simulation progress in real time using Server-Sent Events. Three scenarios run back to back — easy claim, contested claim, and false claim — showing the full claim lifecycle with live balance updates.

```bash
pip install fastapi uvicorn
export GROQ_API_KEY=your_key_here
python server.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser and click **Run Simulation**.

## Deploy your own

**Live demo:** [https://trp-core-production.up.railway.app](https://trp-core-production.up.railway.app)

### Manual deploy on Railway

1. Fork this repository.
2. In Railway, create a new project and choose Deploy from GitHub repo.
3. Select your fork of trp-core.
4. Add the required environment variable: `GROQ_API_KEY`
5. Deploy the service.
6. After deploy succeeds, open Settings → Networking and generate a public domain.

**Required environment variable:** `GROQ_API_KEY` is required for the LLM-backed simulation. Create a key at [console.groq.com/keys](https://console.groq.com/keys). If `GROQ_API_KEY` is missing, `/run-simulation` will return a streamed error event instead of crashing.

**Local equivalent:**

```bash
export GROQ_API_KEY=your_key_here
uvicorn server:app --host 0.0.0.0 --port 8000
```

## Repository Structure

```
trp-core/
├── SPEC.md                              # Protocol specification (v1 draft)
├── SPEC-v2.md                           # v2 specification with JSON schemas
├── README.md                            # This file
├── server.py                            # FastAPI server with SSE simulation endpoint
├── static/
│   └── index.html                       # Browser interface for live simulation
├── trp/
│   ├── __init__.py                      # Package init, exports __version__
│   ├── core.py                          # Data classes: Claim, ProofReference, Stake, Response
│   ├── agent.py                         # Agent ABC and reference implementations
│   ├── knowledge_base.py               # KnowledgeBase ABC, InMemoryKnowledgeBase, get_fact()
│   ├── ledger.py                        # In-memory balance ledger
│   ├── llm.py                           # LLM adapter interface and Groq implementation
│   ├── message.py                       # TRPMessage envelope with protocol versioning
│   └── transport.py                     # WebSocket server/client for networked simulations
└── simulations/
    ├── simple_simulation.py             # Single-process claim/challenge/verify loop
    ├── llm_simulation.py                # Three-scenario LLM-backed simulation
    └── networked_simulation.py          # Multi-agent WebSocket simulation
```

## Specification

See [SPEC.md](SPEC.md) for the full protocol specification including message types, interaction flow, error codes, and signing model. [SPEC-v2.md](SPEC-v2.md) contains JSON schemas for all message types.

## Status and Roadmap

v0.3 is the current release. It adds ToolReceipt (the first mechanically verifiable evidence type), SettlementMessage, AgentCapability declarations, deterministic verification, Ollama and OpenAI adapters, and centralised LLM agent logic. See [CHANGELOG.md](CHANGELOG.md) for full details.

v0.4 will add:
- `ToolReceiptVerifier` engine with deterministic tool registry
- Deterministic verification scenario in the live web demo
- SettlementMessage streaming as first-class TRPMessage events
- MCP transport adapter for tool-calling workflows

## License

Apache-2.0. See [LICENSE](LICENSE).
