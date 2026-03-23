# Getting Started with TRP

From zero to verified receipt in 5 minutes.

## Install

```bash
pip install trp-core
```

## Create a receipt for a tool call

Every tool call can produce a ToolReceipt — a signed, hash-verified record of what happened.

```python
from trp import ToolReceipt

receipt = ToolReceipt(
    receipt_id="",  # auto-generated
    tool_name="compute_fibonacci",
    tool_version="1.0.0",
    provider_name="my_app",
    provider_id="local",
    protocol_family="local_python",
    started_at="2026-03-23T12:00:00Z",
    input_inline={"n": 10},
    output_inline={"input": 10, "result": 55, "algorithm": "iterative"},
)

print(receipt.input_sha256)   # sha256:...
print(receipt.output_sha256)  # sha256:...
```

The hashes are computed automatically using RFC 8785 JCS canonicalization.

## Verify a receipt by replaying the tool

If the tool is deterministic, TRP can re-run it and compare the output hash:

```python
from trp import ToolReceiptVerifier
from trp.deterministic_tools import BUILTIN_TOOLS

verifier = ToolReceiptVerifier()
for name, fn in BUILTIN_TOOLS.items():
    verifier.register(name, fn)

result = verifier.verify(receipt)
print(result.status)  # verified_exact
print(result.detail)  # "Replay output matches receipt..."
```

## Make a structured claim

A StructuredClaim is a machine-parseable proposition that links to receipt evidence:

```python
from trp import StructuredClaim, ToolOutputEquals

claim = StructuredClaim(
    sc_version="0.6",
    kind="tool_output",
    proposition=ToolOutputEquals(
        tool_name="compute_fibonacci",
        input={"n": 10},
        expected_output={"input": 10, "result": 55, "algorithm": "iterative"},
    ),
)

print(claim.fingerprint())       # sha256:... (stable hash)
print(claim.render_statement())  # "compute_fibonacci(n=10) produces..."
```

## Match a claim against evidence

```python
from trp import match_claim

result = match_claim(claim, [receipt])
print(result.overall_status)  # PropStatus.TRUE
print(result.summary)         # "Claim verified: all propositions matched by evidence."
```

Three possible outcomes:
- **TRUE** — evidence mechanically confirms the proposition
- **FALSE** — evidence contradicts it
- **UNKNOWN** — insufficient evidence for mechanical verification

## Use the CLI

```bash
trp verify examples/fibonacci_receipt.json
trp match examples/structured_claim.json examples/fibonacci_receipt.json
trp hash examples/fibonacci_receipt.json
```

## Use the REST API

```bash
# Verify a receipt
curl -X POST http://localhost:8000/api/verify \
  -H "Content-Type: application/json" \
  -d @examples/fibonacci_receipt.json

# Match a claim against evidence
curl -X POST http://localhost:8000/api/match \
  -H "Content-Type: application/json" \
  -d '{"claim": {...}, "evidence": [...]}'
```

## Add receipts to MCP tool calls

```python
from trp.mcp_adapter import wrap_tool_call

receipt = wrap_tool_call(
    tool_name="my_tool",
    tool_version="1.0.0",
    inputs={"query": "example"},
    output={"result": "data"},
    nondeterminism="deterministic",
    side_effects="none",
    replay="strong",
)
# Attach to MCP CallToolResult via _meta["trp:tool_receipt"]
```

## Next steps

- [Spec](../SPEC.md) — full protocol specification
- [Examples](../examples/) — real JSON artifacts
- [Conformance](../conformance/) — test vectors for implementers
- [OpenClaw Case Study](OPENCLAW_CASE_STUDY.md) — why agent accountability matters
