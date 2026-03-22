"""Structured claims for URP v0.5.

Replaces free-text ``statement: str`` in ``Claim`` with machine-parseable
propositions that can be mechanically matched to ToolReceipt evidence.

Proposition types:

- ``ToolOutputEquals`` — "tool X with input Y produces output Z"
- ``ValueComparison`` — "field path P in tool X's output satisfies op against value V"
- ``Compound`` — logical composition (AND, OR, NOT, IMPLIES)

Each proposition supports:
- Deterministic JSON serialisation via ``to_dict()`` / ``from_dict()``
- Canonical fingerprinting for equivalence comparison
- Mechanical matching to ToolReceipt evidence

Deferred to later versions:
- ``FactualAssertion`` (SPO triples) — no mechanical verification path yet
- RFC 8785 (JCS) canonicalization — uses URP's existing sorted-key compact JSON
- NLP parsing of free-text into structured claims
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union


# ---------------------------------------------------------------------------
# Canonical JSON (matches URP's existing pattern in core.py)
# ---------------------------------------------------------------------------

def _canonical_json(obj: Any) -> str:
    """URP canonical JSON: sorted keys, compact separators."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _sha256_of(obj: Any) -> str:
    """Return 'sha256:<hex>' of canonical JSON."""
    return "sha256:" + hashlib.sha256(
        _canonical_json(obj).encode("utf-8")
    ).hexdigest()


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MatchMode(Enum):
    """How to compare dicts when matching claim to receipt."""
    EXACT = "exact"
    SUBSET = "subset"


class LogicalOp(Enum):
    """Connectives for compound propositions."""
    AND = "and"
    OR = "or"
    NOT = "not"
    IMPLIES = "implies"


class ComparisonOp(Enum):
    """Scalar comparison operators."""
    EQ = "=="
    NEQ = "!="
    LT = "<"
    LTE = "<="
    GT = ">"
    GTE = ">="


