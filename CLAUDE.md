# CLAUDE.md

## Project Overview

TRP (Tool Receipt Protocol) is a message protocol that lets autonomous agents make claims, attach proof references, and stake economic value on correctness — with other agents able to challenge or verify those claims. It defines the message shapes and interaction flow for structured claim accountability; it does not prescribe transport, identity, or proof format. The repo is at https://github.com/Spudbe/trp-core, current version 0.3.0 (v0.5 features complete).

## Architecture

The codebase has ten layers:

**Message layer** — `trp/core.py` and `trp/message.py`. All protocol data types as dataclasses with `to_dict()`/`from_dict()`. Core types: `Claim` (with optional `structured_claim` field), `ProofReference`, `Stake`, `Response`, `ToolReceipt`, `SettlementMessage`, `AgentCapability`. Enums: `ClaimType`, `Decision`, `SettlementOutcome`, `EvidenceStrength`, `NondeterminismClass`, `SideEffectClass`, `ReplayClass`, `ClaimKind`, `EvidenceType`. Supporting types: `AgentIdentity`, `StakePolicy`, `JWSSignature`.

**Structured claims layer** — `trp/structured_claim.py` and `trp/claim_verifier.py`. Machine-parseable propositions (ToolOutputEquals, ValueComparison, Compound) with three-valued logic claim-to-evidence matching engine.

**Verification layer** — `trp/verify.py` and `trp/deterministic_tools.py`. `ToolReceiptVerifier` registry-based engine with 7 verification statuses, 6 classification rules, `verify_claim()` batch verification. 4 built-in pure functions.

**Signing layer** — `trp/signing.py`. Ed25519 JWS signing via jwcrypto. Detached signatures, receipt signing with evidence strength auto-escalation, message envelope signing.

**MCP adapter layer** — `trp/mcp_adapter.py`. `wrap_tool_call()`, `wrap_mcp_tool_result()`, `extract_tool_receipt()`. End-to-end: wrap → extract → verify.

**A2A adapter layer** — `trp/a2a_adapter.py`. `trp_capability_to_a2a_card()` and `a2a_card_to_trp_capability()` for lossless round-trip translation.

**Agent layer** — `trp/agent.py`, `trp/knowledge_base.py`, and `trp/llm_agents.py`. Abstract `Agent` base, ResearcherLLM, ChallengerLLM, VerifierLLM shared classes.

**Ledger layer** — `trp/ledger.py`. In-memory balance tracker.

**Transport layer** — `trp/transport.py`. WebSocket server/client.

**LLM adapter layer** — `trp/llm.py`. `LLMAdapter` ABC with `GroqAdapter`, `OllamaAdapter`, `OpenAIAdapter`.

**Web server** — `server.py`. FastAPI with SSE. Endpoints: `/run-simulation`, `/run-deterministic`, `/.well-known/trp-capability.json`, `/.well-known/agent-card.json`, `/debug-env`. Rate limiting, max claim length. Deployed at https://trp-core-production.up.railway.app.

## Current State

**275+ passing tests. v0.3.0 tagged. v0.4 and v0.5 features complete. Railway deployed and live.**

**v0.3 (released):** ToolReceipt, SettlementMessage, AgentCapability, classification enums, deterministic verification demo, Ollama/OpenAI adapters, centralised LLM agents, security hardening.

**v0.4 (implemented):** ToolReceiptVerifier with batch verification, JWS signing (Ed25519), MCP adapter (wrap/extract/verify), capability discovery endpoint, hash test vectors, 6 classification validation rules.

**v0.5 (implemented):** StructuredClaim propositions, claim-to-evidence matching engine, A2A adapter (AgentCapability ↔ AgentCard), /.well-known/agent-card.json endpoint, optional structured_claim field on Claim.

## Engineering Conventions

- Python 3.10+ required
- Dataclasses for all protocol types — no Pydantic, no attrs
- Type hints on all public interfaces
- Docstrings on all public classes and methods
- `pytest` for tests (`tests/` directory)
- No placeholder or stub logic — if a feature isn't implemented, it isn't in the code
- Spec and code must stay in sync — changes to protocol types require updating both SPEC.md/SPEC-v2.md and trp/core.py
- Each serialisable type has `to_dict()` and `from_dict()` class methods
- Pure functions preferred — signing and verification return new objects, not mutations

## What Not To Touch

These files define the core protocol identity. Changes require updating both spec and code together:

- `trp/core.py` — protocol data types
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

1. RFC 8785 (JCS) canonicalization — align with A2A signing requirements (v0.6)
2. Claim.structured_claim migration — make StructuredClaim the primary claim format
3. Sync SPEC.md/SPEC-v2.md with all v0.4-v0.5 implementation details
4. EvidenceBundle — composite evidence grouping multiple receipts and attestations

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
