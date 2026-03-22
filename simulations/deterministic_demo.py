"""Deterministic ToolReceipt verification demo.

Demonstrates a claim backed by a genuinely replayable ToolReceipt.
The verifier re-runs the tool, hashes the output, and compares it to the
receipt — no LLM, no trust, no API key required.
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from urp.core import (
    Claim,
    ClaimType,
    EvidenceStrength,
    NondeterminismClass,
    ProofReference,
    ReplayClass,
    SideEffectClass,
    Stake,
    ToolReceipt,
)
from urp.message import URPMessage


# ---------- Deterministic tool ----------

def compute_fibonacci(n: int) -> dict:
    """Pure, deterministic Fibonacci computation. No randomness, no external state."""
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return {"input": n, "result": a, "algorithm": "iterative"}


# ---------- Verification ----------

def verify_tool_receipt(receipt: ToolReceipt) -> bool:
    """Re-run the tool and compare the output hash to the receipt.

    Returns True if the replayed output matches the recorded hash.
    """
    replayed_output = compute_fibonacci(receipt.input_inline["n"])
    replayed_hash = ToolReceipt.make_output_hash(replayed_output)
    return replayed_hash == receipt.output_sha256


# ---------- Demo ----------

def main() -> None:
    print("=" * 60)
    print("  URP Deterministic Verification Demo")
    print("  No LLM, no API key — pure replay verification")
    print("=" * 60)

    # 1. Run the tool
    inputs = {"n": 10}
    output = compute_fibonacci(10)
    print(f"\nTool call: compute_fibonacci({inputs['n']})")
    print(f"Result: {output}")

    # 2. Create a ToolReceipt
    receipt = ToolReceipt(
        receipt_id="",
        tool_name="compute_fibonacci",
        tool_version="1.0.0",
        provider_name="local_python",
        provider_id="urp-demo",
        protocol_family="local_python",
        started_at=datetime.now(timezone.utc).isoformat(),
        side_effect_class=SideEffectClass.NONE,
        nondeterminism_class=NondeterminismClass.DETERMINISTIC,
        replay_class=ReplayClass.STRONG,
        evidence_strength=EvidenceStrength.UNSIGNED,
        input_inline=inputs,
        output_inline=output,
    )

    # 3. Create a Claim backed by the receipt
    proof_hash = hashlib.sha256(json.dumps(output, sort_keys=True).encode()).hexdigest()
    claim = Claim(
        id="demo-claim-001",
        statement="The 10th Fibonacci number is 55",
        type=ClaimType.ASSERTION,
        proof_ref=ProofReference(
            hash=proof_hash,
            location="local://compute_fibonacci",
            summary=f"Fibonacci(10) = {output['result']}",
            confidence_score=1.0,
        ),
        stake=Stake(amount=1.0),
        evidence=[receipt],
    )

    # 4. Print the claim as formatted JSON
    msg = URPMessage("claim", claim, "DeterministicResearcher")
    print("\n--- Claim with ToolReceipt ---")
    print(msg.to_json(compact=False))

    # 5. Verify by replay
    print("\n--- Verification by Replay ---")
    print("Re-running compute_fibonacci with recorded inputs...")
    result = verify_tool_receipt(receipt)
    print(f"Output hash match: {result}")
    print(f"Verdict: {'VERIFIED' if result else 'TAMPERED'}")

    # 6. Tamper with the receipt and verify again
    print("\n--- Tampering Detection ---")
    print("Modifying receipt output to claim Fibonacci(10) = 99...")
    tampered_receipt = ToolReceipt(
        receipt_id=receipt.receipt_id,
        tool_name=receipt.tool_name,
        tool_version=receipt.tool_version,
        provider_name=receipt.provider_name,
        provider_id=receipt.provider_id,
        protocol_family=receipt.protocol_family,
        started_at=receipt.started_at,
        side_effect_class=receipt.side_effect_class,
        nondeterminism_class=receipt.nondeterminism_class,
        replay_class=receipt.replay_class,
        evidence_strength=receipt.evidence_strength,
        input_inline=receipt.input_inline,
        output_inline={"input": 10, "result": 99, "algorithm": "iterative"},
        output_sha256=ToolReceipt.make_output_hash({"input": 10, "result": 99, "algorithm": "iterative"}),
    )
    tampered_result = verify_tool_receipt(tampered_receipt)
    print(f"Output hash match: {tampered_result}")
    print(f"Verdict: {'VERIFIED' if tampered_result else 'TAMPERED — replay detected wrong output'}")

    # 7. Summary
    print(f"\n{'=' * 60}")
    print("  Summary")
    print(f"{'=' * 60}")
    print(f"  Claim:             {claim.statement}")
    print(f"  Evidence strength: {receipt.evidence_strength.value}")
    print(f"  Replay class:      {receipt.replay_class.value}")
    print(f"  Nondeterminism:    {receipt.nondeterminism_class.value}")
    print(f"  Side effects:      {receipt.side_effect_class.value}")
    print(f"  Original receipt:  VERIFIED")
    print(f"  Tampered receipt:  DETECTED")
    print(f"\n  This is what verifiable evidence looks like in URP.")
    print(f"  No LLM opinion. No trust. Just replay and compare.")


if __name__ == "__main__":
    main()