# ---------------------------------------------------------------------------
# Proposition types (tagged union via type field)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ToolOutputEquals:
    """Atomic proposition: tool X with input Y produces output Z.

    This is the critical link between a structured claim and a ToolReceipt.
    A verifier can extract tool_name, input, and expected_output from the
    proposition and match them against a receipt's input_inline and
    output_inline.

    Attributes:
        tool_name: Name of the tool (must match ToolReceipt.tool_name).
        input: Expected input dict (compared to ToolReceipt.input_inline).
        expected_output: Expected output dict (compared to ToolReceipt.output_inline).
        input_match: How to compare inputs (exact or subset).
        output_match: How to compare outputs (exact or subset).
    """
    tool_name: str
    input: dict
    expected_output: dict
    input_match: MatchMode = MatchMode.EXACT
    output_match: MatchMode = MatchMode.EXACT

    def to_dict(self) -> dict:
        return {
            "type": "tool_output_equals",
            "tool_name": self.tool_name,
            "input": self.input,
            "expected_output": self.expected_output,
            "input_match": self.input_match.value,
            "output_match": self.output_match.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ToolOutputEquals:
        return cls(
            tool_name=data["tool_name"],
            input=data.get("input", {}),
            expected_output=data.get("expected_output", {}),
            input_match=MatchMode(data.get("input_match", "exact")),
            output_match=MatchMode(data.get("output_match", "exact")),
        )

    def canonical_fingerprint(self) -> str:
        """Stable hash for equivalence comparison."""
        return _sha256_of(self.to_dict())


@dataclass(frozen=True)
class ValueComparison:
    """Atomic proposition: a field in a tool's output satisfies a comparison.

    Example: tool=compute_fibonacci, input={"n": 10}, path=["result"],
    op="==", value=55 means "the 'result' field of Fibonacci(10) equals 55."

    Attributes:
        tool_name: Name of the tool.
        input: Expected input dict.
        path: JSON path segments to the field in the output (e.g. ["result"]).
        op: Comparison operator.
        value: The value to compare against.
        input_match: How to compare inputs.
    """
    tool_name: str
    input: dict
    path: list[Union[str, int]]
    op: ComparisonOp
    value: Any
    input_match: MatchMode = MatchMode.EXACT

    def to_dict(self) -> dict:
        return {
            "type": "value_comparison",
            "tool_name": self.tool_name,
            "input": self.input,
            "path": self.path,
            "op": self.op.value,
            "value": self.value,
            "input_match": self.input_match.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ValueComparison:
        return cls(
            tool_name=data["tool_name"],
            input=data.get("input", {}),
            path=data.get("path", []),
            op=ComparisonOp(data["op"]),
            value=data.get("value"),
            input_match=MatchMode(data.get("input_match", "exact")),
        )

    def canonical_fingerprint(self) -> str:
        return _sha256_of(self.to_dict())


@dataclass(frozen=True)
class Compound:
    """Compound proposition with logical composition.

    Supports AND, OR, NOT, and IMPLIES.

    Canonicalization rules for AND/OR:
    - Flatten nested same-op children (AND(AND(a,b),c) → AND(a,b,c))
    - Deduplicate identical operands by fingerprint
    - Sort operands by fingerprint for stable ordering

    NOT requires exactly one arg. IMPLIES requires exactly two args
    (antecedent, consequent — order is significant).

    Attributes:
        op: The logical connective.
        args: Child propositions.
    """
    op: LogicalOp
    args: list  # list of Proposition (ToolOutputEquals | ValueComparison | Compound)

    def to_dict(self) -> dict:
        return {
            "type": "compound",
            "op": self.op.value,
            "args": [a.to_dict() for a in self.args],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Compound:
        return cls(
            op=LogicalOp(data["op"]),
            args=[proposition_from_dict(a) for a in data.get("args", [])],
        )

    def canonicalize(self) -> Compound:
        """Return a canonicalized copy of this compound proposition."""
        canon_args = [
            a.canonicalize() if isinstance(a, Compound) else a
            for a in self.args
        ]

        if self.op == LogicalOp.NOT and len(canon_args) != 1:
            raise ValueError("NOT requires exactly one arg")
        if self.op == LogicalOp.IMPLIES and len(canon_args) != 2:
            raise ValueError("IMPLIES requires exactly two args")

        if self.op in (LogicalOp.AND, LogicalOp.OR):
            # Flatten nested same-op
            flattened: list = []
            for a in canon_args:
                if isinstance(a, Compound) and a.op == self.op:
                    flattened.extend(a.args)
                else:
                    flattened.append(a)

            # Dedupe + sort by fingerprint
            seen: dict[str, Any] = {}
            for a in flattened:
                fp = a.canonical_fingerprint() if hasattr(a, "canonical_fingerprint") else _sha256_of(a.to_dict())
                seen[fp] = a

            ordered = [seen[k] for k in sorted(seen.keys())]
            return Compound(op=self.op, args=ordered)

        return Compound(op=self.op, args=canon_args)

    def canonical_fingerprint(self) -> str:
        return _sha256_of(self.canonicalize().to_dict())


# Type alias for any proposition
Proposition = Union[ToolOutputEquals, ValueComparison, Compound]


def proposition_from_dict(data: dict) -> Proposition:
    """Deserialise a proposition from a dict (tagged union factory).

    Args:
        data: Dict with a "type" field identifying the proposition type.

    Returns:
        The appropriate proposition type.

    Raises:
        ValueError: If the type field is unknown.
    """
    t = data.get("type")
    if t == "tool_output_equals":
        return ToolOutputEquals.from_dict(data)
    if t == "value_comparison":
        return ValueComparison.from_dict(data)
    if t == "compound":
        return Compound.from_dict(data)
    raise ValueError(f"Unknown proposition type: {t!r}")


# ---------------------------------------------------------------------------
# StructuredClaim
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StructuredClaim:
    """Machine-parseable claim content for URP.

    Replaces the free-text ``statement: str`` as the authoritative
    proposition in a Claim. During the transition period, both
    ``statement`` and ``structured_claim`` coexist on Claim.

    Attributes:
        sc_version: Schema version for this StructuredClaim (e.g. "0.5").
        kind: Routing hint from ClaimKind (e.g. "tool_output").
        proposition: The proposition tree.
    """
    sc_version: str
    kind: str  # ClaimKind value string — uses existing enum, not a duplicate
    proposition: Proposition

    def to_dict(self) -> dict:
        return {
            "sc_version": self.sc_version,
            "kind": self.kind,
            "proposition": self.proposition.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> StructuredClaim:
        return cls(
            sc_version=data["sc_version"],
            kind=data["kind"],
            proposition=proposition_from_dict(data["proposition"]),
        )

    def canonicalize(self) -> StructuredClaim:
        """Return a copy with the proposition tree canonicalized."""
        if isinstance(self.proposition, Compound):
            return StructuredClaim(
                sc_version=self.sc_version,
                kind=self.kind,
                proposition=self.proposition.canonicalize(),
            )
        return self

    def canonical_json(self) -> str:
        """Canonical JSON string of the canonicalized claim."""
        return _canonical_json(self.canonicalize().to_dict())

    def fingerprint(self) -> str:
        """SHA-256 fingerprint of the canonical JSON."""
        return _sha256_of(self.canonicalize().to_dict())

    def render_statement(self) -> str:
        """Generate a human-readable summary from the proposition tree.

        This is the auto-generated replacement for ``Claim.statement``
        during the Phase 2 migration.
        """
        return _render_proposition(self.proposition)


def _render_proposition(prop: Proposition) -> str:
    """Render a proposition as a human-readable string."""
    if isinstance(prop, ToolOutputEquals):
        input_str = ", ".join(f"{k}={v!r}" for k, v in sorted(prop.input.items()))
        return f"{prop.tool_name}({input_str}) produces {prop.expected_output}"

    if isinstance(prop, ValueComparison):
        input_str = ", ".join(f"{k}={v!r}" for k, v in sorted(prop.input.items()))
        path_str = ".".join(str(p) for p in prop.path)
        return f"{prop.tool_name}({input_str}).{path_str} {prop.op.value} {prop.value!r}"

    if isinstance(prop, Compound):
        if prop.op == LogicalOp.NOT:
            return f"NOT ({_render_proposition(prop.args[0])})"
        if prop.op == LogicalOp.IMPLIES:
            return (
                f"IF ({_render_proposition(prop.args[0])}) "
                f"THEN ({_render_proposition(prop.args[1])})"
            )
        joiner = f" {prop.op.value.upper()} "
        parts = [f"({_render_proposition(a)})" for a in prop.args]
        return joiner.join(parts)

    return str(prop)
