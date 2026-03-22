# CLAUDE.md

## Project Overview

URP (Universal Reasoning Protocol) is a message protocol that lets autonomous agents make claims, attach proof references, and stake economic value on correctness — with other agents able to challenge or verify those claims. It defines the message shapes and interaction flow for structured claim accountability; it does not prescribe transport, identity, or proof format. The repo is at https://github.com/Spudbe/urp-core, current version 0.3.0 (v0.4 features complete).

## Architecture

The codebase has eight layers:

**Message layer** — `urp/core.py` and `urp/message.py`. Defines all protocol data types as dataclasses with `to_dict()`/`from_dict()` serialisation. Core types: `Claim`, `ProofReference`, `Stake`, `Response`, `ToolReceipt`, `SettlementMessage`, `AgentCapability`. Enums: `ClaimType`, `Decision`, `SettlementOutcome`, `EvidenceStrength`, `NondeterminismClass`, `SideEffectClass`, `ReplayClass`, `ClaimKind`, `EvidenceType`. Supporting types: `AgentIdentity`, `StakePolicy`, `JWSSignature`. `URPMessage` wraps any payload in a versioned envelope.

**Verification layer** — `urp/verify.py` and `urp/deterministic_tools.py`. `ToolReceiptVerifier` is a registry-based engine that validates classification consistency, replays deterministic tools, and compares output hashes. 7 verification statuses. 6 classification validation rules. `verify_claim()` for batch verification over a Claim's full evidence list. 4 built-in pure functions (fibonacci, factorial, sha256, math_eval).

**Signing layer** — `urp/signing.py`. Ed25519 JWS signing via jwcrypto. Key generation, detached JWS signatures, receipt signing with evidence strength auto-escalation (UNSIGNED → CALLER_SIGNED → DUAL_SIGNED), message envelope signing. Canonical JSON via sorted keys + compact separators.

**MCP adapter layer** — `urp/mcp_adapter.py`. `wrap_tool_call()` creates ToolReceipts from tool invocations. `wrap_mcp_tool_result()` builds MCP CallToolResult dicts with receipts in `_meta["urp:tool_receipt"]`. `extract_tool_receipt()` recovers receipts on the client side. End-to-end: wrap → extract → verify.

**Agent layer** — `urp/agent.py`, `urp/knowledge_base.py`, and `urp/llm_agents.py`. Abstract `Agent` base class and reference implementations. `urp/llm_agents.py` contains `ResearcherLLM`, `ChallengerLLM`, `VerifierLLM` — the shared LLM-backed agent classes used by both `server.py` and simulations.

**Ledger layer** — `urp/ledger.py`. In-memory balance tracker for deposits, withdrawals, and settlement transfers between agents.

**Transport layer** — `urp/transport.py`. WebSocket server/client for networked multi-agent simulations.

**LLM adapter layer** — `urp/llm.py`. Abstract `LLMAdapter` base class with three implementations: `GroqAdapter` (Groq API), `OllamaAdapter` (local models via Ollama, stdlib urllib), `OpenAIAdapter` (OpenAI API, stdlib urllib).

**Web server** — `server.py`. FastAPI server with SSE streaming. Endpoints: `/run-simulation` (LLM-backed, requires GROQ_API_KEY), `/run-deterministic` (no API key, 2 scenarios: verified + tampered), `/.well-known/urp-capability.json` (AgentCapability discovery), `/debug-env` (gated behind DEBUG=true). Rate limiting (5 concurrent), max claim length (2000 chars). Deployed at https://urp-core-production.up.railway.app.

## Current State

**196 passing tests. v0.3.0 tagged. v0.4 features complete. Railway deployed and live.**

**v0.3 (released):** ToolReceipt, SettlementMessage, AgentCapability, classification enums, deterministic verification demo, Ollama/OpenAI adapters, centralised LLM agents, security hardening.

**v0.4 (implemented, not yet tagged):** ToolReceiptVerifier with batch verification, JWS signing (Ed25519), MCP adapter (wrap/extract/verify), capability discovery endpoint, hash test vectors, 6 classification validation rules.

## Engineering Conventions

- Python 3.10+ required
- Dataclasses for all protocol types — no Pydantic, no attrs
- Type hints on all public interfaces
- Docstrings on all public classes and methods
- `pytest` for tests (`tests/` directory)
- No placeholder or stub logic — if a feature isn't implemented, it isn't in the code
- Spec and code must stay in sync — changes to protocol types require updating both SPEC.md/SPEC-v2.md and urp/core.py
- Each serialisable type has `to_dict()` and `from_dict()` class methods
- Pure functions preferred — signing and verification return new objects, not mutations

## What Not To Touch

These files define the core protocol identity. Changes require updating both spec and code together:

- `urp/core.py` — protocol data types
- `SPEC.md` — v1 protocol specification
- `SPEC-v2.md` — v2 specification with JSON schemas

Do not modify these independently.

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

# Web interface (requires Groq API key for LLM demo)
export GROQ_API_KEY=your_key_here
python server.py
# Open http://localhost:8000
# Deterministic demo works without API key
```

## Next Priorities

1. Structured claim format — replace free-text statements with machine-parseable propositions (v0.5)
2. A2A adapter — map AgentCapability to/from A2A agent cards
3. RFC 8785 (JCS) canonicalization alignment
4. EvidenceBundle — composite evidence type

## Provider Notes

- `GroqAdapter` uses model `llama-3.3-70b-versatile` by default, reads `GROQ_API_KEY`
- `OllamaAdapter` uses model `llama3` by default, reads `OLLAMA_HOST` (defaults to localhost:11434), stdlib urllib
- `OpenAIAdapter` uses model `gpt-4o-mini` by default, reads `OPENAI_API_KEY`, stdlib urllib
- `LLMAdapter` is the abstract base — any new provider subclasses it and implements `complete(system_prompt, user_prompt) -> str`

## Dependencies

- `websockets>=12.0` — networked simulations
- `groq>=0.4.0` — Groq LLM adapter
- `jwcrypto>=1.5.6` — Ed25519 JWS signing
- `fastapi>=0.115.0` + `uvicorn>=0.30.0` — web server (optional)
- `httpx>=0.27.0` — test client for FastAPI tests

## Commit Style

Prefix commits with: `feat`, `fix`, `spec`, `docs`, `refactor`, `test`, `chore`. Use descriptive messages. One concern per commit.
