# Current State

Snapshot as of 22 March 2026.

## Status

- **Protocol version:** 0.3.0 (tagged, released)
- **Tests:** 275 passing
- **GitHub issues:** 13 created, all closed
- **Live URL:** https://trp-core-production.up.railway.app
- **CI:** GitHub Actions running pytest on push and PR
- **v0.4 features:** All implemented (MCP adapter, JWS signing, batch verification, capability endpoint)
- **v0.5 features:** All implemented (StructuredClaim, claim-to-evidence matching, A2A adapter, agent-card endpoint)

## Module Map (16 modules in trp/)

| Module | Purpose |
|--------|---------|
| `trp/core.py` | All protocol data types: Claim (with optional structured_claim), ProofReference, Stake, Response, ToolReceipt, SettlementMessage, AgentCapability, JWSSignature, and all enums |
| `trp/message.py` | TRPMessage envelope with protocol versioning (PROTOCOL_VERSION = "0.3.0") |
| `trp/structured_claim.py` | StructuredClaim: ToolOutputEquals, ValueComparison, Compound propositions with LogicalOp and ComparisonOp |
| `trp/claim_verifier.py` | Claim-to-evidence matching engine with three-valued logic (true/false/unknown) |
| `trp/verify.py` | ToolReceiptVerifier — registry-based replay verification engine with classification validation, batch verification via verify_claim() |
| `trp/deterministic_tools.py` | 4 built-in pure functions: compute_fibonacci, compute_factorial, compute_sha256, math_eval |
| `trp/signing.py` | Ed25519 JWS signing: key generation, detached signatures, receipt signing with evidence strength escalation, message envelope signing |
| `trp/mcp_adapter.py` | MCP integration: wrap_tool_call, wrap_mcp_tool_result (receipt in _meta), extract_tool_receipt |
| `trp/a2a_adapter.py` | A2A integration: trp_capability_to_a2a_card, a2a_card_to_trp_capability with lossless round-trip |
| `trp/llm.py` | LLMAdapter ABC + GroqAdapter, OllamaAdapter, OpenAIAdapter |
| `trp/llm_agents.py` | ResearcherLLM, ChallengerLLM, VerifierLLM — shared LLM-backed agent classes |
| `trp/agent.py` | Abstract Agent base class and reference implementations |
| `trp/ledger.py` | In-memory balance tracker for deposits, withdrawals, settlement transfers |
| `trp/knowledge_base.py` | KnowledgeBase ABC and InMemoryKnowledgeBase |
| `trp/transport.py` | WebSocket server/client for networked simulations |
| `server.py` | FastAPI server: /run-simulation, /run-deterministic, /.well-known/trp-capability.json, /.well-known/agent-card.json, /debug-env |

## Endpoints

| Path | Method | Auth | Description |
|------|--------|------|-------------|
| `/` | GET | None | Web UI with "Run Simulation" and "Deterministic Demo" buttons |
| `/run-simulation` | GET | GROQ_API_KEY | LLM-backed simulation via SSE (3 scenarios or custom claim) |
| `/run-deterministic` | GET | None | Deterministic verification via SSE: verified claim + tampered receipt detection |
| `/.well-known/trp-capability.json` | GET | None | AgentCapability declaration (JSON) |
| `/.well-known/agent-card.json` | GET | None | A2A AgentCard declaration (JSON) |
| `/debug-env` | GET | DEBUG=true | Environment diagnostics (gated, returns 404 otherwise) |

## Tests by Module

| File | Count | What it covers |
|------|-------|----------------|
| test_core.py | 40 | All protocol types, enums, serialisation round-trips, structured_claim field |
| test_structured_claim.py | 46 | StructuredClaim propositions, claim-to-evidence matching, three-valued logic |
| test_verify.py | 55 | Verification engine, hash vectors, classification rules, batch verification |
| test_signing.py | 33 | Key generation, detached JWS, receipt signing, envelope signing, evidence escalation |
| test_mcp_adapter.py | 25 | wrap_tool_call, wrap_mcp_tool_result, extract, end-to-end verify |
| test_a2a_adapter.py | 24 | AgentCapability ↔ AgentCard translation, lossless round-trip |
| test_server.py | 31 | Debug-env gating, claim length, deterministic endpoint, capability endpoint, agent-card endpoint |
| test_llm_agents.py | 17 | LLM agent parsing, confidence scoring, adapter constructors |
| test_message.py | 4 | TRPMessage versioning and round-trip |
| **Total** | **275** | |

## Next Build Targets

1. **RFC 8785 (JCS) canonicalization** (v0.6) — align with A2A signing requirements
2. **Claim.structured_claim migration** — make StructuredClaim the primary claim format
3. **Sync SPEC.md/SPEC-v2.md** — update specs with all v0.4-v0.5 implementation details
4. **EvidenceBundle** — composite evidence grouping multiple receipts and attestations
