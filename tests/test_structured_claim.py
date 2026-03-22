"""Tests for urp/structured_claim.py and urp/claim_verifier.py."""

import json

import pytest

from urp.core import (
    EvidenceStrength,
    NondeterminismClass,
    ReplayClass,
    SideEffectClass,
    ToolReceipt,
)
from urp.deterministic_tools import compute_fibonacci, compute_factorial, compute_sha256
from urp.structured_claim import (
    ComparisonOp,
    Compound,
    LogicalOp,
    MatchMode,
    StructuredClaim,
    ToolOutputEquals,
    ValueComparison,
    proposition_from_dict,
)
from urp.claim_verifier import (
    ClaimMatchResult,
    PropResult,
    PropStatus,
    evaluate_proposition,
    match_claim,
)


# ---------- Helpers ----------

def _make_receipt(
    tool_name: str = "compute_fibonacci",
    input_inline: dict | None = None,
    output_inline: dict | None = None,
    receipt_id: str = "test-receipt",
) -> ToolReceipt:
    if input_inline is None:
        input_inline = {"n": 10}
    if output_inline is None:
        output_inline = {"input": 10, "result": 55, "algorithm": "iterative"}
    return ToolReceipt(
        receipt_id=receipt_id,
        tool_name=tool_name,
        tool_version="1.0.0",
        provider_name="test",
        provider_id="test",
        protocol_family="local_python",
        started_at="2026-03-22T00:00:00Z",
        input_inline=input_inline,
        output_inline=output_inline,
    )


# ==========================================================================
# StructuredClaim schema tests
# ==========================================================================

class TestToolOutputEquals:
    def test_to_dict_round_trip(self):
        prop = ToolOutputEquals(
            tool_name="compute_fibonacci",
            input={"n": 10},
            expected_output={"input": 10, "result": 55, "algorithm": "iterative"},
        )
        d = prop.to_dict()
        restored = ToolOutputEquals.from_dict(d)
        assert restored.tool_name == "compute_fibonacci"
        assert restored.input == {"n": 10}
        assert restored.expected_output == {"input": 10, "result": 55, "algorithm": "iterative"}
        assert restored.input_match == MatchMode.EXACT
        assert restored.output_match == MatchMode.EXACT

    def test_type_field(self):
        prop = ToolOutputEquals(tool_name="test", input={}, expected_output={})
        assert prop.to_dict()["type"] == "tool_output_equals"

    def test_fingerprint_stable(self):
        p1 = ToolOutputEquals(tool_name="t", input={"a": 1}, expected_output={"b": 2})
        p2 = ToolOutputEquals(tool_name="t", input={"a": 1}, expected_output={"b": 2})
        assert p1.canonical_fingerprint() == p2.canonical_fingerprint()

    def test_fingerprint_changes_with_content(self):
        p1 = ToolOutputEquals(tool_name="t", input={"a": 1}, expected_output={"b": 2})
        p2 = ToolOutputEquals(tool_name="t", input={"a": 1}, expected_output={"b": 3})
        assert p1.canonical_fingerprint() != p2.canonical_fingerprint()

    def test_subset_match_mode(self):
        prop = ToolOutputEquals(
            tool_name="t",
            input={"n": 10},
            expected_output={"result": 55},
            output_match=MatchMode.SUBSET,
        )
        d = prop.to_dict()
        assert d["output_match"] == "subset"
        restored = ToolOutputEquals.from_dict(d)
        assert restored.output_match == MatchMode.SUBSET


class TestValueComparison:
    def test_to_dict_round_trip(self):
        prop = ValueComparison(
            tool_name="compute_fibonacci",
            input={"n": 10},
            path=["result"],
            op=ComparisonOp.EQ,
            value=55,
        )
        d = prop.to_dict()
        restored = ValueComparison.from_dict(d)
        assert restored.tool_name == "compute_fibonacci"
        assert restored.path == ["result"]
        assert restored.op == ComparisonOp.EQ
        assert restored.value == 55

    def test_type_field(self):
        prop = ValueComparison(
            tool_name="t", input={}, path=[], op=ComparisonOp.GT, value=0
        )
        assert prop.to_dict()["type"] == "value_comparison"

    def test_all_comparison_ops(self):
        for op in ComparisonOp:
            prop = ValueComparison(
                tool_name="t", input={}, path=["x"], op=op, value=1
            )
            d = prop.to_dict()
            restored = ValueComparison.from_dict(d)
            assert restored.op == op


