# Changelog

All notable changes to TRP are documented here.

## [0.6.0] – 2026-03-23

### Changed
- **BREAKING**: RFC 8785 JCS canonicalization replaces sorted-key compact JSON for all hash computation and signing
- **BREAKING**: Module renamed from urp/ to trp/ (Tool Receipt Protocol)
- **BREAKING**: License changed from BUSL-1.1 to Apache-2.0
- Protocol version bumped to 0.6.0

### Added
- `trp/canonical.py` — centralised RFC 8785 JCS canonicalization
- `Claim.create()` factory method — structured_claim required, statement auto-generated
- Remote tool replay via `ToolReceiptVerifier.register_remote()`
- `EvidenceBundle` — composite evidence type grouping receipts, document hashes, and attestations
- `trp/cli.py` — CLI entry point (`trp verify`, `trp match`, `trp hash`, `trp version`)
- REST API endpoints: `POST /api/verify`, `POST /api/match`, `POST /api/hash`, `GET /api/schemas/tool-receipt`
- `examples/` directory with real JSON receipt, claim, and verification artifacts
- OpenClaw security crisis case study (`docs/OPENCLAW_CASE_STUDY.md`)
- PyPI package metadata, build configuration, and CLI entry point

## [0.5.0] – 2026-03-22

### Added
- StructuredClaim: machine-parseable propositions (ToolOutputEquals, ValueComparison, Compound) in trp/structured_claim.py
- Claim-to-evidence matching engine in trp/claim_verifier.py with three-valued logic
- A2A adapter in trp/a2a_adapter.py: AgentCapability ↔ AgentCard translation
- StructuredClaim and claim_match SSE events in live deterministic demo
- Optional structured_claim field on Claim (Phase 1 migration)
- /.well-known/agent-card.json A2A discovery endpoint

## [0.4.0] – 2026-03-22

### Added
- MCP adapter in trp/mcp_adapter.py: wrap_tool_call, wrap_mcp_tool_result, extract_tool_receipt
- JWS signing in trp/signing.py: Ed25519 detached signatures, receipt signing with evidence strength escalation
- Batch verification: verify_claim() over Claim.evidence list
- /.well-known/trp-capability.json discovery endpoint
- jwcrypto dependency added

## [0.3.0] – 2026-03-22

### Added
- ToolReceipt evidence type: a structured verifiable record of a tool invocation. Captures tool identity (name, version, provider, endpoint, definition hash), canonicalized input/output with SHA-256 hashes, execution metadata, side-effect class, nondeterminism class, replay instructions, and replay class (none, weak, stateful, strong, witness_only). Includes optional signature support.
- EvidenceStrength enum: unsigned, caller_signed, provider_signed, dual_signed. Makes trust levels explicit. Dual-signed receipts are strongest; caller-signed receipts are weak evidence.
- NondeterminismClass enum: deterministic, time_dependent, randomized, model_based, environment_dependent.
- SideEffectClass enum: none, read_only, external_write, irreversible. Verifiers use these to decide whether replay is possible or safe.
- ReplayClass enum: strong, stateful, weak, witness_only, none. Explicitly sets replay expectations.
- SettlementMessage: first-class protocol message for distributing stakes after claim resolution. Fields: settlement_id, claim_id, outcome, researcher_delta, challenger_delta, timestamp, notes.
- OllamaAdapter: local model support via Ollama. Allows TRP agents to run against any Ollama-compatible model without API keys.
- Centralised LLM agent logic in trp/llm_agents.py: ResearcherLLM, ChallengerLLM, VerifierLLM as shared classes used by both server.py and simulations.
- Deterministic ToolReceipt verification demo (simulations/deterministic_demo.py): pure-function replay verification with tamper detection, no LLM required.
- OpenAI adapter: OpenAIAdapter using stdlib urllib, no openai package dependency.
- `/debug-env` endpoint gated behind `DEBUG=true` environment variable.
- Basic rate limiting on `/run-simulation` (5 concurrent simulations max).
- Maximum claim length enforcement (2000 characters).

### Changed
- ProofReference repositioned as a citation pointer, not proof. Claims now carry an evidence list of ToolReceipt objects.
- Claim format updated: evidence field added as list of ToolReceipt objects (empty by default).
- LLM proof location now reflects actual configured model (dynamic, not hardcoded).

### Design decisions
- Evidence-first pivot: TRP now targets claims verifiable by replay or signature, not claims that require trusting another LLM opinion.
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
- TRPMessage envelope with protocol versioning.
- Agent framework: Agent ABC, ResearcherAgent, ChallengerAgent, VerifierAgent.
- KnowledgeBase ABC and InMemoryKnowledgeBase.
- In-memory Ledger with deposit, withdraw, transfer.
- WebSocket transport (AgentServer, AgentClient).
- LLMAdapter ABC and GroqAdapter implementation.
- FastAPI server with SSE streaming and browser-based simulation interface.
- Error taxonomy: 13 error codes.
- Signing model stub referencing JWS RFC 7515.
- Apache-2.0 license, change date 2030-03-21.
- CLAUDE.md for agent session context.
- GitHub Actions CI.
