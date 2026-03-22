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

Interaction Flow
Submission: An agent submits a Claim along with a Stake. The claim references a proof of correctness.

Evaluation: Another agent receives the claim and evaluates it. It returns a Response with one of three decisions:

accept: The claim is valid. The verifier’s stake (if any) is returned and the claimant receives the payment.

reject: The claim is invalid. The claimant’s stake is forfeited to the verifier.

challenge: The responder disputes the claim but cannot definitively accept or reject it. Both stakes are held until a verifier arbitrates.

Verification: One or more verifier agents inspect the claim and the associated proofs. They return Response messages that determine whether the claim is accepted or rejected. The protocol can require a quorum or majority of verifiers.

Settlement: Based on the final decision, funds are transferred. Accepted claims refund the claimant and pay the responder (if there was a challenge). Rejected claims forfeit the claimant’s stake.

Future Directions
The following areas are recognised as necessary for a complete protocol but are deferred beyond v0.2: proof serialisation format, transport protocol bindings, agent identity and signing model (see signing stub above), privacy and encryption, governance and versioning, and the microtransaction settlement layer. Contributions and feedback via GitHub Issues are welcome.

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

## Signing Model (stub)

URP messages SHOULD be signed by the sending agent to ensure authenticity and tamper-evidence. The intended signing model is JSON Web Signatures (JWS) as defined in RFC 7515. Each URPMessage envelope should carry an optional signature field containing a detached JWS signature over the canonical JSON serialisation of the payload. Key management, DID integration, and signature verification workflows are deferred to v0.3. Implementations that do not yet support signing MUST NOT silently accept unsigned messages in security-sensitive contexts.
