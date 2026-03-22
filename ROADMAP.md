# URP Roadmap

## v0.3 — Current Release

What is complete:

- **Everything from v0.2** (see below)
- **ToolReceipt** — First concretely verifiable proof type. Records tool name, version, inputs, output, timestamp, and optional signature. Verifiable by replay or signature check, not by asking another LLM. ([#12](https://github.com/Spudbe/urp-core/issues/12))
- **EvidenceStrength / NondeterminismClass / SideEffectClass / ReplayClass enums** — Fine-grained classification of evidence quality, reproducibility, and side effects.
- **SettlementMessage** — First-class message type for explicit fund-transfer records, emitted as URPMessage in both LLM and deterministic flows. ([#5](https://github.com/Spudbe/urp-core/issues/5))
- **AgentCapability** — Dataclass letting agents declare supported claim types, accepted proof formats, and protocol version. Served at `/.well-known/urp-capability.json`. ([#6](https://github.com/Spudbe/urp-core/issues/6))
- **ToolReceiptVerifier** — Registry-based verification engine (`urp/verify.py`). Validates classification consistency, replays deterministic tools, compares output hashes. 7 verification statuses.
- **Deterministic tool registry** — 4 built-in pure functions (`urp/deterministic_tools.py`): `compute_fibonacci`, `compute_factorial`, `compute_sha256`, `math_eval`.
- **Classification validation** — 6 rules rejecting contradictory receipt metadata (e.g. DETERMINISTIC+WEAK, RANDOMIZED+STRONG, side effects+STRONG).
- **Hash test vectors** — Pinned canonical JSON → SHA-256 vectors that catch serialisation drift.
- **Live deterministic demo** — `/run-deterministic` endpoint streaming two scenarios: verified claim + tampered receipt detection. No API key required.
- **Capability discovery** — `/.well-known/urp-capability.json` endpoint serving an AgentCapability declaration.
- **OllamaAdapter** — Local model support via Ollama. ([#3](https://github.com/Spudbe/urp-core/issues/3))
- **OpenAIAdapter** — OpenAI model support using stdlib urllib. ([#8](https://github.com/Spudbe/urp-core/issues/8))
- **Centralised LLM agents** — ResearcherLLM, ChallengerLLM, VerifierLLM in `urp/llm_agents.py`. ([#2](https://github.com/Spudbe/urp-core/issues/2))
- **Dynamic confidence scoring** — Confidence derived from LLM reasoning. ([#9](https://github.com/Spudbe/urp-core/issues/9))
- **Security hardening** — `/debug-env` gated behind `DEBUG=true`, rate limiting (5 concurrent), max claim length (2000 chars).

What is not yet implemented:

- JWS signing (stubbed in SPEC.md)
- MCP transport adapter ([#7](https://github.com/Spudbe/urp-core/issues/7))

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

## v0.4 — Next (Interop + Signing)

**Design principle for v0.4:** Make URP useful outside the demo. Prove it works with real tool-calling flows and signed messages.

### MCP integration

- **MCP transport adapter** — Carry URP ToolReceipts as `_meta` on MCP `ToolResultContent`. An MCP server wraps tool call results in ToolReceipts; an MCP client verifies them. ([#7](https://github.com/Spudbe/urp-core/issues/7))
- **"Wrap any tool call" utility** — A reusable function that takes a tool name, inputs, outputs, and classification, and returns a ToolReceipt. Makes it trivial for MCP server authors to add URP receipts.

### JWS signing

- **Signed ToolReceipts** — Implement Ed25519 JWS signing over canonical receipt JSON. `EvidenceStrength.CALLER_SIGNED` and `PROVIDER_SIGNED` become exercised, not just enum values.
- **Signed URPMessage envelopes** — Detached JWS signatures on the wire envelope, using the JWSSignature type already in `urp/core.py`.
- **Key management** — Minimal key generation and verification utilities. No full PKI — just enough for demo signing and local verification.

### Verifier improvements

- **Remote tool replay** — `ToolReceiptVerifier` supports HTTP-callable tools (not just local Python functions). Register a URL + expected schema, verifier calls it and compares.
- **Batch verification** — Verify all receipts in a `Claim.evidence` list in one call, returning a summary result.

## v0.5 — Future Direction

- **EvidenceBundle** — Composite evidence type that groups multiple ToolReceipts, external document hashes, and signed attestations into a single verifiable package attached to a claim.

- **A2A adapter** — Map URP AgentCapability to/from A2A agent cards. Route claims to capable agents using A2A discovery.

- **Structured claim format** — Replace free-text claim statements with machine-parseable propositions. Claims become structured logic, not natural language strings.

- **Canonicalization alignment** — Adopt RFC 8785 (JCS) for canonical JSON, aligning with A2A's canonicalization requirements for signed agent cards.

- **Privacy and encryption** — Selective disclosure of proof details. Zero-knowledge proof integration for sensitive claims.

- **Governance and versioning** — Formal protocol versioning governance, backwards compatibility guarantees, and deprecation policy.
