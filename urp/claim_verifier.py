"""Claim-to-evidence matching for StructuredClaim propositions.

Given a StructuredClaim and a list of ToolReceipts, determines which
receipts satisfy which propositions in the claim's proposition tree.

Uses three-valued logic (TRUE, FALSE, UNKNOWN) for compound evaluation:
- TRUE: proposition mechanically verified against evidence
- FALSE: evidence exists but contradicts the proposition
- UNKNOWN: no mechanical verification path (missing evidence or non-replayable)

This module handles claim-level matching. For receipt-level replay
verification, use ``urp.verify.ToolReceiptVerifier``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from urp.core import ToolReceipt
from urp.structured_claim import (
    Compound,
    LogicalOp,
    MatchMode,
    Proposition,
    StructuredClaim,
    ToolOutputEquals,
    ValueComparison,
    ComparisonOp,
    _canonical_json,
)


class PropStatus(Enum):
    """Three-valued truth status for proposition evaluation."""
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"


@dataclass
class PropResult:
    """Result of evaluating a single proposition against evidence.

    Attributes:
        status: Three-valued truth status.
        matched_receipts: Receipt IDs that satisfied this proposition.
        detail: Human-readable explanation.
    """
    status: PropStatus
    matched_receipts: list[str] = field(default_factory=list)
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "matched_receipts": self.matched_receipts,
            "detail": self.detail,
        }


@dataclass
class ClaimMatchResult:
    """Result of matching a full StructuredClaim against evidence.

    Attributes:
        claim_fingerprint: SHA-256 fingerprint of the canonicalized claim.
        overall_status: Aggregate truth status.
        proposition_results: Results for each leaf and compound node.
        summary: Human-readable summary.
    """
    claim_fingerprint: str
    overall_status: PropStatus
    proposition_results: list[PropResult]
    summary: str

    def to_dict(self) -> dict:
        return {
            "claim_fingerprint": self.claim_fingerprint,
            "overall_status": self.overall_status.value,
            "proposition_results": [r.to_dict() for r in self.proposition_results],
            "summary": self.summary,
        }


def _deep_equals(a: Any, b: Any) -> bool:
    """Deep equality via canonical JSON comparison."""
    return _canonical_json(a) == _canonical_json(b)


def _is_subset(expected: dict, actual: dict) -> bool:
    """Check if expected is a deep subset of actual.

    Every key in expected must exist in actual with the same value.
    """
    for key, val in expected.items():
        if key not in actual:
            return False
        if isinstance(val, dict) and isinstance(actual[key], dict):
            if not _is_subset(val, actual[key]):
                return False
        elif _canonical_json(val) != _canonical_json(actual[key]):
            return False
    return True


def _match_dict(expected: dict, actual: dict, mode: MatchMode) -> bool:
    """Match two dicts according to the given mode."""
    if mode == MatchMode.EXACT:
        return _deep_equals(expected, actual)
    return _is_subset(expected, actual)


def _resolve_path(obj: Any, path: list) -> tuple[bool, Any]:
    """Walk a JSON path into an object.

    Returns (found, value). If any segment is missing, returns (False, None).
    """
    current = obj
    for segment in path:
        if isinstance(current, dict) and isinstance(segment, str):
            if segment not in current:
                return False, None
            current = current[segment]
        elif isinstance(current, list) and isinstance(segment, int):
            if segment < 0 or segment >= len(current):
                return False, None
            current = current[segment]
        else:
            return False, None
    return True, current


def _compare(actual: Any, op: ComparisonOp, expected: Any) -> bool:
    """Apply a comparison operator."""
    try:
        if op == ComparisonOp.EQ:
            return actual == expected
        if op == ComparisonOp.NEQ:
            return actual != expected
        if op == ComparisonOp.LT:
            return actual < expected
        if op == ComparisonOp.LTE:
            return actual <= expected
        if op == ComparisonOp.GT:
            return actual > expected
        if op == ComparisonOp.GTE:
            return actual >= expected
    except TypeError:
        return False
    return False


def _eval_tool_output_equals(
    prop: ToolOutputEquals,
    receipts: list[ToolReceipt],
) -> PropResult:
    """Evaluate a ToolOutputEquals proposition against receipts."""
    candidates = [r for r in receipts if r.tool_name == prop.tool_name]

    if not candidates:
        return PropResult(
            status=PropStatus.UNKNOWN,
            detail=f"No receipt found for tool '{prop.tool_name}'.",
        )

    for r in candidates:
        input_match = _match_dict(prop.input, r.input_inline, prop.input_match)
        if not input_match:
            continue
        output_match = _match_dict(
            prop.expected_output, r.output_inline, prop.output_match
        )
        if output_match:
            return PropResult(
                status=PropStatus.TRUE,
                matched_receipts=[r.receipt_id],
                detail=(
                    f"Receipt {r.receipt_id} matches: "
                    f"tool={r.tool_name}, input and output verified."
                ),
            )

    # Candidates exist but none matched
    return PropResult(
        status=PropStatus.FALSE,
        detail=(
            f"Receipt(s) found for '{prop.tool_name}' but "
            f"input/output did not match expected values."
        ),
    )


def _eval_value_comparison(
    prop: ValueComparison,
    receipts: list[ToolReceipt],
) -> PropResult:
    """Evaluate a ValueComparison proposition against receipts."""
    candidates = [r for r in receipts if r.tool_name == prop.tool_name]

    if not candidates:
        return PropResult(
            status=PropStatus.UNKNOWN,
            detail=f"No receipt found for tool '{prop.tool_name}'.",
        )

    for r in candidates:
        input_match = _match_dict(prop.input, r.input_inline, prop.input_match)
        if not input_match:
            continue

        found, actual_value = _resolve_path(r.output_inline, prop.path)
        if not found:
            continue

        if _compare(actual_value, prop.op, prop.value):
            return PropResult(
                status=PropStatus.TRUE,
                matched_receipts=[r.receipt_id],
                detail=(
                    f"Receipt {r.receipt_id}: "
                    f"path {prop.path} = {actual_value!r} {prop.op.value} {prop.value!r} is true."
                ),
            )

    return PropResult(
        status=PropStatus.FALSE,
        detail=(
            f"Receipt(s) found for '{prop.tool_name}' but "
            f"value comparison {prop.path} {prop.op.value} {prop.value!r} failed."
        ),
    )


def _eval_compound(
    prop: Compound,
    receipts: list[ToolReceipt],
) -> PropResult:
    """Evaluate a compound proposition using three-valued logic."""
    child_results = [evaluate_proposition(a, receipts) for a in prop.args]

    if prop.op == LogicalOp.AND:
        if any(r.status == PropStatus.FALSE for r in child_results):
            status = PropStatus.FALSE
        elif all(r.status == PropStatus.TRUE for r in child_results):
            status = PropStatus.TRUE
        else:
            status = PropStatus.UNKNOWN

    elif prop.op == LogicalOp.OR:
        if any(r.status == PropStatus.TRUE for r in child_results):
            status = PropStatus.TRUE
        elif all(r.status == PropStatus.FALSE for r in child_results):
            status = PropStatus.FALSE
        else:
            status = PropStatus.UNKNOWN

    elif prop.op == LogicalOp.NOT:
        child = child_results[0]
        if child.status == PropStatus.TRUE:
            status = PropStatus.FALSE
        elif child.status == PropStatus.FALSE:
            status = PropStatus.TRUE
        else:
            status = PropStatus.UNKNOWN

    elif prop.op == LogicalOp.IMPLIES:
        # IMPLIES(A, B) = NOT(A) OR B
        antecedent = child_results[0]
        consequent = child_results[1]
        if antecedent.status == PropStatus.FALSE:
            status = PropStatus.TRUE  # vacuously true
        elif consequent.status == PropStatus.TRUE:
            status = PropStatus.TRUE
        elif (
            antecedent.status == PropStatus.TRUE
            and consequent.status == PropStatus.FALSE
        ):
            status = PropStatus.FALSE
        else:
            status = PropStatus.UNKNOWN
    else:
        status = PropStatus.UNKNOWN

    all_receipts = []
    for r in child_results:
        all_receipts.extend(r.matched_receipts)

    return PropResult(
        status=status,
        matched_receipts=list(set(all_receipts)),
        detail=f"{prop.op.value.upper()}({', '.join(r.status.value for r in child_results)})",
    )


def evaluate_proposition(
    prop: Proposition,
    receipts: list[ToolReceipt],
) -> PropResult:
    """Evaluate a proposition against a list of ToolReceipts.

    Args:
        prop: Any proposition type.
        receipts: The evidence to match against.

    Returns:
        A PropResult with three-valued truth status and matched receipts.
    """
    if isinstance(prop, ToolOutputEquals):
        return _eval_tool_output_equals(prop, receipts)
    if isinstance(prop, ValueComparison):
        return _eval_value_comparison(prop, receipts)
    if isinstance(prop, Compound):
        return _eval_compound(prop, receipts)
    return PropResult(
        status=PropStatus.UNKNOWN,
        detail=f"Unknown proposition type: {type(prop).__name__}",
    )


def match_claim(
    claim: StructuredClaim,
    receipts: list[ToolReceipt],
) -> ClaimMatchResult:
    """Match a StructuredClaim against a list of ToolReceipts.

    This is the top-level entry point for claim-to-evidence matching.

    Args:
        claim: The structured claim to evaluate.
        receipts: The evidence list (typically from Claim.evidence).

    Returns:
        A ClaimMatchResult with overall status and per-proposition results.
    """
    result = evaluate_proposition(claim.proposition, receipts)

    if result.status == PropStatus.TRUE:
        summary = "Claim verified: all propositions matched by evidence."
    elif result.status == PropStatus.FALSE:
        summary = "Claim falsified: evidence contradicts one or more propositions."
    else:
        summary = "Claim unresolved: insufficient evidence for mechanical verification."

    return ClaimMatchResult(
        claim_fingerprint=claim.fingerprint(),
        overall_status=result.status,
        proposition_results=[result],
        summary=summary,
    )
