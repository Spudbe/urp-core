"""Tests for trp/verify.py and trp/deterministic_tools.py.

Includes deterministic hash test vectors that catch serialisation drift.
"""

import pytest

from trp.core import (
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
from trp.deterministic_tools import (
    BUILTIN_TOOLS,
    compute_factorial,
    compute_fibonacci,
    compute_sha256,
    math_eval,
)
from trp.verify import (
    BatchVerificationResult,
    ToolReceiptVerifier,
    VerificationResult,
    VerificationStatus,
)


# ---------- Helpers ----------

def _make_receipt(
    tool_name: str = "compute_fibonacci",
    input_inline: dict | None = None,
    output_inline: dict | None = None,
    replay_class: ReplayClass = ReplayClass.STRONG,
    nondeterminism_class: NondeterminismClass = NondeterminismClass.DETERMINISTIC,
    side_effect_class: SideEffectClass = SideEffectClass.NONE,
    evidence_strength: EvidenceStrength = EvidenceStrength.UNSIGNED,
    output_sha256: str = "",
    input_sha256: str = "",
) -> ToolReceipt:
    """Build a ToolReceipt with sensible defaults for testing."""
    if input_inline is None:
        input_inline = {"n": 10}
    if output_inline is None:
        output_inline = {"input": 10, "result": 55, "algorithm": "iterative"}
    return ToolReceipt(
        receipt_id="test-receipt-001",
        tool_name=tool_name,
        tool_version="1.0.0",
        provider_name="test",
        provider_id="test-provider",
        protocol_family="local_python",
        started_at="2026-03-22T00:00:00Z",
        side_effect_class=side_effect_class,
        nondeterminism_class=nondeterminism_class,
        replay_class=replay_class,
        evidence_strength=evidence_strength,
        input_inline=input_inline,
        output_inline=output_inline,
        output_sha256=output_sha256,
        input_sha256=input_sha256,
    )


def _make_verifier() -> ToolReceiptVerifier:
    """Build a verifier with all built-in tools registered."""
    v = ToolReceiptVerifier()
    for name, fn in BUILTIN_TOOLS.items():
        v.register(name, fn)
    return v


# ==========================================================================
# Hash test vectors — these MUST remain stable across releases.
# If canonical JSON serialisation changes, these will break on purpose.
# ==========================================================================

class TestHashVectors:
    """Deterministic hash test vectors for ToolReceipt hashing.

    These use RFC 8785 JCS canonicalization, then SHA-256 hex digest
    prefixed with "sha256:".
    """

    def test_fibonacci_input_hash(self):
        """input_inline = {"n": 10} → canonical: {"n":10}"""
        h = ToolReceipt.make_input_hash({"n": 10})
        assert h == "sha256:3ff6698e101869f36e088516c6c0ca6495c40c0abdae72f6e4d124610dace7b0"

    def test_fibonacci_output_hash(self):
        """output = {"algorithm":"iterative","input":10,"result":55}"""
        h = ToolReceipt.make_output_hash(
            {"input": 10, "result": 55, "algorithm": "iterative"}
        )
        assert h == "sha256:5a8b9c743b28631ed8a5f815c092daafbe690ba091810f6ac22e497c06498e26"

    def test_fibonacci_tampered_output_hash(self):
        """Tampered: result=99 instead of 55."""
        h = ToolReceipt.make_output_hash(
            {"input": 10, "result": 99, "algorithm": "iterative"}
        )
        assert h == "sha256:df6b9dff088fd0ab56424fa329f3a4c76892298371207bf0bdacc943dd87e57e"

    def test_factorial_input_hash(self):
        """input_inline = {"n": 5} → canonical: {"n":5}"""
        h = ToolReceipt.make_input_hash({"n": 5})
        assert h == "sha256:11d0a8967009cbcdf468f09e5b09e73e7119b528c35a0e0b23f2ae052786b8fa"

    def test_factorial_output_hash(self):
        """output = {"algorithm":"iterative","input":5,"result":120}"""
        h = ToolReceipt.make_output_hash(
            {"input": 5, "result": 120, "algorithm": "iterative"}
        )
        assert h == "sha256:99c0a3ce03411a50a6015b5e32bb67e4cbf88179dfc486917c528488d492fef3"

    def test_sha256_tool_output_hash(self):
        """compute_sha256({"data": "hello"}) output hash."""
        output = compute_sha256({"data": "hello"})
        h = ToolReceipt.make_output_hash(output)
        # This is stable because SHA-256 of "hello" is deterministic
        # and canonical JSON sorting is stable.
        assert h.startswith("sha256:")
        assert len(h) == 71  # "sha256:" + 64 hex chars

    def test_math_eval_output_hash(self):
        """math_eval({"expression": "2 + 3"}) output hash."""
        output = math_eval({"expression": "2 + 3"})
        assert output == {"expression": "2 + 3", "result": 5, "algorithm": "ast_eval"}
        h = ToolReceipt.make_output_hash(output)
        assert h.startswith("sha256:")

    def test_hash_is_order_independent(self):
        """Keys in different insertion order must produce the same hash."""
        h1 = ToolReceipt.make_output_hash(
            {"result": 55, "input": 10, "algorithm": "iterative"}
        )
        h2 = ToolReceipt.make_output_hash(
            {"algorithm": "iterative", "input": 10, "result": 55}
        )
        assert h1 == h2

    def test_empty_dict_hash(self):
        """Empty dict hash must be stable."""
        h = ToolReceipt.make_input_hash({})
        assert h == "sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"  # sha256 of "{}"


# ==========================================================================
# ToolReceiptVerifier tests
# ==========================================================================

class TestToolReceiptVerifier:
    """Core verifier behaviour."""

    def test_verified_exact_fibonacci(self):
        v = _make_verifier()
        receipt = _make_receipt()
        result = v.verify(receipt)
        assert result.status == VerificationStatus.VERIFIED_EXACT
        assert result.actual_output_hash == result.expected_output_hash

    def test_hash_mismatch_on_tampered_output(self):
        v = _make_verifier()
        receipt = _make_receipt(
            output_inline={"input": 10, "result": 99, "algorithm": "iterative"},
        )
        result = v.verify(receipt)
        assert result.status == VerificationStatus.OUTPUT_HASH_MISMATCH
        assert result.actual_output_hash != result.expected_output_hash

    def test_tool_not_registered(self):
        v = ToolReceiptVerifier()  # empty registry
        receipt = _make_receipt()
        result = v.verify(receipt)
        assert result.status == VerificationStatus.TOOL_NOT_REGISTERED
        assert "compute_fibonacci" in result.detail

    def test_not_replayable_none(self):
        v = _make_verifier()
        receipt = _make_receipt(
            replay_class=ReplayClass.NONE,
            nondeterminism_class=NondeterminismClass.RANDOMIZED,
        )
        result = v.verify(receipt)
        assert result.status == VerificationStatus.NOT_REPLAYABLE

    def test_not_replayable_witness_only(self):
        v = _make_verifier()
        receipt = _make_receipt(
            replay_class=ReplayClass.WITNESS_ONLY,
            nondeterminism_class=NondeterminismClass.ENVIRONMENT_DEPENDENT,
        )
        result = v.verify(receipt)
        assert result.status == VerificationStatus.NOT_REPLAYABLE

    def test_classification_invalid_deterministic_weak(self):
        v = _make_verifier()
        receipt = _make_receipt(
            nondeterminism_class=NondeterminismClass.DETERMINISTIC,
            replay_class=ReplayClass.WEAK,
        )
        result = v.verify(receipt)
        assert result.status == VerificationStatus.CLASSIFICATION_INVALID

    def test_classification_invalid_model_based_strong(self):
        v = _make_verifier()
        receipt = _make_receipt(
            nondeterminism_class=NondeterminismClass.MODEL_BASED,
            replay_class=ReplayClass.STRONG,
        )
        result = v.verify(receipt)
        assert result.status == VerificationStatus.CLASSIFICATION_INVALID

    def test_classification_invalid_randomized_strong(self):
        v = _make_verifier()
        receipt = _make_receipt(
            nondeterminism_class=NondeterminismClass.RANDOMIZED,
            replay_class=ReplayClass.STRONG,
        )
        result = v.verify(receipt)
        assert result.status == VerificationStatus.CLASSIFICATION_INVALID

    def test_classification_invalid_time_dependent_strong(self):
        v = _make_verifier()
        receipt = _make_receipt(
            nondeterminism_class=NondeterminismClass.TIME_DEPENDENT,
            replay_class=ReplayClass.STRONG,
        )
        result = v.verify(receipt)
        assert result.status == VerificationStatus.CLASSIFICATION_INVALID

    def test_classification_invalid_environment_dependent_strong(self):
        v = _make_verifier()
        receipt = _make_receipt(
            nondeterminism_class=NondeterminismClass.ENVIRONMENT_DEPENDENT,
            replay_class=ReplayClass.STRONG,
        )
        result = v.verify(receipt)
        assert result.status == VerificationStatus.CLASSIFICATION_INVALID

    def test_classification_invalid_side_effect_with_strong(self):
        v = _make_verifier()
        receipt = _make_receipt(
            side_effect_class=SideEffectClass.EXTERNAL_WRITE,
            replay_class=ReplayClass.STRONG,
        )
        result = v.verify(receipt)
        assert result.status == VerificationStatus.CLASSIFICATION_INVALID

    def test_non_strict_mode_ignores_classification(self):
        v = ToolReceiptVerifier(strict=False)
        v.register("compute_fibonacci", compute_fibonacci)
        receipt = _make_receipt(
            nondeterminism_class=NondeterminismClass.DETERMINISTIC,
            replay_class=ReplayClass.WEAK,
        )
        # In non-strict mode, classification issues are noted but
        # verification proceeds. Since replay_class is WEAK (not NONE),
        # it still attempts replay.
        result = v.verify(receipt)
        # The tool is registered and produces correct output, so it verifies.
        assert result.status == VerificationStatus.VERIFIED_EXACT

    def test_input_hash_mismatch(self):
        v = _make_verifier()
        receipt = _make_receipt(
            input_sha256="sha256:0000000000000000000000000000000000000000000000000000000000000000",
        )
        result = v.verify(receipt)
        assert result.status == VerificationStatus.INPUT_HASH_MISMATCH

    def test_replay_error_on_bad_input(self):
        v = _make_verifier()
        receipt = _make_receipt(
            input_inline={"n": -1},
            output_inline={"input": -1, "result": 0, "algorithm": "iterative"},
        )
        result = v.verify(receipt)
        assert result.status == VerificationStatus.REPLAY_ERROR
        assert "ValueError" in result.detail

    def test_verified_exact_factorial(self):
        v = _make_verifier()
        receipt = _make_receipt(
            tool_name="compute_factorial",
            input_inline={"n": 5},
            output_inline={"input": 5, "result": 120, "algorithm": "iterative"},
        )
        result = v.verify(receipt)
        assert result.status == VerificationStatus.VERIFIED_EXACT

    def test_verified_exact_math_eval(self):
        v = _make_verifier()
        receipt = _make_receipt(
            tool_name="math_eval",
            input_inline={"expression": "2 ** 10"},
            output_inline={"expression": "2 ** 10", "result": 1024, "algorithm": "ast_eval"},
        )
        result = v.verify(receipt)
        assert result.status == VerificationStatus.VERIFIED_EXACT

    def test_verified_exact_sha256(self):
        v = _make_verifier()
        output = compute_sha256({"data": "hello"})
        receipt = _make_receipt(
            tool_name="compute_sha256",
            input_inline={"data": "hello"},
            output_inline=output,
        )
        result = v.verify(receipt)
        assert result.status == VerificationStatus.VERIFIED_EXACT


class TestVerifierRegistry:
    """Registry management."""

    def test_register_and_list(self):
        v = ToolReceiptVerifier()
        v.register("tool_a", lambda x: x)
        v.register("tool_b", lambda x: x)
        assert v.registered_tools == ["tool_a", "tool_b"]

    def test_unregister(self):
        v = ToolReceiptVerifier()
        v.register("tool_a", lambda x: x)
        v.unregister("tool_a")
        assert v.registered_tools == []

    def test_unregister_missing_raises(self):
        v = ToolReceiptVerifier()
        with pytest.raises(KeyError):
            v.unregister("nonexistent")

    def test_register_empty_name_raises(self):
        v = ToolReceiptVerifier()
        with pytest.raises(ValueError, match="must not be empty"):
            v.register("", lambda x: x)

    def test_builtin_tools_count(self):
        assert len(BUILTIN_TOOLS) == 4
        assert "compute_fibonacci" in BUILTIN_TOOLS
        assert "compute_factorial" in BUILTIN_TOOLS
        assert "compute_sha256" in BUILTIN_TOOLS
        assert "math_eval" in BUILTIN_TOOLS


class TestVerificationResultSerialization:
    """VerificationResult.to_dict() round-trip."""

    def test_to_dict_verified(self):
        r = VerificationResult(
            status=VerificationStatus.VERIFIED_EXACT,
            receipt_id="r-1",
            expected_output_hash="sha256:abc",
            actual_output_hash="sha256:abc",
            detail="OK",
        )
        d = r.to_dict()
        assert d["status"] == "verified_exact"
        assert d["actual_output_hash"] == "sha256:abc"

    def test_to_dict_omits_none_actual(self):
        r = VerificationResult(
            status=VerificationStatus.NOT_REPLAYABLE,
            receipt_id="r-2",
            expected_output_hash="sha256:abc",
        )
        d = r.to_dict()
        assert "actual_output_hash" not in d
        assert "detail" not in d  # empty string omitted


# ==========================================================================
# Deterministic tool function tests
# ==========================================================================

class TestComputeFibonacci:
    def test_fib_0(self):
        assert compute_fibonacci({"n": 0}) == {"input": 0, "result": 0, "algorithm": "iterative"}

    def test_fib_1(self):
        assert compute_fibonacci({"n": 1}) == {"input": 1, "result": 1, "algorithm": "iterative"}

    def test_fib_10(self):
        assert compute_fibonacci({"n": 10}) == {"input": 10, "result": 55, "algorithm": "iterative"}

    def test_fib_20(self):
        assert compute_fibonacci({"n": 20}) == {"input": 20, "result": 6765, "algorithm": "iterative"}

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            compute_fibonacci({"n": -1})

    def test_missing_key_raises(self):
        with pytest.raises(KeyError):
            compute_fibonacci({})


class TestComputeFactorial:
    def test_factorial_0(self):
        assert compute_factorial({"n": 0}) == {"input": 0, "result": 1, "algorithm": "iterative"}

    def test_factorial_5(self):
        assert compute_factorial({"n": 5}) == {"input": 5, "result": 120, "algorithm": "iterative"}

    def test_factorial_too_large(self):
        with pytest.raises(ValueError, match="too large"):
            compute_factorial({"n": 1001})


class TestMathEval:
    def test_addition(self):
        assert math_eval({"expression": "2 + 3"})["result"] == 5

    def test_multiplication(self):
        assert math_eval({"expression": "6 * 7"})["result"] == 42

    def test_power(self):
        assert math_eval({"expression": "2 ** 10"})["result"] == 1024

    def test_parentheses(self):
        assert math_eval({"expression": "(2 + 3) * 4"})["result"] == 20

    def test_disallowed_chars(self):
        with pytest.raises(ValueError, match="disallowed"):
            math_eval({"expression": "import os"})

    def test_float_to_int_normalisation(self):
        """10 / 2 = 5.0 should normalise to 5."""
        assert math_eval({"expression": "10 / 2"})["result"] == 5


class TestComputeSha256:
    def test_hello(self):
        result = compute_sha256({"data": "hello"})
        assert result["hash"] == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        assert result["algorithm"] == "sha256"


# ==========================================================================
# Batch verification tests
# ==========================================================================

def _make_claim_with_evidence(receipts: list) -> Claim:
    """Build a Claim with the given evidence list."""
    return Claim(
        id="batch-test-claim",
        statement="test",
        type=ClaimType.ASSERTION,
        proof_ref=ProofReference(hash="h", location="l", summary="s"),
        stake=Stake(amount=0.1),
        evidence=receipts,
    )


class TestBatchVerification:
    """verify_claim() over a Claim's full evidence list."""

    def test_all_verified(self):
        v = _make_verifier()
        r1 = _make_receipt(
            tool_name="compute_fibonacci",
            input_inline={"n": 10},
            output_inline={"input": 10, "result": 55, "algorithm": "iterative"},
        )
        r2 = _make_receipt(
            tool_name="compute_factorial",
            input_inline={"n": 5},
            output_inline={"input": 5, "result": 120, "algorithm": "iterative"},
        )
        claim = _make_claim_with_evidence([r1, r2])
        result = v.verify_claim(claim)
        assert result.all_verified is True
        assert len(result.results) == 2
        assert result.claim_id == "batch-test-claim"
        assert "2" in result.summary

    def test_one_tampered(self):
        v = _make_verifier()
        good = _make_receipt(
            tool_name="compute_fibonacci",
            input_inline={"n": 10},
            output_inline={"input": 10, "result": 55, "algorithm": "iterative"},
        )
        bad = _make_receipt(
            tool_name="compute_fibonacci",
            input_inline={"n": 10},
            output_inline={"input": 10, "result": 99, "algorithm": "iterative"},
        )
        claim = _make_claim_with_evidence([good, bad])
        result = v.verify_claim(claim)
        assert result.all_verified is False
        assert len(result.results) == 2
        assert "1/2 verified" in result.summary

    def test_empty_evidence(self):
        v = _make_verifier()
        claim = _make_claim_with_evidence([])
        result = v.verify_claim(claim)
        assert result.all_verified is False
        assert len(result.results) == 0
        assert "No evidence" in result.summary

    def test_single_receipt(self):
        v = _make_verifier()
        r = _make_receipt()
        claim = _make_claim_with_evidence([r])
        result = v.verify_claim(claim)
        assert result.all_verified is True
        assert len(result.results) == 1

    def test_to_dict_round_trip(self):
        v = _make_verifier()
        r = _make_receipt()
        claim = _make_claim_with_evidence([r])
        result = v.verify_claim(claim)
        d = result.to_dict()
        assert d["claim_id"] == "batch-test-claim"
        assert d["all_verified"] is True
        assert len(d["results"]) == 1
        assert d["results"][0]["status"] == "verified_exact"

    def test_mixed_tools(self):
        v = _make_verifier()
        fib = _make_receipt(
            tool_name="compute_fibonacci",
            input_inline={"n": 10},
            output_inline={"input": 10, "result": 55, "algorithm": "iterative"},
        )
        sha = _make_receipt(
            tool_name="compute_sha256",
            input_inline={"data": "hello"},
            output_inline=compute_sha256({"data": "hello"}),
        )
        math = _make_receipt(
            tool_name="math_eval",
            input_inline={"expression": "2 + 3"},
            output_inline={"expression": "2 + 3", "result": 5, "algorithm": "ast_eval"},
        )
        claim = _make_claim_with_evidence([fib, sha, math])
        result = v.verify_claim(claim)
        assert result.all_verified is True
        assert len(result.results) == 3
        assert "3" in result.summary


class TestStructuredClaimAwareVerification:
    """verify_claim() with structured_claim proposition matching."""

    _SC_MATCHING = {
        "sc_version": "0.5",
        "kind": "tool_output",
        "proposition": {
            "type": "tool_output_equals",
            "tool_name": "compute_fibonacci",
            "input": {"n": 10},
            "expected_output": {"input": 10, "result": 55, "algorithm": "iterative"},
            "input_match": "exact",
            "output_match": "exact",
        },
    }

    _SC_MISMATCHING = {
        "sc_version": "0.5",
        "kind": "tool_output",
        "proposition": {
            "type": "tool_output_equals",
            "tool_name": "compute_fibonacci",
            "input": {"n": 10},
            "expected_output": {"input": 10, "result": 99, "algorithm": "iterative"},
            "input_match": "exact",
            "output_match": "exact",
        },
    }

    def test_verify_claim_without_structured_claim(self):
        v = _make_verifier()
        r = _make_receipt()
        claim = _make_claim_with_evidence([r])
        result = v.verify_claim(claim)
        assert result.claim_match_status is None
        assert result.claim_match_summary is None

    def test_verify_claim_with_matching_structured_claim(self):
        v = _make_verifier()
        r = _make_receipt()
        claim = _make_claim_with_evidence([r])
        claim.structured_claim = self._SC_MATCHING
        result = v.verify_claim(claim)
        assert result.claim_match_status == "true"

    def test_verify_claim_with_mismatching_structured_claim(self):
        v = _make_verifier()
        r = _make_receipt()
        claim = _make_claim_with_evidence([r])
        claim.structured_claim = self._SC_MISMATCHING
        result = v.verify_claim(claim)
        assert result.claim_match_status == "false"

    def test_verify_claim_to_dict_includes_match(self):
        v = _make_verifier()
        r = _make_receipt()
        claim = _make_claim_with_evidence([r])
        claim.structured_claim = self._SC_MATCHING
        result = v.verify_claim(claim)
        d = result.to_dict()
        assert "claim_match_status" in d
        assert "claim_match_summary" in d
