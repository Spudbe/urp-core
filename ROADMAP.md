# URP Roadmap

## v0.3 — Released (tagged)

- **ToolReceipt** with EvidenceStrength, NondeterminismClass, SideEffectClass, ReplayClass enums
- **SettlementMessage** as first-class URPMessage
- **AgentCapability** with capability discovery at `/.well-known/urp-capability.json`
- **ToolReceiptVerifier** — replay verification engine with 7 statuses, 6 classification rules, hash test vectors
- **Deterministic tool registry** — 4 built-in pure functions (fibonacci, factorial, sha256, math_eval)
- **Live deterministic demo** — `/run-deterministic` with verified + tampered scenarios
- **Ollama and OpenAI adapters**, centralised LLM agents, dynamic confidence scoring
- **Security hardening** — debug-env gating, rate limiting, max claim length

## v0.2 — Previous (Public Draft)

- Core protocol types (Claim, ProofReference, Stake, Response, ClaimType, Decision)
- URPMessage envelope with protocol versioning
- Agent framework (Agent ABC, ResearcherAgent, ChallengerAgent, VerifierAgent)
- KnowledgeBase, Ledger, WebSocket transport
- GroqAdapter, FastAPI server with SSE, GitHub Actions CI

## v0.4 — Complete (Interop + Signing)

- **MCP adapter** — `urp/mcp_adapter.py`: wrap_tool_call, wrap_mcp_tool_result, extract_tool_receipt
- **JWS signing** — `urp/signing.py`: Ed25519 detached JWS, receipt signing with evidence strength escalation, message envelope signing
- **Batch verification** — `verify_claim()` over full Claim.evidence list

## v0.5 — Complete (Structured Claims + Interop)

- **StructuredClaim** — `urp/structured_claim.py`: machine-parseable propositions (ToolOutputEquals, ValueComparison, Compound with AND/OR/NOT/IMPLIES), canonical fingerprinting, render_statement()
- **Claim-to-evidence matching** — `urp/claim_verifier.py`: three-valued logic (TRUE/FALSE/UNKNOWN), mechanical proposition-to-receipt matching
- **StructuredClaim in live demo** — structured_claim and claim_match SSE events in /run-deterministic
- **A2A adapter** — `urp/a2a_adapter.py`: AgentCapability ↔ AgentCard translation with lossless round-trip via extension embedding

## v0.6 — Next

**Design principle:** Harden canonicalization, expand verification reach, migrate Claim to use StructuredClaim.

### Canonicalization and signing

- **RFC 8785 (JCS) adoption** — Replace sorted-key compact JSON with proper JSON Canonicalization Scheme. Aligns with A2A's signing requirements. Affects urp/signing.py and all hash computation.

### Claim migration

- **Phase 1: Claim.structured_claim field** — Add `structured_claim: Optional[StructuredClaim]` to Claim dataclass. Verifiers prefer it when present; statement becomes informational.
- **Phase 2: StructuredClaim required** — Make structured_claim required for new protocol versions. statement auto-generated via render_statement().

### Verification expansion

- **Remote tool replay** — ToolReceiptVerifier supports HTTP-callable tools. Register URL + expected schema, verifier calls and compares.
- **StructuredClaim-aware verification** — Wire claim_verifier.match_claim() into ToolReceiptVerifier.verify_claim() so batch verification checks proposition-to-evidence alignment, not just receipt integrity.

### Spec sync

- **SPEC.md and SPEC-v2.md update** — Add StructuredClaim schemas, signing protocol, MCP adapter spec, A2A extension spec. Currently code is ahead of spec.

## v0.7 — Future Direction

- **EvidenceBundle** — Composite evidence grouping multiple ToolReceipts, external document hashes, and signed attestations.
- **FactualAssertion propositions** — SPO triples for structured factual claims (deferred from StructuredClaim v0.5 — no mechanical verification path yet).
- **Privacy and encryption** — Selective disclosure, zero-knowledge proof integration.
- **Governance and versioning** — Formal protocol versioning governance, backwards compatibility guarantees.
