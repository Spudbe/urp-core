# CLAUDE.md

## Project Overview

URP (Universal Reasoning Protocol) is a message protocol that lets autonomous agents make claims, attach proof references, and stake economic value on correctness — with other agents able to challenge or verify those claims. It defines the message shapes and interaction flow for structured claim accountability; it does not prescribe transport, identity, or proof format. The repo is at https://github.com/Spudbe/urp-core, current version 0.2.0 (public draft, v0.3 features built and tag pending).

## Architecture

The codebase has six layers:

**Message layer** — `urp/core.py` and `urp/message.py`. Defines all protocol data types as dataclasses with `to_dict()`/`from_dict()` serialisation. Core types: `Claim`, `ProofReference`, `Stake`, `Response`, `ToolReceipt`, `SettlementMessage`, `AgentCapability`. Enums: `ClaimType`, `Decision`, `SettlementOutcome`, `EvidenceStrength`, `NondeterminismClass`, `SideEffectClass`, `ReplayClass`, `ClaimKind`, `EvidenceType`. Supporting types: `AgentIdentity`, `StakePolicy`, `JWSSignature`. `URPMessage` wraps any payload in a versioned envelope.

**Agent layer** — `urp/agent.py`, `urp/knowledge_base.py`, and `urp/llm_agents.py`. Abstract `Agent` base class and reference implementations. `urp/llm_agents.py` contains `ResearcherLLM`, `ChallengerLLM`, `VerifierLLM` — the shared LLM-backed agent classes used by both `server.py` and simulations.

**Ledger layer** — `urp/ledger.py`. In-memory balance tracker for deposits, withdrawals, and settlement transfers between agents.

**Transport layer** — `urp/transport.py`. WebSocket server/client for networked multi-agent simulations. MCP and A2A transport adapters are specced but not implemented.

**LLM adapter layer** — `urp/llm.py`. Abstract `LLMAdapter` base class with three implementations: `GroqAdapter` (Groq API), `OllamaAdapter` (local models via Ollama, stdlib urllib), `OpenAIAdapter` (OpenAI API, stdlib urllib).

**Web server** — `server.py`. FastAPI server with SSE streaming endpoint (`/run-simulation`), heartbeat keep-alive for Railway proxy, custom claim input. Deployed at https://urp-core-production.up.railway.app.

## Current State

**All 13 GitHub issues closed.** 59 passing tests. Railway deployed and live.

**Protocol types (all complete with serialisation, specs, schemas, and tests):**
- `Claim` with `evidence: list[ToolReceipt]`
- `ProofReference` — citation pointer (hash + URI + summary)
- `Stake`, `Response`, `SettlementMessage`
- `ToolReceipt` — verifiable tool call record with 17 fields including SHA-256 hashes, replay/nondeterminism/side-effect classification, evidence strength
- `AgentCapability` — preflight declaration with `ClaimKind` routing, `EvidenceType` acceptance, `StakePolicy`, validation

**Enums:** `ClaimType`, `Decision`, `SettlementOutcome`, `EvidenceStrength`, `NondeterminismClass`, `SideEffectClass`, `ReplayClass`, `ClaimKind`, `EvidenceType`

**LLM adapters:** `GroqAdapter`, `OllamaAdapter`, `OpenAIAdapter`

**Simulations:**
- `simple_simulation.py` — single-process, no API key
- `llm_simulation.py` — three-scenario Groq-backed
- `ollama_demo.py` — local model demo
- `deterministic_demo.py` — replayable ToolReceipt verification, no LLM

**Infrastructure:** GitHub Actions CI, Railway Dockerfile deployment, SSE heartbeat

## Engineering Conventions

- Python 3.10+ required
- Dataclasses for all protocol types — no Pydantic, no attrs
- Type hints on all public interfaces
- Docstrings on all public classes and methods
- `pytest` for tests (`tests/` directory)
- No placeholder or stub logic — if a feature isn't implemented, it isn't in the code
- Spec and code must stay in sync — changes to protocol types require updating both SPEC.md/SPEC-v2.md and urp/core.py
- Each serialisable type has `to_dict()` and `from_dict()` class methods

## What Not To Touch

These files define the core protocol identity. Changes require updating both spec and code together:

- `urp/core.py` — protocol data types
- `SPEC.md` — v1 protocol specification
- `SPEC-v2.md` — v2 specification with JSON schemas

Do not modify these independently. A change to a field name in `core.py` must be reflected in the specs, and vice versa.

## How To Run

```bash
# Install dependencies
pip install -r requirements.txt

# Simple simulation (no API key needed)
python simulations/simple_simulation.py

# Deterministic verification demo (no API key needed)
python simulations/deterministic_demo.py

# LLM-backed simulation (requires Groq API key)
export GROQ_API_KEY=your_key_here
python simulations/llm_simulation.py

# Local model simulation (requires Ollama)
python simulations/ollama_demo.py

# Web interface (requires Groq API key)
export GROQ_API_KEY=your_key_here
python server.py
# Open http://localhost:8000
```

## Next Priorities

1. EvidenceBundle type — composite evidence grouping multiple ToolReceipts and signed attestations
2. Structured claim format — replace free-text statements with machine-parseable propositions
3. JWS signing implementation — implement the signing model stubbed in SPEC.md
4. Machine-native reasoning layer — binary-efficient message encoding for high-throughput agent communication

## Provider Notes

- `GroqAdapter` uses model `llama-3.3-70b-versatile` by default, reads `GROQ_API_KEY`
- `OllamaAdapter` uses model `llama3` by default, reads `OLLAMA_HOST` (defaults to localhost:11434), stdlib urllib
- `OpenAIAdapter` uses model `gpt-4o-mini` by default, reads `OPENAI_API_KEY`, stdlib urllib
- `LLMAdapter` is the abstract base — any new provider subclasses it and implements `complete(system_prompt, user_prompt) -> str`
- Proof location URIs use the format `llm://groq/{model_name}`, read dynamically from the adapter's `model` attribute

## Commit Style

Prefix commits with: `feat`, `fix`, `spec`, `docs`, `refactor`, `test`, `chore`. Use descriptive messages. One concern per commit.
