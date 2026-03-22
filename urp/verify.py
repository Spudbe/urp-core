"""ToolReceipt verification engine.

Provides ToolReceiptVerifier — a registry of deterministic tool functions
that can replay a ToolReceipt and mechanically verify its output hash.
No LLM, no trust, no API key required.

Typical usage:

    from urp.verify import ToolReceiptVerifier

    verifier = ToolReceiptVerifier()
    verifier.register("compute_fibonacci", compute_fibonacci)
    result = verifier.verify(receipt)
    assert result.status == VerificationStatus.VERIFIED_EXACT
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from urp.core import NondeterminismClass, ReplayClass, SideEffectClass, ToolReceipt


class VerificationStatus(Enum):
    """Outcome of a ToolReceipt verification attempt."""
    VERIFIED_EXACT = "verified_exact"
    OUTPUT_HASH_MISMATCH = "output_hash_mismatch"
    INPUT_HASH_MISMATCH = "input_hash_mismatch"
    NOT_REPLAYABLE = "not_replayable"
    TOOL_NOT_REGISTERED = "tool_not_registered"
    REPLAY_ERROR = "replay_error"
    CLASSIFICATION_INVALID = "classification_invalid"


@dataclass
class VerificationResult:
    """Structured result of a ToolReceipt verification.

    Attributes:
        status: The verification outcome.
        receipt_id: The receipt that was verified.
        expected_output_hash: The output_sha256 recorded in the receipt.
        actual_output_hash: The hash of the replayed output, if replay was attempted.
        detail: Human-readable explanation of the result.
    """
    status: VerificationStatus
    receipt_id: str
    expected_output_hash: str
    actual_output_hash: Optional[str] = None
    detail: str = ""

    def to_dict(self) -> dict:
        """Serialise to a plain dict."""
        d: dict = {
            "status": self.status.value,
            "receipt_id": self.receipt_id,
            "expected_output_hash": self.expected_output_hash,
        }
        if self.actual_output_hash is not None:
            d["actual_output_hash"] = self.actual_output_hash
        if self.detail:
            d["detail"] = self.detail
        return d


# Type alias for a registered deterministic tool function.
# The function takes the input_inline dict and returns an output dict.
DeterministicToolFn = Callable[[dict], dict]


class ToolReceiptVerifier:
    """Registry-based verifier for deterministic ToolReceipts.

    Register tool functions by name, then call verify() with a ToolReceipt.
    The verifier will:

    1. Validate that the receipt's classification is internally consistent
       (e.g. DETERMINISTIC + STRONG is valid; DETERMINISTIC + WEAK is not).
    2. Recompute input_sha256 from input_inline and confirm it matches.
    3. Look up the tool function by tool_name in the registry.
    4. Replay the tool with the receipt's input_inline.
    5. Hash the replayed output and compare to output_sha256.

    Args:
        strict: If True (default), reject receipts with inconsistent
            classification (e.g. DETERMINISTIC but WEAK replay). If False,
            log a warning but continue with verification.
    """

    def __init__(self, strict: bool = True) -> None:
        self._registry: dict[str, DeterministicToolFn] = {}
        self._strict = strict

    def register(self, tool_name: str, fn: DeterministicToolFn) -> None:
        """Register a deterministic tool function for replay verification.

        Args:
            tool_name: The tool_name value that receipts will carry.
            fn: A callable that accepts a dict (input_inline) and returns
                a dict (the expected output).

        Raises:
            ValueError: If tool_name is empty.
        """
        if not tool_name:
            raise ValueError("tool_name must not be empty")
        self._registry[tool_name] = fn

    def unregister(self, tool_name: str) -> None:
        """Remove a tool from the registry.

        Args:
            tool_name: The tool to remove.

        Raises:
            KeyError: If tool_name is not registered.
        """
        del self._registry[tool_name]

    @property
    def registered_tools(self) -> list[str]:
        """Return a sorted list of registered tool names."""
        return sorted(self._registry.keys())

    def _validate_classification(self, receipt: ToolReceipt) -> Optional[VerificationResult]:
        """Check that the receipt's classification fields are internally consistent.

        Returns a VerificationResult with CLASSIFICATION_INVALID if there is
        an inconsistency, or None if the classification is valid.

        Rules:
        - DETERMINISTIC + (WEAK | NONE) is contradictory.
        - MODEL_BASED + STRONG is contradictory.
        - RANDOMIZED + STRONG is contradictory.
        - TIME_DEPENDENT + STRONG is contradictory.
        - ENVIRONMENT_DEPENDENT + STRONG is contradictory.
        - Any side_effect_class other than NONE with STRONG replay is
          contradictory (side effects make replay unsafe or irreproducible).
        """
        # A DETERMINISTIC receipt should have STRONG replay, not WEAK or NONE.
        if (
            receipt.nondeterminism_class == NondeterminismClass.DETERMINISTIC
            and receipt.replay_class in (ReplayClass.WEAK, ReplayClass.NONE)
        ):
            return VerificationResult(
                status=VerificationStatus.CLASSIFICATION_INVALID,
                receipt_id=receipt.receipt_id,
                expected_output_hash=receipt.output_sha256,
                detail=(
                    f"Inconsistent classification: nondeterminism_class is "
                    f"{receipt.nondeterminism_class.value} but replay_class is "
                    f"{receipt.replay_class.value}. Deterministic tools should "
                    f"have replay_class STRONG or STATEFUL."
                ),
            )

        # Non-deterministic tools should not claim STRONG replay.
        _no_strong = (
            NondeterminismClass.MODEL_BASED,
            NondeterminismClass.RANDOMIZED,
            NondeterminismClass.TIME_DEPENDENT,
            NondeterminismClass.ENVIRONMENT_DEPENDENT,
        )
        if (
            receipt.nondeterminism_class in _no_strong
            and receipt.replay_class == ReplayClass.STRONG
        ):
            return VerificationResult(
                status=VerificationStatus.CLASSIFICATION_INVALID,
                receipt_id=receipt.receipt_id,
                expected_output_hash=receipt.output_sha256,
                detail=(
                    f"Inconsistent classification: nondeterminism_class is "
                    f"{receipt.nondeterminism_class.value} but replay_class is "
                    f"{receipt.replay_class.value}. Non-deterministic tools "
                    f"cannot guarantee identical replay output."
                ),
            )

        # Tools with side effects should not claim STRONG replay.
        if (
            receipt.side_effect_class != SideEffectClass.NONE
            and receipt.replay_class == ReplayClass.STRONG
        ):
            return VerificationResult(
                status=VerificationStatus.CLASSIFICATION_INVALID,
                receipt_id=receipt.receipt_id,
                expected_output_hash=receipt.output_sha256,
                detail=(
                    f"Inconsistent classification: side_effect_class is "
                    f"{receipt.side_effect_class.value} but replay_class is "
                    f"{receipt.replay_class.value}. Tools with side effects "
                    f"cannot safely guarantee deterministic replay."
                ),
            )

        return None

    def verify(self, receipt: ToolReceipt) -> VerificationResult:
        """Verify a ToolReceipt by replaying the registered tool function.

        Args:
            receipt: The ToolReceipt to verify.

        Returns:
            A VerificationResult indicating the outcome.
        """
        # 1. Validate classification consistency.
        classification_error = self._validate_classification(receipt)
        if classification_error is not None:
            if self._strict:
                return classification_error
            # In non-strict mode, we note it but continue.

        # 2. Check that the receipt is replayable.
        if receipt.replay_class in (ReplayClass.NONE, ReplayClass.WITNESS_ONLY):
            return VerificationResult(
                status=VerificationStatus.NOT_REPLAYABLE,
                receipt_id=receipt.receipt_id,
                expected_output_hash=receipt.output_sha256,
                detail=(
                    f"Receipt replay_class is {receipt.replay_class.value}; "
                    f"replay verification is not possible."
                ),
            )

        # 3. Verify input hash integrity.
        recomputed_input_hash = ToolReceipt.make_input_hash(receipt.input_inline)
        if recomputed_input_hash != receipt.input_sha256:
            return VerificationResult(
                status=VerificationStatus.INPUT_HASH_MISMATCH,
                receipt_id=receipt.receipt_id,
                expected_output_hash=receipt.output_sha256,
                detail=(
                    f"Input hash mismatch: receipt claims {receipt.input_sha256} "
                    f"but recomputed hash is {recomputed_input_hash}."
                ),
            )

        # 4. Look up the tool in the registry.
        fn = self._registry.get(receipt.tool_name)
        if fn is None:
            return VerificationResult(
                status=VerificationStatus.TOOL_NOT_REGISTERED,
                receipt_id=receipt.receipt_id,
                expected_output_hash=receipt.output_sha256,
                detail=f"Tool '{receipt.tool_name}' is not in the verifier registry.",
            )

        # 5. Replay the tool.
        try:
            replayed_output = fn(receipt.input_inline)
        except Exception as exc:
            return VerificationResult(
                status=VerificationStatus.REPLAY_ERROR,
                receipt_id=receipt.receipt_id,
                expected_output_hash=receipt.output_sha256,
                detail=f"Replay raised {type(exc).__name__}: {exc}",
            )

        # 6. Hash the replayed output and compare.
        actual_hash = ToolReceipt.make_output_hash(replayed_output)
        if actual_hash == receipt.output_sha256:
            return VerificationResult(
                status=VerificationStatus.VERIFIED_EXACT,
                receipt_id=receipt.receipt_id,
                expected_output_hash=receipt.output_sha256,
                actual_output_hash=actual_hash,
                detail="Replayed output hash matches receipt.",
            )
        else:
            return VerificationResult(
                status=VerificationStatus.OUTPUT_HASH_MISMATCH,
                receipt_id=receipt.receipt_id,
                expected_output_hash=receipt.output_sha256,
                actual_output_hash=actual_hash,
                detail=(
                    f"Output hash mismatch: receipt claims "
                    f"{receipt.output_sha256} but replay produced {actual_hash}."
                ),
            )

    def verify_claim(self, claim) -> BatchVerificationResult:
        """Verify all ToolReceipts in a Claim's evidence list.

        Returns a summary result indicating whether all receipts verified,
        some failed, or none were present.

        Args:
            claim: A Claim object with an ``evidence`` list of ToolReceipts.

        Returns:
            A BatchVerificationResult summarising the outcomes.
        """
        if not claim.evidence:
            return BatchVerificationResult(
                claim_id=claim.id,
                results=[],
                all_verified=False,
                summary="No evidence attached to claim.",
            )

        results = [self.verify(receipt) for receipt in claim.evidence]
        all_verified = all(
            r.status == VerificationStatus.VERIFIED_EXACT for r in results
        )
        verified_count = sum(
            1 for r in results if r.status == VerificationStatus.VERIFIED_EXACT
        )
        total = len(results)

        if all_verified:
            summary = f"All {total} receipt(s) verified by replay."
        else:
            failed = total - verified_count
            summary = f"{verified_count}/{total} verified, {failed} failed."

        return BatchVerificationResult(
            claim_id=claim.id,
            results=results,
            all_verified=all_verified,
            summary=summary,
        )


@dataclass
class BatchVerificationResult:
    """Summary result of verifying all receipts in a Claim.

    Attributes:
        claim_id: The claim that was verified.
        results: Individual VerificationResult for each receipt.
        all_verified: True only if every receipt has VERIFIED_EXACT status.
        summary: Human-readable summary of the batch outcome.
    """
    claim_id: str
    results: list[VerificationResult]
    all_verified: bool
    summary: str

    def to_dict(self) -> dict:
        """Serialise to a plain dict."""
        return {
            "claim_id": self.claim_id,
            "results": [r.to_dict() for r in self.results],
            "all_verified": self.all_verified,
            "summary": self.summary,
        }
