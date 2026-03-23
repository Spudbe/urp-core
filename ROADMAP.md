# TRP Roadmap

## v0.5 — Current Release

279 tests. 16 modules. 7 endpoints. Railway deployed.

What is complete:

- **Everything from v0.2, v0.3, and v0.4** (see below)
- **StructuredClaim** — machine-parseable propositions (ToolOutputEquals, ValueComparison, Compound with AND/OR/NOT/IMPLIES), canonical fingerprinting, render_statement()
- **Claim-to-evidence matching** — three-valued logic (TRUE/FALSE/UNKNOWN), mechanical proposition-to-receipt matching
- **StructuredClaim-aware batch verification** — verify_claim() checks proposition-to-evidence alignment, not just receipt integrity
- **StructuredClaim in live demo** — structured_claim and claim_match SSE events in /run-deterministic
- **A2A adapter** — AgentCapability ↔ AgentCard translation with lossless round-trip via extension embedding
- **A2A discovery** — `/.well-known/agent-card.json` endpoint
- **Claim.structured_claim field** — Phase 1 migration: optional structured_claim on Claim
- **Spec completion** — StructuredClaim, MCP adapter, A2A extension, JWS signing all specified in SPEC.md and SPEC-v2.md
- **EU AI Act alignment document** — honest mapping to Articles 14, 15, 17

## v0.4 — Previous (Interop + Signing)

- MCP adapter, JWS signing (Ed25519), batch verification, capability discovery endpoint

## v0.3 — Released (tagged)

- ToolReceipt, SettlementMessage, AgentCapability, ToolReceiptVerifier, deterministic tool registry, live demo, LLM adapters, security hardening

## v0.2 — Previous (Public Draft)

- Core protocol types, TRPMessage envelope, agent framework, ledger, transport, CI

---

## v0.6 — Next (Hardening)

**Design principle:** Make TRP's evidence artifacts cryptographically interoperable and usable in CI pipelines. This is the "court-grade determinism" release.

### RFC 8785 (JCS) canonicalization

- Replace sorted-key compact JSON with proper JSON Canonicalization Scheme across `trp/signing.py`, `trp/core.py`, `trp/structured_claim.py`
- Publish cross-language test vectors (canonical bytes → expected hashes)
- This is a breaking change boundary — treat it as the v0.6 line in the sand

### Claim migration Phase 2

- Make `structured_claim` required for new protocol versions
- `statement` auto-generated via `render_statement()` — human-readable but non-authoritative
- Ship simultaneously with JCS so there's one migration, not two

### Remote tool replay

- ToolReceiptVerifier supports HTTP-callable tools (register URL + expected schema, verifier calls and compares)
- Makes TRP usable beyond local Python functions

### OpenClaw case study

- Publish `docs/OPENCLAW_CASE_STUDY.md` immediately after JCS lands
- Factual, non-marketing — maps specific TRP features to specific OpenClaw failure modes
- This becomes the "why TRP exists" document for newcomers

**Who it unblocks:** Framework maintainers who refuse to adopt formats without standard canonicalization. Security reviewers who need cross-environment hash reproducibility.

**Credibility signal:** "Given these receipts + claims, an independent verifier reproduces the same digests and verdicts."

## v0.7 — Ecosystem Integration

**Design principle:** Make TRP easy to embed without adopting the full reference server. Lead with receipts, not staking.

### Permissive interop kit (Apache-2.0)

- Split out a minimal, permissively-licensed package: receipt schemas, structured claim types, canonicalization helper, verifier skeleton
- BUSL stays on the reference server/settlement implementation
- This is the single biggest adoption unblock — without it, BUSL quietly caps the ecosystem

### OpenTelemetry mapping

- Define TRP ↔ OTel mapping: receipt hash + claim fingerprint as span/event attributes
- Reference exporter: TRP → OTLP
- OTel is where ops and security teams already live — TRP shows up as an evidence layer inside existing traces, not a competing stack

### Canonical HTTP binding

- Minimal REST API: submit claim, verify claim, fetch evidence by digest
- No bespoke wire protocol — boring HTTP that works everywhere
- MCP and A2A adapters remain for agent-native channels

### EvidenceBundle

- Composite evidence type grouping multiple ToolReceipts, external document hashes, and signed attestations
- Makes `_meta` less fragile — receipts can be stored as first-class artifacts referenced by hash

### "TRP for tool marketplaces" profile

- Minimum evidence strength for skill installation
- Required receipt classes for high-risk tools
- Optional witness checks
- Directly motivated by the OpenClaw ClawHub poisoning

