# Design Decisions

Architectural and strategic decisions made during URP development, with rationale.

## Evidence-first pivot

**Decision:** Move from "verify LLM reasoning" to "verify claims backed by receipts, signatures, or reproducible outputs."

**Why:** The original proof model was circular — an LLM generates a claim, hashes its own reasoning as "proof," and another LLM evaluates it. The proof is "the LLM said so." A challenger cannot mechanically verify it without trusting the same class of system that made the claim. This has no accountability. ToolReceipt constrains verification to claims that can be checked by replay or signature, not by asking another LLM.

## ToolReceipt attaches to Claim, not ProofReference

**Decision:** `Claim.evidence` is a `list[ToolReceipt]`. ProofReference does not carry evidence.

**Why:** Cleaner separation of concerns. ProofReference is a citation pointer — it says "here is where the proof lives" (hash + URI + summary). It is metadata about evidence, not evidence itself. ToolReceipt is the actual verifiable record. Mixing them would overload ProofReference with two different roles. The evidence list on Claim also allows multiple receipts per claim.

## BUSL-1.1, not MIT

**Decision:** Licensed under Business Source License 1.1 with change date 2030-03-21, converting to Apache-2.0.

**Why:** Preserves commercial optionality while the protocol is developed. The spec and implementation are open for review, feedback, and non-production use. After the change date, everything becomes Apache-2.0. This allows the protocol to develop in the open while sustaining development through commercial agreements if demand materialises.

## Groq as default, not Anthropic or OpenAI

**Decision:** `GroqAdapter` is the default LLM adapter. OpenAI and Ollama are available but not the default.

**Why:** Groq offers free API keys with generous rate limits, making the demo accessible without payment. Llama models on Groq align with the r/LocalLLaMA audience that cares about open models. The `LLMAdapter` ABC makes the choice provider-agnostic — switching to any adapter is a one-line change.

## Railway Dockerfile, not Railpack

**Decision:** Deploy with a Dockerfile rather than Railway's RAILPACK builder.

**Why:** RAILPACK had environment variable injection timing issues — `GROQ_API_KEY` was not available at startup. The Dockerfile gives full control over the build and runtime environment. The `CMD` uses Python to read `PORT` from the environment, avoiding shell expansion issues.

## AgentCapability separate from A2A agent cards

**Decision:** AgentCapability is a URP-native type, not an extension of A2A agent cards.

**Why:** URP owns claim verification; A2A owns agent discovery. Coupling them would create a dependency on A2A's schema evolution. AgentCapability aligns with A2A's concept (both declare what an agent can do) but is self-contained. An A2A adapter can map between them at the transport layer.

## ClaimKind separate from ClaimType

**Decision:** Added `ClaimKind` enum (7 values) alongside existing `ClaimType` enum (2 values).

**Why:** `ClaimType` is protocol-level intent (`assertion` vs `request`) — it controls how the protocol handles the message. `ClaimKind` is a routing taxonomy (`factual_assertion`, `tool_output`, `code_verification`, etc.) — it controls which agents can verify the claim. Overloading `ClaimType` with routing semantics would break backward compatibility and conflate two different concerns.