class TestCompound:
    def test_and_to_dict_round_trip(self):
        p1 = ToolOutputEquals(tool_name="a", input={}, expected_output={})
        p2 = ToolOutputEquals(tool_name="b", input={}, expected_output={})
        compound = Compound(op=LogicalOp.AND, args=[p1, p2])
        d = compound.to_dict()
        restored = Compound.from_dict(d)
        assert restored.op == LogicalOp.AND
        assert len(restored.args) == 2

    def test_not_requires_one_arg(self):
        p1 = ToolOutputEquals(tool_name="a", input={}, expected_output={})
        p2 = ToolOutputEquals(tool_name="b", input={}, expected_output={})
        compound = Compound(op=LogicalOp.NOT, args=[p1, p2])
        with pytest.raises(ValueError, match="NOT requires exactly one arg"):
            compound.canonicalize()

    def test_implies_requires_two_args(self):
        p1 = ToolOutputEquals(tool_name="a", input={}, expected_output={})
        compound = Compound(op=LogicalOp.IMPLIES, args=[p1])
        with pytest.raises(ValueError, match="IMPLIES requires exactly two args"):
            compound.canonicalize()

    def test_and_canonicalize_sorts_by_fingerprint(self):
        p1 = ToolOutputEquals(tool_name="zzz", input={}, expected_output={})
        p2 = ToolOutputEquals(tool_name="aaa", input={}, expected_output={})
        c1 = Compound(op=LogicalOp.AND, args=[p1, p2])
        c2 = Compound(op=LogicalOp.AND, args=[p2, p1])
        assert c1.canonical_fingerprint() == c2.canonical_fingerprint()

    def test_and_canonicalize_flattens(self):
        p1 = ToolOutputEquals(tool_name="a", input={}, expected_output={})
        p2 = ToolOutputEquals(tool_name="b", input={}, expected_output={})
        p3 = ToolOutputEquals(tool_name="c", input={}, expected_output={})
        nested = Compound(op=LogicalOp.AND, args=[
            p1,
            Compound(op=LogicalOp.AND, args=[p2, p3]),
        ])
        canon = nested.canonicalize()
        assert len(canon.args) == 3  # flattened

    def test_and_canonicalize_dedupes(self):
        p1 = ToolOutputEquals(tool_name="a", input={"x": 1}, expected_output={"y": 2})
        p2 = ToolOutputEquals(tool_name="a", input={"x": 1}, expected_output={"y": 2})
        compound = Compound(op=LogicalOp.AND, args=[p1, p2])
        canon = compound.canonicalize()
        assert len(canon.args) == 1  # deduped


class TestStructuredClaim:
    def test_to_dict_round_trip(self):
        sc = StructuredClaim(
            sc_version="0.5",
            kind="tool_output",
            proposition=ToolOutputEquals(
                tool_name="compute_fibonacci",
                input={"n": 10},
                expected_output={"input": 10, "result": 55, "algorithm": "iterative"},
            ),
        )
        d = sc.to_dict()
        restored = StructuredClaim.from_dict(d)
        assert restored.sc_version == "0.5"
        assert restored.kind == "tool_output"
        assert isinstance(restored.proposition, ToolOutputEquals)

    def test_fingerprint_stable(self):
        sc1 = StructuredClaim(
            sc_version="0.5",
            kind="tool_output",
            proposition=ToolOutputEquals(tool_name="t", input={"a": 1}, expected_output={"b": 2}),
        )
        sc2 = StructuredClaim(
            sc_version="0.5",
            kind="tool_output",
            proposition=ToolOutputEquals(tool_name="t", input={"a": 1}, expected_output={"b": 2}),
        )
        assert sc1.fingerprint() == sc2.fingerprint()

    def test_canonical_json_deterministic(self):
        sc = StructuredClaim(
            sc_version="0.5",
            kind="tool_output",
            proposition=ToolOutputEquals(tool_name="t", input={}, expected_output={}),
        )
        j1 = sc.canonical_json()
        j2 = sc.canonical_json()
        assert j1 == j2
        # Must be valid JSON
        parsed = json.loads(j1)
        assert parsed["sc_version"] == "0.5"

    def test_render_statement_tool_output(self):
        sc = StructuredClaim(
            sc_version="0.5",
            kind="tool_output",
            proposition=ToolOutputEquals(
                tool_name="compute_fibonacci",
                input={"n": 10},
                expected_output={"input": 10, "result": 55, "algorithm": "iterative"},
            ),
        )
        stmt = sc.render_statement()
        assert "compute_fibonacci" in stmt
        assert "n=" in stmt

    def test_render_statement_compound(self):
        sc = StructuredClaim(
            sc_version="0.5",
            kind="tool_output",
            proposition=Compound(
                op=LogicalOp.AND,
                args=[
                    ToolOutputEquals(tool_name="a", input={}, expected_output={}),
                    ToolOutputEquals(tool_name="b", input={}, expected_output={}),
                ],
            ),
        )
        stmt = sc.render_statement()
        assert "AND" in stmt