**Who it unblocks:** CrewAI, LangGraph, AutoGen, Haystack — frameworks that already support OTel and want exportable audit artifacts. Enterprises who won't touch custom transports but will accept protocol-over-HTTP + OTel.

**Credibility signal:** A one-page integration recipe: "Turn on TRP receipts for tool calls. See them as OTel events. Verify them externally."

## v0.8 — Trust Infrastructure

**Design principle:** Expand verification beyond deterministic replay. TRP becomes a verification ladder: strong replay when possible, provider attestation when not, witness/quorum when the provider isn't trusted.

### Provider signature registry

- Interface for verifiers to discover provider public keys and supported tool versions
- Decentralised: enterprises and communities plug in their own registries
- Required for non-replayable tools where provider attestation is the trust anchor

### Reputation system

- Scoped by ClaimKind (good at tool_output ≠ good at policy_compliance)
- Evidence-strength aware (dual-signed receipts count more than unsigned)
- Requires stronger identity before reputation matters — aligns with signed agent cards

### Witness/quorum verification

- Multiple independent tool providers produce receipts for the same claim
- Disagreement triggers challenge
- Covers the gap where replay is impossible and single-provider trust is insufficient

### Environment attestation

- Tool receipts carry verifiable environment metadata (runtime version, container hash, config fingerprint)
- Aligns with emerging IETF "verifiable provenance" thinking

**Who it unblocks:** Marketplace and regulated workflows where most actions are network calls, API calls, or side effects. Security teams reasoning about "who attested to what" at scale.

**Credibility signal:** A public provider key registry demo: verifiers can reject receipts not signed by recognised tool providers.

## v0.9 — Compliance Profiles

**Design principle:** Stop hand-waving about compliance. Ship profiles that integrators can implement. Lead with evidence/auditability — compliance is downstream.

### Review gate profile

- Certain ClaimKinds must be challenged/verified by a designated verifier role with auditable outcomes
- Standard "human oversight" envelope that TRP feeds — Article 14 alignment

### Log retention and export profile

- How receipts, verification results, and settlements are stored, how long, and how to export for audits
- Article 26 deployer obligation alignment

### "TRP and the AI Act" formal mapping

- Honest, precise, not overclaiming
- Maps Articles 14, 15, 17, 26, and Title IV (Article 50) to specific TRP artifacts
- Clearly states what TRP does NOT provide (risk assessment, conformity assessment, CE marking)

### Incident report message type

- Binds incident claims to receipts with privacy controls
- Supports structured "what went wrong" artifacts for regulated incident reporting

**Who it unblocks:** Healthcare, finance, legal deployments needing explicit human oversight gating and durable logs. Public sector procurement where auditability matters more than model choice.

**Credibility signal:** A compliance profile checklist with reference implementations and example log exports.

## v1.0 — Protocol Stability

**Design principle:** Make TRP safe to build on. Vendors and OSS maintainers can integrate without fear of breaking changes.

### Schema freeze

- Backwards compatibility guarantees for all message types
- Deprecation policy for evolving schemas

### Conformance test suite

- Reference test vectors + expected verdicts
- Third-party verifiers can run the suite and prove interoperability

### Federation

- Cross-org receipt verification and settlement portability
- Only compelling when agents cross organisational boundaries

### IETF informational draft

- Frame TRP as "evidence and claim interoperability" — not "AI reasoning correctness"
- Adjacent to existing IETF work on dispute protocols and verifiable provenance

**Who it unblocks:** Agent marketplaces, third-party verifiers, cross-org agent workflows. Standards-adjacent adopters who need stability.

**Credibility signal:** An external verifier suite run by third parties passing conformance tests.

---

## Strategic principles

1. **Lead with receipts, not staking.** The intro story is "every tool call gets a tamper-evident receipt." Staking is a marketplace profile, not the onboarding requirement.
2. **Don't compete with observability.** LangSmith, Arize, Langfuse, W&B Weave own tracing. TRP adds cryptographic accountability artifacts to their traces.
3. **Permissive interop surface is non-negotiable.** If the only way to use TRP is through BUSL code, adoption is capped. The interop kit must be Apache-2.0.
4. **Compliance is downstream, not the lead.** Evidence and auditability first. AI Act alignment follows naturally once the artifacts exist.
5. **The OpenClaw crisis is the defining case study.** Every positioning conversation opens with "135,000 exposed agent instances with no audit trail."
