# CLAUDE.md

## Project Overview

URP (Universal Reasoning Protocol) is a message protocol that lets autonomous agents make claims, attach proof references, and stake economic value on correctness — with other agents able to challenge or verify those claims. It defines the message shapes and interaction flow for structured claim accountability; it does not prescribe transport, identity, or proof format. The repo is at https://github.com/Spudbe/urp-core, current version 0.2.0 (public draft).

## Architecture

The codebase has five layers:

**Message layer** — `urp/core.py` and `urp/message.py`. Defines the protocol data types (`Claim`, `ProofReference`, `Stake`, `Response`, `ClaimType`, `Decision`) as dataclasses with `to_dict()`/`from_dict()` serialisation. `URPMessage` wraps any payload in a versioned envelope with sender, timestamp, and message ID.

**Agent layer** — `urp/agent.py` and `urp/knowledge_base.py`. Abstract `Agent` base class and reference implementations (`ResearcherAgent`, `ChallengerAgent`, `VerifierAgent`). `KnowledgeBase` ABC with `InMemoryKnowledgeBase` for fact lookup.

**Ledger layer** — `urp/ledger.py`. In-memory balance tracker for deposits, withdrawals, and settlement transfers between agents.

**Transport layer** — `urp/transport.py`. WebSocket server/client for networked multi-agent simulations.

**LLM adapter layer** — `urp/llm.py`. Abstract `LLMAdapter` base class and `GroqAdapter` implementation. Any new LLM provider subclasses `LLMAdapter` and implements `complete(system_prompt, user_prompt) -> str`.

**Web server** — `server.py`. FastAPI server with SSE streaming endpoint (`/run-simulation`) and static file serving. Contains its own inline LLM agent helpers (duplicated from `simulations/llm_simulation.py` — consolidation needed). `static/index.html` is the browser UI.

## Current State

**Complete:**
- `urp/core.py` — all protocol types implemented with serialisation
- `urp/message.py` — URPMessage envelope with protocol versioning
- `urp/agent.py` — agent ABCs and reference implementations
- `urp/knowledge_base.py` — knowledge base ABC and in-memory implementation
- `urp/ledger.py` — balance tracking
- `urp/llm.py` — LLMAdapter ABC and GroqAdapter
- `urp/transport.py` — WebSocket transport
- `simulations/simple_simulation.py` — single-process demo
- `simulations/networked_simulation.py` — multi-agent WebSocket demo
- `simulations/llm_simulation.py` — three-scenario LLM-backed simulation
- `server.py` — FastAPI server with SSE streaming and custom claim input
- `static/index.html` — browser interface
- `tests/test_core.py` — core type tests
- `tests/test_message.py` — message serialisation tests
- `SPEC.md` — v1 protocol spec
- `SPEC-v2.md` — v2 spec with JSON schemas

**In progress:**
- LLM agent logic is duplicated between `server.py` and `simulations/llm_simulation.py` — needs consolidation into a shared module

**Not yet started:**
- `SettlementMessage` type (specified in roadmap, not implemented)
- Agent capability declarations
- MCP transport adapter
- OpenAI and Ollama LLM adapters
- Signing model (JWS stub described in SPEC.md, not implemented)

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

# LLM-backed simulation (requires Groq API key)
export GROQ_API_KEY=your_key_here
python simulations/llm_simulation.py

# Web interface (requires Groq API key)
pip install fastapi uvicorn
export GROQ_API_KEY=your_key_here
python server.py
# Open http://localhost:8000
```

## Next Priorities

1. Centralise LLM agent logic from `server.py` and `simulations/llm_simulation.py` into a shared module (e.g. `urp/agents/llm_agents.py`)
2. Add OpenAI adapter (subclass `LLMAdapter`)
3. Add Ollama adapter (subclass `LLMAdapter`)
4. Add `SettlementMessage` type to `urp/core.py` and specs
5. Add agent capability declarations
6. Add MCP transport adapter stub

## Provider Notes

- `GroqAdapter` uses model `llama-3.3-70b-versatile` by default
- Reads `GROQ_API_KEY` from environment; raises `EnvironmentError` if missing
- `LLMAdapter` is the abstract base — any new provider follows the same pattern: subclass it, implement `complete(system_prompt: str, user_prompt: str) -> str`, expose a `model` attribute
- Proof location URIs use the format `llm://groq/{model_name}`, read dynamically from the adapter's `model` attribute

## Commit Style

Prefix commits with: `feat`, `fix`, `spec`, `docs`, `refactor`, `test`, `chore`. Use descriptive messages. One concern per commit.
