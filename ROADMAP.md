# URP Roadmap

## v0.5 — Current (Structured Claims + Interop)

275 tests passing. 16 modules. 7 endpoints. Railway deployed.

What is complete:

- **Everything from v0.3 and v0.4** (see below)
- **StructuredClaim** — `urp/structured_claim.py`: machine-parseable propositions (ToolOutputEquals, ValueComparison, Compound with AND/OR/NOT/IMPLIES), canonical fingerprinting, render_statement()
- **Claim-to-evidence matching** — `urp/claim_verifier.py`: three-valued logic (TRUE/FALSE/UNKNOWN), mechanical proposition-to-receipt matching
- **StructuredClaim in live demo** — structured_claim and claim_match SSE events in /run-deterministic
- **A2A adapter** — `urp/a2a_adapter.py`: AgentCapability ↔ AgentCard translation with lossless round-trip via extension embedding
- **A2A discovery** — `/.well-known/agent-card.json` endpoint serving A2A AgentCard
- **Claim.structured_claim field** — Phase 1 migration: optional `structured_claim: dict` on Claim alongside existing `statement: str`
- **Spec sync (partial)** — StructuredClaim section in SPEC.md, JSON schemas in SPEC-v2.md

## v0.4 — Previous (Interop + Signing)

- **MCP adapter** — `urp/mcp_adapter.py`: wrap_tool_call, wrap_mcp_tool_result, extract_tool_receipt
- **JWS signing** — `urp/signing.py`: Ed25519 detached JWS, receipt signing with evidence strength escalation, message envelope signing
- **Batch verification** — `verify_claim()` over full Claim.evidence list
- **Capability discovery** — `/.well-known/urp-capability.json` endpoint

## v0.3 — Released (tagged)

- **ToolReceipt** with EvidenceStrength, NondeterminismClass, SideEffectClass, ReplayClass enums
- **SettlementMessage** as first-class URPMessage
- **AgentCapability** with stake policy, evidence requirements, claim routing
- **ToolReceiptVerifier** — replay verification engine with 7 statuses, 6 classification rules, hash test vectors
- **Deterministic tool registry** — 4 built-in pure functions (fibonacci, factorial, sha256, math_eval)
- **Live deterministic demo** — `/run-deterministic` with verified + tampered scenarios
- **Ollama and OpenAI adapters**, centralised LLM agents, dynamic confidence scoring
- **Security hardening** — debug-env gating, rate limiting, max claim length

## v0.2 — Previous (Public Draft)

- Core protocol types (Claim, ProofReference, Stake, Response, ClaimType, Decision)
- URPMessage envelope with protocol versioning
- Agent framework, KnowledgeBase, Ledger, WebSocket transport
- GroqAdapter, FastAPI server with SSE, GitHub Actions CI

## v0.6 — Next

**Design principle:** Harden canonicalization, complete the claim migration, expand verification to remote tools.

### Canonicalization

- **RFC 8785 (JCS) adoption** — Replace sorted-key compact JSON with proper JSON Canonicalization Scheme. Aligns with A2A's signing requirements. Affects `urp/signing.py`, `urp/core.py` (hash computation), `urp/structured_claim.py` (fingerprinting).

### Claim migration Phase 2

- **StructuredClaim required** — Make `structured_claim` required for new protocol versions. `statement` auto-generated via `render_statement()`. Update Claim validation to enforce presence.

### Verification

- **Remote tool replay** — ToolReceiptVerifier supports HTTP-callable tools. Register URL + expected schema, verifier calls and compares.
- **StructuredClaim-aware batch verification** — Wire `claim_verifier.match_claim()` into `verify_claim()` so batch verification checks proposition-to-evidence alignment, not just receipt integrity.

### Spec completion

- **SPEC.md** — Add MCP adapter protocol, A2A extension spec, JWS signing protocol, Claim migration rules.
- **SPEC-v2.md** — Add MCP adapter schemas, A2A extension schemas, signing schemas.

## v0.7 — Future Direction

- **EvidenceBundle** — Composite evidence grouping multiple ToolReceipts, external document hashes, and signed attestations.
- **FactualAssertion propositions** — SPO triples for structured factual claims (deferred from v0.5 — no mechanical verification path yet).
- **Privacy and encryption** — Selective disclosure, zero-knowledge proof integration.
- **Governance and versioning** — Formal protocol versioning, backwards compatibility guarantees, deprecation policy.
- **EU AI Act alignment** — Map URP's audit trail (signed receipts, structured claims, settlement records) to Articles 14, 15, and 17 traceability requirements. Document compliance mapping.
