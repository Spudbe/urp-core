Universal Reasoning Protocol – Draft Specification
Status: Draft

This document describes the first draft of the Universal Reasoning Protocol (URP). The goal of URP is to enable autonomous agents to exchange structured reasoning, verify each other’s claims and settle payments based on the outcome. The protocol is designed for machine‑to‑machine communication and is not intended to be read by humans during normal operation.

Overview
URP messages carry logical statements (“claims”), references to supporting proofs, staked value and responses. Agents interacting via URP follow a request–response pattern: one agent submits a claim with a stake, other agents evaluate the claim and either accept it, reject it or challenge it. Verifier agents arbitrate disputes and unlock the staked funds accordingly.

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
This draft omits many details, including:

Proof format and logic representation (symbolic logic, embeddings, etc.).

Network transport and message serialization.

Reputation and identity management.

Governance and extension mechanisms.

Privacy and encryption features.

These topics will be addressed in subsequent versions of the specification.
