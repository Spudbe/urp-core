# Universal Reasoning Protocol (URP)

A protocol for structured claim exchange, verification, and settlement between autonomous agents.

> **Status: Protocol Draft v0.2 — not production code.**

## What URP Is

URP is a message protocol that lets agents make claims, attach proofs, and stake value on correctness. Other agents evaluate claims, challenge them, or accept them, and a settlement step redistributes stakes based on the outcome. The protocol defines the message shapes and interaction flow; it does not prescribe transport, identity, or proof format.

## Why It Exists

When one agent asks another for information, there is no built-in mechanism for the responding agent to demonstrate correctness or for the requesting agent to verify it. URP addresses this gap by requiring claims to carry proof references and stakes, making accuracy an economic commitment rather than a trust assumption.

## Core Concepts

- **Claim** — An atomic assertion or request, carrying a statement, a proof reference, and a stake.
- **ProofReference** — A pointer (hash + URI + summary) to external evidence backing a claim.
- **Stake** — A quantity of credits locked with a claim or challenge to signal confidence and fund verification.
- **Response** — A decision (`accept`, `reject`, or `challenge`) returned by an evaluating agent, optionally with its own proof and counter-stake.
- **Agent** — An autonomous participant that creates claims, evaluates others' claims, or verifies disputes. The reference implementation provides `ResearcherAgent`, `ChallengerAgent`, and `VerifierAgent`.
- **Ledger** — An in-memory balance tracker that records deposits, withdrawals, and settlement transfers between agents.

## How It Fits

Where MCP handles tool invocation and A2A handles agent discovery, URP handles claim accountability. An agent that retrieves data via MCP or delegates work via A2A can use URP to attach a verifiable proof and an economic stake to the result, giving downstream consumers a reason to trust or challenge it.

## Quick Start

Requires Python 3.10+. Install dependencies with `pip install -r requirements.txt`.

```bash
git clone https://github.com/Spudbe/urp-core.git
cd urp-core
python simulations/simple_simulation.py
```

Expected output (UUIDs and timestamps will differ):

```
=== Initial Balances ===
Researcher: 1.00 URC
Challenger: 1.00 URC
Verifier: 1.00 URC

Sending CLAIM message (compact):
{"protocol_version":"0.2.0","message_id":"...","timestamp":"...","sender":"Researcher","type":"claim","payload":{...}}

Received CLAIM message (pretty):
{
  "protocol_version": "0.2.0",
  ...
}

Sending CHALLENGE message:
{"protocol_version":"0.2.0",...,"decision":"accept",...}

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

An optional simulation replaces the hard-coded agents with LLM-backed agents that use the Groq API to generate real reasoning. Each agent (Researcher, Challenger, Verifier) calls Llama 3 via Groq to produce claims, evaluate evidence, and make decisions, exchanging full URPMessage envelopes throughout.

```bash
pip install groq
export GROQ_API_KEY=your_key_here
python simulations/llm_simulation.py
```

`GROQ_API_KEY` is required. The demo will not run without it. Get a free key at [console.groq.com](https://console.groq.com).

### Ollama (Local Models)

URP also works with local models via [Ollama](https://ollama.com). No API key needed.

```bash
# Install Ollama from https://ollama.com, then:
ollama pull llama3
python simulations/ollama_demo.py
```

Set `OLLAMA_HOST` if Ollama is not running on the default `http://localhost:11434`.

## Web Interface

A browser-based interface streams simulation progress in real time using Server-Sent Events. Three scenarios run back to back — easy claim, contested claim, and false claim — showing the full claim lifecycle with live balance updates.

```bash
pip install fastapi uvicorn
export GROQ_API_KEY=your_key_here
python server.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser and click **Run Simulation**.

## Repository Structure

```
urp-core/
├── SPEC.md                              # Protocol specification (v1 draft)
├── SPEC-v2.md                           # v2 specification with JSON schemas
├── README.md                            # This file
├── server.py                            # FastAPI server with SSE simulation endpoint
├── static/
│   └── index.html                       # Browser interface for live simulation
├── urp/
│   ├── __init__.py                      # Package init, exports __version__
│   ├── core.py                          # Data classes: Claim, ProofReference, Stake, Response
│   ├── agent.py                         # Agent ABC and reference implementations
│   ├── knowledge_base.py               # KnowledgeBase ABC, InMemoryKnowledgeBase, get_fact()
│   ├── ledger.py                        # In-memory balance ledger
│   ├── llm.py                           # LLM adapter interface and Groq implementation
│   ├── message.py                       # URPMessage envelope with protocol versioning
│   └── transport.py                     # WebSocket server/client for networked simulations
└── simulations/
    ├── simple_simulation.py             # Single-process claim/challenge/verify loop
    ├── llm_simulation.py                # Three-scenario LLM-backed simulation
    └── networked_simulation.py          # Multi-agent WebSocket simulation
```

## Specification

See [SPEC.md](SPEC.md) for the full protocol specification including message types, interaction flow, error codes, and signing model. [SPEC-v2.md](SPEC-v2.md) contains JSON schemas for all message types.

## Status and Roadmap

v0.2 is a public draft. The reference implementation covers the core message flow but does not yet include settlement messages, agent capability declarations, or transport adapters.

v0.3 will add:
- `SettlementMessage` type for explicit fund-transfer records
- Agent capability declarations so agents can advertise supported claim types
- MCP transport adapter for integration with tool-calling workflows

## License

BUSL-1.1. Change date: 2030-03-21. On the change date the license converts to Apache-2.0.
