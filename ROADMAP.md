# URP Roadmap

## v0.2 — Current (Public Draft)

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

## v0.3 — Planned

**Design principle for v0.3:** URP constrains its verification model to claims that can be verified without asking another LLM. ToolReceipt is the first concrete implementation of this principle.

### Protocol additions

- **SettlementMessage** — First-class message type for explicit fund-transfer records. Fields: claim_id, outcome (accepted/rejected/expired), researcher_delta, challenger_delta, timestamp. Makes settlement auditable and replayable. ([#5](https://github.com/Spudbe/urp-core/issues/5))

- **AgentCapability** — Dataclass letting agents declare supported claim types, accepted proof formats, and protocol version. Enables routing claims to capable agents. ([#6](https://github.com/Spudbe/urp-core/issues/6))

- **ToolReceipt** — First concretely verifiable proof type. Records tool name, version, inputs, output, timestamp, and optional signature. Verifiable by replay or signature check, not by asking another LLM. ([#12](https://github.com/Spudbe/urp-core/issues/12))

- **JWS signing** — Implement the signing model stubbed in SPEC.md. URPMessage envelopes carry detached JWS signatures over canonical JSON. Key management via DID or pre-shared keys.

### Transport

- **MCP transport adapter** — Spec and stub implementation for carrying URP messages as MCP tool calls. Positions URP as the accountability layer for MCP-based tool workflows. ([#7](https://github.com/Spudbe/urp-core/issues/7))

### LLM providers

- **Ollama adapter** — OllamaAdapter for local model inference via Ollama API. ([#3](https://github.com/Spudbe/urp-core/issues/3))

- **OpenAI adapter** — OpenAIAdapter following the same pattern as GroqAdapter. ([#8](https://github.com/Spudbe/urp-core/issues/8))

### Agent improvements

- **Dynamic confidence scoring** — Derive confidence_score from LLM reasoning rather than hardcoding 0.8. ([#9](https://github.com/Spudbe/urp-core/issues/9))

- **Centralised agent module** — Consolidate duplicated LLM agent logic from server.py and llm_simulation.py into urp/llm_agents.py. ([#2](https://github.com/Spudbe/urp-core/issues/2))

## v0.4 — Future Direction

- **EvidenceBundle** — Composite evidence type that groups multiple ToolReceipts, external document hashes, and signed attestations into a single verifiable package attached to a claim.

- **Structured reasoning format** — Replace free-text claim statements with a structured logic representation. Claims become machine-parseable propositions rather than natural language strings.

- **Machine-native communication layer** — Binary-efficient message encoding and transport optimised for high-throughput agent-to-agent communication. Move beyond JSON-over-WebSocket toward a protocol designed for machines, not human readability.

- **Privacy and encryption** — End-to-end encryption for claim content, selective disclosure of proof details, and zero-knowledge proof integration for sensitive claims.

- **Governance and versioning** — Formal protocol versioning governance, backwards compatibility guarantees, and deprecation policy.
