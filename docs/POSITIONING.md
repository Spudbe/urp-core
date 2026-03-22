# Positioning

## The Problem

Agents now automate research, code generation, and decision-making. They produce assertions like "the patch passes all tests" or "no personal data is present" yet there is no common way for downstream consumers to verify these claims without asking another language model. Agents can be wrong, manipulated, or malicious, and free-form natural language output provides no reliable handle for independent verification.

This gap matters in enterprise and regulated environments. The EU AI Act requires that high-risk AI systems provide traceability and accountability for their outputs. Financial services regulators expect audit trails showing why a decision was made and what evidence supported it. In multi-agent systems where one agent's output becomes another agent's input, there is currently no standard way to record who claimed what, what proof was offered, whether it was challenged, and how the dispute was resolved.

## Where URP Sits

Other initiatives touch adjacent parts of the problem. The IETF [Agentic Integrity Verification Standard (AIVS)](https://www.ietf.org/archive/id/draft-stone-aivs-00.html) describes a portable, self-verifying archive format for AI session logs — a session-level provenance mechanism rather than a claim-level one. Attestix provides DID-based identity, agent cards, delegation, and EU AI Act compliance tooling. A2A added signed agent cards in v0.3, enabling agents to discover each other and authenticate capabilities via JSON Web Signatures. Payment rails like x402 are seeing adoption in agent marketplaces for per-use settlement. None of these provide a general claim-level verification protocol.

| Name | What it solves | What it does not solve |
|------|---------------|----------------------|
| MCP | Standardised tool invocation — lets an agent call external tools and receive structured results. | Does not verify whether the tool's output is correct, or let the caller challenge it. |
| A2A | Agent discovery and task delegation — lets agents find each other and hand off work. Signed agent cards authenticate capabilities. | Does not attach proof or economic commitment to the results of delegated work. |
| [AIVS](https://www.ietf.org/archive/id/draft-stone-aivs-00.html) | Session-level provenance — hash-chained audit logs for complete AI sessions. | Session integrity, not claim-level accountability. No challenge/dispute mechanism. |
| [VCAP](https://datatracker.ietf.org/doc/draft-stone-vcap/) | Verified commerce — escrow, proof-of-delivery, and payment settlement between agents. | Transaction settlement, not general claim verification. Assumes work delivery, not arbitrary assertions. |
| Attestix | DID-based agent identity, credentials, EU AI Act compliance workflows. | Identity attestation, not claim verification. No economic staking or challenge model. |
| LangGraph / CrewAI | Agent orchestration — manages multi-step workflows and coordination. | Framework-specific. No wire protocol for cross-framework claim verification. |
| URP | Claim accountability — structured claim submission with verifiable evidence, economic staking, challenge/response evaluation, and settlement. | Does not handle tool invocation, agent discovery, orchestration, identity, or transport. Designed to layer on top of protocols that do. |

## What URP Is Not

- Not a transport protocol. URP defines message shapes and interaction flow. It does not specify how messages move between agents.
- Not an orchestration framework. URP handles one concern: whether a claim is backed by verifiable evidence and what happens economically if the evidence is challenged.
- Not an identity system. Agents are currently identified by plain string names. URP stubs a JWS signing model but does not implement authentication or key management.
- Not production-ready. The reference implementation uses an in-memory ledger and exists to validate the protocol design.

## The Core Claim

URP is built on the thesis that structured accountability produces more reliable agent outputs than trust-based systems. When an agent must back a claim with verifiable evidence — a tool receipt, a signed computation, a reproducible output — and risks losing staked value if the evidence is successfully challenged, the agent has a direct incentive to provide accurate, grounded claims. This is not novel: it is how audit trails, signed receipts, and dispute bonds work in traditional systems. URP applies the same mechanism to inter-agent communication, targeting claims that can be verified by replay, signature, or reproducible output — not claims that require trusting another LLM opinion.

## Commercial Optionality

URP is published as a protocol draft under the Business Source License 1.1 (BUSL-1.1). The specification and reference implementation are open for community review, feedback, and non-production use. On the change date of 2030-03-21, the license converts automatically to Apache-2.0. Before the change date, commercial licensing is available for organisations that want to use URP in production systems or build proprietary extensions.

## Contact

- Spec feedback: GitHub Issues at https://github.com/Spudbe/urp-core/issues
- Commercial licensing: GitHub Issues at https://github.com/Spudbe/urp-core/issues