class TestPropositionFromDict:
    def test_tool_output_equals(self):
        d = {"type": "tool_output_equals", "tool_name": "t", "input": {}, "expected_output": {}}
        p = proposition_from_dict(d)
        assert isinstance(p, ToolOutputEquals)

    def test_value_comparison(self):
        d = {"type": "value_comparison", "tool_name": "t", "input": {}, "path": ["x"], "op": "==", "value": 1}
        p = proposition_from_dict(d)
        assert isinstance(p, ValueComparison)

    def test_compound(self):
        d = {"type": "compound", "op": "and", "args": [
            {"type": "tool_output_equals", "tool_name": "t", "input": {}, "expected_output": {}},
        ]}
        p = proposition_from_dict(d)
        assert isinstance(p, Compound)

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown proposition type"):
            proposition_from_dict({"type": "bogus"})


# ==========================================================================
# Claim-to-evidence matching tests
# ==========================================================================

class TestToolOutputMatching:
    def test_exact_match(self):
        prop = ToolOutputEquals(
            tool_name="compute_fibonacci",
            input={"n": 10},
            expected_output={"input": 10, "result": 55, "algorithm": "iterative"},
        )
        receipt = _make_receipt()
        result = evaluate_proposition(prop, [receipt])
        assert result.status == PropStatus.TRUE
        assert "test-receipt" in result.matched_receipts

    def test_output_mismatch(self):
        prop = ToolOutputEquals(
            tool_name="compute_fibonacci",
            input={"n": 10},
            expected_output={"input": 10, "result": 99, "algorithm": "iterative"},
        )
        receipt = _make_receipt()
        result = evaluate_proposition(prop, [receipt])
        assert result.status == PropStatus.FALSE

    def test_no_matching_tool(self):
        prop = ToolOutputEquals(
            tool_name="nonexistent_tool",
            input={"n": 10},
            expected_output={"result": 55},
        )
        receipt = _make_receipt()
        result = evaluate_proposition(prop, [receipt])
        assert result.status == PropStatus.UNKNOWN

    def test_input_mismatch(self):
        prop = ToolOutputEquals(
            tool_name="compute_fibonacci",
            input={"n": 20},  # different from receipt
            expected_output={"input": 10, "result": 55, "algorithm": "iterative"},
        )
        receipt = _make_receipt()
        result = evaluate_proposition(prop, [receipt])
        assert result.status == PropStatus.FALSE

    def test_subset_output_match(self):
        prop = ToolOutputEquals(
            tool_name="compute_fibonacci",
            input={"n": 10},
            expected_output={"result": 55},  # subset of full output
            output_match=MatchMode.SUBSET,
        )
        receipt = _make_receipt()
        result = evaluate_proposition(prop, [receipt])
        assert result.status == PropStatus.TRUE

    def test_empty_evidence_list(self):
        prop = ToolOutputEquals(
            tool_name="compute_fibonacci",
            input={"n": 10},
            expected_output={"result": 55},
        )
        result = evaluate_proposition(prop, [])
        assert result.status == PropStatus.UNKNOWN


