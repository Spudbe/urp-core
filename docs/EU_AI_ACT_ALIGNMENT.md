# EU AI Act Alignment

How TRP's capabilities map to EU AI Act requirements. This is a technical mapping, not legal advice.

## Overview

TRP provides structured claim accountability that aligns with the EU AI Act's traceability and documentation requirements for high-risk AI systems. TRP produces auditable, tamper-evident records of what agents claimed, what evidence they provided, whether claims were challenged, and how disputes were resolved.

## Article 14 — Human Oversight

TRP's live demo and structured claims provide human-readable verification results. `render_statement()` auto-generates human-readable summaries from machine-parseable propositions. The web interface at `/.well-known/trp-capability.json` and the SSE-streamed simulation allow human operators to observe the full claim lifecycle in real time: claim submission, challenge, verification, and settlement.

SettlementMessage records provide an auditable trail of outcomes with researcher and challenger balance deltas, enabling human review of dispute resolution.

## Article 15 — Accuracy, Robustness and Cybersecurity

**Tamper evidence:** ToolReceipts include SHA-256 hashes of both inputs (`input_sha256`) and outputs (`output_sha256`). Any modification to the recorded data is detectable by hash comparison.

**Authentication:** JWS signing with Ed25519 provides cryptographic authentication. Evidence strength levels (unsigned, caller_signed, provider_signed, dual_signed) make the trust model explicit. Dual-signed receipts are the strongest — both the caller and the tool provider attest to the record.

**Classification validation:** The ToolReceiptVerifier enforces 6 classification rules that reject contradictory metadata (e.g. a tool claiming to be DETERMINISTIC with WEAK replay, or a tool with EXTERNAL_WRITE side effects claiming STRONG replay). This prevents agents from misrepresenting their evidence quality.

**Replay verification:** For deterministic tools, claims can be verified mechanically by re-running the tool and comparing output hashes. No trust in the claiming agent is required.

## Article 17 — Quality Management System

TRP produces three categories of auditable records:

| Record type | What it proves | TRP type |
|-------------|---------------|----------|
| Tool receipts | What tool was called, with what inputs, and what output was produced | ToolReceipt |
| Structured claims | What was asserted, in machine-parseable form | StructuredClaim |
| Settlement records | How the dispute was resolved and what economic consequences followed | SettlementMessage |

All records are serialisable to JSON via `to_dict()`, hashable, and optionally signable with Ed25519 JWS.

## What TRP Provides

| EU AI Act requirement | TRP feature |
|----------------------|-------------|
| Traceability of outputs | ToolReceipt with input/output hashes and timestamps |
| Documentation of decisions | SettlementMessage with outcome, deltas, and notes |
| Human-readable explanation | `render_statement()` for StructuredClaim propositions |
| Tamper detection | SHA-256 hashes on all receipts, replay verification |
| Authentication | Ed25519 JWS signing with evidence strength classification |
| Audit trail | Full claim lifecycle: claim → challenge → verify → settle |

## What TRP Does NOT Provide

- **Risk assessment** — TRP does not classify AI systems by risk level.
- **Conformity assessment** — TRP does not perform or document conformity assessments.
- **CE marking** — TRP has no relationship to product certification.
- **Fundamental rights impact assessment** — TRP does not assess societal impact.
- **Bias detection** — TRP verifies tool outputs, not fairness or representativeness.
- **Data governance** — TRP does not manage training data quality or provenance.

TRP is an audit trail mechanism for inter-agent communication, not a compliance platform. It provides the evidentiary infrastructure that a compliance system could build on.
