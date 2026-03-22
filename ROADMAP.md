# URP Roadmap

## v0.3 — Current Release

What is complete:

- **Everything from v0.2** (see below)
- **ToolReceipt** — First concretely verifiable proof type. Records tool name, version, inputs, output, timestamp, and optional signature. Verifiable by replay or signature check, not by asking another LLM. ([#12](https://github.com/Spudbe/urp-core/issues/12))
- **EvidenceStrength / NondeterminismClass / SideEffectClass / ReplayClass enums** — Fine-grained classification of evidence quality, reproducibility, and side effects.
- **SettlementMessage** — First-class message type for explicit fund-transfer records. ([#5](https://github.com/Spudbe/urp-core/issues/5))
- **AgentCapability** — Dataclass letting agents declare supported claim types, accepted proof formats, and protocol version. ([#6](https://github.com/Spudbe/urp-core/issues/6))
- **OllamaAdapter** — Local model support via Ollama. ([#3](https://github.com/Spudbe/urp-core/issues/3))
- **OpenAIAdapter** — OpenAI model support using stdlib urllib. ([#8](https://github.com/Spudbe/urp-core/issues/8))
- **Centralised LLM agents** — ResearcherLLM, ChallengerLLM, VerifierLLM in `urp/llm_agents.py`. ([#2](https://github.com/Spudbe/urp-core/issues/2))
- **Dynamic confidence scoring** — Confidence derived from LLM reasoning. ([#9](https://github.com/Spudbe/urp-core/issues/9))
- **Deterministic verification demo** — Pure-function replay verification with tamper detection (`simulations/deterministic_demo.py`).
- **Security hardening** — `/debug-env` gated behind `DEBUG=true`, rate limiting on simulations, max claim length enforcement.

What is not yet implemented:

- JWS signing (stubbed in SPEC.md)
- MCP transport adapter ([#7](https://github.com/Spudbe/urp-core/issues/7))
- `ToolReceiptVerifier` engine with deterministic tool registry
- Deterministic verification scenario in live web demo
- SettlementMessage streaming as URPMessage events

## v0.2 — Previous (Public Draft)

What is complete:

- **Protocol types** — Claim, ProofReference, Stake, Response, ClaimType, Decision dataclasses with full serialisation (`urp/core.py`)
- **Message envelope** — URPMessage with protocol versioning, sender, timestamp, message ID (`urp/message.py`)
- **Agent framework** — Abstract Agent base class, ResearcherAgent, ChallengerAgent, VerifierAgent (`urp/agent.py`)
- **Knowledge base** — KnowledgeBase ABC and InMemoryKnowledgeBase (`urp/knowledge_base.py`)
- **Ledger** — In-memory balance tracker for deposits, withdrawals, settlement transfers (`urp/ledger.py`)
- **LLM adapter** — Abstract LLMAdapter base class and GroqAdapter for Groq API (`urp/llm.py`)
- **WebSocket transport** — Server/client for networked multi-agent simulations (`urp/transport.py`)
- **Simulations** — Simple single-process demo, networked WebSocket demo, three-scenario LLM-backed simulation (`simulations/`)
- **Web interface** — FastAPI server with SSE streaming, browser UI with custom claim input (`server.py`, `static/index.html`)
- **Specification** — v1 protocol spec with error codes and signing stub (`SPEC.md`), v2 spec with JSON schemas (`SPEC-v2.md`)
- **CI** — GitHub Actions running pytest on push and PR (`.github/workflows/ci.yml`)

What is not yet implemented:

- Settlement is implicit in simulation scripts, not a first-class message type
- Agents cannot declare capabilities
- Proofs are LLM-generated summaries — no mechanically verifiable evidence type
- No message signing
- No MCP transport integration
- Only one LLM provider (Groq)

## v0.4 — Planned

**Design principle for v0.4:** Build the verification engine and prove it in the live demo.

### Verification engine

- **`ToolReceiptVerifier`** — `urp/verify.py` with a registry of deterministic tool functions, automatic replay, and hash comparison.
- **Test vectors** — Canonical test cases for receipt hashing to catch serialisation drift.
- **Deterministic tool registry** — Registry of pure functions that can be replayed for verification.

### Live demo integration

- **Deterministic scenario in web demo** — Add a replay-verified scenario to the SSE simulation stream alongside the LLM scenarios.
- **SettlementMessage streaming** — Emit SettlementMessage as a first-class URPMessage event in the SSE stream.

### Signing and transport

- **JWS signing** — Implement the signing model stubbed in SPEC.md. URPMessage envelopes carry detached JWS signatures over canonical JSON.
- **MCP transport adapter** — Spec and stub implementation for carrying URP messages as MCP tool calls. ([#7](https://github.com/Spudbe/urp-core/issues/7))

## v0.5 — Future Direction

- **EvidenceBundle** — Composite evidence type that groups multiple ToolReceipts, external document hashes, and signed attestations into a single verifiable package attached to a claim.

- **Structured reasoning format** — Replace free-text claim statements with a structured logic representation. Claims become machine-parseable propositions rather than natural language strings.

- **Machine-native communication layer** — Binary-efficient message encoding and transport optimised for high-throughput agent-to-agent communication. Move beyond JSON-over-WebSocket toward a protocol designed for machines, not human readability.

- **Privacy and encryption** — End-to-end encryption for claim content, selective disclosure of proof details, and zero-knowledge proof integration for sensitive claims.

- **Governance and versioning** — Formal protocol versioning governance, backwards compatibility guarantees, and deprecation policy.
