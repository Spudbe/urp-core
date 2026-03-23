# Current State

Snapshot as of 23 March 2026.

## Status

- **Protocol version:** 0.6.0 (tagged, released)
- **Tests:** 300 passing
- **GitHub issues:** 13 created, all closed
- **Live URL:** https://trp-core-production.up.railway.app
- **CI:** GitHub Actions running pytest on push and PR
- **v0.4 features:** All implemented (MCP adapter, JWS signing, batch verification, capability endpoint)
- **v0.5 features:** All implemented (StructuredClaim, claim-to-evidence matching, A2A adapter, agent-card endpoint)
- **v0.6 features:** All implemented (RFC 8785 JCS, Claim.create(), remote tool replay, EvidenceBundle, CLI, REST API, examples, PyPI prep)

## Module Map (18 modules in trp/)

| Module | Purpose |
|--------|---------|
| `trp/core.py` | All protocol data types: Claim (with Claim.create() factory), ProofReference, Stake, Response, ToolReceipt, SettlementMessage, EvidenceBundle, AgentCapability, JWSSignature, and all enums |
| `trp/cli.py` | CLI entry point: trp verify, trp match, trp hash, trp version |
| `trp/canonical.py` | RFC 8785 JCS canonicalization: canonical_bytes(), canonical_str(), sha256_hex() |
| `trp/message.py` | TRPMessage envelope with protocol versioning (PROTOCOL_VERSION = "0.6.0") |
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
| `server.py` | FastAPI server: /run-simulation, /run-deterministic, /.well-known/trp-capability.json, /.well-known/agent-card.json, /api/verify, /api/match, /api/hash, /api/schemas/tool-receipt, /debug-env |

## Endpoints

| Path | Method | Auth | Description |
|------|--------|------|-------------|
| `/` | GET | None | Web UI with "Run Simulation" and "Deterministic Demo" buttons |
| `/run-simulation` | GET | GROQ_API_KEY | LLM-backed simulation via SSE (3 scenarios or custom claim) |
| `/run-deterministic` | GET | None | Deterministic verification via SSE: verified claim + tampered receipt detection |
| `/.well-known/trp-capability.json` | GET | None | AgentCapability declaration (JSON) |
| `/.well-known/agent-card.json` | GET | None | A2A AgentCard declaration (JSON) |
| `/api/verify` | POST | None | Verify a ToolReceipt by replaying registered tools |
| `/api/match` | POST | None | Match a StructuredClaim against ToolReceipt evidence |
| `/api/hash` | POST | None | Compute JCS canonical hash of a JSON object |
| `/api/schemas/tool-receipt` | GET | None | ToolReceipt field descriptions for integrators |
| `/debug-env` | GET | DEBUG=true | Environment diagnostics (gated, returns 404 otherwise) |

## Tests by Module

| File | Count | What it covers |
|------|-------|----------------|
| test_core.py | 48 | All protocol types, enums, serialisation round-trips, structured_claim, EvidenceBundle |
| test_structured_claim.py | 46 | StructuredClaim propositions, claim-to-evidence matching, three-valued logic |
| test_verify.py | 59 | Verification engine, hash vectors, classification rules, batch verification, remote replay |
| test_signing.py | 33 | Key generation, detached JWS, receipt signing, envelope signing, evidence escalation |
| test_mcp_adapter.py | 25 | wrap_tool_call, wrap_mcp_tool_result, extract, end-to-end verify |
| test_a2a_adapter.py | 24 | AgentCapability ↔ AgentCard translation, lossless round-trip |
| test_server.py | 35 | Debug-env gating, claim length, deterministic endpoint, capability endpoint, REST API |
| test_cli.py | 5 | CLI verify, match, hash, version commands |
| test_llm_agents.py | 17 | LLM agent parsing, confidence scoring, adapter constructors |
| test_message.py | 4 | TRPMessage versioning and round-trip |
| **Total** | **300** | |

## Next Build Targets

1. **Sync SPEC.md/SPEC-v2.md** — update specs with all v0.4-v0.6 implementation details
2. **DID-based identity and key resolution**
3. **Timestamp authorities for non-repudiation**
4. **PyPI publication**
