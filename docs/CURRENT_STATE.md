# Current State

Snapshot as of 22 March 2026.

## Status

- **Protocol version:** 0.3.0 (tagged, released)
- **Tests:** 196 passing
- **GitHub issues:** 13 created, all closed
- **Live URL:** https://urp-core-production.up.railway.app
- **CI:** GitHub Actions running pytest on push and PR
- **v0.4 features:** All implemented (MCP adapter, JWS signing, batch verification, capability endpoint)

## Module Map

| Module | Purpose |
|--------|---------|
| `urp/core.py` | All protocol data types: Claim, ProofReference, Stake, Response, ToolReceipt, SettlementMessage, AgentCapability, JWSSignature, and all enums |
| `urp/message.py` | URPMessage envelope with protocol versioning (PROTOCOL_VERSION = "0.3.0") |
| `urp/verify.py` | ToolReceiptVerifier — registry-based replay verification engine with classification validation, batch verification via verify_claim() |
| `urp/deterministic_tools.py` | 4 built-in pure functions: compute_fibonacci, compute_factorial, compute_sha256, math_eval |
| `urp/signing.py` | Ed25519 JWS signing: key generation, detached signatures, receipt signing with evidence strength escalation, message envelope signing |
| `urp/mcp_adapter.py` | MCP integration: wrap_tool_call, wrap_mcp_tool_result (receipt in _meta), extract_tool_receipt |
| `urp/llm.py` | LLMAdapter ABC + GroqAdapter, OllamaAdapter, OpenAIAdapter |
| `urp/llm_agents.py` | ResearcherLLM, ChallengerLLM, VerifierLLM — shared LLM-backed agent classes |
| `urp/agent.py` | Abstract Agent base class and reference implementations |
| `urp/ledger.py` | In-memory balance tracker for deposits, withdrawals, settlement transfers |
| `urp/knowledge_base.py` | KnowledgeBase ABC and InMemoryKnowledgeBase |
| `urp/transport.py` | WebSocket server/client for networked simulations |
| `server.py` | FastAPI server: /run-simulation (LLM), /run-deterministic (no API key, 2 scenarios), /.well-known/urp-capability.json, /debug-env (gated) |

## Endpoints

| Path | Method | Auth | Description |
|------|--------|------|-------------|
| `/` | GET | None | Web UI with "Run Simulation" and "Deterministic Demo" buttons |
| `/run-simulation` | GET | GROQ_API_KEY | LLM-backed simulation via SSE (3 scenarios or custom claim) |
| `/run-deterministic` | GET | None | Deterministic verification via SSE: verified claim + tampered receipt detection |
| `/.well-known/urp-capability.json` | GET | None | AgentCapability declaration (JSON) |
| `/debug-env` | GET | DEBUG=true | Environment diagnostics (gated, returns 404 otherwise) |

## Security Hardening

- `/debug-env` gated behind `DEBUG=true` env var
- Max 5 concurrent simulations (HTTP 429 on overflow)
- Max claim length 2000 chars (HTTP 400 on overflow)
- CORS still allow_origins=["*"] (acceptable for demo)

## Verification Engine

- **ToolReceiptVerifier** with 7 verification statuses: VERIFIED_EXACT, OUTPUT_HASH_MISMATCH, INPUT_HASH_MISMATCH, NOT_REPLAYABLE, TOOL_NOT_REGISTERED, REPLAY_ERROR, CLASSIFICATION_INVALID
- **6 classification validation rules** rejecting contradictory metadata (DETERMINISTIC+WEAK, MODEL_BASED+STRONG, RANDOMIZED+STRONG, TIME_DEPENDENT+STRONG, ENVIRONMENT_DEPENDENT+STRONG, side_effect≠NONE+STRONG)
- **Batch verification** via verify_claim() — verifies all receipts in a Claim.evidence list
- **9 hash test vectors** pinned for serialisation stability
- Strict and non-strict modes

## JWS Signing

- Ed25519 key generation via jwcrypto
- Detached JWS signatures (payload not embedded)
- Receipt signing with automatic evidence strength escalation (UNSIGNED → CALLER_SIGNED → DUAL_SIGNED)
- Message envelope signing
- Canonical JSON: sorted keys, compact separators (RFC 8785 JCS deferred to v0.5)

## MCP Integration

- `wrap_tool_call()` — convenience function to create ToolReceipts from any tool invocation
- `wrap_mcp_tool_result()` — wraps tool output into MCP CallToolResult shape with receipt in `_meta["urp:tool_receipt"]`
- `extract_tool_receipt()` — extracts receipt from MCP _meta on the client side
- End-to-end: wrap → extract → verify works with ToolReceiptVerifier

## Tests by Module

| File | Count | What it covers |
|------|-------|----------------|
| test_core.py | 38 | All protocol types, enums, serialisation round-trips |
| test_verify.py | 55 | Verification engine, hash vectors, classification rules, batch verification |
| test_signing.py | 33 | Key generation, detached JWS, receipt signing, envelope signing, evidence escalation |
| test_mcp_adapter.py | 25 | wrap_tool_call, wrap_mcp_tool_result, extract, end-to-end verify |
| test_server.py | 24 | Debug-env gating, claim length, deterministic endpoint, capability endpoint |
| test_llm_agents.py | 17 | LLM agent parsing, confidence scoring, adapter constructors |
| test_message.py | 4 | URPMessage versioning and round-trip |
| **Total** | **196** | |

## Next Build Targets

1. **Structured claim format** (v0.5) — replace free-text statements with machine-parseable propositions
2. **A2A adapter** — map AgentCapability to/from A2A agent cards
3. **RFC 8785 (JCS) canonicalization** — align with A2A signing requirements
4. **EvidenceBundle** — composite evidence grouping multiple receipts and attestations