class TestValueComparisonMatching:
    def test_equals(self):
        prop = ValueComparison(
            tool_name="compute_fibonacci",
            input={"n": 10},
            path=["result"],
            op=ComparisonOp.EQ,
            value=55,
        )
        receipt = _make_receipt()
        result = evaluate_proposition(prop, [receipt])
        assert result.status == PropStatus.TRUE

    def test_greater_than(self):
        prop = ValueComparison(
            tool_name="compute_fibonacci",
            input={"n": 10},
            path=["result"],
            op=ComparisonOp.GT,
            value=50,
        )
        receipt = _make_receipt()
        result = evaluate_proposition(prop, [receipt])
        assert result.status == PropStatus.TRUE

    def test_less_than_fails(self):
        prop = ValueComparison(
            tool_name="compute_fibonacci",
            input={"n": 10},
            path=["result"],
            op=ComparisonOp.LT,
            value=50,
        )
        receipt = _make_receipt()
        result = evaluate_proposition(prop, [receipt])
        assert result.status == PropStatus.FALSE

    def test_missing_path(self):
        prop = ValueComparison(
            tool_name="compute_fibonacci",
            input={"n": 10},
            path=["nonexistent_field"],
            op=ComparisonOp.EQ,
            value=55,
        )
        receipt = _make_receipt()
        result = evaluate_proposition(prop, [receipt])
        assert result.status == PropStatus.FALSE

    def test_no_matching_tool(self):
        prop = ValueComparison(
            tool_name="missing",
            input={},
            path=["x"],
            op=ComparisonOp.EQ,
            value=1,
        )
        result = evaluate_proposition(prop, [_make_receipt()])
        assert result.status == PropStatus.UNKNOWN


class TestCompoundMatching:
    def test_and_all_true(self):
        p1 = ToolOutputEquals(
            tool_name="compute_fibonacci",
            input={"n": 10},
            expected_output={"input": 10, "result": 55, "algorithm": "iterative"},
        )
        p2 = ValueComparison(
            tool_name="compute_fibonacci",
            input={"n": 10},
            path=["result"],
            op=ComparisonOp.GT,
            value=0,
        )
        compound = Compound(op=LogicalOp.AND, args=[p1, p2])
        receipt = _make_receipt()
        result = evaluate_proposition(compound, [receipt])
        assert result.status == PropStatus.TRUE

    def test_and_one_false(self):
        p1 = ToolOutputEquals(
            tool_name="compute_fibonacci",
            input={"n": 10},
            expected_output={"input": 10, "result": 55, "algorithm": "iterative"},
        )
        p2 = ToolOutputEquals(
            tool_name="compute_fibonacci",
            input={"n": 10},
            expected_output={"input": 10, "result": 99, "algorithm": "iterative"},
        )
        compound = Compound(op=LogicalOp.AND, args=[p1, p2])
        result = evaluate_proposition(compound, [_make_receipt()])
        assert result.status == PropStatus.FALSE

    def test_or_one_true(self):
        p1 = ToolOutputEquals(
            tool_name="compute_fibonacci",
            input={"n": 10},
            expected_output={"input": 10, "result": 55, "algorithm": "iterative"},
        )
        p2 = ToolOutputEquals(
            tool_name="compute_fibonacci",
            input={"n": 10},
            expected_output={"input": 10, "result": 99, "algorithm": "iterative"},
        )
        compound = Compound(op=LogicalOp.OR, args=[p1, p2])
        result = evaluate_proposition(compound, [_make_receipt()])
        assert result.status == PropStatus.TRUE

    def test_or_all_false(self):
        p1 = ToolOutputEquals(tool_name="x", input={}, expected_output={"wrong": True})
        p2 = ToolOutputEquals(tool_name="y", input={}, expected_output={"wrong": True})
        compound = Compound(op=LogicalOp.OR, args=[p1, p2])
        result = evaluate_proposition(compound, [])
        assert result.status == PropStatus.UNKNOWN

    def test_not_true_becomes_false(self):
        p = ToolOutputEquals(
            tool_name="compute_fibonacci",
            input={"n": 10},
            expected_output={"input": 10, "result": 55, "algorithm": "iterative"},
        )
        compound = Compound(op=LogicalOp.NOT, args=[p])
        result = evaluate_proposition(compound, [_make_receipt()])
        assert result.status == PropStatus.FALSE

    def test_not_false_becomes_true(self):
        p = ToolOutputEquals(
            tool_name="compute_fibonacci",
            input={"n": 10},
            expected_output={"input": 10, "result": 99, "algorithm": "iterative"},
        )
        compound = Compound(op=LogicalOp.NOT, args=[p])
        result = evaluate_proposition(compound, [_make_receipt()])
        assert result.status == PropStatus.TRUE

    def test_implies_true_antecedent_true_consequent(self):
        # IF fib(10)=55 THEN fib(10).result > 0 — both true, so true
        ante = ToolOutputEquals(
            tool_name="compute_fibonacci",
            input={"n": 10},
            expected_output={"input": 10, "result": 55, "algorithm": "iterative"},
        )
        cons = ValueComparison(
            tool_name="compute_fibonacci",
            input={"n": 10},
            path=["result"],
            op=ComparisonOp.GT,
            value=0,
        )
        compound = Compound(op=LogicalOp.IMPLIES, args=[ante, cons])
        result = evaluate_proposition(compound, [_make_receipt()])
        assert result.status == PropStatus.TRUE

    def test_implies_false_antecedent_vacuously_true(self):
        ante = ToolOutputEquals(
            tool_name="compute_fibonacci",
            input={"n": 10},
            expected_output={"input": 10, "result": 99, "algorithm": "iterative"},
        )
        cons = ToolOutputEquals(tool_name="anything", input={}, expected_output={})
        compound = Compound(op=LogicalOp.IMPLIES, args=[ante, cons])
        result = evaluate_proposition(compound, [_make_receipt()])
        assert result.status == PropStatus.TRUE  # vacuously true


