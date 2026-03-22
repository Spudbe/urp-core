# Changelog

All notable changes to URP are documented here.

## [0.3.0] – Unreleased

### Added
- ToolReceipt evidence type: a structured verifiable record of a tool invocation. Captures tool identity (name, version, provider, endpoint, definition hash), canonicalized input/output with SHA-256 hashes, execution metadata, side-effect class, nondeterminism class, replay instructions, and replay class (none, weak, stateful, strong, witness_only). Includes optional signature support.
- EvidenceStrength enum: unsigned, caller_signed, provider_signed, dual_signed. Makes trust levels explicit. Dual-signed receipts are strongest; caller-signed receipts are weak evidence.
- NondeterminismClass enum: deterministic, time_dependent, randomized, model_based, environment_dependent.
- SideEffectClass enum: none, read_only, external_write, irreversible. Verifiers use these to decide whether replay is possible or safe.
- ReplayClass enum: strong, stateful, weak, witness_only, none. Explicitly sets replay expectations.
- SettlementMessage: first-class protocol message for distributing stakes after claim resolution. Fields: settlement_id, claim_id, outcome, researcher_delta, challenger_delta, timestamp, notes.
- OllamaAdapter: local model support via Ollama. Allows URP agents to run against any Ollama-compatible model without API keys.
- Centralised LLM agent logic in urp/llm_agents.py: ResearcherLLM, ChallengerLLM, VerifierLLM as shared classes used by both server.py and simulations.

### Changed
- ProofReference repositioned as a citation pointer, not proof. Claims now carry an evidence list of ToolReceipt objects.
- Claim format updated: evidence field added as list of ToolReceipt objects (empty by default).
- LLM proof location now reflects actual configured model (dynamic, not hardcoded).

### Design decisions
- Evidence-first pivot: URP now targets claims verifiable by replay or signature, not claims that require trusting another LLM opinion.
- Replay classification: replay_class field prevents false expectations about deterministic replay for model-based or stateful tool calls.
- Evidence strength levels: explicitly surfaces the difference between unsigned, caller-signed, and provider-signed receipts.

### Deferred to v0.4
- Selective disclosure and zero-knowledge proofs.
- Full DID / verifiable credential integration.
- Streaming Merkle proofs.
- Governance, reputation models, and on-chain escrow.

## [0.2.0] – 2026-03-22

### Added
- Initial public draft release.
- Core protocol types: Claim, ProofReference, Stake, Response, ClaimType, Decision.
- URPMessage envelope with protocol versioning.
- Agent framework: Agent ABC, ResearcherAgent, ChallengerAgent, VerifierAgent.
- KnowledgeBase ABC and InMemoryKnowledgeBase.
- In-memory Ledger with deposit, withdraw, transfer.
- WebSocket transport (AgentServer, AgentClient).
- LLMAdapter ABC and GroqAdapter implementation.
- FastAPI server with SSE streaming and browser-based simulation interface.
- Error taxonomy: 13 error codes.
- Signing model stub referencing JWS RFC 7515.
- BUSL-1.1 license, change date 2030-03-21.
- CLAUDE.md for agent session context.
- GitHub Actions CI.
