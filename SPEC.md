Universal Reasoning Protocol – Draft Specification

**Status: Public Draft v0.2 — reference implementation only. Not production-ready. Spec and API subject to change.**

This document describes the Universal Reasoning Protocol (URP), a draft proposal for structured claim accountability between autonomous agents. URP defines message types and interaction patterns that allow agents to submit claims with proof references and economic stakes, and for other agents to evaluate, challenge, or accept those claims.

Overview
URP messages carry structured claims, references to supporting proofs, staked value, and responses. Agents interacting via URP follow a request–response pattern: one agent submits a claim with a stake, other agents evaluate the claim and either accept it, reject it, or challenge it. Verifier agents arbitrate disputes and the protocol defines how staked funds are redistributed based on the outcome.

Core Message Types
Claim
A Claim is an atomic assertion of fact or intent. It includes:

Field	Type	Description
id	string	Unique identifier for the claim.
statement	string or object	The propositional content. In future versions this will be a structured logic object rather than free text.
type	enum('assertion', 'request')	Whether this claim is stating a fact (assertion) or requesting an action or data (request).
proof_ref	string	Reference (e.g. a hash) to an external proof object backing the claim. May be empty.
stake	Stake	The amount of value locked to signal confidence and pay verifiers.

ProofReference
A ProofReference is a pointer to an external proof artifact. URP itself does not mandate a proof format, but it requires a proof to be verifiable and tamper‑evident. A ProofReference includes:

Field	Type	Description
hash	string	Cryptographic hash of the proof data.
location	string	URI where the proof can be retrieved (e.g. IPFS, HTTP).
summary	string	Optional short description of the proof contents.
confidence_score	float	A value between 0.0 and 1.0 representing the submitting agent's confidence in the evidence, where 1.0 is certain and 0.0 is speculative. Optional.

Stake
A Stake signals the sender’s confidence and funds the verification process. It includes:

Field	Type	Description
amount	decimal	Quantity of URP credits locked with the claim.
currency	string	Unit of account (e.g. URC).
refundable	bool	Indicates whether stake is returned upon acceptance or distributed to verifiers.

Response
Responses are returned by evaluating agents and indicate the outcome:

Field	Type	Description
claim_id	string	Identifier of the claim being responded to.
decision	enum('accept', 'reject', 'challenge')	The responder’s decision.
proof_ref	string	Optional proof supporting the decision.
stake	Stake	Stake placed by the responder. Only used when challenging.

SettlementMessage
A SettlementMessage is a first-class protocol message that records the outcome of a claim settlement and the resulting balance changes. It makes settlement auditable and replayable.

| Field | Type | Description |
|-------|------|-------------|
| settlement_id | string | UUID identifying this settlement, auto-assigned if not provided. |
| claim_id | string | The claim this settlement resolves. |
| outcome | enum('accepted', 'rejected', 'expired') | The settlement outcome. |
| researcher_delta | float | Change in researcher balance (positive = gained, negative = lost). |
| challenger_delta | float | Change in challenger balance (positive = gained, negative = lost). |
| timestamp | string | ISO 8601 UTC timestamp of when settlement occurred. |
| notes | string or null | Optional human-readable summary of why this outcome was reached. |

Interaction Flow
Submission: An agent submits a Claim along with a Stake. The claim references a proof of correctness.

Evaluation: Another agent receives the claim and evaluates it. It returns a Response with one of three decisions:

accept: The claim is valid. The verifier’s stake (if any) is returned and the claimant receives the payment.

reject: The claim is invalid. The claimant’s stake is forfeited to the verifier.

challenge: The responder disputes the claim but cannot definitively accept or reject it. Both stakes are held until a verifier arbitrates.

Verification: One or more verifier agents inspect the claim and the associated proofs. They return Response messages that determine whether the claim is accepted or rejected. The protocol can require a quorum or majority of verifiers.

Settlement: Based on the final decision, funds are transferred. Accepted claims refund the claimant and pay the responder (if there was a challenge). Rejected claims forfeit the claimant’s stake.

Future Directions
The following areas are recognised as necessary for a complete protocol but are deferred beyond v0.2: proof serialisation format, transport protocol bindings, agent identity and signing model (see signing stub above), privacy and encryption, governance and versioning, and the microtransaction settlement layer. See [ROADMAP.md](ROADMAP.md) for planned work. Contributions and feedback via GitHub Issues are welcome.

## Error Codes

| Code | Description |
|------|-------------|
| CLAIM_MALFORMED | The claim object is missing required fields or contains invalid types. |
| PROOF_MISSING | The claim references a proof that cannot be retrieved. |
| PROOF_INVALID | The proof hash does not match the retrieved content. |
| STAKE_INSUFFICIENT | The stake amount is below the minimum required by the receiving agent. |
| STAKE_CURRENCY_UNKNOWN | The currency code in the stake is not recognised. |
| UNSUPPORTED_VERSION | The protocol_version in the message envelope is not supported by the receiving agent. |
| AGENT_UNKNOWN | The sender identifier cannot be resolved. |
| CLAIM_DUPLICATE | A claim with the same id has already been submitted. |
| DECISION_INVALID | The response decision value is not one of the accepted enum values. |
| VERIFICATION_TIMEOUT | The verifier did not return a decision within the allowed window. |
| SETTLEMENT_FAILED | The settlement transaction could not be completed. |
| CHALLENGE_EXPIRED | The challenge window closed before a response was submitted. |
| UNSUPPORTED_CLAIM_TYPE | The claim type is not handled by the receiving agent. |

