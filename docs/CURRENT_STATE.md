# Current State

Snapshot as of 22 March 2026.

## Status

- **Protocol version:** 0.2.0 public draft (v0.3 features built, tag pending)
- **Tests:** 59 passing
- **GitHub issues:** 13 created, all closed
- **Live URL:** https://urp-core-production.up.railway.app
- **CI:** GitHub Actions running pytest on push and PR

## Protocol Types

| Type | Module | Purpose |
|------|--------|---------|
| Claim | urp/core.py | Atomic assertion or request with proof reference, stake, and evidence list |
| ProofReference | urp/core.py | Citation pointer (hash + URI + summary + confidence score) |
| Stake | urp/core.py | Economic commitment attached to claims and challenges |
| Response | urp/core.py | Accept/challenge/reject decision on a claim |
| ToolReceipt | urp/core.py | Verifiable record of a tool call with SHA-256 hashes, replay classification, and evidence strength |
| SettlementMessage | urp/core.py | First-class message recording stake distribution after claim resolution |
| AgentCapability | urp/core.py | Preflight declaration of what an agent can verify, with stake policy and evidence requirements |
| AgentIdentity | urp/core.py | Agent identity (id, name, version) |
| StakePolicy | urp/core.py | Stake requirements for incoming claims |
| JWSSignature | urp/core.py | JWS signature block for future signing support |
| URPMessage | urp/message.py | Versioned envelope wrapping any protocol payload |

## Enums

| Enum | Values |
|------|--------|
| ClaimType | assertion, request |
| Decision | accept, challenge, reject, expired |
| SettlementOutcome | accepted, rejected, expired |
| EvidenceStrength | unsigned, caller_signed, provider_signed, dual_signed |
| NondeterminismClass | deterministic, time_dependent, randomized, model_based, environment_dependent |
| SideEffectClass | none, read_only, external_write, irreversible |
| ReplayClass | none, weak, stateful, strong, witness_only |
| ClaimKind | factual_assertion, tool_output, code_verification, data_integrity, provenance_check, policy_compliance, safety_check |
| EvidenceType | proof_reference, tool_receipt |

## LLM Adapters

| Adapter | Provider | API Key Env Var | Default Model | Dependencies |
|---------|----------|-----------------|---------------|--------------|
| GroqAdapter | Groq | GROQ_API_KEY | llama-3.3-70b-versatile | groq package |
| OllamaAdapter | Ollama (local) | OLLAMA_HOST (optional) | llama3 | stdlib urllib |
| OpenAIAdapter | OpenAI | OPENAI_API_KEY | gpt-4o-mini | stdlib urllib |

## Shared Agent Classes (urp/llm_agents.py)

| Class | Role | Returns |
|-------|------|---------|
| ResearcherLLM | Creates claims with ToolReceipt evidence and dynamic confidence score | Claim |
| ChallengerLLM | Evaluates claims, decides accept or challenge | (Response, reason_string) |
| VerifierLLM | Makes final accept/reject decision | (Response, reason_string) |

## Simulations

| File | Description | API Key Required |
|------|-------------|-----------------|
| simple_simulation.py | Single-process claim/challenge/verify loop | No |
| deterministic_demo.py | Replayable ToolReceipt verification with tampering detection | No |
| llm_simulation.py | Three-scenario LLM-backed simulation (accept, challenge, reject) | GROQ_API_KEY |
| ollama_demo.py | Single-scenario local model demo | Ollama running |
| networked_simulation.py | Multi-agent WebSocket simulation | No |

## Web Server (server.py)

- FastAPI with SSE streaming
- Custom claim input via query parameter
- Background task + queue pattern with 5-second heartbeat for Railway proxy
- GROQ_API_KEY checked at request time, not startup
- Debug endpoint at /debug-env
- Deployed via Dockerfile on Railway

## Specifications

| File | Content |
|------|---------|
| SPEC.md | Protocol spec with message types, interaction flow, error codes, evidence types, signing model, transport adapters, AgentCapability |
| SPEC-v2.md | JSON schemas for all message types |
| ROADMAP.md | v0.2 current state, v0.3 planned, v0.4 future direction |
| CHANGELOG.md | Detailed changelog for v0.2.0 and v0.3.0 |

## Next Build Targets (priority order)

1. **EvidenceBundle** — composite evidence type grouping multiple ToolReceipts and signed attestations
2. **Structured claim format** — replace free-text statements with machine-parseable propositions
3. **JWS signing implementation** — implement the signing model stubbed in SPEC.md
4. **Machine-native reasoning layer** — binary-efficient message encoding for high-throughput agent communication
5. **Privacy and encryption** — selective disclosure, zero-knowledge proof integration