class TestMatchClaim:
    def test_fibonacci_claim_matches(self):
        sc = StructuredClaim(
            sc_version="0.5",
            kind="tool_output",
            proposition=ToolOutputEquals(
                tool_name="compute_fibonacci",
                input={"n": 10},
                expected_output={"input": 10, "result": 55, "algorithm": "iterative"},
            ),
        )
        receipt = _make_receipt()
        result = match_claim(sc, [receipt])
        assert result.overall_status == PropStatus.TRUE
        assert "verified" in result.summary.lower()

    def test_tampered_claim_fails(self):
        sc = StructuredClaim(
            sc_version="0.5",
            kind="tool_output",
            proposition=ToolOutputEquals(
                tool_name="compute_fibonacci",
                input={"n": 10},
                expected_output={"input": 10, "result": 99, "algorithm": "iterative"},
            ),
        )
        receipt = _make_receipt()
        result = match_claim(sc, [receipt])
        assert result.overall_status == PropStatus.FALSE

    def test_compound_claim_with_multiple_receipts(self):
        fib_output = compute_fibonacci({"n": 10})
        sha_output = compute_sha256({"data": "hello"})

        sc = StructuredClaim(
            sc_version="0.5",
            kind="tool_output",
            proposition=Compound(
                op=LogicalOp.AND,
                args=[
                    ToolOutputEquals(
                        tool_name="compute_fibonacci",
                        input={"n": 10},
                        expected_output=fib_output,
                    ),
                    ToolOutputEquals(
                        tool_name="compute_sha256",
                        input={"data": "hello"},
                        expected_output=sha_output,
                    ),
                ],
            ),
        )
        receipts = [
            _make_receipt(
                tool_name="compute_fibonacci",
                input_inline={"n": 10},
                output_inline=fib_output,
                receipt_id="fib-receipt",
            ),
            _make_receipt(
                tool_name="compute_sha256",
                input_inline={"data": "hello"},
                output_inline=sha_output,
                receipt_id="sha-receipt",
            ),
        ]
        result = match_claim(sc, receipts)
        assert result.overall_status == PropStatus.TRUE

    def test_result_to_dict(self):
        sc = StructuredClaim(
            sc_version="0.5",
            kind="tool_output",
            proposition=ToolOutputEquals(
                tool_name="compute_fibonacci",
                input={"n": 10},
                expected_output={"input": 10, "result": 55, "algorithm": "iterative"},
            ),
        )
        result = match_claim(sc, [_make_receipt()])
        d = result.to_dict()
        assert d["overall_status"] == "true"
        assert "claim_fingerprint" in d
        assert len(d["proposition_results"]) > 0