## Evidence Types

URP distinguishes between two levels of evidence. A ProofReference is a pointer — it records a hash, a location, and a summary, but does not itself constitute verifiable proof. An EvidenceType is a structured record that can be mechanically verified without trusting the same agent that made the claim. Claims backed by ToolReceipts are verifiable. Claims backed only by a ProofReference are assertions. URP treats these differently in the challenge/verify flow.

A Claim carries an `evidence` list of zero or more ToolReceipt objects. When present, challengers can verify the claim by replaying tool calls and comparing output hashes, rather than trusting the claiming agent.

### Classification Enums

**EvidenceStrength** — How strongly a ToolReceipt is authenticated.

| Value | Description |
|-------|-------------|
| unsigned | No cryptographic signature attached. |
| caller_signed | Signed by the agent that invoked the tool. |
| provider_signed | Signed by the tool provider. |
| dual_signed | Signed by both caller and provider. |

**NondeterminismClass** — How reproducible a tool call's output is.

| Value | Description |
|-------|-------------|
| deterministic | Same inputs always produce same output. |
| time_dependent | Output varies with wall-clock time. |
| randomized | Output depends on random seed or sampling. |
| model_based | Output depends on a model (e.g. LLM) that may change between invocations. |
| environment_dependent | Output depends on external state (e.g. database, network). |

**SideEffectClass** — What external effects a tool call has.

| Value | Description |
|-------|-------------|
| none | No external effects. |
| read_only | Reads external state but does not modify it. |
| external_write | Writes to an external system. |
| irreversible | Produces effects that cannot be undone. |

**ReplayClass** — How verifiable a tool call is by replay.

| Value | Description |
|-------|-------------|
| none | Cannot be replayed or verified. |
| weak | Can be replayed but output may differ. |
| stateful | Replay requires matching external state. |
| strong | Replay produces identical output. |
| witness_only | Verified by a third-party witness, not by replay. |

### ToolReceipt

A ToolReceipt is the first concrete EvidenceType. It records a tool call with enough metadata for a challenger to verify by replay or signature.

| Field | Type | Description |
|-------|------|-------------|
| receipt_id | string | UUID identifying this receipt, auto-assigned if not provided. |
| tool_name | string | Name of the tool that was called. |
| tool_version | string | Version string of the tool; "unknown" if not available. |
| provider_name | string | Human-readable name of the tool provider. |
| provider_id | string | Identifier for the tool provider. |
| protocol_family | string | Protocol used to invoke the tool (default "local_python"). |
| started_at | string | ISO 8601 UTC timestamp of when the tool was called. |
| status | string | Outcome of the tool call (default "succeeded"). |
| side_effect_class | SideEffectClass | What external effects the tool call has. |
| nondeterminism_class | NondeterminismClass | How reproducible the output is. |
| input_inline | object | The inputs passed to the tool, JSON-serialisable. |
| input_sha256 | string | SHA-256 hash of canonical JSON of inputs, prefixed with "sha256:". |
| output_inline | object | The output returned by the tool, JSON-serialisable. |
| output_sha256 | string | SHA-256 hash of canonical JSON of output, prefixed with "sha256:". |
| replay_class | ReplayClass | How verifiable the call is by replay. |
| evidence_strength | EvidenceStrength | How strongly the receipt is authenticated. |
| signature | string or null | Optional JWS signature over the canonical receipt; null until signing is implemented. |

## Signing Model (stub)

URP messages SHOULD be signed by the sending agent to ensure authenticity and tamper-evidence. The intended signing model is JSON Web Signatures (JWS) as defined in RFC 7515. Each URPMessage envelope should carry an optional signature field containing a detached JWS signature over the canonical JSON serialisation of the payload. Key management, DID integration, and signature verification workflows are deferred to v0.3. Implementations that do not yet support signing MUST NOT silently accept unsigned messages in security-sensitive contexts.

## Transport Adapters

URP is transport-agnostic. The reference implementation uses WebSockets. Production deployments should use existing agent communication protocols as the transport layer rather than building new transport infrastructure.

### MCP Transport Adapter (spec-only, not yet implemented)

URP messages can be carried over the Model Context Protocol (MCP) by wrapping them as MCP tool calls. This allows URP claim accountability to be added to any MCP-connected agent workflow without a separate transport layer.

The mapping is:

| URP operation | MCP equivalent |
|---------------|----------------|
| Submit claim | Call tool: urp_submit_claim, arguments: {claim: ClaimMessage} |
| Challenge claim | Call tool: urp_challenge_claim, arguments: {claim_id: str, response: ResponseMessage} |
| Verify claim | Call tool: urp_verify_claim, arguments: {claim_id: str, response: ResponseMessage} |
| Settle claim | Call tool: urp_settle_claim, arguments: {settlement: SettlementMessage} |
| Get capability | Call tool: urp_get_capability, returns: AgentCapability |

An MCP server implementing URP would expose these five tools. Any MCP-connected agent can then participate in the URP claim lifecycle without a direct WebSocket connection.

This adapter is not yet implemented. It is described here to establish the intended integration path and to invite implementation contributions. See [ROADMAP.md](ROADMAP.md) for planned work.

### A2A Transport Adapter (spec-only, not yet implemented)

URP messages can also be carried over the Agent-to-Agent Protocol (A2A) as task artifacts. A URP claim becomes an A2A task; the response and settlement become task artifacts returned by the delegated agent. A2A's signed agent cards can carry AgentCapability declarations, enabling capability discovery before claim submission.

This adapter is not yet implemented.

## AgentCapability

AgentCapability is a preflight declaration that lets an agent advertise what kinds of claims it can verify, what evidence it accepts, and what stake policy it enforces. It is used for routing — a sender can check an agent's capability before submitting a claim, avoiding wasted stakes on agents that cannot handle the claim type.

AgentCapability is not part of claim settlement. It is a discovery mechanism that aligns with A2A agent discovery (where signed agent cards declare capabilities) without coupling URP to A2A transport.

### ClaimType vs ClaimKind

**ClaimType** is the protocol-level intent: `assertion` (stating a fact) or `request` (asking for data/action). It controls how the protocol handles the message.

**ClaimKind** is the routable verification category: what domain the claim belongs to. An agent that can verify `tool_output` claims may not be able to verify `policy_compliance` claims. ClaimKind enables routing without overloading ClaimType.

### ClaimKind

| Value | Description |
|-------|-------------|
| factual_assertion | A claim about a fact that can be checked against reference data. |
| tool_output | A claim backed by the output of a tool call. |
| code_verification | A claim about code correctness (tests pass, no vulnerabilities). |
| data_integrity | A claim about data completeness, consistency, or format. |
| provenance_check | A claim about the origin or chain of custody of data. |
| policy_compliance | A claim that an action or output meets a specific policy. |
| safety_check | A claim that content is safe or meets safety criteria. |

### EvidenceType

| Value | Description |
|-------|-------------|
| proof_reference | A ProofReference pointer (hash + URI + summary). |
| tool_receipt | A ToolReceipt with verifiable inputs, outputs, and hashes. |

### AgentIdentity

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier for the agent. |
| name | string | Human-readable name. |
| version | string | Agent software version string. |

### StakePolicy

| Field | Type | Description |
|-------|------|-------------|
| required | bool | Whether a stake must be attached (default false). |
| minimum_amount | float | Minimum stake amount accepted (default 0.0). |
| currency | string | Currency unit for stakes (default "credits"). |

### JWSSignature

| Field | Type | Description |
|-------|------|-------------|
| protected | string | Base64url-encoded protected header. |
| signature | string | Base64url-encoded signature value. |
| header | object or null | Optional unprotected header parameters. |

### AgentCapability Fields

| Field | Type | Description |
|-------|------|-------------|
| protocol_version | string | URP protocol version this declaration targets. |
| agent | AgentIdentity | Identity of the declaring agent. |
| supported_claim_types | list[ClaimType] | ClaimType values this agent handles. |
| supported_claim_kinds | list[ClaimKind] | ClaimKind values this agent can verify. |
| accepted_evidence_types | list[EvidenceType] | EvidenceType values this agent accepts. |
| minimum_evidence_strength | EvidenceStrength | Weakest evidence strength this agent will consider. |
| stake_policy | StakePolicy | Stake requirements for incoming claims. |
| compatible_protocol_versions | list[string] | Protocol versions this agent supports. |
| expires_at | string or null | Optional ISO 8601 expiry timestamp. |
| refresh_url | string or null | Optional URL to fetch an updated declaration. |
| signatures | list[JWSSignature] or null | Optional JWS signatures over this declaration. |
| metadata | object or null | Optional provider-specific metadata. |

All list fields (supported_claim_types, supported_claim_kinds, accepted_evidence_types, compatible_protocol_versions) must contain at least one element.

### Example

```json
{
  "protocol_version": "0.3.0",
  "agent": { "id": "verifier-001", "name": "FactChecker", "version": "1.0.0" },
  "supported_claim_types": ["assertion"],
  "supported_claim_kinds": ["factual_assertion", "tool_output"],
  "accepted_evidence_types": ["tool_receipt"],
  "minimum_evidence_strength": "unsigned",
  "stake_policy": { "required": true, "minimum_amount": 0.1, "currency": "URC" },
  "compatible_protocol_versions": ["0.2.0", "0.3.0"]
}
```
