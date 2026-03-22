# Positioning

## The Problem

Agents can invoke tools through MCP and discover each other through A2A, but neither protocol provides a mechanism for one agent to prove a claim to another or for a receiving agent to challenge it. When Agent A tells Agent B that a dataset contains no PII, or that a calculation is correct, Agent B has no structured way to demand evidence, verify it, or impose a cost on Agent A for being wrong. The receiving agent must either trust the claim or discard it. There is no middle ground.

This gap matters in enterprise and regulated environments. The EU AI Act requires that high-risk AI systems provide traceability and accountability for their outputs. Financial services regulators expect audit trails showing why a decision was made and what evidence supported it. In multi-agent systems where one agent's output becomes another agent's input, there is currently no standard way to record who claimed what, what proof was offered, whether it was challenged, and how the dispute was resolved. Without this, accountability stops at the boundary between agents.

## Where URP Sits

| Name | What it solves | What it does not solve |
|------|---------------|----------------------|
| **MCP** (Model Context Protocol) | Standardised tool invocation — lets an agent call external tools and receive structured results. | Does not verify whether the tool's output is correct, or let the caller challenge it. |
| **A2A** (Agent-to-Agent Protocol) | Agent discovery and task delegation — lets agents find each other and hand off work. | Does not attach proof or economic commitment to the results of delegated work. |
| **LangGraph / CrewAI** | Agent orchestration — manages multi-step workflows, agent coordination, and state within a single application. | Framework-specific; does not define a wire protocol. No mechanism for cross-framework claim verification or staking. |
| **URP** (Universal Reasoning Protocol) | Claim accountability — structured claim submission with proof references, economic staking, challenge/response evaluation, and settlement. | Does not handle tool invocation, agent discovery, orchestration, identity, or transport. Designed to layer on top of protocols that do. |

## What URP Is Not

- **Not a transport protocol.** URP defines message shapes and interaction flow. It does not specify how messages move between agents. The reference implementation uses WebSockets; a production deployment might use MCP, gRPC, or message queues.
- **Not an orchestration framework.** URP does not manage agent lifecycles, workflow state, or task routing. It handles one concern: whether a claim is backed by evidence and what happens economically if the evidence is wrong.
- **Not an identity system.** Agents are currently identified by plain string names. URP's spec stubs a JWS signing model but does not implement authentication, key management, or DID resolution.
- **Not production-ready.** The reference implementation uses dummy proof hashes, an in-memory ledger, and a hard-coded knowledge base with three facts. It exists to validate the protocol design, not to run in production.

## The Core Claim

URP is built on the thesis that structured accountability produces more reliable agent outputs than trust-based systems. When an agent must back a claim with verifiable evidence — a tool receipt, a signed computation, a reproducible output — and risks losing staked value if the evidence is successfully challenged, the agent has a direct incentive to provide accurate, grounded claims. This is not novel: it is how audit trails, signed receipts, and dispute bonds work in traditional systems. URP applies the same mechanism to inter-agent communication, targeting claims that can be verified by replay, signature, or reproducible output — not claims that require trusting another LLM's opinion.

## Commercial Optionality

URP is published as a protocol draft under the Business Source License 1.1 (BUSL-1.1). The specification and reference implementation are open for community review, feedback, and non-production use. On the change date of 2030-03-21, the license converts automatically to Apache-2.0, making the code freely available for all uses. Before the change date, commercial licensing is available for organisations that want to use URP in production systems, integrate it into commercial products, or build proprietary extensions. This structure allows the protocol to develop in the open while preserving the option to sustain development through commercial agreements.

## Contact

- **Spec feedback:** GitHub Issues on the [urp-core repository](https://github.com/Spudbe/urp-core/issues)
- **Commercial licensing:** GitHub Issues at https://github.com/Spudbe/urp-core/issues
